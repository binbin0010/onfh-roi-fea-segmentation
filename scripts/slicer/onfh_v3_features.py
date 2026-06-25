"""Geometry, seeded region growing, and research features for ONFH V3.

The functions in this module are deterministic and independent of 3D Slicer.
Reported angular and composite features are research measurements. They are not
validated probabilities, clinical stages, or treatment recommendations.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
from scipy.ndimage import (
    binary_erosion,
    binary_propagation,
    distance_transform_edt,
    generate_binary_structure,
)


@dataclass(frozen=True)
class SphereFit:
    """Algebraic sphere fit expressed in physical right-anterior-superior axes."""

    center_ras_mm: Tuple[float, float, float]
    radius_mm: float
    rms_residual_mm: float
    coordinate_source: str
    surface_point_count: int


def _coordinate_arrays(
    shape: Tuple[int, int, int],
    spacing_zyx: Tuple[float, float, float],
    right_coordinates: Optional[np.ndarray],
    anterior_coordinates: Optional[np.ndarray],
    superior_coordinates: Optional[np.ndarray],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    provided = (
        right_coordinates is not None,
        anterior_coordinates is not None,
        superior_coordinates is not None,
    )
    if any(provided) and not all(provided):
        raise ValueError(
            "right, anterior, and superior coordinate arrays must be provided together."
        )
    if all(provided):
        arrays = tuple(
            np.asarray(value, dtype=np.float32)
            for value in (
                right_coordinates,
                anterior_coordinates,
                superior_coordinates,
            )
        )
        if any(array.shape != shape for array in arrays):
            raise ValueError("Physical coordinate arrays must match the mask shape.")
        return arrays[0], arrays[1], arrays[2], "physical_ras"

    zz, yy, xx = np.indices(shape, dtype=np.float32)
    return (
        xx * float(spacing_zyx[2]),
        yy * float(spacing_zyx[1]),
        zz * float(spacing_zyx[0]),
        "voxel_physical_fallback",
    )


def _surface_mask(mask: np.ndarray) -> np.ndarray:
    structure = generate_binary_structure(3, 1)
    return mask & ~binary_erosion(mask, structure=structure, border_value=0)


def fit_sphere_to_mask(
    mask: np.ndarray,
    spacing_zyx: Tuple[float, float, float],
    right_coordinates: Optional[np.ndarray] = None,
    anterior_coordinates: Optional[np.ndarray] = None,
    superior_coordinates: Optional[np.ndarray] = None,
) -> SphereFit:
    """Fit a sphere to femoral-head surface voxels using physical coordinates."""
    head = np.asarray(mask, dtype=bool)
    if head.ndim != 3 or not np.any(head):
        raise ValueError("mask must be a non-empty three-dimensional array.")
    spacing = tuple(float(value) for value in spacing_zyx)
    if len(spacing) != 3 or any(value <= 0 for value in spacing):
        raise ValueError("spacing_zyx must contain three positive values.")

    right, anterior, superior, source = _coordinate_arrays(
        head.shape,
        spacing,
        right_coordinates,
        anterior_coordinates,
        superior_coordinates,
    )
    surface = _surface_mask(head)
    points = np.column_stack(
        (right[surface], anterior[surface], superior[surface])
    )
    if points.shape[0] < 16:
        raise ValueError("At least 16 surface voxels are required for sphere fitting.")
    if points.shape[0] > 50000:
        indices = np.linspace(0, points.shape[0] - 1, 50000, dtype=int)
        points = points[indices]

    active = np.ones(points.shape[0], dtype=bool)
    solution = None
    for _ in range(3):
        selected = points[active].astype(np.float64, copy=False)
        matrix = np.column_stack(
            (
                2.0 * selected[:, 0],
                2.0 * selected[:, 1],
                2.0 * selected[:, 2],
                np.ones(selected.shape[0], dtype=float),
            )
        )
        target = np.sum(selected**2, axis=1)
        solution, _, rank, _ = np.linalg.lstsq(matrix, target, rcond=None)
        if rank < 4:
            raise ValueError("Femoral-head surface does not support a stable sphere fit.")
        center = solution[:3]
        radius_squared = float(solution[3] + np.dot(center, center))
        if radius_squared <= 0:
            raise ValueError("Sphere fitting produced a non-positive radius.")
        radius = float(np.sqrt(radius_squared))
        residuals = np.abs(np.linalg.norm(points - center, axis=1) - radius)
        cutoff = float(np.percentile(residuals, 95.0))
        updated = residuals <= max(cutoff, 1e-6)
        if np.array_equal(updated, active):
            break
        active = updated

    if solution is None:
        raise RuntimeError("Sphere fitting did not produce a solution.")
    center = solution[:3]
    radius = float(np.sqrt(float(solution[3] + np.dot(center, center))))
    selected_residuals = (
        np.linalg.norm(points[active] - center, axis=1) - radius
    )
    rms = float(np.sqrt(np.mean(selected_residuals**2)))
    return SphereFit(
        center_ras_mm=tuple(float(value) for value in center),
        radius_mm=radius,
        rms_residual_mm=rms,
        coordinate_source=source,
        surface_point_count=int(points.shape[0]),
    )


def build_spherical_geometry(
    mask: np.ndarray,
    spacing_zyx: Tuple[float, float, float],
    right_coordinates: Optional[np.ndarray] = None,
    anterior_coordinates: Optional[np.ndarray] = None,
    superior_coordinates: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Return a sphere fit and interpretable radial geometry maps."""
    head = np.asarray(mask, dtype=bool)
    spacing = tuple(float(value) for value in spacing_zyx)
    right, anterior, superior, source = _coordinate_arrays(
        head.shape,
        spacing,
        right_coordinates,
        anterior_coordinates,
        superior_coordinates,
    )
    fit = fit_sphere_to_mask(
        head,
        spacing,
        right,
        anterior,
        superior,
    )
    if fit.coordinate_source != source:
        fit = SphereFit(
            center_ras_mm=fit.center_ras_mm,
            radius_mm=fit.radius_mm,
            rms_residual_mm=fit.rms_residual_mm,
            coordinate_source=source,
            surface_point_count=fit.surface_point_count,
        )
    center_right, center_anterior, center_superior = (
        np.float32(value) for value in fit.center_ras_mm
    )
    radial_distance = np.sqrt(
        (right - center_right) ** 2
        + (anterior - center_anterior) ** 2
        + (superior - center_superior) ** 2
    )
    sphere_surface_distance = np.abs(fit.radius_mm - radial_distance)
    normalized_radial_depth = np.clip(
        (fit.radius_mm - radial_distance) / max(fit.radius_mm, 1e-6),
        0.0,
        1.0,
    )
    distance_to_mask_surface = distance_transform_edt(head, sampling=spacing)
    return {
        "fit": fit,
        "right_coordinates": right,
        "anterior_coordinates": anterior,
        "superior_coordinates": superior,
        "radial_distance_mm": radial_distance,
        "sphere_surface_distance_mm": sphere_surface_distance * head,
        "distance_to_mask_surface_mm": distance_to_mask_surface,
        "normalized_radial_depth": normalized_radial_depth * head,
    }


