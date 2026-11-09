"""Step 2: label-budget experiments on frozen DINOv2 patch features.

Methods (all operate on frozen, L2-normalised DINOv2 ViT-B/14-reg patch tokens):
  kmeans_hungarian : K = #classes k-means, cluster->class by Hungarian matching on the
                     evaluation set (standard unsupervised protocol; 0 labels).
  cluster_label    : K = 50 k-means fitted on the unlabelled pool; each cluster named by
                     majority vote of the n labelled images' patches.
  linear           : multinomial logistic regression (L-BFGS, fixed L2 = 1e-3) on the
                     n labelled images' patches.
No hyperparameter is selected on evaluation data.

Scoring: every patch prediction is applied to all pixels of its 14x14 patch and
compared with the per-pixel ground truth (exact pixel-level confusion at 518x518).
"""
import json, time
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.cluster import MiniBatchKMeans
from scipy.optimize import linear_sum_assignment
from common import OUT, NP, DIM, IGNORE, PATCH, N_CLASSES, load_feats

dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
BUDGETS = [1, 2, 5, 10, 25, 50, 100, 250, "all"]
SEEDS = [0, 1, 2, 3, 4]
CAP = 500_000         # max labelled patches per linear fit
KM_CAP = 300_000      # patches used to fit k-means
R = 256               # patches kept per image in the reduced cache (large budgets)
K_OVER = 50
LAMBDA = 1e-3
PURITY = 0.5          # training patch label = majority class if it covers >= 50% of pixels


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def patch_labels(H):
    y = H.argmax(-1).astype(np.uint8)
    y[H.max(-1) < PURITY * PATCH * PATCH] = IGNORE
    return y


def reduced(src):
    f = OUT / f"reduced_{src}.npz"
    if f.exists():
        z = np.load(f)
        return z["X"], z["idx"]
    Fm = load_feats(src)
    N = Fm.shape[0] // NP
    rng = np.random.default_rng(12345)
    idx = np.stack([np.sort(rng.choice(NP, R, replace=False)) for _ in range(N)])
    X = np.empty((N, R, DIM), dtype=np.float16)
    for i in range(N):
        X[i] = np.asarray(Fm[i * NP:(i + 1) * NP])[idx[i]]
    np.savez(f, X=X, idx=idx)
    return X, idx


def train_set(Fm, Y, red, imgs, seed):
    imgs = np.sort(imgs)
    if len(imgs) * NP <= CAP:
        X = np.concatenate([np.asarray(Fm[i * NP:(i + 1) * NP]) for i in imgs])
        y = Y[imgs].reshape(-1)
    else:
        Xr, ridx = red
        X = Xr[imgs].reshape(-1, DIM)
        y = np.take_along_axis(Y[imgs], ridx[imgs], 1).reshape(-1)
        if len(X) > CAP:
            sel = np.random.default_rng(10_000 + seed).choice(len(X), CAP, replace=False)
            X, y = X[sel], y[sel]
    keep = y != IGNORE
    return X[keep], y[keep]


def fit_linear(X, y, C):
    X = torch.from_numpy(X).to(dev).float()
    y = torch.from_numpy(y.astype(np.int64)).to(dev)
    mu, sd = X.mean(0), X.std(0) + 1e-6
    W = torch.zeros(DIM, C, device=dev, requires_grad=True)
    b = torch.zeros(C, device=dev, requires_grad=True)
    opt = torch.optim.LBFGS([W, b], lr=1, max_iter=200, history_size=20,
                            tolerance_grad=1e-6, tolerance_change=1e-9,
                            line_search_fn="strong_wolfe")

    def closure():
        opt.zero_grad()
        We = W / sd[:, None]
        loss = F.cross_entropy(X @ We + (b - mu @ We), y) + LAMBDA * (W ** 2).sum()
        loss.backward()
        return loss

    opt.step(closure)
    with torch.no_grad():
        We = W / sd[:, None]
        be = b - mu @ We
    del X, y
    return We.cpu(), be.cpu()


