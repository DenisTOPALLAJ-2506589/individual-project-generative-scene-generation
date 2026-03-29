import numpy as np
from scipy.spatial import KDTree


def load_colmap_points3d_txt(txt_path: str) -> np.ndarray:
    points = []
    with open(txt_path) as f:
        for line in f:
            if line.startswith("#") or line.strip() == "":
                continue
            parts = line.split()
            points.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return np.array(points, dtype=np.float32)


def load_ply_points(ply_path: str) -> np.ndarray:
    points = []
    with open(ply_path, "rb") as f:
        header_lines = []
        while True:
            line = f.readline().decode("utf-8", errors="ignore").strip()
            header_lines.append(line)
            if line == "end_header":
                break

        n_vertices = 0
        is_binary = False
        for line in header_lines:
            if line.startswith("element vertex"):
                n_vertices = int(line.split()[-1])
            if "binary" in line:
                is_binary = True

        if is_binary:
            raw = np.frombuffer(f.read(n_vertices * 3 * 4), dtype=np.float32)
            points = raw.reshape(-1, 3)
        else:
            for _ in range(n_vertices):
                row = f.readline().decode().split()
                points.append([float(row[0]), float(row[1]), float(row[2])])
            points = np.array(points, dtype=np.float32)

    return points


def depth_metrics(pred: np.ndarray, gt: np.ndarray, max_depth: float = 10.0) -> dict:
    mask = (gt > 0) & (gt < max_depth)
    pred, gt = pred[mask], gt[mask]

    if len(pred) == 0:
        raise ValueError(
            f"No valid depth points after masking with max_depth={max_depth}. "
            "Try increasing max_depth."
        )

    thresh = np.maximum(pred / gt, gt / pred)
    d1 = (thresh < 1.25).mean()
    d2 = (thresh < 1.25**2).mean()
    d3 = (thresh < 1.25**3).mean()

    rmse = float(np.sqrt(((pred - gt) ** 2).mean()))
    abs_rel = float((np.abs(pred - gt) / gt).mean())

    return {"delta1": d1, "delta2": d2, "delta3": d3, "RMSE": rmse, "AbsRel": abs_rel}


def compute_chamfer(splat_path: str, ref_pts: np.ndarray) -> float:
    splat_pts = load_ply_points(splat_path)

    print(f"Splat points:     {len(splat_pts):,}")
    print(f"Reference points: {len(ref_pts):,}")

    ref_tree = KDTree(ref_pts)
    splat_tree = KDTree(splat_pts)

    dists_sr, _ = ref_tree.query(splat_pts)
    dists_rs, _ = splat_tree.query(ref_pts)

    return float(np.mean(dists_sr) + np.mean(dists_rs))


splat_pts = load_ply_points("splat.ply")
ref_pts = load_colmap_points3d_txt("./0/points3D.txt")

# Use Z coordinate as a depth proxy for both clouds
pred_depth = splat_pts[:, 2]
gt_depth = ref_pts[:, 2]

# Interpolate reference depth to match splat sample count
if len(pred_depth) != len(gt_depth):
    indices = np.linspace(0, len(gt_depth) - 1, len(pred_depth)).astype(int)
    gt_depth = gt_depth[indices]

# Scale max_depth to the actual range of the scene
max_depth = float(np.percentile(gt_depth, 95))
print(f"Using max_depth: {max_depth:.3f} (95th percentile of reference depths)\n")

metrics = depth_metrics(pred_depth, gt_depth, max_depth=max_depth)
for k, v in metrics.items():
    print(f"{k}: {v:.4f}")

chamfer = compute_chamfer("splat.ply", ref_pts)
print(f"Chamfer distance: {chamfer:.5f}  (lower = more geometrically accurate)")
