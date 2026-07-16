# V3 Anatomy-Adaptive Segmentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish an explainable v3 ONFH ROI initialization workflow with adaptive image features, anatomical priors, structured QC, and reproducible ROI-to-FEA exports.

**Architecture:** A Slicer-independent NumPy/SciPy core performs feature extraction, fusion, morphology, measurement, and QC. A separate 3D Slicer wrapper handles TotalSegmentator, MRML segments, physical coordinates, STL export, and JSON/CSV reporting. Synthetic tests exercise the core without clinical data.

**Tech Stack:** Python 3.10+, NumPy, SciPy, 3D Slicer 5.10, SlicerTotalSegmentator, `unittest`, GitHub Actions.

---

### Task 1: Define Core Behavior with Synthetic Tests

**Files:**
- Create: `tests/test_onfh_v3_core.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write a synthetic femoral-head fixture**

Create a spherical mask with normal cancellous HU, a superior subchondral
low-density lesion, a high-density rim, and an inferior low-density decoy.

- [ ] **Step 2: Write failing tests for the public API**

Import `AdaptiveSegmentationConfig`, `segment_onfh_roi`, and
`make_json_safe_report` from `scripts.slicer.onfh_v3_core`. Assert that the
superior lesion is retained, the inferior decoy is rejected, every output is
inside the head, and the report contains thresholds and QC.

- [ ] **Step 3: Verify the tests fail because the module is absent**

Run:

```powershell
& "G:\3D Slicer\3D Slicer 5.10.0\bin\PythonSlicer.EXE" -m unittest tests.test_onfh_v3_core -v
```

Expected: import failure for `scripts.slicer.onfh_v3_core`.

### Task 2: Implement the Pure V3 Core

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/slicer/__init__.py`
- Create: `scripts/slicer/onfh_v3_core.py`
- Test: `tests/test_onfh_v3_core.py`

- [ ] **Step 1: Add configuration and result data classes**

Define `AdaptiveSegmentationConfig` with percentile, HU-bound, anatomical-depth,
fusion-weight, morphology, component-volume, and QC thresholds. Define
`SegmentationResult` with masks, thresholds, metrics, QC, and configuration.

- [ ] **Step 2: Implement anatomical priors**

Use `scipy.ndimage.distance_transform_edt` with physical spacing. Construct a
cortical-margin exclusion, subchondral score, and normalized superior
weight-bearing score.

- [ ] **Step 3: Implement adaptive intensity features**

Estimate low and high thresholds from the cancellous reference mask with
absolute safety bounds. Create low-density and sclerotic-rim masks and a
distance-based rim-proximity score.

- [ ] **Step 4: Implement feature fusion and component filtering**

Apply the documented weights and score threshold. Retain components that
intersect high-confidence low-density seeds, apply spacing-aware closing, fill
holes, remove small components by physical volume, and re-mask the output.

- [ ] **Step 5: Implement measurements and QC**

Return physical volumes, ROI ratio, component count, inferior fraction,
reference count, structured warning/error codes, and `PASS`, `REVIEW`, or
`FAIL`.

- [ ] **Step 6: Run the core tests**

Run:

```powershell
& "G:\3D Slicer\3D Slicer 5.10.0\bin\PythonSlicer.EXE" -m unittest tests.test_onfh_v3_core -v
```

Expected: all tests pass.

### Task 3: Integrate V3 with 3D Slicer

**Files:**
- Create: `scripts/slicer/femoral_necrosis_pipeline_v3.py`
- Reference: `scripts/slicer/femoral_necrosis_pipeline_v2.py`

- [ ] **Step 1: Copy only the robust Slicer boundary functions**

Reuse v2 behavior for CT selection, HU/GV integrity checking,
TotalSegmentator API adaptation, segment-name matching, physical-superior
femoral-head extraction, segment writing, volume geometry, and robust STL
export.

- [ ] **Step 2: Generate the physical superior-coordinate array**

Use the volume IJK-to-RAS matrix and NumPy `[k, j, i]` indexing to create the
physical superior coordinate passed into `segment_onfh_roi`.

- [ ] **Step 3: Create all explainable segments**

Write `FEMORAL_HEAD`, `LOW_DENSITY_CORE`, `SCLEROTIC_RIM`,
`SUBCHONDRAL_BAND`, `WEIGHT_BEARING_ZONE`, `NECROSIS_ROI_FINAL`, and
`QC_WARNING_REGION` to a Slicer segmentation node.

- [ ] **Step 4: Export reproducibility artifacts**

Export named STL files, a JSON report, and a one-row CSV summary containing
case ID, side, software version, thresholds, volumes, ROI ratio, QC status, and
QC codes.

- [ ] **Step 5: Compile both Slicer scripts**

Run:

```powershell
& "G:\3D Slicer\3D Slicer 5.10.0\bin\PythonSlicer.EXE" -m py_compile scripts\slicer\onfh_v3_core.py scripts\slicer\femoral_necrosis_pipeline_v2.py scripts\slicer\femoral_necrosis_pipeline_v3.py
```

Expected: exit code 0.

### Task 4: Add Research Documentation and CI

**Files:**
- Modify: `README.md`
- Modify: `docs/SOP.md`
- Modify: `docs/parameter_table.md`
- Modify: `docs/fea_preprocessing.md`
- Modify: `docs/code_availability_statement.md`
- Modify: `examples/README.md`
- Modify: `CHANGELOG.md`
- Create: `docs/algorithm_v3.md`
- Create: `docs/validation_protocol.md`
- Create: `.github/workflows/test.yml`

- [ ] **Step 1: Reframe the README**

Present v2 as the fixed-threshold baseline and v3 as the anatomy-adaptive
expert-reviewed workflow. Add quick-start commands, outputs, QC interpretation,
claim boundaries, repository map, and validation status.

- [ ] **Step 2: Document exact v3 parameters**

Record percentile thresholds, HU safety bounds, anatomical depths, score
weights, component filters, and QC limits. State that parameter values require
external validation before clinical deployment.

- [ ] **Step 3: Add the validation protocol**

Specify multi-expert contours, adjudication, overlap and surface metrics,
correction time, external scanner testing, ablation analysis, and propagation
of ROI perturbations into FEA.

- [ ] **Step 4: Add CI**

Configure Python 3.11 on Ubuntu, install NumPy and SciPy, run `unittest`, and
compile the pure core and both Slicer scripts without executing Slicer imports.

### Task 5: Verify and Publish

**Files:**
- Modify only files listed in Tasks 1-4.

- [ ] **Step 1: Run full automated verification**

```powershell
& "G:\3D Slicer\3D Slicer 5.10.0\bin\PythonSlicer.EXE" -m unittest discover -s tests -v
& "G:\3D Slicer\3D Slicer 5.10.0\bin\PythonSlicer.EXE" -m py_compile scripts\slicer\onfh_v3_core.py scripts\slicer\femoral_necrosis_pipeline_v2.py scripts\slicer\femoral_necrosis_pipeline_v3.py
git diff --check
```

Expected: all tests pass, compilation succeeds, and `git diff --check` reports
no whitespace errors.

- [ ] **Step 2: Review scope and claims**

Confirm that no documentation calls v3 diagnostically validated or fully
automatic. Confirm that v1.0.0 remains identified as the historical baseline
and that v3.0.0 is the manuscript-associated release.

- [ ] **Step 3: Commit and push**

```powershell
git add .github README.md CHANGELOG.md docs examples scripts tests
git commit -m "Add anatomy-adaptive ONFH segmentation v3"
git push -u origin codex/v3-anatomy-adaptive-segmentation
```
