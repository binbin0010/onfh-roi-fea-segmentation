import json
import unittest

import numpy as np
from scipy.ndimage import distance_transform_edt

from scripts.slicer.onfh_v3_core import (
    AdaptiveSegmentationConfig,
    evaluate_qc,
    make_csv_summary_row,
    make_json_safe_report,
    segment_onfh_roi,
)


def make_synthetic_head(shape=(48, 48, 48)):
    zz, yy, xx = np.indices(shape, dtype=float)
    center = np.array([24.0, 24.0, 24.0])
    head_radius = 16.0
    head_distance = np.sqrt(
        (zz - center[0]) ** 2 + (yy - center[1]) ** 2 + (xx - center[2]) ** 2
    )
    head = head_distance <= head_radius

    hu = np.full(shape, -1000.0, dtype=float)
    hu[head] = 340.0
    cortical_shell = head & (distance_transform_edt(head) <= 1.0)
    hu[cortical_shell] = 1200.0

    lesion_center = np.array([34.0, 24.0, 24.0])
    lesion_distance = np.sqrt(
        (zz - lesion_center[0]) ** 2
        + (yy - lesion_center[1]) ** 2
        + (xx - lesion_center[2]) ** 2
    )
    lesion = (lesion_distance <= 4.2) & head & ~cortical_shell
    rim = (
        (lesion_distance > 4.2)
        & (lesion_distance <= 6.2)
        & head
        & ~cortical_shell
    )
    hu[lesion] = 90.0
    hu[rim] = 850.0

    decoy_center = np.array([15.0, 24.0, 24.0])
    decoy_distance = np.sqrt(
        (zz - decoy_center[0]) ** 2
        + (yy - decoy_center[1]) ** 2
        + (xx - decoy_center[2]) ** 2
    )
    inferior_decoy = (decoy_distance <= 3.5) & head
    hu[inferior_decoy] = 80.0

    tiny_center = np.array([33.0, 33.0, 24.0])
    tiny_distance = np.sqrt(
        (zz - tiny_center[0]) ** 2
        + (yy - tiny_center[1]) ** 2
        + (xx - tiny_center[2]) ** 2
    )
    tiny_decoy = (tiny_distance <= 1.0) & head
    hu[tiny_decoy] = 70.0

    return {
        "hu": hu,
        "head": head,
        "superior": zz,
        "anterior": yy,
        "right": xx,
        "lesion": lesion,
        "rim": rim,
        "inferior_decoy": inferior_decoy,
        "tiny_decoy": tiny_decoy,
        "cortical_shell": cortical_shell,
    }


