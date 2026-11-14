"""Frozen same-unit source comparison. MERIT agreement is never called accuracy."""
import argparse,csv,json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import Resampling
from shapely.geometry import shape
from research.experiments.flow_vectors import MeritField,normalized,orientation,hydro_vectors,paired_summary,cosines
from research.experiments.drainage_core import points_on_line
from research.experiments.drainage_pilot import demfiles
from research.cases.process_campaign import metric_grid,warp,roi
from research.terrain_exposure.hydrology import derive
from research.terrain_exposure.io import save_json,sha256
from research.experiments.validation_identity import full_commit

ROOT=Path(__file__).resolve().parents[2]
PROTOCOL=ROOT/'research/experiments/drainage-validation-20261112.json'


def feature_flags(feature,pilot):
    if not feature['dates']:return {'clear':False,'water_warning':None,'vegetation_unstable':None,'width_trend':None}
    f=feature['dates'][0];clear=f['clear_fraction']>=pilot['units']['minimum_clear_fraction']
    values=[f['water']['MNDWI:'+str(t)]['near_fraction'] for t in pilot['spectral']['water_thresholds']]
    vegetation=[f['vegetation'][str(t)]['below_fraction'] for t in pilot['spectral']['ndvi_thresholds']]
    width=f['morphology']['total_width_trend_m']
    return {'clear':bool(clear),'water_warning':bool(max(values)<pilot['features']['spectral_conflict_fraction']) if clear else None,
        'vegetation_unstable':bool(max(vegetation)-min(vegetation)>pilot['features']['threshold_instability_range']) if clear else None,
        'width_trend':None if not clear or width is None else 'widening' if width>=20 else 'narrowing' if width<=-20 else 'small',
        'width_support':f['morphology']['eligible_width_samples']}


