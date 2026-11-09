"""Tables, statistics and figures for the paper, from the FINAL outputs only:
outputs/final.jsonl, outputs/backbone_*.jsonl, outputs/finetune.jsonl (if present).
Writes outputs/final_tables.md and outputs/figures_final/*.{png,pdf}.
"""
import glob, json, sys
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import OUT, DG_CLASSES, LD_CLASSES

sys.stdout.reconfigure(encoding="utf-8")
FIG = OUT / "figures_final"; FIG.mkdir(exist_ok=True)
BUD = ["1", "2", "5", "10", "25", "50", "100", "250", "all"]
BUD_X = {b: (int(b) if b != "all" else None) for b in BUD}
KM2 = {"dg": 2448 * 2448 * 0.5 ** 2 / 1e6, "ld": 1024 * 1024 * 0.3 ** 2 / 1e6}   # ground area per image


def load(path):
    d = pd.DataFrame([json.loads(l) for l in open(path)])
    d["n"] = d["n"].astype(int)
    d["b"] = [("all" if (u == "images" and n == p) else str(n)) for n, p, u in zip(d.n, d.pool, d.unit)]
    d["ds"] = np.where(d.exp.str.startswith("DG"), "dg", "ld")
    return d


df = load(OUT / "final.jsonl")
bb = pd.concat([load(f) for f in sorted(glob.glob(str(OUT / "backbone_*.jsonl")))], ignore_index=True)
ft_path = OUT / "finetune.jsonl"
ft = load_ft = None
if ft_path.exists():
    ft = pd.DataFrame([json.loads(l) for l in open(ft_path)])
    ft = ft[ft.iters == ft.iters.max()]

# main evaluation slices: DeepGlobe = pooled over the 5 CV folds; LoveDA = combined val set
def main_slice(d, ds):
    if ds == "dg":
        return d[d.exp.str.startswith("DG") & (d["eval"] == "test")]
    return d[(d.exp == "LD-all") & (d["eval"] == "all")]


BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False})
TITLE = {"dg": "DeepGlobe", "ld": "LoveDA"}
lines = []


def md(title, tab, note=None):
    lines.append(f"\n### {title}\n\n" + tab.to_markdown() + "\n")
    if note:
        lines.append(f"\n{note}\n")


def ms(x):
    x = np.asarray(x, float)
    return f"{x.mean():.1f} ± {x.std(ddof=1):.1f}" if len(x) > 1 else f"{x.mean():.1f}"


def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); m = len(p)
    adj = np.empty(m); run = 0
    for r, i in enumerate(o):
        run = max(run, (m - r) * p[i]); adj[i] = min(1, run)
    return adj


def paired(d, a, b, keys=("exp", "seed")):
    """Paired differences a-b per budget (pairs = same fold/draw = same labelled images)."""
    out = {}
    for bud in BUD:
        A = d[(d.method == a) & (d.b == bud)].set_index(list(keys)).miou
        B = d[(d.method == b) & (d.b == bud)].set_index(list(keys)).miou
        j = A.index.intersection(B.index)
        if len(j) < 2:
            continue
        diff = (A[j] - B[j]).values
        out[bud] = (diff.mean(), diff.std(ddof=1) / np.sqrt(len(diff)), stats.ttest_rel(A[j], B[j]).pvalue,
                    diff.mean() / diff.std(ddof=1) if diff.std(ddof=1) > 0 else np.inf, len(diff))
    adj = holm([v[2] for v in out.values()])
    return {k: (*v, pa) for (k, v), pa in zip(out.items(), adj)}


def fmt_pair(r):
    m, se, p, dz, n, pa = r
    star = "*" if pa < 0.05 else ""
    return f"{m:+.1f} (d_z={dz:.1f}, p_Holm={pa:.2g}){star}"


