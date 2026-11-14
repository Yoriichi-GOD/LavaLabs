"""Static research figures from recorded pilot CSVs; no invented evaluation data."""
import argparse,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(source,output):
    src=Path(source);out=Path(output);out.mkdir(parents=True,exist_ok=False)
    cases=['nepal','varanasi','sangam-vihar'];names=['Nepal','Varanasi','Sangam Vihar']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    rows=list(csv.DictReader((src/'ablation.csv').open()))
    states=['CONFLICTING_EVIDENCE','AMBIGUOUS_DIRECTION','INSUFFICIENT_SPATIAL_RESOLUTION','INSUFFICIENT_OBSERVATION','REFERENCE_UNAVAILABLE']
    labels=['Corridor conflict','Ambiguous','Scale insufficient','Observation insufficient','Outlet unavailable']
    colors=['#ba4c35','#ababab','#684e80','#dedede','#3f6978']
    fig,axes=plt.subplots(1,3,figsize=(12,4),sharey=True)
    for ax,case,name in zip(axes,cases,names):
        selected={r['arm']:r for r in rows if r['case']==case};arms=list('ABCDEF');bottom=np.zeros(6)
        for state,label,color in zip(states,labels,colors):
            values=np.array([int(selected[a][state])/int(selected[a]['n']) for a in arms])
            ax.bar(arms,values,bottom=bottom,label=label,color=color);bottom+=values
        ax.set_title(f"{name}: n={selected['A']['n']} units");ax.set_ylim(0,1.02);ax.set_xlabel('Prespecified arm')
    axes[0].set_ylabel('Fraction of fixed evaluation units')
    fig.suptitle('Qualified outcomes: zero physically asserted directions\nConflicts are spectral disagreements, not verified routing errors',fontsize=12)
    handles,labs=axes[0].get_legend_handles_labels();fig.legend(handles,labs,loc='lower center',ncol=3,frameon=False)
    fig.tight_layout(rect=(0,.14,1,.9))
    for ext in ['png','pdf','svg']:fig.savefig(out/('ablation-outcomes.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)
    rows=list(csv.DictReader((src/'terrain-sensitivity.csv').open()))
    fig,axes=plt.subplots(1,3,figsize=(12,4),sharey=True)
    for ax,case,name in zip(axes,cases,names):
        chosen=[r for r in rows if r['case']==case and int(r['stream_area_m2'])==100000]
        order=[(30,'fill'),(30,'none'),(90,'fill'),(90,'none')]
        chosen=[next(r for r in chosen if (int(r['cell_m']),r['conditioning'])==x) for x in order]
        ax.bar(['30m\nfill','30m\nnone','90m\nfill','90m\nnone'],[float(r['changed_fraction']) for r in chosen],color=['#999999','#ba4c35','#3f6978','#684e80'])
        for i,r in enumerate(chosen):ax.text(i,float(r['changed_fraction'])+.025,f"{r['changed_direction_samples']}/\n{r['compared_direction_samples']}",ha='center',fontsize=8)
        ax.set_title(name);ax.set_ylim(0,1.02)
    axes[0].set_ylabel('Fraction of local D8 vectors changed')
    fig.suptitle('Same-unit terrain sensitivity, fixed 0.1 km² stream threshold\nCompared with primary 30 m/fill; changes are not independently verified errors',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.86))
    for ext in ['png','pdf','svg']:fig.savefig(out/('terrain-sensitivity.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)
    rows=list(csv.DictReader((src/'spectral-threshold-summary.csv').open()))
    fig,axes=plt.subplots(1,3,figsize=(12,3.8),sharey=True)
    for ax,case,name in zip(axes,cases,names):
        for family,color in [('NDWI','#3f6978'),('MNDWI','#ba4c35')]:
            chosen=[r for r in rows if r['case']==case and r['family']==family]
            ax.plot([float(r['threshold']) for r in chosen],[float(r['mean_unit_near_fraction']) for r in chosen],marker='o',color=color,label=family)
        ax.set_title(name+f" (clear n={chosen[0]['eligible_units']})");ax.set_xlabel('Correlated threshold');ax.set_xticks([-.1,0,.1]);ax.set_ylim(0,.5)
    axes[0].set_ylabel('Mean near-water sample fraction');axes[-1].legend(frameon=False)
    fig.suptitle('Observed corridor association within 30 m of spectral water\nNot channel-location accuracy or downstream-direction validation',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.85))
    for ext in ['png','pdf','svg']:fig.savefig(out/('spectral-thresholds.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();main(a.source,a.output)
