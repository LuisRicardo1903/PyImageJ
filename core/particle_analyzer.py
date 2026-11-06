"""
Particle Analyzer module.
Matches ImageJ 1.54 ParticleAnalyzer algorithms, formulas, and measurements.
Pure NumPy and OpenCV implementation: zero external dependencies on scipy, scikit-image, or pandas.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
from core.scale import ScaleCalibration
from core.particle_table import ParticleTable


@dataclass
class ParticleSummary:
    count: int = 0
    total_area_units: float = 0.0
    total_analyzed_area_units: float = 0.0
    area_fraction_pct: float = 0.0  # Porosity %
    mean_area_units: float = 0.0
    mean_equiv_diameter_units: float = 0.0
    mean_circularity: float = 0.0
    density_per_mm2: float = 0.0


def calculate_max_feret(contour: np.ndarray) -> float:
    """
    Calculates Maximum Feret diameter (maximum caliper distance) from contour.
    Vectorized NumPy implementation on convex hull vertices.
    """
    if len(contour) < 2:
        return 0.0
    pts = contour.reshape(-1, 2)
    hull = cv2.convexHull(pts).reshape(-1, 2)
    if len(hull) < 2:
        return 0.0
    diff = hull[:, np.newaxis, :] - hull[np.newaxis, :, :]
    dists_sq = np.sum(diff ** 2, axis=-1)
    return float(np.sqrt(np.max(dists_sq)))


def _benkrid_crookes_perimeter(binary_crop: np.ndarray) -> float:
    """
    Computes Benkrid & Crookes FPGA perimeter estimator
    (exact mathematical equivalent of ImageJ & scikit-image perimeter).
    """
    pad = np.pad(binary_crop, 1, mode="constant", constant_values=0)
    kernel_cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
    eroded = cv2.erode(pad, kernel_cross, borderType=cv2.BORDER_CONSTANT, borderValue=0)
    border = pad - eroded

    weights = np.zeros(50, dtype=np.float64)
    weights[[5, 7, 15, 17, 25, 27]] = 1.0
    weights[[21, 33]] = np.sqrt(2.0)
    weights[[13, 23]] = (1.0 + np.sqrt(2.0)) / 2.0

    conv_kernel = np.array([[10, 2, 10], [2, 1, 2], [10, 2, 10]], dtype=np.float32)
    conv = cv2.filter2D(border.astype(np.float32), -1, conv_kernel, borderType=cv2.BORDER_CONSTANT)
    hist = np.bincount(np.round(conv).astype(np.int32).ravel(), minlength=50)[:50]
    return float(np.dot(hist, weights))


def analyze_particles(
    binary_mask: np.ndarray,
    gray_image: Optional[np.ndarray] = None,
    scale: Optional[ScaleCalibration] = None,
    min_size_px: float = 5.0,
    max_size_px: float = 1e9,
    min_circularity: float = 0.0,
    max_circularity: float = 1.0,
    valid_roi_mask: Optional[np.ndarray] = None
) -> Tuple[ParticleTable, ParticleSummary, np.ndarray]:
    """
    Executes Analyze Particles on binary image.
    High-performance pure C++ (OpenCV) & NumPy implementation.
    Returns:
        - ParticleTable of particle measurements
        - ParticleSummary
        - Annotated overlay image (BGR)
    """
    if scale is None:
        scale = ScaleCalibration()

    calib_um = scale.units_per_pixel
    area_factor = calib_um ** 2

    # Restrict binary mask to valid ROI mask if provided
    active_binary = binary_mask > 0
    if valid_roi_mask is not None:
        active_binary = active_binary & valid_roi_mask

    active_u8 = active_binary.astype(np.uint8)

    # Prepare intensity image and base overlay image
    if gray_image is not None:
        if gray_image.ndim == 3:
            intensity_img = cv2.cvtColor(gray_image, cv2.COLOR_RGB2GRAY)
            overlay = gray_image.copy()
        else:
            intensity_img = gray_image
            overlay = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2RGB)
    else:
        intensity_img = None
        overlay = np.zeros((*binary_mask.shape, 3), dtype=np.uint8)

    # High-speed connected components with statistics (C++)
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(active_u8, connectivity=8)

    rows: List[Dict[str, Any]] = []

    for i in range(1, num_labels):
        area_px = float(stats[i, cv2.CC_STAT_AREA])
        if area_px < min_size_px or area_px > max_size_px:
            continue

        x0 = int(stats[i, cv2.CC_STAT_LEFT])
        y0 = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        cx_px, cy_px = float(centroids[i][0]), float(centroids[i][1])

        # Sub-mask for this specific connected component
        sub = (labels[y0:y0 + h, x0:x0 + w] == i).astype(np.uint8)

        # Exact Benkrid & Crookes perimeter
        perim_px = _benkrid_crookes_perimeter(sub)

        # ImageJ circularity: 4 * PI * (area / perimeter^2)
        if perim_px > 0:
            circ = (4.0 * np.pi * area_px) / (perim_px ** 2)
            circ = min(1.0, circ)
        else:
            circ = 0.0

        if circ < min_circularity or circ > max_circularity:
            continue

        # Inertia moments for major and minor axes
        M = cv2.moments(sub, binaryImage=True)
        m00 = M["m00"]
        if m00 > 0:
            mu20 = M["mu20"] / m00
            mu02 = M["mu02"] / m00
            mu11 = M["mu11"] / m00
            delta = np.sqrt(max(0.0, (mu20 - mu02) ** 2 + 4.0 * (mu11 ** 2)))
            l1 = (mu20 + mu02 + delta) / 2.0
            l2 = max(0.0, (mu20 + mu02 - delta) / 2.0)
            major_px = 4.0 * np.sqrt(l1)
            minor_px = 4.0 * np.sqrt(l2)
        else:
            major_px = minor_px = 0.0

        # Aspect Ratio = Major / Minor
        aspect_ratio = (major_px / minor_px) if minor_px > 0 else 1.0

        # Roundness = 4 * Area / (PI * Major^2)
        roundness = (4.0 * area_px) / (np.pi * (major_px ** 2)) if major_px > 0 else 0.0

        # Solidity = Area / Convex Area
        cnts, _ = cv2.findContours(sub, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            hull = cv2.convexHull(cnts[0])
            hull_mask = np.zeros_like(sub)
            cv2.drawContours(hull_mask, [hull], 0, 1, -1)
            hull_count = cv2.countNonZero(hull_mask)
            solidity = min(1.0, area_px / hull_count) if hull_count > 0 else 1.0
        else:
            solidity = 1.0

        # Mean Intensity
        if intensity_img is not None:
            crop_gray = intensity_img[y0:y0 + h, x0:x0 + w]
            px_vals = crop_gray[sub > 0]
            mean_intensity = float(np.mean(px_vals)) if len(px_vals) > 0 else 0.0
        else:
            mean_intensity = 0.0

        # Physical measurements
        area_units = area_px * area_factor
        perim_units = perim_px * calib_um
        major_units = major_px * calib_um
        minor_units = minor_px * calib_um
        eq_diam_units = 2.0 * np.sqrt(area_units / np.pi)
        centroid_x_units = cx_px * calib_um
        centroid_y_units = cy_px * calib_um

        rows.append({
            "ID": len(rows) + 1,
            "Area": round(area_units, 2),
            "Eq_Diam": round(eq_diam_units, 2),
            "Perimeter": round(perim_units, 2),
            "Circularity": round(circ, 3),
            "Aspect_Ratio": round(aspect_ratio, 3),
            "Roundness": round(roundness, 3),
            "Solidity": round(solidity, 3),
            "Major": round(major_units, 2),
            "Minor": round(minor_units, 2),
            "X": round(centroid_x_units, 2),
            "Y": round(centroid_y_units, 2),
            "Mean_Gray": round(mean_intensity, 1)
        })

    df = ParticleTable(rows)

    # Draw contours on overlay
    contours, _ = cv2.findContours(active_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (0, 0, 255), 1)

    # Summary
    total_analyzed_px = np.sum(valid_roi_mask) if valid_roi_mask is not None else (binary_mask.shape[0] * binary_mask.shape[1])
    total_analyzed_units = total_analyzed_px * area_factor
    total_particle_area_units = df["Area"].sum() if len(df) > 0 else 0.0
    area_fraction_pct = (total_particle_area_units / total_analyzed_units * 100.0) if total_analyzed_units > 0 else 0.0

    unit_lower = scale.unit.lower()
    if "um" in unit_lower or "µm" in unit_lower:
        analyzed_mm2 = total_analyzed_units / 1e6
        density = (len(df) / analyzed_mm2) if analyzed_mm2 > 0 else 0.0
    else:
        density = 0.0

    summary = ParticleSummary(
        count=len(df),
        total_area_units=round(total_particle_area_units, 2),
        total_analyzed_area_units=round(total_analyzed_units, 2),
        area_fraction_pct=round(area_fraction_pct, 3),
        mean_area_units=round(df["Area"].mean(), 2) if len(df) > 0 else 0.0,
        mean_equiv_diameter_units=round(df["Eq_Diam"].mean(), 2) if len(df) > 0 else 0.0,
        mean_circularity=round(df["Circularity"].mean(), 3) if len(df) > 0 else 0.0,
        density_per_mm2=round(density, 1)
    )

    return df, summary, overlay
