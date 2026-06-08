"""Femoral head necrosis ROI segmentation in 3D Slicer.

This script implements a segmentation-assisted workflow for ONFH studies:

1. Read the active CT scalar volume in 3D Slicer.
2. Run TotalSegmentator to segment the affected-side femur.
3. Extract the femoral head by adaptive geometric separation.
4. Threshold the necrotic core and sclerotic rim on the real HU scale.
5. Combine and morphologically refine masks into a final ROI.
6. Report volumes and optionally export STL files.

The script is intended to be run from the 3D Slicer Python console:

    exec(open(r"path/to/femoral_necrosis_pipeline_v2.py", encoding="utf-8").read())

No patient identifiers are required. Set PATIENT_NAME to an anonymized study ID.
"""

import inspect
import os
import sys

import numpy as np
import slicer
import vtk  # noqa: F401  # imported for Slicer extension compatibility


# =========================
# User configuration
# =========================

PATIENT_NAME = "example_case"
SIDE = "right"  # "left" or "right"
OUTPUT_DIR = os.path.abspath("outputs/slicer")
EXPORT_STL = True


# =========================
# HU thresholds
# =========================

# Mimics gray value (GV) = real HU + 1024.
# Bone: Mimics GV 1324-3024 -> real HU 300-2000.
# Necrotic core: Mimics GV 1034-1324 -> real HU 10-300.
# Sclerotic rim: Mimics GV 1624-2824 -> real HU 600-1800.
HU_BONE_MIN, HU_BONE_MAX = 300, 2000
HU_NECRO_MIN, HU_NECRO_MAX = 10, 300
HU_SCL_MIN, HU_SCL_MAX = 600, 1800


def get_volume_node():
    """Return the first scalar volume node in the current Slicer scene."""
    nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
    if not nodes:
        raise RuntimeError("No CT scalar volume node was found. Load DICOM first.")
    return nodes[0]


def check_hu_offset(vol):
    """Detect whether the volume appears to use real HU or Mimics-style GV.

    Returns an offset that converts the loaded array to real HU before
    thresholding. For most Slicer DICOM imports, the offset is 0.
    """
    arr = slicer.util.arrayFromVolume(vol)
    p99 = float(np.percentile(arr, 99))
    p01 = float(np.percentile(arr, 1))
    print(f"  [HU check] voxel distribution: p01={p01:.1f}, p99={p99:.1f}")

    # A distribution roughly in [0, 2500] is often Mimics-style GV.
    if p01 > -200 and p99 < 1500:
        print("  [HU check] GV-like values detected; applying -1024 offset.")
        return -1024
    return 0


def get_totalseg_logic():
    """Return TotalSegmentator logic across Slicer extension versions."""
    try:
        logic = slicer.util.getModuleLogic("TotalSegmentator")
        if logic is not None:
            return logic
    except Exception:
        pass

    try:
        return slicer.modules.totalsegmentator.widgetRepresentation().self().logic
    except Exception:
        pass

    try:
        from TotalSegmentator import TotalSegmentatorLogic

        return TotalSegmentatorLogic()
    except Exception as exc:
        raise RuntimeError(
            "Could not access TotalSegmentator logic. Install and restart the "
            f"SlicerTotalSegmentator extension. Original error: {exc}"
        ) from exc


def call_totalseg_process(ts_logic, vol, out_seg):
    """Call TotalSegmentator while adapting to old and new extension APIs."""
    sig = inspect.signature(ts_logic.process)
    params = sig.parameters
    print(f"  [TotalSeg] process() parameters: {list(params.keys())}")

    kwargs = {}
    for in_key in ("inputVolume", "inputVolumeNode", "input_volume"):
        if in_key in params:
            kwargs[in_key] = vol
            break

    for out_key in ("outputSegmentation", "outputSegmentationNode", "output_segmentation"):
        if out_key in params:
            kwargs[out_key] = out_seg
            break

    if not kwargs:
        ts_logic.process(vol, out_seg)
        return

    if "task" in params:
        kwargs["task"] = "total_fast"
    elif "fast" in params:
        kwargs["fast"] = True

    for subset_key in ("subset", "subsetOfTotalSegmentator", "labels"):
        if subset_key in params:
            kwargs[subset_key] = ["femur_left", "femur_right"]
            break

    print(f"  [TotalSeg] call arguments: {list(kwargs.keys())}")
    ts_logic.process(**kwargs)


