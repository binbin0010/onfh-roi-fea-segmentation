# ONFH ROI and FEA Preprocessing Workflow

Research code for segmentation-assisted region-of-interest (ROI) definition and
finite element analysis (FEA) preprocessing in osteonecrosis of the femoral head
(ONFH).

The workflow was designed to support reproducible extraction of femoral-head
masks, necrotic-core masks, sclerotic-rim masks, final lesion-related ROIs,
volume measurements, STL export, and downstream Mimics/3-matic/ANSYS
preprocessing.

## Repository Contents

```text
scripts/
  slicer/
    femoral_necrosis_pipeline_v2.py
  mimics_matlab_link/
    femoral_necrosis_pipeline.m
docs/
  SOP.md
  parameter_table.md
  fea_preprocessing.md
  code_availability_statement.md
  workflow_figure.png
examples/
  README.md
```

## Workflows

![ROI-to-FEA workflow](docs/workflow_figure.png)

### 1. 3D Slicer + TotalSegmentator route

Use `scripts/slicer/femoral_necrosis_pipeline_v2.py` when CT DICOM data can be
loaded into 3D Slicer and the SlicerTotalSegmentator extension is available.

Main operations:

1. Load CT DICOM into 3D Slicer.
2. Check whether voxel intensities are on the real HU scale or Mimics-style
   gray-value scale.
3. Use TotalSegmentator/nnU-Net to segment the affected-side femur.
4. Extract the femoral head by adaptive head-neck separation.
5. Generate candidate masks for necrotic core and sclerotic rim.
6. Refine the final ROI by dilation, closing, and slice-wise hole filling.
7. Export femoral-head and final-ROI STL files.

### 2. Mimics 21 Research + MATLAB Link route

Use `scripts/mimics_matlab_link/femoral_necrosis_pipeline.m` when the workflow is
run inside Mimics 21 Research through `Run MATLAB Script`.

Main operations:

1. Activate an `ALL_BONE` mask in Mimics.
2. Launch the MATLAB Link script.
3. Enter a femoral-head seed point and affected side.
4. Segment the seed-containing femoral-head component.
5. Apply Mimics gray-value thresholds for necrotic core and sclerotic rim.
6. Return `NewMask` to Mimics as the final ROI.
7. Save masks and a volume report for downstream 3-matic/FEA use.

## Key Parameters

| Quantity | Real HU | Mimics GV |
|---|---:|---:|
| Bone threshold | 300-2000 | 1324-3024 |
| Necrotic core | 10-300 | 1034-1324 |
| Sclerotic rim | 600-1800 | 1624-2824 |
| Sclerotic-rim dilation | 3 iterations | 3D spherical element |
| ROI closing | 4 iterations | 3D spherical element |

Mimics gray value (GV) is treated as `HU + 1024`.

## Inputs and Outputs

Inputs:

- Hip CT DICOM volume or Mimics volume data.
- Affected side (`left` or `right`).
- Optional femoral-head seed point for the MATLAB route.

Outputs:

- `FEMORAL_HEAD`
- `NECROTIC_CORE`
- `SCLEROTIC_RIM`
- `NECROSIS_ROI_FINAL`
- ROI/femoral-head STL files
- Volume report and necrosis ratio
- Files suitable for Mimics/3-matic/ANSYS preprocessing

## Privacy and Data

This repository contains no patient-level DICOM data. Do not commit raw DICOM
files, protected health information, screenshots containing patient identifiers,
or institution-specific file paths.

## Citation

If you use this workflow, please cite the archived software DOI and the
associated manuscript. See `CITATION.cff` for citation metadata.

## Status

Version `v1.0.0` is intended as the manuscript-associated release.
