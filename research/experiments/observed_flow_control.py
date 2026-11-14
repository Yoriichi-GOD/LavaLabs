"""Sealed terrain predictors, then conditional observed ADCP-vector evaluation.

Reference-specific protocol predates measurement access. This is one braided
river, not independent global basins, and coordinate/heading limitations remain.
"""
import argparse,csv,io,json,math,re,zipfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from affine import Affine
from rasterio.warp import Resampling
from research.terrain_exposure.io import Grid,save_json,sha256
from research.terrain_exposure.hydrology import derive
from research.cases.process_campaign import warp
from research.experiments.flow_vectors import MeritField,hydro_vectors,normalized,angles,cosines
from research.experiments.validation_identity import full_commit

ROOT=Path(__file__).resolve().parents[2]
PROTOCOL=ROOT/'research/experiments/observed-flow-20261112.json'


def prepare(geometry,inputs,output,source_commit):
    full_commit(source_commit)
    folder=Path(output).resolve();inputs=Path(inputs).resolve()
    if folder.exists():raise FileExistsError('Keep predictor attempts; use fresh output')
    folder.mkdir(parents=True)
    cfg=json.loads(Path(geometry).read_text());p=json.loads(PROTOCOL.read_text())
    seal=json.loads((inputs/'input-seal.json').read_text())
    if seal['geometry_sha256']!=sha256(geometry):raise ValueError('Geometry identity changed')
    for f in seal['files']:
        if sha256(inputs/f['name'])!=f['sha256']:raise ValueError('Input identity changed')
    paths=[inputs/f['name'] for f in seal['files'] if f['name'].startswith('copernicus-')]
    if len(paths)!=1:raise ValueError('Expected exactly one declared native terrain crop')
    fields=[];bounds=cfg['metric_domain_bounds']
    for cell in [30,90]:
        left,bottom=[math.floor(v/cell)*cell for v in bounds[:2]]
        right,top=[math.ceil(v/cell)*cell for v in bounds[2:]]
        g=Grid((round((top-bottom)/cell),round((right-left)/cell)),Affine(cell,0,left,0,-cell,top),'EPSG:32613')
        z=warp(paths,g,Resampling.bilinear)
        for conditioning in ['fill','none']:
            h=derive(z,np.isfinite(z),g,100000,conditioning)
            name=f'GLO30_{cell}m_{conditioning}';path=folder/(name+'.npz')
            np.savez_compressed(path,downstream=h.downstream,valid=h.valid)
            fields.append({'name':name,'file':path.name,'sha256':sha256(path),'grid':g.describe(),'hydrology':h.summary})
    merit=inputs/'flowdir71.tif';MeritField(merit) # Validate native codes before opening reference.
    result={'state':'PREDICTORS_SEALED','source_commit':source_commit,'protocol_sha256':sha256(PROTOCOL),
        'geometry_sha256':sha256(geometry),'input_seal_sha256':sha256(inputs/'input-seal.json'),
        'merit_file':str(merit),'merit_sha256':sha256(merit),'fields':fields,
        'velocity_columns_read':False,'known_physical_outlet':False,
        'outlet_gain':'BLOCKED unless a separate frozen input protocol is added before references open'}
    save_json(folder/'prediction-seal.json',result)
    print({'state':result['state'],'fields':len(fields),'velocity_columns_read':False},flush=True)


def field_models(predictions):
    predictions=Path(predictions).resolve();seal=json.loads((predictions/'prediction-seal.json').read_text())
    if seal['protocol_sha256']!=sha256(PROTOCOL):raise ValueError('Frozen reference protocol changed')
    fields={}
    for r in seal['fields']:
        path=predictions/r['file']
        if sha256(path)!=r['sha256']:raise ValueError('Sealed predictor changed')
        data=np.load(path);description=r['grid']
        g=Grid(tuple(description['shape']),Affine(*description['transform']),description['crs'])
        fields[r['name']]=SimpleNamespace(grid=g,valid=data['valid'],downstream=data['downstream'])
    if sha256(seal['merit_file'])!=seal['merit_sha256']:raise ValueError('Sealed MERIT changed')
    return fields,MeritField(seal['merit_file']),seal


