# SOP: ONFH ROI Initialization and FEA Preprocessing

## Scope

This SOP covers the fixed-threshold v2 baseline and the anatomy-adaptive v3
research workflow. Both are expert-reviewed initialization methods. Neither is
approved for autonomous diagnosis or staging.

## Required Records

Before processing, record:

- anonymized case ID;
- affected side;
- CT acquisition and reconstruction settings;
- Slicer and SlicerTotalSegmentator versions;
- script commit or release;
- operator and reviewer identifiers;
- approved output location.

## Route A: Anatomy-Adaptive V3

### 1. Prepare the files

Keep these files together:

```text
femoral_necrosis_pipeline_v2.py
femoral_necrosis_pipeline_v3.py
onfh_v3_core.py
```

### 2. Load and verify CT

1. Import the target CT DICOM series into 3D Slicer.
2. Confirm that the active scalar volume is the intended series.
3. Check orientation, spacing, completeness, metal artifact, and field of view.
4. Confirm that patient identifiers will not be written to the repository.

### 3. Configure the case

Edit the v3 user configuration:

```python
PATIENT_NAME = "anonymized_case_id"
SIDE = "right"
OUTPUT_DIR = r"D:\approved_output_folder"
EXPORT_STL = True
```

Do not change research parameters during a comparative study unless the change
is prespecified, versioned, and applied consistently.

### 4. Run v3

Use the Slicer Python console:

```python
import runpy

runpy.run_path(
    r"path\to\femoral_necrosis_pipeline_v3.py",
    run_name="__main__",
)
```

The workflow:

1. checks HU/GV scale;
2. segments bilateral femora with TotalSegmentator;
3. selects the affected femur;
4. extracts the head using physical superior geometry;
5. estimates adaptive intensity thresholds;
6. creates anatomical priors and candidate masks;
7. generates the final ROI and QC warning region;
8. exports STL, JSON, and CSV.

### 5. Review every output

Inspect:

- `FEMORAL_HEAD`
- `LOW_DENSITY_CORE`
- `SCLEROTIC_RIM`
- `SUBCHONDRAL_BAND`
- `WEIGHT_BEARING_ZONE`
- `NECROSIS_ROI_FINAL`
- `QC_WARNING_REGION`

Mandatory acceptance checks:

- correct side and anatomically plausible femoral head;
- no acetabular inclusion;
- no excessive femoral-neck inclusion;
- final ROI contained within the femoral head;
- cortical shell not incorporated as lesion tissue;
- core and rim compatible with CT morphology;
- ROI compatible with surgical graft location when postoperative;
- all QC codes reviewed and documented;
- manual corrections saved outside the public repository.

`PASS` means only that programmed QC thresholds were not triggered. It does not
establish clinical correctness.

### 6. Record corrections

Record:

- whether correction was required;
- correction time;
- structures added or removed;
- reason for correction;
- final reviewer decision;
- final MRML or mask location.

Correction time is a recommended validation outcome.

## Route B: Fixed-Threshold V2 Baseline

1. Configure `PATIENT_NAME`, `SIDE`, and `OUTPUT_DIR`.
2. Run:

   ```python
   exec(open(r"path\to\femoral_necrosis_pipeline_v2.py", encoding="utf-8").read())
   ```

3. Review `FEMORAL_HEAD`, `NECROTIC_CORE`, `SCLEROTIC_RIM`, and
   `NECROSIS_ROI_FINAL`.
4. Correct leakage, omissions, and anatomically implausible regions.
5. Export the corrected surfaces for downstream analysis.

V2 must be used when reproducing release `v1.0.0`.

## Route C: Mimics MATLAB Link Fallback

1. Load the CT case in Mimics.
2. Create or activate an `ALL_BONE` mask.
3. Select `Run MATLAB Script`.
4. Choose `scripts/mimics_matlab_link/femoral_necrosis_pipeline.m`.
5. Enter the femoral-head seed and affected side.
6. Inspect and correct the returned masks.
7. Export approved surfaces for 3-matic/FEA.

## FEA Transfer

Before meshing:

1. verify STL units and orientation;
2. repair surfaces without changing clinically reviewed boundaries;
3. create host-bone, lesion/graft, and implant partitions;
4. preserve conformal interfaces;
5. document Boolean operations and manual surface edits;
6. perform mesh-sensitivity analysis when reporting quantitative FEA.

## Failure Handling

Stop and review the case if:

- TotalSegmentator fails or returns the wrong side;
- the femoral-head mask is empty or implausible;
- the adaptive reference tissue is insufficient;
- ROI ratio is unusually high or low;
- the final ROI is empty;
- QC indicates inferior extension or fragmentation;
- CT artifacts prevent reliable interpretation.

Do not suppress a QC code solely to make a case pass.

## Privacy

Never commit patient DICOM, NIfTI, MRML scenes, patient-derived STL files,
meshes, identifiable screenshots, or clinical reports to the public repository.
