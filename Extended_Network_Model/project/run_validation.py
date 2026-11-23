"""Paired time-grid refinement, startup perturbations, and spike-time diagnostics.

Run from the project root: python run_validation.py
Durations are in ms. Outputs are seed-level tables and matched differences.
"""
import argparse
import csv
from dataclasses import replace
from pathlib import Path
from statistics import mean

import numpy as np
from scipy.integrate import solve_ivp
from scipy.stats import t

from auditory import Config, Stimulus, simulate
from auditory.model import _wiring

SEEDS = (107, 211, 307, 401, 503, 601)
DT_VALUES = (1.0, 0.5, 0.25, 0.125)
POPULATIONS = {"sp": (0, 40), "i": (40, 50), "l4": (50, 90)}
WINDOW = 100


def table(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def trial_counts(times, onsets, pre):
    lo = onsets - WINDOW if pre else onsets
    return np.searchsorted(times, lo + WINDOW) - np.searchsorted(times, lo)


def measure(res):
    summary = {}
    for label, (lo, hi) in POPULATIONS.items():
        keep = (res.cells >= lo) & (res.cells < hi)
        spikes = np.sort(res.times[keep])
        summary[label + "_hz"] = len(spikes) * 1000.0 / ((hi - lo) * res.duration)
    cells = res.cells >= 50
    spikes = np.sort(res.times[cells])
    onsets = np.asarray(res.onsets)
    counts = trial_counts(spikes, onsets, False) - trial_counts(spikes, onsets, True)
    hz = counts * (1000.0 / WINDOW / 40)
    for role, tone in (("standard", res.standard), ("deviant", res.deviant)):
        selected = hz[res.tones == tone]
        summary[role + "_net_hz"] = selected.mean()
    summary["contrast_hz"] = summary["deviant_net_hz"] - summary["standard_net_hz"]
    summary["first10_hz"] = hz[:10].mean()
    summary["last10_hz"] = hz[-10:].mean()
    mask = np.asarray(res.mask, dtype=bool)
    w0, w1 = res.initial_weights[mask], res.final_weights[mask]
    summary["mean_weight_change"] = (w1 - w0).mean()
    summary["final_weight_mean"] = w1.mean()
    summary["final_weight_min"] = w1.min()
    summary["final_weight_max"] = w1.max()
    summary["weight_at_limit_fraction"] = np.mean((w1 <= 1e-10) | (w1 >= res.max_weight - 1e-10))
    summary["weight_near_limit_fraction"] = np.mean((w1 <= 0.01) | (w1 >= res.max_weight - 0.01))
    return summary


def spike_windows(res):
    # Occupancy at fixed 1-ms resolution, independent of integration grid.
    cube = np.zeros((len(res.tones), WINDOW, 40), dtype=bool)
    take = res.cells >= 50
    times, cells = res.times[take], res.cells[take] - 50
    trial = np.searchsorted(res.onsets, times, side="right") - 1
    phase = times - res.onsets[np.clip(trial, 0, None)]
    use = (trial >= 0) & (phase >= 0) & (phase < WINDOW)
    cube[trial[use], phase[use].astype(int), cells[use]] = True
    return cube


def mean_coactive_peers(cube):
    n = cube.sum(axis=2)
    return np.sum(n * (n - 1)) / n.sum() if n.sum() else 0.0


def synchrony(res, seed):
    cube = spike_windows(res)
    population = cube.sum(axis=2)
    observed = mean_coactive_peers(cube)
    # Match identity, presentation phase, and coarse experimental epoch across trials.
    groups = []
    half = np.arange(len(cube)) >= len(cube) // 2
    for tone in np.unique(res.tones):
        for late in (False, True):
            idx = np.flatnonzero((res.tones == tone) & (half == late))
            if len(idx):
                groups.append(idx)
    rng = np.random.default_rng(seed + 8123)
    null = []
    shuffled = np.empty_like(cube)
    for _ in range(32):
        for idx in groups:
            for neuron in range(cube.shape[2]):
                shuffled[idx, :, neuron] = cube[rng.permutation(idx), :, neuron]
        null.append(mean_coactive_peers(shuffled))
    active = cube.any(axis=(0, 1))
    rasters = np.moveaxis(cube, 2, 0).reshape(40, -1)
    unique = np.unique(rasters[active], axis=0)
    return {
        "active_l4": int(active.sum()),
        "unique_active_rasters": len(unique),
        "max_bin_fraction_l4": population.max() / 40.0,
        "observed_peers": observed,
        "shuffled_peers_mean": np.mean(null),
        "shuffled_peers_sd": np.std(null, ddof=1),
        "excess_peers": observed - np.mean(null),
    }


def paired_refinement(rows):
    groups = {}
    for row in rows:
        key = row["regime"], row["rate_factor"], row["seed"]
        groups.setdefault(key, {})[row["dt_ms"]] = row
    metrics = ("sp_hz", "i_hz", "l4_hz", "contrast_hz", "mean_weight_change")
    rows_out = []
    for regime in ("early", "late"):
        for rate in (1.0, 1.25):
            replicates = [g for (r, f, _), g in groups.items() if (r, f) == (regime, rate)]
            for dt in DT_VALUES[:-1]:
                # Smallest tested step is a reference estimate, not ground truth.
                for metric in metrics:
                    diffs = np.array([g[dt][metric] - g[DT_VALUES[-1]][metric] for g in replicates])
                    mu = diffs.mean()
                    u = t.ppf(0.975, len(diffs) - 1) * diffs.std(ddof=1) / np.sqrt(len(diffs))
                    rows_out.append(dict(regime=regime, rate_factor=rate, dt_ms=dt,
                                         reference_dt_ms=DT_VALUES[-1], metric=metric,
                                         n_seed=len(diffs), reference_mean=mean(
                                             g[DT_VALUES[-1]][metric] for g in replicates),
                                         mean_difference=mu, ci95_low=mu-u, ci95_high=mu+u,
                                         mean_abs_difference=np.abs(diffs).mean(),
                                         max_abs_difference=np.abs(diffs).max()))
    return rows_out


def isolated_cell_grid(n_impulse, grids):
    """Isolate an SP neuron via the feedforward topology, keeping the native kernel."""
    cfg = replace(Config.for_regime("early"), std=False, stdp=False)
    seed = 3
    ts, _, _, _, _, _, threshold, _ = _wiring(cfg, seed)
    cell = int(np.argmax(ts[:, 0]))
    ge0 = ts[cell, 0] * n_impulse
    duration = 40.0
    stimulus = Stimulus(np.array([0]), np.array([0.0]), np.zeros(n_impulse),
                        np.zeros(n_impulse, dtype=np.int32), 0, 5, duration)

    def voltage_rhs(time, v):
        ge = ge0 * np.exp(-time / 5.0)
        return (-65.0 - v - ge * v) / 20.0

    def crossing(time, v):
        return v[0] - threshold[cell]
    crossing.terminal = True
    crossing.direction = 1
    start = 0.0
    exact = []
    while start < duration:
        solution = solve_ivp(voltage_rhs, (start, duration), [-65.0], events=crossing,
                             method="DOP853", max_step=0.2, rtol=1e-11, atol=1e-12)
        if not len(solution.t_events[0]):
            break
        exact.append(solution.t_events[0][0])
        start = exact[-1] + 2.0
    rows = []
    for dt in grids:
        result = simulate(replace(cfg, dt=dt), seed=seed, stimulus=stimulus)
        times = result.times[result.cells == cell]
        for i in range(max(len(exact), len(times))):
            ref = exact[i] if i < len(exact) else float("nan")
            computed = times[i] if i < len(times) else float("nan")
            rows.append(dict(n_impulse=n_impulse, sp_cell=cell, dt_ms=dt, spike_ordinal=i+1,
                             reference_spikes=len(exact), computed_spikes=len(times),
                             reference_ms=ref, computed_ms=computed, error_ms=computed-ref))
    return rows


def write_isolated(output):
    grids = (1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625, 0.0078125)
    rows = [row for n in (5, 8) for row in isolated_cell_grid(n, grids)]
    table(output / "validation_isolated.csv", rows)


def primary_refinement(output):
    """Repeat role-reversed primary protocol at two step sizes, including controls."""
    from run_experiments import SEEDS as primary_seeds, configuration, estimate, event_table

    records = []
    intervals = []
    pairs = {}
    conditions = ("intact", "many", "no_std", "many_no_std")
    for dt in (0.5, 0.125):
        for regime in ("early", "late"):
            for seed in primary_seeds:
                data = {}
                for condition in conditions:
                    cfg, protocol = configuration(regime, condition)
                    role_swaps = []
                    for swap in (False, True):
                        res = simulate(replace(cfg, dt=dt), seed=seed, n_tokens=100,
                                       protocol=protocol, swap=swap)
                        trial = event_table(res)
                        role = trial.groupby("role")[["l4_post", "l4_pre", "sp_post", "sp_pre"]].mean()
                        l4 = (role.l4_post - role.l4_pre) / 4.0
                        sp = (role.sp_post - role.sp_pre) / 4.0
                        dw = res.weight_history[-1] - res.weight_history[0]
                        role_swaps.append([l4.dev, l4["std"], sp.dev-sp["std"],
                                           dw[res.deviant] - dw[res.standard]])
                    data[condition] = np.mean(role_swaps, axis=0)
                intact, many, no_std, many_no_std = [data[k] for k in conditions]
                outcomes = {"intact_D_minus_S_hz": intact[0]-intact[1],
                            "target_oddball_minus_many_hz": intact[0]-many[0],
                            "no_std_D_minus_S_hz": no_std[0]-no_std[1],
                            "no_std_target_oddball_minus_many_hz": no_std[0]-many_no_std[0],
                            "intact_D_minus_S_weight_change": intact[3],
                            "SP_minus_L4_role_contrast_hz": intact[2]-(intact[0]-intact[1])}
                for key, value in outcomes.items():
                    records.append(dict(dt_ms=dt, regime=regime, seed=seed, outcome=key, value=value))
                    pairs[dt, regime, seed, key] = value
    for key in outcomes:
        for regime in ("early", "late", "late_minus_early"):
            values = {}
            for dt in (0.5, 0.125):
                if regime == "late_minus_early":
                    vals = [pairs[dt,"late",seed,key]-pairs[dt,"early",seed,key] for seed in primary_seeds]
                else:
                    vals = [pairs[dt,regime,seed,key] for seed in primary_seeds]
                values[dt] = np.asarray(vals)
                intervals.append(dict(comparison=f"dt_{dt:g}", regime=regime,
                                      outcome=key, **estimate(vals)))
            change = values[0.5] - values[0.125]
            intervals.append(dict(comparison="coarse_minus_fine", regime=regime,
                                  outcome=key, **estimate(change)))
    table(output / "validation_primary_seeds.csv", records)
    table(output / "validation_primary.csv", intervals)


def run(output, tokens):
    output.mkdir(parents=True, exist_ok=True)
    write_isolated(output)
    curves, diagnostics = [], []
    for regime in ("early", "late"):
        cfg = Config.for_regime(regime)
        for seed in SEEDS:
            for rate in (1.0, 1.25):
                for dt in DT_VALUES:
                    mods = replace(cfg, dt=dt, input_rate=cfg.input_rate * rate)
                    res = simulate(mods, seed=seed, n_tokens=tokens)
                    stats = measure(res)
                    curves.append(dict(regime=regime, seed=seed, rate_factor=rate, dt_ms=dt, **stats))
                    if rate == 1 and dt == cfg.dt:
                        diagnostics.append(dict(regime=regime, seed=seed, case="reference",
                                                **stats, **synchrony(res, seed)))
            for name, kwargs in (
                ("fixed_weights", {"stdp": False}),
                ("no_inhibition", {"inhibition_scale": 0.0}),
                ("initial_resource_0p5", {"initial_resource": 0.5}),
                ("initial_voltage_minus58", {"initial_voltage": -58.0}),
            ):
                res = simulate(replace(cfg, **kwargs), seed=seed, n_tokens=tokens)
                diagnostics.append(dict(regime=regime, seed=seed, case=name,
                                        **measure(res), **synchrony(res, seed)))
        print(f"Completed {regime} validation", flush=True)
    table(output / "validation_grids.csv", curves)
    table(output / "validation_refinement.csv", paired_refinement(curves))
    table(output / "validation_diagnostics.csv", diagnostics)
    primary_refinement(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=int, default=60)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "results")
    args = parser.parse_args()
    run(args.output, args.tokens)