def score(vectors,reference):
    angle=angles(vectors,reference);c=cosines(vectors,reference);ok=np.isfinite(angle)
    return {'reference_units':len(angle),'available':int(ok.sum()),'unavailable':int((~ok).sum()),
        'positive_cosine':int((c[ok]>1e-12).sum()),'at_most45deg':int((angle[ok]<=45+1e-9).sum()),
        'median_angle_deg':None if not ok.any() else float(np.median(angle[ok])),
        'p90_angle_deg':None if not ok.any() else float(np.percentile(angle[ok],90))}


def observed_blocks(rows,p):
    cfg=p['scoring'];years=rows[:,0].astype(int);xy=rows[:,1:3];velocity=rows[:,4:6]
    speed=np.linalg.norm(velocity,axis=1);eligible=np.isfinite(velocity).all(axis=1)&(speed>=cfg['reference_speed_min_m_s'])
    keys=np.column_stack([years,np.floor(xy/cfg['block_m']).astype(int)])
    blocks=[];excluded={'below_minimum_points':0,'incoherent':0}
    for key in sorted(set(map(tuple,keys))):
        allsupport=np.all(keys==key,axis=1);v=allsupport&eligible
        if v.sum()<cfg['block_min_points']:excluded['below_minimum_points']+=1;continue
        coherence=float(np.linalg.norm(normalized(velocity[v]).mean(axis=0)))
        if coherence<cfg['block_min_directional_coherence']:excluded['incoherent']+=1;continue
        blocks.append({'id':':'.join(map(str,key)),'year':int(key[0]),'points':int(v.sum()),
            'location':xy[v].mean(axis=0).tolist(),'reference_vector':velocity[v].mean(axis=0).tolist(),
            'coherence':coherence,'all_points_in_tile':int(allsupport.sum())})
    return blocks,{'all_rows':len(rows),'finite_velocity_rows':int(np.isfinite(velocity).all(axis=1).sum()),
        'speed_eligible_rows':int(eligible.sum()),'all_year_spatial_tiles':len(set(map(tuple,keys))),
        'eligible_blocks':len(blocks),'excluded_blocks':excluded},eligible


