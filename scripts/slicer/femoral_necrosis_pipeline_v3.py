"""Anatomy-adaptive ONFH ROI initialization for 3D Slicer.

V3 combines:

1. affected-side femur segmentation with TotalSegmentator;
2. physical-axis femoral-head extraction;
3. patient-adaptive CT intensity features;
4. subchondral and superior weight-bearing anatomical priors;
5. sphere-derived anterosuperior geometry and seeded region growing;
6. research angular and anatomical-involvement features;
7. structured QC and reproducible STL/JSON/CSV export.

This script initializes an expert-reviewable ROI. It is not an autonomous
diagnostic system and does not replace MRI, radiologist review, or ARCO staging.

Run from the 3D Slicer Python console with ``runpy`` so companion modules can be
resolved reliably:

    import runpy
    runpy.run_path(
        r"path/to/scripts/slicer/femoral_necrosis_pipeline_v3.py",
        run_name="__main__",
    )
"""

import csv
import json
import os
import sys

import numpy as np
import slicer
import vtk


SOFTWARE_VERSION = "3.0.0"


# =========================
# User configuration
# =========================

PATIENT_NAME = "example_case"  # Use an anonymized study ID.
SIDE = "right"  # "left" or "right"
OUTPUT_DIR = os.path.abspath("outputs/slicer_v3")
EXPORT_STL = True
EXPORT_INTERMEDIATE_STL = False

TS_QUALITY = "fast"  # "normal", "fast", or "faster"
TS_CPU = True


def _script_directory():
    script_file = globals().get("__file__")
    if not script_file or script_file == "<string>":
        raise RuntimeError(
            "V3 must be run with runpy.run_path(..., run_name='__main__'). "
            "Plain exec(open(...).read()) does not expose the companion-module path."
        )
    return os.path.dirname(os.path.abspath(script_file))


SCRIPT_DIR = _script_directory()
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import femoral_necrosis_pipeline_v2 as v2  # noqa: E402
from onfh_v3_core import (  # noqa: E402
    AdaptiveSegmentationConfig,
    make_csv_summary_row,
    make_json_safe_report,
    segment_onfh_roi,
)


V3_CONFIG = AdaptiveSegmentationConfig(
    low_percentile=20.0,
    high_percentile=85.0,
    cortical_margin_mm=1.0,
    subchondral_depth_mm=8.0,
    superior_weight_bearing_fraction=0.45,
    anterior_weight_bearing_fraction=0.60,
    rim_proximity_mm=6.0,
    seed_score_threshold=0.58,
    background_seed_score_threshold=0.20,
    region_grow_minimum_score=0.40,
    region_grow_maximum_gradient=0.85,
    region_grow_connectivity=2,
    closing_radius_mm=2.0,
    min_component_volume_mm3=100.0,
)


SEGMENT_COLORS = {
    "FEMORAL_HEAD": (0.12, 0.47, 0.86),
    "LOW_DENSITY_CORE": (0.86, 0.16, 0.16),
    "SCLEROTIC_RIM": (0.90, 0.69, 0.00),
    "SUBCHONDRAL_BAND": (0.15, 0.75, 0.65),
    "WEIGHT_BEARING_ZONE": (0.55, 0.30, 0.75),
    "ANTEROSUPERIOR_ZONE": (0.35, 0.18, 0.70),
    "FOREGROUND_SEED": (0.90, 0.10, 0.10),
    "BACKGROUND_SEED": (0.45, 0.45, 0.45),
    "REGION_GROWN_ROI": (0.95, 0.45, 0.10),
    "NECROSIS_ROI_FINAL": (1.00, 0.43, 0.00),
    "QC_WARNING_REGION": (1.00, 0.00, 1.00),
}


def validate_config():
    side = SIDE.lower().strip()
    if side not in ("left", "right"):
        raise ValueError("SIDE must be 'left' or 'right'.")
    if TS_QUALITY not in ("normal", "fast", "faster"):
        raise ValueError("TS_QUALITY must be 'normal', 'fast', or 'faster'.")
    if not PATIENT_NAME.strip():
        raise ValueError("PATIENT_NAME must contain an anonymized case ID.")
    V3_CONFIG.validate()
    return side


