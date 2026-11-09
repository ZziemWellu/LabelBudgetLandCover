"""Baseline: end-to-end fine-tuning of DeepLabV3-ResNet50 (COCO-pretrained) on the SAME
labelled images as the matched linear-probe runs (DeepGlobe folds 0-2, LoveDA draws 0-2).

Fixed recipe chosen a priori (no tuning on test data): output stride 16 (the DeepLabV3
training setting; COCO weights loaded unchanged), 518x518 input, batch 4, 1500 iterations,
AdamW (backbone 1e-4, heads 1e-3, wd 1e-4), poly decay 0.9, flips + 90-degree rotations,
CE (+0.4 aux), fp32, final iterate evaluated (no checkpoint selection).
Scored per pixel at 518x518 against the same ground truth as the probes.
Usage: python finetune.py [ITERS]
"""
import json, os, sys, time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from torchvision.models import resnet50
from torchvision.models.segmentation import deeplabv3_resnet50
from torchvision.models.segmentation.deeplabv3 import _deeplabv3_resnet
from PIL import Image
from common import OUT, IMG, IGNORE, N_CLASSES, list_items, decode_mask
from lab import log, scores, dev

ITERS = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
BUDGETS = [10, 100]
RUNS = [("DG-f0", 0), ("DG-f1", 0), ("DG-f2", 0), ("LD-all", 0), ("LD-all", 1), ("LD-all", 2)]
if os.environ.get("SMOKE") == "1":
    BUDGETS, RUNS = [10], [("DG-f0", 0)]
tf = transforms.Compose([transforms.Resize((IMG, IMG), interpolation=transforms.InterpolationMode.BILINEAR),
                         transforms.ToTensor(),
                         transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])


def load(src, items, i):
    return tf(Image.open(items[i][0]).convert("RGB")), torch.from_numpy(decode_mask(src, items[i][1]).astype(np.int64))


def build(C):
    sd = deeplabv3_resnet50(weights="DEFAULT").state_dict()
    m = _deeplabv3_resnet(resnet50(replace_stride_with_dilation=[False, False, True]), 21, True)
    m.load_state_dict(sd)    # output stride 16; parameters identical to the COCO checkpoint
    m.classifier[-1] = nn.Conv2d(256, C, 1)
    m.aux_classifier[-1] = nn.Conv2d(256, C, 1)
    return m.to(dev)


def train(src, imgs, C, seed):
    torch.manual_seed(seed); np.random.seed(seed)
    items = list_items(src)
    data = [load(src, items, i) for i in imgs]
    X = torch.stack([d[0] for d in data]); Y = torch.stack([d[1] for d in data])
    m = build(C)
    head = [p for n, p in m.named_parameters() if "classifier" in n]
    bb = [p for n, p in m.named_parameters() if "classifier" not in n]
    opt = torch.optim.AdamW([{"params": bb, "lr": 1e-4}, {"params": head, "lr": 1e-3}], weight_decay=1e-4)
    base_lr = [g["lr"] for g in opt.param_groups]
    rng = np.random.default_rng(seed)
    m.train(); t0 = time.time()
    for it in range(ITERS):
        for g, lr in zip(opt.param_groups, base_lr):
            g["lr"] = lr * (1 - it / ITERS) ** 0.9
        b = rng.integers(0, len(X), 4)
        x, y = X[b].clone(), Y[b].clone()
        if rng.random() < 0.5: x, y = x.flip(-1), y.flip(-1)
        if rng.random() < 0.5: x, y = x.flip(-2), y.flip(-2)
        k = int(rng.integers(0, 4))
        x, y = torch.rot90(x, k, (-2, -1)), torch.rot90(y, k, (-2, -1))
        x, y = x.to(dev), y.to(dev)
        out = m(x)
        loss = F.cross_entropy(out["out"], y, ignore_index=IGNORE) + \
            0.4 * F.cross_entropy(out["aux"], y, ignore_index=IGNORE)
        opt.zero_grad(set_to_none=True)
        loss.backward(); opt.step()
        if (it + 1) % 250 == 0:
            log(f"    it {it+1}/{ITERS} loss {loss.item():.3f} {time.time()-t0:.0f}s")
    return m


@torch.no_grad()
def evaluate(m, src, idx, C):
    m.eval()
    items = list_items(src)
    M = np.zeros((C, C))
    for s in range(0, len(idx), 4):
        data = [load(src, items, i) for i in idx[s:s + 4]]
        x = torch.stack([d[0] for d in data]).to(dev)
        p = m(x)["out"].argmax(1).cpu().numpy()
        g = torch.stack([d[1] for d in data]).numpy()
        v = g != IGNORE
        M += np.bincount(p[v] * C + g[v], minlength=C * C).reshape(C, C)
    return M


splits = json.load(open(OUT / "final_splits.json"))
out = open(OUT / ("finetune_smoke.jsonl" if os.environ.get("SMOKE") == "1" else "finetune.jsonl"), "a")
for exp, seed in RUNS:
    src = "dg" if exp.startswith("DG") else "ld_train"
    C = N_CLASSES[src]
    pool = np.array(splits[exp]["pool"])
    order = np.random.default_rng(1000 + seed).permutation(pool)   # same draw as the probes
    for n in BUDGETS:
        log(f"[{exp} seed {seed} n={n}] training")
        m = train(src, order[:n], C, seed)
        if src == "dg":
            evals = {"test": ("dg", np.array(splits[exp]["test"]))}
        else:
            evals = {"rural": ("ld_val", np.array(splits[exp]["rural"])),
                     "urban": ("ld_val", np.array(splits[exp]["urban"]))}
        Ms = {k: evaluate(m, s, idx, C) for k, (s, idx) in evals.items()}
        if len(Ms) > 1:
            Ms["all"] = sum(Ms.values())
        for k, M in Ms.items():
            iou, acc = scores(M)
            out.write(json.dumps(dict(exp=exp, method="finetune_deeplabv3", n=n, seed=seed, eval=k,
                                      miou=float(iou.mean()), acc=float(acc),
                                      iou=[float(v) for v in iou], iters=ITERS,
                                      recipe="os16_fp32")) + "\n")
            out.flush()
            log(f"  {k}: mIoU {iou.mean():.1f}")
        del m; torch.cuda.empty_cache()
log("finetune done")
