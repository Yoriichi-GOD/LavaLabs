"""Acquire one declared observed-flow archive, sealed until scoring is frozen."""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import zipfile
import requests
from research.terrain_exposure.io import save_json

URL='https://data-package.ceh.ac.uk/data/e4fe2ebe-b207-47d5-8c77-9873afc63da9.zip'


def run(output):
    folder=Path(output).resolve()
    if folder.exists():raise FileExistsError('Retain attempts; choose fresh output')
    folder.mkdir(parents=True)
    path=folder/'sealed-observations.zip'
    cap=64*1024**2;size=0;h=hashlib.sha256()
    with requests.get(URL,stream=True,timeout=(10,40),allow_redirects=False) as r:
        if r.status_code!=200:raise ValueError('Declared public source unavailable')
        with path.open('xb') as f:
            for chunk in r.iter_content(65536):
                size+=len(chunk)
                if size>cap:raise ValueError('64MiB archive budget exceeded')
                f.write(chunk);h.update(chunk)
        headers={k:r.headers.get(k) for k in ['Content-Length','ETag','Last-Modified','Content-Type']}
    # Read only the ZIP directory, never a measurement member.
    with zipfile.ZipFile(path) as z:
        members=[{'name':i.filename,'compressed_bytes':i.compress_size,'uncompressed_bytes':i.file_size,'crc':i.CRC} for i in z.infolist()]
        if len(members)>500 or sum(m['uncompressed_bytes'] for m in members)>256*1024**2:
            raise ValueError('Archive expansion budget exceeded')
    receipt={'state':'ACQUIRED_SEALED','url':URL,'doi':'10.5285/e4fe2ebe-b207-47d5-8c77-9873afc63da9',
             'sha256':h.hexdigest(),'bytes':size,'network_body_bytes':size,'maximum_bytes':cap,
             'retrieved_utc':datetime.now(timezone.utc).isoformat(),'headers':headers,'members':members,
             'measurement_members_read':False,'credentials':False,
             'rule':'Freeze reference-specific scoring and CRS before opening measurement rows'}
    save_json(folder/'acquisition.json',receipt)
    print({'state':receipt['state'],'bytes':size,'members':len(members),'sha256':h.hexdigest()},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);run(p.parse_args().output)
