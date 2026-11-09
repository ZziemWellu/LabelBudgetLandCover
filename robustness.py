"""Reviewer-driven robustness checks on the existing results (no new model fitting).
1. Fold-level tests on DeepGlobe: average the 3 draws within each CV fold, then test the
   5 fold means (removes the dependence between draws that share a test fold).
2. Fold sign consistency: in how many of the 5 folds does each effect have the same sign.
3. Actual number of labelled training patches per image after the 50% purity rule.
4. Break-even point cost: the cost ratio at which point labelling equals dense labelling.
Writes outputs/robustness.md.
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
from common import OUT

BUD = ["1", "2", "5", "10", "25", "50", "100", "250", "all"]


def load(path):
    d = pd.DataFrame([json.loads(l) for l in open(path)])
    d["b"] = [("all" if (u == "images" and n == p) else str(n)) for n, p, u in zip(d.n, d.pool, d.unit)]
    return d


def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); m = len(p)
    adj = np.empty(m); run = 0
    for r, i in enumerate(o):
        run = max(run, (m - r) * p[i]); adj[i] = min(1, run)
    return adj


df = load(OUT / "final.jsonl")
dg = df[df.exp.str.startswith("DG") & (df["eval"] == "test")]
L = []


def fold_means(meth, b, unit="images"):
    s = dg[(dg.method == meth) & (dg.b == b)]
    return s.groupby("exp").miou.mean()


def fold_test(A, B):
    j = A.index.intersection(B.index)
    d = (A[j] - B[j]).values
    return d.mean(), stats.ttest_rel(A[j], B[j]).pvalue, int((d > 0).sum()), len(d)


L.append("### DeepGlobe fold-level paired tests (3 draws averaged within each fold; n = 5 folds)\n")
L.append("| Comparison | budget | mean diff | p (fold-level) | p_Holm | folds with diff > 0 |")
L.append("|---|---|---|---|---|---|")
for a, b_, name in [("linear", "cluster_label", "probe − cluster"),
                    ("linear_balanced", "linear", "balanced − probe")]:
    rows = []
    for b in BUD:
        rows.append((b, *fold_test(fold_means(a, b), fold_means(b_, b))))
    adj = holm([r[2] for r in rows])
    for (b, m, p, pos, n), pa in zip(rows, adj):
        L.append(f"| {name} | {b} | {m:+.1f} | {p:.2g} | {pa:.2g} | {pos}/{n} |")
for P, n in [("100", "5"), ("300", "10"), ("1000", "50"), ("30000", "250")]:
    m, p, pos, k = fold_test(fold_means("linear_points", P), fold_means("linear", n))
    L.append(f"| {P} points − {n} images | — | {m:+.1f} | {p:.2g} | — | {pos}/{k} |")

# labelled patches per image after the purity rule
L.append("\n### Labelled training patches per image after the 50% purity rule\n")
for src, name in [("dg", "DeepGlobe"), ("ld_train", "LoveDA train")]:
    H = np.load(OUT / f"hist_{src}.npy", mmap_mode="r")
    tot = H.sum(-1)
    pure = (H.max(-1) >= 0.5 * 196) & (tot > 0)
    per = pure.sum(1)
    L.append(f"- {name}: mean {per.mean():.0f} of 1369 patches per image are labelled "
             f"(median {np.median(per):.0f}; {100 * per.mean() / 1369:.1f}%).")
    if src == "dg":
        dg_per = per.mean()
    else:
        ld_per = per.mean()

# break-even: points match dense accuracy at P points vs n images -> a point may cost up to n/P images
L.append("\n### Break-even annotation cost (from equal-accuracy pairs)\n")
L.append("- DeepGlobe: 1000 points ≈ 50 images (52.4 vs 52.5) → point labelling is cheaper whenever "
         "labelling 20 points takes less time than annotating one 2448 × 2448 image.")
L.append("- DeepGlobe: 30,000 points ≈ 250 images (62.2 vs 61.9) → break-even at 120 points per image.")
L.append("- LoveDA: 30,000 points (43.8) ≈ 250 images (44.1) → break-even at 120 points per image.")
L.append(f"- Patch labels supplied: DeepGlobe 50 images ≈ {50 * dg_per:,.0f}; 250 images ≈ {250 * dg_per:,.0f}; "
         f"LoveDA 250 images ≈ {250 * ld_per:,.0f}.")

(OUT / "robustness.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
