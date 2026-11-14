"""Experimental drainage consistency features, not a hydraulic/direction truth model."""
from collections import Counter
import math
import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize

ARMS={'A':{'terrain'},'B':{'terrain','vegetation'},'C':{'terrain','water'},
      'D':{'terrain','morphology'},'E':{'terrain','outlet'},
      'F':{'terrain','vegetation','water','morphology','outlet'}}
for name in ['vegetation','water','morphology','outlet']:
    ARMS['F_no_'+name]=ARMS['F']-{name}


def indices(bands,valid,epsilon=1e-8):
    result={}
    for name,a,b in [('NDVI','nir','red'),('NDWI','green','nir'),('MNDWI','green','swir16')]:
        x,y=np.asarray(bands[a],float),np.asarray(bands[b],float)
        v=np.asarray(valid,bool)&np.isfinite(x)&np.isfinite(y)&(x>=0)&(y>=0)&(np.abs(x+y)>epsilon)
        result[name]=np.divide(x-y,x+y,out=np.full(x.shape,np.nan),where=v)
    return result


def longest_run(values):
    best=run=0
    for value in values:
        run=run+1 if value else 0
        best=max(best,run)
    return best


def sample(array,grid,xy,default=np.nan):
    xy=np.asarray(xy,float)
    rr=np.floor((xy[:,1]-grid.transform.f)/grid.transform.e).astype(int)
    cc=np.floor((xy[:,0]-grid.transform.c)/grid.transform.a).astype(int)
    inside=(rr>=0)&(cc>=0)&(rr<array.shape[0])&(cc<array.shape[1])
    result=np.full(len(xy),default,dtype=float)
    result[inside]=array[rr[inside],cc[inside]]
    return result


def points_on_line(line,spacing=10):
    # Equal-step interior quadrature, never inferred direction from coordinate order.
    distances=np.arange(spacing/2,line.length,spacing)
    if len(distances)==0:distances=np.array([line.length/2])
    xy=np.array([[line.interpolate(d).x,line.interpolate(d).y] for d in distances])
    tangent=np.array([[line.interpolate(min(line.length,d+1)).x-line.interpolate(max(0,d-1)).x,
                       line.interpolate(min(line.length,d+1)).y-line.interpolate(max(0,d-1)).y] for d in distances])
    norm=np.linalg.norm(tangent,axis=1)
    unit=np.divide(tangent,norm[:,None],out=np.zeros_like(tangent),where=norm[:,None]>0)
    normal=np.column_stack([-unit[:,1],unit[:,0]])
    return xy,distances,unit,np.concatenate([xy+75*normal,xy-75*normal])


def robust_width_slope(distances,widths,minimum_samples=5):
    d,w=np.asarray(distances),np.asarray(widths)
    v=np.isfinite(w)&np.isfinite(d)
    d,w=d[v],w[v]
    if len(d)<minimum_samples:return None
    i,j=np.triu_indices(len(d),1)
    usable=d[j]>d[i]
    return float(np.median((w[j[usable]]-w[i[usable]])/(d[j[usable]]-d[i[usable]]))) if usable.any() else None


def spectral_features(lines,arrays,valid,grid,protocol):
    configs=protocol['spectral'];pixel=abs(grid.transform.a)
    pts=[points_on_line(line,protocol['units']['sample_spacing_m']) for line in lines]
    rows=[]
    allvalid=np.asarray(valid,bool)&np.isfinite(arrays['NDVI'])&np.isfinite(arrays['NDWI'])&np.isfinite(arrays['MNDWI'])
    for xy,d,t,flank in pts:
        v=sample(allvalid,grid,xy,0)>0
        nd=sample(arrays['NDVI'],grid,xy)
        fl=sample(arrays['NDVI'],grid,flank)
        flvalid=sample(allvalid,grid,flank,0)>0
        base={'samples':len(xy),'clear_samples':int(v.sum()),'clear_fraction':float(v.mean()),
              'ndvi_median':float(np.median(nd[v])) if v.any() else None,
              'ndvi_corridor_minus_flank':float(np.median(nd[v])-np.median(fl[flvalid])) if v.any() and flvalid.any() else None,
              'vegetation':{},'water':{}}
        for threshold in configs['ndvi_thresholds']:
            low=v&(nd<threshold)
            base['vegetation'][str(threshold)]={'below_fraction':float(low.sum()/v.sum()) if v.any() else None,
                'longest_contiguous_below_fraction':longest_run(low)/v.sum() if v.any() else None}
        rows.append(base)
    quality_distance=ndimage.distance_transform_edt(np.pad(allvalid,1),sampling=pixel)[1:-1,1:-1]
    for name in ['NDWI','MNDWI']:
        for threshold in configs['water_thresholds']:
            water=allvalid&(arrays[name]>threshold)
            labels,count=ndimage.label(water,structure=np.array([[0,1,0],[1,1,1],[0,1,0]]))
            if water.any():
                distance,nearest=ndimage.distance_transform_edt(~water,sampling=pixel,return_indices=True)
                near_labels=labels[tuple(nearest)]
            else:
                distance=np.full(water.shape,np.inf);near_labels=np.zeros(water.shape,int)
            is_primary=name=='MNDWI' and threshold==0.0
            widths=None
            if is_primary and water.any():
                skeleton=skeletonize(water)
                radius=ndimage.distance_transform_edt(water,sampling=pixel)
                # Widths touching cloudy/unknown/image boundary are censored, not narrow.
                usable=skeleton&(quality_distance>radius+pixel)
                if usable.any():
                    ds,ix=ndimage.distance_transform_edt(~usable,sampling=pixel,return_indices=True)
                    widths=2*radius[tuple(ix)]
                    widths[(ds>protocol['units']['corridor_halfwidth_m'])|(widths<protocol['units']['minimum_width_m'])]=np.nan
            for result,(xy,d,t,flank) in zip(rows,pts):
                v=sample(allvalid,grid,xy,0)>0
                near=(sample(distance,grid,xy,np.inf)<=protocol['units']['corridor_halfwidth_m'])&v
                ids=sample(near_labels,grid,xy,0).astype(int);ids=ids[near]
                result['water'][name+':'+str(threshold)]={
                    'near_fraction':float(near.sum()/v.sum()) if v.any() else None,
                    'largest_component_fraction':max(Counter(ids.tolist()).values(),default=0)/v.sum() if v.any() else None,
                    'longest_contiguous_near_fraction':longest_run(near)/v.sum() if v.any() else None,
                    'scene_components':int(count),'scene_water_pixels':int(water.sum())}
                if is_primary:
                    ws=sample(widths,grid,xy) if widths is not None else np.full(len(xy),np.nan)
                    ws[~v]=np.nan
                    slope=robust_width_slope(d,ws,protocol['units']['minimum_width_samples'])
                    result['morphology']={'eligible_width_samples':int(np.isfinite(ws).sum()),
                        'median_apparent_width_m':float(np.nanmedian(ws)) if np.isfinite(ws).any() else None,
                        'width_slope_m_per_m':slope,
                        'total_width_trend_m':None if slope is None else float(slope*(d[-1]-d[0])),
                        'interpretation':'Censored skeleton-based wetted diameter, not bed depth/incision/flow direction'}
    return rows


