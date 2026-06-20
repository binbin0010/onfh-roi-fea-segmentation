# FEA Preprocessing and Provenance

## Purpose

The segmentation workflow creates reviewed geometric transfer objects for
Mimics, 3-matic, and ANSYS. Segmentation and FEA validation are separate.

## Required Inputs

- approved femoral-head surface;
- approved lesion- or graft-related ROI surface;
- implant geometry when applicable;
- source CT used for material mapping;
- JSON/CSV provenance report;
- record of manual segmentation and surface corrections.

## Geometric Partitioning

1. Import named STL files into 3-matic Research.
2. Verify coordinate system, units, side, and anatomical orientation.
3. Repair surface defects without altering reviewed clinical boundaries.
4. Use Boolean operations to create:
   - host or relatively healthy femoral-head region;
   - lesion- or graft-related ROI region;
   - fixation-device region.
5. Preserve conformal interfaces between material regions.
6. Document every manual surface edit and Boolean operation.

## Material Assignment

Segmentation masks define geometry. They do not replace HU-based stiffness
mapping.

Report:

- HU-to-density equation;
- density-to-modulus equation;
- HU clipping or extrapolation rules;
- Poisson ratio;
- implant material properties;
- whether calibration phantoms or internal references were used.

## Boundary and Loading Conditions

Report:

- gait phase and source dataset;
- force and moment vectors;
- coordinate system;
- body-weight scaling;
- distal constraint;
- graft-host and implant-bone contact assumptions;
- friction coefficient and justification;
- quasi-static or dynamic analysis choice.

## Mesh and Numerical Checks

At minimum:

- inspect element quality;
- perform a mesh-convergence or sensitivity analysis;
- confirm conformal interfaces;
- report element type and characteristic size;
- verify force direction and constraint orientation;
- check that peak values are not numerical artifacts at isolated nodes.

## Segmentation Uncertainty Propagation

For v3 validation, perturb the reviewed ROI boundary or compare independent
expert contours. Repeat FEA and quantify changes in:

- peak von Mises stress;
- average ROI stress;
- maximum displacement;
- strain energy;
- clinically interpreted stress-concentration regions.

This analysis determines whether segmentation differences materially alter the
engineering conclusion.

## Reproducibility Record

For each model, retain:

- anonymized case ID;
- script commit/release;
- JSON and CSV report;
- reviewed mask version;
- exported STL checksums where permitted;
- surface-edit log;
- mesh settings;
- material equations;
- contact definitions;
- loading vectors;
- solver version and settings.

Patient-derived models must remain in approved storage and must not be committed
to the public repository.
