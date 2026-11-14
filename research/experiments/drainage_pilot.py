"""Frozen, bounded, already-designated-development drainage consistency pilot."""
import argparse
from collections import Counter
import csv
import itertools
import json
import math
from pathlib import Path
import platform
import sys
import time
import numpy as np
import rasterio
from rasterio.warp import reproject,Resampling
from shapely.geometry import LineString,Point,shape,mapping
from shapely.ops import substring,linemerge,unary_union
from shapely import get_parts
from research.terrain_exposure.io import Grid,save_json,sha256,canonical_hash
from research.terrain_exposure.hydrology import derive
from research.cases.process_campaign import metric_grid,warp,roi,roi_geometry
from research.experiments.delhi_drainage import load_layer
from research.experiments.drainage_core import indices,spectral_features,points_on_line,sample,decision,ARMS,eligible_direction_score

ROOT=Path(__file__).resolve().parents[2]
PROTOCOL=ROOT/'research/experiments/drainage-consistency-20261112.json'
SCALE=ROOT/'research/experiments/drainage-scale-20261112.json'
CALIBRATION=ROOT/'research/experiments/drainage-calibration-20261112.json'


def csvfile(path,rows):
    if not rows:return
    with Path(path).open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def source_record(path,role):
    path=Path(path)
    return {'path':str(path.resolve()),'sha256':sha256(path),'bytes':path.stat().st_size,'role':role}


def regrid(path,grid,scale=1,offset=0,categorical=False):
    with rasterio.open(path) as src:
        values=src.read(1,masked=True).astype('float64').filled(np.nan)*scale+offset
        out=np.full(grid.shape,np.nan)
        reproject(values,out,src_transform=src.transform,src_crs=src.crs,src_nodata=np.nan,
                  dst_transform=grid.transform,dst_crs=grid.crs,dst_nodata=np.nan,
                  resampling=Resampling.nearest if categorical else Resampling.bilinear)
    return out


def effective_calibration(item,band,asset):
    if band=='scl':return 1,0
    flag=item['properties'].get('earthsearch:boa_offset_applied')
    if type(flag) is not bool:
        raise ValueError('Explicit provider offset convention required; do not guess calibration')
    scale=asset['scale'];offset=0 if flag else asset['offset']
    if not np.isfinite([scale,offset]).all() or scale<=0:raise ValueError('Invalid radiometric calibration')
    return scale,offset


def optical(case,source,optical_root,inputs):
    result=[]
    if case=='nepal':
        folder=source/'components/floodlab/data/automatic/event-fe47db331390/optical'
        expected={'2026-08-22':'ed892dbf52413907ed7f9f0ae58aca3d716c2e5fb452a54a0218d7dba2b2691b',
                  '2026-08-27':'964b26a5c8f218e6605c09fd929bac7849abd3acc4c3b334aa714809f89069a1'}
        for date,digest in expected.items():
            path=folder/date/'default.tif'
            if sha256(path)!=digest:raise ValueError('Frozen optical source changed')
            with rasterio.open(path) as src:
                a=src.read();g=Grid(src.shape,src.transform,src.crs.to_string())
            valid=np.isfinite(a).all(0)&(a[6]==1)&np.isin(a[5],[4,5,6])
            bands={key:a[i] for key,i in [('green',1),('red',2),('nir',3),('swir16',4)]}
            result.append({'date':date,'grid':g,'indices':indices(bands,valid),'valid':valid,'source':str(path)})
            inputs.append(source_record(path,'retained consumed optical development'))
        return result
    acquisition=json.loads((optical_root/'acquisition.json').read_text())
    for record in acquisition['records']:
        if record['case']!=case or record['state']!='ACQUIRED':continue
        assets={a['band']:a for a in record['assets']}
        item=json.loads((optical_root/Path(assets['swir16']['file']).parent/'item.json').read_text())
        # Work on the actual coarsest required optical band grid. Do not raise
        # Grid's safety limit or imply 10m detail in native20m SWIR/SCL.
        with rasterio.open(optical_root/assets['swir16']['file']) as src:g=Grid(src.shape,src.transform,src.crs.to_string())
        bands={}
        for name,a in assets.items():
            path=optical_root/a['file']
            if sha256(path)!=a['sha256']:raise ValueError('Acquired optical hash changed')
            gain,offset=effective_calibration(item,name,a)
            bands[name]=regrid(path,g,gain,offset,name=='scl')
            inputs.append(source_record(path,'new public optical development'))
        valid=np.isfinite(np.stack(list(bands.values()))).all(0)&np.isin(bands['scl'],[4,5,6])
        result.append({'date':record['date'],'grid':g,'indices':indices(bands,valid),'valid':valid,'source':record['item_id'],
                       'calibration':{'boa_offset_applied':item['properties']['earthsearch:boa_offset_applied'],
                                      'effective':{name:effective_calibration(item,name,a) for name,a in assets.items()}}})
    return result


