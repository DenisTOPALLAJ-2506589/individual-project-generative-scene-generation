# Gaussian Splatting — Reconstruction Quality Metrics

This document explains the metrics used to evaluate the quality of a Gaussian Splatting reconstruction, what each metric measures, and what scores to aim for.

---

## Overview

Quality evaluation falls into four categories:

- **Reference-based** — compares your rendered views against held-out ground truth photos. These are the most meaningful metrics and are used in all published benchmarks.
- **No-reference** — scores a rendered frame on its own, without needing a ground truth. Useful when you have no held-out test images.
- **Geometric accuracy** — compares the 3D point cloud of the splat against the COLMAP sparse reconstruction to measure how accurately the scene geometry was captured.
- **Depth accuracy** — compares the depth distribution of the splat against the COLMAP reference to measure per-point depth error.

---

## Reference-based Metrics

### PSNR — Peak Signal-to-Noise Ratio

**What it measures:** Pixel-level fidelity. Compares the average squared difference between corresponding pixels in the rendered image and the ground truth. Expressed in decibels (dB) — a logarithmic scale.

**Interpretation:** Higher is better. A difference of 3 dB roughly means the rendered image has twice as much noise/error. PSNR is sensitive to exact pixel values, so it can penalise small spatial shifts harshly even if the image looks correct to the eye.

**Thresholds:**

| Score    | Quality                                           |
| -------- | ------------------------------------------------- |
| > 35 dB  | Excellent — near-perfect reconstruction           |
| 30–35 dB | Good — minor visible artefacts                    |
| 25–30 dB | Acceptable — noticeable but tolerable degradation |
| < 25 dB  | Poor — significant reconstruction errors          |

**Typical range for Gaussian Splatting:** 27–34 dB on standard scenes (Tanks & Temples, Mip-NeRF 360).

---

### SSIM — Structural Similarity Index

**What it measures:** Perceptual similarity based on luminance, contrast, and local structure. Rather than comparing pixel values directly, it compares local patches, making it more aligned with how humans perceive image quality than PSNR.

**Interpretation:** Ranges from 0 to 1. Higher is better. A score of 1.0 means the images are structurally identical.

**Thresholds:**

| Score     | Quality    |
| --------- | ---------- |
| > 0.90    | Excellent  |
| 0.80–0.90 | Good       |
| 0.70–0.80 | Acceptable |
| < 0.70    | Poor       |

**Typical range for Gaussian Splatting:** 0.82–0.93 on standard scenes.

---

### LPIPS — Learned Perceptual Image Patch Similarity

**What it measures:** Perceptual distance using deep neural network features (AlexNet by default). Compares how similar two images look to a neural network trained on human perceptual judgements, rather than comparing raw pixel values. Widely considered the most human-aligned of the three.

**Interpretation:** Lower is better. A score of 0.0 means perceptually identical.

**Thresholds:**

| Score     | Quality    |
| --------- | ---------- |
| < 0.05    | Excellent  |
| 0.05–0.15 | Good       |
| 0.15–0.25 | Acceptable |
| > 0.25    | Poor       |

**Typical range for Gaussian Splatting:** 0.04–0.18 on standard scenes.

---

## No-reference Metrics

These metrics do not require a ground truth image. They are computed directly on sampled frames from the video and give a quick signal about overall render quality without needing a held-out test set.

### Blur — Laplacian Variance

**What it measures:** Sharpness of a frame. Applies a Laplacian filter (edge detector) to the grayscale image and computes the variance of the response. Sharp images have strong, high-variance edges; blurry images have weak, low-variance responses.

**Interpretation:** Higher is better.

**Thresholds:**

| Score   | Quality                      |
| ------- | ---------------------------- |
| > 500   | Excellent — very sharp       |
| 100–500 | Good — acceptable sharpness  |
| 50–100  | Acceptable — slightly blurry |
| < 50    | Poor — noticeably blurry     |

---

### Brightness — Mean Pixel Intensity

**What it measures:** Average brightness of a frame on a 0–255 scale. Flags frames that are under- or over-exposed, which can indicate bad lighting conditions in the original video or tone-mapping issues in the render.

**Interpretation:** A well-exposed frame sits in the middle of the range. Very low or very high values indicate exposure problems.

**Thresholds:**

| Score             | Quality                              |
| ----------------- | ------------------------------------ |
| 100–180           | Good — well exposed                  |
| 60–100 or 180–220 | Acceptable — slightly dark or bright |
| < 60 or > 220     | Poor — under- or over-exposed        |

---

### Contrast — Standard Deviation of Pixel Intensity

**What it measures:** Spread of brightness values across the frame. A high standard deviation means the image uses a wide tonal range (dark shadows and bright highlights), which indicates rich detail. A low value means the image is flat and washed out.

**Interpretation:** Higher is generally better, though very high values can indicate harsh lighting.

**Thresholds:**

| Score | Quality                      |
| ----- | ---------------------------- |
| > 60  | Excellent — rich tonal range |
| 40–60 | Good                         |
| 20–40 | Acceptable — somewhat flat   |
| < 20  | Poor — very low contrast     |

---

## Geometric Accuracy

These metrics compare the 3D point cloud exported from your Gaussian Splat against the COLMAP sparse reconstruction used as a reference. They measure how well the spatial structure of the scene was reconstructed, independent of how the renders look.

The reference points are read directly from `points3D.txt` produced by COLMAP — no additional conversion needed.

### Chamfer Distance