def outlet_constraint(route_cells,outlet_cells,predictor_source_ids,evaluation_source_ids,known_physical=False):
    if set(predictor_source_ids)&set(evaluation_source_ids):
        raise ValueError('Outlet predictor and evaluation reference share source identity')
    if not known_physical or not outlet_cells:
        return {'available':False,'reason':'No independently established physical outlet supplied'}
    return {'available':True,'connected':len(route_cells)>1 and route_cells[-1] in set(outlet_cells),
            'predictor_source_ids':list(predictor_source_ids)}


def decision(features,arm,cell_m,target_width_m,protocol,outlet=None):
    evidence=ARMS[arm]
    def result(category,reason):
        return {'category':category,'reason':reason,'direction_asserted':category=='SUPPORTED_DIRECTION',
                'probability':None,'evidence_families':sorted(evidence)}
    if 2*cell_m>target_width_m:
        return result('INSUFFICIENT_SPATIAL_RESOLUTION','Declared target cannot be sampled by two terrain cells')
    if evidence-{'terrain','outlet'} and (not features or features['clear_fraction']<protocol['units']['minimum_clear_fraction']):
        return result('INSUFFICIENT_OBSERVATION','Required spectral samples fail clear-support gate')
    if 'water' in evidence:
        coverage=[features['water']['MNDWI:'+str(t)]['near_fraction'] for t in protocol['spectral']['water_thresholds']]
        if max(coverage)<protocol['features']['spectral_conflict_fraction']:
            return result('CONFLICTING_EVIDENCE','Clear observed-water corridor disagreement; not a verified DEM error')
    if 'outlet' in evidence:
        if not outlet or not outlet.get('available'):
            return result('REFERENCE_UNAVAILABLE','Independent known outlet constraint unavailable')
        if not outlet.get('connected'):
            return result('CONFLICTING_EVIDENCE','D8 route fails supplied independent outlet connectivity constraint')
    if 'morphology' in evidence and (not features.get('morphology') or features['morphology']['eligible_width_samples']<protocol['units']['minimum_width_samples']):
        return result('INSUFFICIENT_OBSERVATION','Insufficient resolved uncensored wetted-width samples')
    if 'vegetation' in evidence:
        occupancy=[v['below_fraction'] for v in features['vegetation'].values()]
        if max(occupancy)-min(occupancy)>protocol['features']['threshold_instability_range']:
            return result('AMBIGUOUS_DIRECTION','NDVI corridor designation sensitive to correlated thresholds')
    if 'outlet' in evidence and 'water' in evidence and outlet.get('connected'):
        return result('SUPPORTED_DIRECTION','Qualified consistency with supplied outlet and observed corridor; not physical validation')
    return result('AMBIGUOUS_DIRECTION','Terrain vector/width/vegetation alone cannot establish physical flow orientation')


def eligible_direction_score(rows):
    eligible=[r for r in rows if r.get('independent_verified_direction') and r.get('registration_verified') and r.get('scale_passed')]
    answered=[r for r in eligible if r.get('predicted_direction') is not None]
    return {'eligible':len(eligible),'answered':len(answered),
            'accuracy':sum(r['predicted_direction']==r['reference_direction'] for r in answered)/len(answered) if answered else None,
            'useful_answer_coverage':len(answered)/len(eligible) if eligible else None,
            'correct_error_flags':None if not eligible else sum(r.get('flag',False) and r.get('terrain_wrong',False) for r in eligible),
            'false_error_flags':None if not eligible else sum(r.get('flag',False) and not r.get('terrain_wrong',False) for r in eligible),
            'status':'VERIFIED_REFERENCE_EVALUATION' if eligible else 'BLOCKED_NO_ELIGIBLE_DIRECTION_REFERENCE'}