def demfiles(source,case,inputs):
    folder=source/'research/datasets/local/campaign-20261107'/case
    inventory=json.loads((folder/'acquisition.json').read_text())
    selected=[]
    for asset in inventory['assets']:
        if asset.get('state')!='ACQUIRED' or not asset['receipt']['product'].startswith('CopernicusGLO30'):continue
        path=folder/asset['file']
        if sha256(path)!=asset['receipt']['sha256']:raise ValueError('Retained DEM identity changed')
        selected.append(path);inputs.append(source_record(path,'historical GLO30, not event terrain'))
    if not selected:raise ValueError('No declared DEM input')
    return selected


def stream_units(hydro,case):
    stream=hydro.streams.ravel()&hydro.valid.ravel();down=hydro.downstream.ravel()
    incoming=np.zeros(stream.size,int)
    for i in np.flatnonzero(stream):
        j=int(down[i])
        if j>=0 and stream[j]:incoming[j]+=1
    units=[];short=0
    for start in np.flatnonzero(stream&(incoming!=1)):
        route=[int(start)];current=int(start)
        for _ in range(stream.size):
            nxt=int(down[current])
            if nxt<0 or not stream[nxt]:break
            route.append(nxt);current=nxt
            if incoming[nxt]!=1:break
        if len(route)<2:short+=1;continue
        line=LineString([hydro.grid.centre(i) for i in route])
        for k,begin in enumerate(np.arange(0,line.length,300)):
            end=min(begin+300,line.length)
            if end-begin<90:short+=1;continue
            units.append({'id':f'{case}:{start}:{k}','geometry':substring(line,begin,end),
                          'reference_id':None,'construction':'primary D8 reach, direction is computational only'})
    return units,{'retained_units':len(units),'short_or_singleton_exclusions':short}


def drain_units(source,cfg,inputs):
    folder=source/'research/datasets/local/validation-20261107/delhi-official-v1'
    acq=json.loads((folder/'acquisition.json').read_text())
    record=next(r for r in acq['layers'] if r['service']=='DIFC/sangam' and r['layer_id']==3)
    rows=load_layer(folder,record)
    inputs.append(source_record(folder/record['file'],'already consumed native administrative reference'))
    inside=shape(roi_geometry(cfg['bbox'],cfg['crs']))
    units=[]
    for geometry,attrs in rows:
        clipped=geometry.intersection(inside)
        for k,line in enumerate(get_parts(clipped)):
            if line.geom_type!='LineString' or line.length<=0:continue
            units.append({'id':f'drain:{attrs["FID"]}:{k}','geometry':line,'reference_id':attrs['FID'],
                          'construction':'clipped mapped geometry only; directional attributes withheld from prediction'})
    return units,{'retained_units':len(units),'raw_features':len(rows),'positive_clipped_reference_ids':len(set(u['reference_id'] for u in units))},rows


def terrain_vectors(hydro,line,spacing=10):
    xy,d,t,flank=points_on_line(line,spacing)
    rr=np.floor((xy[:,1]-hydro.grid.transform.f)/hydro.grid.transform.e).astype(int)
    cc=np.floor((xy[:,0]-hydro.grid.transform.c)/hydro.grid.transform.a).astype(int)
    vectors=[]
    for r,c in zip(rr,cc):
        if r<0 or c<0 or r>=hydro.grid.shape[0] or c>=hydro.grid.shape[1] or not hydro.valid[r,c]:
            vectors.append(None);continue
        i=r*hydro.grid.shape[1]+c;j=int(hydro.downstream.ravel()[i])
        if j<0:vectors.append(None);continue
        a,b=hydro.grid.centre(i),hydro.grid.centre(j)
        vectors.append([b[0]-a[0],b[1]-a[1]])
    return xy,t,vectors