def kmeans(X, K, seed):
    km = MiniBatchKMeans(n_clusters=K, batch_size=4096, n_init=3, max_iter=100,
                         random_state=seed)
    km.fit(X.astype(np.float32))
    return torch.from_numpy(km.cluster_centers_.astype(np.float32))


def nearest(X, cents):
    out = []
    c = cents.to(dev)
    c2 = 0.5 * (c ** 2).sum(1)
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


# ── Experiment definitions ──────────────────────────────────────
meta = {s: json.load(open(OUT / f"meta_{s}.json")) for s in ["dg", "ld_train", "ld_val"]}
dom = {s: np.array([m["domain"] for m in meta[s]]) for s in meta}
perm = np.random.default_rng(2026).permutation(len(meta["dg"]))
n_dg_pool = int(0.8 * len(perm))
dg_pool, dg_test = np.sort(perm[:n_dg_pool]), np.sort(perm[n_dg_pool:])
ld_all = np.arange(len(meta["ld_train"]))
ld_val_sets = {"rural": np.where(dom["ld_val"] == "Rural")[0],
               "urban": np.where(dom["ld_val"] == "Urban")[0]}

EXPS = [
    dict(name="DG", src="dg", pool=dg_pool, eval_src="dg", sets={"test": dg_test}),
    dict(name="LD-all", src="ld_train", pool=ld_all, eval_src="ld_val", sets=ld_val_sets),
    dict(name="LD-rural", src="ld_train", pool=np.where(dom["ld_train"] == "Rural")[0],
         eval_src="ld_val", sets=ld_val_sets),
    dict(name="LD-urban", src="ld_train", pool=np.where(dom["ld_train"] == "Urban")[0],
         eval_src="ld_val", sets=ld_val_sets),
]
json.dump({"dg_pool": dg_pool.tolist(), "dg_test": dg_test.tolist()},
          open(OUT / "dg_split.json", "w"))

# ── Phase A: fit all models ─────────────────────────────────────
models, cent_sets = [], {}
t_start = time.time()
for E in EXPS:
    src, C = E["src"], N_CLASSES[E["src"]]
    Fm = load_feats(src)
    Y = patch_labels(np.load(OUT / f"hist_{src}.npy"))
    red = reduced(src)
    pool = E["pool"]
    log(f"[{E['name']}] pool={len(pool)} images, C={C}")
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        kx = red[0][pool].reshape(-1, DIM)
        if len(kx) > KM_CAP:
            kx = kx[rng.choice(len(kx), KM_CAP, replace=False)]
        t0 = time.time()
        cent_sets[(E["name"], seed, C)] = kmeans(kx, C, seed)
        cent_sets[(E["name"], seed, K_OVER)] = kmeans(kx, K_OVER, seed)
        del kx
        models.append(dict(exp=E["name"], method="kmeans_hungarian", n=0, seed=seed,
                           kind="cent", key=(E["name"], seed, C), mapping=None))
        log(f"  seed {seed}: k-means done ({time.time()-t0:.0f}s)")
        draw_rng = np.random.default_rng(1000 + seed)
        order = draw_rng.permutation(pool)   # nested budgets: first n images of one ordering
        for n in BUDGETS:
            nn_ = len(pool) if n == "all" else n
            if n != "all" and n >= len(pool):
                continue
            X, y = train_set(Fm, Y, red, order[:nn_], seed)
            t0 = time.time()
            W, b = fit_linear(X, y, C)
            models.append(dict(exp=E["name"], method="linear", n=nn_, seed=seed,
                               kind="lin", W=W, b=b))
            mp = label_clusters(cent_sets[(E["name"], seed, K_OVER)], X, y, C)
            models.append(dict(exp=E["name"], method="cluster_label", n=nn_, seed=seed,
                               kind="cent", key=(E["name"], seed, K_OVER), mapping=mp))
            log(f"  seed {seed} n={nn_:>5}: {len(y):>7} labelled patches, "
                f"classes={len(np.unique(y))}, fit {time.time()-t0:.1f}s")
            del X, y
            torch.cuda.empty_cache()