# ── T1 label efficiency ─────────────────────────────────────────
for ds in ["dg", "ld"]:
    d = main_slice(df, ds)
    km = d[d.method == "kmeans_hungarian"].miou
    orc = d[d.method == "patch_oracle"].miou
    t = {}
    for meth, lab in [("linear", "Linear probe"), ("linear_balanced", "Class-balanced probe"),
                      ("cluster_label", "Cluster-then-label (K=50)")]:
        t[lab] = {b: ms(d[(d.method == meth) & (d.b == b)].miou) for b in BUD}
    tab = pd.DataFrame(t).loc[BUD]
    P1 = paired(d, "linear", "cluster_label"); P2 = paired(d, "linear_balanced", "linear")
    tab["Linear − cluster"] = pd.Series({k: fmt_pair(v) for k, v in P1.items()})
    tab["Balanced − linear"] = pd.Series({k: fmt_pair(v) for k, v in P2.items()})
    pool = int(d[d.b == "all"].pool.mean().round())
    tab.insert(0, "area (km²)", [f"{(BUD_X[b] or pool) * KM2[ds]:.2f}" for b in BUD])
    tab.index.name = "labelled images"
    npairs = next(iter(P1.values()))[4]
    md(f"Table: {TITLE[ds]} mIoU (%) vs. labelled images (mean ± SD over {npairs} folds×draws)", tab,
       f"Zero labels (k-means, K = #classes, Hungarian-matched on test — optimistic): {ms(km)}. "
       f"Patch-oracle ceiling (every 14×14 patch assigned its majority class): {ms(orc)}. "
       f"Paired differences: same labelled images; Holm correction across the 9 budgets; * p_Holm<0.05.")
    lm = d[d.method == "linear"].groupby("b").miou.mean().reindex(BUD)
    full = lm["all"]
    cross = next((b for b in BUD if lm[b] > km.mean()), None)
    reach = {q: next((b for b in BUD if lm[b] >= q * full), None) for q in (0.8, 0.9, 0.95)}
    lines.append(f"- {TITLE[ds]}: probe exceeds the 0-label baseline from n={cross} images; "
                 f"full-pool mIoU {full:.1f} ({100 * full / orc.mean():.0f}% of the patch ceiling); "
                 f"80/90/95% of full-pool mIoU reached at n={reach[0.8]}/{reach[0.9]}/{reach[0.95]} images.\n")

# ── T2 sparse points vs dense images ────────────────────────────
for ds in ["dg", "ld"]:
    d = main_slice(df, ds)
    pts = d[d.method == "linear_points"].groupby("n").miou
    t = pd.DataFrame({"mIoU": pts.apply(ms)})
    t.index.name = "random point labels"
    dens = d[d.method == "linear"].groupby("b").miou.mean()
    # dense budget with the closest mean mIoU
    t["≈ dense images with equal mIoU"] = [
        min(BUD, key=lambda b: abs(dens[b] - pts.get_group(n).mean())) for n in t.index]
    md(f"Table: {TITLE[ds]} sparse point annotation (linear probe, points spread over the whole pool)", t)
    # paired: 100 points vs 5 images; 1000 points vs 50 images
    for P, B in [(100, "5"), (300, "10"), (1000, "50")]:
        A = d[(d.method == "linear_points") & (d.n == P)].set_index(["exp", "seed"]).miou
        Bv = d[(d.method == "linear") & (d.b == B)].set_index(["exp", "seed"]).miou
        j = A.index.intersection(Bv.index)
        r = stats.ttest_rel(A[j], Bv[j])
        lines.append(f"- {TITLE[ds]}: {P} points {A[j].mean():.1f} vs {B} full images {Bv[j].mean():.1f} "
                     f"(diff {A[j].mean() - Bv[j].mean():+.1f}, paired p={r.pvalue:.2g}, n={len(j)}); "
                     f"a full image holds {1369} patch labels.\n")

# ── T3 sensitivity: lambda and K ────────────────────────────────
for ds in ["dg", "ld"]:
    d = main_slice(df, ds)
    t = {}
    for lam, meth in [("1e-4", "linear_lam0.0001"), ("1e-3 (main)", "linear"), ("1e-2", "linear_lam0.01"),
                      ("1e-1", "linear_lam0.1")]:
        t[f"λ={lam}"] = {b: ms(d[(d.method == meth) & (d.b == b)].miou) for b in ["5", "50", "all"]}
    md(f"Table: {TITLE[ds]} L2-strength sensitivity, linear probe mIoU (%)", pd.DataFrame(t).T)
    t = {}
    seeds0 = d[d.method == "cluster_label_K25"][["exp", "seed"]].drop_duplicates()
    sub = d.merge(seeds0, on=["exp", "seed"])
    for K, meth in [(25, "cluster_label_K25"), ("50 (main)", "cluster_label"), (100, "cluster_label_K100"),
                    (200, "cluster_label_K200")]:
        t[f"K={K}"] = {b: ms(sub[(sub.method == meth) & (sub.b == b)].miou) for b in ["5", "50", "all"]}
    t["linear probe"] = {b: ms(sub[(sub.method == "linear") & (sub.b == b)].miou) for b in ["5", "50", "all"]}
    md(f"Table: {TITLE[ds]} cluster-then-label K sensitivity (same draws), mIoU (%)", pd.DataFrame(t).T)

