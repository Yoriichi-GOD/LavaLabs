"""Independent stored-output recount/packaging. Does not import prediction rules."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics


def load(path):return json.loads(Path(path).read_text())
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def table(path,rows):
    with Path(path).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def check_ablation_rows(expected,recorded):
    # JSON serialization sorts arm names; CSV retains declaration order. Match
    # experimental identities, not presentation order, and still reject duplicates.
    lookup={(r['case'],r['arm']):r for r in recorded}
    assert len(lookup)==len(recorded)==len(expected)
    assert set(lookup)=={(r['case'],r['arm']) for r in expected}
    for row in expected:
        actual=lookup[(row['case'],row['arm'])]
        assert all(str(value)==actual[key] for key,value in row.items()),(row,actual)


def run(source,output,source_commit,baseline_root):
    src=Path(source);out=Path(output)
    if out.exists():raise FileExistsError('Keep verification receipts immutable')
    out.mkdir(parents=True)
    manifest=load(src/'manifest.json')
    for name,expected in manifest['files'].items():
        if digest(src/name)!=expected:raise ValueError('Output hash mismatch: '+name)
    inputs=load(src/'inputs.json')
    for item in inputs:
        if digest(item['path'])!=item['sha256']:raise ValueError('Input hash mismatch: '+item['path'])
    summary=load(src/'summary.json');report={};counts=[];thresholds=[];examples=[]
    for case in ['nepal','varanasi','sangam-vihar']:
        pred=load(src/case/'predictions.json');features=load(src/case/'spectral-features.json')
        seal=load(src/case/'prediction-seal.json')
        for filename,key in [('predictions.json','predictions_sha256'),('spectral-features.json','features_sha256'),('units.geojson','units_sha256')]:
            assert digest(src/case/filename)==seal[key]
        assert len(pred)==len(features)==summary[case]['units']
        assert [p['id'] for p in pred]==[f['id'] for f in features]
        n=len(pred);clear=[];raw_water_flags=[];primary=[];widths=[];ndsensitive=[]
        temporal=sum(f['temporal']['status']!='INSUFFICIENT_OBSERVATION' for f in features)
        for p,f in zip(pred,features):
            if not f['dates']:continue
            d=f['dates'][0];primary.append(d)
            for date in f['dates']:
                if date['ndvi_median'] is not None:assert -1-1e-10<=date['ndvi_median']<=1+1e-10
            good=d['clear_fraction']>=.8
            if good:clear.append(p['id'])
            coverage=[d['water']['MNDWI:'+str(t)]['near_fraction'] for t in [-.1,0.,.1]]
            robust=good and max(coverage)<.2
            if robust:raw_water_flags.append(p['id'])
            if good:
                vs=[v['below_fraction'] for v in d['vegetation'].values()]
                ndsensitive.append(max(vs)-min(vs)>.4)
                if d['morphology']['eligible_width_samples']>=5:widths.append(d['morphology'])
            if robust and len([e for e in examples if e['case']==case])<3:
                examples.append({'case':case,'id':p['id'],'role':'Observed spectral-corridor disagreement; not verified DEM error',
                    'clear_fraction':d['clear_fraction'],'mndwi_threshold_near_fraction':coverage,
                    'category_C':p['arms']['C']['category'],'category_F':p['arms']['F']['category']})
        for arm in pred[0]['arms']:
            c=Counter(p['arms'][arm]['category'] for p in pred)
            row={'case':case,'arm':arm,'n':n,'direction_assertions':sum(p['arms'][arm]['direction_asserted'] for p in pred)}
            for k in ['SUPPORTED_DIRECTION','CONFLICTING_EVIDENCE','AMBIGUOUS_DIRECTION','INSUFFICIENT_SPATIAL_RESOLUTION','INSUFFICIENT_OBSERVATION','REFERENCE_UNAVAILABLE']:row[k]=c[k]
            assert sum(row[k] for k in c)==n
            counts.append(row)
        for family in ['NDWI','MNDWI']:
            for threshold in [-.1,0.,.1]:
                values=[d['water'][family+':'+str(threshold)]['near_fraction'] for d in primary if d['clear_fraction']>=.8]
                long=[d['water'][family+':'+str(threshold)]['largest_component_fraction'] for d in primary if d['clear_fraction']>=.8]
                thresholds.append({'case':case,'family':family,'threshold':threshold,'eligible_units':len(values),
                    'mean_unit_near_fraction':statistics.mean(values) if values else None,
                    'median_unit_near_fraction':statistics.median(values) if values else None,
                    'mean_largest_component_fraction':statistics.mean(long) if long else None})
        annotation=load(src/case/'administrative-direction-diagnostic.json')
        labelled=[r for r in annotation if r.get('majority_agreement') is not None]
        lookup={r['id']:r for r in labelled}
        flagged_labelled=[lookup[i] for i in raw_water_flags if i in lookup]
        report[case]={'units':n,'clear_eligible_units':len(clear),'temporal_common_eligible_units':temporal,
            'raw_robust_water_disagreements':len(raw_water_flags),'ndvi_threshold_sensitive_clear_units':sum(ndsensitive),
            'resolved_uncensored_width_units':len(widths),
            'width_widening_ge20m':sum(w['total_width_trend_m'] is not None and w['total_width_trend_m']>=20 for w in widths),
            'width_narrowing_le_minus20m':sum(w['total_width_trend_m'] is not None and w['total_width_trend_m']<=-20 for w in widths),
            'administrative_orientable':len(labelled),'administrative_majority_agreements':sum(r['majority_agreement'] for r in labelled),
            'raw_water_flag_admin_agree':sum(r['majority_agreement'] for r in flagged_labelled),
            'raw_water_flag_admin_disagree':sum(not r['majority_agreement'] for r in flagged_labelled),
            'physical_direction_accuracy':None,'verified_error_detection_precision':None,'verified_false_flags':None}
        assert summary[case]['physical_direction_evaluation']['eligible']==0
        assert summary[case]['physical_direction_evaluation']['accuracy'] is None
    recorded=list(csv.DictReader((src/'ablation.csv').open()))
    check_ablation_rows(counts,recorded)
    assert len(counts)==len(recorded)==30
    terrain=list(csv.DictReader((src/'terrain-sensitivity.csv').open()))
    for row in terrain:
        compared=int(row['compared_direction_samples']);changed=int(row['changed_direction_samples'])
        assert changed<=compared<=int(row['total_direction_samples'])
        assert math.isclose(changed/compared,float(row['changed_fraction']),abs_tol=1e-12)
        assert math.isclose(int(row['fixed_unit_samples_within30m_stream'])/int(row['fixed_unit_samples']),float(row['location_association_fraction']),abs_tol=1e-12)
    for name in ['ablation.csv','terrain-sensitivity.csv','summary.json','protocol.json','scale-clarification.json','calibration-clarification.json']:
        shutil.copy2(src/name,out/name)
    table(out/'spectral-threshold-summary.csv',thresholds)
    table(out/'case-measurements.csv',[{'case':case,**row} for case,row in report.items()])
    save(out/'disagreement-examples.json',examples)
    save(out/'independent-recount.json',{'status':'PASS','output_manifest_files_verified':len(manifest['files']),
        'input_records_hash_verified':len(inputs),'ablation_rows_recounted':len(counts),'terrain_rows_checked':len(terrain),
        'population':'Stored pilot records and retained inputs; not field/independent scientific validation',
        'cases':report,'reserved_data_opened':False})
    root=Path(__file__).resolve().parents[1]
    code=[root/'research/experiments'/name for name in ['drainage_core.py','drainage_acquire.py','drainage_pilot.py',
          'drainage-consistency-20261112.json','drainage-scale-20261112.json','drainage-calibration-20261112.json']]
    original=Path(baseline_root).resolve()
    inherited=[root/'research/terrain_exposure'/name for name in ['hydrology.py','io.py','graph.py']]
    unchanged={str(f.relative_to(root)):digest(f)==digest(original/f.relative_to(root)) for f in inherited}
    assert all(unchanged.values())
    # Caller supplies native Git identity: Linux Git cannot resolve this Windows worktree pointer.
    if len(source_commit)!=40 or any(c not in '0123456789abcdef' for c in source_commit):
        raise ValueError('Supply full native Git commit identity')
    save(out/'reproduction-identities.json',{'code_commit':source_commit,
        'code_sha256':{str(f.relative_to(root)):digest(f) for f in code},'unchanged_inherited_methods':unchanged,
        'source_run':str(src.resolve()),'source_run_manifest_sha256':digest(src/'manifest.json'),
        'source_input_records_sha256':digest(src/'inputs.json')})
    print(json.dumps({'status':'PASS','cases':report,'artifact_files':len(manifest['files'])},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--output',required=True);p.add_argument('--source-commit',required=True);p.add_argument('--baseline-root',required=True)
    a=p.parse_args();run(a.run,a.output,a.source_commit,a.baseline_root)
