import unittest
import numpy as np

from research.experiments.spectral_review import features, score


class SpectralReviewTests(unittest.TestCase):
    def test_disagreement_can_catch_false_negative_without_rewriting_prediction(self):
        # Index signs: MNDWI land, NDWI water, and two unflagged nearer-margin cells.
        image = np.array([[[1., 5., 5., 5.]], [[.5, 4., 5., 5.]],
                          [[.5, 6., 4., 4.]], [[4., 6., 4., 4.]]])
        prediction = features(image)
        ref = np.array([[[1, 1, 1, 1]], [[2, 1, 2, 2]]])
        result = score(prediction, ref, {"review_budget_fractions": [.25]})
        self.assertEqual(result["review"]["0.25"]["ndwi"]["captured_false_negative"], 1)
        self.assertEqual(result["review"]["0.25"]["margin"]["captured"], 0)
        self.assertFalse(prediction["water"][0, 0])

    def test_unknown_reference_and_invalid_band_are_excluded_from_all_arms(self):
        image = np.ones((4, 1, 3))
        image[1, 0, 2] = 0
        ref = np.array([[[1, 2, 1]], [[1, 2, 2]]])
        result = score(features(image), ref, {"review_budget_fractions": [1]})
        self.assertEqual(result["common_pixels"], 1)
        self.assertEqual(result["review"]["1"]["either"]["reviewed"], 1)
        self.assertEqual(result["hard_filter"]["mndwi_both"]["n"], 1)


if __name__ == "__main__":
    unittest.main()
