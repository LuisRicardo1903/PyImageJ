"""
Scale calibration module.
Handles spatial calibration (pixels to physical units like µm, mm, nm)
and automatic scale-bar detection from micrographs.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import cv2
import numpy as np


@dataclass
class ScaleCalibration:
    pixels: float = 1.0
    known_distance: float = 1.0
    unit: str = "px"

    @property
    def units_per_pixel(self) -> float:
        if self.pixels <= 0:
            return 1.0
        return self.known_distance / self.pixels

    @property
    def pixels_per_unit(self) -> float:
        if self.known_distance <= 0:
            return 1.0
        return self.pixels / self.known_distance

    def to_units_length(self, length_px: float) -> float:
        return length_px * self.units_per_pixel

    def to_units_area(self, area_px: float) -> float:
        return area_px * (self.units_per_pixel ** 2)


def auto_detect_scale_bar(image_bgr: np.ndarray, known_distance: float = 100.0, unit: str = "µm") -> Tuple[Optional[ScaleCalibration], Optional[Tuple[int, int, int, int]]]:
    """
    Automatically detects a scale bar box in a micrograph (typically bottom-right or bottom-left).
    Returns (ScaleCalibration, (min_x, min_y, max_x, max_y)) or (None, None).
    """
    if image_bgr is None or image_bgr.ndim < 2:
        return None, None

    h, w = image_bgr.shape[:2]
    # Check for white box in the bottom regions
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if image_bgr.ndim == 3 else image_bgr.copy()
    
    if image_bgr.ndim == 3:
        white_box = (image_bgr[:, :, 0] > 240) & (image_bgr[:, :, 1] > 240) & (image_bgr[:, :, 2] > 240)
    else:
        white_box = gray > 240

    coords = np.argwhere(white_box)
    if len(coords) < 100:
        return None, None

    min_y, min_x = coords.min(axis=0)
    max_y, max_x = coords.max(axis=0)

    # Box must be in bottom half of image and reasonable size
    box_w = max_x - min_x + 1
    box_h = max_y - min_y + 1
    if min_y < h * 0.4 or box_w < 30 or box_h < 15 or box_w > w * 0.6 or box_h > h * 0.5:
        return None, None

    box_crop = gray[min_y:max_y, min_x:max_x]
    black_pixels = (box_crop < 60).astype(np.uint8)
    h_proj = black_pixels.sum(axis=1)

    if h_proj.max() < 10:
        return None, None

    bar_y = int(np.argmax(h_proj))
    bar_indices = np.where(black_pixels[bar_y, :] > 0)[0]
    if len(bar_indices) < 10:
        return None, None

    bar_len_px = float(bar_indices[-1] - bar_indices[0] + 1)
    calib = ScaleCalibration(pixels=bar_len_px, known_distance=known_distance, unit=unit)
    bbox = (int(min_x), int(min_y), int(max_x), int(max_y))
    return calib, bbox
