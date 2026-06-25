# V3 Anatomy-Adaptive Algorithm

## Intended Use

V3 initializes an expert-reviewable CT ROI for ONFH research and FEA
preprocessing. It does not diagnose ONFH, determine viability, replace MRI, or
assign clinical stage.

## Inputs

- real-HU CT volume;
- affected-side femoral-head mask;
- voxel spacing in NumPy `(z, y, x)` order;
- physical RAS-superior coordinate array;
- versioned configuration.

## 1. Anatomical Constraint and Sphere Geometry

The femoral-head mask is a hard boundary. A physical distance transform defines
distance to the head surface. Voxels within the cortical margin are excluded
from final lesion candidates.

An algebraic least-squares sphere is fitted to the femoral-head surface in
physical right-anterior-superior (RAS) coordinates. The fit provides:

- physical head center;
- fitted head radius;
- sphere-fit residual;
- radial distance;
- normalized radial depth.

The measured mask surface remains the primary boundary. The sphere supplies a
stable coordinate frame and does not replace the patient-specific mask.

The subchondral score decreases linearly between the cortical margin and the
configured subchondral depth.

The weight-bearing score increases within the superior fraction of the head and
is modulated toward the anterior head. It is a soft anterosuperior location
prior and cannot independently label a lesion. If full RAS coordinates are
unavailable, the software uses voxel-aligned physical coordinates and emits
`PHYSICAL_RAS_FALLBACK`.

## 2. Adaptive CT Features

The reference population contains finite, cancellous-appearing voxels inside
the head after cortical-margin and extreme-density exclusion.

```text
low threshold =
  min(lower percentile,
      absolute low-HU ceiling,
      reference median - minimum contrast)

sclerotic threshold =
  bounded max(upper percentile, absolute sclerotic floor)
```

The absolute bounds prevent implausible thresholds. The patient-specific
percentiles reduce dependence on one fixed cutoff.

## 3. Sclerotic-Rim Proximity

A distance transform is calculated from the high-density rim candidate. The
rim-proximity score decreases linearly to zero over the configured distance.

Rim evidence supports a nearby low-density region but does not define a lesion
alone.

## 4. Feature Fusion and Seed Definition

```text
score =
  0.45 * low-density score
  + 0.20 * rim-proximity score
  + 0.20 * subchondral score
  + 0.15 * anterosuperior weight-bearing score
```

The candidate envelope requires either low-density evidence or sufficient
proximity to a sclerotic rim. High-confidence low-density voxels are foreground
seeds. Cortical-margin voxels and low-scoring normal-appearing cancellous
voxels are background seeds.

## 5. Gradient-Aware Seeded Region Growing

The HU gradient magnitude is calculated in physical spacing and normalized
within the analysis mask. Foreground seeds propagate only through voxels that:

- remain inside the candidate envelope;
- exceed the region-growing feature-score threshold;
- remain below the normalized gradient boundary threshold;
- do not intersect background seeds.

The implementation uses deterministic connected propagation and requires only
NumPy and SciPy. It is an explainable seeded region-growing method, not a
trained model.

## 6. Morphology

- components are measured in physical volume;
- small or seed-free components are removed;
- closing uses a spacing-aware ellipsoidal element;
- holes are filled;
- the result is re-confined to the analysis mask;
- rejected candidate components are exposed in `QC_WARNING_REGION`.

## 7. Research Measurements

The final expert-reviewable ROI is used to calculate:

- coronal angular span from the fitted sphere center;
- sagittal angular span from the fitted sphere center;
- 3D Kerboul-like combined angle as the sum of both spans;
- percentage of the subchondral band occupied by the ROI;
- percentage of the anterosuperior weight-bearing zone occupied by the ROI.

An experimental 0-100 collapse-feature score combines normalized subchondral
involvement (40%), weight-bearing involvement (40%), and combined angular extent
(20%). These coefficients are prespecified engineering weights. The score is
not calibrated against collapse outcomes and is not a probability, clinical
stage, or treatment threshold.

## 8. Outputs

Intermediate masks reveal why a voxel was considered:

- low density;
- high-density rim;
- subchondral location;
- anterosuperior weight-bearing location;
- foreground and background seeds;
- region-grown candidate;
- retained final ROI;
- rejected or suspicious QC region.

This transparency supports expert correction and algorithm ablation.

## Known Failure Modes

- severe metal artifact;
- very low bone density or osteoporosis;
- unusual reconstruction kernels;
- extensive postoperative graft or sclerosis;
- incomplete femoral-head field of view;
- inaccurate femoral-head separation;
- lesions without clear low-density or rim evidence;
- non-ONFH cysts or other low-density abnormalities.

Every failure mode requires image review. QC cannot identify all clinically
important errors.