def physical_ras_coordinates(vol, shape):
    """Return RAS coordinate arrays matching NumPy volume order [k, j, i]."""
    ijk_to_ras = vtk.vtkMatrix4x4()
    vol.GetIJKToRASMatrix(ijk_to_ras)
    k = np.arange(shape[0], dtype=np.float32)[:, None, None]
    j = np.arange(shape[1], dtype=np.float32)[None, :, None]
    i = np.arange(shape[2], dtype=np.float32)[None, None, :]
    coordinates = []
    for axis in range(3):
        coordinates.append(
            (
                ijk_to_ras.GetElement(axis, 0) * i
            + ijk_to_ras.GetElement(axis, 1) * j
            + ijk_to_ras.GetElement(axis, 2) * k
            + ijk_to_ras.GetElement(axis, 3)
            ).astype(np.float32, copy=False)
        )
    return tuple(coordinates)


def spacing_in_array_order(vol):
    """Convert Slicer IJK spacing (x, y, z) to NumPy order (z, y, x)."""
    spacing_xyz = vol.GetSpacing()
    return (
        float(spacing_xyz[2]),
        float(spacing_xyz[1]),
        float(spacing_xyz[0]),
    )


def write_json_report(path, report):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)


def write_csv_summary(path, row):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)


def print_report(result):
    metrics = result.metrics
    print("=" * 68)
    print(f"  ONFH v3 report - {PATIENT_NAME} (side: {SIDE.lower().strip()})")
    print("=" * 68)
    print(f"  Adaptive low-density threshold : {result.thresholds['low_hu']:.1f} HU")
    print(f"  Adaptive sclerotic threshold   : {result.thresholds['sclerotic_hu']:.1f} HU")
    print(f"  Reference median               : {result.thresholds['reference_median_hu']:.1f} HU")
    print(f"  Femoral-head volume            : {metrics['femoral_head_mm3']:.2f} mm^3")
    print(f"  Low-density-core volume        : {metrics['low_density_core_mm3']:.2f} mm^3")
    print(f"  Sclerotic-rim volume           : {metrics['sclerotic_rim_mm3']:.2f} mm^3")
    print(f"  Final ROI volume               : {metrics['final_roi_mm3']:.2f} mm^3")
    print(f"  ROI/head ratio                 : {metrics['roi_to_head_percent']:.2f} %")
    print(f"  Sphere radius                  : {metrics['sphere_radius_mm']:.2f} mm")
    print(f"  Sphere-fit RMS                 : {metrics['sphere_fit_rms_mm']:.2f} mm")
    print(
        "  Kerboul-like combined angle    : "
        f"{metrics['kerboul_like_combined_angle_deg']:.1f} deg"
    )
    print(
        "  Subchondral-zone involvement   : "
        f"{metrics['subchondral_involvement_percent']:.2f} %"
    )
    print(
        "  Weight-bearing-zone involvement: "
        f"{metrics['weight_bearing_involvement_percent']:.2f} %"
    )
    print(
        "  Experimental feature score     : "
        f"{metrics['experimental_collapse_feature_score']:.2f} / 100"
    )
    print("    Research feature only; not a validated collapse probability.")
    print(f"  QC status                      : {result.qc['status']}")
    for finding in result.qc["findings"]:
        print(
            f"    [{finding['severity']}] {finding['code']}: "
            f"{finding['message']}"
        )
    if not result.qc["findings"]:
        print("    No automatic QC warnings. Expert visual review is still required.")
    print("=" * 68)


