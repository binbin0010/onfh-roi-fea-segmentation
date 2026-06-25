import unittest

import numpy as np

from scripts.slicer.onfh_v3_features import (
    build_anterosuperior_prior,
    build_spherical_geometry,
    compute_experimental_collapse_feature_score,
    compute_kerboul_like_3d_angles,
    compute_zone_involvement,
    seeded_region_grow,
)


def make_physical_sphere(
    shape=(52, 48, 44),
    spacing_zyx=(1.4, 1.1, 0.9),
    center_ras=(18.0, 23.0, 31.0),
    radius_mm=15.0,
):
    zz, yy, xx = np.indices(shape, dtype=float)
    right = xx * spacing_zyx[2]
    anterior = yy * spacing_zyx[1]
    superior = zz * spacing_zyx[0]
    radial = np.sqrt(
        (right - center_ras[0]) ** 2
        + (anterior - center_ras[1]) ** 2
        + (superior - center_ras[2]) ** 2
    )
    return {
        "mask": radial <= radius_mm,
        "right": right,
        "anterior": anterior,
        "superior": superior,
        "spacing": spacing_zyx,
        "center": center_ras,
        "radius": radius_mm,
    }


class SphericalGeometryTests(unittest.TestCase):
    def setUp(self):
        self.case = make_physical_sphere()
        self.geometry = build_spherical_geometry(
            self.case["mask"],
            self.case["spacing"],
            right_coordinates=self.case["right"],
            anterior_coordinates=self.case["anterior"],
            superior_coordinates=self.case["superior"],
        )

    def test_sphere_fit_recovers_physical_center_and_radius(self):
        fit = self.geometry["fit"]
        np.testing.assert_allclose(fit.center_ras_mm, self.case["center"], atol=0.7)
        self.assertAlmostEqual(fit.radius_mm, self.case["radius"], delta=0.7)
        self.assertLess(fit.rms_residual_mm, 1.0)
        self.assertEqual(fit.coordinate_source, "physical_ras")

    def test_normalized_radial_depth_is_surface_zero_and_center_high(self):
        depth = self.geometry["normalized_radial_depth"]
        center_index = np.unravel_index(
            np.argmin(self.geometry["radial_distance_mm"]), depth.shape
        )
        shell = self.case["mask"] & (
            self.geometry["distance_to_mask_surface_mm"] <= max(self.case["spacing"])
        )
        self.assertGreater(depth[center_index], 0.90)
        self.assertLess(float(np.median(depth[shell])), 0.15)
        self.assertTrue(np.all(depth[~self.case["mask"]] == 0.0))

    def test_missing_ras_arrays_is_labeled_as_voxel_physical_fallback(self):
        fallback = build_spherical_geometry(
            self.case["mask"],
            self.case["spacing"],
        )
        self.assertEqual(
            fallback["fit"].coordinate_source,
            "voxel_physical_fallback",
        )

    def test_anterosuperior_prior_favors_anterior_superior_voxels(self):
        score, zone = build_anterosuperior_prior(
            self.case["mask"],
            self.geometry,
            anterior_fraction=0.60,
            superior_fraction=0.45,
        )
        fit = self.geometry["fit"]
        anterior_superior = (
            self.case["mask"]
            & (self.case["anterior"] > fit.center_ras_mm[1] + 4.0)
            & (self.case["superior"] > fit.center_ras_mm[2] + 4.0)
        )
        posterior_superior = (
            self.case["mask"]
            & (self.case["anterior"] < fit.center_ras_mm[1] - 4.0)
            & (self.case["superior"] > fit.center_ras_mm[2] + 4.0)
        )
        self.assertGreater(
            float(np.mean(score[anterior_superior])),
            float(np.mean(score[posterior_superior])) + 0.15,
        )
        self.assertGreater(float(np.mean(zone[anterior_superior])), 0.75)
        self.assertLess(float(np.mean(zone[posterior_superior])), 0.40)