def evaluate(archive,predictions,output,source_commit):
    full_commit(source_commit)
    folder=Path(output).resolve()
    if folder.exists():raise FileExistsError('Preserve evaluations; use fresh output')
    folder.mkdir(parents=True)
    p=json.loads(PROTOCOL.read_text())
    if sha256(archive)!=p['reference']['archive_sha256']:raise ValueError('Reference archive identity changed')
    fields,merit,seal=field_models(predictions)
    # Reference becomes semantically unsealed here, after predictors and rules are hashed.
    records=[];member_counts=[]
    with zipfile.ZipFile(archive) as z:
        names=sorted(n for n in z.namelist() if re.fullmatch(r'data/adcp_20(15|16|17)_xs\d+\.csv',n))
        if len(names)!=50:raise ValueError('Expected all50 published transects')
        for name in names:
            values=[]
            for i,row in enumerate(csv.reader(io.StringIO(z.read(name).decode('utf-8-sig')))):
                if not row or not any(row):continue
                try:v=[float(value) for value in row]
                except ValueError:
                    if i>0:raise
                    continue
                if len(v)!=5:raise ValueError('Five source columns required')
                values.append(v)
            year=int(re.search(r'20\d\d',name)[0])
            records.extend([[year,*r] for r in values]);member_counts.append({'member':name,'rows':len(values)})
    rows=np.asarray(records,float)
    blocks,coverage,roweligible=observed_blocks(rows,p)
    if not blocks:raise ValueError('No eligible reference blocks; do not invent a score')
    xy=np.asarray([r['location'] for r in blocks]);reference=np.asarray([r['reference_vector'] for r in blocks])
    vectors={name:hydro_vectors(h,xy) for name,h in fields.items()}
    vectors['MERIT_derived_native']=merit.sample(xy,'EPSG:32613')[0]
    common=np.logical_and.reduce([np.isfinite(v).all(axis=1) for v in vectors.values()])
    results={};paired=[];stress=[];point=[]
    for year in [2015,2016,2017]:
        selected=np.array([r['year']==year for r in blocks]);matched=selected&common
        results[str(year)]={'eligible_blocks':int(selected.sum()),'common_blocks_all_sources':int(matched.sum()),
            'own_support':{name:score(v[selected],reference[selected]) for name,v in vectors.items()},
            'matched_support':{name:score(v[matched],reference[matched]) for name,v in vectors.items()}}
        a=angles(vectors['GLO30_30m_fill'][matched],reference[matched])
        for name in vectors:
            b=angles(vectors[name][matched],reference[matched])
            paired.append({'year':year,'against':'GLO30_30m_fill','source':name,'blocks':len(a),
                'lower_angular_error':int((b<a-1e-9).sum()),'higher_angular_error':int((b>a+1e-9).sum()),
                'tie':int((np.abs(b-a)<=1e-9).sum()),
                'mean_angle_difference_deg':None if not len(a) else float(np.mean(b-a))})
    for distance in p['scoring']['position_stress_m']:
        shifts=[(0,0)] if distance==0 else [(distance,0),(-distance,0),(0,distance),(0,-distance)]
        for dx,dy in shifts:
            shifted={name:hydro_vectors(h,xy+[dx,dy]) for name,h in fields.items()}
            shifted['MERIT_derived_native']=merit.sample(xy+[dx,dy],'EPSG:32613')[0]
            for heading in p['scoring']['heading_stress_degrees']:
                theta=np.radians(heading);rotation=np.array([[np.cos(theta),-np.sin(theta)],[np.sin(theta),np.cos(theta)]])
                rotated=reference @ rotation.T
                for name,v in shifted.items():
                    stress.append({'source':name,'dx_m':dx,'dy_m':dy,'reference_heading_offset_deg':heading,
                        **score(v[common],rotated[common])})
    for name,h in list(fields.items())+[('MERIT_derived_native',merit)]:
        v=merit.sample(rows[roweligible,1:3],'EPSG:32613')[0] if name=='MERIT_derived_native' else hydro_vectors(h,rows[roweligible,1:3])
        point.append({'source':name,**score(v,rows[roweligible,4:6]),'role':'CORRELATED_POINT_DIAGNOSTIC'})
    detailed=[]
    for i,block in enumerate(blocks):
        detailed.append({**block,'common_all_sources':bool(common[i]),'predictions':{
            name:{'vector':None if not np.isfinite(v[i]).all() else v[i].tolist(),
                  'angle_deg':None if not np.isfinite(v[i]).all() else float(angles(v[i:i+1],reference[i:i+1])[0])}
            for name,v in vectors.items()}})
    summary={'schema':'satquery.observed-flow-control-result/1','source_commit':source_commit,
        'protocol_sha256':sha256(PROTOCOL),'reference_archive_sha256':sha256(archive),
        'prediction_seal_sha256':sha256(Path(predictions)/'prediction-seal.json'),
        'coverage':coverage,'survey_years':results,'paired_angular_comparisons':paired,
        'coordinate_status':'COMPANION_INFERRED_UTM13N; no measured absolute registration/heading residual',
        'scope':'Conditional agreement with observed local flow in one braided river; not regional/global routing accuracy',
        'independent_basins':1,'known_physical_outlets':0,'fusion_gain':None,'physical_registration_verified':False}
    save_json(folder/'summary.json',summary);save_json(folder/'blocks.json',detailed)
    save_json(folder/'registration-heading-stress.json',stress);save_json(folder/'point-diagnostic.json',point)
    save_json(folder/'reference-members.json',member_counts)
    save_json(folder/'manifest.json',{'files':{f.name:sha256(f) for f in sorted(folder.glob('*.json'))}})
    print({'state':'EVALUATED','coverage':coverage,'years':{y:v['matched_support'] for y,v in results.items()}},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare')
    for name in ['geometry','inputs','output','source-commit']:p.add_argument('--'+name,required=True)
    e=sub.add_parser('evaluate')
    for name in ['archive','predictions','output','source-commit']:e.add_argument('--'+name,required=True)
    a=vars(parser.parse_args());command=a.pop('command');a={k.replace('-','_'):v for k,v in a.items()}
    (prepare if command=='prepare' else evaluate)(**a)
