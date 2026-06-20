# Code Availability Statements

## Manuscript-Associated V2 Statement

```text
Code availability
The scripts used for segmentation-assisted ROI initialization, mask refinement,
volume calculation, STL export, and finite-element preprocessing are available
at https://github.com/binbin0010/onfh-roi-fea-segmentation. Release v1.0.0
corresponds to the fixed-threshold workflow associated with this study.
Patient-level DICOM data and derived identifiable models are not publicly
available because of privacy and ethical restrictions.
```

## V3 Method-Development Statement

Use this statement only after the v3 branch is assigned an archived release or
DOI:

```text
Code availability
The anatomy-adaptive, expert-reviewed ONFH ROI initialization workflow is
available at [repository URL] and archived as [release/DOI]. The repository
contains the Slicer-independent NumPy/SciPy core, 3D Slicer integration,
synthetic unit tests, parameter definitions, structured QC, and reproducible
STL/JSON/CSV export. The software is intended for research use and requires
expert mask review. Clinical spatial validation against multi-expert consensus
contours is described separately and should not be inferred from software unit
tests. Patient-level DICOM data and derived models are not publicly shared.
```

## Release Boundary

- `v1.0.0`: manuscript-associated v2 fixed-threshold workflow.
- v3 development branch: adaptive anatomy-constrained workflow; not yet an
  archived clinical-validation release.
