import tempfile,unittest
from pathlib import Path
import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from research.experiments.flow_vectors import normalized,angles,orientation,paired_summary,MeritField
from research.experiments.validation_identity import full_commit


class FlowVectorTest(unittest.TestCase):
    def test_full_verified_source_identity_required(self):
        for value in ['6408454','not-a-commit','']:
            with self.assertRaises(ValueError):full_commit(value)
        self.assertEqual(full_commit('a'*40),'a'*40)
    def test_missing_and_zero_vectors_stay_unknown(self):
        a=normalized([[1,0],None,[0,0]])
        np.testing.assert_allclose(a[0],[1,0]);self.assertTrue(np.isnan(a[1:]).all())
        self.assertIsNone(orientation([[0,0]],[[1,0]]))
    def test_right_angle_opposite_and_denominators(self):
        a=[[1,0],[1,0],[1,0],None];b=[[1,0],[0,1],[-1,0],[1,0]]
        s=paired_summary(a,b)
        self.assertEqual((s['samples'],s['paired_samples'],s['at_least_90deg']),(4,3,2))
        self.assertEqual(s['source_a_available'],3)
    def test_ties_and_perpendicular_unknown(self):
        self.assertIsNone(orientation([[1,0],[-1,0]],[[1,0],[1,0]]))
        self.assertIsNone(orientation([[0,1]],[[1,0]]))
    def test_reversal_is_180degrees(self):
        np.testing.assert_allclose(angles([[3,4]],[[-3,-4]]),[180])
    def test_merit_codes_are_not_interpolated_and_projected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'d.tif';t=Affine(.001,0,-107.1,0,-.001,51.6)
            with rasterio.open(path,'w',driver='GTiff',height=2,width=2,count=1,dtype='uint8',crs='EPSG:4326',transform=t) as dst:
                dst.write(np.array([[2,247],[0,255]],dtype='uint8'),1)
            xy=[Transformer.from_crs(4326,32613,always_xy=True).transform(*(t @ (c+.5,r+.5))) for r,c in [(0,0),(0,1),(1,0),(1,1)]]
            v,cells=MeritField(path).sample(xy,'EPSG:32613')
            self.assertTrue(np.isfinite(v[0]).all());self.assertTrue(np.isnan(v[1:]).all())
            # A geographic diagonal near51N is not a45-degree metric diagonal.
            self.assertGreater(abs(v[0,1]),abs(v[0,0]))
            np.testing.assert_array_equal(cells,[[0,0],[0,1],[1,0],[1,1]])


if __name__=='__main__':unittest.main()
