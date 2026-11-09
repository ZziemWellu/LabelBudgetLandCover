"""FINAL main experiment (DINOv2 ViT-B/14-reg, frozen).

Changes vs the pilot (run_experiments.py), each answering a foreseeable reviewer objection:
  * DeepGlobe: 5-fold cross-validation x 3 label draws (pilot: one 161-image split).
  * Same patch protocol at every budget: all patches of the labelled images, uniformly
    subsampled per image only when the 500k-patch memory cap is exceeded.
  * Class-balanced linear probe added (imbalance is the obvious objection).
  * L2-strength sensitivity (lambda in {1e-4, 1e-3, 1e-2, 1e-1}) at 5 / 50 / all images.
  * Cluster-then-label K-sensitivity (K in {25, 50, 100, 200}).
  * Sparse point annotation: N random single-pixel labels spread over the whole pool.
  * Patch-oracle ceiling: best achievable mIoU for any 14x14-patch classifier.
No hyperparameter is selected on evaluation data.
"""
import json, os
import numpy as np
import torch
from common import OUT, NP, N_CLASSES, load_feats
from lab import (log, patch_labels, build_reduced, dense_set, point_set, fit_linear, kmeans,
                 label_clusters, Scorer, finalize, dev, R_RED, KM_CAP)

SMOKE = os.environ.get("SMOKE") == "1"
BUDGETS = [1, 2, 5, 10, 25, 50, 100, 250, "all"]
POINTS = [100, 300, 1000, 3000, 10000, 30000]
LAMBDA_MAIN, LAMBDAS, LAMBDA_N = 1e-3, [1e-4, 1e-2, 1e-1], {5, 50, "all"}
K_MAIN, K_SWEEP = 50, [25, 100, 200]
DG_DRAWS, LD_SEEDS = [0, 1, 2], [0, 1, 2, 3, 4]
if SMOKE:
    BUDGETS, POINTS, DG_DRAWS, LD_SEEDS, K_SWEEP = [1, 5, "all"], [100, 1000], [0], [0], [25]
PREFIX = "smoke" if SMOKE else "final"

meta = {s: json.load(open(OUT / f"meta_{s}.json")) for s in ["dg", "ld_train", "ld_val"]}
dom = {s: np.array([m["domain"] for m in meta[s]]) for s in meta}
folds = np.array_split(np.random.default_rng(2026).permutation(len(meta["dg"])), 5)
EXPS = []
for f in range(5):
    test = np.sort(folds[f])
    pool = np.sort(np.concatenate([folds[g] for g in range(5) if g != f]))
    EXPS.append(dict(name=f"DG-f{f}", src="dg", pool=pool, sets={"test": test}, seeds=DG_DRAWS,
                     lam=True, ksweep_seeds=[0], points=True))
    if SMOKE:
        break
ld_sets = {"rural": np.where(dom["ld_val"] == "Rural")[0], "urban": np.where(dom["ld_val"] == "Urban")[0]}
for name, pool, extra in [("LD-all", np.arange(len(meta["ld_train"])), True),
                          ("LD-rural", np.where(dom["ld_train"] == "Rural")[0], False),
                          ("LD-urban", np.where(dom["ld_train"] == "Urban")[0], False)]:
    EXPS.append(dict(name=name, src="ld_train", pool=pool, sets=ld_sets, seeds=LD_SEEDS,
                     lam=extra, ksweep_seeds=LD_SEEDS if extra else [], points=extra))
json.dump({E["name"]: {"pool": E["pool"].tolist(), **{k: v.tolist() for k, v in E["sets"].items()}}
           for E in EXPS}, open(OUT / f"{PREFIX}_splits.json", "w"))

