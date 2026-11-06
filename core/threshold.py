"""
Thresholding and binary morphological filters module.
Pure NumPy and OpenCV implementation: 100% independent of scipy and scikit-image.
Matches ImageJ AutoThresholder methods and binary processing at high C++ speeds.
"""

from typing import Optional
import cv2
import numpy as np


THRESHOLD_METHODS = [
    "Otsu",
    "Triangle",
    "Default (IsoData)",
    "Li",
    "Yen",
    "Mean",
    "Minimum",
    "Manual"
]


def calculate_threshold(
    gray: np.ndarray,
    method: str = "Otsu",
    mask: Optional[np.ndarray] = None
) -> int:
    """
    Computes threshold cut-off value using specified algorithm.
    Optimized with pure OpenCV and vectorized NumPy (zero external dependencies).
    """
    if mask is not None:
        pixels = gray[mask]
    else:
        pixels = gray.ravel()

    if len(pixels) == 0:
        return 128

    m = method.lower()
    try:
        if "otsu" in m:
            val, _ = cv2.threshold(pixels.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return int(np.clip(round(val), 0, 255))

        elif "triangle" in m:
            val, _ = cv2.threshold(pixels.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_TRIANGLE)
            return int(np.clip(round(val), 0, 255))

        elif "default" in m or "isodata" in m:
            # Ridler-Calvard iterative selection (ImageJ Default IsoData)
            hist = np.bincount(pixels.astype(np.uint8).ravel(), minlength=256).astype(np.float64)
            centers = np.arange(256)
            t = int(np.mean(pixels))
            for _ in range(100):
                w1 = np.sum(hist[:t])
                w2 = np.sum(hist[t:])
                if w1 == 0 or w2 == 0:
                    break
                m1 = np.sum(hist[:t] * centers[:t]) / w1
                m2 = np.sum(hist[t:] * centers[t:]) / w2
                t_next = int(round((m1 + m2) / 2.0))
                if t_next == t:
                    break
                t = t_next
            return int(np.clip(t, 0, 255))

        elif "li" in m:
            # Li's Minimum Cross Entropy thresholding
            hist = np.bincount(pixels.astype(np.uint8).ravel(), minlength=256).astype(np.float64)
            centers = np.arange(256, dtype=np.float64)
            t = float(np.mean(pixels))
            for _ in range(100):
                t_int = int(round(t))
                w0 = np.sum(hist[:t_int])
                w1 = np.sum(hist[t_int:])
                if w0 == 0 or w1 == 0:
                    break
                m0 = np.sum(hist[:t_int] * centers[:t_int]) / w0
                m1 = np.sum(hist[t_int:] * centers[t_int:]) / w1
                if m0 <= 0 or m1 <= 0:
                    break
                t_next = (m0 - m1) / (np.log(m0) - np.log(m1))
                if abs(t_next - t) < 0.5:
                    break
                t = t_next
            return int(np.clip(round(t), 0, 255))

        elif "yen" in m:
            # Yen's maximum correlation algorithm
            hist = np.bincount(pixels.astype(np.uint8).ravel(), minlength=256).astype(np.float64)
            prob = hist / max(1.0, np.sum(hist))
            cum_prob = np.cumsum(prob)
            p_sq = prob ** 2
            cum_p_sq = np.cumsum(p_sq)
            total_p_sq = cum_p_sq[-1]
            crit = np.zeros(256)
            for t_idx in range(1, 255):
                w0 = cum_p_sq[t_idx]
                w1 = total_p_sq - w0
                p0 = cum_prob[t_idx]
                p1 = 1.0 - p0
                if w0 > 0 and w1 > 0 and p0 > 0 and p1 > 0:
                    crit[t_idx] = -np.log(w0 * w1) + 2.0 * (np.log(p0) + np.log(p1))
            return int(np.argmax(crit))

        elif "mean" in m:
            return int(np.clip(round(np.mean(pixels)), 0, 255))

        elif "minimum" in m:
            # Smooth histogram and find local minimum between the two main peaks
            hist = np.bincount(pixels.astype(np.uint8).ravel(), minlength=256).astype(np.float32)
            p = hist.copy()
            kernel = np.array([1, 2, 1], dtype=np.float32) / 4.0
            for _ in range(1000):
                peaks = [i for i in range(1, 255) if p[i - 1] < p[i] and p[i] > p[i + 1]]
                if len(peaks) <= 2:
                    break
                p = np.convolve(p, kernel, mode="same")
            if len(peaks) == 2:
                return int(peaks[0] + np.argmin(p[peaks[0]:peaks[1]]))
            val, _ = cv2.threshold(pixels.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return int(np.clip(round(val), 0, 255))

        else:
            val, _ = cv2.threshold(pixels.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return int(np.clip(round(val), 0, 255))

    except Exception:
        return 128


def apply_threshold(
    gray: np.ndarray,
    threshold_val: int,
    dark_objects: bool = True,
    mask: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Binarizes image given threshold value.
    If dark_objects=True (typical for pores/defects on metal), pixels < threshold_val are foreground.
    Returns uint8 binary mask where foreground=255, background=0.
    """
    if dark_objects:
        bin_img = (gray < threshold_val)
    else:
        bin_img = (gray >= threshold_val)

    if mask is not None:
        bin_img = bin_img & mask

    return (bin_img.astype(np.uint8)) * 255


def binary_watershed(binary_mask: np.ndarray) -> np.ndarray:
    """
    Applies distance-transform watershed separation on touching binary particles
    (Equivalent to ImageJ 'Process > Binary > Watershed').
    """
    if np.sum(binary_mask) == 0:
        return binary_mask.copy()

    bin_u8 = (binary_mask > 0).astype(np.uint8) * 255
    dist = cv2.distanceTransform(bin_u8, cv2.DIST_L2, 5)

    # Peak detection using dilation max-filter
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated = cv2.dilate(dist, kernel)
    peaks = (dist == dilated) & (dist > 1.5)

    num_peaks, markers = cv2.connectedComponents(peaks.astype(np.uint8))
    if num_peaks <= 2:
        return bin_u8

    img_3ch = cv2.cvtColor(bin_u8, cv2.COLOR_GRAY2BGR)
    markers_32 = markers.astype(np.int32)
    cv2.watershed(img_3ch, markers_32)

    result = bin_u8.copy()
    result[markers_32 == -1] = 0
    return result


def fill_holes(binary_mask: np.ndarray) -> np.ndarray:
    """
    Fills holes inside particles (ImageJ 'Process > Binary > Fill Holes').
    High-speed OpenCV flood-fill implementation.
    """
    if np.sum(binary_mask) == 0:
        return binary_mask.copy()

    im_in = (binary_mask > 0).astype(np.uint8) * 255
    h, w = im_in.shape[:2]
    padded = np.pad(im_in, 1, mode="constant", constant_values=0)
    flood_mask = np.zeros((h + 4, w + 4), np.uint8)
    cv2.floodFill(padded, flood_mask, (0, 0), 255)
    unpadded_flood = padded[1:-1, 1:-1]
    return im_in | cv2.bitwise_not(unpadded_flood)


def morphology_operation(binary_mask: np.ndarray, op: str = "open", kernel_size: int = 3) -> np.ndarray:
    """
    Applies morphological operation: erode, dilate, open, close.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    op_lower = op.lower()
    if op_lower == "erode":
        return cv2.erode(binary_mask, kernel, iterations=1)
    elif op_lower == "dilate":
        return cv2.dilate(binary_mask, kernel, iterations=1)
    elif op_lower == "open":
        return cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, kernel)
    elif op_lower == "close":
        return cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)
    return binary_mask