# ── T4 domain transfer ─────────────────────────────────────────
rows = {}
for exp, lab in [("LD-rural", "Rural"), ("LD-urban", "Urban"), ("LD-all", "Rural+Urban")]:
    for b in ["10", "100", "all"]:
        d = df[(df.exp == exp) & (df.method == "linear") & (df.b == b)]
        r = rows.setdefault(f"{lab} train, n={b}" + (f" ({int(d.n.iloc[0])})" if b == "all" else ""), {})
        for ev in ["rural", "urban"]:
            r[f"test {ev}"] = ms(d[d["eval"] == ev].miou)
md("Table: LoveDA rural/urban transfer, linear probe mIoU (%) (5 draws)", pd.DataFrame(rows).T)
for b in ["10", "100"]:
    for ev in ["rural", "urban"]:
        A = df[(df.exp == "LD-rural") & (df.method == "linear") & (df.b == b) & (df["eval"] == ev)].set_index("seed").miou
        B = df[(df.exp == "LD-urban") & (df.method == "linear") & (df.b == b) & (df["eval"] == ev)].set_index("seed").miou
        r = stats.ttest_rel(A, B)
        lines.append(f"- n={b}, test {ev}: rural-trained − urban-trained = {A.mean() - B.mean():+.1f} "
                     f"(paired over draws, p={r.pvalue:.2g}).\n")
# per-class cross-domain drops at n=100
t = {}
for ev, (same, other) in [("rural", ("LD-rural", "LD-urban")), ("urban", ("LD-urban", "LD-rural"))]:
    a = np.mean(df[(df.exp == same) & (df.method == "linear") & (df.b == "100") & (df["eval"] == ev)].iou.tolist(), 0)
    o = np.mean(df[(df.exp == other) & (df.method == "linear") & (df.b == "100") & (df["eval"] == ev)].iou.tolist(), 0)
    t[f"test {ev}: in-domain"] = a; t[f"test {ev}: cross-domain"] = o; t[f"test {ev}: Δ"] = o - a
md("Table: LoveDA per-class IoU (%), in- vs cross-domain training, n=100 images",
   pd.DataFrame(t, index=LD_CLASSES).round(1))

# ── T5 per-class ───────────────────────────────────────────────
for ds, cls in [("dg", DG_CLASSES), ("ld", LD_CLASSES)]:
    d = main_slice(df, ds)
    t = {}
    for meth, b, lab in [("kmeans_hungarian", "0", "0 labels"), ("linear", "5", "5 img"),
                         ("linear_points", "100", "100 pts"), ("linear", "50", "50 img"),
                         ("linear", "all", "all img"), ("patch_oracle", "-1", "patch ceiling")]:
        x = np.array(d[(d.method == meth) & (d.b == b)].iou.tolist())
        t[lab] = [f"{v:.1f}" for v in x.mean(0)]
    md(f"Table: {TITLE[ds]} per-class IoU (%)", pd.DataFrame(t, index=cls))

# ── T6 backbones ───────────────────────────────────────────────
BBS = [("dinov2_s", "DINOv2 ViT-S/14"), ("dinov2_b", "DINOv2 ViT-B/14"), ("dinov2_l", "DINOv2 ViT-L/14"),
       ("resnet50", "ResNet-50 (IN-1k sup.)")]
