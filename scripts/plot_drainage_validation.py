"""Export the two drainage comparisons on their recorded denominators."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def run(verified, output):
    regional = json.loads((verified / "regional-summary.json").read_text())["cases"]
    field = json.loads((verified / "verification.json").read_text())["observed_pooled_descriptive_recount"]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "pdf.fonttype": 42})
    figure, (left, right) = plt.subplots(1, 2, figsize=(12.5, 4.4), layout="constrained")
    labels = ["Nepal", "Varanasi", "Sangam Vihar"]
    cases = [regional[key]["glo30_merit"] for key in ["nepal", "varanasi", "sangam-vihar"]]
    bars = left.barh(labels, [100*r["at_least_90deg"]/r["paired_samples"] for r in cases],
                     height=.55, color="#506682")
    left.bar_label(bars, labels=[f'{r["at_least_90deg"]:,}/{r["paired_samples"]:,}' for r in cases],
                   padding=5, fontsize=9)
    left.invert_yaxis()
    left.set_xlim(0, 65)
    left.set_xlabel("Paired samples differing by 90° or more (%)")
    left.set_title("Copernicus 30 m vs MERIT-derived directions", loc="left", fontsize=11, fontweight="bold")

    models = ["GLO30_30m_fill", "GLO30_90m_fill", "MERIT_derived_native"]
    values = [field[model] for model in models]
    labels = ["Copernicus 30 m, filled", "Copernicus 90 m, filled", "MERIT-derived native"]
    y = np.arange(len(labels))
    bars = right.barh(y-.16, [r["positive_cosine"] for r in values], height=.29,
                      color="#506682", label="Error < 90°")
    right.bar_label(bars, labels=[str(r["positive_cosine"]) for r in values], padding=4, fontsize=9)
    bars = right.barh(y+.16, [r["at_most45deg"] for r in values], height=.29,
                      color="#c47d43", label="Error ≤ 45°")
    right.bar_label(bars, labels=[str(r["at_most45deg"]) for r in values], padding=4, fontsize=9)
    right.set_yticks(y, labels)
    right.set_ylim(2.85, -.55)
    right.set_xlim(0, 42)
    right.set_xticks([0, 10, 20, 30, 42])
    right.set_xlabel("Blocks out of 42 with observed ADCP reference")
    right.set_title("South Saskatchewan River, 2015–2017", loc="left", fontsize=11, fontweight="bold")
    right.legend(loc="lower right", frameon=False, fontsize=9)
    for axis in (left, right):
        axis.set_axisbelow(True)
        axis.grid(axis="x", color="#e1e5ea", linewidth=.7)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.tick_params(axis="y", length=0, pad=7)
    figure.suptitle("Drainage direction agreement depends on source and support",
                    fontsize=15, fontweight="bold")
    for suffix in [".png", ".pdf"]:
        figure.savefig(output.with_suffix(suffix), dpi=220, facecolor="white")
    plt.close(figure)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verified", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.verified, args.output)
