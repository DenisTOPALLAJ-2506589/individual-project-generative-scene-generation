import torch
import numpy as np
import subprocess
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity
import lpips


def get_first_frame(video_path: str):
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-frames:v", "1", "output.png"],
        capture_output=True,
        text=True,
    )


def load_img(path, target_size: tuple | None = None):
    img = Image.open(path).convert("RGB")
    if target_size is not None:
        img = img.resize(target_size, Image.Resampling.LANCZOS)
    return np.array(img).astype(np.float32) / 255.0


get_first_frame("input.mp4")

ground_truth = load_img("ground-truth.png")
target_size = (ground_truth.shape[1], ground_truth.shape[0])  # (width, height)
rendered = load_img("output.png", target_size=target_size)

print(f"Comparing images at resolution: {ground_truth.shape}")

# PSNR
psnr = peak_signal_noise_ratio(ground_truth, rendered, data_range=1.0)
print(f"PSNR: {psnr:.2f} dB")

# SSIM
ssim = structural_similarity(ground_truth, rendered, channel_axis=2, data_range=1.0)
print(f"SSIM: {ssim:.4f}")

# LPIPS
loss_fn = lpips.LPIPS(net="alex")
t_rendered = torch.tensor(rendered).permute(2, 0, 1).unsqueeze(0) * 2 - 1
t_gt = torch.tensor(ground_truth).permute(2, 0, 1).unsqueeze(0) * 2 - 1
lpips_score = loss_fn(t_rendered, t_gt).item()
print(f"LPIPS: {lpips_score:.4f}")
