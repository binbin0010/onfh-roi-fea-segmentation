# Proposed Clinical Validation Protocol

## Objective

Evaluate whether v3 provides accurate and efficient expert-reviewed
initialization across scanners, disease patterns, and surgical states.

## Dataset

Use a prespecified cohort that includes:

- preoperative and postoperative CT;
- both affected sides;
- multiple scanners or reconstruction kernels;
- a range of ARCO stages and lesion sizes;
- collapsed and non-collapsed heads where appropriate;
- cases with sclerosis, cystic change, graft material, and metal artifact.

Separate development, internal test, and external test sets at the patient
level.

## Reference Standard

1. Two musculoskeletal radiologists or experienced ONFH clinicians independently
   delineate the lesion-related ROI.
2. Readers are blinded to algorithm output during initial contouring.
3. A third expert adjudicates disagreements.
4. Record contouring time and reader confidence.
5. Preserve independent contours and the adjudicated consensus.

MRI-CT registration may be used when MRI defines lesion extent more clearly.
Registration quality must be assessed separately.

## Comparators

- manual contouring without initialization;
- v2 fixed-threshold initialization;
- v3 anatomy-adaptive initialization;
- optional graph-cut or trained segmentation method when available.

All methods must use matched cases and evaluation masks.

## Primary Spatial Metrics

- Dice similarity coefficient;
- Jaccard index;
- 95% Hausdorff distance;
- average symmetric surface distance;
- absolute and relative volume error.

Report confidence intervals and per-case distributions, not only mean values.

## Geometry and Research-Feature Validation

Evaluate the new measurements against expert or independently derived
references:

- sphere center and radius repeatability;
- sphere-fit residual stratified by collapse and deformity;
- coronal, sagittal, and combined Kerboul-like angular agreement;
- subchondral-zone involvement agreement;
- anterosuperior weight-bearing-zone involvement agreement.

Use ICC and Bland-Altman analysis for continuous measurements. Report failures
where sphere fitting or physical-axis recovery is unreliable.

The experimental collapse-feature score requires a separate prognosis study:

1. prespecify the clinical endpoint and follow-up horizon;
2. separate development, calibration, and external test cohorts;
3. fit or recalibrate weights using only the development cohort;
4. report discrimination, calibration, confidence intervals, and decision
   analysis where appropriate;
5. compare against established clinical and imaging predictors;
6. do not select thresholds on the external test cohort.

Until that study is completed, report the score only as an exploratory imaging
feature, not as a predicted risk.

## Workflow Metrics

- initialization runtime;
- manual correction time;
- fraction of cases requiring correction;
- QC warning rate;
- algorithm failure rate;
- interobserver and intraobserver agreement;
- proportion of cases excluded and reasons.

## Ablation Analysis

Evaluate:

1. low-density feature alone;
2. fixed HU thresholds;
3. adaptive percentile thresholds;
4. adaptive features plus subchondral prior;
5. adaptive features plus weight-bearing prior;
6. full model with rim proximity;
7. full model without seeded region growing;
8. full model without the anterior component of the location prior;
9. full model without component filtering.

This identifies which components contribute to performance.

## Generalizability

Stratify by:

- scanner vendor;
- reconstruction kernel;
- slice thickness;
- osteoporosis or low bone density;
- preoperative versus postoperative CT;
- lesion size and location;
- presence of implants or artifact.

## FEA Uncertainty Propagation

Run matched FEA models using:

- each independent expert contour;
- adjudicated consensus;
- uncorrected v3 output;
- corrected v3 output.

Compare peak stress, ROI stress, displacement, strain energy, and location of
stress concentration. Report whether segmentation uncertainty changes the
engineering conclusion.

## Statistical Analysis

- use paired comparisons for matched methods;
- report effect sizes and confidence intervals;
- correct for multiple comparisons in ablation analyses;
- use ICC or appropriate agreement statistics for continuous measurements;
- use Bland-Altman analysis for volume agreement;
- prespecify clinically acceptable error margins;
- perform sample-size planning before data collection.

## Reporting

Follow relevant medical-imaging AI and software reporting guidance. Report
software version, exact parameters, excluded cases, failures, QC warnings,
manual corrections, and external-validation results. Synthetic unit tests must
be reported separately from clinical accuracy.
