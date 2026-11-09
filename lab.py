"""Shared fitting, sampling and scoring routines for the final experiments."""
import json, time
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.cluster import MiniBatchKMeans
from scipy.optimize import linear_sum_assignment
from common import OUT, NP, IGNORE, PATCH

dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
CAP = 500_000      # max labelled patches in one linear fit
KM_CAP = 300_000   # patches used to fit k-means
R_RED = 400        # patches per image kept in the reduced cache
PURITY = 0.5       # a dense training patch is labelled if one class covers >= 50% of it


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def patch_labels(H):
    y = H.argmax(-1).astype(np.uint8)
    y[H.max(-1) < PURITY * PATCH * PATCH] = IGNORE
    return y


def red_index(n_img):
    """Fixed random patch order per image (first R_RED kept). Same for every backbone."""
    f = OUT / f"red_idx_{n_img}.npy"
    if f.exists():
        return np.load(f)
    rng = np.random.default_rng(12345)
    idx = np.stack([rng.permutation(NP)[:R_RED] for _ in range(n_img)]).astype(np.int16)
    np.save(f, idx)
    return idx


def build_reduced(Fm, n_img, keep, path):
    """(n_img, keep, D) float16 from a full (n_img*NP, D) memmap, using red_index."""
    if path.exists():
        return np.load(path, mmap_mode="r")
    idx = red_index(n_img)[:, :keep]
    X = np.lib.format.open_memmap(str(path.with_suffix(".partial.npy")), mode="w+",
                                  dtype=np.float16, shape=(n_img, keep, Fm.shape[1]))
    for i in range(n_img):
        X[i] = np.asarray(Fm[i * NP:(i + 1) * NP])[idx[i]]
    X.flush(); del X
    path.with_suffix(".partial.npy").replace(path)
    return np.load(path, mmap_mode="r")