def main():
    side = validate_config()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f">>> Start ONFH v3 processing: {PATIENT_NAME} (side: {side})")

    v2.TS_QUALITY = TS_QUALITY
    v2.TS_CPU = TS_CPU

    vol = v2.get_volume_node()
    loaded_array = slicer.util.arrayFromVolume(vol)
    hu_offset = v2.check_hu_offset(vol)
    hu_array = loaded_array.astype(np.float32, copy=False) + float(hu_offset)

    print("[1/7] Extract affected femoral head")
    femoral_head_mask, _ = v2.femoral_head_from_totalsegmentator(vol, side=side)

    print("[2/7] Build physical anatomical priors")
    right, anterior, superior = physical_ras_coordinates(vol, hu_array.shape)
    spacing_zyx = spacing_in_array_order(vol)

    print("[3/7] Estimate adaptive CT features and fuse candidate ROI")
    result = segment_onfh_roi(
        hu_volume=hu_array,
        femoral_head_mask=femoral_head_mask,
        spacing_zyx=spacing_zyx,
        superior_coordinates=superior,
        anterior_coordinates=anterior,
        right_coordinates=right,
        config=V3_CONFIG,
    )

    print("[4/7] Create explainable Slicer segments")
    seg = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode", "FemoralNecrosis_V3"
    )
    seg.CreateDefaultDisplayNodes()
    seg.SetReferenceImageGeometryParameterFromVolumeNode(vol)
    segment_ids = {}
    for name, mask in result.masks.items():
        segment_ids[name] = v2.write_mask_to_segment(
            seg,
            name,
            mask,
            SEGMENT_COLORS[name],
            vol,
        )

    print("[5/7] Evaluate QC")
    print_report(result)

    print("[6/7] Export reproducibility artifacts")
    output_files = {}
    if EXPORT_STL:
        head_path = os.path.join(OUTPUT_DIR, f"{PATIENT_NAME}_femoral_head_v3.stl")
        v2.export_segment_stl(seg, segment_ids["FEMORAL_HEAD"], head_path)
        output_files["femoral_head_stl"] = os.path.basename(head_path)

        if result.masks["NECROSIS_ROI_FINAL"].any():
            roi_path = os.path.join(
                OUTPUT_DIR, f"{PATIENT_NAME}_necrosis_ROI_v3.stl"
            )
            v2.export_segment_stl(seg, segment_ids["NECROSIS_ROI_FINAL"], roi_path)
            output_files["final_roi_stl"] = os.path.basename(roi_path)
        else:
            print("  [QC] Final ROI is empty; final-ROI STL export was skipped.")

        if EXPORT_INTERMEDIATE_STL:
            for name in (
                "LOW_DENSITY_CORE",
                "SCLEROTIC_RIM",
                "SUBCHONDRAL_BAND",
                "WEIGHT_BEARING_ZONE",
                "ANTEROSUPERIOR_ZONE",
                "FOREGROUND_SEED",
                "BACKGROUND_SEED",
                "REGION_GROWN_ROI",
                "QC_WARNING_REGION",
            ):
                if not result.masks[name].any():
                    continue
                path = os.path.join(
                    OUTPUT_DIR, f"{PATIENT_NAME}_{name.lower()}_v3.stl"
                )
                v2.export_segment_stl(seg, segment_ids[name], path)
                output_files[f"{name.lower()}_stl"] = os.path.basename(path)

    report_path = os.path.join(
        OUTPUT_DIR, f"{PATIENT_NAME}_onfh_v3_report.json"
    )
    csv_path = os.path.join(
        OUTPUT_DIR, f"{PATIENT_NAME}_onfh_v3_summary.csv"
    )
    output_files["json_report"] = os.path.basename(report_path)
    output_files["csv_summary"] = os.path.basename(csv_path)

    report = make_json_safe_report(
        result,
        case_id=PATIENT_NAME,
        side=side,
        software_version=SOFTWARE_VERSION,
        output_files=output_files,
    )
    summary_row = make_csv_summary_row(
        result,
        case_id=PATIENT_NAME,
        side=side,
        software_version=SOFTWARE_VERSION,
    )
    write_json_report(report_path, report)
    write_csv_summary(csv_path, summary_row)
    print(f"      JSON report: {report_path}")
    print(f"      CSV summary: {csv_path}")

    print("[7/7] Done")
    print("  Mandatory next step: review and, if needed, correct every mask in Slicer.")
    print("  Save an MRML scene only in an approved clinical-data location.")


if __name__ == "__main__":
    main()
