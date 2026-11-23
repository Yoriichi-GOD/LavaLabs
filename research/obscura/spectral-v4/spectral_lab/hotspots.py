"""Independent physics-inspired descriptors, not calibrated fire detections.

Motivated by Massimetti2020, Fisher/Wooster2018 and the public methods reviewed
in literature-20261123. No third-party implementation is vendored.
"""
import numpy as np
from scipy.ndimage import uniform_filter,label

EPS=1e-10
STRUCTURE_NAMES=['peak','top8_mean','selected_sum','selected_count','components8','largest_component_fraction']
THERMAL_NAMES=[f'h_{n}' for n in STRUCTURE_NAMES]+[
    'h_mean_positive_e12','h_max_positive_e11','h_median_nir_excess_ratio',
    'h_low_nir_fraction','h_candidate_nonclear_fraction','h_background_support_fraction']
QUALITY_NAMES=['q_observable_fraction','q_clear_fraction','q_valid_cloud_mean','q_defect_flag_fraction']
BRIGHTNESS_NAMES=[f'b_{n}' for n in STRUCTURE_NAMES]

def validate(chip):
    chip=np.asarray(chip)
    if chip.ndim!=3 or chip.shape[0]!=14 or min(chip.shape[1:])<15:raise ValueError('Expected14layers and >=15pixels')
    if not np.isfinite(chip).all() or (chip<0).any():raise ValueError('Invalid nonfinite/negative source pixel')
    if (chip[13]>100).any() or (chip[12]>11).any():raise ValueError('Quality layer scale mismatch')
    if not np.equal(chip[12],np.floor(chip[12])).all():raise ValueError('Noninteger scene classes')
    return chip

def layers(chip):
    # B8A is zero-based8; B11=10,B12=11. Float BEFORE subtraction.
    r=chip[[8,10,11]].astype(np.float64)*1e-4
    scl=chip[12];cloud=chip[13].astype(float)*.01
    observed=(r.sum(axis=0)>0)&~np.isin(scl,[0,1])
    clear=observed&~np.isin(scl,[3,8,9,10])&(cloud<.4)
    return r,observed,clear,cloud

def local_mean(values,valid):
    total=uniform_filter(np.where(valid,values,0.),size=15,mode='constant',cval=0.)
    support=uniform_filter(valid.astype(float),size=15,mode='constant',cval=0.)
    return np.divide(total,support,out=np.zeros_like(total),where=support>0)

def select(score,eligible):
    idx=np.flatnonzero(eligible&(score>EPS))
    if len(idx):idx=idx[np.lexsort((idx,-score.ravel()[idx]))[:32]]
    selected=np.zeros(score.shape,dtype=bool);selected.ravel()[idx]=True
    return idx,selected

def structure(score,idx,selected,has_observations):
    if not has_observations:return np.full(6,np.nan)
    if not len(idx):return np.array([np.nan,np.nan,0.,0.,0.,np.nan])
    values=score.ravel()[idx]
    components,n=label(selected,structure=np.ones((3,3),dtype=np.uint8))
    largest=np.bincount(components.ravel())[1:].max()
    return np.array([values.max(),values[:8].mean(),values.sum(),len(idx),n,largest/len(idx)],dtype=float)

def thermal(r,observed,clear,cloud):
    r8a,r11,r12=r
    positive=np.maximum((r12-r11)/np.maximum(r8a,.02),0.)
    score=positive-local_mean(positive,observed)
    curvature=r12-2*r11+r8a
    idx,selected=select(score,observed&(curvature>EPS))
    first=structure(score,idx,selected,bool(observed.any()))
    if not len(idx):return np.r_[first,np.full(6,np.nan)],selected
    height,width=observed.shape;excess=[]
    for flat in idx:
        row,col=divmod(int(flat),width)
        top,bottom=max(row-7,0),min(row+8,height);left,right=max(col-7,0),min(col+8,width)
        background=(clear&~selected)[top:bottom,left:right].copy()
        ys,xs=np.ogrid[top:bottom,left:right]
        background[(abs(ys-row)<=1)&(abs(xs-col)<=1)]=False
        if background.sum()>=16:
            local=r[:,top:bottom,left:right][:,background]
            excess.append(r[:,row,col]-np.median(local,axis=1))
    cloudy=float(np.mean(~clear.ravel()[idx]));support=len(excess)/len(idx)
    if excess:
        e=np.asarray(excess);positive12=e[:,2]>0
        ratio=float(np.median(e[positive12,0]/np.maximum(e[positive12,2],.02))) if positive12.any() else np.nan
        low=float(np.mean(e[positive12,0]<.1*e[positive12,2])) if positive12.any() else np.nan
        context=[np.maximum(e[:,2],0).mean(),np.maximum(e[:,1],0).max(),ratio,low,cloudy,support]
    else:context=[np.nan,np.nan,np.nan,np.nan,cloudy,support]
    return np.r_[first,context],selected

def extract(chip,include_scramble=True):
    chip=validate(chip);r,observed,clear,cloud=layers(chip)
    h,selected=thermal(r,observed,clear,cloud)
    bright=r[2]-local_mean(r[2],observed)
    bi,bmask=select(bright,observed)
    b=structure(bright,bi,bmask,bool(observed.any()))
    q=np.array([observed.mean(),clear.mean(),cloud[observed].mean() if observed.any() else np.nan,(chip[12]==1).mean()])
    result={'thermal':h,'quality':q,'brightness':b}
    if include_scramble:
        perm=np.random.default_rng(2026).permutation(observed.size)
        shape=observed.shape
        sr=r.reshape(3,-1)[:,perm].reshape(r.shape)
        so=observed.ravel()[perm].reshape(shape);sc=clear.ravel()[perm].reshape(shape);sp=cloud.ravel()[perm].reshape(shape)
        result['scrambled']=thermal(sr,so,sc,sp)[0]
    if any(np.isinf(value).any() for value in result.values()):raise ValueError('Infinite extracted feature')
    diagnostic={'observable_fraction':float(observed.mean()),'clear_fraction':float(clear.mean()),
        'candidate_count':int(selected.sum()),'strict_clear_candidate_count':int((selected&clear).sum()),
        'band_over_one_fraction':float((r>1).mean()),'band_max':float(r.max()),
        'quality_flag1_fraction':float((chip[12]==1).mean())}
    return result,diagnostic
