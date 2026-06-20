"""Slicer-independent anatomy-adaptive ONFH ROI initialization.

This module provides deterministic NumPy/SciPy functions that can be tested
without 3D Slicer. It initializes an expert-reviewable lesion-related ROI; it
does not provide autonomous diagnosis or clinical staging.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Tuple

import numpy as np
from scipy.ndimage import (
    binary_closing,
    binary_fill_holes,
    distance_transform_edt,
    label,
)


@dataclass(frozen=True)
class AdaptiveSegmentationConfig:
    """Configuration for anatomy-adaptive feature extraction and fusion."""

    low_percentile: float = 30.0
    high_percentile: float = 85.0
    reference_min_hu: float = -100.0
    reference_max_hu: float = 1000.0
    low_hu_ceiling: float = 400.0
    minimum_low_contrast_hu: float = 40.0
    sclerotic_hu_floor: float = 500.0
    sclerotic_hu_ceiling: float = 1800.0
    cortical_exclusion_hu: float = 1500.0
    cortical_margin_mm: float = 1.0
    subchondral_depth_mm: float = 8.0
    superior_weight_bearing_fraction: float = 0.45
    rim_proximity_mm: float = 6.0
    low_density_weight: float = 0.45
    rim_proximity_weight: float = 0.20
    subchondral_weight: float = 0.20
    weight_bearing_weight: float = 0.15
    score_threshold: float = 0.52
    seed_score_threshold: float = 0.58
    rim_envelope_threshold: float = 0.25
    closing_radius_mm: float = 2.0
    min_component_volume_mm3: float = 100.0
    minimum_reference_voxels: int = 500
    minimum_rim_volume_mm3: float = 20.0
    roi_ratio_low_percent: float = 0.5
    roi_ratio_high_percent: float = 65.0
    inferior_zone_fraction: float = 0.25
    inferior_roi_warning_fraction: float = 0.10
    fragmented_component_warning_count: int = 3

    def validate(self) -> None:
        percentile_values = (self.low_percentile, self.high_percentile)
        if not all(0.0 < value < 100.0 for value in percentile_values):
            raise ValueError("Percentiles must be between 0 and 100.")
        if self.low_percentile >= self.high_percentile:
            raise ValueError("low_percentile must be less than high_percentile.")
        if self.cortical_margin_mm < 0 or self.subchondral_depth_mm <= 0:
            raise ValueError("Anatomical distances must be positive.")
        if self.subchondral_depth_mm <= self.cortical_margin_mm:
            raise ValueError("subchondral_depth_mm must exceed cortical_margin_mm.")
        if not 0.0 < self.superior_weight_bearing_fraction <= 1.0:
            raise ValueError("superior_weight_bearing_fraction must be in (0, 1].")
        weights = (
            self.low_density_weight,
            self.rim_proximity_weight,
            self.subchondral_weight,
            self.weight_bearing_weight,
        )
        if not np.isclose(sum(weights), 1.0):
            raise ValueError("Feature-fusion weights must sum to 1.0.")


@dataclass
class SegmentationResult:
    """Masks and reportable metadata produced by the v3 core."""

    masks: Dict[str, np.ndarray]
    thresholds: Dict[str, float]
    metrics: Dict[str, Any]
    qc: Dict[str, Any]
    config: AdaptiveSegmentationConfig


def _validate_inputs(
    hu_volume: np.ndarray,
    femoral_head_mask: np.ndarray,
    spacing_zyx: Tuple[float, float, float],
    superior_coordinates: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, Tuple[float, float, float], np.ndarray]:
    hu = np.asarray(hu_volume, dtype=float)
    head = np.asarray(femoral_head_mask, dtype=bool)
    superior = np.asarray(superior_coordinates, dtype=float)
    spacing = tuple(float(value) for value in spacing_zyx)

    if hu.ndim != 3:
        raise ValueError("hu_volume must be a three-dimensional array.")
    if head.shape != hu.shape or superior.shape != hu.shape:
        raise ValueError("HU, femoral-head, and superior-coordinate arrays must match.")
    if len(spacing) != 3 or any(value <= 0 for value in spacing):
        raise ValueError("spacing_zyx must contain three positive values.")
    if not np.any(head):
        raise ValueError("femoral_head_mask is empty.")
    return hu, head, spacing, superior


def _ellipsoidal_structure(
    spacing_zyx: Tuple[float, float, float], radius_mm: float
) -> np.ndarray:
    if radius_mm <= 0:
        return np.ones((1, 1, 1), dtype=bool)
    extents = [max(1, int(np.ceil(radius_mm / value))) for value in spacing_zyx]
    zz, yy, xx = np.ogrid[
        -extents[0] : extents[0] + 1,
        -extents[1] : extents[1] + 1,
        -extents[2] : extents[2] + 1,
    ]
    distance_squared = (
        (zz * spacing_zyx[0]) ** 2
        + (yy * spacing_zyx[1]) ** 2
        + (xx * spacing_zyx[2]) ** 2
    )
    return distance_squared <= radius_mm**2


def _component_filter(
    candidate: np.ndarray,
    seed: np.ndarray,
    voxel_volume_mm3: float,
    minimum_volume_mm3: float,
) -> Tuple[np.ndarray, np.ndarray]:
    labels, component_count = label(candidate)
    kept = np.zeros_like(candidate, dtype=bool)
    removed = np.zeros_like(candidate, dtype=bool)

    for component_id in range(1, component_count + 1):
        component = labels == component_id
        volume_mm3 = float(component.sum()) * voxel_volume_mm3
        intersects_seed = bool(np.any(component & seed))
        if volume_mm3 >= minimum_volume_mm3 and intersects_seed:
            kept |= component
        else:
            removed |= component
    return kept, removed


def _component_count(mask: np.ndarray) -> int:
    _, count = label(mask)
    return int(count)


def _volume_mm3(mask: np.ndarray, spacing_zyx: Tuple[float, float, float]) -> float:
    return float(np.asarray(mask, dtype=bool).sum()) * float(np.prod(spacing_zyx))


def _normalized_superior_score(
    superior_coordinates: np.ndarray,
    femoral_head_mask: np.ndarray,
    superior_fraction: float,
) -> Tuple[np.ndarray, np.ndarray]:
    values = superior_coordinates[femoral_head_mask]
    minimum = float(np.min(values))
    maximum = float(np.max(values))
    span = maximum - minimum
    if span <= 0:
        normalized = np.zeros_like(superior_coordinates, dtype=float)
    else:
        normalized = np.clip((superior_coordinates - minimum) / span, 0.0, 1.0)

    start = 1.0 - superior_fraction
    score = np.clip((normalized - start) / max(superior_fraction, 1e-6), 0.0, 1.0)
    zone = femoral_head_mask & (normalized >= start)
    return score * femoral_head_mask, zone


def evaluate_qc(
    femoral_head_mask: np.ndarray,
    final_roi: np.ndarray,
    low_density_core: np.ndarray,
    sclerotic_rim: np.ndarray,
    superior_coordinates: np.ndarray,
    spacing_zyx: Tuple[float, float, float],
    reference_voxel_count: int,
    config: AdaptiveSegmentationConfig,
) -> Dict[str, Any]:
    """Evaluate explainable software QC without making a diagnosis."""
    head = np.asarray(femoral_head_mask, dtype=bool)
    roi = np.asarray(final_roi, dtype=bool)
    low = np.asarray(low_density_core, dtype=bool)
    rim = np.asarray(sclerotic_rim, dtype=bool)
    superior = np.asarray(superior_coordinates, dtype=float)
    voxel_volume = float(np.prod(spacing_zyx))

    findings = []

    def add(severity: str, code: str, message: str) -> None:
        findings.append({"severity": severity, "code": code, "message": message})

    head_volume = float(head.sum()) * voxel_volume
    roi_volume = float(roi.sum()) * voxel_volume
    ratio = roi_volume / head_volume * 100.0 if head_volume else 0.0
    component_count = _component_count(roi)

    head_superior = superior[head]
    superior_min = float(np.min(head_superior))
    superior_max = float(np.max(head_superior))
    inferior_cut = superior_min + (
        superior_max - superior_min
    ) * config.inferior_zone_fraction
    inferior_zone = head & (superior <= inferior_cut)
    inferior_roi_fraction = (
        float((roi & inferior_zone).sum()) / float(roi.sum()) if np.any(roi) else 0.0
    )

    if np.any(roi & ~head):
        add("ERROR", "ROI_OUTSIDE_HEAD", "Final ROI extends outside the femoral-head mask.")
    if reference_voxel_count < config.minimum_reference_voxels:
        add(
            "ERROR",
            "REFERENCE_INSUFFICIENT",
            "Insufficient cancellous reference voxels for stable adaptive thresholds.",
        )
    if roi_volume == 0:
        add("WARNING", "ROI_EMPTY", "No final ROI was generated; expert review is required.")
    elif ratio < config.roi_ratio_low_percent:
        add(
            "WARNING",
            "ROI_RATIO_LOW",
            "The lesion-related ROI occupies an unusually small fraction of the head.",
        )
    if ratio > config.roi_ratio_high_percent:
        add(
            "WARNING",
            "ROI_RATIO_HIGH",
            "The lesion-related ROI occupies an unusually large fraction of the head.",
        )
    if _volume_mm3(rim, spacing_zyx) < config.minimum_rim_volume_mm3:
        add(
            "WARNING",
            "RIM_EVIDENCE_WEAK",
            "Sclerotic-rim evidence is weak or absent on CT.",
        )
    if not np.any(low):
        add(
            "WARNING",
            "LOW_DENSITY_SEED_ABSENT",
            "No low-density seed was identified inside the anatomical prior.",
        )
    if component_count > config.fragmented_component_warning_count:
        add(
            "WARNING",
            "ROI_FRAGMENTED",
            "The final ROI contains more connected components than expected.",
        )
    if inferior_roi_fraction > config.inferior_roi_warning_fraction:
        add(
            "WARNING",
            "INFERIOR_EXTENSION",
            "A substantial fraction of the ROI extends into the inferior head region.",
        )

    status = "FAIL" if any(x["severity"] == "ERROR" for x in findings) else (
        "REVIEW" if findings else "PASS"
    )
    return {
        "status": status,
        "findings": findings,
        "component_count": component_count,
        "inferior_roi_fraction": inferior_roi_fraction,
        "reference_voxel_count": int(reference_voxel_count),
    }


def segment_onfh_roi(
    hu_volume: np.ndarray,
    femoral_head_mask: np.ndarray,
    spacing_zyx: Tuple[float, float, float],
    superior_coordinates: np.ndarray,
    config: AdaptiveSegmentationConfig = AdaptiveSegmentationConfig(),
) -> SegmentationResult:
    """Initialize an explainable ONFH lesion-related ROI."""
    config.validate()
    hu, head, spacing, superior = _validate_inputs(
        hu_volume, femoral_head_mask, spacing_zyx, superior_coordinates
    )
    finite = np.isfinite(hu)
    voxel_volume = float(np.prod(spacing))
    distance_inside = distance_transform_edt(head, sampling=spacing)

    cortical_margin = head & (distance_inside <= config.cortical_margin_mm)
    analysis_mask = (
        head
        & finite
        & ~cortical_margin
        & (hu < config.cortical_exclusion_hu)
        & (hu >= config.reference_min_hu)
    )
    reference_mask = (
        analysis_mask
        & (hu >= config.reference_min_hu)
        & (hu <= config.reference_max_hu)
    )
    reference_values = hu[reference_mask]
    if reference_values.size < config.minimum_reference_voxels:
        raise ValueError(
            "Insufficient cancellous reference voxels for adaptive segmentation: "
            f"{reference_values.size} < {config.minimum_reference_voxels}."
        )

    reference_median = float(np.median(reference_values))
    percentile_low = float(np.percentile(reference_values, config.low_percentile))
    percentile_high = float(np.percentile(reference_values, config.high_percentile))
    low_threshold = min(
        percentile_low,
        config.low_hu_ceiling,
        reference_median - config.minimum_low_contrast_hu,
    )
    low_threshold = max(low_threshold, config.reference_min_hu)
    sclerotic_threshold = max(percentile_high, config.sclerotic_hu_floor)
    sclerotic_threshold = min(sclerotic_threshold, config.sclerotic_hu_ceiling)

    low_density_core = analysis_mask & (hu <= low_threshold)
    sclerotic_rim = (
        head
        & finite
        & (hu >= sclerotic_threshold)
        & (hu <= config.sclerotic_hu_ceiling)
    )

    low_denominator = max(reference_median - low_threshold, 1.0)
    low_score = np.clip((reference_median - hu) / low_denominator, 0.0, 1.0)
    low_score *= analysis_mask

    if np.any(sclerotic_rim):
        distance_to_rim = distance_transform_edt(~sclerotic_rim, sampling=spacing)
        rim_proximity_score = np.clip(
            1.0 - distance_to_rim / config.rim_proximity_mm, 0.0, 1.0
        )
    else:
        rim_proximity_score = np.zeros_like(hu, dtype=float)
    rim_proximity_score *= analysis_mask

    subchondral_score = np.clip(
        (config.subchondral_depth_mm - distance_inside)
        / (config.subchondral_depth_mm - config.cortical_margin_mm),
        0.0,
        1.0,
    )
    subchondral_score *= analysis_mask
    subchondral_band = analysis_mask & (
        distance_inside <= config.subchondral_depth_mm
    )

    weight_bearing_score, weight_bearing_zone = _normalized_superior_score(
        superior, head, config.superior_weight_bearing_fraction
    )
    weight_bearing_score *= analysis_mask

    combined_score = (
        config.low_density_weight * low_score
        + config.rim_proximity_weight * rim_proximity_score
        + config.subchondral_weight * subchondral_score
        + config.weight_bearing_weight * weight_bearing_score
    )
    candidate_envelope = analysis_mask & (
        low_density_core
        | (rim_proximity_score >= config.rim_envelope_threshold)
    )
    candidate = candidate_envelope & (combined_score >= config.score_threshold)
    seed = low_density_core & (combined_score >= config.seed_score_threshold)

    retained, removed = _component_filter(
        candidate,
        seed,
        voxel_volume,
        config.min_component_volume_mm3,
    )
    structure = _ellipsoidal_structure(spacing, config.closing_radius_mm)
    refined = binary_closing(retained, structure=structure)
    refined = binary_fill_holes(refined)
    refined &= analysis_mask
    final_roi, removed_after_refinement = _component_filter(
        refined,
        refined,
        voxel_volume,
        config.min_component_volume_mm3,
    )
    removed |= removed_after_refinement

    head_values = superior[head]
    inferior_cut = float(np.min(head_values)) + (
        float(np.max(head_values)) - float(np.min(head_values))
    ) * config.inferior_zone_fraction
    inferior_warning = final_roi & (superior <= inferior_cut)
    warning_region = (removed | inferior_warning) & head

    volumes = {
        "femoral_head_mm3": _volume_mm3(head, spacing),
        "low_density_core_mm3": _volume_mm3(low_density_core, spacing),
        "sclerotic_rim_mm3": _volume_mm3(sclerotic_rim, spacing),
        "final_roi_mm3": _volume_mm3(final_roi, spacing),
        "qc_warning_region_mm3": _volume_mm3(warning_region, spacing),
    }
    roi_ratio = (
        volumes["final_roi_mm3"] / volumes["femoral_head_mm3"] * 100.0
        if volumes["femoral_head_mm3"]
        else 0.0
    )
    qc = evaluate_qc(
        femoral_head_mask=head,
        final_roi=final_roi,
        low_density_core=low_density_core,
        sclerotic_rim=sclerotic_rim,
        superior_coordinates=superior,
        spacing_zyx=spacing,
        reference_voxel_count=int(reference_values.size),
        config=config,
    )
    metrics = {
        **volumes,
        "roi_to_head_percent": roi_ratio,
        "retained_component_count": _component_count(final_roi),
        "reference_voxel_count": int(reference_values.size),
        "candidate_voxel_count": int(candidate.sum()),
        "seed_voxel_count": int(seed.sum()),
    }
    masks = {
        "FEMORAL_HEAD": head,
        "LOW_DENSITY_CORE": low_density_core,
        "SCLEROTIC_RIM": sclerotic_rim,
        "SUBCHONDRAL_BAND": subchondral_band,
        "WEIGHT_BEARING_ZONE": weight_bearing_zone,
        "NECROSIS_ROI_FINAL": final_roi,
        "QC_WARNING_REGION": warning_region,
    }
    thresholds = {
        "low_hu": float(low_threshold),
        "sclerotic_hu": float(sclerotic_threshold),
        "reference_median_hu": reference_median,
        "reference_low_percentile_hu": percentile_low,
        "reference_high_percentile_hu": percentile_high,
        "score_threshold": float(config.score_threshold),
    }
    return SegmentationResult(
        masks=masks,
        thresholds=thresholds,
        metrics=metrics,
        qc=qc,
        config=config,
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def make_json_safe_report(
    result: SegmentationResult,
    case_id: str,
    side: str,
    software_version: str,
    output_files: Mapping[str, str] = None,
) -> Dict[str, Any]:
    """Create a JSON-safe report without embedding voxel arrays."""
    report = {
        "schema_version": "1.0",
        "software": {
            "name": "ONFH anatomy-adaptive ROI initialization",
            "version": software_version,
        },
        "case": {"id": str(case_id), "side": str(side)},
        "method": {
            "mode": "expert-reviewed initialization",
            "diagnostic_use": False,
            "configuration": asdict(result.config),
        },
        "adaptive_thresholds_hu": result.thresholds,
        "measurements": result.metrics,
        "quality_control": result.qc,
        "output_files": dict(output_files or {}),
    }
    return _json_safe(report)


def make_csv_summary_row(
    result: SegmentationResult,
    case_id: str,
    side: str,
    software_version: str,
) -> Dict[str, Any]:
    """Flatten key thresholds, measurements, and QC into a one-row summary."""
    findings = result.qc.get("findings", [])
    row = {
        "case_id": str(case_id),
        "side": str(side),
        "software_version": str(software_version),
        "low_hu": float(result.thresholds["low_hu"]),
        "sclerotic_hu": float(result.thresholds["sclerotic_hu"]),
        "reference_median_hu": float(result.thresholds["reference_median_hu"]),
        "femoral_head_mm3": float(result.metrics["femoral_head_mm3"]),
        "low_density_core_mm3": float(result.metrics["low_density_core_mm3"]),
        "sclerotic_rim_mm3": float(result.metrics["sclerotic_rim_mm3"]),
        "final_roi_mm3": float(result.metrics["final_roi_mm3"]),
        "roi_to_head_percent": float(result.metrics["roi_to_head_percent"]),
        "retained_component_count": int(result.metrics["retained_component_count"]),
        "reference_voxel_count": int(result.metrics["reference_voxel_count"]),
        "qc_status": str(result.qc["status"]),
        "qc_codes": ";".join(str(item["code"]) for item in findings),
    }
    return _json_safe(row)
