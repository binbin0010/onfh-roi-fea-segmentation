# Supplementary SOP: ONFH ROI Segmentation and FEA Preprocessing

This SOP describes the reproducible workflow used to define femoral-head
necrosis ROIs and prepare segmentation outputs for downstream FEA.

## Route A: 3D Slicer + TotalSegmentator

1. Load the hip CT DICOM series into 3D Slicer.
2. Confirm that the active scalar volume is the target CT series.
3. Install or enable the SlicerTotalSegmentator extension.
4. Edit `scripts/slicer/femoral_necrosis_pipeline_v2.py`:
   - `PATIENT_NAME`: anonymized study ID.
   - `SIDE`: `left` or `right`.
   - `OUTPUT_DIR`: output folder.
5. Run the script in the 3D Slicer Python console:

   ```python
   exec(open(r"path/to/femoral_necrosis_pipeline_v2.py", encoding="utf-8").read())
   ```

6. Review the generated masks:
   - `FEMORAL_HEAD`
   - `NECROTIC_CORE`
   - `SCLEROTIC_RIM`
   - `NECROSIS_ROI_FINAL`
7. Manually correct masks if they include acetabular bone, cross cortical bone,
   omit visually evident lesion/graft tissue, or conflict with the surgical
   location.
8. Export STL files for the femoral head and final ROI.
9. Save the Slicer scene if additional review is needed.

## Route B: Mimics 21 Research + MATLAB Link

1. Load the CT case in Mimics.
2. Create or activate an `ALL_BONE` mask.
3. In Mimics, select `Run MATLAB Script`.
4. Choose `scripts/mimics_matlab_link/femoral_necrosis_pipeline.m`.
5. Enter the femoral-head seed point and affected side.
6. Confirm that `NewMask` is imported into the Mimics project.
7. Inspect and correct the returned mask.
8. Compute 3D models for `NewMask` and `FEMORAL_HEAD`.
9. Export STL files for 3-matic/FEA preprocessing.

## Acceptance Checks

- Femoral-head mask is anatomically plausible and affected-side-specific.
- Final ROI is contained within the femoral head.
- ROI does not include acetabulum or unrelated cortical bone.
- Necrotic core and sclerotic rim are visually consistent with CT morphology.
- Volume report has nonzero femoral-head volume.
- If ROI volume is zero or unexpectedly small, HU/GV scale and thresholds are
  checked before exclusion.

## Privacy

Do not store patient identifiers, raw DICOM files, or identifiable screenshots
in this repository.
