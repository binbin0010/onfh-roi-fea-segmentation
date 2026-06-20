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

## 1. Anatomical Constraint

The femoral-head mask is a hard boundary. A physical distance transform defines
distance to the head surface. Voxels within the cortical margin are excluded
from final lesion candidates.

The subchondral score decreases linearly between the cortical margin and the
configured subchondral depth.

The superior weight-bearing score increases within the superior fraction of
the head. It is a soft location prior and cannot independently label a lesion.

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

## 4. Feature Fusion

```text
score =
  0.45 * low-density score
  + 0.20 * rim-proximity score
  + 0.20 * subchondral score
  + 0.15 * superior weight-bearing score
```

The candidate envelope requires either low-density evidence or sufficient
proximity to a sclerotic rim. Components must intersect a high-confidence
low-density seed.

## 5. Morphology

- components are measured in physical volume;
- small or seed-free components are removed;
- closing uses a spacing-aware ellipsoidal element;
- holes are filled;
- the result is re-confined to the analysis mask;
- rejected candidate components are exposed in `QC_WARNING_REGION`.

## 6. Outputs

Intermediate masks reveal why a voxel was considered:

- low density;
- high-density rim;
- subchondral location;
- superior weight-bearing location;
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

