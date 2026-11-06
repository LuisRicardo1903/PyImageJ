"""
Thresholding and binary morphological filters module.
Implements ImageJ AutoThresholder methods and binary processing.
"""

from typing import Tuple, Optional
import cv2
import numpy as np
from scipy import ndimage
from skimage.filters import (
    threshold_otsu,
    threshold_triangle,
    threshold_isodata,
    threshold_li,
    threshold_yen,
    threshold_mean,
    threshold_minimum
)
from skimage.segmentation import watershed
from skimage.feature import peak_local_max


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
    """
    pixels = gray[mask] if mask is not None else gray.ravel()
    if len(pixels) == 0:
        return 128

    m = method.lower()
    try:
        if "otsu" in m:
            val = threshold_otsu(pixels)
        elif "triangle" in m:
            val = threshold_triangle(pixels)
        elif "default" in m or "isodata" in m:
            val = threshold_isodata(pixels)
        elif "li" in m:
            val = threshold_li(pixels)
        elif "yen" in m:
            val = threshold_yen(pixels)
        elif "mean" in m:
            val = threshold_mean(pixels)
        elif "minimum" in m:
            val = threshold_minimum(pixels)
        else:
            val = threshold_otsu(pixels)
        return int(np.clip(val, 0, 255))
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
    bin_bool = binary_mask > 0
    distance = ndimage.distance_transform_edt(bin_bool)
    coords = peak_local_max(distance, min_distance=3, labels=bin_bool)
    mask_peaks = np.zeros(distance.shape, dtype=bool)
    mask_peaks[tuple(coords.T)] = True
    markers, _ = ndimage.label(mask_peaks)
    labels = watershed(-distance, markers, mask=bin_bool)
    return (labels > 0).astype(np.uint8) * 255


def fill_holes(binary_mask: np.ndarray) -> np.ndarray:
    """
    Fills holes inside particles (ImageJ 'Process > Binary > Fill Holes').
    """
    filled = ndimage.binary_fill_holes(binary_mask > 0)
    return (filled.astype(np.uint8)) * 255


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
