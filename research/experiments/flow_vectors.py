"""Directional comparisons: explicit support, categorical sampling, metric vectors."""
import numpy as np
from pyproj import Transformer
import rasterio

OFFSETS={1:(1,0),2:(1,1),4:(0,1),8:(-1,1),16:(-1,0),32:(-1,-1),64:(0,-1),128:(1,-1)}
NONVECTORS={0,247,255}


def normalized(vectors):
    if not isinstance(vectors,np.ndarray):
        vectors=[(np.nan,np.nan) if v is None else v for v in vectors]
    a=np.asarray(vectors,dtype=float).reshape(-1,2)
    norms=np.linalg.norm(a,axis=1)
    ok=np.isfinite(a).all(axis=1)&(norms>0)
    out=np.full(a.shape,np.nan);out[ok]=a[ok]/norms[ok,None]
    return out


def cosines(a,b):
    return np.clip(np.sum(normalized(a)*normalized(b),axis=1),-1,1)


def angles(a,b): return np.degrees(np.arccos(cosines(a,b)))


def orientation(vectors,tangents):
    c=cosines(vectors,tangents);valid=np.isfinite(c)
    if not valid.any():return None
    positive=int((c[valid]>1e-12).sum());negative=int((c[valid]<-1e-12).sum())
    # Perpendicular projections are no vote; exact directional ties stay unknown.
    return 1 if positive>len(c[valid])/2 else -1 if negative>len(c[valid])/2 else None


def hydro_vectors(hydro,xy):
    xy=np.asarray(xy,float);g=hydro.grid
    rr=np.floor((xy[:,1]-g.transform.f)/g.transform.e).astype(int)
    cc=np.floor((xy[:,0]-g.transform.c)/g.transform.a).astype(int)
    out=np.full((len(xy),2),np.nan)
    for k,(r,c) in enumerate(zip(rr,cc)):
        if not(0<=r<g.shape[0] and 0<=c<g.shape[1]) or not hydro.valid[r,c]:continue
        i=int(r*g.shape[1]+c);j=int(hydro.downstream.ravel()[i])
        if j>=0:out[k]=np.subtract(g.centre(j),g.centre(i))
    return normalized(out)


class MeritField:
    def __init__(self,path):
        with rasterio.open(path) as src:
            if src.crs.to_epsg()!=4326 or src.count!=1 or src.transform.b or src.transform.d:
                raise ValueError('Native north-up EPSG4326 categorical field required')
            self.data,self.transform=src.read(1),src.transform
        if not set(np.unique(self.data).tolist())<=set(OFFSETS)|NONVECTORS:
            raise ValueError('Unexpected categorical flow direction code')

    def sample(self,xy,crs):
        xy=np.asarray(xy,float)
        inverse=Transformer.from_crs(crs,'EPSG:4326',always_xy=True)
        forward=Transformer.from_crs('EPSG:4326',crs,always_xy=True)
        lon,lat=inverse.transform(xy[:,0],xy[:,1]);t=self.transform
        rr=np.floor((lat-t.f)/t.e).astype(int);cc=np.floor((lon-t.c)/t.a).astype(int)
        out=np.full((len(xy),2),np.nan);cells=np.full((len(xy),2),-1,dtype=int)
        for k,(r,c) in enumerate(zip(rr,cc)):
            if not(0<=r<self.data.shape[0] and 0<=c<self.data.shape[1]):continue
            cells[k]=[int(r),int(c)];code=int(self.data[r,c])
            if code not in OFFSETS:continue
            dc,dr=OFFSETS[code]
            a=t @ (c+.5,r+.5);b=t @ (c+.5+dc,r+.5+dr)
            x0,y0=forward.transform(*a);x1,y1=forward.transform(*b)
            out[k]=[x1-x0,y1-y0]
        return normalized(out),cells


def paired_summary(a,b):
    c=cosines(a,b);valid=np.isfinite(c);angle=np.degrees(np.arccos(c[valid]))
    return {'samples':len(c),'paired_samples':int(valid.sum()),
        'source_a_available':int(np.isfinite(normalized(a)).all(axis=1).sum()),
        'source_b_available':int(np.isfinite(normalized(b)).all(axis=1).sum()),
        'at_least_90deg':int((c[valid]<=1e-12).sum()),
        'over_45deg':int((angle>45+1e-9).sum()),'over_1deg':int((angle>1+1e-9).sum()),
        'median_angle_deg':None if not len(angle) else float(np.median(angle)),
        'p90_angle_deg':None if not len(angle) else float(np.percentile(angle,90))}