BBS = [x for x in BBS if x[0] in set(bb.backbone)]
for ds in ["dg", "ld"]:
    d = main_slice(bb, ds)
    t = {}
    for k, lab in BBS:
        e = d[d.backbone == k]
        t[lab] = {"0 labels": ms(e[e.method == "kmeans_hungarian"].miou),
                  **{f"linear n={b}": ms(e[(e.method == "linear") & (e.b == b)].miou) for b in ["5", "10", "50", "all"]},
                  "cluster K=50, all": ms(e[(e.method == "cluster_label") & (e.b == "all")].miou)}
    tab = pd.DataFrame(t).T
    md(f"Table: {TITLE[ds]} backbone comparison, identical protocol (256 patches/img), mIoU (%)", tab)
    # does the probe-vs-cluster conclusion hold for every backbone? (paired over folds/draws)
    for k, lab in BBS:
        e = d[d.backbone == k]
        P = paired(e, "linear", "cluster_label")
        win = [b for b, v in P.items() if v[0] > 0 and v[5] < 0.05]
        lines.append(f"- {TITLE[ds]} / {lab}: linear > cluster-then-label (Holm p<0.05) at budgets {win}.\n")

# ── T7 fine-tuning baseline ────────────────────────────────────
if ft is not None and len(ft):
    rows = []
    for (exp, seed, n), g in ft.groupby(["exp", "seed", "n"]):
        ev = "test" if exp.startswith("DG") else "all"
        f = g[g["eval"] == ev].miou.iloc[0]
        p = df[(df.exp == exp) & (df.seed == seed) & (df.n == n) & (df["eval"] == ev)]
        rows.append(dict(ds=TITLE["dg" if exp.startswith("DG") else "ld"], n=n, exp=exp, seed=seed, finetune=f,
                         linear=p[p.method == "linear"].miou.iloc[0],
                         balanced=p[p.method == "linear_balanced"].miou.iloc[0]))
    r = pd.DataFrame(rows)
    t = r.groupby(["ds", "n"]).agg(runs=("finetune", "size"), finetune=("finetune", ms),
                                    linear=("linear", ms), balanced=("balanced", ms))
    md(f"Table: end-to-end DeepLabV3-ResNet50 fine-tuning vs frozen DINOv2-B probe, same labelled images "
       f"({int(ft.iters.max())} iterations), mIoU (%)", t)
    for (ds, n), g in r.groupby(["ds", "n"]):
        if len(g) > 1:
            lines.append(f"- {ds}, n={n}: probe − fine-tune = {(g.linear - g.finetune).mean():+.1f} "
                         f"(paired p={stats.ttest_rel(g.linear, g.finetune).pvalue:.2g}, {len(g)} pairs).\n")

(OUT / "final_tables.md").write_text("".join(lines), encoding="utf-8")
print("".join(lines))


# ── Figures ────────────────────────────────────────────────────
def xpos(ds, d):
    pool = d[d.b == "all"].pool.mean() if (d.b == "all").any() else None
    return {b: (BUD_X[b] or pool) for b in BUD}


def curve(ax, d, meth, color, label, marker="o", ls="-", ds="dg", unit_x=None):
    g = d[d.method == meth].groupby("b").miou
    m, s = g.mean().reindex(BUD).dropna(), g.std(ddof=1).reindex(BUD).dropna()
    xp = xpos(ds, d)
    x = np.array([xp[b] for b in m.index], float)
    if unit_x is not None:
        x = x * unit_x
    ax.fill_between(x, m - s, m + s, color=color, alpha=0.13, lw=0)
    ax.plot(x, m.values, color=color, lw=2, marker=marker, ms=5, ls=ls, label=label,
            markeredgecolor="white", markeredgewidth=0.8)
    return x, m.values


def style(ax, title, xlabel):
    ax.set_xscale("log"); ax.set_xlabel(xlabel)
    ax.set_title(title, color=INK, fontsize=10, loc="left")
    ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)


# Fig 1: label efficiency
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2))
for ax, ds in zip(axes, ["dg", "ld"]):
    d = main_slice(df, ds)
    curve(ax, d, "linear", BLUE, "Linear probe", "o", ds=ds)
    curve(ax, d, "linear_balanced", AQUA, "Class-balanced probe", "s", "--", ds=ds)
    curve(ax, d, "cluster_label", ORANGE, "Cluster-then-label (K=50)", "^", ds=ds)
    ax.axhline(d[d.method == "kmeans_hungarian"].miou.mean(), color=MUTED, lw=1.3, ls=":",
               label="0 labels (k-means, matched)")
    style(ax, TITLE[ds], "Fully labelled training images (log)")
