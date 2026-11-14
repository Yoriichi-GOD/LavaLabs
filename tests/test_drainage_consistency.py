import json
from pathlib import Path
import unittest
import tempfile
import numpy as np
import rasterio
from affine import Affine
from shapely.geometry import LineString
from research.terrain_exposure.io import Grid
from research.experiments.drainage_core import indices,spectral_features,decision,outlet_constraint,eligible_direction_score,robust_width_slope,ARMS
from research.experiments.drainage_pilot import evaluate_administrative,optical,effective_calibration
from research.terrain_exposure.io import sha256
from scripts.verify_drainage_pilot import check_ablation_rows

P=json.loads((Path(__file__).resolve().parents[1]/'research/experiments/drainage-consistency-20261112.json').read_text())


class DrainageTests(unittest.TestCase):
    def feature(self):
        return {'clear_fraction':1.,'water':{'MNDWI:'+str(t):{'near_fraction':1.} for t in P['spectral']['water_thresholds']},
                'vegetation':{str(t):{'below_fraction':0.} for t in P['spectral']['ndvi_thresholds']},
                'morphology':{'eligible_width_samples':10}}

    def test_indices_known_values_and_zero_denominator(self):
        a={k:np.array([[v,0.]]) for k,v in {'red':.2,'green':.3,'nir':.6,'swir16':.1}.items()}
        result=indices(a,np.ones((1,2),bool))
        self.assertAlmostEqual(result['NDVI'][0,0],.5)
        self.assertAlmostEqual(result['NDWI'][0,0],-1/3)
        self.assertAlmostEqual(result['MNDWI'][0,0],.5)
        self.assertTrue(all(np.isnan(x[0,1]) for x in result.values()))

    def test_unknown_is_not_water_absence(self):
        f=self.feature();f['clear_fraction']=.79
        self.assertEqual(decision(f,'C',30,60,P)['category'],'INSUFFICIENT_OBSERVATION')

    def test_scale_precedes_good_spectral_evidence(self):
        for arm in ARMS:
            self.assertEqual(decision(self.feature(),arm,30,1,P)['category'],'INSUFFICIENT_SPATIAL_RESOLUTION')

    def test_thresholds_do_not_create_independent_direction_votes(self):
        for arm in ['A','B','C','D']:
            self.assertFalse(decision(self.feature(),arm,30,60,P)['direction_asserted'])

    def test_explicit_outlet_missingness(self):
        self.assertEqual(decision(self.feature(),'E',30,60,P)['category'],'REFERENCE_UNAVAILABLE')
        self.assertEqual(decision(self.feature(),'F',30,60,P)['category'],'REFERENCE_UNAVAILABLE')

    def test_reference_leakage_rejected(self):
        with self.assertRaises(ValueError):outlet_constraint([1,2],[2],['same'],['same'],True)

    def test_boundary_is_not_automatically_known_outlet(self):
        self.assertFalse(outlet_constraint([1,2],[2],['dem'],['survey'],False)['available'])

    def test_independent_outlet_connection_and_reversal(self):
        o=outlet_constraint([1,2,3],[3],['outlet-survey'],['interior-survey'],True)
        self.assertTrue(decision(self.feature(),'F',30,60,P,o)['direction_asserted'])
        o=outlet_constraint([3,2,1],[3],['outlet-survey'],['interior-survey'],True)
        self.assertEqual(decision(self.feature(),'F',30,60,P,o)['category'],'CONFLICTING_EVIDENCE')

    def test_width_slope_changes_sign_when_order_reversed(self):
        d=np.arange(7)*10.;w=np.arange(7)*2.+40
        self.assertAlmostEqual(robust_width_slope(d,w),.2)
        self.assertAlmostEqual(robust_width_slope(d,w[::-1]),-.2)
        self.assertIsNone(robust_width_slope(d,np.full(7,np.nan)))

    def test_clear_disagreement_is_not_accuracy(self):
        f=self.feature()
        for v in f['water'].values():v['near_fraction']=0.
        self.assertEqual(decision(f,'C',30,60,P)['category'],'CONFLICTING_EVIDENCE')
        self.assertIsNone(eligible_direction_score([])['accuracy'])

    def test_unregistered_reference_cannot_be_promoted(self):
        r={'independent_verified_direction':True,'registration_verified':False,'scale_passed':True,
           'predicted_direction':1,'reference_direction':1}
        self.assertEqual(eligible_direction_score([r])['eligible'],0)

    def test_known_eligible_metric_with_abstention(self):
        base={'independent_verified_direction':True,'registration_verified':True,'scale_passed':True,'reference_direction':1}
        score=eligible_direction_score([{**base,'predicted_direction':1},{**base,'predicted_direction':None}])
        self.assertEqual(score['eligible'],2);self.assertEqual(score['accuracy'],1.)
        self.assertEqual(score['useful_answer_coverage'],.5)

    def test_straight_channel_continuity_and_width_are_symmetric(self):
        grid=Grid((41,61),Affine(10,0,0,0,-10,410),'EPSG:32644')
        v=np.ones(grid.shape,bool);water=np.full(grid.shape,-.8);water[17:24,:]=.8
        a={'NDVI':np.full(grid.shape,-.2),'NDWI':water,'MNDWI':water}
        line=LineString([(100,205),(500,205)])
        forward,reverse=spectral_features([line,LineString(list(line.coords)[::-1])],a,v,grid,P)
        self.assertEqual(forward['water']['MNDWI:0.0']['near_fraction'],1.)
        self.assertEqual(forward['water'],reverse['water'])
        self.assertEqual(forward['morphology']['median_apparent_width_m'],reverse['morphology']['median_apparent_width_m'])
        self.assertFalse(decision(forward,'D',30,60,P)['direction_asserted'])

    def test_reference_geometry_order_is_not_direction_truth(self):
        # Original polyline coordinates run west, official From->To runs east.
        geometry=LineString([(100,0),(0,0)])
        attrs={'FID':1,'Long_From':0,'Lat_From':0,'Long_To':100,'Lat_To':0,
               'INLETNODE':'A','OUTLETNODE':'B'}
        prediction={'id':'unit','reference_id':1,'sample_xy':[[25,0],[75,0]],'d8_vectors':[[30,0],[30,0]]}
        row=evaluate_administrative([prediction],[(geometry,attrs)])[0]
        self.assertEqual(row['positive_cosine_samples'],2)
        self.assertTrue(row['majority_agreement'])
        self.assertFalse(row['independent_verified_direction'])

    def test_unmatched_reference_endpoints_are_unknown(self):
        geometry=LineString([(0,0),(100,0)])
        attrs={'FID':1,'Long_From':1000,'Lat_From':0,'Long_To':1100,'Lat_To':0,
               'INLETNODE':'A','OUTLETNODE':'B'}
        prediction={'id':'unit','reference_id':1,'sample_xy':[[25,0]],'d8_vectors':[[30,0]]}
        self.assertEqual(evaluate_administrative([prediction],[(geometry,attrs)])[0]['status'],'ANNOTATION_ENDPOINT_MISMATCH')

    def test_urban_processing_uses_native_coarsest_required_grid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);assets=[]
            for band in ['blue','green','red','nir','swir16','scl']:
                coarse=band in ['swir16','scl'];cell=20 if coarse else 10;n=4 if coarse else 8
                values=np.full((n,n),4 if band=='scl' else 1000,dtype='uint16')
                file=root/(band+'.tif')
                with rasterio.open(file,'w',driver='GTiff',height=n,width=n,count=1,dtype='uint16',
                                   crs='EPSG:32644',transform=Affine(cell,0,0,0,-cell,80)) as dst:dst.write(values,1)
                assets.append({'band':band,'file':file.name,'sha256':sha256(file),'scale':1 if band=='scl' else .0001,'offset':0})
            (root/'acquisition.json').write_text(json.dumps({'records':[{'case':'varanasi','state':'ACQUIRED',
                'date':'2023-10-01','item_id':'synthetic-grid-check','assets':assets}]}))
            (root/'item.json').write_text(json.dumps({'properties':{'earthsearch:boa_offset_applied':True}}))
            obs=optical('varanasi',root,root,[])[0]
            self.assertEqual(obs['grid'].shape,(4,4))
            self.assertEqual(obs['grid'].transform.a,20)

    def test_already_applied_provider_offset_is_not_applied_twice(self):
        asset={'scale':.0001,'offset':-.1}
        self.assertEqual(effective_calibration({'properties':{'earthsearch:boa_offset_applied':True}},'red',asset),(.0001,0))
        self.assertEqual(effective_calibration({'properties':{'earthsearch:boa_offset_applied':False}},'red',asset),(.0001,-.1))
        with self.assertRaises(ValueError):effective_calibration({'properties':{}},'red',asset)

    def test_negative_reflectance_is_unknown_not_extreme_ndvi(self):
        bands={k:np.array([[v]]) for k,v in {'red':-.05,'green':.1,'nir':.3,'swir16':.1}.items()}
        self.assertTrue(np.isnan(indices(bands,np.ones((1,1),bool))['NDVI'][0,0]))

    def test_recount_joins_arm_identity_not_json_key_order(self):
        expected=[{'case':'c','arm':'F_no_water','n':2},{'case':'c','arm':'F_no_morphology','n':3}]
        recorded=[{'case':'c','arm':'F_no_morphology','n':'3'},{'case':'c','arm':'F_no_water','n':'2'}]
        check_ablation_rows(expected,recorded)
        recorded[1]['n']='99'
        with self.assertRaises(AssertionError):check_ablation_rows(expected,recorded)


if __name__=='__main__':unittest.main()