def dense_set(Fm, red, Y, imgs, seed, keep):
    """Labelled patches of fully-annotated images.
    Fm: full memmap or None; red: (N, keep, D) reduced features; keep: patches/img in red."""
    imgs = np.sort(np.asarray(imgs))
    ridx = red_index(len(Y))
    if Fm is not None and len(imgs) * NP <= CAP:
        X = np.concatenate([np.asarray(Fm[i * NP:(i + 1) * NP]) for i in imgs])
        y = Y[imgs].reshape(-1)
    else:
        k = min(keep, max(1, CAP // len(imgs)))
        rng = np.random.default_rng(20_000 + seed)
        sel = np.stack([rng.choice(keep, k, replace=False) for _ in imgs]) if k < keep \
            else np.tile(np.arange(keep), (len(imgs), 1))
        X = np.concatenate([np.asarray(red[i])[s] for i, s in zip(imgs, sel)])
        y = np.concatenate([Y[i][ridx[i, s].astype(np.int64)] for i, s in zip(imgs, sel)])
    keep_m = y != IGNORE
    return X[keep_m], y[keep_m]


def point_set(Fm, H, pool, n_pts, seed):
    """n_pts single-pixel labels at random locations of random pool images.
    A pixel's class is drawn from its patch's GT histogram, i.e. a uniformly random pixel."""
    rng = np.random.default_rng(30_000 + seed)
    img = rng.choice(pool, n_pts)
    pat = rng.integers(0, NP, n_pts)
    h = H[img, pat].astype(np.float64)
    ok = h.sum(1) > 0
    img, pat, h = img[ok], pat[ok], h[ok]
    cum = h.cumsum(1)
    u = rng.random(len(h)) * cum[:, -1]
    y = (cum < u[:, None]).sum(1).astype(np.uint8)
    rows = img.astype(np.int64) * NP + pat
    o = np.argsort(rows)
    X = np.asarray(Fm[rows[o]])
    return X, y[o]


def fit_linear(X, y, C, lam=1e-3, balanced=False):
    X = torch.from_numpy(np.ascontiguousarray(X)).to(dev).float()
    y = torch.from_numpy(y.astype(np.int64)).to(dev)
    w = None
    if balanced:
        cnt = torch.bincount(y, minlength=C).float()
        w = torch.where(cnt > 0, cnt.sum() / (C * cnt.clamp(min=1)), torch.ones_like(cnt))
    mu, sd = X.mean(0), X.std(0) + 1e-6
    D = X.shape[1]
    W = torch.zeros(D, C, device=dev, requires_grad=True)
    b = torch.zeros(C, device=dev, requires_grad=True)
    opt = torch.optim.LBFGS([W, b], lr=1, max_iter=200, history_size=20,
                            tolerance_grad=1e-6, tolerance_change=1e-9,
                            line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        We = W / sd[:, None]
        loss = F.cross_entropy(X @ We + (b - mu @ We), y, weight=w) + lam * (W ** 2).sum()
        loss.backward()
        return loss

    opt.step(closure)
    with torch.no_grad():
        We = W / sd[:, None]
        be = b - mu @ We
    del X, y
    torch.cuda.empty_cache()
    return We.cpu(), be.cpu()


def kmeans(X, K, seed):
    km = MiniBatchKMeans(n_clusters=K, batch_size=4096, n_init=3, max_iter=100, random_state=seed)
    km.fit(np.asarray(X, dtype=np.float32))
    return torch.from_numpy(km.cluster_centers_.astype(np.float32))


def nearest(X, cents):
    c = cents.to(dev)
    c2 = 0.5 * (c ** 2).sum(1)
    out = []
    for s in range(0, len(X), 200_000):
        x = torch.from_numpy(np.asarray(X[s:s + 200_000])).to(dev).float()
        out.append((x @ c.T - c2).argmax(1).cpu())
    return torch.cat(out).numpy()


def label_clusters(cents, X, y, C):
    a = nearest(X, cents)
    K = len(cents)
    counts = np.zeros((K, C))
    np.add.at(counts, (a, y), 1)
    has = counts.sum(1) > 0
    mapping = counts.argmax(1)
    if not has.all():
        d = torch.cdist(cents, cents).numpy()
        d[:, ~has] = np.inf
        mapping[~has] = mapping[d[~has].argmin(1)]
    return torch.from_numpy(mapping)


class Scorer:
    """Accumulates exact pixel-level confusion matrices (rows = prediction, cols = GT)
    for many models at once from patch features and per-patch GT histograms."""

    def __init__(self, models, cent_sets, C):
        self.C = C
        self.lin = [(i, m) for i, m in models if m["kind"] == "lin"]
        self.cen = [(i, m) for i, m in models if m["kind"] == "cent"]
        self.orc = [(i, m) for i, m in models if m["kind"] == "oracle"]
        self.Wall = torch.cat([m["W"] for _, m in self.lin], 1).to(dev) if self.lin else None
        self.ball = torch.cat([m["b"] for _, m in self.lin]).to(dev) if self.lin else None
        self.keys = sorted({m["key"] for _, m in self.cen})
        self.cents = {k: cent_sets[k].to(dev) for k in self.keys}
        self.maps = {i: (m["mapping"].to(dev) if m["mapping"] is not None else None)
                     for i, m in self.cen}
        self.conf = {}

    def add(self, X, h, sname, model_filter=None):
        """X: (P, D) features (torch, on dev); h: (P, C) float64 GT pixel counts."""
        C = self.C
        ok = (lambda m: True) if model_filter is None else model_filter

        def acc(i, pred):
            k = (i, sname)
            if k not in self.conf:
                self.conf[k] = torch.zeros(C, C, dtype=torch.float64, device=dev)
            self.conf[k].index_add_(0, pred, h)

        if self.lin:
            P = (X @ self.Wall + self.ball).view(len(X), len(self.lin), C).argmax(-1)
            for j, (i, m) in enumerate(self.lin):
                if ok(m):
                    acc(i, P[:, j])
        if self.cen:
            assign = {}
            for k in self.keys:
                c = self.cents[k]
                assign[k] = (X @ c.T - 0.5 * (c ** 2).sum(1)).argmax(1)
            for i, m in self.cen:
                if ok(m):
                    a = assign[m["key"]]
                    acc(i, a if self.maps[i] is None else self.maps[i][a])
        for i, m in self.orc:
            if ok(m):
                acc(i, h.argmax(1))


def scores(M):
    tp = np.diag(M)
    iou = tp / np.maximum(M.sum(0) + M.sum(1) - tp, 1)
    return 100 * iou, 100 * tp.sum() / M.sum()


def finalize(models, conf, set_names, extra=None, out_prefix="results"):
    """Hungarian-match unsupervised models, compute metrics, write jsonl + confusions."""
    rows, cm = [], {}
    for i, m in models:
        Ms = {s: conf[(i, s)].cpu().numpy() for s in set_names(m) if (i, s) in conf}
        if not Ms:
            continue
        if len(Ms) > 1:
            Ms["all"] = sum(Ms.values())
        perm = None
        if m["method"] == "kmeans_hungarian":
            ref = Ms.get("all", next(iter(Ms.values())))
            r, c = linear_sum_assignment(-ref)
            perm = np.empty(len(r), dtype=int)
            perm[c] = r
        for s, M in Ms.items():
            if perm is not None:
                M = M[perm]
            iou, acc = scores(M)
            row = dict(exp=m["exp"], method=m["method"], n=m["n"], seed=m["seed"], eval=s,
                       miou=float(iou.mean()), acc=float(acc), iou=[float(v) for v in iou],
                       pool=int(m["pool"]), unit=m.get("unit", "images"))
            if extra:
                row.update(extra)
            rows.append(row)
            cm[f"{m['exp']}|{m['method']}|{m['n']}|{m['seed']}|{s}"] = M
    with open(OUT / f"{out_prefix}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    np.savez_compressed(OUT / f"{out_prefix}_confusions.npz", **cm)
    return rows
