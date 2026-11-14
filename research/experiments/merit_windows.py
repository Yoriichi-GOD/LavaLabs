"""Budgeted anonymous range crops of the declared MERIT-derived distributor TIFFs.

This adapter deliberately supports only simple one-row DEFLATE strips. It never
silently falls back to downloading a full basin, authenticating, or resampling.
"""
import argparse
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
from urllib.parse import urlsplit
import zlib

import numpy as np
import requests
import rasterio
from affine import Affine
import tifffile
from research.terrain_exposure.io import save_json, sha256

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT/'research/experiments/drainage-validation-20261112.json'
PREFIX = 'https://mghydro.com/watersheds/data/'


class RangeFile(io.RawIOBase):
    """Seekable, cached HTTP ranges with exact identity and transfer accounting."""
    def __init__(self, url, budget, session=None, block_size=262144):
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or parsed.netloc != 'mghydro.com' or
                parsed.path not in ['/watersheds/data/flowdir45.tif', '/watersheds/data/accum45.tif',
                                    '/watersheds/data/flowdir71.tif'] or
                parsed.query or parsed.fragment):
            raise ValueError('Only the declared anonymous distributor files are allowed')
        self.url, self.budget = url, budget
        self.session = session or requests.Session()
        self.block_size, self.position, self.cache, self.ranges = block_size, 0, {}, []
        head = self.session.head(url, timeout=40, allow_redirects=False)
        if head.status_code != 200:
            raise ValueError('Source HEAD unavailable')
        self.length = int(head.headers['Content-Length'])
        self.etag = head.headers.get('ETag')
        self.modified = head.headers.get('Last-Modified')
        if not self.etag or self.length <= 0:
            raise ValueError('Source identity/length required')

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        position = offset + (0 if whence == 0 else self.position if whence == 1 else self.length if whence == 2 else -10**20)
        if position < 0 or position > self.length:
            raise ValueError('Seek outside source')
        self.position = position
        return position

    def read(self, size=-1):
        if size is None or size < 0:
            raise ValueError('Unbounded reads are forbidden')
        end = min(self.length, self.position + size)
        result = bytearray()
        while self.position < end:
            block = self.position // self.block_size
            start = block * self.block_size
            stop = min(self.length, start + self.block_size) - 1
            if block not in self.cache:
                wanted = stop-start+1
                if self.budget['bytes'] + wanted > self.budget['maximum_bytes']:
                    raise ValueError('Global HTTP byte budget would be exceeded')
                for attempt in range(3):
                    # Retries count consumed body chunks too; no budget reset.
                    if self.budget['bytes'] + wanted > self.budget['maximum_bytes']:
                        raise ValueError('Global HTTP byte budget would be exceeded')
                    try:
                        response = self.session.get(self.url, headers={
                            'Range': f'bytes={start}-{stop}', 'If-Match': self.etag,
                            'Accept-Encoding': 'identity'}, stream=True, timeout=(10,40), allow_redirects=False)
                        try:
                            if (response.status_code != 206 or
                                    response.headers.get('Content-Range') != f'bytes {start}-{stop}/{self.length}' or
                                    response.headers.get('ETag') != self.etag or
                                    response.headers.get('Content-Encoding', 'identity') not in ('identity','')):
                                raise ValueError('Exact stable HTTP 206 range required; no full-file fallback')
                            data = bytearray()
                            for chunk in response.iter_content(16384):
                                self.budget['bytes'] += len(chunk)
                                data.extend(chunk)
                                if len(data) > wanted or self.budget['bytes'] > self.budget['maximum_bytes']:
                                    raise ValueError('HTTP response exceeded declared byte budget')
                            if len(data) != wanted:raise ValueError('Truncated HTTP range')
                            self.cache[block] = bytes(data)
                            self.ranges.append([start, stop, len(data)])
                            break
                        finally:
                            response.close()
                    except (requests.Timeout,requests.ConnectionError):
                        self.budget['transport_retries'] = self.budget.get('transport_retries',0)+1
                        if attempt==2:raise
            take = min(end-self.position, stop-self.position+1)
            result.extend(self.cache[block][self.position-start:self.position-start+take])
            self.position += take
        return bytes(result)

    def verify_identity(self):
        head = self.session.head(self.url, timeout=40, allow_redirects=False)
        if head.status_code != 200 or head.headers.get('ETag') != self.etag or int(head.headers['Content-Length']) != self.length:
            raise ValueError('Remote source identity changed during acquisition')