def terrain_features(hydro,line):
    xy,d,t,flank=points_on_line(line)
    original=sample(hydro.original,hydro.grid,xy);conditioned=sample(hydro.filled,hydro.grid,xy)
    hand=sample(hydro.hand,hydro.grid,xy);slope=sample(hydro.slope,hydro.grid,xy)
    v=np.isfinite(original)&np.isfinite(conditioned)
    def gradient(a):
        w=np.isfinite(a)
        return float((a[w][-1]-a[w][0])/(d[w][-1]-d[w][0])) if w.sum()>1 and d[w][-1]>d[w][0] else None
    return {'samples':len(xy),'valid_samples':int(v.sum()),
            'original_endpoint_gradient_m_per_m':gradient(original),'conditioned_endpoint_gradient_m_per_m':gradient(conditioned),
            'maximum_sampled_fill_m':float(np.max(conditioned[v]-original[v])) if v.any() else None,
            'median_hand_m':float(np.nanmedian(hand)) if np.isfinite(hand).any() else None,
            'median_slope_deg':float(np.nanmedian(slope)) if np.isfinite(slope).any() else None,
            'interpretation':'DSM surface gradients and modeled HAND, not surveyed bed/hydraulic gradient or incision'}


def temporal_features(line,observations,protocol):
    if len(observations)<2:return {'status':'INSUFFICIENT_OBSERVATION','common_samples':0}
    xy,d,t,flank=points_on_line(line)
    values=[]
    for obs in observations[:2]:
        valid=sample(obs['valid'],obs['grid'],xy,0)>0
        nd=sample(obs['indices']['NDVI'],obs['grid'],xy)
        mw=sample(obs['indices']['MNDWI'],obs['grid'],xy)
        values.append((valid&np.isfinite(nd)&np.isfinite(mw),nd,mw))
    common=values[0][0]&values[1][0]
    eligible=common.mean()>=protocol['units']['minimum_clear_fraction']
    return {'status':'CONDITIONAL_SHARED_COORDINATES_NOT_PHYSICAL_REGISTRATION' if eligible else 'INSUFFICIENT_OBSERVATION',
            'samples':len(xy),'common_samples':int(common.sum()),'common_fraction':float(common.mean()),
            'median_ndvi_change':float(np.median(values[1][1][common]-values[0][1][common])) if eligible else None,
            'water_both_fraction':float(((values[0][2]>0)&(values[1][2]>0)&common).sum()/common.sum()) if eligible else None,
            'observation_dates':[o['date'] for o in observations[:2]],'registration_verified':False}


def evaluate_administrative(predictions,native_rows):
    """Only called after predictions sealed. No physical-flow truth is claimed."""
    reference={attrs['FID']:(geometry,attrs) for geometry,attrs in native_rows}
    rows=[]
    for row in predictions:
        geometry,attrs=reference[row['reference_id']]
        parts=list(get_parts(geometry))
        if len(parts)!=1:
            rows.append({'id':row['id'],'status':'UNINITIALIZED_MULTIPART_ORIENTATION'});continue
        line=parts[0]
        try:
            start=Point(float(attrs['Long_From']),float(attrs['Lat_From']))
            end=Point(float(attrs['Long_To']),float(attrs['Lat_To']))
            forward=max(start.distance(Point(line.coords[0])),end.distance(Point(line.coords[-1])))
            reverse=max(start.distance(Point(line.coords[-1])),end.distance(Point(line.coords[0])))
        except (KeyError,TypeError,ValueError):
            rows.append({'id':row['id'],'status':'MISSING_DIRECTION_ANNOTATION'});continue
        if min(forward,reverse)>1 or not attrs.get('INLETNODE') or not attrs.get('OUTLETNODE'):
            rows.append({'id':row['id'],'status':'ANNOTATION_ENDPOINT_MISMATCH'});continue
        orientation=1 if forward<=reverse else -1
        # Every clipped sample is projected onto the full original line. Shapely
        # clipping may reverse coordinate order; never inherit that order as truth.
        cosines=[]
        for xy,vector in zip(row['sample_xy'],row['d8_vectors']):
            if vector is None:continue
            position=line.project(Point(xy));left=line.interpolate(max(0,position-1));right=line.interpolate(min(line.length,position+1))
            tangent=np.array([right.x-left.x,right.y-left.y])*orientation
            vector=np.asarray(vector);norm=np.linalg.norm(tangent)*np.linalg.norm(vector)
            if norm>0:cosines.append(float(np.dot(tangent,vector)/norm))
        rows.append({'id':row['id'],'status':'ADMINISTRATIVE_ANNOTATION_ONLY',
                     'source_id':attrs['FID'],'endpoint_match_m':min(forward,reverse),'samples':len(cosines),
                     'positive_cosine_samples':sum(v>0 for v in cosines),
                     'mean_cosine':float(np.mean(cosines)) if cosines else None,
                     'majority_agreement':sum(v>0 for v in cosines)>len(cosines)/2 if cosines else None,
                     'registration_verified':False,'independent_verified_direction':False,'scale_passed':False})
    return rows


