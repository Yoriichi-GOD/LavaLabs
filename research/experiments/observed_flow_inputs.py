"""Predictor-only acquisition from the geometry phase; no velocity labels."""
import argparse,json,math
from pathlib import Path
import rasterio
import requests
from research.datasets.cog import acquire
from research.datasets.cog import native_window
from rasterio.warp import transform_bounds
from research.experiments.merit_windows import RangeFile,metadata,crop,PREFIX
from research.terrain_exposure.io import save_json,sha256


def checked_tile(url,bbox,out):
    """Fallback for a truncated GDAL range: bounded complete24MB source tile."""
    head=requests.head(url,timeout=40);head.raise_for_status()
    size=int(head.headers['Content-Length']);etag=head.headers['ETag']
    if size>32*1024**2:raise ValueError('Fallback tile exceeds32MiB')
    path=out/'whole-source-tile.tif';received=0
    with path.open('xb') as f:
        for start in range(0,size,1024*1024):
            end=min(size,start+1024*1024)-1
            for attempt in range(3):
                try:
                    with requests.get(url,headers={'Range':f'bytes={start}-{end}','If-Match':etag,'Accept-Encoding':'identity'},
                            stream=True,timeout=(10,40),allow_redirects=False) as r:
                        if r.status_code!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{end}/{size}' or r.headers.get('ETag')!=etag:
                            raise ValueError('Exact stable tile range required')
                        data=bytearray()
                        for chunk in r.iter_content(16384):
                            received+=len(chunk);data.extend(chunk)
                            if received>64*1024**2 or len(data)>end-start+1:raise ValueError('Fallback transfer budget exceeded')
                        if len(data)!=end-start+1:raise ValueError('Truncated tile range')
                    f.write(data);break
                except (requests.Timeout,requests.ConnectionError):
                    if attempt==2:raise
    after=requests.head(url,timeout=40);after.raise_for_status()
    if after.headers.get('ETag')!=etag or path.stat().st_size!=size:raise ValueError('Tile identity/length changed')
    destination=out/'copernicus-native-crop.tif'
    with rasterio.open(path) as src:
        w=native_window(transform_bounds('EPSG:4326',src.crs,*bbox,densify_pts=21),src.transform,src.width,src.height)
        if w.width*w.height>1000000:raise ValueError('Crop pixel budget exceeded')
        data=src.read(1,window=w);mask=src.read_masks(1,window=w);profile=src.profile
        profile.update(height=data.shape[0],width=data.shape[1],transform=src.window_transform(w),tiled=False,compress='deflate')
        profile.pop('blockxsize',None);profile.pop('blockysize',None)
        with rasterio.open(destination,'w',**profile) as dst:dst.write(data,1);dst.write_mask(mask)
    return {'source_url':url,'source_etag':etag,'source_full_size_bytes':size,'source_full_sha256':sha256(path),
        'sha256':sha256(destination),'file':destination.name,'bytes':destination.stat().st_size,
        'native_window':list(w.flatten()),'http_response_body_bytes':received,'maximum_network_bytes':64*1024**2,
        'fallback_reason':'GDAL remote tile read truncated; exact checked HTTP ranges then local native crop',
        'product':'Copernicus GLO30 historical DSM','resampling':'none','bbox_wgs84':bbox,'credentials':False}


def run(geometry,output):
    g=json.loads(Path(geometry).read_text());bbox=g['acquisition_bbox_wgs84']
    out=Path(output).resolve()
    if out.exists():raise FileExistsError('Retain attempts; use fresh output')
    out.mkdir(parents=True)
    records=[]
    for lat in range(math.floor(bbox[1]),math.ceil(bbox[3])):
        for lon in range(math.floor(bbox[0]),math.ceil(bbox[2])):
            tile=f'Copernicus_DSM_COG_10_{"N" if lat>=0 else "S"}{abs(lat):02d}_00_{"E" if lon>=0 else "W"}{abs(lon):03d}_00_DEM'
            url=f'https://copernicus-dem-30m.s3.amazonaws.com/{tile}/{tile}.tif'
            records.append(checked_tile(url,bbox,out))
    save_json(out/'dem-acquisition.json',{'records':records,'geometry_sha256':sha256(geometry)})
    print({'phase':'DEM_ACQUIRED','crop_bytes':sum(r['bytes'] for r in records)},flush=True)
    budget={'bytes':0,'maximum_bytes':64*1024**2}
    remote=RangeFile(PREFIX+'flowdir71.tif',budget);info=metadata(remote)
    data,t,window=crop(remote,info,bbox)
    path=out/'flowdir71.tif'
    with rasterio.open(path,'w',driver='GTiff',height=data.shape[0],width=data.shape[1],count=1,dtype=data.dtype,
                       crs='EPSG:4326',transform=t,compress='deflate') as dst:dst.write(data,1)
    remote.verify_identity()
    save_json(out/'merit-acquisition.json',{'url':remote.url,'etag':remote.etag,'full_size_bytes':remote.length,
        'full_file_sha256':'NOT_VERIFIED_FROM_WINDOW','source_version':'MERIT-derived distributor mosaic, original version not verified',
        'license':'https://creativecommons.org/licenses/by-nc-sa/4.0/', 'window':window,'shape':list(data.shape),
        'http_response_body_bytes':budget['bytes'],'maximum_network_bytes':budget['maximum_bytes'],'ranges':remote.ranges,
        'sha256':sha256(path),'bytes':path.stat().st_size,'credentials':False,'resampling':'none'})
    save_json(out/'input-seal.json',{'geometry_sha256':sha256(geometry),'velocity_labels_read':False,
        'files':[{'name':p.name,'sha256':sha256(p)} for p in sorted(out.glob('*.tif')) if p.name!='whole-source-tile.tif']})
    print({'phase':'PREDICTORS_ACQUIRED_SEALED','merit_network_bytes':budget['bytes'],'velocity_labels_read':False},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--geometry',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();run(a.geometry,a.output)
