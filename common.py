"""Shared paths, dataset listing, label decoding and feature extraction.

Study: label-efficiency and urban-rural transfer of frozen DINOv2 patch
features for land-cover mapping (DeepGlobe, LoveDA).
"""
from pathlib import Path
import numpy as np

# ── Paths ───────────────────────────────────────────────────────
DATA_ROOT = Path(r"C:\Users\egest\Desktop\Ph.D\Gifty\Dataset")
DG_TRAIN = DATA_ROOT / "DeepGlobe Land Cover Classification Dataset" / "train"
LD_ROOT = DATA_ROOT / "LoveDA Dataset"
# Feature caches produced earlier by the same DINOv2 preprocessing (read-only).
OLD_CACHE = Path(r"C:\Users\egest\Desktop\Ph.D\Gifty\Code\outputs")
HUB_DIR = Path.home() / ".cache" / "torch" / "hub" / "facebookresearch_dinov2_main"

OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

FEATS = {
    "dg": OLD_CACHE / "deepglobe_features.npy",      # 803 DeepGlobe train/ images
    "ld_train": OLD_CACHE / "loveda_features.npy",   # 2522 LoveDA Train images
    "ld_val": OUT / "loveda_val_features.npy",       # 1669 LoveDA Val images
}

# ── Geometry ────────────────────────────────────────────────────
IMG = 518            # 37 x 14
PATCH = 14
GRID = IMG // PATCH  # 37
NP = GRID * GRID     # 1369 patches per image
DIM = 768
IGNORE = 255

# ── Classes ─────────────────────────────────────────────────────
# DeepGlobe: 'unknown' (black) is not a land-cover class and is ignored,
# following the DeepGlobe challenge protocol (6 evaluated classes).
DG_CLASSES = ["Urban", "Agriculture", "Rangeland", "Forest", "Water", "Barren"]
DG_RGB = {(0, 255, 255): 0, (255, 255, 0): 1, (255, 0, 255): 2,
          (0, 255, 0): 3, (0, 0, 255): 4, (255, 255, 255): 5}
# LoveDA: 0 = no-data (ignored), 1..7 -> 0..6
LD_CLASSES = ["Background", "Building", "Road", "Water", "Barren", "Forest", "Agriculture"]
N_CLASSES = {"dg": len(DG_CLASSES), "ld_train": len(LD_CLASSES), "ld_val": len(LD_CLASSES)}

_DG_LUT = np.full(8, IGNORE, dtype=np.uint8)
for (r, g, b), k in DG_RGB.items():
    _DG_LUT[(r >= 128) * 4 + (g >= 128) * 2 + (b >= 128)] = k
_LD_LUT = np.array([IGNORE, 0, 1, 2, 3, 4, 5, 6] + [IGNORE] * 248, dtype=np.uint8)


def list_items(src: str):
    """Return [(image_path, mask_path, domain)] in the exact order used by the feature caches."""
    if src == "dg":
        items = []
        for ip in sorted(DG_TRAIN.glob("*_sat.jpg")):
            mp = ip.parent / ip.name.replace("_sat.jpg", "_mask.png")
            if mp.exists():
                items.append((ip, mp, "DeepGlobe"))
        return items
    split = {"ld_train": "Train", "ld_val": "Val"}[src]
    base = LD_ROOT / split / split
    items = []
    for dom in ["Rural", "Urban"]:
        for ip in sorted((base / dom / "images_png").glob("*.png")):
            mp = base / dom / "masks_png" / ip.name
            if mp.exists():
                items.append((ip, mp, dom))
    return items


def decode_mask(src: str, mask_path) -> np.ndarray:
    """Mask -> (IMG, IMG) uint8 class map, IGNORE where not evaluated."""
    from PIL import Image
    m = Image.open(mask_path)
    if src == "dg":
        a = np.asarray(m.convert("RGB").resize((IMG, IMG), Image.NEAREST))
        code = (a[..., 0] >= 128) * 4 + (a[..., 1] >= 128) * 2 + (a[..., 2] >= 128)
        return _DG_LUT[code]
    a = np.asarray(m.resize((IMG, IMG), Image.NEAREST))
    return _LD_LUT[a]


def patch_hist(lbl: np.ndarray, C: int) -> np.ndarray:
    """(IMG, IMG) labels -> (NP, C) uint16 pixel counts per 14x14 patch."""
    p = lbl.reshape(GRID, PATCH, GRID, PATCH).transpose(0, 2, 1, 3).reshape(NP, PATCH * PATCH)
    return np.stack([(p == c).sum(1) for c in range(C)], axis=1).astype(np.uint16)


def load_feats(src: str) -> np.ndarray:
    """Memory-mapped (N*NP, DIM) float16 features."""
    return np.load(str(FEATS[src]), mmap_mode="r")


def load_dinov2(device):
    import torch
    m = torch.hub.load(str(HUB_DIR), "dinov2_vitb14_reg", source="local", pretrained=True)
    return m.eval().to(device)


def image_transform():
    from torchvision import transforms
    return transforms.Compose([
        transforms.Resize((IMG, IMG), interpolation=transforms.InterpolationMode.BILINEAR),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])


def extract(model, paths, device, batch=8):
    """Yield (B, NP, DIM) float16 L2-normalised patch tokens."""
    import torch
    import torch.nn.functional as F
    from PIL import Image
    tf = image_transform()
    with torch.no_grad():
        for s in range(0, len(paths), batch):
            x = torch.stack([tf(Image.open(p).convert("RGB")) for p in paths[s:s + batch]]).to(device)
            tok = model.forward_features(x)["x_norm_patchtokens"]
            assert tok.shape[1] == NP
            yield F.normalize(tok, dim=-1).half().cpu().numpy()