# ── Phase A: fit ────────────────────────────────────────────────
models, cents = [], {}
src_cache = {}
for E in EXPS:
    src, C, pool = E["src"], N_CLASSES[E["src"]], E["pool"]
    if src not in src_cache:
        Fm = load_feats(src)
        H = np.load(OUT / f"hist_{src}.npy")
        red = build_reduced(Fm, len(H), R_RED, OUT / f"red400_dinov2_b_{src}.npy")
        src_cache[src] = (Fm, H, patch_labels(H), red)
    Fm, H, Y, red = src_cache[src]
    log(f"[{E['name']}] pool={len(pool)} C={C}")
    base = dict(exp=E["name"], pool=len(pool))
    models.append(dict(base, method="patch_oracle", n=-1, seed=0, kind="oracle"))
    for seed in E["seeds"]:
        rng = np.random.default_rng(seed)
        flat = np.sort(rng.choice(len(pool) * R_RED, min(KM_CAP, len(pool) * R_RED), replace=False))
        kx = red[pool[flat // R_RED], flat % R_RED]
        Ks = [C, K_MAIN] + (K_SWEEP if seed in E["ksweep_seeds"] else [])
        for K in Ks:
            cents[(E["name"], seed, K)] = kmeans(kx, K, seed)
        del kx
        models.append(dict(base, method="kmeans_hungarian", n=0, seed=seed, kind="cent",
                           key=(E["name"], seed, C), mapping=None))
        log(f"  seed {seed}: k-means K={Ks} done")
        order = np.random.default_rng(1000 + seed).permutation(pool)
        for n in BUDGETS:
            nn_ = len(pool) if n == "all" else n
            X, y = dense_set(Fm, red, Y, order[:nn_], seed, R_RED)
            W, b = fit_linear(X, y, C, LAMBDA_MAIN)
            models.append(dict(base, method="linear", n=nn_, seed=seed, kind="lin", W=W, b=b))
            W, b = fit_linear(X, y, C, LAMBDA_MAIN, balanced=True)
            models.append(dict(base, method="linear_balanced", n=nn_, seed=seed, kind="lin", W=W, b=b))
            if E["lam"] and n in LAMBDA_N:
                for lam in LAMBDAS:
                    W, b = fit_linear(X, y, C, lam)
                    models.append(dict(base, method=f"linear_lam{lam:g}", n=nn_, seed=seed,
                                       kind="lin", W=W, b=b))
            for K in Ks[1:]:
                mp = label_clusters(cents[(E["name"], seed, K)], X, y, C)
                models.append(dict(base, method="cluster_label" if K == K_MAIN else f"cluster_label_K{K}",
                                   n=nn_, seed=seed, kind="cent", key=(E["name"], seed, K), mapping=mp))
            log(f"  seed {seed} n={nn_:>5}: {len(y):>7} patches, {len(np.unique(y))} classes")
            del X, y
        if E["points"]:
            for P in POINTS:
                X, y = point_set(Fm, H, pool, P, seed)
                W, b = fit_linear(X, y, C, LAMBDA_MAIN)
                models.append(dict(base, method="linear_points", n=P, seed=seed, kind="lin",
                                   W=W, b=b, unit="points"))
            log(f"  seed {seed}: point budgets done")
log(f"Phase A done: {len(models)} models")

# ── Phase B: score ──────────────────────────────────────────────
indexed = list(enumerate(models))
conf = {}
groups = [[E] for E in EXPS if E["src"] == "dg"] + [[E for E in EXPS if E["src"] == "ld_train"]]
for G in groups:
    names = {E["name"] for E in G}
    ms = [(i, m) for i, m in indexed if m["exp"] in names]
    eval_src = "dg" if G[0]["src"] == "dg" else "ld_val"
    C = N_CLASSES[eval_src]
    Fm = load_feats(eval_src)
    H = np.load(OUT / f"hist_{eval_src}.npy")
    sc = Scorer(ms, cents, C)
    for sname, idx in G[0]["sets"].items():
        for s in range(0, len(idx), 32):
            ch = idx[s:s + 32]
            X = torch.from_numpy(np.concatenate([np.asarray(Fm[i * NP:(i + 1) * NP]) for i in ch])).to(dev).float()
            h = torch.from_numpy(H[ch].reshape(-1, C).astype(np.float64)).to(dev)
            sc.add(X, h, sname)
    conf.update(sc.conf)
    log(f"  scored {sorted(names)}")
    del sc
    torch.cuda.empty_cache()

set_names = lambda m: ["test"] if m["exp"].startswith("DG") else ["rural", "urban"]
rows = finalize(indexed, conf, set_names, extra={"backbone": "dinov2_b"}, out_prefix=PREFIX)
log(f"wrote {len(rows)} rows to {PREFIX}.jsonl")