class SeededRegionGrowingTests(unittest.TestCase):
    def test_region_grow_retains_seed_connected_path_and_rejects_decoy(self):
        shape = (24, 24, 24)
        allowed = np.zeros(shape, dtype=bool)
        allowed[10:13, 4:18, 10:13] = True
        allowed[3:7, 3:7, 3:7] = True
        foreground = np.zeros(shape, dtype=bool)
        foreground[11, 5, 11] = True
        background = np.zeros(shape, dtype=bool)
        background[11, 17, 11] = True
        score = np.zeros(shape, dtype=float)
        score[allowed] = 0.72
        gradient = np.zeros(shape, dtype=float)
        gradient[10:13, 14, 10:13] = 0.95

        grown = seeded_region_grow(
            foreground_seed=foreground,
            background_seed=background,
            allowed_mask=allowed,
            combined_score=score,
            gradient_score=gradient,
            minimum_score=0.60,
            maximum_gradient=0.80,
            connectivity=1,
        )

        self.assertTrue(grown[11, 12, 11])
        self.assertFalse(grown[11, 16, 11])
        self.assertFalse(np.any(grown[3:7, 3:7, 3:7]))
        self.assertFalse(np.any(grown & background))


class ResearchMeasurementTests(unittest.TestCase):
    def setUp(self):
        self.case = make_physical_sphere(shape=(56, 56, 56), spacing_zyx=(1, 1, 1),
                                         center_ras=(28, 28, 28), radius_mm=20)
        self.geometry = build_spherical_geometry(
            self.case["mask"],
            self.case["spacing"],
            right_coordinates=self.case["right"],
            anterior_coordinates=self.case["anterior"],
            superior_coordinates=self.case["superior"],
        )

    def test_kerboul_like_angle_uses_coronal_and_sagittal_spans(self):
        fit = self.geometry["fit"]
        r = self.case["right"] - fit.center_ras_mm[0]
        a = self.case["anterior"] - fit.center_ras_mm[1]
        s = self.case["superior"] - fit.center_ras_mm[2]
        coronal_angle = np.degrees(np.arctan2(r, s))
        sagittal_angle = np.degrees(np.arctan2(a, s))
        roi = (
            self.case["mask"]
            & (coronal_angle >= -30.0)
            & (coronal_angle <= 30.0)
            & (sagittal_angle >= -20.0)
            & (sagittal_angle <= 20.0)
            & (s > 0)
        )

        angles = compute_kerboul_like_3d_angles(
            roi,
            self.geometry,
            right_coordinates=self.case["right"],
            anterior_coordinates=self.case["anterior"],
            superior_coordinates=self.case["superior"],
        )

        self.assertAlmostEqual(angles["coronal_span_deg"], 60.0, delta=8.0)
        self.assertAlmostEqual(angles["sagittal_span_deg"], 40.0, delta=8.0)
        self.assertAlmostEqual(angles["combined_angle_deg"], 100.0, delta=14.0)

    def test_zone_involvement_uses_zone_volume_as_denominator(self):
        roi = np.zeros((4, 4, 4), dtype=bool)
        subchondral = np.zeros_like(roi)
        weight_bearing = np.zeros_like(roi)
        subchondral.flat[:20] = True
        weight_bearing.flat[20:30] = True
        roi.flat[:10] = True
        roi.flat[20:22] = True

        metrics = compute_zone_involvement(roi, subchondral, weight_bearing)

        self.assertAlmostEqual(metrics["subchondral_involvement_percent"], 50.0)
        self.assertAlmostEqual(metrics["weight_bearing_involvement_percent"], 20.0)

    def test_experimental_feature_score_is_bounded_and_monotonic(self):
        low = compute_experimental_collapse_feature_score(
            subchondral_involvement_percent=10.0,
            weight_bearing_involvement_percent=10.0,
            combined_angle_deg=60.0,
        )
        high = compute_experimental_collapse_feature_score(
            subchondral_involvement_percent=80.0,
            weight_bearing_involvement_percent=70.0,
            combined_angle_deg=280.0,
        )
        self.assertGreaterEqual(low, 0.0)
        self.assertLessEqual(high, 100.0)
        self.assertGreater(high, low)


if __name__ == "__main__":
    unittest.main()