**What it measures:** The average nearest-neighbour distance between two point clouds, computed symmetrically. For every point in the splat cloud the closest point in the reference cloud is found, and vice versa. The chamfer distance is the mean of both directions added together. A low value means the two clouds are spatially close to each other.

**Interpretation:** Lower is better. The scale depends on the scene units — a COLMAP reconstruction in metres will have different absolute values than one in arbitrary units. Always compare chamfer distances from the same pipeline.

**Thresholds:**

| Score     | Quality                                |
| --------- | -------------------------------------- |
| < 0.01    | Excellent — very tight geometric match |
| 0.01–0.05 | Good                                   |
| 0.05–0.10 | Acceptable                             |
| > 0.10    | Poor — significant geometric deviation |

---

## Depth Accuracy

These metrics compare the Z-coordinate depth of splat points against the COLMAP reference points. They measure how accurately the depth of the scene is represented, which directly affects how convincing the reconstruction looks from novel viewpoints.

### AbsRel — Absolute Relative Error

**What it measures:** The mean absolute difference between predicted and reference depth values, divided by the reference depth. Normalising by the reference depth makes this scale-invariant, so it works regardless of how far away the scene is.

**Interpretation:** Lower is better. A score of 0.10 means the predicted depth is on average 10% off from the reference.

**Thresholds:**

| Score     | Quality    |
| --------- | ---------- |
| < 0.05    | Excellent  |
| 0.05–0.10 | Good       |
| 0.10–0.20 | Acceptable |
| > 0.20    | Poor       |

---

### RMSE — Root Mean Squared Error

**What it measures:** The square root of the mean squared difference between predicted and reference depth values. Compared to AbsRel, RMSE penalises large outlier errors more heavily, making it sensitive to occasional large depth mistakes.

**Interpretation:** Lower is better. Units match the scene scale.

**Thresholds:**

| Score     | Quality    |
| --------- | ---------- |
| < 0.10    | Excellent  |
| 0.10–0.25 | Good       |
| 0.25–0.50 | Acceptable |
| > 0.50    | Poor       |

---

### Delta Thresholds (δ1, δ2, δ3)

**What it measures:** The percentage of depth predictions within a multiplicative threshold of the ground truth. δ1 counts predictions where `max(pred/gt, gt/pred) < 1.25`, δ2 uses `1.25²`, and δ3 uses `1.25³`. Together they show what fraction of points are within 25%, 56%, and 95% of the reference depth.

**Interpretation:** Higher is better. δ1 is the strictest and most informative.

**Thresholds:**

| Metric | Excellent | Good      | Acceptable | Poor   |
| ------ | --------- | --------- | ---------- | ------ |
| δ1     | > 0.90    | 0.80–0.90 | 0.70–0.80  | < 0.70 |
| δ2     | > 0.95    | 0.90–0.95 | 0.80–0.90  | < 0.80 |
| δ3     | > 0.99    | 0.95–0.99 | 0.90–0.95  | < 0.90 |

---

## Quick Reference

| Metric        | Category        | Direction        | Excellent | Good             | Acceptable   | Poor         |
| ------------- | --------------- | ---------------- | --------- | ---------------- | ------------ | ------------ |
| PSNR (dB)     | Reference-based | Higher is better | > 35      | 30–35            | 25–30        | < 25         |
| SSIM          | Reference-based | Higher is better | > 0.90    | 0.80–0.90        | 0.70–0.80    | < 0.70       |
| LPIPS         | Reference-based | Lower is better  | < 0.05    | 0.05–0.15        | 0.15–0.25    | > 0.25       |
| Blur          | No-reference    | Higher is better | > 500     | 100–500          | 50–100       | < 50         |
| Brightness    | No-reference    | Middle is better | 100–180   | 60–100 / 180–220 | outside that | < 60 / > 220 |
| Contrast      | No-reference    | Higher is better | > 60      | 40–60            | 20–40        | < 20         |
| Chamfer dist. | Geometric       | Lower is better  | < 0.01    | 0.01–0.05        | 0.05–0.10    | > 0.10       |
| AbsRel        | Depth           | Lower is better  | < 0.05    | 0.05–0.10        | 0.10–0.20    | > 0.20       |
| RMSE          | Depth           | Lower is better  | < 0.10    | 0.10–0.25        | 0.25–0.50    | > 0.50       |
| δ1            | Depth           | Higher is better | > 0.90    | 0.80–0.90        | 0.70–0.80    | < 0.70       |
| δ2            | Depth           | Higher is better | > 0.95    | 0.90–0.95        | 0.80–0.90    | < 0.80       |
| δ3            | Depth           | Higher is better | > 0.99    | 0.95–0.99        | 0.90–0.95    | < 0.90       |

---

## Notes

- Thresholds vary by scene type. Indoor scenes with flat walls typically score higher than outdoor scenes with fine vegetation or sky detail.
- PSNR and SSIM can disagree — a blurry render may score well on PSNR but poorly on SSIM. Always report all three reference metrics together.
- LPIPS is the most reliable single metric for perceptual quality. If you can only use one, use LPIPS.
- No-reference metrics (blur, brightness, contrast) are computed over 10 randomly sampled frames. The standard deviation reported alongside each mean indicates consistency — a high std means quality varies significantly across the video.
- Chamfer distance and depth metrics depend on the coordinate scale of the COLMAP reconstruction. Only compare values produced by the same pipeline.
- Depth metrics use the 95th percentile of the reference depth as max_depth to avoid outliers skewing the results.