def run(source_root,prior_root,acquisition,output,source_commit):
    full_commit(source_commit)
    out=Path(output).resolve()
    if out.exists():raise FileExistsError('Retain runs; choose fresh output')
    out.mkdir(parents=True)
    source,prior,acq=map(lambda p:Path(p).resolve(),[source_root,prior_root,acquisition])
    p=json.loads(PROTOCOL.read_text());pilot=json.loads((prior/'protocol.json').read_text())
    manifest=json.loads((prior/'manifest.json').read_text())['files']
    cfgs=json.loads((ROOT/'research/experiments/case-campaign-20261107.json').read_text())['cases']
    acquired=json.loads((acq/'acquisition.json').read_text())
    if acquired['state']!='COMPLETE':raise ValueError('Acquisition not complete')
    for r in acquired['records']:
        if sha256(acq/r['file'])!=r['sha256']:raise ValueError('New crop identity changed')
    summaries={};stress=[];unit_counts=[];inputs=[]
    for case in p['cases']:
        cfg=cfgs[case];folder=out/case;folder.mkdir()
        for name in ['units.geojson','predictions.json','spectral-features.json']:
            if sha256(prior/case/name)!=manifest[case+'/'+name]:raise ValueError('Prior accepted input changed')
        units=json.loads((prior/case/'units.geojson').read_text())['features']
        preds={f['id']:f for f in json.loads((prior/case/'predictions.json').read_text())}
        feats={f['id']:f for f in json.loads((prior/case/'spectral-features.json').read_text())}
        files=demfiles(source,case,inputs);g=metric_grid(cfg,90);z=warp(files,g,Resampling.bilinear)
        h=derive(z,np.isfinite(z)&roi(cfg['bbox'],g.shape,g.transform,g.crs),g,100000,'fill')
        field=MeritField(acq/case/'flowdir45.tif')
        a30=[];a90=[];am=[];allcells=[];rows=[];point_records=[]
        for u in units:
            uid=u['properties']['id'];line=shape(u['geometry']);xy,_,t,_=points_on_line(line,10)
            old=preds[uid]
            if not np.allclose(xy,old['sample_xy'],atol=1e-7,rtol=0):raise ValueError('Fixed sample geometry changed')
            v30=normalized(old['d8_vectors']);v90=hydro_vectors(h,xy);vm,cells=field.sample(xy,g.crs)
            a30.extend(v30);a90.extend(v90);am.extend(vm);allcells.extend(cells)
            o30,o90,om=[orientation(v,t) for v in [v30,v90,vm]]
            row={'id':uid,'samples':len(xy),'glo30_orientation':o30,'glo90_orientation':o90,'merit_orientation':om,
                 'source_disagreement':None if o30 is None or om is None else o30!=om,
                 **feature_flags(feats[uid],pilot)}
            rows.append(row)
            # Source-level records allow an independent arithmetic recount without rerunning hydrology.
            c30=cosines(v30,vm);c90=cosines(v90,vm)
            point_records.extend([{'unit':uid,'merit_cell':cell.tolist(),
                'glo30_merit_cosine':None if not np.isfinite(c0) else float(c0),
                'glo90_merit_cosine':None if not np.isfinite(c1) else float(c1)} for cell,c0,c1 in zip(cells,c30,c90)])
        a30,a90,am=map(np.asarray,[a30,a90,am]);allcells=np.asarray(allcells)
        validcells=allcells[np.all(allcells>=0,axis=1)];distinct=np.unique(validcells,axis=0)
        with rasterio.open(acq/case/'accum45.tif') as src:
            accumulation=src.read(1)
        # Both native crops have identical grids; assert, never assume.
        with rasterio.open(acq/case/'accum45.tif') as src:
            if src.transform!=field.transform or src.shape!=field.data.shape:raise ValueError('Accumulation grid mismatch')
        upg=accumulation[distinct[:,0],distinct[:,1]];upg=upg[upg>0]
        pairs=[r for r in rows if r['source_disagreement'] is not None]
        table={}
        for warning in [True,False]:
            for disagree in [True,False]:
                table[f'warning_{warning}_comparator_disagree_{disagree}']=sum(r['water_warning']==warning and r['source_disagreement']==disagree for r in pairs)
        summary={'units':len(rows),'fixed_samples':len(a30),'distinct_native_merit_cells_at_samples':len(distinct),
            'glo30_merit':paired_summary(a30,am),'glo90_merit':paired_summary(a90,am),
            'orientable_unit_pairs':len(pairs),'opposite_majority_unit_orientations':sum(r['source_disagreement'] for r in pairs),
            'clear_units':sum(r['clear'] for r in rows),'water_warnings':sum(r['water_warning'] is True for r in rows),
            'water_warning_comparator_contingency':table,
            'vegetation_unstable_units':sum(r['vegetation_unstable'] is True for r in rows),
            'width_trend_counts':{str(label) if label is not None else 'unavailable':sum(r['width_trend']==label for r in rows) for label in ['widening','narrowing','small',None]},
            'sampled_unique_cell_upstream_count':{'valid_cells':int(len(upg)),'median':None if not len(upg) else float(np.median(upg)),
                'maximum':None if not len(upg) else int(upg.max()),'unit':'upstream grid cells, not km2'},
            'physical_direction_accuracy':None,'physical_reference_units':0}
        # Position stress is fixed, uncalibrated sensitivity, not an alignment correction.
        xyall=np.concatenate([points_on_line(shape(u['geometry']),10)[0] for u in units])
        for distance in p['comparisons']['registration_stress_m']:
            shifts=[(0,0)] if distance==0 else [(distance,0),(-distance,0),(0,distance),(0,-distance)]
            for dx,dy in shifts:
                shifted,_=field.sample(xyall+[dx,dy],g.crs)
                stress.append({'case':case,'dx_m':dx,'dy_m':dy,**paired_summary(a30,shifted)})
        save_json(folder/'unit-outcomes.json',rows);save_json(folder/'point-comparisons.json',point_records)
        summaries[case]=summary
        print({'case':case,'units':len(rows),'paired_samples':summary['glo30_merit']['paired_samples'],
               'at_least90':summary['glo30_merit']['at_least_90deg']},flush=True)
    save_json(out/'summary.json',{'schema':'satquery.merit-comparison/1','source_commit':source_commit,
        'protocol_sha256':sha256(PROTOCOL),'acquisition_sha256':sha256(acq/'acquisition.json'),
        'prior_manifest_sha256':sha256(prior/'manifest.json'),'role':'MODELED_SOURCE_COMPARISON_NOT_PHYSICAL_ACCURACY','cases':summaries})
    save_json(out/'registration-stress.json',stress);save_json(out/'inputs.json',inputs)
    save_json(out/'manifest.json',{'files':{str(f.relative_to(out)):sha256(f) for f in sorted(out.rglob('*')) if f.is_file()}})


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ['source-root','prior-root','acquisition','output','source-commit']:p.add_argument('--'+name,required=True)
    a=p.parse_args();run(a.source_root,a.prior_root,a.acquisition,a.output,a.source_commit)
