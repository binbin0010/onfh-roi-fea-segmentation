# Code Availability Statement

## Manuscript-Associated V3 Statement

```text
Code availability
The Version 3 (V3) anatomy-adaptive, segmentation-assisted workflow used for
ROI delineation and finite element analysis preprocessing in this study is
publicly available under the MIT License at
https://github.com/binbin0010/onfh-roi-fea-segmentation and archived as release
v3.0.0 at
https://github.com/binbin0010/onfh-roi-fea-segmentation/releases/tag/v3.0.0.
The repository contains the Slicer-independent NumPy/SciPy core, 3D Slicer
integration, synthetic unit tests, software environment, parameter table,
standard operating procedure, validation protocol, structured quality control,
FEA preprocessing documentation, and reproducible STL/JSON/CSV export. All
generated masks require expert review and correction when necessary before
measurement or FEA. Release v1.0.0 is retained only as the historical
fixed-threshold baseline and was not used for the analyses reported in the
current manuscript. Patient-level DICOM data, identifiable images,
patient-derived models, and institution-specific file paths are not publicly
shared. De-identified imaging data may be made available by the corresponding
author upon reasonable request, subject to institutional approval and
applicable privacy regulations.
```

## Release Boundary

- `v3.0.0`: manuscript-associated anatomy-adaptive V3 workflow.
- `v1.0.0`: historical fixed-threshold V2 baseline; not used in the current
  manuscript.

The V3 release supports computational reproducibility but does not by itself
constitute independent clinical validation. The software is intended for
research use with mandatory expert review and is not an autonomous diagnostic,
staging, prognostic, or treatment-decision system.
