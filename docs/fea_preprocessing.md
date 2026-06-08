# FEA Preprocessing Notes

The segmentation outputs are intended to support Mimics/3-matic/ANSYS finite
element preprocessing.

## Geometric Partitioning

1. Import femoral-head and final-ROI STL files into 3-matic Research.
2. Use Boolean operations to create:
   - host/relatively healthy femoral-head region;
   - lesion or graft-related ROI region;
   - fixation-device region when applicable.
3. Use conformal meshing at shared interfaces when separating material regions.
4. Export tetrahedral volume meshes to ANSYS-compatible formats.

## Material Assignment

The manuscript workflow assigns element-specific material properties from CT HU
values. The segmentation masks define geometric partitions; they should not be
interpreted as replacing HU-based stiffness mapping unless a simplified analysis
is explicitly stated.

## Boundary and Loading

Downstream FEA loading and constraints should be reported with:

- load vectors and gait phase;
- coordinate system;
- body-weight scaling;
- distal femur constraint;
- contact assumptions at graft-host and implant-bone interfaces;
- mesh convergence or sensitivity checks when available.
