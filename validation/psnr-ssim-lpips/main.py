import torch
import numpy as np
import subprocess
import os
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
import lpips


def get_video_duration(video_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def extract_frame_at(video_path: str, timestamp: float, output_path: str):
    duration = get_video_duration(video_path)
    timestamp = min(timestamp, duration - 0.1)  # clamp to avoid overshooting
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


def load_img(path, target_size: tuple | None = None):
    img = Image.open(path).convert("RGB")
    if target_size is not None:
        img = img.resize(target_size, Image.Resampling.LANCZOS)
    return np.array(img).astype(np.float32) / 255.0


def compute_metrics(gt: np.ndarray, rendered: np.ndarray, loss_fn) -> dict:
    psnr = peak_signal_noise_ratio(gt, rendered, data_range=1.0)
    ssim = structural_similarity(gt, rendered, channel_axis=2, data_range=1.0)

    t_r = torch.tensor(rendered).permute(2, 0, 1).unsqueeze(0) * 2 - 1
    t_g = torch.tensor(gt).permute(2, 0, 1).unsqueeze(0) * 2 - 1
    lpips_score = loss_fn(t_r, t_g).item()

    return {"psnr": psnr, "ssim": ssim, "lpips": lpips_score}


GT_VIDEO = "ground-truth.mp4"
AI_VIDEO = "input.mp4"
OUT_DIR = "frame_comparisons"
os.makedirs(OUT_DIR, exist_ok=True)

# Relative positions to sample (0.0 = first frame, 1.0 = last frame)
SAMPLE_POSITIONS = [0.0, 0.25, 0.5, 0.75]

gt_duration = get_video_duration(GT_VIDEO)
ai_duration = get_video_duration(AI_VIDEO)

print(f"Ground truth duration : {gt_duration:.2f}s")
print(f"AI video duration     : {ai_duration:.2f}s")
print()

loss_fn = lpips.LPIPS(net="alex")

results = []

for pos in SAMPLE_POSITIONS:
    gt_ts = pos * gt_duration
    ai_ts = pos * ai_duration

    gt_frame_path = os.path.join(OUT_DIR, f"gt_{pos:.2f}.png")
    ai_frame_path = os.path.join(OUT_DIR, f"ai_{pos:.2f}.png")

    extract_frame_at(GT_VIDEO, gt_ts, gt_frame_path)
    extract_frame_at(AI_VIDEO, ai_ts, ai_frame_path)

    gt_img = load_img(gt_frame_path)
    ai_img = load_img(ai_frame_path, target_size=(gt_img.shape[1], gt_img.shape[0]))

    metrics = compute_metrics(gt_img, ai_img, loss_fn)
    results.append({"position": pos, "gt_ts": gt_ts, "ai_ts": ai_ts, **metrics})

    print(
        f"Position {pos*100:3.0f}%  |  GT {gt_ts:5.2f}s  AI {ai_ts:5.2f}s  |"
        f"  PSNR {metrics['psnr']:5.2f} dB"
        f"  SSIM {metrics['ssim']:.4f}"
        f"  LPIPS {metrics['lpips']:.4f}"
    )

print("\n── Averages ──────────────────────────────────────────────────")
print(f"  PSNR  : {np.mean([r['psnr']  for r in results]):.2f} dB")
print(f"  SSIM  : {np.mean([r['ssim']  for r in results]):.4f}")
print(f"  LPIPS : {np.mean([r['lpips'] for r in results]):.4f}")
