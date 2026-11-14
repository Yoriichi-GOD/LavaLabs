import unittest

import numpy as np
from affine import Affine
from shapely.geometry import LineString

from research.experiments.road_exposure import binary_label, downstream_distances, road_points
from research.terrain_exposure.hydrology import derive
from research.terrain_exposure.io import Grid


class RoadExposureTests(unittest.TestCase):
    def test_downstream_propagation_stops_at_missing_observation(self):
        g = Grid((3, 5), Affine(30, 0, 0, 0, -30, 90), "EPSG:32632")
        z = np.tile(np.arange(5., 0., -1.), (3, 1))
        valid = np.ones(g.shape, dtype=bool)
        hydro = derive(z, valid, g, 100000, "none")
        seed = np.zeros(g.shape, dtype=bool)
        seed[1, 0] = True
        valid[1, 2] = False
        path = downstream_distances(hydro, seed, valid)
        np.testing.assert_array_equal(path[1], [0, 30, np.inf, np.inf, np.inf])

    def test_road_sampling_retains_total_length(self):
        points, weights = road_points(LineString([(0, 0), (21, 0)]))
        self.assertEqual(len(points), 3)
        self.assertAlmostEqual(weights.sum(), 21)
        np.testing.assert_allclose(points[:, 0], [3.5, 10.5, 17.5])

    def test_unknown_road_grade_is_not_a_negative(self):
        self.assertIsNone(binary_label(None))
        self.assertIsNone(binary_label("unknown"))
        self.assertIs(binary_label("no"), False)
        self.assertIs(binary_label("yes"), True)


if __name__ == "__main__":
    unittest.main()
