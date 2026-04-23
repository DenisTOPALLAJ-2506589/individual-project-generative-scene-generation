# Gaussian Splatting — Reconstruction Quality Metrics

This document explains the metrics used to evaluate the quality of a Gaussian Splatting reconstruction, what each metric measures, and what scores to aim for.

---

## Overview

Quality evaluation falls into four categories:

- **Reference-based** - compares your rendered views against held-out ground truth photos. These are the most meaningful metrics and are used in all published benchmarks.
- **COLMAP statistics** - using the COLMAP statistics, we can determine the reprojection errors, amount of points, images, and other valuable information.

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

### Reprojection Error

**What it measures:** The average distance, in pixels, between where COLMAP _observed_ a 2D feature point in an image and where that same point _projects_ back onto the image after 3D reconstruction. In other words: after COLMAP has estimated the 3D position of a point and the camera pose for each image, it re-projects the 3D point back into every image it was seen in and measures how far off it lands from the original detected keypoint. The mean of all these distances across the entire reconstruction is the reprojection error.

A low reprojection error means the recovered 3D structure and camera poses are mutually consistent — the geometry "explains" the observed 2D measurements well. A high reprojection error means either the camera poses are inaccurate, the 3D points are poorly localised, or both. For Gaussian Splatting specifically, inaccurate poses directly corrupt the photometric loss during training, since each Gaussian is optimised to match the training images under the assumption that the camera poses are correct.

**Interpretation:** Lower is better. Expressed in pixels.

**Thresholds:**

| Score      | Quality                                                          |
| ---------- | ---------------------------------------------------------------- |
| < 0.5 px   | Excellent — very accurate pose and structure estimation          |
| 0.5–1.0 px | Good — acceptable for most downstream tasks including 3DGS       |
| 1.0–2.0 px | Acceptable — reconstruction will work but quality may be reduced |
| > 2.0 px   | Poor — poses are unreliable; reconstruction likely to diverge    |

**Typical range for Gaussian Splatting:** 0.3–0.8 px on well-captured real-world video. Values above 1.0 px are a warning sign, particularly for generated video inputs where inter-frame inconsistency is the most common cause.
