"""Step 1: extract missing features, verify cache alignment, build patch label histograms.

Outputs (in outputs/):
  loveda_val_features.npy       (1669*1369, 768) float16
  hist_{dg,ld_train,ld_val}.npy (N, 1369, C) uint16 per-patch GT pixel counts
  meta_{src}.json               image names and domains in cache order
"""
import json, sys, time
import numpy as np
import torch
from common import (OUT, FEATS, NP, DIM, N_CLASSES, list_items, decode_mask,
                    patch_hist, load_feats, load_dinov2, extract)

dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("device:", dev)

# ── Metadata ────────────────────────────────────────────────────
items = {s: list_items(s) for s in ["dg", "ld_train", "ld_val"]}
for s, it in items.items():
    doms = {d: sum(1 for x in it if x[2] == d) for d in sorted({x[2] for x in it})}
    print(f"{s}: {len(it)} images {doms}")
    json.dump([{"image": x[0].name, "domain": x[2]} for x in it],
              open(OUT / f"meta_{s}.json", "w"), indent=0)

model = None

# ── LoveDA val features ─────────────────────────────────────────
if not FEATS["ld_val"].exists():
    model = load_dinov2(dev)
    paths = [x[0] for x in items["ld_val"]]
    tmp = FEATS["ld_val"].with_suffix(".partial.npy")
    mm = np.lib.format.open_memmap(str(tmp), mode="w+", dtype=np.float16,
                                   shape=(len(paths) * NP, DIM))
    t0 = time.time(); row = 0
    for i, f in enumerate(extract(model, paths, dev)):
        n = f.shape[0] * NP
        mm[row:row + n] = f.reshape(n, DIM); row += n
        if (i + 1) % 25 == 0:
            done = row // NP
            print(f"  val features {done}/{len(paths)}  {time.time()-t0:.0f}s")
    mm.flush(); del mm
    tmp.replace(FEATS["ld_val"])
    print(f"  saved {FEATS['ld_val'].name} in {time.time()-t0:.0f}s")

# ── Verify cached features belong to the images we think they do ─
for s in ["dg", "ld_train", "ld_val"]:
    F_ = load_feats(s)
    assert F_.shape == (len(items[s]) * NP, DIM), (s, F_.shape)
for s in ["dg", "ld_train"]:
    if model is None:
        model = load_dinov2(dev)
    F_ = load_feats(s)
    idx = [0, len(items[s]) // 2, len(items[s]) - 1]
    fresh = next(extract(model, [items[s][i][0] for i in idx], dev, batch=3)).astype(np.float32)
    for j, i in enumerate(idx):
        cached = np.asarray(F_[i * NP:(i + 1) * NP], dtype=np.float32)
        cos = (cached * fresh[j]).sum(1).mean()
        print(f"  alignment {s}[{i}] mean cosine fresh-vs-cache = {cos:.4f}")
        assert cos > 0.98, "feature cache does not match image order"
del model
torch.cuda.empty_cache()

# ── Per-patch ground-truth histograms ───────────────────────────
for s in ["dg", "ld_train", "ld_val"]:
    out = OUT / f"hist_{s}.npy"
    if out.exists():
        continue
    C = N_CLASSES[s]
    H = np.zeros((len(items[s]), NP, C), dtype=np.uint16)
    t0 = time.time()
    for i, (_, mp, _) in enumerate(items[s]):
        H[i] = patch_hist(decode_mask(s, mp), C)
        if (i + 1) % 400 == 0:
            print(f"  {s} masks {i+1}/{len(items[s])}  {time.time()-t0:.0f}s")
    np.save(out, H)
    tot = H.sum((0, 1)).astype(np.float64)
    print(f"  {s}: class pixel shares " +
          " ".join(f"{100*t/tot.sum():.1f}%" for t in tot) +
          f" | ignored {100*(1 - tot.sum()/(H.shape[0]*NP*196)):.1f}%")

print("prepare done")
