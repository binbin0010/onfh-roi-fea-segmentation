# Changelog

## Unreleased

- Fixed TotalSegmentator 2.x invocation by using `task="total"` with
  `quality="fast"` instead of the invalid `task="total_fast"`.
- Added robust femur segment-name matching for both raw labels
  (`femur_right`) and Slicer terminology display names (`right femur`).
- Made femoral-head candidate selection use the physical superior direction
  instead of assuming the NumPy z-axis is always superior.
- Re-masked slice-wise hole-filled ROIs by the femoral-head mask to prevent
  final ROI leakage outside the head.
- Hardened STL export by exporting through a temporary folder and renaming the
  generated STL to the requested output path.

## v1.0.0

- Initial manuscript-associated release.
- Added 3D Slicer + TotalSegmentator segmentation workflow.
- Added Mimics 21 Research MATLAB Link fallback workflow.
- Added SOP, parameter table, and FEA preprocessing notes.
