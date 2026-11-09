"""Step 3: tables, statistics and figures from outputs/results.jsonl."""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import OUT, DG_CLASSES, LD_CLASSES

FIG = OUT / "figures"; FIG.mkdir(exist_ok=True)
df = pd.DataFrame([json.loads(l) for l in open(OUT / "results.jsonl")])
df["n"] = df["n"].astype(int)

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False})
NAMES = {"linear": "Linear probe", "cluster_label": "Cluster-then-label (K=50)",
         "kmeans_hungarian": "k-means + Hungarian (0 labels)"}
lines = []


def md(title, tab):
    lines.append(f"\n### {title}\n\n" + tab.to_markdown() + "\n")


def agg(sub):
    g = sub.groupby("n")["miou"]
    return g.mean(), g.std(ddof=1)


def fmt(m, s):
    return f"{m:.1f} ± {s:.1f}"


# ── Table 1: label efficiency ───────────────────────────────────
main = [("DeepGlobe", "DG", "test"), ("LoveDA", "LD-all", "all")]
for title, exp, ev in main:
    d = df[(df.exp == exp) & (df["eval"] == ev)]
    km = d[d.method == "kmeans_hungarian"].miou
    t = {}
    for meth in ["linear", "cluster_label"]:
        m, s = agg(d[d.method == meth])
        t[NAMES[meth]] = {n: fmt(m[n], s[n]) for n in m.index}
    tab = pd.DataFrame(t)
    tab.index.name = "labelled images"
    # paired t-test linear vs cluster_label, same seeds = same labelled images
    p = {}
    for n in tab.index:
        a = d[(d.method == "linear") & (d.n == n)].sort_values("seed").miou.values
        b = d[(d.method == "cluster_label") & (d.n == n)].sort_values("seed").miou.values
        r = stats.ttest_rel(a, b)
        p[n] = f"{a.mean()-b.mean():+.1f} (p={r.pvalue:.3g})"
    tab["Linear − cluster (paired t)"] = pd.Series(p)
    md(f"Table: {title} mIoU (%) vs labelled images; 0-label k-means + Hungarian = "
       f"{fmt(km.mean(), km.std(ddof=1))}", tab)
    # crossover and fraction of full-label performance
    lm, _ = agg(d[d.method == "linear"])
    full = lm.iloc[-1]
    cross = next((n for n in lm.index if lm[n] > km.mean()), None)
    reach = {q: next((n for n in lm.index if lm[n] >= q * full), None) for q in (0.8, 0.9, 0.95)}
    lines.append(f"- {title}: linear probe beats 0-label k-means from n={cross}; "
                 f"full-label mIoU {full:.1f}; reaches 80/90/95% of it at n="
                 f"{reach[0.8]}/{reach[0.9]}/{reach[0.95]} images "
                 f"(pool {int(d.pool.iloc[0])}).\n")

# ── Table 2: urban/rural transfer ───────────────────────────────
rows = {}
for exp, lab in [("LD-rural", "Rural"), ("LD-urban", "Urban"), ("LD-all", "Rural+Urban")]:
    for n in [10, 100]:
        for ev in ["rural", "urban"]:
            d = df[(df.exp == exp) & (df.method == "linear") & (df.n == n) & (df["eval"] == ev)]
            rows.setdefault(f"{lab} train, n={n}", {})[f"test {ev}"] = fmt(d.miou.mean(), d.miou.std(ddof=1))
    d = df[(df.exp == exp) & (df.method == "linear")]
    nmax = d.n.max()
    for ev in ["rural", "urban"]:
        x = d[(d.n == nmax) & (d["eval"] == ev)].miou
        rows.setdefault(f"{lab} train, all ({nmax})", {})[f"test {ev}"] = fmt(x.mean(), x.std(ddof=1))
md("Table: LoveDA domain transfer, linear probe mIoU (%)", pd.DataFrame(rows).T)

