"""Backbone comparison: is the label-efficiency picture specific to one model?

Backbones (all frozen): DINOv2 ViT-S/14-reg, ViT-B/14-reg, ViT-L/14-reg (self-supervised,
three sizes) and ResNet-50 trained with ImageNet-1k labels (layer3, stride 16; input 592 px
so that its 37x37 grid covers exactly the same ground footprint as the ViT 14-px patches).

Identical protocol for every backbone: 256 fixed random patches per labelled image (same
positions for every backbone), DeepGlobe 5-fold CV (1 draw/fold), LoveDA all-pool (3 draws).
Evaluation streams every test image through the backbone and scores all its patches.
Usage: python run_backbones.py dinov2_s resnet50 dinov2_b dinov2_l
"""
import json, sys, time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from torchvision import transforms
from PIL import Image
from common import OUT, NP, N_CLASSES, HUB_DIR, list_items, load_feats
from lab import (log, patch_labels, red_index, dense_set, fit_linear, kmeans, label_clusters,
                 Scorer, finalize, dev, KM_CAP)

KEEP = 256
BUDGETS = [1, 2, 5, 10, 25, 50, 100, 250, "all"]
DG_SEEDS, LD_SEEDS, K_MAIN = [0], [0, 1, 2], 50
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


def make_backbone(name):
    if name.startswith("dinov2"):
        arch = {"dinov2_s": "dinov2_vits14_reg", "dinov2_b": "dinov2_vitb14_reg",
                "dinov2_l": "dinov2_vitl14_reg"}[name]
        m = torch.hub.load(str(HUB_DIR), arch, source="local", pretrained=True).eval().to(dev)
        size, bs = 518, (4 if name == "dinov2_l" else 8)
        fn = lambda x: m.forward_features(x)["x_norm_patchtokens"]
    else:
        r = torchvision.models.resnet50(weights="IMAGENET1K_V2")
        m = nn.Sequential(r.conv1, r.bn1, r.relu, r.maxpool, r.layer1, r.layer2, r.layer3).eval().to(dev)
        size, bs = 592, 8
        fn = lambda x: m(x).flatten(2).transpose(1, 2)
    tf = transforms.Compose([transforms.Resize((size, size), interpolation=transforms.InterpolationMode.BILINEAR),
                             transforms.ToTensor(), transforms.Normalize(MEAN, STD)])

    @torch.no_grad()
    def feats(paths):
        x = torch.stack([tf(Image.open(p).convert("RGB")) for p in paths]).to(dev)
        t = fn(x)
        assert t.shape[1] == NP, t.shape
        return F.normalize(t.float(), dim=-1)
    return feats, bs


