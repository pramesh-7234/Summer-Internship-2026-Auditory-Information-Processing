"""Regenerate the figures from executed seed tables and a fixed example simulation.

Run from any directory with python /path/to/make_figures.py.
The example seed and plotting rules are fixed, independent of the responses.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Patch
from matplotlib.ticker import ScalarFormatter
import numpy as np
import pandas as pd
from scipy.stats import t as student_t


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
RESULTS = ROOT / "results"
EXAMPLE_SEED = 1001
REGIMES = ("early", "late")
AGE_COLOR = {"early": "#146965", "late": "#a44b27"}
ROLE_COLOR = {"standard": "#355e8b", "deviant": "#aa441e"}
POP_COLOR = ("#006b66", "#745089", "#305a89")
INK = "#1e2f37"
MUTED = "#536776"


def style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9.4, "axes.titlesize": 10.5,
        "axes.titleweight": "bold", "axes.labelsize": 9.3,
        "axes.labelcolor": INK, "axes.edgecolor": "#859298", "axes.linewidth": 0.75,
        "text.color": INK, "xtick.color": INK, "ytick.color": INK,
        "xtick.labelsize": 8.5, "ytick.labelsize": 8.5, "xtick.major.size": 3.0,
        "ytick.major.size": 3.0, "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "legend.fontsize": 8.5, "svg.fonttype": "none",
        "pdf.fonttype": 42, "savefig.facecolor": "white", "figure.facecolor": "white",
    })


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=245, bbox_inches="tight", pad_inches=0.16)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight", pad_inches=0.16)
    plt.close(fig)


def title(ax, label, text):
    ax.set_title(f"{label}   {text}", loc="left", pad=10)


def form_rows(frame, condition="intact", epoch="all"):
    return frame.loc[(frame["condition"] == condition) & (frame["epoch"] == epoch)]


def ci(values):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return np.nan, np.nan
    if len(a) == 1:
        return a[0], 0
    return a.mean(), student_t.ppf(.975, len(a) - 1) * a.std(ddof=1) / np.sqrt(len(a))


def soft_grid(ax, axis="y"):
    ax.set_axisbelow(True)
    ax.grid(True, axis=axis, color="#dfe4e7", linewidth=0.6)


def zero(ax, axis="y"):
    if axis == "y":
        ax.axhline(0, color=MUTED, linewidth=.8, linestyle=(0, (3, 3)), zorder=1)
    else:
        ax.axvline(0, color=MUTED, linewidth=.8, linestyle=(0, (3, 3)), zorder=1)


def fmt_small(ax, axis="y"):
    fmt = ScalarFormatter(useMathText=True, useOffset=False)
    fmt.set_powerlimits((-3, 3))
    getattr(ax, f"{axis}axis").set_major_formatter(fmt)


def age_legend(ax, **kwargs):
    artists = [Line2D([], [], color=AGE_COLOR[r], marker="o", lw=1.5,
                      markersize=4, label=r.title()) for r in REGIMES]
    ax.legend(handles=artists, ncol=2, **kwargs)


def fixed_examples():
    from auditory import Config, simulate
    return {r: simulate(Config.for_regime(r), seed=EXAMPLE_SEED, n_tokens=100,
                        protocol="oddball", swap=False) for r in REGIMES}


def network_diagram(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    def node(x, y, w, h, label, color):
        p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.013,rounding_size=0.018",
                           facecolor=color, edgecolor=color, linewidth=1)
        ax.add_patch(p)
        ax.text(x+w/2, y+h/2, label, ha="center", va="center", color="white",
                fontsize=9, weight="bold", linespacing=1.3)

    def arrow(a, b, color=INK, inhibitory=False):
        if inhibitory:
            ax.plot([a[0], b[0]], [a[1], b[1]], c=color, lw=1.7)
            # Construct a perpendicular endpoint bar in display coordinates.
            p0, p1 = ax.transData.transform([a, b])
            vx, vy = p1 - p0
            normal = 5 * np.array([-vy, vx]) / np.hypot(vx, vy)
            h, j = ax.transData.inverted().transform([p1 - normal, p1 + normal])
            ax.plot([h[0], j[0]], [h[1], j[1]], c=color, lw=1.7)
        else:
            ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=14,
                                         lw=1.7, color=color, shrinkA=0, shrinkB=0))

    # Direct and relayed paths share presynaptic input.
    node(.035, .42, .20, .17, "Thalamus\n40 fibers", "#535f6a")
    node(.34, .72, .16, .15, "Subplate\n40 cells", POP_COLOR[0])
    node(.60, .72, .18, .15, "Inhibitory\n10 cells", POP_COLOR[1])
    node(.80, .42, .16, .17, "Layer 4\n40 cells", POP_COLOR[2])
    arrow((.24, .588), (.334, .732))
    arrow((.514, .79), (.580, .79))
    arrow((.507, .729), (.80, .576))
    arrow((.785, .731), (.867, .608), POP_COLOR[1], True)
    arrow((.252, .476), (.781, .476), ROLE_COLOR["deviant"])
    ax.text(.517, .415, "Direct, STDP", color=ROLE_COLOR["deviant"], ha="center",
            va="top", weight="bold", fontsize=9.5)
    ax.text(.5, .20, "Arrowhead = excitation     Bar = inhibition",
            color=MUTED, ha="center", fontsize=8.7)
    ax.text(.5, .12, "Thalamic and subplate outputs depress.",
            ha="center", color=MUTED, fontsize=8.7)


def circuit(examples):
    fig = plt.figure(figsize=(9.9, 3.7), layout="constrained")
    gs = fig.add_gridspec(1, 3, width_ratios=(1.85, 1, 1), wspace=.16)
    diagram = fig.add_subplot(gs[0])
    title(diagram, "A", "Feedforward auditory circuit")
    network_diagram(diagram)
    axs = [fig.add_subplot(gs[i]) for i in (1, 2)]
    peak = max(np.max(r.direct_base * r.initial_weights) for r in examples.values())
    for i, (regime, ax) in enumerate(zip(REGIMES, axs)):
        r = examples[regime]
        values = np.ma.masked_where(~np.asarray(r.mask, dtype=bool), r.direct_base * r.initial_weights)
        cmap = plt.get_cmap("viridis").copy()
        cmap.set_bad("#e7e9e9")
        im = ax.imshow(values, interpolation="nearest", cmap=cmap, vmin=0, vmax=peak,
                       origin="lower", aspect="equal")
        ax.set(xticks=[0, 19, 39], xticklabels=[1, 20, 40],
               yticks=[0, 19, 39], yticklabels=[1, 20, 40],
               xlabel="Thalamic fiber")
        if i == 0:
            ax.set_ylabel("Layer 4 neuron")
        title(ax, "BC"[i], f"{regime.title()} direct input")
    cb = fig.colorbar(im, ax=axs, orientation="horizontal", shrink=.84, pad=.09, aspect=32)
    cb.set_label(r"Recovered increment ($g/g_L$)   ·   gray = absent", fontsize=8.6)
    save(fig, "01_circuit")


def example_activity(examples, stim_ms):
    r0 = examples["early"]
    dev = int(np.flatnonzero(r0.tones == r0.deviant)[0])
    first = int(np.clip(dev - 2, 0, len(r0.tones) - 8))
    last = first + 8
    a = r0.onsets[first] - 55
    b = r0.onsets[last - 1] + 140
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(9, 5.2), layout="constrained")
    for i, (ax, (regime, r)) in enumerate(zip(axes, examples.items())):
        for k in range(first, last):
            role = "deviant" if r.tones[k] == r.deviant else "standard"
            ax.axvspan(r.onsets[k] / 1000, (r.onsets[k] + stim_ms) / 1000, color=ROLE_COLOR[role],
                       alpha=.16, lw=0, zorder=0)
        mask = (r.times >= a) & (r.times <= b)
        cells = r.cells[mask]
        palette = np.array(POP_COLOR)[np.digitize(cells, [40, 50])]
        ax.scatter(r.times[mask] / 1000, cells + 1, c=palette, s=8, marker="|", linewidths=.60)
        for separator in (40.5, 50.5):
            ax.axhline(separator, c="#a3afb1", lw=.55)
        ax.set(xlim=(a/1000, b/1000), ylim=(0, 91), yticks=[20.5, 45.5, 70.5],
               yticklabels=["SP (40)", "IN (10)", "L4 (40)"])
        title(ax, "AB"[i], f"{regime.title()} regime")
    axes[0].legend(handles=[Patch(facecolor=ROLE_COLOR[role], alpha=.28, label=role.title())
                            for role in ROLE_COLOR], loc="lower right", ncol=2,
                   bbox_to_anchor=(1, 1.02), borderaxespad=0)
    axes[-1].set_xlabel("Time from simulation start (s)")
    save(fig, "02_example_activity")


def role_responses(frame):
    intact, many = form_rows(frame), form_rows(frame, "many")
    fig, axs = plt.subplots(1, 3, figsize=(10.8, 3.7), layout="constrained",
                            gridspec_kw={"width_ratios": [1, 1.08, 1]})
    ax = axs[0]
    for j, reg in enumerate(REGIMES):
        data = intact[intact.regime == reg].sort_values("seed")
        xx = np.array([0, 1]) + j * .12 - .06
        yy = data[["l4_std_hz", "l4_dev_hz"]].to_numpy()
        for pair in yy:
            ax.plot(xx, pair, lw=.65, alpha=.22, c=AGE_COLOR[reg], marker="o", ms=2)
        centers, errs = zip(*(ci(v) for v in yy.T))
        ax.errorbar(xx, centers, yerr=errs, lw=1.9, color=AGE_COLOR[reg], fmt="o-",
                    ms=5, capsize=3, zorder=4)
    ax.set(xticks=[0, 1], xticklabels=["Standard", "Deviant"], xlim=(-.28, 1.28),
           ylabel="Evoked rate above baseline (Hz/cell)")
    soft_grid(ax)
    title(ax, "A", "Layer 4 by role")
    for j, reg in enumerate(REGIMES):
        data = intact[intact.regime == reg].sort_values("seed")
        ax = axs[1]
        for k, name in enumerate(("sp", "i", "l4")):
            vals = data[f"{name}_dev_hz"] - data[f"{name}_std_hz"]
            x = k + (j - .5) * .24
            ax.scatter(x+np.linspace(-.036,.036,len(vals)), vals,
                       s=6, color=AGE_COLOR[reg], alpha=.28)
            mean, err = ci(vals)
            ax.errorbar(x, mean, yerr=err, fmt="o", ms=5, capsize=3, color=AGE_COLOR[reg])
        ax = axs[2]
        combined = data.set_index("seed")[["l4_dev_hz"]].join(
            many[many.regime == reg].set_index("seed")[["l4_dev_hz"]],
            how="inner", lsuffix="_oddball", rsuffix="_many")
        vals = (combined.iloc[:,0] - combined.iloc[:,1]).values
        ax.scatter(j+np.linspace(-.075,.075,len(vals)), vals, color=AGE_COLOR[reg],
                   alpha=.45, s=13)
        mean, err = ci(vals)
        ax.errorbar(j, mean, yerr=err, ms=6, fmt="o", capsize=4, color=AGE_COLOR[reg])
    ax = axs[1]
    ax.set(xticks=[0,1,2], xticklabels=["SP", "IN", "L4"], xlim=(-.45,2.45),
           ylabel="Deviant − standard (Hz/cell)")
    soft_grid(ax)
    zero(ax)
    title(ax, "B", "Role contrast by population")
    ax = axs[2]
    ax.set(xticks=[0,1], xticklabels=["Early", "Late"], xlim=(-.45,1.45),
           ylabel="Oddball − many-standards (Hz/cell)")
    soft_grid(ax)
    zero(ax)
    title(ax, "C", "Layer 4, matched rare tone")
    age_legend(axs[0], loc="best", handlelength=1.2)
    save(fig, "03_role_responses")


def plasticity(frame, trajectories, examples):
    subset = trajectories[trajectories.condition == "intact"].copy()
    # Center each trajectory on its own initial value before averaging identity swaps.
    keys = ["regime", "role", "seed", "swap"]
    initial = subset.loc[subset.token == subset.token.min(), keys + ["efficacy"]]
    joined = subset.merge(initial.rename(columns={"efficacy": "start"}), on=keys,
                          validate="many_to_one")
    joined["change"] = joined.efficacy - joined.start
    points = (joined.groupby(["regime", "role", "seed", "token"], as_index=False)
              .agg(change=("change", "mean")))
    fig, axes = plt.subplots(2, 2, figsize=(9.1, 5.9), layout="constrained")
    for idx, regime in enumerate(REGIMES):
        ax = axes[0, idx]
        for role, color in ROLE_COLOR.items():
            tag = {"standard": "std", "deviant": "dev"}[role]
            d = points[(points.regime == regime) & (points.role == tag)]
            pivot = d.pivot(index="token", columns="seed", values="change").sort_index()
            xy = pivot.index.to_numpy()
            mean, err = np.array([ci(row) for row in pivot.to_numpy()]).T
            ax.fill_between(xy, mean-err, mean+err, alpha=.15, lw=0, color=color)
            ax.plot(xy, mean, color=color, lw=2, ls="-" if role == "standard" else "--",
                    label=role.title())
        title(ax, "AB"[idx], f"{regime.title()} direct-path learning")
        ax.set_xlabel("Completed tone presentations")
        ax.set_ylabel("Change in mean efficacy")
        ax.set_xlim(0, points.token.max())
        soft_grid(ax)
        zero(ax)
        fmt_small(ax)
        if idx == 0:
            ax.legend(loc="best")
    # Shared vertical limits let the slopes be compared directly across regimes.
    y_extent = [ax.get_ylim() for ax in axes[0]]
    for ax in axes[0]:
        ax.set_ylim(min(v[0] for v in y_extent), max(v[1] for v in y_extent))
    ax = axes[1, 0]
    for i, reg in enumerate(REGIMES):
        sub = frame[(frame.condition == "intact") & (frame.regime == reg)]
        d = sub.pivot(index="seed", columns="epoch", values="dweight_dev_minus_std")
        names = ["first_half", "second_half"]
        x = np.arange(2) + (i - .5) * .13
        for y in d[names].to_numpy():
            ax.plot(x, y, color=AGE_COLOR[reg], alpha=.2, lw=.7)
        mean, err = np.array([ci(d[n]) for n in names]).T
        ax.errorbar(x, mean, yerr=err, fmt="o-", color=AGE_COLOR[reg], ms=5, capsize=3)
    ax.set(xticks=[0, 1], xticklabels=["Midpoint", "Endpoint"], xlim=(-.24, 1.24),
           ylabel="Deviant − standard efficacy change")
    title(ax, "C", "Cumulative learning contrast")
    soft_grid(ax)
    zero(ax)
    fmt_small(ax)
    age_legend(ax, loc="best")
    ax = axes[1, 1]
    samples = {reg: (r.final_weights - r.initial_weights)[np.asarray(r.mask, dtype=bool)]
               for reg, r in examples.items()}
    for reg in REGIMES:
        values = np.sort(samples[reg])
        ax.step(values, np.arange(1, len(values)+1)/len(values), where="post", lw=1.65,
                color=AGE_COLOR[reg], label=reg.title(), ls="-" if reg == "early" else "--")
    title(ax, "D", "Single-seed edge distribution")
    ax.set(xlabel="Final − initial efficacy, connected edges", ylabel="Cumulative fraction",
           ylim=(0,1.04))
    fmt_small(ax, "x")
    soft_grid(ax)
    zero(ax, "x")
    ax.legend(loc="best")
    save(fig, "04_plasticity")


def forest(axis, frame, regimes, names, values, metric, xlabel, delta=True):
    baseline = form_rows(frame).set_index(["regime", "seed"])[metric]
    for j, key in enumerate(values):
        rows = form_rows(frame, key).set_index(["regime","seed"])[metric]
        for k, regime in enumerate(regimes):
            z = rows.loc[regime]
            if delta:
                z = z - baseline.loc[regime]
            mean, err = ci(z)
            y = j + (k - .5)*.29
            axis.errorbar(mean, y, xerr=err, c=AGE_COLOR[regime], fmt="o",
                          ms=4.5, capsize=2.3, elinewidth=1.4, zorder=3)
    axis.set(yticks=np.arange(len(names)), yticklabels=names, xlabel=xlabel,
             ylim=(len(names)-.5,-.5))
    axis.tick_params(axis="y", length=0)
    for j in range(0,len(names),2):
        axis.axhspan(j-.48,j+.48,color="#f1f4f4",zorder=0,lw=0)
    soft_grid(axis, "x")
    zero(axis, "x")


def ablations(frame):
    key_names = [("no_stdp", "STDP off"), ("no_std", "Depression off"),
                 ("no_plasticity", "STD + STDP off"), ("no_sp_l4", "SP → L4 off"), ("no_inhibition", "Inhibition off"),
                 ("no_direct", "Thalamus → L4 off")]
    present = set(frame.condition)
    keys, labels = zip(*[(k,v) for k,v in key_names if k in present])
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.7), layout="constrained")
    # Available effects are paired within each seed and developmental regime.
    forest(axes[0], frame, REGIMES, labels, keys, "l4_dev_minus_std_hz",
           "Change in deviant − standard rate (Hz/cell)")
    title(axes[0], "A", "Ablation effect on the Layer 4 role contrast")
    # Deleting the entire direct pathway leaves no direct synapse to interpret.
    indices = [i for i,k in enumerate(keys) if k != "no_direct"]
    forest(axes[1], frame, REGIMES, [labels[i] for i in indices],
           [keys[i] for i in indices], "dweight_dev_minus_std",
           "Change in deviant − standard efficacy gain")
    fmt_small(axes[1], "x")
    title(axes[1], "B", "Ablation effect on direct-path learning")
    age_legend(axes[0], loc="upper left", bbox_to_anchor=(0, -.18), borderaxespad=0)
    save(fig, "05_ablations")


def sensitivity(frame):
    params = [("threshold", "Threshold", "−2 mV", "+2 mV"),
              ("recovery", "Recovery time", "×0.75", "×1.25"),
              ("rate", "Input rate", "×0.75", "×1.25"),
              ("learning", "Learning rate", "×0.50", "×1.50"),
              ("ltp", "LTP amplitude", "×0.80", "×1.20"),
              ("width", "Tuning width", "×0.75", "×1.25")]
    keys, names = [], []
    for param, name, lo, hi in params:
        for which, label in [("lo",lo),("hi",hi)]:
            key = f"{param}_{which}"
            if key in set(frame.condition):
                keys.append(key)
                names.append(f"{name}   {label}")
    fig, axes = plt.subplots(1,2,figsize=(9.7,5.3), layout="constrained")
    forest(axes[0], frame, REGIMES, names, keys, "l4_dev_minus_std_hz",
           "Change in deviant − standard rate (Hz/cell)")
    title(axes[0], "A", "Layer 4 role contrast")
    forest(axes[1], frame, REGIMES, names, keys, "dweight_dev_minus_std",
           "Change in deviant − standard efficacy gain")
    fmt_small(axes[1], "x")
    title(axes[1], "B", "Direct-path learning contrast")
    age_legend(axes[1], loc="upper left", bbox_to_anchor=(0,-.14), borderaxespad=0)
    save(fig,"06_sensitivity")



def held_out(frame):
    """Plot pairing by seed and training role for identical test-tone events."""
    fig, axes = plt.subplots(2, 2, figsize=(8.8, 6.3), layout="constrained",
                             sharey="row", sharex=True)
    for col, n_tokens in enumerate((100, 1000)):
        block = frame[frame.n_tokens == n_tokens]
        n_seeds = block.seed.nunique()
        for row, (measure, population) in enumerate((
                ("gain_hz", "All L4 cells"), ("tuned_gain_hz", "Top four recipients"))):
            ax = axes[row, col]
            for j, reg in enumerate(REGIMES):
                data = block[block.age == reg].sort_values("seed")
                xx = np.arange(2) + (j - .5) * .14
                yy = data[[f"{measure}_standard", f"{measure}_deviant"]].to_numpy()
                for pair in yy:
                    ax.plot(xx, pair, lw=.75, alpha=.28, color=AGE_COLOR[reg],
                            marker="o", ms=2.4)
                mean, err = np.array([ci(role) for role in yy.T]).T
                ax.errorbar(xx, mean, yerr=err, fmt="o-", ms=5, lw=1.8,
                            capsize=3.5, color=AGE_COLOR[reg], zorder=4)
            title(ax, "ABCD"[2*row+col], f"{population} · {n_tokens:,} training tones")
            ax.set(xticks=[0, 1], xticklabels=["Standard", "Deviant"], xlim=(-.22, 1.22))
            if col == 0:
                ax.set_ylabel("Post − pre probe response (Hz/cell)")
            if row == 1:
                ax.set_xlabel(f"Training role ({n_seeds} seeds)")
            soft_grid(ax)
            zero(ax)
    age_legend(axes[0,0], loc="best")
    save(fig, "07_held_out")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["circuit","raster","responses","plasticity",
                                           "ablations","sensitivity","held_out"], nargs="+")
    args=parser.parse_args()
    draw=set(args.only or ("circuit","raster","responses","plasticity","ablations","sensitivity","held_out"))
    style()
    examples = fixed_examples() if draw & {"circuit", "raster", "plasticity"} else None
    frame = pd.read_csv(RESULTS / "seed_metrics.csv") if draw & {"plasticity", "responses", "ablations", "sensitivity"} else None
    if "circuit" in draw:
        circuit(examples)
    if "raster" in draw:
        example_activity(examples, stim_ms=50)
    if "responses" in draw:
        role_responses(frame)
    if "plasticity" in draw:
        trajectories = pd.read_csv(RESULTS / "weight_trajectories.csv")
        plasticity(frame, trajectories, examples)
    if "ablations" in draw:
        ablations(frame)
    if "sensitivity" in draw:
        sensitivity(frame)
    if "held_out" in draw:
        held_out(pd.read_csv(RESULTS / "probe_seeds.csv"))


if __name__ == "__main__":
    main()
