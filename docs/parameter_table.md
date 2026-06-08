# Parameter Table

## Intensity Thresholds

| Target | Real HU | Mimics GV | Use |
|---|---:|---:|---|
| Bone | 300-2000 | 1324-3024 | Initial bone/femur mask context |
| Necrotic core | 10-300 | 1034-1324 | Low-attenuation necrotic candidate |
| Sclerotic rim | 600-1800 | 1624-2824 | High-attenuation rim candidate |

Mimics GV is defined here as `real HU + 1024`.

## Morphology

| Step | Parameter | Value |
|---|---|---|
| Femoral-head candidate band | superior femur fraction | 40% |
| Femoral-head separation | binary opening | 3 iterations |
| Small component exclusion | component size | <500 voxels ignored |
| Sclerotic-rim expansion | binary dilation | 3 iterations |
| ROI refinement | binary closing | 4 iterations |
| ROI fill | slice-wise hole filling | applied to every axial slice |

## Volume Measurements

```text
voxel volume (mm3) = dx * dy * dz
mask volume (mm3) = number of positive voxels * voxel volume
necrosis ratio (%) = final ROI volume / femoral-head volume * 100
```

## ARCO Reference Label

The scripts return a volume-based reference label only. Final ARCO staging must
be reviewed with imaging morphology, especially crescent sign and collapse.

| Script rule | Reference label |
|---|---|
| ratio < 15% and ROI volume < 1000 mm3 | ARCO I |
| ratio < 15% | ARCO I-II |
| 15% <= ratio <= 30% | ARCO II |
| ratio > 30% | ARCO III-IV, review crescent sign |
