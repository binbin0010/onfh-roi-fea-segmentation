# Parameter Table

## V3 Adaptive Intensity Parameters

| Parameter | Default | Purpose |
|---|---:|---|
| Lower reference percentile | 30% | Patient-specific low-density threshold candidate |
| Upper reference percentile | 85% | Patient-specific high-density threshold candidate |
| Reference HU interval | -100 to 1000 HU | Cancellous-appearing reference population |
| Low-density HU ceiling | 400 HU | Absolute safety bound |
| Minimum contrast below reference median | 40 HU | Prevents the normal median from becoming the low threshold |
| Sclerotic HU floor | 500 HU | Conservative lower safety bound |
| Sclerotic HU ceiling | 1800 HU | Excludes extreme cortical/metal density |
| Cortical exclusion threshold | 1500 HU | Removes extreme-density voxels from adaptive analysis |

V3 expects real HU. The Slicer wrapper checks for a likely Mimics-style offset
and converts `GV` to `HU` with `HU = GV - 1024` when indicated.

## V3 Anatomical Parameters

| Parameter | Default | Purpose |
|---|---:|---|
| Cortical margin | 1.0 mm | Prevents the final ROI from occupying the outer cortical shell |
| Subchondral depth | 8.0 mm | Soft prior for the subchondral region |
| Superior weight-bearing fraction | 45% | Soft prior for the superior head |
| Sclerotic-rim proximity | 6.0 mm | Distance over which rim evidence contributes |

These priors are continuous scores. They do not define a lesion independently.

## V3 Fusion Parameters

| Feature | Weight |
|---|---:|
| Low-density score | 0.45 |
| Sclerotic-rim proximity | 0.20 |
| Subchondral score | 0.20 |
| Superior weight-bearing score | 0.15 |

| Parameter | Default |
|---|---:|
| Final score threshold | 0.52 |
| High-confidence seed threshold | 0.58 |
| Rim-envelope threshold | 0.25 |
| Spacing-aware closing radius | 2.0 mm |
| Minimum component volume | 100 mm3 |

The weights and thresholds are prespecified development parameters. They must
be evaluated by ablation and external validation before clinical deployment.

## V3 QC Parameters

| QC rule | Default trigger |
|---|---:|
| Insufficient reference tissue | <500 voxels |
| Weak rim evidence | <20 mm3 |
| Unusually small ROI | <0.5% of head |
| Unusually large ROI | >65% of head |
| Inferior head zone | lowest 25% of superior range |
| Inferior extension warning | >10% of ROI in inferior zone |
| Fragmentation warning | >3 retained components |

## V2 Fixed-Threshold Baseline

| Target | Real HU | Mimics GV |
|---|---:|---:|
| Bone context | 300-2000 | 1324-3024 |
| Necrotic-core candidate | 10-300 | 1034-1324 |
| Sclerotic-rim candidate | 600-1800 | 1624-2824 |

| V2 morphology | Default |
|---|---:|
| Superior femur candidate fraction | 40% |
| Femoral-head opening | 3 iterations |
| Small component exclusion | <500 voxels |
| Sclerotic-rim dilation | 3 iterations |
| ROI closing | 4 iterations |
| Hole filling | slice-wise |

## Volume Equations

```text
voxel volume (mm3) = spacing_x * spacing_y * spacing_z
mask volume (mm3) = positive voxels * voxel volume
ROI/head ratio (%) = final ROI volume / femoral-head volume * 100
```

The ratio is a geometric software output. It must not be used alone to assign
ARCO stage or predict collapse.