# ── Table 3: per-class IoU ──────────────────────────────────────
for title, exp, ev, cls in [("DeepGlobe", "DG", "test", DG_CLASSES), ("LoveDA", "LD-all", "all", LD_CLASSES)]:
    d = df[(df.exp == exp) & (df["eval"] == ev)]
    t = {}
    for meth, n in [("kmeans_hungarian", 0), ("linear", 5), ("linear", 50), ("linear", int(d.n.max()))]:
        x = np.array(d[(d.method == meth) & (d.n == n)].iou.tolist())
        t[f"{'k-means' if n == 0 else 'linear'} n={n}"] = [fmt(a, b) for a, b in zip(x.mean(0), x.std(0, ddof=1))]
    md(f"Table: {title} per-class IoU (%)", pd.DataFrame(t, index=cls))

(OUT / "tables.md").write_text("".join(lines), encoding="utf-8")


# ── Figure 1: label-efficiency curves ───────────────────────────
def curve(ax, d, meth, color, label, label_y_off=0):
    m, s = agg(d[d.method == meth])
    x = m.index.values
    ax.fill_between(x, m - s, m + s, color=color, alpha=0.15, lw=0)
    ax.plot(x, m, color=color, lw=2, marker="o", ms=4, label=label)


fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=False)
for ax, (title, exp, ev) in zip(axes, main):
    d = df[(df.exp == exp) & (df["eval"] == ev)]
    curve(ax, d, "linear", BLUE, NAMES["linear"])
    curve(ax, d, "cluster_label", ORANGE, NAMES["cluster_label"])
    km = d[d.method == "kmeans_hungarian"].miou.mean()
    ax.axhline(km, color=AQUA, lw=2, ls="--", label=NAMES["kmeans_hungarian"])
    ax.set_xscale("log")
    ax.set_xlabel("Labelled training images (log scale)")
    ax.set_title(title, color=INK, fontsize=10, loc="left")
    ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
axes[0].set_ylabel("mIoU (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=8)
fig.tight_layout(rect=(0, 0.1, 1, 1))
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"fig_label_efficiency.{ext}", dpi=300)
plt.close(fig)

# ── Figure 2: domain transfer curves ────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
for ax, ev in zip(axes, ["rural", "urban"]):
    for exp, col, lab in [("LD-rural", BLUE, "Trained on rural"), ("LD-urban", ORANGE, "Trained on urban"),
                          ("LD-all", AQUA, "Trained on both")]:
        curve(ax, df[(df.exp == exp) & (df["eval"] == ev)], "linear", col, lab)
    ax.set_xscale("log"); ax.set_xlabel("Labelled training images (log scale)")
    ax.set_title(f"Tested on {ev} LoveDA", color=INK, fontsize=10, loc="left")
    ax.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True)
axes[0].set_ylabel("mIoU (%)")
h, l = axes[0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=8)
fig.tight_layout(rect=(0, 0.1, 1, 1))
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"fig_domain_transfer.{ext}", dpi=300)
plt.close(fig)

# ── Figure 3: per-class IoU heatmap vs budget (linear probe) ────
fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.2), gridspec_kw={"wspace": 0.55})
for ax, (title, exp, ev, cls) in zip(axes, [("DeepGlobe", "DG", "test", DG_CLASSES),
                                             ("LoveDA", "LD-all", "all", LD_CLASSES)]):
    d = df[(df.exp == exp) & (df["eval"] == ev) & (df.method == "linear")]
    ns = sorted(d.n.unique())
    M = np.array([np.mean(d[d.n == n].iou.tolist(), axis=0) for n in ns]).T
    im = ax.imshow(M, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(ns))); ax.set_xticklabels(ns, fontsize=7)
    ax.set_yticks(range(len(cls))); ax.set_yticklabels(cls, fontsize=8)
    ax.set_xlabel("Labelled training images")
    ax.set_title(title, color=INK, fontsize=10, loc="left")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=6,
                    color="white" if M[i, j] > 55 else INK)
    for s in ax.spines.values():
        s.set_visible(False)
cb = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02); cb.set_label("IoU (%)")
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"fig_per_class.{ext}", dpi=300, bbox_inches="tight")
plt.close(fig)
import sys
sys.stdout.reconfigure(encoding="utf-8")
print((OUT / "tables.md").read_text(encoding="utf-8"))
