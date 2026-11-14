"""Coordinate-only phase. Never parse or expose the observed velocity columns."""
import argparse,csv,io,json,math,re,zipfile
from pathlib import Path
import numpy as np
from pyproj import Transformer
from research.terrain_exposure.io import save_json,sha256

ROOT=Path(__file__).resolve().parents[2]
PROTOCOL=ROOT/'research/experiments/observed-flow-20261112.json'


def geometry(archive,output):
    out=Path(output).resolve()
    if out.exists():raise FileExistsError('Retain geometry phase; choose fresh output')
    out.mkdir(parents=True)
    p=json.loads(PROTOCOL.read_text())
    if sha256(archive)!=p['reference']['archive_sha256']:raise ValueError('Archive identity changed')
    records=[];allxy=[];members=[]
    with zipfile.ZipFile(archive) as z:
        names=sorted(n for n in z.namelist() if re.fullmatch(r'data/adcp_20(15|16|17)_xs\d+\.csv',n))
        if len(names)!=50:raise ValueError('Expected exactly50 prespecified cross-sections')
        for name in names:
            raw=z.read(name);coordinates=[];headers=[]
            for line_no,row in enumerate(csv.reader(io.StringIO(raw.decode('utf-8-sig')))):
                if not row or not any(row):continue
                try:x,y=float(row[0]),float(row[1])
                except (ValueError,IndexError):
                    if line_no>0:raise ValueError('Unexpected nonnumeric coordinate row')
                    headers=row;continue
                if len(row)!=5 or not(np.isfinite(x) and np.isfinite(y)):
                    raise ValueError('Expected five columns and finite coordinates')
                coordinates.append([x,y])
            xy=np.asarray(coordinates,float)
            allxy.extend(coordinates)
            record={'name':name,'rows':len(xy),'source_member_sha256':__import__('hashlib').sha256(raw).hexdigest(),
                'year':int(re.search(r'20\d\d',name)[0]),'coordinate_min':xy.min(axis=0).tolist(),
                'coordinate_max':xy.max(axis=0).tolist(),'header':headers,
                'velocity_columns_parsed':False}
            records.append(record);members.extend([[name,i,*point] for i,point in enumerate(coordinates)])
    xy=np.asarray(allxy);lon,lat=Transformer.from_crs('EPSG:32613','EPSG:4326',always_xy=True).transform(xy[:,0],xy[:,1])
    bounds=[float(min(lon)),float(min(lat)),float(max(lon)),float(max(lat))]
    expected=p['reference']['published_broad_bbox_wgs84']
    if not(expected[0]<=bounds[0]<=bounds[2]<=expected[2] and expected[1]<=bounds[1]<=bounds[3]<=expected[3]):
        raise ValueError('Inferred CRS does not fit source coverage; stop before scoring')
    lo=xy.min(axis=0)-300;hi=xy.max(axis=0)+300
    metric_bounds=[float(lo[0]),float(lo[1]),float(hi[0]),float(hi[1])]
    pixels=math.ceil((hi[0]-lo[0])/30)*math.ceil((hi[1]-lo[1])/30)
    if pixels>1000000:raise ValueError('Declared30m domain exceeds analysis budget')
    corners=np.array([[lo[0],lo[1]],[lo[0],hi[1]],[hi[0],lo[1]],[hi[0],hi[1]]])
    lons,lats=Transformer.from_crs('EPSG:32613','EPSG:4326',always_xy=True).transform(corners[:,0],corners[:,1])
    bbox=[float(min(lons)),float(min(lats)),float(max(lons)),float(max(lats))]
    save_json(out/'coordinates-only.json',{'columns':['member','row','easting','northing'],'records':members})
    summary={'state':'GEOMETRY_ONLY_COMPLETE','protocol_sha256':sha256(PROTOCOL),'archive_sha256':sha256(archive),
        'crs':'EPSG:32613','crs_status':'COMPANION_SUPPORTED_INFERENCE_NOT_DIRECTLY_CERTIFIED',
        'coordinate_fit':'Within broad official metadata envelope; does not prove positional accuracy',
        'point_bbox_wgs84':bounds,'acquisition_bbox_wgs84':bbox,'metric_domain_bounds':metric_bounds,
        'predicted_30m_pixels':pixels,'rows':len(xy),'members':records,'velocity_columns_parsed':False}
    save_json(out/'geometry.json',summary)
    print({k:v for k,v in summary.items() if k not in ['members']},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();geometry(a.archive,a.output)
