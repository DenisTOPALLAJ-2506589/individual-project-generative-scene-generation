import cv2
import numpy as np
import random


def extract_random_frames(video_path: str, n_frames: int = 10) -> list[np.ndarray]:
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if total_frames < n_frames:
        raise ValueError(
            f"Video only has {total_frames} frames, cannot sample {n_frames}"
        )

    indices = sorted(random.sample(range(total_frames), n_frames))
    frames = []

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()
    return frames


def blur_score(frame_bgr: np.ndarray) -> float:
    """Higher = sharper. Uses Laplacian variance."""
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def brightness_score(frame_bgr: np.ndarray) -> float:
    """Mean brightness 0-255. ~100-180 is a well-exposed frame."""
    return float(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY).mean())


def contrast_score(frame_bgr: np.ndarray) -> float:
    """Std deviation of brightness. Higher = more contrast."""
    return float(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY).std())


def score_frames(frames: list[np.ndarray]) -> dict:
    blur_scores = []
    brightness_scores = []
    contrast_scores = []

    for i, frame in enumerate(frames):
        b = blur_score(frame)
        br = brightness_score(frame)
        c = contrast_score(frame)

        blur_scores.append(b)
        brightness_scores.append(br)
        contrast_scores.append(c)

        print(
            f"  Frame {i+1:02d} — Blur: {b:7.2f}  Brightness: {br:.1f}  Contrast: {c:.2f}"
        )

    return {
        "blur_mean": np.mean(blur_scores),
        "blur_std": np.std(blur_scores),
        "brightness_mean": np.mean(brightness_scores),
        "brightness_std": np.std(brightness_scores),
        "contrast_mean": np.mean(contrast_scores),
        "contrast_std": np.std(contrast_scores),
    }


frames = extract_random_frames("input.mp4", n_frames=10)
print(f"Sampled {len(frames)} frames\n")

results = score_frames(frames)

print(f"\nAverage scores over {len(frames)} frames:")
print(
    f"  Blur:       {results['blur_mean']:.2f} ± {results['blur_std']:.2f}  (higher = sharper, >100 is good)"
)
print(
    f"  Brightness: {results['brightness_mean']:.1f} ± {results['brightness_std']:.1f}  (100–180 is well exposed)"
)
print(
    f"  Contrast:   {results['contrast_mean']:.2f} ± {results['contrast_std']:.2f}  (higher = more detail)"
)