def femoral_head_from_totalsegmentator(vol, side="right"):
    """Segment the femur and extract the femoral head.

    Returns:
        tuple[np.ndarray, np.ndarray]: femoral-head mask and full-femur mask.
    """
    print(f"  [TotalSeg] Running TotalSegmentator for side={side} ...")
    try:
        import totalsegmentator  # noqa: F401
    except ImportError:
        slicer.util.pip_install("totalsegmentator")

    ts_logic = get_totalseg_logic()
    out_seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "TS_femur")
    out_seg.CreateDefaultDisplayNodes()
    out_seg.SetReferenceImageGeometryParameterFromVolumeNode(vol)

    call_totalseg_process(ts_logic, vol, out_seg)

    seg_name = f"femur_{side}"
    seg_id = out_seg.GetSegmentation().GetSegmentIdBySegmentName(seg_name)
    if not seg_id:
        all_names = []
        for idx in range(out_seg.GetSegmentation().GetNumberOfSegments()):
            sid = out_seg.GetSegmentation().GetNthSegmentID(idx)
            all_names.append(out_seg.GetSegmentation().GetSegment(sid).GetName())
        raise RuntimeError(f"TotalSegmentator did not output {seg_name!r}. Found: {all_names}")

    full_femur = slicer.util.arrayFromSegmentBinaryLabelmap(out_seg, seg_id, vol).astype(bool)
    nvox = int(full_femur.sum())
    print(f"  [TotalSeg] full femur voxels = {nvox}")
    if nvox == 0:
        raise RuntimeError("TotalSegmentator output was empty. Check model loading and side.")

    from scipy.ndimage import binary_opening
    from scipy.ndimage import label as cc_label

    z_idx = np.where(full_femur.any(axis=(1, 2)))[0]
    z_top, z_bot = z_idx.max(), z_idx.min()
    z_span = z_top - z_bot
    z_cut = z_top - int(z_span * 0.40)
    print(f"  [TotalSeg] femur z-range [{z_bot}, {z_top}], head candidate z >= {z_cut}")

    head_band = full_femur.copy()
    head_band[:z_cut, :, :] = False
    head_band = binary_opening(head_band, iterations=3)
    labels, n_components = cc_label(head_band)

    if n_components == 0:
        print("  [TotalSeg] warning: opening removed all candidates; falling back.")
        head_band = full_femur.copy()
        head_band[:z_cut, :, :] = False
        labels, n_components = cc_label(head_band)

    if n_components == 0:
        raise RuntimeError("Femoral head extraction failed after geometric separation.")

    best_score, best_id = -1.0, 1
    for cid in range(1, n_components + 1):
        comp = labels == cid
        volume = int(comp.sum())
        if volume < 500:
            continue

        zs, ys, xs = np.where(comp)
        bbox_volume = (
            (zs.max() - zs.min() + 1)
            * (ys.max() - ys.min() + 1)
            * (xs.max() - xs.min() + 1)
        )
        compactness = volume / max(bbox_volume, 1)
        score = volume * compactness
        print(
            f"    candidate #{cid}: voxels={volume}, compactness={compactness:.3f}, "
            f"score={score:.0f}"
        )
        if score > best_score:
            best_score, best_id = score, cid

    head = labels == best_id
    print(f"  [TotalSeg] selected component #{best_id}; femoral-head voxels = {int(head.sum())}")

    slicer.mrmlScene.RemoveNode(out_seg)
    return head, full_femur


def write_mask_to_segment(seg_node, name, mask_bool, color, ref_vol):
    """Write a NumPy binary mask into a Slicer segmentation node."""
    seg_id = seg_node.GetSegmentation().AddEmptySegment(name)
    seg_node.GetSegmentation().GetSegment(seg_id).SetColor(*color)
    slicer.util.updateSegmentBinaryLabelmapFromArray(
        mask_bool.astype(np.uint8), seg_node, seg_id, ref_vol
    )
    return seg_id


def threshold_mask(vol_array, hu_offset, lo, hi):
    """Threshold the active CT volume after conversion to real HU."""
    effective_hu = vol_array + hu_offset
    return (effective_hu >= lo) & (effective_hu <= hi)


def compute_volume_mm3(mask_bool, vol):
    """Compute mask volume in cubic millimetres."""
    spacing = vol.GetSpacing()
    voxel_mm3 = spacing[0] * spacing[1] * spacing[2]
    return float(mask_bool.sum()) * voxel_mm3


def export_segment_stl(seg, seg_id, path):
    """Export a segment as an STL file."""
    slicer.modules.segmentations.logic().ExportSegmentsClosedSurfaceRepresentation(seg, [seg_id])
    name = seg.GetSegmentation().GetSegment(seg_id).GetName()
    model_node = slicer.util.getNode(name)
    slicer.util.saveNode(model_node, path)


