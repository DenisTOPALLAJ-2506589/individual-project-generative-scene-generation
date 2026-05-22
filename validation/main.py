import os
import cv2
import lpips
import torch
import pandas as pd
import numpy as np

from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

# =========================================================
# CONFIG
# =========================================================

ROOT_FOLDERS = [
    "./kot_5fps_eval/",
    "./kot_10fps_eval/",
    "./ai_kot_10fps_eval/",
    "./ai_kot_5fps_eval/",
]

OUTPUT_CSV = "all_validation_metrics.csv"

# =========================================================
# LPIPS SETUP
# =========================================================

device = "cuda" if torch.cuda.is_available() else "cpu"

loss_fn = lpips.LPIPS(net="alex").to(device)

# =========================================================
# Helper Functions
# =========================================================


def compute_lpips(img1, img2):
    """
    LPIPS expects:
    - RGB
    - float32
    - normalized to [-1, 1]
    - shape [1, 3, H, W]
    """

    img1 = img1.astype(np.float32) / 127.5 - 1.0
    img2 = img2.astype(np.float32) / 127.5 - 1.0

    tensor1 = torch.tensor(img1).permute(2, 0, 1).unsqueeze(0).to(device)
    tensor2 = torch.tensor(img2).permute(2, 0, 1).unsqueeze(0).to(device)

    with torch.no_grad():
        distance = loss_fn(tensor1, tensor2)

    return float(distance.item())


# =========================================================
# Main Processing
# =========================================================

all_results = []

for root_folder in ROOT_FOLDERS:

    eval_folder = os.path.join(root_folder, "eval_step_7000")

    if not os.path.exists(eval_folder):
        print(f"Missing folder: {eval_folder}")
        continue

    dataset_name = os.path.basename(os.path.normpath(root_folder))

    print(f"\n===================================")
    print(f"Processing: {dataset_name}")
    print(f"===================================")

    image_files = sorted(
        [f for f in os.listdir(eval_folder) if f.lower().endswith(".png")]
    )

    for filename in image_files:

        image_path = os.path.join(eval_folder, filename)

        # -------------------------------------------------
        # Load image
        # -------------------------------------------------

        img = cv2.imread(image_path)

        if img is None:
            print(f"Failed loading {image_path}")
            continue

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        h, w, _ = img.shape

        # -------------------------------------------------
        # Split image
        # Assumption:
        # LEFT  = Ground Truth
        # RIGHT = Reconstruction
        # -------------------------------------------------

        mid = w // 2

        gt = img[:, :mid]
        render = img[:, mid:]

        # -------------------------------------------------
        # Metrics
        # -------------------------------------------------

        image_psnr = psnr(gt, render, data_range=255)

        image_ssim = ssim(gt, render, channel_axis=2, data_range=255)

        image_lpips = compute_lpips(gt, render)

        # -------------------------------------------------
        # Store result
        # -------------------------------------------------

        all_results.append(
            {
                "dataset": dataset_name,
                "image": filename,
                "psnr": image_psnr,
                "ssim": image_ssim,
                "lpips": image_lpips,
                "height": h,
                "width": w,
            }
        )

        print(
            f"{dataset_name} | {filename} | "
            f"PSNR={image_psnr:.3f} | "
            f"SSIM={image_ssim:.4f} | "
            f"LPIPS={image_lpips:.4f}"
        )

# =========================================================
# Save CSV
# =========================================================

df = pd.DataFrame(all_results)

df = df.sort_values(by=["dataset", "psnr"], ascending=[True, False])

df.to_csv(OUTPUT_CSV, index=False)

print("\n===================================")
print("DONE")
print("===================================")
print(f"Saved CSV: {OUTPUT_CSV}")

# =========================================================
# Print Dataset Summaries
# =========================================================

print("\n===================================")
print("DATASET SUMMARIES")
print("===================================")

grouped = df.groupby("dataset")

for dataset, group in grouped:

    avg_psnr = group["psnr"].mean()
    avg_ssim = group["ssim"].mean()
    avg_lpips = group["lpips"].mean()

    best_psnr = group["psnr"].max()
    worst_psnr = group["psnr"].min()

    print(f"\n{dataset}")
    print(f"Images:      {len(group)}")
    print(f"Avg PSNR:    {avg_psnr:.4f}")
    print(f"Avg SSIM:    {avg_ssim:.4f}")
    print(f"Avg LPIPS:   {avg_lpips:.4f}")
    print(f"Best PSNR:   {best_psnr:.4f}")
    print(f"Worst PSNR:  {worst_psnr:.4f}")
