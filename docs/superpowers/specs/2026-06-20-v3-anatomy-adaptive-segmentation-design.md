# V3 Anatomy-Adaptive Segmentation Design

## Objective

Add an explainable, expert-reviewed v3 ROI initialization workflow for
osteonecrosis of the femoral head (ONFH). The method combines patient-specific
femoral-head anatomy, adaptive CT intensity features, subchondral and superior
weight-bearing priors, sclerotic-rim proximity, explicit quality control (QC),
and reproducible ROI-to-FEA exports.

The v2 script remains unchanged as the manuscript-associated fixed-threshold
baseline. V3 is a new method and must not be described as clinically validated
until independent expert reference contours are available.

## Research Claim Boundary

V3 may be described as:

- anatomy-constrained, feature-guided ROI initialization;
- patient-adaptive within the femoral-head mask;
- explainable because all intermediate masks and thresholds are retained;
- reproducible because configuration, measurements, QC, and output paths are
  written to JSON and CSV;
- human-in-the-loop because every final mask requires expert review.

V3 must not be described as:

- an autonomous diagnostic system;
- a replacement for MRI or radiologist assessment;
- a validated automatic necrosis contour;
- an ARCO staging system;
- a predictor of collapse without a separate clinical validation study.

## Architecture

### Pure algorithm module

`scripts/slicer/onfh_v3_core.py` contains no Slicer imports. It accepts NumPy
arrays, voxel spacing, and a physical superior-coordinate array. It returns
intermediate masks, adaptive thresholds, quantitative metrics, and structured
QC findings.

### Slicer integration

`scripts/slicer/femoral_necrosis_pipeline_v3.py` reuses the robust
TotalSegmentator invocation and physical-axis femoral-head extraction from v2.
It calls the pure core, creates named Slicer segments, exports STL files, and
writes machine-readable reports.

### Tests and continuous integration

`tests/test_onfh_v3_core.py` uses synthetic femoral-head phantoms to test:

- adaptive threshold estimation;
- anatomical-prior containment;
- rejection of an inferior low-density decoy;
- retention of a superior subchondral lesion with a sclerotic rim;
- small-component removal;
- oversized and empty ROI QC warnings;
- JSON-safe report generation.

`.github/workflows/test.yml` runs the tests and compiles both Slicer scripts.

## Algorithm

### Inputs

- real-HU CT array;
- binary femoral-head mask;
- voxel spacing in NumPy axis order `(z, y, x)`;
- physical superior coordinate for every voxel;
- `AdaptiveSegmentationConfig`.

### Anatomical priors

The Euclidean distance transform inside the femoral-head mask defines distance
to the head surface. A cortical margin is excluded from lesion candidates.

The subchondral prior decreases linearly from the cortical margin to a
configurable depth. The weight-bearing prior increases within the superior
fraction of the femoral head. Both are soft scores rather than hard diagnostic
rules.

### Adaptive image features

The reference population is cancellous-appearing tissue inside the head after
excluding the cortical margin, extreme density values, and non-finite voxels.

The low-density threshold is the configured lower percentile of the reference
distribution, capped by an absolute HU ceiling. The sclerotic threshold is the
configured upper percentile, bounded by conservative absolute HU limits.

The method preserves:

- `LOW_DENSITY_CORE`;
- `SCLEROTIC_RIM`;
- `SUBCHONDRAL_BAND`;
- `WEIGHT_BEARING_ZONE`.

### Feature fusion

The final voxel score is:

```text
0.45 * low-density score
+ 0.20 * sclerotic-rim proximity
+ 0.20 * subchondral score
+ 0.15 * superior weight-bearing score
```

The candidate envelope requires low-density evidence or proximity to a
sclerotic rim. Connected components must intersect a high-confidence
low-density seed. Morphological closing uses a spacing-aware ellipsoidal
structuring element. Components smaller than the configured physical volume
are removed.

The final ROI is always re-confined to the femoral-head mask and excludes the
cortical margin.

## Explainable QC

The QC report includes:

- femoral-head, core, rim, final-ROI, and warning-region volumes;
- ROI-to-head volume ratio;
- adaptive low and high HU thresholds;
- number of retained components;
- reference-voxel count;
- inferior-zone fraction;
- surface-margin enforcement;
- warning and error codes;
- final status: `PASS`, `REVIEW`, or `FAIL`.

Warnings include empty or unusually small ROI, unusually large ROI, weak
sclerotic-rim evidence, fragmented ROI, inferior extension, and insufficient
reference tissue. QC warnings do not automatically diagnose or exclude a case.

## Reproducible Outputs

For each anonymized case, v3 exports:

- named Slicer segments for all intermediate masks;
- femoral-head and final-ROI STL files;
- `<case>_onfh_v3_report.json`;
- `<case>_onfh_v3_summary.csv`.

The JSON report records the software version, configuration, thresholds,
measurements, QC findings, and output filenames. Patient DICOM and identifiable
metadata remain excluded from the repository.

## Validation Boundary

Synthetic tests verify deterministic algorithm behavior and software
reproducibility. Clinical validation requires a separate dataset with at least
two independent expert contours and adjudicated consensus. Recommended metrics
are Dice similarity, Jaccard index, 95% Hausdorff distance, average surface
distance, volume error, correction time, failure rate, and propagation of ROI
uncertainty into FEA outputs.