torch.save({"models": models, "cent_sets": cent_sets}, OUT / "models.pt")
log(f"Phase A done in {(time.time()-t_start)/60:.1f} min, {len(models)} models")

# ── Phase B: one streaming pass per evaluation source ───────────
conf = {}
for eval_src in ["dg", "ld_val"]:
    exps = {E["name"]: E for E in EXPS if E["eval_src"] == eval_src}
    ms = [(i, m) for i, m in enumerate(models) if m["exp"] in exps]
    C = N_CLASSES[eval_src]
    Fm = load_feats(eval_src)
    H = np.load(OUT / f"hist_{eval_src}.npy")
    lin = [(i, m) for i, m in ms if m["kind"] == "lin"]
    Wall = torch.cat([m["W"] for _, m in lin], 1).to(dev)
    ball = torch.cat([m["b"] for _, m in lin]).to(dev)
    keys = sorted({m["key"] for _, m in ms if m["kind"] == "cent"})
    sets = next(iter(exps.values()))["sets"]
    for i, m in ms:
        for sname in sets:
            conf[(i, sname)] = torch.zeros(C, C, dtype=torch.float64, device=dev)
    t0 = time.time()
    for sname, idx in sets.items():
        for s in range(0, len(idx), 32):
            ch = idx[s:s + 32]
            X = torch.from_numpy(np.concatenate(
                [np.asarray(Fm[i * NP:(i + 1) * NP]) for i in ch])).to(dev).float()
            h = torch.from_numpy(H[ch].reshape(-1, C).astype(np.float64)).to(dev)
            P = (X @ Wall + ball).view(len(X), len(lin), C).argmax(-1)
            for j, (i, m) in enumerate(lin):
                conf[(i, sname)].index_add_(0, P[:, j], h)
            assign = {}
            for k in keys:
                c = cent_sets[k].to(dev)
                assign[k] = (X @ c.T - 0.5 * (c ** 2).sum(1)).argmax(1)
            for i, m in ms:
                if m["kind"] != "cent":
                    continue
                a = assign[m["key"]]
                pred = a if m["mapping"] is None else m["mapping"].to(dev)[a]
                conf[(i, sname)].index_add_(0, pred, h)
        log(f"  evaluated {eval_src}/{sname} ({len(idx)} images) {time.time()-t0:.0f}s")


# ── Metrics ─────────────────────────────────────────────────────
def scores(M):
    tp = np.diag(M)
    iou = tp / np.maximum(M.sum(0) + M.sum(1) - tp, 1)
    return 100 * iou, 100 * tp.sum() / M.sum()


rows, conf_np = [], {}
for i, m in enumerate(models):
    E = next(e for e in EXPS if e["name"] == m["exp"])
    Ms = {s: conf[(i, s)].cpu().numpy() for s in E["sets"]}
    if len(Ms) > 1:
        Ms["all"] = sum(Ms.values())
    perm_rows = None
    if m["method"] == "kmeans_hungarian":
        ref = Ms["all"] if "all" in Ms else next(iter(Ms.values()))
        r, c = linear_sum_assignment(-ref)
        perm_rows = np.empty(len(r), dtype=int)
        perm_rows[c] = r
    for s, M in Ms.items():
        if perm_rows is not None:
            M = M[perm_rows]
        iou, acc = scores(M)
        rows.append(dict(exp=m["exp"], method=m["method"], n=m["n"], seed=m["seed"],
                         eval=s, miou=float(iou.mean()), acc=float(acc),
                         iou=[float(v) for v in iou], pool=int(len(E["pool"]))))
        conf_np[f"{m['exp']}|{m['method']}|{m['n']}|{m['seed']}|{s}"] = M
with open(OUT / "results.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
np.savez_compressed(OUT / "confusions.npz", **conf_np)
log(f"wrote {len(rows)} result rows; total {(time.time()-t_start)/60:.1f} min")
