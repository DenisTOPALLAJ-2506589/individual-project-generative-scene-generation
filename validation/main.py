import torch
import numpy as np
import subprocess
import os
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
import lpips
import cv2


GT_VIDEO = "ground-truth.mp4"
AI_VIDEO = "input.mp4"
OUT_DIR = "frame_comparisons"
os.makedirs(OUT_DIR, exist_ok=True)

# How many anchor frames to extract from the GT video for matching
N_ANCHORS = 10


def get_video_duration(path: str) -> float:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True,
        text=True,
    )
    return float(r.stdout.strip())


def extract_all_frames(video_path: str, out_dir: str, fps: float = 2.0) -> list[str]:
    """
    Dump the entire video at `fps` frames/sec into out_dir.
    Returns sorted list of output paths.
    """
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vf",
            f"fps={fps}",
            os.path.join(out_dir, "%06d.png"),
        ],
        capture_output=True,
        text=True,
    )
    return sorted(
        os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.endswith(".png")
    )


def extract_frame_at(video_path: str, timestamp: float, output_path: str):
    duration = get_video_duration(video_path)
    timestamp = min(timestamp, duration - 0.1)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(timestamp),
            "-i",
            video_path,
            "-frames:v",
            "1",
            output_path,
        ],
        capture_output=True,
        text=True,
    )


def load_img_np(path: str, target_size: tuple | None = None) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    if target_size:
        img = img.resize(target_size, Image.Resampling.LANCZOS)
    return np.array(img).astype(np.float32) / 255.0


def compute_metrics(gt: np.ndarray, ai: np.ndarray, loss_fn) -> dict:
    psnr = peak_signal_noise_ratio(gt, ai, data_range=1.0)
    ssim = structural_similarity(gt, ai, channel_axis=2, data_range=1.0)
    t_ai = torch.tensor(ai).permute(2, 0, 1).unsqueeze(0) * 2 - 1
    t_gt = torch.tensor(gt).permute(2, 0, 1).unsqueeze(0) * 2 - 1
    lpips_score = loss_fn(t_ai, t_gt).item()
    return {"psnr": psnr, "ssim": ssim, "lpips": lpips_score}