def arco_stage(ratio, roi_volume_mm3):
    """Return a volume-based ARCO reference label requiring clinical review."""
    if ratio < 15 and roi_volume_mm3 < 1000:
        return "ARCO I"
    if ratio < 15:
        return "ARCO I-II"
    if 15 <= ratio <= 30:
        return "ARCO II"
    if ratio > 30:
        return "ARCO III-IV (review crescent sign)"
    return "Unclassified"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f">>> Start processing: {PATIENT_NAME} (side: {SIDE})")

    vol = get_volume_node()
    vol_arr = slicer.util.arrayFromVolume(vol)
    hu_offset = check_hu_offset(vol)

    seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "FemoralNecrosis")
    seg.CreateDefaultDisplayNodes()
    seg.SetReferenceImageGeometryParameterFromVolumeNode(vol)

    print("[1/7] Extract femoral head (TotalSegmentator + geometry)")
    femoral_head_mask, _full_femur = femoral_head_from_totalsegmentator(vol, side=SIDE)
    femoral_head_id = write_mask_to_segment(
        seg, "FEMORAL_HEAD", femoral_head_mask, (0.12, 0.47, 0.86), vol
    )

    print(f"[2/7] Necrotic-core threshold (real HU {HU_NECRO_MIN}-{HU_NECRO_MAX})")
    necro_raw = threshold_mask(vol_arr, hu_offset, HU_NECRO_MIN, HU_NECRO_MAX)
    necro_mask = necro_raw & femoral_head_mask
    print(f"      necrotic-core voxels = {int(necro_mask.sum())}")
    if necro_mask.sum() == 0:
        print("  [warning] Necrotic core is empty. Check thresholds, HU offset, and disease stage.")
    necrotic_core_id = write_mask_to_segment(
        seg, "NECROTIC_CORE", necro_mask, (0.86, 0.16, 0.16), vol
    )

    print(f"[3/7] Sclerotic-rim threshold (real HU {HU_SCL_MIN}-{HU_SCL_MAX})")
    scl_raw = threshold_mask(vol_arr, hu_offset, HU_SCL_MIN, HU_SCL_MAX)
    scl_mask = scl_raw & femoral_head_mask
    print(f"      sclerotic-rim voxels = {int(scl_mask.sum())}")
    sclerotic_rim_id = write_mask_to_segment(
        seg, "SCLEROTIC_RIM", scl_mask, (0.90, 0.69, 0.00), vol
    )

    print("[4/7] Morphological refinement -> NECROSIS_ROI_FINAL")
    from scipy.ndimage import binary_closing, binary_dilation, binary_fill_holes

    scl_dilated = binary_dilation(scl_mask, iterations=3) & femoral_head_mask
    roi = necro_mask | scl_dilated
    roi = binary_closing(roi, iterations=4) & femoral_head_mask
    roi = np.stack([binary_fill_holes(slice_mask) for slice_mask in roi])
    print(f"      final ROI voxels = {int(roi.sum())}")
    roi_id = write_mask_to_segment(seg, "NECROSIS_ROI_FINAL", roi, (1.00, 0.43, 0.00), vol)

    print("[5/7] Volume measurement")
    volumes = {
        "FEMORAL_HEAD": compute_volume_mm3(femoral_head_mask, vol),
        "NECROTIC_CORE": compute_volume_mm3(necro_mask, vol),
        "SCLEROTIC_RIM": compute_volume_mm3(scl_mask, vol),
        "NECROSIS_ROI_FINAL": compute_volume_mm3(roi, vol),
    }
    ratio = (
        volumes["NECROSIS_ROI_FINAL"] / volumes["FEMORAL_HEAD"] * 100
        if volumes["FEMORAL_HEAD"]
        else 0.0
    )

    print("=" * 56)
    print(f"        Volume report - {PATIENT_NAME} (side: {SIDE})")
    print("=" * 56)
    for key, value in volumes.items():
        print(f"  {key:<22s} : {value:10.2f} mm^3")
    print(f"  {'Necrosis ratio':<22s} : {ratio:10.2f} %")
    print(f"  {'ARCO reference':<22s} : {arco_stage(ratio, volumes['NECROSIS_ROI_FINAL'])}")
    print("=" * 56)

    _ = necrotic_core_id, sclerotic_rim_id
    if EXPORT_STL:
        print("[6/7] Export STL")
        export_segment_stl(seg, roi_id, os.path.join(OUTPUT_DIR, f"{PATIENT_NAME}_necrosis_ROI.stl"))
        export_segment_stl(
            seg, femoral_head_id, os.path.join(OUTPUT_DIR, f"{PATIENT_NAME}_femoral_head.stl")
        )

    print(f"[7/7] Done. Output directory: {OUTPUT_DIR}")
    print("    Manual step: save the Slicer scene as an .mrml file if needed.")


if __name__ == "__main__":
    main()