axes[0].set_ylabel("mIoU (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=7.5)
fig.tight_layout(rect=(0, 0.09, 1, 1))
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"fig1_label_efficiency.{ext}", dpi=300)
plt.close(fig)

# Fig 2: points vs dense, x = number of labelled locations (patch labels or point labels)
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2))
for ax, ds in zip(axes, ["dg", "ld"]):
    d = main_slice(df, ds)
    curve(ax, d, "linear", BLUE, "Dense: whole images (1369 patch labels each)", "o", ds=ds, unit_x=1369)
    g = d[d.method == "linear_points"].groupby("n").miou
    m, s = g.mean(), g.std(ddof=1)
    ax.fill_between(m.index, m - s, m + s, color=ORANGE, alpha=0.13, lw=0)
    ax.plot(m.index, m.values, color=ORANGE, lw=2, marker="D", ms=5, label="Sparse: random single-pixel points",
            markeredgecolor="white", markeredgewidth=0.8)
    style(ax, TITLE[ds], "Labelled locations (log)")
axes[0].set_ylabel("mIoU (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=2, frameon=False, fontsize=7.5)
fig.tight_layout(rect=(0, 0.09, 1, 1))
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"fig2_points_vs_dense.{ext}", dpi=300)
plt.close(fig)

# Fig 3: domain transfer
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2), sharey=True)
for ax, ev in zip(axes, ["rural", "urban"]):
    for exp, col, lab, mk in [("LD-rural", BLUE, "Trained on rural", "o"), ("LD-urban", ORANGE, "Trained on urban", "^"),
                              ("LD-all", AQUA, "Trained on both", "s")]:
        curve(ax, df[(df.exp == exp) & (df["eval"] == ev)], "linear", col, lab, mk, ds="ld")
    style(ax, f"Tested on {ev} LoveDA", "Fully labelled training images (log)")
axes[0].set_ylabel("mIoU (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=7.5)
fig.tight_layout(rect=(0, 0.09, 1, 1))
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"fig3_domain_transfer.{ext}", dpi=300)
plt.close(fig)

# Fig 4: backbones
cols = {"dinov2_s": AQUA, "dinov2_b": BLUE, "dinov2_l": YELLOW, "resnet50": ORANGE}
mks = {"dinov2_s": "s", "dinov2_b": "o", "dinov2_l": "D", "resnet50": "^"}
fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.2))
for ax, ds in zip(axes, ["dg", "ld"]):
    d = main_slice(bb, ds)
    for k, lab in BBS:     # endpoints of ViT-B/L nearly coincide: identity via legend + marker shape
        curve(ax, d[d.backbone == k], "linear", cols[k], lab, mks[k], ds=ds)
    style(ax, TITLE[ds], "Fully labelled training images (log)")
axes[0].set_ylabel("mIoU (%), linear probe")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=7.5)
fig.tight_layout(rect=(0, 0.09, 1, 1))
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"fig4_backbones.{ext}", dpi=300)
plt.close(fig)

# Fig 5: per-class IoU vs budget heatmap
fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.3), gridspec_kw={"wspace": 0.55})
for ax, (ds, cls) in zip(axes, [("dg", DG_CLASSES), ("ld", LD_CLASSES)]):
    d = main_slice(df, ds)
    d = d[d.method == "linear"]
    M = np.array([np.mean(d[d.b == b].iou.tolist(), axis=0) for b in BUD]).T
    im = ax.imshow(M, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(BUD))); ax.set_xticklabels(BUD, fontsize=7)
    ax.set_yticks(range(len(cls))); ax.set_yticklabels(cls, fontsize=8)
    ax.set_xlabel("Fully labelled training images")
    ax.set_title(TITLE[ds], color=INK, fontsize=10, loc="left")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=6,
                    color="white" if M[i, j] > 55 else INK)
    for s in ax.spines.values():
        s.set_visible(False)
cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02); cb.set_label("IoU (%)")
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"fig5_per_class.{ext}", dpi=300, bbox_inches="tight")
plt.close(fig)
print("figures ->", FIG)