def orb_descriptor(image_path: str) -> np.ndarray | None:
    """
    Compute ORB descriptors for an image.
    ORB is faster than SIFT and has no patent issues.
    Returns descriptor array or None if extraction fails.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    orb = cv2.ORB_create(nfeatures=1000)
    _, desc = orb.detectAndCompute(img, None)
    return desc  # shape (N, 32) uint8, or None


def find_best_match_with_homography_check(
    gt_path: str, ai_frame_paths: list, ai_descs: list
) -> tuple[int, str, float]:
    """
    Extends ORB matching with a homography inlier check.
    Rejects candidates where the camera shift is implausibly large.
    Returns (best_idx, best_path, inlier_ratio).
    """
    gt_img = cv2.imread(gt_path, cv2.IMREAD_GRAYSCALE)
    orb = cv2.ORB_create(nfeatures=1000)
    kp_gt, desc_gt = orb.detectAndCompute(gt_img, None)

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    best_idx, best_score, best_path = 0, -1.0, ai_frame_paths[0]

    for i, (ai_path, ai_desc) in enumerate(zip(ai_frame_paths, ai_descs)):
        if ai_desc is None or len(ai_desc) < 8:
            continue

        matches = bf.match(desc_gt, ai_desc)
        matches = sorted(matches, key=lambda m: m.distance)
        good = [m for m in matches if m.distance < 64]

        if len(good) < 8:
            continue

        # Extract point correspondences
        ai_img = cv2.imread(ai_path, cv2.IMREAD_GRAYSCALE)
        kp_ai, _ = orb.detectAndCompute(ai_img, None)

        pts_gt = np.float32([kp_gt[m.queryIdx].pt for m in good])
        pts_ai = np.float32([kp_ai[m.trainIdx].pt for m in good])

        # Homography with RANSAC — inliers are geometrically consistent matches
        _, mask = cv2.findHomography(
            pts_gt, pts_ai, cv2.RANSAC, ransacReprojThreshold=5.0
        )

        if mask is None:
            continue

        inlier_ratio = mask.sum() / len(good)

        # Score = inlier count (not just match count)
        score = mask.sum()

        if score > best_score:
            best_score = score
            best_idx = i
            best_path = ai_path

    return best_idx, best_path, best_score


loss_fn = lpips.LPIPS(net="alex")

gt_duration = get_video_duration(GT_VIDEO)
ai_duration = get_video_duration(AI_VIDEO)
print(f"GT duration : {gt_duration:.2f}s")
print(f"AI duration : {ai_duration:.2f}s\n")

# 1. Dump AI video frames at 2 fps so we have a dense pool to search through
print("Extracting AI video frames for matching pool …")
ai_frames_dir = os.path.join(OUT_DIR, "ai_pool")
ai_frame_paths = extract_all_frames(AI_VIDEO, ai_frames_dir, fps=2.0)
print(f"  {len(ai_frame_paths)} AI frames extracted\n")

# 2. Pre-compute descriptors for every AI frame  (done once, reused N_ANCHORS times)
print("Computing ORB descriptors for AI pool …")
ai_descs = [orb_descriptor(p) for p in ai_frame_paths]
print("  Done\n")

# 3. For each anchor position in the GT video, find the best-matching AI frame
anchor_positions = np.linspace(0.0, 1.0, N_ANCHORS, endpoint=False)
# Skip 1.0 — last frame is often a duplicate or black frame

results = []
print(
    f"{'GT pos':>8}  {'GT ts':>6}  {'AI frame':>10}  {'AI ts':>6}  "
    f"{'PSNR':>8}  {'SSIM':>7}  {'LPIPS':>7}"
)
print("─" * 70)

for pos in anchor_positions:
    gt_ts = pos * gt_duration

    # Extract the GT anchor frame
    gt_path = os.path.join(OUT_DIR, f"gt_{pos:.3f}.png")
    extract_frame_at(GT_VIDEO, gt_ts, gt_path)
    gt_desc = orb_descriptor(gt_path)

    if gt_desc is None:
        print(f"  WARNING: no features found in GT frame at {gt_ts:.2f}s, skipping")
        continue

    # Find the AI frame that best matches this GT frame
    best_idx, best_path, best_score = find_best_match_with_homography_check(
        gt_path, ai_frame_paths, ai_descs
    )

    # Derive the actual timestamp of that AI frame from its filename index
    # ffmpeg names frames 000001.png, 000002.png … at the chosen fps
    frame_number = int(os.path.splitext(os.path.basename(best_path))[0])
    ai_ts = (frame_number - 1) / 2.0  # because we dumped at 2 fps

    # Load and compare
    gt_img = load_img_np(gt_path)
    ai_img = load_img_np(best_path, target_size=(gt_img.shape[1], gt_img.shape[0]))
    m = compute_metrics(gt_img, ai_img, loss_fn)

    results.append({"gt_pos": pos, "gt_ts": gt_ts, "ai_ts": ai_ts, **m})
    print(
        f"  {pos*100:5.1f}%   {gt_ts:6.2f}s   {os.path.basename(best_path):>10}  "
        f"{ai_ts:6.2f}s   {m['psnr']:6.2f} dB   {m['ssim']:.4f}   {m['lpips']:.4f}"
    )

print("\n── Averages ────────────────────────────────────────────────")
print(f"  PSNR  : {np.mean([r['psnr']  for r in results]):.2f} dB")
print(f"  SSIM  : {np.mean([r['ssim']  for r in results]):.4f}")
print(f"  LPIPS : {np.mean([r['lpips'] for r in results]):.4f}")