class AnatomyAdaptiveSegmentationTests(unittest.TestCase):
    def setUp(self):
        self.case = make_synthetic_head()
        self.config = AdaptiveSegmentationConfig(
            min_component_volume_mm3=40.0,
            closing_radius_mm=1.5,
        )
        self.result = segment_onfh_roi(
            hu_volume=self.case["hu"],
            femoral_head_mask=self.case["head"],
            spacing_zyx=(1.0, 1.0, 1.0),
            superior_coordinates=self.case["superior"],
            anterior_coordinates=self.case["anterior"],
            right_coordinates=self.case["right"],
            config=self.config,
        )

    def test_default_adaptive_reference_matches_v3_specification(self):
        defaults = AdaptiveSegmentationConfig()
        self.assertEqual(defaults.low_percentile, 20.0)
        self.assertEqual(defaults.high_percentile, 85.0)
        self.assertEqual(defaults.reference_min_hu, -100.0)
        self.assertEqual(defaults.reference_max_hu, 600.0)

    def test_adaptive_thresholds_and_features_identify_expected_tissue(self):
        self.assertGreater(self.result.thresholds["low_hu"], 50.0)
        self.assertLess(self.result.thresholds["low_hu"], 340.0)
        self.assertGreaterEqual(self.result.thresholds["sclerotic_hu"], 500.0)
        self.assertLessEqual(self.result.thresholds["sclerotic_hu"], 1000.0)

        low_overlap = (
            self.result.masks["LOW_DENSITY_CORE"] & self.case["lesion"]
        ).sum() / self.case["lesion"].sum()
        rim_overlap = (
            self.result.masks["SCLEROTIC_RIM"] & self.case["rim"]
        ).sum() / self.case["rim"].sum()
        self.assertGreater(low_overlap, 0.90)
        self.assertGreater(rim_overlap, 0.90)
        self.assertFalse(
            np.any(self.result.masks["SCLEROTIC_RIM"] & self.case["cortical_shell"])
        )

    def test_all_anatomical_priors_and_final_roi_remain_inside_head(self):
        for name, mask in self.result.masks.items():
            self.assertEqual(mask.shape, self.case["head"].shape, name)
            self.assertFalse(np.any(mask & ~self.case["head"]), name)

    def test_geometry_region_growing_and_research_features_are_reported(self):
        expected_masks = {
            "ANTEROSUPERIOR_ZONE",
            "FOREGROUND_SEED",
            "BACKGROUND_SEED",
            "REGION_GROWN_ROI",
        }
        self.assertTrue(expected_masks.issubset(self.result.masks))
        self.assertGreater(self.result.metrics["sphere_radius_mm"], 10.0)
        self.assertLess(self.result.metrics["sphere_fit_rms_mm"], 2.0)
        self.assertEqual(
            self.result.metrics["physical_coordinate_mode"], "physical_ras"
        )
        for key in (
            "kerboul_like_coronal_angle_deg",
            "kerboul_like_sagittal_angle_deg",
            "kerboul_like_combined_angle_deg",
            "subchondral_involvement_percent",
            "weight_bearing_involvement_percent",
            "experimental_collapse_feature_score",
        ):
            self.assertIn(key, self.result.metrics)
            self.assertTrue(np.isfinite(self.result.metrics[key]))
        self.assertGreater(
            (
                self.result.masks["REGION_GROWN_ROI"] & self.case["lesion"]
            ).sum(),
            0,
        )
        self.assertGreater(
            self.result.metrics["region_grown_voxel_count"],
            self.result.metrics["seed_voxel_count"],
        )
        self.assertEqual(
            self.result.metrics["candidate_voxel_count"],
            self.result.metrics["region_grown_voxel_count"],
        )

    def test_missing_full_ras_coordinates_is_exposed_as_qc_warning(self):
        fallback_result = segment_onfh_roi(
            hu_volume=self.case["hu"],
            femoral_head_mask=self.case["head"],
            spacing_zyx=(1.0, 1.0, 1.0),
            superior_coordinates=self.case["superior"],
            config=self.config,
        )
        codes = {item["code"] for item in fallback_result.qc["findings"]}
        self.assertIn("PHYSICAL_RAS_FALLBACK", codes)
        self.assertEqual(
            fallback_result.metrics["physical_coordinate_mode"],
            "voxel_physical_fallback",
        )

    def test_feature_fusion_retains_superior_lesion_and_rejects_inferior_decoy(self):
        final_roi = self.result.masks["NECROSIS_ROI_FINAL"]
        lesion_recall = (final_roi & self.case["lesion"]).sum() / self.case["lesion"].sum()
        decoy_recall = (
            final_roi & self.case["inferior_decoy"]
        ).sum() / self.case["inferior_decoy"].sum()
        self.assertGreater(lesion_recall, 0.70)
        self.assertLess(decoy_recall, 0.10)

    def test_small_isolated_component_is_removed_and_exposed_for_qc(self):
        final_roi = self.result.masks["NECROSIS_ROI_FINAL"]
        warning_region = self.result.masks["QC_WARNING_REGION"]
        self.assertFalse(np.any(final_roi & self.case["tiny_decoy"]))
        self.assertTrue(np.any(warning_region & self.case["tiny_decoy"]))

    def test_qc_flags_empty_and_oversized_rois(self):
        empty_qc = evaluate_qc(
            femoral_head_mask=self.case["head"],
            final_roi=np.zeros_like(self.case["head"]),
            low_density_core=np.zeros_like(self.case["head"]),
            sclerotic_rim=np.zeros_like(self.case["head"]),
            superior_coordinates=self.case["superior"],
            spacing_zyx=(1.0, 1.0, 1.0),
            reference_voxel_count=1000,
            config=self.config,
        )
        empty_codes = {item["code"] for item in empty_qc["findings"]}
        self.assertEqual(empty_qc["status"], "REVIEW")
        self.assertIn("ROI_EMPTY", empty_codes)

        oversized = self.case["head"].copy()
        oversized_qc = evaluate_qc(
            femoral_head_mask=self.case["head"],
            final_roi=oversized,
            low_density_core=oversized,
            sclerotic_rim=self.case["rim"],
            superior_coordinates=self.case["superior"],
            spacing_zyx=(1.0, 1.0, 1.0),
            reference_voxel_count=1000,
            config=self.config,
        )
        oversized_codes = {item["code"] for item in oversized_qc["findings"]}
        self.assertEqual(oversized_qc["status"], "REVIEW")
        self.assertIn("ROI_RATIO_HIGH", oversized_codes)

    def test_insufficient_reference_tissue_returns_auditable_fail_result(self):
        small = make_synthetic_head(shape=(20, 20, 20))
        small_config = AdaptiveSegmentationConfig(
            minimum_reference_voxels=10000,
            min_component_volume_mm3=5.0,
        )
        result = segment_onfh_roi(
            hu_volume=small["hu"],
            femoral_head_mask=small["head"],
            spacing_zyx=(1.0, 1.0, 1.0),
            superior_coordinates=small["superior"],
            config=small_config,
        )
        codes = {item["code"] for item in result.qc["findings"]}
        self.assertEqual(result.qc["status"], "FAIL")
        self.assertIn("REFERENCE_INSUFFICIENT", codes)
        report = make_json_safe_report(
            result,
            case_id="insufficient_reference",
            side="right",
            software_version="3.0.0",
        )
        json.dumps(report, allow_nan=False)

    def test_report_is_json_serializable_and_excludes_voxel_arrays(self):
        report = make_json_safe_report(
            self.result,
            case_id="synthetic_case",
            side="right",
            software_version="3.0.0",
        )
        encoded = json.dumps(report, sort_keys=True)
        self.assertIn("synthetic_case", encoded)
        self.assertIn("adaptive_thresholds_hu", report)
        self.assertIn("quality_control", report)
        self.assertIn("research_feature_status", report["method"])
        self.assertFalse(report["method"]["research_feature_status"]["validated_predictor"])
        self.assertNotIn("masks", report)

    def test_csv_summary_has_stable_scalar_fields(self):
        row = make_csv_summary_row(
            self.result,
            case_id="synthetic_case",
            side="right",
            software_version="3.0.0",
        )
        self.assertEqual(row["case_id"], "synthetic_case")
        self.assertEqual(row["side"], "right")
        self.assertEqual(row["software_version"], "3.0.0")
        self.assertIn("low_hu", row)
        self.assertIn("final_roi_mm3", row)
        self.assertIn("kerboul_like_combined_angle_deg", row)
        self.assertIn("subchondral_involvement_percent", row)
        self.assertIn("weight_bearing_involvement_percent", row)
        self.assertIn("experimental_collapse_feature_score", row)
        self.assertIn("qc_status", row)
        self.assertIsInstance(row["qc_codes"], str)
        self.assertFalse(any(isinstance(value, (dict, list, np.ndarray)) for value in row.values()))


if __name__ == "__main__":
    unittest.main()
