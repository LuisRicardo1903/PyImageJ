"""
Particle Analyzer module.
Matches ImageJ 1.54 ParticleAnalyzer algorithms, formulas, and measurements.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
import cv2
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist
from skimage.measure import label, regionprops
from core.scale import ScaleCalibration


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
    """
    if len(contour) < 2:
        return 0.0
    pts = contour.reshape(-1, 2)
    hull = cv2.convexHull(pts).reshape(-1, 2)
    if len(hull) < 2:
        return 0.0
    dists = pdist(hull)
    return float(np.max(dists)) if len(dists) > 0 else 0.0


def analyze_particles(
    binary_mask: np.ndarray,
    gray_image: Optional[np.ndarray] = None,
    scale: Optional[ScaleCalibration] = None,
    min_size_px: float = 5.0,
    max_size_px: float = 1e9,
    min_circularity: float = 0.0,
    max_circularity: float = 1.0,
    valid_roi_mask: Optional[np.ndarray] = None
) -> Tuple[pd.DataFrame, ParticleSummary, np.ndarray]:
    """
    Executes Analyze Particles on binary image.
    Returns:
        - DataFrame of particle measurements
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

    # Find connected components / contours
    lbl = label(active_binary)
    props = regionprops(lbl, intensity_image=intensity_img)

    # Prepare contours for drawing and feret
    contours, _ = cv2.findContours(active_binary.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rows: List[Dict[str, Any]] = []

    for p in props:
        area_px = p.area
        if area_px < min_size_px or area_px > max_size_px:
            continue

        perim_px = p.perimeter
        # ImageJ circularity: 4 * PI * (area / perimeter^2)
        if perim_px > 0:
            circ = (4.0 * np.pi * area_px) / (perim_px ** 2)
            circ = min(1.0, circ)
        else:
            circ = 0.0

        if circ < min_circularity or circ > max_circularity:
            continue

        # Physical measurements
        area_units = area_px * area_factor
        perim_units = perim_px * calib_um
        major_units = p.major_axis_length * calib_um
        minor_units = p.minor_axis_length * calib_um
        eq_diam_units = 2.0 * np.sqrt(area_units / np.pi)

        # Aspect Ratio = Major / Minor
        aspect_ratio = (p.major_axis_length / p.minor_axis_length) if p.minor_axis_length > 0 else 1.0

        # Roundness = 4 * Area / (PI * Major^2)
        roundness = (4.0 * area_px) / (np.pi * (p.major_axis_length ** 2)) if p.major_axis_length > 0 else 0.0

        # Solidity = Area / Convex Area
        solidity = p.solidity

        # Centroid
        centroid_y_px, centroid_x_px = p.centroid
        centroid_x_units = centroid_x_px * calib_um
        centroid_y_units = centroid_y_px * calib_um

        # Mean Intensity
        if intensity_img is not None:
            if np.isscalar(p.mean_intensity):
                mean_intensity = float(p.mean_intensity)
            else:
                mean_intensity = float(np.mean(p.mean_intensity))
        else:
            mean_intensity = 0.0

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

    df = pd.DataFrame(rows)

    # Draw contours and IDs on overlay
    cv2.drawContours(overlay, contours, -1, (0, 0, 255), 1)  # Red outline

    # Summary
    total_analyzed_px = np.sum(valid_roi_mask) if valid_roi_mask is not None else (binary_mask.shape[0] * binary_mask.shape[1])
    total_analyzed_units = total_analyzed_px * area_factor
    total_particle_area_units = df["Area"].sum() if len(df) > 0 else 0.0
    area_fraction_pct = (total_particle_area_units / total_analyzed_units * 100.0) if total_analyzed_units > 0 else 0.0

    # Density per mm2 (1 mm2 = 1e6 um2 if unit is um)
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