def metadata(remote):
    with tifffile.TiffFile(remote) as tif:
        if len(tif.pages) != 1:
            raise ValueError('Exactly one image page required')
        page = tif.pages[0]
        if (page.is_tiled or page.samplesperpixel != 1 or page.rowsperstrip != 1 or
                int(page.compression) not in (8,32946) or int(page.predictor) != 1):
            raise ValueError('Only one-row, one-band, predictor-free DEFLATE strips supported')
        scale = page.tags['ModelPixelScaleTag'].value
        tie = page.tags['ModelTiepointTag'].value
        keys = page.tags['GeoKeyDirectoryTag'].value
        geokeys = {keys[i]:tuple(keys[i+1:i+4]) for i in range(4,len(keys),4)}
        if geokeys.get(2048) != (0,1,4326) or geokeys.get(1025) != (0,1,1):
            raise ValueError('EPSG:4326 pixel-is-area TIFF required')
        transform = Affine(scale[0],0,tie[3]-tie[0]*scale[0],0,-scale[1],tie[4]+tie[1]*scale[1])
        return {'shape':page.shape, 'dtype':page.dtype, 'offsets':tuple(page.dataoffsets),
                'counts':tuple(page.databytecounts), 'transform':transform,
                'nodata':page.tags['GDAL_NODATA'].value if 'GDAL_NODATA' in page.tags else None,
                'byteorder':tif.byteorder}


def crop(remote, info, bbox, halo=2, max_pixels=1000000):
    t = info['transform']; height,width = info['shape']
    west,south,east,north = bbox
    c0 = max(0,math.floor((west-t.c)/t.a)-halo)
    c1 = min(width,math.ceil((east-t.c)/t.a)+halo)
    r0 = max(0,math.floor((north-t.f)/t.e)-halo)
    r1 = min(height,math.ceil((south-t.f)/t.e)+halo)
    if c1 <= c0 or r1 <= r0 or (r1-r0)*(c1-c0) > max_pixels:
        raise ValueError('Empty/out-of-budget native crop')
    dtype = np.dtype(info['dtype']).newbyteorder(info['byteorder'])
    out = np.empty((r1-r0,c1-c0),dtype=info['dtype'])
    expected = width*dtype.itemsize
    for r in range(r0,r1):
        remote.seek(info['offsets'][r])
        packed = remote.read(info['counts'][r])
        decoder = zlib.decompressobj()
        raw = decoder.decompress(packed,expected+1)
        if len(raw) != expected or not decoder.eof or decoder.unused_data:
            raise ValueError('Invalid or oversized native strip decode')
        out[r-r0] = np.frombuffer(raw,dtype=dtype)[c0:c1]
    return out, t @ Affine.translation(c0,r0), [c0,r0,c1-c0,r1-r0]


def run(output):
    out = Path(output).resolve()
    if out.exists(): raise FileExistsError('Keep acquisition attempts; use a fresh output')
    out.mkdir(parents=True)
    protocol = json.loads(PROTOCOL.read_text())
    cases = json.loads((ROOT/'research/experiments/case-campaign-20261107.json').read_text())['cases']
    budget = {'bytes':0,'maximum_bytes':protocol['source']['acquisition_network_budget_mib']*1024**2}
    records = []
    for filename in protocol['source']['files']:
        remote = RangeFile(PREFIX+filename,budget)
        info = metadata(remote)
        for case in protocol['cases']:
            folder = out/case; folder.mkdir(exist_ok=True)
            data,t,window = crop(remote,info,cases[case]['bbox'],
                protocol['source']['native_crop_halo_cells'],protocol['source']['maximum_native_crop_pixels'])
            destination = folder/filename
            nodata = None if info['nodata'] is None else float(str(info['nodata']).strip('\x00'))
            with rasterio.open(destination,'w',driver='GTiff',height=data.shape[0],width=data.shape[1],
                               count=1,dtype=data.dtype,crs='EPSG:4326',transform=t,nodata=nodata,compress='deflate') as dst:
                dst.write(data,1)
            record = {'case':case,'file':str(destination.relative_to(out)), 'source_url':remote.url,
                'source_etag':remote.etag, 'source_last_modified':remote.modified,
                'source_full_size_bytes':remote.length,'source_full_sha256':'NOT_VERIFIED_FROM_WINDOW',
                'source_version':'MERIT-derived distributor mosaic, original version not verified',
                'license':protocol['source']['license'], 'native_crs':'EPSG:4326',
                'native_full_shape':list(info['shape']),'native_crop_window':window,
                'native_transform':list(t)[:6],'dtype':str(data.dtype),'nodata':nodata,
                'sha256':sha256(destination),'bytes':destination.stat().st_size,
                'unit':'D8 categorical code' if filename.startswith('flowdir') else 'upstream grid cell count',
                'resampling':'none','credentials':False}
            save_json(destination.with_suffix('.source.json'),record); records.append(record)
            print(json.dumps({'case':case,'file':filename,'crop_shape':list(data.shape),'network_bytes_so_far':budget['bytes']}),flush=True)
        remote.verify_identity()
        save_json(out/(filename+'.ranges.json'),{'url':remote.url,'etag':remote.etag,'ranges':remote.ranges,
                  'response_body_bytes':sum(r[2] for r in remote.ranges)})
    result = {'state':'COMPLETE','retrieved_utc':datetime.now(timezone.utc).isoformat(),
        'protocol_sha256':sha256(PROTOCOL),'http_response_body_bytes':budget['bytes'],
        'network_budget_bytes':budget['maximum_bytes'],'transport_retries':budget.get('transport_retries',0),'records':records,
        'role':'MODELED_COMPARATOR_NOT_PHYSICAL_TRUTH'}
    save_json(out/'acquisition.json',result)
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