def build_anterosuperior_prior(
    mask: np.ndarray,
    geometry: Dict[str, Any],
    anterior_fraction: float,
    superior_fraction: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Build a soft anterosuperior score and a corresponding binary zone."""
    if not 0.0 < anterior_fraction <= 1.0:
        raise ValueError("anterior_fraction must be in (0, 1].")
    if not 0.0 < superior_fraction <= 1.0:
        raise ValueError("superior_fraction must be in (0, 1].")
    head = np.asarray(mask, dtype=bool)
    fit = geometry["fit"]
    radius = np.float32(max(float(fit.radius_mm), 1e-6))
    anterior_unit = (
        np.asarray(geometry["anterior_coordinates"])
        - fit.center_ras_mm[1]
    ) / radius
    superior_unit = (
        np.asarray(geometry["superior_coordinates"])
        - fit.center_ras_mm[2]
    ) / radius

    anterior_start = 1.0 - 2.0 * anterior_fraction
    superior_start = 1.0 - 2.0 * superior_fraction
    anterior_score = np.clip(
        (anterior_unit - anterior_start) / max(1.0 - anterior_start, 1e-6),
        0.0,
        1.0,
    )
    superior_score = np.clip(
        (superior_unit - superior_start) / max(1.0 - superior_start, 1e-6),
        0.0,
        1.0,
    )
    score = superior_score * (0.35 + 0.65 * anterior_score)
    zone = (
        head
        & (superior_unit >= superior_start)
        & (anterior_unit >= anterior_start)
    )
    return score * head, zone


def seeded_region_grow(
    foreground_seed: np.ndarray,
    background_seed: np.ndarray,
    allowed_mask: np.ndarray,
    combined_score: np.ndarray,
    gradient_score: np.ndarray,
    minimum_score: float,
    maximum_gradient: float,
    connectivity: int = 1,
) -> np.ndarray:
    """Propagate foreground seeds through an explainable score/gradient mask."""
    foreground = np.asarray(foreground_seed, dtype=bool)
    background = np.asarray(background_seed, dtype=bool)
    allowed = np.asarray(allowed_mask, dtype=bool)
    score = np.asarray(combined_score, dtype=float)
    gradient = np.asarray(gradient_score, dtype=float)
    shapes = {foreground.shape, background.shape, allowed.shape, score.shape, gradient.shape}
    if len(shapes) != 1 or foreground.ndim != 3:
        raise ValueError("All region-growing arrays must be matching 3D arrays.")
    if connectivity not in (1, 2, 3):
        raise ValueError("connectivity must be 1, 2, or 3.")

    propagation_mask = (
        allowed
        & ~background
        & (score >= float(minimum_score))
        & (gradient <= float(maximum_gradient))
    )
    propagation_mask |= foreground & allowed & ~background
    seeds = foreground & propagation_mask
    if not np.any(seeds):
        return np.zeros_like(foreground, dtype=bool)
    structure = generate_binary_structure(3, connectivity)
    return np.asarray(
        binary_propagation(seeds, structure=structure, mask=propagation_mask),
        dtype=bool,
    )


def _minimal_circular_span_degrees(angles: np.ndarray) -> float:
    finite = np.mod(np.asarray(angles, dtype=float), 360.0)
    finite = finite[np.isfinite(finite)]
    if finite.size <= 1:
        return 0.0
    ordered = np.sort(finite)
    gaps = np.diff(np.concatenate((ordered, [ordered[0] + 360.0])))
    return float(360.0 - np.max(gaps))


def compute_kerboul_like_3d_angles(
    roi: np.ndarray,
    geometry: Dict[str, Any],
    right_coordinates: Optional[np.ndarray] = None,
    anterior_coordinates: Optional[np.ndarray] = None,
    superior_coordinates: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Measure 3D-ROI angular spans in coronal and sagittal projections."""
    lesion = np.asarray(roi, dtype=bool)
    if not np.any(lesion):
        return {
            "coronal_span_deg": 0.0,
            "sagittal_span_deg": 0.0,
            "combined_angle_deg": 0.0,
        }
    right = np.asarray(
        geometry["right_coordinates"] if right_coordinates is None else right_coordinates,
    )
    anterior = np.asarray(
        geometry["anterior_coordinates"]
        if anterior_coordinates is None
        else anterior_coordinates,
    )
    superior = np.asarray(
        geometry["superior_coordinates"]
        if superior_coordinates is None
        else superior_coordinates,
    )
    if right.shape != lesion.shape or anterior.shape != lesion.shape or superior.shape != lesion.shape:
        raise ValueError("ROI and physical coordinate arrays must match.")
    center_right, center_anterior, center_superior = geometry["fit"].center_ras_mm
    right_offset = right[lesion].astype(float, copy=False) - center_right
    anterior_offset = anterior[lesion].astype(float, copy=False) - center_anterior
    superior_offset = superior[lesion].astype(float, copy=False) - center_superior

    coronal_valid = np.hypot(right_offset, superior_offset) > 1e-6
    sagittal_valid = np.hypot(anterior_offset, superior_offset) > 1e-6
    coronal_angles = np.degrees(
        np.arctan2(right_offset[coronal_valid], superior_offset[coronal_valid])
    )
    sagittal_angles = np.degrees(
        np.arctan2(anterior_offset[sagittal_valid], superior_offset[sagittal_valid])
    )
    coronal_span = _minimal_circular_span_degrees(coronal_angles)
    sagittal_span = _minimal_circular_span_degrees(sagittal_angles)
    return {
        "coronal_span_deg": coronal_span,
        "sagittal_span_deg": sagittal_span,
        "combined_angle_deg": coronal_span + sagittal_span,
    }


def compute_zone_involvement(
    roi: np.ndarray,
    subchondral_band: np.ndarray,
    weight_bearing_zone: np.ndarray,
) -> Dict[str, float]:
    """Return the percentage of each anatomical zone occupied by the ROI."""
    lesion = np.asarray(roi, dtype=bool)
    subchondral = np.asarray(subchondral_band, dtype=bool)
    weight_bearing = np.asarray(weight_bearing_zone, dtype=bool)
    if lesion.shape != subchondral.shape or lesion.shape != weight_bearing.shape:
        raise ValueError("ROI and anatomical zones must have matching shapes.")

    def occupied(zone: np.ndarray) -> float:
        denominator = int(zone.sum())
        return (
            float((lesion & zone).sum()) / float(denominator) * 100.0
            if denominator
            else 0.0
        )

    return {
        "subchondral_involvement_percent": occupied(subchondral),
        "weight_bearing_involvement_percent": occupied(weight_bearing),
    }


def compute_experimental_collapse_feature_score(
    subchondral_involvement_percent: float,
    weight_bearing_involvement_percent: float,
    combined_angle_deg: float,
) -> float:
    """Return an uncalibrated 0-100 feature composite for research analysis."""
    subchondral = np.clip(float(subchondral_involvement_percent) / 100.0, 0.0, 1.0)
    weight_bearing = np.clip(
        float(weight_bearing_involvement_percent) / 100.0, 0.0, 1.0
    )
    angular = np.clip(float(combined_angle_deg) / 360.0, 0.0, 1.0)
    return float(np.clip(100.0 * (0.40 * subchondral + 0.40 * weight_bearing + 0.20 * angular), 0.0, 100.0))
