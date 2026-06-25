# V3 Geometry, Region Growing, and Research Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the ONFH V3 research workflow with sphere-derived geometry, an anterosuperior location prior, seeded region growing, 3D Kerboul-like angular extent, zone-involvement metrics, and an explicitly uncalibrated collapse-feature score.

**Architecture:** Keep the public entry point in `onfh_v3_core.py`, but move reusable geometry and measurement logic into `onfh_v3_features.py`. The segmentation core will combine adaptive CT evidence, anatomical priors, gradient-aware seeded region growing, morphology, QC, and expert review. Slicer will provide physical RAS coordinate arrays so directional and angular features are calculated in patient coordinates.

**Tech Stack:** Python 3.10+, NumPy, SciPy, 3D Slicer, `unittest`.

---

### Task 1: Geometry and Directional Priors

**Files:**
- Create: `scripts/slicer/onfh_v3_features.py`
- Create: `tests/test_onfh_v3_features.py`

- [ ] Write failing tests for algebraic sphere fitting on anisotropic synthetic data, normalized radial depth, and an anterosuperior zone that favors physically anterior-superior voxels.
- [ ] Run `python -m unittest tests.test_onfh_v3_features -v` and confirm failures are caused by missing feature APIs.
- [ ] Implement:

```python
fit_sphere_to_mask(mask, spacing_zyx, right_coordinates=None,
                   anterior_coordinates=None, superior_coordinates=None)
build_spherical_geometry(mask, spacing_zyx, right_coordinates=None,
                         anterior_coordinates=None, superior_coordinates=None)
build_anterosuperior_prior(mask, geometry, anterior_fraction,
                           superior_fraction)
```

- [ ] Re-run the focused tests and confirm the fitted center, radius, residual, depth map, and directional zone pass.

### Task 2: Explainable Seeded Region Growing

**Files:**
- Modify: `scripts/slicer/onfh_v3_features.py`
- Modify: `tests/test_onfh_v3_features.py`

- [ ] Write failing tests showing that foreground-connected moderate-cost voxels are retained while background seeds and disconnected low-cost decoys are rejected.
- [ ] Implement:

```python
seeded_region_grow(foreground_seed, background_seed, allowed_mask,
                   combined_score, gradient_score, minimum_score,
                   maximum_gradient, connectivity)
```

- [ ] Use deterministic SciPy binary propagation over a score/gradient-constrained mask; no optional package is required.
- [ ] Re-run focused tests.

### Task 3: Research Measurements

**Files:**
- Modify: `scripts/slicer/onfh_v3_features.py`
- Modify: `tests/test_onfh_v3_features.py`

- [ ] Write failing tests for coronal and sagittal angular spans, combined 3D Kerboul-like angle, subchondral-zone involvement, weight-bearing-zone involvement, and bounded experimental score.
- [ ] Implement:

```python
compute_kerboul_like_3d_angles(roi, geometry)
compute_zone_involvement(roi, subchondral_band, weight_bearing_zone)
compute_experimental_collapse_feature_score(metrics, config)
```

- [ ] Define the score as an uncalibrated 0-100 feature composite, not a probability or clinical decision rule.
- [ ] Re-run focused tests.

### Task 4: Integrate with V3 Segmentation and QC

**Files:**
- Modify: `scripts/slicer/onfh_v3_core.py`
- Modify: `tests/test_onfh_v3_core.py`

- [ ] Write failing integration tests for new masks, metrics, threshold fields, sphere-fit QC, physical-coordinate fallback, and JSON/CSV scalar export.
- [ ] Extend `AdaptiveSegmentationConfig` with directional-prior, gradient, region-growing, sphere-fit, and experimental-score parameters.
- [ ] Extend `segment_onfh_roi()` with optional physical right/anterior arrays while retaining the existing superior-coordinate argument.
- [ ] Add masks `ANTEROSUPERIOR_ZONE`, `FOREGROUND_SEED`, and `REGION_GROWN_ROI`.
- [ ] Add geometry, angular, involvement, runtime-ready report fields and QC warnings.
- [ ] Re-run core and feature tests.

### Task 5: Slicer and Documentation

**Files:**
- Modify: `scripts/slicer/femoral_necrosis_pipeline_v3.py`
- Modify: `README.md`
- Modify: `docs/algorithm_v3.md`
- Modify: `docs/parameter_table.md`
- Modify: `docs/SOP.md`
- Modify: `docs/validation_protocol.md`
- Modify: `CHANGELOG.md`

- [ ] Generate RAS right, anterior, and superior coordinate arrays from the volume IJK-to-RAS matrix.
- [ ] Pass the arrays to the core and expose new intermediate masks in Slicer.
- [ ] Print the new research measurements without labeling them as validated collapse predictions.
- [ ] Document exact definitions and denominators for involvement percentages.
- [ ] State that the experimental score requires independent outcome calibration and external validation.

### Task 6: Verification

**Files:**
- Verify all modified files.

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `python -m py_compile scripts/slicer/onfh_v3_features.py scripts/slicer/onfh_v3_core.py scripts/slicer/femoral_necrosis_pipeline_v3.py`.
- [ ] Run whitespace and diff checks with `git diff --check` and inspect `git diff --stat`.
- [ ] Confirm all outputs are finite JSON/CSV scalars and no patient data or generated binary artifacts were added.
