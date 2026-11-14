"""Prepare small, hash-linked views from the retained scientific inputs.

NDVI uses the prior calibrated adapters. Any mapping onto DSM is display-only;
it does not establish physical registration or create a new fusion method.
SI-assisted implementation: OpenAI Codex.
"""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.terrain_exposure.io import Grid
from research.experiments.drainage_pilot import optical
from research.cases.process_campaign import warp,roi,landsat_clear,index

NAMES={'nepal':'Syapru Besi, Nepal','kedarnath':'Kedarnath, Upper Mandakini','varanasi':'Varanasi, Ganges floodplain','sangam-vihar':'Sangam Vihar, Delhi'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def safe(array):return [[None if not np.isfinite(value) else round(float(value),6) for value in row] for row in array]
def stats(array):
 values=array[np.isfinite(array)]
 return {'n':int(values.size),'median':float(np.median(values)) if values.size else None,'p10':float(np.quantile(values,.1)) if values.size else None,'p90':float(np.quantile(values,.9)) if values.size else None}

def prepare():
 protocol=json.loads((ROOT/'research/experiments/case-campaign-20261107.json').read_text())
 destination=ROOT/'data/views';destination.mkdir(parents=True,exist_ok=True)
 outputs={}
 for case,cfg in protocol['cases'].items():
  folder=ROOT/'data/case-grids'/case
  frozen_summary=json.loads((folder/'summary.json').read_text())
  product=frozen_summary['terrain']['30']['source_product']
  product_label={'CopernicusGLO30':'Copernicus GLO-30 DSM','NASADEM_HGT_v001':'NASADEM elevation model'}.get(product,product)
  with rasterio.open(folder/'dem-30m.tif') as source:
   grid=Grid(source.shape,source.transform,source.crs.to_string());dem=source.read(1).astype(float)
   dem[(source.read_masks(1)==0)|~np.isfinite(dem)]=np.nan
  step=max(1,int(np.ceil(max(grid.shape)/150)))
  xs=[float((grid.transform*(column+.5,.5))[0]) for column in range(0,grid.shape[1],step)]
  ys=[float((grid.transform*(.5,row+.5))[1]) for row in range(0,grid.shape[0],step)]
  fields={};sources=[]
  for key,label,filename,unit in [('elevation','Elevation · DSM','dem-30m.tif','m'),('slope','Slope','slope-30m.tif','degrees'),('hand','Height above drainage · modeled','hand-30m.tif','m')]:
   path=folder/filename
   with rasterio.open(path) as source:
    values=source.read(1).astype(float);values[source.read_masks(1)==0]=np.nan
   fields[key]={'label':label,'unit':unit,'values':safe(values[::step,::step]),'native_stats':stats(values),'native_resolution_m':30,'display_mapping':'original frozen grid; display decimation only'}
   sources.append({'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'role':'frozen measured derivative; not independent validation'})
  records=[]
  if case=='kedarnath':
   source_folder=ROOT/'.runtime/case-campaign-20261107/sources/kedarnath'
   clear={};bands={};inside=roi(cfg['bbox'],grid.shape,grid.transform,grid.crs)
   for epoch in ('before','after'):
    current={band:warp([source_folder/f'landsat-{epoch}-{band}.tif'],grid) for band in protocol['landsat']['bands']}
    valid=inside.copy()
    for array in current.values():valid&=np.isfinite(array)
    clear[epoch]=landsat_clear(np.nan_to_num(current['qa_pixel']),np.nan_to_num(current['qa_radsat']),valid)
    bands[epoch]={band:current[band]*protocol['landsat']['reflectance_scale']+protocol['landsat']['reflectance_offset'] for band in ('red','nir08')}
    for band in protocol['landsat']['bands']:
     path=source_folder/f'landsat-{epoch}-{band}.tif';sources.append({'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path),'role':'Landsat source'})
   common=clear['before']&clear['after']
   observations=[]
   for epoch in ('before','after'):
    observations.append({'date':cfg[epoch] if epoch in cfg else epoch,'grid':grid,'indices':{'NDVI':index(bands[epoch]['nir08'],bands[epoch]['red'],common)},'valid':common,'source':'Landsat Collection 2 Level 2; QA masked, scale 0.0000275 and offset −0.2'})
  else:
   observations=optical(case,ROOT,ROOT/'research/datasets/local/drainage-20261112/optical-attempt-2',records)
   observations.sort(key=lambda item:item['date'])
   for record in records:
    # The existing adapter has already checked source identities. Retain a
    # project-relative reference without publishing original machine paths.
    sources.append({key:value for key,value in record.items() if key not in ('path','resolved_path')})
  optical_summary=[];mapped=[]
  for number,observation in enumerate(observations[:2]):
   values=observation['indices']['NDVI'].copy();values[~observation['valid']]=np.nan
   display=np.full(grid.shape,np.nan,dtype='float64')
   reproject(values,display,src_transform=observation['grid'].transform,src_crs=observation['grid'].crs,src_nodata=np.nan,dst_transform=grid.transform,dst_crs=grid.crs,dst_nodata=np.nan,resampling=Resampling.nearest)
   display[~np.isfinite(dem)]=np.nan;mapped.append(display)
   key='ndvi_before' if number==0 else 'ndvi_after'
   fields[key]={'label':'NDVI · '+('before' if number==0 else 'after'),'unit':'index','values':safe(display[::step,::step]),'native_stats':stats(values),'native_resolution_m':abs(observation['grid'].transform.a),'date':observation['date'],'display_mapping':'nearest-neighbor mapping to DSM for visualization; physical registration not validated'}
   optical_summary.append({'date':observation['date'],'source':str(observation['source']).replace(str(ROOT),'.'),'native_grid':observation['grid'].describe(),'clear_pixels':int(observation['valid'].sum()),'total_grid_pixels':int(observation['valid'].size),'clear_fraction':float(observation['valid'].mean()),'calibration':observation.get('calibration')})
  if len(mapped)==2:
   change=mapped[1]-mapped[0]
   fields['ndvi_change']={'label':'NDVI change · after − before','unit':'index','values':safe(change[::step,::step]),'display_grid_stats':stats(change),'native_resolution_m':max(abs(item['grid'].transform.a) for item in observations[:2]),'mapped_grid_m':30,'display_mapping':'difference on display-mapped common finite support; not a significance test','caution':'Two-date index change, not a long-term trend or confirmed vegetation loss.'}
  if product.startswith('NASADEM'):fields['elevation']['label']='Elevation · NASADEM'
  value={'case_id':case,'name':NAMES[case],'event':cfg.get('event'),'study_period':[cfg.get('before'),cfg.get('after')],'bbox':cfg['bbox'],'crs':grid.crs,'grid':grid.describe(),'x':xs,'y':ys,'elevation':safe(dem[::step,::step]),'fields':fields,'observations':optical_summary,'sources':sources,'display_step':step,'terrain_product':product,'terrain_product_label':product_label,'original_case_summary_sha256':sha(folder/'summary.json'),'surface_kind':'historical '+product_label+', not surveyed bare-earth DTM or event-time terrain','limitations':['Physical sensor registration remains unvalidated.','NDVI is an index, not a direct measurement of vegetation health or damage.','NDVI mapped onto terrain is for display only; it does not validate a fused hazard classifier.','HAND and drainage are static topographic models, not flood depth, hydraulics or safe-route evidence.']}
  path=destination/(case+'.json');path.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8');outputs[path.name]=sha(path)
  print(case,'display',len(ys),'×',len(xs),'fields',len(fields),'optical',[(item['date'],round(item['clear_fraction'],4)) for item in optical_summary],flush=True)
 (destination/'manifest.json').write_text(json.dumps({'schema':1,'files':outputs,'role':'frozen genuine-data display views; no new independent accuracy claim'},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':prepare()