def run(source_root,optical_root,output):
    started=time.perf_counter();source=Path(source_root);optical_root=Path(optical_root);out=Path(output)
    if out.exists():raise FileExistsError('Immutable run; choose a new output')
    out.mkdir(parents=True)
    p=json.loads(PROTOCOL.read_text());scale=json.loads(SCALE.read_text())
    cfgs=json.loads((ROOT/'research/experiments/case-campaign-20261107.json').read_text())['cases']
    inputs=[];summary={};ablation=[];sensitivity=[];threshold_rows=[];vegetation_rows=[]
    save_json(out/'protocol.json',p);save_json(out/'scale-clarification.json',scale)
    save_json(out/'calibration-clarification.json',json.loads(CALIBRATION.read_text()))
    for case in p['cases']:
        print(json.dumps({'case':case,'phase':'START'}),flush=True)
        folder=out/case;folder.mkdir();cfg=cfgs[case]
        files=demfiles(source,case,inputs)
        grid=metric_grid(cfg,30);z=warp(files,grid,Resampling.bilinear)
        valid=np.isfinite(z)&roi(cfg['bbox'],grid.shape,grid.transform,grid.crs)
        primary=derive(z,valid,grid,100000,'fill')
        native=None
        if case=='sangam-vihar':units,unitinfo,native=drain_units(source,cfg,inputs)
        else:units,unitinfo=stream_units(primary,case)
        if not units:raise ValueError('No units under declared fixed selection')
        lines=[u['geometry'] for u in units]
        observations=optical(case,source,optical_root,inputs)
        feature_dates=[]
        for observation in observations:
            feature_dates.append(spectral_features(lines,observation['indices'],observation['valid'],observation['grid'],p))
        primary_features=feature_dates[0] if feature_dates else [None]*len(units)
        features=[{'id':u['id'],'terrain':terrain_features(primary,u['geometry']),
                   'temporal':temporal_features(u['geometry'],observations,p),
                   'dates':[{'date':o['date'],'analysis_cell_m':abs(o['grid'].transform.a),**f[i]} for o,f in zip(observations,feature_dates)]} for i,u in enumerate(units)]
        save_json(folder/'spectral-features.json',features)
        save_json(folder/'units.geojson',{'type':'FeatureCollection','crs':{'type':'name','properties':{'name':grid.crs}},
            'features':[{'type':'Feature','geometry':mapping(u['geometry']),'properties':{k:v for k,v in u.items() if k!='geometry'}} for u in units]})
        predictions=[]
        for unit,feature in zip(units,primary_features):
            xy,t,vectors=terrain_vectors(primary,unit['geometry'])
            predictions.append({'id':unit['id'],'reference_id':unit['reference_id'],'length_m':unit['geometry'].length,
                'sample_xy':xy.tolist(),'d8_vectors':vectors,
                'arms':{arm:decision(feature,arm,30,scale['declared_target_width_m'][case],p) for arm in ARMS}})
        save_json(folder/'predictions.json',predictions)
        save_json(folder/'prediction-seal.json',{'protocol_sha256':sha256(PROTOCOL),'scale_sha256':sha256(SCALE),'calibration_sha256':sha256(CALIBRATION),
            'predictions_sha256':sha256(folder/'predictions.json'),'features_sha256':sha256(folder/'spectral-features.json'),
            'units_sha256':sha256(folder/'units.geojson'),'direction_attributes_used_by_predictors':False,
            'known_outlets_supplied':0,'independent_direction_labels_opened':False})
        for arm in ARMS:
            counts=Counter(row['arms'][arm]['category'] for row in predictions)
            ablation.append({'case':case,'arm':arm,'n':len(units),'direction_assertions':counts.get('SUPPORTED_DIRECTION',0),
                **{category:counts.get(category,0) for category in p['categories']}})
        # Direction-reference attributes are accessed only after the prediction seal.
        annotation=evaluate_administrative(predictions,native) if native is not None else []
        save_json(folder/'administrative-direction-diagnostic.json',annotation)
        eligible=eligible_direction_score(annotation)
        clear=sum(f is not None and f['clear_fraction']>=p['units']['minimum_clear_fraction'] for f in primary_features)
        summary[case]={'role':'DEVELOPMENT ONLY','unit_info':unitinfo,'units':len(units),'dates':[o['date'] for o in observations],
            'primary_clear_eligible_units':clear,'optical_calibration':[o.get('calibration',{'provider':'retained physical reflectance cube'}) for o in observations],
            'primary_terrain':primary.summary,'physical_direction_evaluation':eligible,
            'administrative_annotation_rows':len(annotation),'administrative_orientable_units':sum(r.get('majority_agreement') is not None for r in annotation),
            'administrative_majority_matches':sum(r.get('majority_agreement') is True for r in annotation),
            'not_accuracy':'Unverified administrative orientation diagnostic; no valid physical-error/false-flag denominator',
            'registration':'UNVERIFIED','known_outlets':0,'reference_independent_verified_directions':0}
        for i,(u,f) in enumerate(zip(units,primary_features)):
            if f:
                for key,value in f['water'].items():threshold_rows.append({'case':case,'id':u['id'],'family_threshold':key,
                    'clear_fraction':f['clear_fraction'],**value})
                for key,value in f['vegetation'].items():vegetation_rows.append({'case':case,'id':u['id'],'ndvi_threshold':key,
                    'clear_fraction':f['clear_fraction'],**value})
        # Same geometries for every terrain setting; no best-result reach selection.
        primary_vectors=[terrain_vectors(primary,line)[2] for line in lines]
        for cell,conditioning,area in itertools.product(p['dem']['resolution_m'],p['dem']['conditioning'],p['dem']['stream_area_m2']):
            if (cell,conditioning,area)==(30,'fill',100000):h=primary
            else:
                g=metric_grid(cfg,cell);a=warp(files,g,Resampling.bilinear)
                v=np.isfinite(a)&roi(cfg['bbox'],g.shape,g.transform,g.crs)
                h=derive(a,v,g,area,conditioning)
            changed=compared=0;stream_hits=total_valid=0
            from scipy.spatial import cKDTree
            cells=np.flatnonzero(h.streams&h.valid)
            tree=cKDTree([h.grid.centre(i) for i in cells]) if len(cells) else None
            for line,base in zip(lines,primary_vectors):
                xy,t,vectors=terrain_vectors(h,line)
                for a,b in zip(base,vectors):
                    if a is not None and b is not None:
                        compared+=1;changed+=np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))<.999999
                if tree is not None:
                    distances=tree.query(xy)[0];stream_hits+=int((distances<=30).sum());total_valid+=len(xy)
            sensitivity.append({'case':case,'cell_m':cell,'conditioning':conditioning,'stream_area_m2':area,
                'fixed_units':len(units),'stream_cells':int(h.streams.sum()),'outlets':h.summary['outlets'],
                'filled_cells':h.summary['filled_cells'],'maximum_fill_m':h.summary['maximum_fill_m'],
                'total_direction_samples':sum(len(v) for v in primary_vectors),
                'compared_direction_samples':compared,'changed_direction_samples':int(changed),
                'changed_fraction':changed/compared if compared else None,
                'fixed_unit_samples_within30m_stream':stream_hits,'fixed_unit_samples':total_valid,
                'location_association_fraction':stream_hits/total_valid if total_valid else None})
        print(json.dumps({'case':case,'phase':'COMPLETE','units':len(units),'clear':clear,'direction_eligible':eligible['eligible']}),flush=True)
    csvfile(out/'ablation.csv',ablation);csvfile(out/'terrain-sensitivity.csv',sensitivity);csvfile(out/'spectral-thresholds.csv',threshold_rows)
    csvfile(out/'ndvi-thresholds.csv',vegetation_rows)
    save_json(out/'inputs.json',inputs)
    summary['execution']={'seconds':time.perf_counter()-started,'python':sys.version,'platform':platform.platform(),
                          'protocol_sha256':sha256(PROTOCOL),'scale_sha256':sha256(SCALE),'calibration_sha256':sha256(CALIBRATION),'reserved_data_accessed':False}
    save_json(out/'summary.json',summary)
    files={str(f.relative_to(out)):sha256(f) for f in out.rglob('*') if f.is_file()}
    save_json(out/'manifest.json',{'state':'complete','files':files,'reference_scope':'No independently verified physical directions'})
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for key in ['source-root','optical-root','output']:parser.add_argument('--'+key,required=True)
    args=parser.parse_args();run(args.source_root,args.optical_root,args.output)
