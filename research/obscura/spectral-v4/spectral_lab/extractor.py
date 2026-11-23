"""Private single-pass official/sparse feature extraction; aggregate receipts only."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib,inspect,json,time,warnings
import numpy as np
from . import hotspots,features
from .hotspots import THERMAL_NAMES,QUALITY_NAMES,BRIGHTNESS_NAMES

def read_one(root,sid):
    import rasterio
    from rasterio.errors import NotGeoreferencedWarning
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',NotGeoreferencedWarning)
            with rasterio.open(Path(root)/'images'/f'{sid}.tif') as source:chip=source.read()
        if chip.dtype!=np.uint16 or chip.shape!=(14,384,384):raise ValueError('Source array contract mismatch')
        values,diagnostic=hotspots.extract(chip)
        official=features.chip_summary(chip,'official')
        values['official']=np.array([official[n] for n in sorted(official)])
        return values,diagnostic
    except Exception:
        raise RuntimeError('A private source chip failed extraction; no fabricated fallback.') from None

def summarize(diagnostics):
    return {name:{'mean':float(np.mean([d[name] for d in diagnostics])),
                  'max':float(np.max([d[name] for d in diagnostics])),
                  'min':float(np.min([d[name] for d in diagnostics]))} for name in diagnostics[0]}

def profile(root,train_ids,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    chosen=np.random.default_rng(2026).choice(len(train_ids),size=min(32,len(train_ids)),replace=False)
    tick=time.monotonic()
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(lambda i:read_one(root,train_ids[i]),chosen))
    elapsed=time.monotonic()-tick;diags=[r[1] for r in rows]
    thermal=np.array([r[0]['thermal'] for r in rows])
    varying=sum(len(np.unique(col[np.isfinite(col)]))>1 for col in thermal.T)
    supported=sum(d['observable_fraction']>=.1 for d in diags)
    projection=elapsed*4439/len(rows)
    passed=supported>=8 and varying>=2 and projection<=2700
    receipt={'schema':1,'experiment':'label_blind_sparse_profile','chips':len(rows),'seconds':elapsed,
        'workers':2,'linear_full_pass_projection_seconds':projection,'supported_chips':supported,
        'varying_thermal_columns':int(varying),'summary':summarize(diags),'passed':bool(passed),
        'limits':['Projection is not a runtime guarantee. No labels or accuracy inspected.',
                  'Reflectance-shaped anomalies are not calibrated heat/fire measurements.']}
    (output/'profile_receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False))
    # Only private relative-shape overlays, selected without targets; never publish them.
    import matplotlib.pyplot as plt
    for case,i in enumerate(chosen[:6]):
        import rasterio
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with rasterio.open(Path(root)/'images'/f'{train_ids[i]}.tif') as src:chip=src.read()
        r,observed,clear,cloud=hotspots.layers(chip)
        _,mask=hotspots.thermal(r,observed,clear,cloud)
        rgb=np.moveaxis(chip[[3,2,1]].astype(float)*1e-4,0,-1)
        scale=max(float(np.quantile(rgb,.995)),.01)
        fig,axes=plt.subplots(1,2,figsize=(8,3.5))
        axes[0].imshow(np.clip(rgb/scale,0,1));axes[0].set_title(f'Private label-blind case {case+1}')
        axes[1].imshow(np.clip(rgb/scale,0,1));ys,xs=np.where(mask);axes[1].scatter(xs,ys,s=8,facecolors='none',edgecolors='red')
        axes[1].set_title('Sparse spectral candidates; not fire truth')
        for ax in axes:ax.axis('off')
        fig.tight_layout();fig.savefig(output/f'private_overlay_{case+1}.png',dpi=110);plt.close(fig)
    print('SPECTRAL_PROFILE_BEGIN');print(json.dumps(receipt,sort_keys=True));print('SPECTRAL_PROFILE_END',flush=True)
    if not passed:raise RuntimeError('Fixed sparse-profile feasibility gate failed; no automatic threshold adjustment')
    return receipt

def matrices(root,ids,cache):
    cache=Path(cache);source=inspect.getsource(hotspots)+inspect.getsource(features)+inspect.getsource(read_one)
    source_sha=hashlib.sha256(source.encode()).hexdigest()
    fingerprint=hashlib.sha256((source_sha+'\n'+str(Path(root).resolve())+'\n'+'\n'.join(ids)).encode()).hexdigest()
    widths={'official':54,'thermal':12,'quality':4,'brightness':6,'scrambled':12}
    if cache.exists():
        with np.load(cache,allow_pickle=False) as saved:
            if saved['fingerprint'].item()==fingerprint:
                result={name:saved[name].copy() for name in widths}
                if any(a.shape!=(len(ids),widths[n]) or np.isinf(a).any() for n,a in result.items()):raise ValueError('Invalid private feature cache')
                print('Verified sparse private cache loaded.',flush=True)
                return result,json.loads(saved['receipt'].item())
    tick=time.monotonic();rows={name:[] for name in widths};diags=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for count,(values,d) in enumerate(pool.map(lambda sid:read_one(root,sid),ids),1):
            for name in widths:rows[name].append(values[name])
            diags.append(d)
            if time.monotonic()-tick>2700:raise RuntimeError('Extraction exceeded45minutes')
            if count%250==0 or count==len(ids):print('SPARSE_CHIPS',count,len(ids),round(time.monotonic()-tick,1),flush=True)
    result={name:np.asarray(value,dtype=float) for name,value in rows.items()}
    if any(a.shape!=(len(ids),widths[n]) or np.isinf(a).any() for n,a in result.items()):raise ValueError('Invalid feature matrix')
    receipt={'schema':1,'chips':len(ids),'widths':widths,'source_sha256':source_sha,'seconds':time.monotonic()-tick,
        'summary':summarize(diags),'names':{'thermal':THERMAL_NAMES,'quality':QUALITY_NAMES,'brightness':BRIGHTNESS_NAMES,
        'official':sorted(features.chip_summary(np.ones((14,16,16),dtype=np.uint16),'official'))},
        'limits':['L2A content-only descriptors; unknown physical pixel area. No labels used in extraction.']}
    cache.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(cache,**result,fingerprint=np.array(fingerprint),receipt=np.array(json.dumps(receipt,allow_nan=False)))
    return result,receipt
