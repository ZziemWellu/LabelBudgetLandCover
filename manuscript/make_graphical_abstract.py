"""Graphical abstract: designed at the final size (13 cm wide) so text stays >= 7 pt.
Data: DeepGlobe linear probe, dense images vs random points (outputs/final.jsonl).
Writes manuscript/Graphical_abstract.{pdf,tiff,png}.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
INK, MUTED, GRID, BLUE, ORANGE, FILL = "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6", "#eb6834", "#f3f2ef"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.edgecolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": INK,
                     "axes.spines.top": False, "axes.spines.right": False})

d = pd.DataFrame([json.loads(l) for l in open(ROOT / "outputs" / "final.jsonl")])
d = d[d.exp.str.startswith("DG") & (d["eval"] == "test")]
PER_IMG = 1366          # labelled patches per DeepGlobe image after the purity rule (robustness.md)
dense = d[(d.method == "linear") & (d.n < d.pool)].groupby("n").miou.agg(["mean", "std"])
pts = d[d.method == "linear_points"].groupby("n").miou.agg(["mean", "std"])

W, H = 13 / 2.54, 5.4 / 2.54
fig = plt.figure(figsize=(W, H))
bg = fig.add_axes([0, 0, 1, 1]); bg.set_xlim(0, 100); bg.set_ylim(0, 41.5); bg.axis("off")


def box(x, y, w, h, title, body, color):
    bg.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.5",
                                fc=FILL, ec=color, lw=1.0))
    bg.text(x + w / 2, y + h - 1.6, title, ha="center", va="top", fontsize=8, weight="bold", color=INK)
    bg.text(x + w / 2, y + h - 7.2, body, ha="center", va="top", fontsize=7, color=MUTED, linespacing=1.4)


box(1.5, 4, 25, 33.5, "Frozen DINOv2",
    "VHR image\n↓\npatch features\n(no fine-tuning)\n↓\nlinear probe\n\nDeepGlobe · LoveDA", BLUE)

ax = fig.add_axes([0.375, 0.24, 0.3, 0.62])
x = np.array(dense.index) * PER_IMG
ax.plot(x, dense["mean"], "-o", color=BLUE, lw=1.6, ms=3, label="whole images")
ax.plot(pts.index, pts["mean"], "-o", color=ORANGE, lw=1.6, ms=3, label="random points")
ax.set_xscale("log"); ax.set_ylim(10, 82); ax.set_yticks(range(10, 71, 10))
ax.set_xlabel("labelled locations"); ax.set_ylabel("mIoU (%)")
ax.grid(True, color=GRID, lw=0.5); ax.set_axisbelow(True)
ax.tick_params(labelsize=6.5)
ax.legend(frameon=False, fontsize=6.5, loc="upper left", handlelength=1.2)
ax.set_title("DeepGlobe: same labels,\nmore accuracy when spread", fontsize=7.5, color=INK, pad=3)

box(72.5, 4, 26, 33.5, "Take-aways",
    "100 images ≈ 90%\nof full-pool accuracy\n\n100 points beat\n5 images by 11 mIoU\n\n"
    "no significant gap to\nfine-tuned DeepLabV3", ORANGE)

out = ROOT / "manuscript"
fig.savefig(out / "Graphical_abstract.pdf")
fig.savefig(out / "Graphical_abstract.png", dpi=600)
fig.savefig(out / "Graphical_abstract.tiff", dpi=600, pil_kwargs={"compression": "tiff_lzw"})
print("saved", out / "Graphical_abstract.pdf")
