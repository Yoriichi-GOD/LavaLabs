"""Plot review gains and the recall comparison on explicitly flagged roads."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main(folder):
    evidence = folder / "verified"
    water = json.loads((evidence / "spectral-reserve.json").read_text())["totals"]
    road = json.loads((evidence / "ahr-results.json").read_text())["explicit_positive_only"]
    fig, (left, right) = plt.subplots(1,2,figsize=(11.4,4.3),layout="constrained")
    for ax in [left,right]:
        ax.spines[["top","right","left"]].set_visible(False)
        ax.grid(axis="x", color="#e0e5e8")
        ax.set_axisbelow(True)
        ax.tick_params(axis="y",length=0)
    colors = ["#557083", "#16715a", "#ae6744"]
    methods = ["margin","ndvi","either"]
    names = ["MNDWI margin","NDVI flag + margin","NDVI or NDWI + margin"]
    for i, (method, name) in enumerate(zip(methods,names)):
        values = [100*water[b][method]["error_recall"] for b in ["0.1","0.2"]]
        bars = left.barh(np.arange(2)+(i-1)*.23,values,height=.2,color=colors[i],label=name)
        left.bar_label(bars,labels=[f"{v:.1f}%" for v in values],padding=4,fontsize=8)
    left.set_yticks([0,1],["10% review","20% review"])
    left.set_ylim(1.48,-.45)
    left.set_xlim(0,43)
    left.set_xlabel("Baseline errors captured (%)")
    left.set_title("Water review · four held-out windows",loc="left",fontweight="bold")
    left.legend(fontsize=8,frameon=False,loc="upper right")

    labels = ["Direct change overlap","Terrain path","Euclidean proximity"]
    hits = [road["positive_hits"][key] for key in ["B_change","C_terrain","P_proximity"]]
    bars = right.barh(labels,hits,height=.52,color=["#557083","#607da1","#16715a"])
    right.bar_label(bars,labels=[f"{n}/{road['positive']}" for n in hits],padding=4,fontsize=9)
    right.invert_yaxis()
    right.set_xlim(0,44)
    right.set_xticks([0,10,20,30,44])
    right.set_xlabel("Explicitly flagged roads found")
    right.set_title("Road screening · Ahr Valley, July 2021",loc="left",fontweight="bold")
    for ext in ["png","pdf"]:
        fig.savefig(folder/f"review-and-exposure.{ext}",dpi=220,facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder",type=Path)
    main(parser.parse_args().folder)
