"""Content-only chip summaries; explicit cloud ablations, no geospatial metadata.

The official feature recipe is adapted from Zelzy's Apache-2.0 starter.
OpenAI Codex assisted the implementation and tests.
"""
import numpy as np

BAND_ORDER = ['B1','B2','B3','B4','B5','B6','B7','B8','B8A','B9','B11','B12','SCL','CLDPRB']
STAT_BANDS = ['B2','B3','B4','B8','B11','B12']
SCL_CLASSES = [2,3,4,5,6,7,8,9,10,11]
MIN_CLEAR = 500


def _statistics(values, prefix):
    if not values.size:
        return {f'{prefix}_{name}': float('nan') for name in ['mean','std','p50','p95','p99','max']}
    p50,p95,p99 = np.percentile(values,[50,95,99])
    return {f'{prefix}_{name}':float(value) for name,value in
            zip(['mean','std','p50','p95','p99','max'],[values.mean(),values.std(),p50,p95,p99,values.max()])}


def _spatial(bands, mask, sufficient):
    names = [f's_{band}_{stat}' for band in ['B11','B12'] for stat in ['centre_mean','outer_mean','centre_minus_outer']]
    names += ['s_ndvi_centre_minus_outer','s_bsi_centre_minus_outer','s_B12_tail_contrast','s_B11_tail_contrast',
              's_B12_centre_std','s_B12_gradient','s_B11_gradient','s_ndvi_gradient','s_centre_clear_fraction','s_outer_clear_fraction']
    if not sufficient:
        return dict.fromkeys(names,float('nan'))
    height,width = mask.shape
    rows,cols = np.indices(mask.shape)
    centre = (rows>=height/4)&(rows<3*height/4)&(cols>=width/4)&(cols<3*width/4)
    c,edge = mask&centre,mask&~centre
    output = {}
    for band in ['B11','B12']:
        a = bands[band]
        cm = float(a[c].mean()) if c.sum()>=20 else float('nan')
        em = float(a[edge].mean()) if edge.sum()>=20 else float('nan')
        output.update({f's_{band}_centre_mean':cm,f's_{band}_outer_mean':em,f's_{band}_centre_minus_outer':cm-em})
    ndvi = (bands['B8']-bands['B4'])/(bands['B8']+bands['B4']+1e-6)
    bsi = ((bands['B11']+bands['B4'])-(bands['B8']+bands['B2']))/(bands['B11']+bands['B4']+bands['B8']+bands['B2']+1e-6)
    for label,a in [('ndvi',ndvi),('bsi',bsi)]:
        output[f's_{label}_centre_minus_outer'] = float(a[c].mean()-a[edge].mean()) if min(c.sum(),edge.sum())>=20 else float('nan')
    for band in ['B12','B11']:
        p50,p99 = np.percentile(bands[band][mask],[50,99])
        output[f's_{band}_tail_contrast'] = float(p99-p50)
    output['s_B12_centre_std'] = float(bands['B12'][c].std()) if c.sum()>=20 else float('nan')
    for label,a in [('B12',bands['B12']),('B11',bands['B11']),('ndvi',ndvi)]:
        vertical = np.abs(np.diff(a,axis=0))[mask[1:]&mask[:-1]]
        horizontal = np.abs(np.diff(a,axis=1))[mask[:,1:]&mask[:,:-1]]
        values = np.concatenate([vertical,horizontal])
        output[f's_{label}_gradient'] = float(values.mean()) if values.size>=20 else float('nan')
    output['s_centre_clear_fraction'] = float(mask[centre].mean())
    output['s_outer_clear_fraction'] = float(mask[~centre].mean())
    return output


def chip_summary(chip, method='official', spatial=False):
    chip = np.asarray(chip)
    if chip.ndim!=3 or chip.shape[0]!=14 or min(chip.shape[1:])<8:
        raise ValueError('Expected fourteen chip layers and at least eight pixels per dimension')
    if method not in {'official','no_fallback','strict'}:
        raise ValueError('Unknown cloud-mask method')
    if not np.isfinite(chip).all():
        raise ValueError('Unexpected nonfinite source chip')
    scl,cloud = chip[12],chip[13]
    has_data = chip[3]>0
    clear = has_data&~np.isin(scl,[3,8,9,10])
    if method=='strict': clear = has_data&np.isin(scl,[4,5,6])&(cloud<20)
    sufficient = clear.sum()>=MIN_CLEAR
    mask = has_data if method=='official' and not sufficient else clear
    bands = {name:chip[index].astype(np.float64)*1e-4 for index,name in enumerate(BAND_ORDER[:12])}
    available = bool(mask.any()) if method=='official' else bool(sufficient)
    output = {}
    for band in STAT_BANDS:
        values = bands[band][mask] if available else np.array([])
        if method=='official' and not values.size: values=np.zeros(1)
        output.update(_statistics(values,f'c_{band}'))
    if available:
        b4,b8,b11,b12 = (bands[name][mask] for name in ['B4','B8','B11','B12'])
        ndvi = (b8-b4)/(b8+b4+1e-6)
        values = [ndvi.std(),np.percentile(ndvi,95),np.percentile(b12/(b11+1e-6),95),
                  (b12>.2).mean(),(b12>.4).mean(),(b11>.4).mean()]
    else:
        values = [0.]*6 if method=='official' else [float('nan')]*6
    output.update(dict(zip(['c_ndvi_std','c_ndvi_p95','c_b12_b11_p95','c_hot12_gt_0.2','c_hot12_gt_0.4','c_hot11_gt_0.4'],map(float,values))))
    for cls in SCL_CLASSES: output[f'c_scl_{cls}']=float((scl==cls).mean())
    output['c_cloudprob']=float(cloud.mean())
    output['c_valid_frac']=float(mask.mean())
    if method!='official':
        output['q_insufficient_clear']=float(not sufficient)
        output['q_clear_count']=float(clear.sum())
        output['q_cloud_high_fraction']=float((cloud>=40).mean())
    if spatial: output.update(_spatial(bands,mask,available))
    return output
