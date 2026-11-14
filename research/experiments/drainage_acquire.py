"""Small public optical DEVELOPMENT windows; no held-out direction/reference access."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
import requests
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from shapely.geometry import shape, box
from research.datasets.cog import native_window
from research.terrain_exposure.io import save_json, sha256

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT/'research/experiments/drainage-consistency-20261112.json'


def acquire(url,bbox,destination,*,license_url,product,max_pixels):
    """Pilot-only exact-host adapter; does not relax the existing acquisition helper."""
    parsed=urlsplit(url)
    if (parsed.scheme!='https' or parsed.hostname!='sentinel-cogs.s3.us-west-2.amazonaws.com'
            or not parsed.path.startswith('/sentinel-s2-l2a-cogs/') or parsed.query
            or parsed.username or parsed.password):
        raise ValueError('Only the declared anonymous Sentinel COG store is eligible')
    before=requests.head(url,timeout=40);before.raise_for_status()
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',GDAL_HTTP_TIMEOUT='40',GDAL_HTTP_MAX_RETRY='1',GDAL_CACHEMAX=64):
        with rasterio.open(url) as src:
            if not src.is_tiled or src.count!=1 or src.crs is None:
                raise ValueError('One-band georeferenced tiled source required')
            if any(h*w*np.dtype(src.dtypes[0]).itemsize>8*1024**2 for h,w in src.block_shapes):
                raise ValueError('Native decode block budget exceeded')
            window=native_window(transform_bounds('EPSG:4326',src.crs,*bbox,densify_pts=21),src.transform,src.width,src.height)
            if window.width*window.height>max_pixels:
                raise ValueError('Native pixel budget exceeded')
            data=src.read(1,window=window);valid=src.read_masks(1,window=window)>0
            transform=src.window_transform(window)
            profile={'driver':'GTiff','height':data.shape[0],'width':data.shape[1],'count':1,
                     'dtype':data.dtype,'crs':src.crs,'transform':transform,'nodata':src.nodata,'compress':'deflate'}
            grid={'crs':src.crs.to_string(),'transform':list(transform)[:6],'native_resolution':list(src.res),
                  'native_shape':list(src.shape),'window_col_row_width_height':list(window.flatten())}
    after=requests.head(url,timeout=40);after.raise_for_status()
    if before.headers.get('ETag')!=after.headers.get('ETag'):
        raise ValueError('Remote source changed during window acquisition')
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(destination,'w',**profile) as dst:
            dst.write(data,1);dst.write_mask(valid.astype('uint8')*255)
    receipt={'source_url':url,'source_etag':before.headers.get('ETag'),'product':product,'license_url':license_url,
             'retrieved_utc':datetime.now(timezone.utc).isoformat(),'bbox_wgs84':bbox,'native_window':grid,
             'pixels':int(data.size),'valid_pixels':int(valid.sum()),'sha256':sha256(destination),
             'bytes':Path(destination).stat().st_size,'uncompressed_bytes':int(data.nbytes),
             'resampling':'none; native crop','source_full_file_sha256':'NOT_ASSERTED','credentials':False}
    save_json(Path(destination).with_suffix('.source.json'),receipt)
    return receipt


def run(output):
    out = Path(output)
    if out.exists():
        raise FileExistsError('Retain acquisition attempts; choose a fresh directory')
    out.mkdir(parents=True)
    protocol = json.loads(PROTOCOL.read_text())
    cases = json.loads((ROOT/'research/experiments/case-campaign-20261107.json').read_text())['cases']
    save_json(out/'protocol.json', protocol)
    records = []
    total = 0
    for case in ['varanasi', 'sangam-vihar']:
        for period_no, period in enumerate(protocol['urban_optical']['periods']):
            folder = out/case/str(period_no)
            folder.mkdir(parents=True)
            try:
                query = {'collections':['sentinel-2-l2a'], 'bbox':cases[case]['bbox'],
                         'datetime':period, 'limit':100,
                         'sortby':[{'field':'properties.eo:cloud_cover','direction':'asc'}]}
                save_json(folder/'query.json', query)
                response = requests.post('https://earth-search.aws.element84.com/v1/search', json=query, timeout=(10,40))
                response.raise_for_status()
                if len(response.content)>4*1024*1024:
                    raise ValueError('Metadata response budget exceeded')
                metadata = response.json()
                save_json(folder/'search.json', metadata)
                eligible = [item for item in metadata['features'] if shape(item['geometry']).covers(box(*cases[case]['bbox']))]
                eligible.sort(key=lambda item:(item['properties'].get('eo:cloud_cover',101),item['properties']['datetime'],item['id']))
                if not eligible:
                    raise ValueError('No full-footprint scene in bounded metadata response')
                item = eligible[0]
                save_json(folder/'item.json', item)
                assets = []
                for band in protocol['urban_optical']['bands']:
                    asset = item['assets'][band]
                    calibration = asset.get('raster:bands', [{}])[0]
                    if band!='scl' and not {'scale','offset'} <= calibration.keys():
                        raise ValueError('No explicit reflectance scale/offset; do not assume DN calibration')
                    receipt = acquire(asset['href'], cases[case]['bbox'], folder/(band+'.tif'),
                        product='Sentinel-2 L2A '+item['id']+' '+band,
                        license_url='https://sentinel.esa.int/documents/247904/690755/Sentinel_Data_Legal_Notice',
                        max_pixels=protocol['urban_optical']['maximum_native_pixels_per_band'])
                    total += receipt['bytes']
                    if total>protocol['urban_optical']['maximum_total_native_download_mib']*1024**2:
                        raise ValueError('Total native optical budget exceeded')
                    assets.append({'band':band,'file':str((folder/(band+'.tif')).relative_to(out)),
                                   'sha256':receipt['sha256'],'scale':calibration.get('scale',1),
                                   'offset':calibration.get('offset',0),'native_receipt':receipt})
                record = {'case':case,'period':period_no,'state':'ACQUIRED','date':item['properties']['datetime'],
                          'item_id':item['id'],'search_truncated':any(link.get('rel')=='next' for link in metadata.get('links',[])),
                          'assets':assets,'selection':'metadata only, no reference/pixel score selection'}
            except Exception as error:
                record = {'case':case,'period':period_no,'state':'FAILED','error_type':type(error).__name__,
                          'reason':str(error)[:350]}
            records.append(record)
            save_json(folder/'result.json',record)
            print(json.dumps({k:v for k,v in record.items() if k!='assets'}),flush=True)
    result = {'protocol_sha256':sha256(PROTOCOL),'role':'PUBLIC_DEVELOPMENT_OPTICAL_NOT_TRUTH',
              'bytes':total,'records':records,'reference_acquired':False}
    save_json(out/'acquisition.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
