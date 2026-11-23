"""Independent single-tone readout of the circuit before and after oddball exposure."""
from __future__ import annotations

import argparse
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from auditory import Config, make_stimulus, simulate

ROOT = Path(__file__).resolve().parent
POPULATION = 40
WINDOW_MS = 100


def evoked_cell_rates(run):
    """L4 mean response above the immediately preceding, equal-length baseline."""
    onset = run.onsets[0]
    keep = (run.cells >= 50) & (run.cells < 90)
    times, cells = run.times[keep], run.cells[keep].astype(int) - 50
    evoked = np.bincount(cells[(times >= onset) & (times < onset + WINDOW_MS)], minlength=POPULATION)
    baseline = np.bincount(cells[(times >= onset - WINDOW_MS) & (times < onset)], minlength=POPULATION)
    return (evoked - baseline) * (1000.0 / WINDOW_MS)


def exposure_and_probe(args):
    age, seed, n_tokens, replicates, dt = args
    cfg = replace(Config.for_regime(age), dt=dt)
    frozen = replace(cfg, stdp=False)
    records, termini = [], []
    # Separate stimulus seed namespace; both role orders and both learned
    # states receive the exact same test events for each physical tone.
    tests = {}
    for tone in (0, 5):
        tests[tone] = [make_stimulus(frozen, seed=300_000 + seed * 1000 + rep,
                                    n_tokens=1, protocol="probe", swap=tone == 5)
                       for rep in range(replicates)]
    before = {}
    for swap in (False, True):
        train = simulate(cfg, seed=seed, n_tokens=n_tokens, protocol="oddball", swap=swap)
        w0, w1 = train.initial_weights, train.final_weights
        mask = train.mask.astype(bool)
        end = w1[mask]
        termini.append(dict(age=age, seed=seed, n_tokens=n_tokens, swap=swap,
                            start_mean=float(w0[mask].mean()), end_mean=float(end.mean()),
                            end_min=float(end.min()), end_max=float(end.max()),
                            at_limit=float(np.mean((end <= 1e-12) | (end >= 1-1e-12))),
                            within_one_pct=float(np.mean((end <= .01) | (end >= .99)))))
        for tone, role in ((train.standard, "standard"), (train.deviant, "deviant")):
            probe_set = tests[tone]
            if tone not in before:
                before[tone] = [evoked_cell_rates(simulate(frozen, seed=seed, stimulus=s, initial_weights=w0))
                                for s in probe_set]
            after = [evoked_cell_rates(simulate(frozen, seed=seed, stimulus=s, initial_weights=w1))
                     for s in probe_set]
            paired_change = np.asarray(after) - before[tone]
            # Structural zeros are excluded. Each tone has four afferents.
            cols = slice(4 * tone, 4 * tone + 4)
            dw = (w1 - w0)[:, cols][mask[:, cols]]
            # The four strongest anatomical recipients are determined before learning.
            strength = (train.direct_base[:, cols] * w0[:, cols]).sum(axis=1)
            tuned = np.argsort(-strength, kind="stable")[:4]
            # Changes during the intervals ending with the same physical tone.
            token_delta = np.diff(train.weight_history[:, tone])
            on_tone = train.tones == tone
            np.testing.assert_allclose(token_delta.sum(), dw.mean(), atol=2.e-10)
            records.append(dict(age=age, seed=seed, n_tokens=n_tokens, swap=swap, tone=tone,
                                training_role=role, probe_trials=replicates,
                                response_before_hz=np.mean(before[tone]), response_after_hz=np.mean(after),
                                gain_hz=paired_change.mean(),
                                tuned_gain_hz=paired_change[:, tuned].mean(),
                                fraction_trials_changed=np.mean(paired_change.sum(axis=1) != 0),
                                mean_delta_per_own_token=token_delta[on_tone].mean(),
                                mean_delta_per_other_token=token_delta[~on_tone].mean(),
                                mean_edge_change=dw.mean()))
    return records, termini


def summarise(df):
    # Same physical tone is tested in both training roles. First average the
    # two role orders; each interval therefore has one observation per seed.
    avg = df.groupby(["age", "n_tokens", "seed", "training_role"]).mean(numeric_only=True)
    seed_metrics = avg[["gain_hz", "tuned_gain_hz", "mean_edge_change", "mean_delta_per_own_token"]].unstack("training_role")
    seed_metrics.columns = ["_".join(c) for c in seed_metrics.columns]
    for col in ("gain_hz", "tuned_gain_hz", "mean_edge_change", "mean_delta_per_own_token"):
        seed_metrics[col + "_D_minus_S"] = seed_metrics[col + "_deviant"] - seed_metrics[col + "_standard"]
    seed_metrics = seed_metrics.reset_index()
    rows = []
    for (age, n), group in seed_metrics.groupby(["age", "n_tokens"]):
        for col in seed_metrics.columns[3:]:
            v = group[col].to_numpy()
            half = student_t.ppf(.975, len(v) - 1) * v.std(ddof=1) / np.sqrt(len(v))
            rows.append(dict(age=age, n_tokens=n, metric=col, n_seeds=len(v), mean=v.mean(),
                             ci_low=v.mean()-half, ci_high=v.mean()+half))
    return seed_metrics, pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    parser.add_argument("--refine", action="store_true",
                        help="Repeat 100-token training and probes at 0.125 ms and pair against nominal results.")
    opts = parser.parse_args()
    dt = 0.125 if opts.refine else Config().dt
    cohorts = ((100, 8),) if opts.refine else ((100, 8), (1000, 4))
    if opts.refine and not (opts.output / "probe_seeds.csv").exists():
        parser.error("Run the nominal probes first in the same output directory.")
    tasks = [(age, seed, n, 64, dt) for n, num_seeds in cohorts
             for seed in range(1001, 1001 + num_seeds) for age in ("early", "late")]
    opts.output.mkdir(parents=True, exist_ok=True)
    records, termini = [], []
    with ProcessPoolExecutor(max_workers=opts.jobs) as pool:
        for rows, ends in pool.map(exposure_and_probe, tasks):
            records.extend(rows)
            termini.extend(ends)
    df = pd.DataFrame(records)
    seeds, summary = summarise(df)
    for name, frame in (("probe_runs", df), ("probe_seeds", seeds), ("probe_summary", summary),
                        ("exposure_termini", pd.DataFrame(termini))):
        suffix = "_fine" if opts.refine else ""
        frame.to_csv(opts.output / (name + suffix + ".csv"), index=False, float_format="%.12g")
    if opts.refine:
        nominal = pd.read_csv(opts.output / "probe_seeds.csv").query("n_tokens == 100")
        paired = []
        for age, fine in seeds.groupby("age"):
            fine = fine.set_index("seed").sort_index()
            base = nominal[nominal.age == age].set_index("seed").sort_index()
            if not fine.index.equals(base.index):
                raise ValueError("refinement needs the same training seeds in both grids")
            for metric in ("gain_hz_D_minus_S", "tuned_gain_hz_D_minus_S", "mean_edge_change_D_minus_S"):
                diff = fine[metric] - base[metric]
                half = student_t.ppf(.975, len(diff) - 1) * diff.sem()
                paired.append(dict(age=age, metric=metric, n_seeds=len(diff), nominal=base[metric].mean(),
                                   fine=fine[metric].mean(), fine_minus_nominal=diff.mean(),
                                   ci_low=diff.mean()-half, ci_high=diff.mean()+half,
                                   mean_absolute_difference=diff.abs().mean()))
        pd.DataFrame(paired).to_csv(opts.output / "probe_refinement.csv", index=False, float_format="%.12g")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