def reduced_feats(name, src, feats, bs):
    """(N, KEEP, D) float16 at the fixed patch positions; cached on disk."""
    path = OUT / f"red{KEEP}_{name}_{src}.npy"
    if path.exists():
        return np.load(path, mmap_mode="r")
    if name == "dinov2_b":    # reuse the 400-patch cache built by run_final.py (same positions)
        return np.load(OUT / f"red400_dinov2_b_{src}.npy", mmap_mode="r")[:, :KEEP]
    items = list_items(src)
    idx = torch.from_numpy(red_index(len(items))[:, :KEEP].astype(np.int64)).to(dev)
    X = None
    t0 = time.time()
    for s in range(0, len(items), bs):
        f = feats([it[0] for it in items[s:s + bs]])
        g = torch.gather(f, 1, idx[s:s + len(f)].unsqueeze(-1).expand(-1, -1, f.shape[-1]))
        if X is None:
            X = np.lib.format.open_memmap(str(path.with_suffix(".partial.npy")), mode="w+",
                                          dtype=np.float16, shape=(len(items), KEEP, f.shape[-1]))
        X[s:s + len(f)] = g.half().cpu().numpy()
        if (s // bs) % 100 == 0:
            log(f"    {name}/{src} {s + len(f)}/{len(items)} {time.time() - t0:.0f}s")
    X.flush(); del X
    path.with_suffix(".partial.npy").replace(path)
    return np.load(path, mmap_mode="r")


def run(name):
    log(f"=== backbone {name} ===")
    feats, bs = make_backbone(name)
    splits = json.load(open(OUT / "final_splits.json"))
    meta_v = json.load(open(OUT / "meta_ld_val.json"))
    exps = [dict(name=f"DG-f{f}", src="dg", pool=np.array(splits[f"DG-f{f}"]["pool"]),
                 test=np.array(splits[f"DG-f{f}"]["test"]), seeds=DG_SEEDS) for f in range(5)]
    exps.append(dict(name="LD-all", src="ld_train", pool=np.array(splits["LD-all"]["pool"]), seeds=LD_SEEDS))
    models, cents = [], {}
    for E in exps:
        src, C, pool = E["src"], N_CLASSES[E["src"]], E["pool"]
        red = reduced_feats(name, src, feats, bs)
        H = np.load(OUT / f"hist_{src}.npy")
        Y = patch_labels(H)
        base = dict(exp=E["name"], pool=len(pool))
        for seed in E["seeds"]:
            rng = np.random.default_rng(seed)
            flat = np.sort(rng.choice(len(pool) * KEEP, min(KM_CAP, len(pool) * KEEP), replace=False))
            kx = np.asarray(red[pool[flat // KEEP], flat % KEEP])
            for K in (C, K_MAIN):
                cents[(E["name"], seed, K)] = kmeans(kx, K, seed)
            del kx
            models.append(dict(base, method="kmeans_hungarian", n=0, seed=seed, kind="cent",
                               key=(E["name"], seed, C), mapping=None))
            order = np.random.default_rng(1000 + seed).permutation(pool)
            for n in BUDGETS:
                nn_ = len(pool) if n == "all" else n
                X, y = dense_set(None, red, Y, order[:nn_], seed, KEEP)
                W, b = fit_linear(X, y, C)
                models.append(dict(base, method="linear", n=nn_, seed=seed, kind="lin", W=W, b=b))
                mp = label_clusters(cents[(E["name"], seed, K_MAIN)], X, y, C)
                models.append(dict(base, method="cluster_label", n=nn_, seed=seed, kind="cent",
                                   key=(E["name"], seed, K_MAIN), mapping=mp))
        log(f"  [{name}] fitted {E['name']}")

    indexed = list(enumerate(models))
    conf = {}
    # DeepGlobe: stream each fold's test images, score only that fold's models
    Hd = np.load(OUT / "hist_dg.npy")
    dg_items = list_items("dg")
    sc = Scorer([(i, m) for i, m in indexed if m["exp"].startswith("DG")], cents, N_CLASSES["dg"])
    for E in exps[:5]:
        for s in range(0, len(E["test"]), bs):
            ch = E["test"][s:s + bs]
            X = feats([dg_items[i][0] for i in ch])
            X = X.reshape(-1, X.shape[-1])
            h = torch.from_numpy(Hd[ch].reshape(-1, N_CLASSES["dg"]).astype(np.float64)).to(dev)
            sc.add(X, h, "test", model_filter=lambda m, n=E["name"]: m["exp"] == n)
    conf.update(sc.conf); del sc
    log(f"  [{name}] scored DeepGlobe")
    # LoveDA val, rural and urban
    Hv = np.load(OUT / "hist_ld_val.npy")
    val_items = list_items("ld_val")
    sc = Scorer([(i, m) for i, m in indexed if m["exp"] == "LD-all"], cents, N_CLASSES["ld_val"])
    cached = load_feats("ld_val") if name == "dinov2_b" else None
    t0 = time.time()
    for dname in ["Rural", "Urban"]:
        idx = np.array([i for i, m in enumerate(meta_v) if m["domain"] == dname])
        for s in range(0, len(idx), bs):
            ch = idx[s:s + bs]
            if cached is not None:
                X = torch.from_numpy(np.concatenate([np.asarray(cached[i * NP:(i + 1) * NP]) for i in ch])).to(dev).float()
            else:
                X = feats([val_items[i][0] for i in ch])
                X = X.reshape(-1, X.shape[-1])
            h = torch.from_numpy(Hv[ch].reshape(-1, N_CLASSES["ld_val"]).astype(np.float64)).to(dev)
            sc.add(X, h, dname.lower())
        log(f"  [{name}] scored LoveDA {dname} {time.time() - t0:.0f}s")
    conf.update(sc.conf); del sc
    set_names = lambda m: ["test"] if m["exp"].startswith("DG") else ["rural", "urban"]
    finalize(indexed, conf, set_names, extra={"backbone": name}, out_prefix=f"backbone_{name}")
    torch.cuda.empty_cache()


if __name__ == "__main__":
    for name in sys.argv[1:]:
        run(name)
    log("backbones done")
