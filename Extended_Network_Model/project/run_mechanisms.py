"""Separate the locations of depression and test the original recovery-time extremes."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t

from auditory import Config, simulate
from run_experiments import event_table

ROOT = Path(__file__).resolve().parent
CONDITIONS = ("intact", "thalamus_only", "subplate_only", "neither", "recovery_100", "recovery_4200")


def one_seed(args):
    age, seed = args
    samples = []
    for condition in CONDITIONS:
        cfg = Config.for_regime(age)
        if condition.startswith("recovery_"):
            cfg = replace(cfg, tau_rec=float(condition.split("_")[1]))
        else:
            cfg = replace(cfg, thalamic_std=condition in ("intact", "thalamus_only"),
                          subplate_std=condition in ("intact", "subplate_only"))
        for swap in (False, True):
            common = {}
            for protocol in ("oddball", "many"):
                r = simulate(cfg, seed=seed, n_tokens=100, protocol=protocol, swap=swap)
                tab = event_table(r)
                for pop in ("sp", "l4"):
                    for role in ("dev", "std"):
                        raw = tab.loc[tab.role == role]
                        common[protocol, pop, role] = (raw[pop + "_post"] - raw[pop + "_pre"]).mean() / 4
                if protocol == "oddball":
                    dw = r.weight_history[-1] - r.weight_history[0]
                    dev_dw, std_dw = dw[r.deviant], dw[r.standard]
            contrasts = {}
            for pop in ("sp", "l4"):
                d = common["oddball", pop, "dev"]
                s = common["oddball", pop, "std"]
                contrasts[pop + "_role_hz"] = d - s
                contrasts[pop + "_index"] = (d-s)/(abs(d)+abs(s)) if (abs(d)+abs(s)) else np.nan
                contrasts[pop + "_context_hz"] = d - common["many", pop, "dev"]
            samples.append(dict(age=age, seed=seed, swap=swap, condition=condition,
                                layer_index_gap=contrasts["sp_index"] - contrasts["l4_index"],
                                dweight_dev_minus_std=dev_dw-std_dw, **contrasts))
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    tasks = [(a, s) for s in range(1001, 1009) for a in ("early","late")]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        rows = [r for group in pool.map(one_seed, tasks) for r in group]
    seeds = pd.DataFrame(rows).drop(columns="swap").groupby(["age","condition","seed"]).mean().reset_index()
    summary = []
    for (age, condition), group in seeds.groupby(["age","condition"]):
        for name in seeds.columns[3:]:
            x = group[name].dropna()
            mean = x.mean()
            half = t.ppf(0.975, len(x)-1)*x.sem()
            summary.append(dict(age=age, condition=condition, metric=name, n_seeds=len(x),
                                mean=mean, ci_low=mean-half, ci_high=mean+half))
    args.output.mkdir(parents=True, exist_ok=True)
    seeds.to_csv(args.output / "mechanism_seeds.csv", index=False, float_format="%.12g")
    pd.DataFrame(summary).to_csv(args.output / "mechanism_summary.csv", index=False, float_format="%.12g")


if __name__ == "__main__":
    main()
