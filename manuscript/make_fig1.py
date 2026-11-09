"""Fig. 1: study-design schematic with a real DeepGlobe tile and its reference mask."""
import sys
from pathlib import Path
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from common import list_items   # noqa: E402

INK, MUTED, BLUE, ORANGE, AQUA = "#0b0b0b", "#52514e", "#2a78d6", "#eb6834", "#1baf7a"
FILL = "#f3f2ef"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})

TILE = 239   # chosen for class diversity (urban, agriculture, rangeland, forest)
img_p, mask_p, _ = list_items("dg")[TILE]
img = Image.open(img_p).convert("RGB").resize((518, 518), Image.BILINEAR)
mask = Image.open(mask_p).convert("RGB").resize((518, 518), Image.NEAREST)

W, Hh = 7.4, 3.0
fig = plt.figure(figsize=(W, Hh))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 40.5); ax.axis("off")


def box(x, y, w, h, title, body="", color=MUTED, fs=6.9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2",
                                fc=FILL, ec=color, lw=1.2))
    ax.text(x + w / 2, y + h - 1.3, title, ha="center", va="top", fontsize=7.8, weight="bold", color=INK)
    if body:
        ax.text(x + w / 2, y + h - 4.4, body, ha="center", va="top", fontsize=fs, color=MUTED,
                linespacing=1.35)


def arrow(x0, y0, x1, y1):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=9,
                                 lw=1.1, color=MUTED))


def thumb(rect, im, grid=False):
    a = fig.add_axes(rect); a.imshow(im); a.set_xticks([]); a.set_yticks([])
    for s in a.spines.values():
        s.set_color(MUTED); s.set_linewidth(0.6)
    if grid:
        for k in range(0, 519, 14 * 6):
            a.axhline(k, color="white", lw=0.35, alpha=0.7); a.axvline(k, color="white", lw=0.35, alpha=0.7)


# thumbnails (axes fractions); y in data units → fraction = y/40.5
thumb([0.012, 0.555, 0.14, 0.14 * W / Hh], img, grid=True)
thumb([0.012, 0.115, 0.14, 0.14 * W / Hh], mask)
ax.text(8.2, 37.6, "VHR image (518 × 518)", ha="center", fontsize=7, color=INK)
ax.text(8.2, 19.3, "Reference mask", ha="center", fontsize=7, color=INK)
leg = [Patch(fc=c, ec=MUTED, lw=0.3, label=l) for c, l in
       [("#00ffff", "urban"), ("#ffff00", "agric."), ("#ff00ff", "range"), ("#00ff00", "forest")]]
ax.legend(handles=leg, loc="lower left", bbox_to_anchor=(0.0, -0.01), ncol=4, fontsize=5.2, frameon=False,
          handlelength=0.9, handletextpad=0.3, columnspacing=0.5)

arrow(17.0, 29.5, 19.6, 29.5)
box(19.9, 22.5, 15.0, 14.5, "Frozen backbone", "DINOv2 ViT-S/B/L\n(+ ResNet-50 check)\nno weights updated", BLUE)
arrow(35.3, 29.5, 38.4, 29.5)
box(38.7, 22.5, 14.8, 14.5, "Patch features", "37 × 37 grid\n768-d (ViT-B)\nextracted once", BLUE)

box(19.9, 3.0, 33.6, 14.5, "Annotation regime",
    "Dense: n fully annotated images\n(n = 1 … all)\nSparse: P random single-pixel points\n(P = 100 … 30,000)",
    ORANGE)
arrow(17.0, 11.6, 19.6, 11.6)

arrow(53.9, 29.5, 57.6, 27.5)
arrow(53.9, 10.5, 57.6, 19.0)
box(57.9, 13.0, 19.6, 24.0, "Classifiers",
    "Linear probe\nClass-balanced probe\nCluster-then-label (K = 50)\nZero-label k-means\n\nBaseline:\nDeepLabV3 fine-tuning", AQUA)
arrow(77.9, 25.0, 80.4, 25.0)
box(80.7, 13.0, 18.3, 24.0, "Exact scoring",
    "patch label → its 196 px\npixel-level confusion\nper-class IoU, mIoU\npatch-oracle ceiling\npaired tests (Holm)", AQUA)
box(57.9, 1.0, 41.1, 9.0, "Protocol",
    "DeepGlobe 5-fold CV × 3 draws · LoveDA train→val × 5 draws\nurban↔rural transfer · λ, K sensitivity · 4 backbones",
    MUTED, fs=6.4)

out = ROOT / "outputs" / "figures_final"
for ext in ("png", "pdf"):
    fig.savefig(out / f"fig1.{ext}", dpi=300)
print("saved", out / "fig1.png")
