"""Run matched virtual circuits and regenerate the tidy experiment tables.

Launch from the repository root. All simulations are independent; role reversal,
protocol, stage, and single-factor changes are explicitly paired by seed.
"""
from __future__ import annotations

import argparse
import itertools
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t

from auditory import Config, simulate


MAIN = ('intact', 'no_stdp', 'no_std', 'no_plasticity', 'no_sp_l4', 'no_inhibition',
        'no_direct', 'many', 'many_no_std')
FACTORS = {'recovery': 'tau_rec', 'rate': 'input_rate', 'learning': 'learning_scale', 'width': 'width',
           'ltp': 'ltp_amplitude'}
SENSITIVITIES = tuple(f'{factor}_{level}' for factor in ['threshold', *FACTORS] for level in ('lo', 'hi'))
STAGE_FACTORS = ('sp_scale', 'direct_scale', 'tau_rec')
HISTORICAL = ('rate_8hz', 'sp_threshold_raised', 'l4_threshold_raised')
SWITCHES = tuple('late_' + field for field in STAGE_FACTORS)
POPS = {'sp': (0, 40), 'i': (40, 50), 'l4': (50, 90)}
ROLES = ('std', 'dev')
SEEDS = tuple(range(1001, 1009))
WINDOW = 100.0  # milliseconds, applied equally before and after each onset


def configuration(regime, condition):
    cfg = Config.for_regime(regime)
    protocol = 'many' if condition in ('many', 'many_no_std') else 'oddball'
    fixed = {'no_stdp': {'stdp': False}, 'no_std': {'std': False},
             'many_no_std': {'std': False}, 'no_plasticity': {'std': False, 'stdp': False},
             'no_sp_l4': {'sp_scale': 0.0}, 'no_inhibition': {'inhibition_scale': 0.0},
             'no_direct': {'direct_scale': 0.0}, 'rate_8hz': {'input_rate': 8.0},
             'sp_threshold_raised': {'sp_threshold_shift': 2.0},
             'l4_threshold_raised': {'l4_threshold_shift': 2.0}}
    if condition in fixed:
        cfg = replace(cfg, **fixed[condition])
    elif condition in SENSITIVITIES:
        factor, level = condition.rsplit('_', 1)
        if factor == 'threshold':
            cfg = replace(cfg, threshold_shift=cfg.threshold_shift + (-2.0 if level == 'lo' else 2.0))
        else:
            scale = {'learning': (0.5, 1.5), 'ltp': (0.8, 1.2)}.get(factor, (0.75, 1.25))
            field = FACTORS[factor]
            cfg = replace(cfg, **{field: getattr(cfg, field) * scale[level == 'hi']})
    elif condition in SWITCHES:
        field = condition.removeprefix('late_')
        cfg = replace(cfg, **{field: getattr(Config.for_regime('late'), field)})
    elif condition not in ('intact', 'many'):
        raise ValueError(condition)
    return cfg, protocol


def event_table(run):
    """Counts per token from half-open windows [onset-W,onset), [onset,onset+W)."""
    onsets = np.asarray(run.onsets)
    if onsets[0] < WINDOW or onsets[-1] + WINDOW > run.duration:
        raise ValueError('Stimulus windows must lie inside the run')
    data = {'token': np.arange(1, len(onsets) + 1), 'onset_ms': onsets, 'tone': run.tones,
            'role': np.where(run.tones == run.deviant, 'dev', np.where(run.tones == run.standard, 'std', 'other'))}
    for pop, (first, end) in POPS.items():
        times = np.sort(run.times[(run.cells >= first) & (run.cells < end)])
        pos = np.searchsorted(times, onsets)
        data[pop + '_pre'] = pos - np.searchsorted(times, onsets - WINDOW)
        data[pop + '_post'] = np.searchsorted(times, onsets + WINDOW) - pos
    return pd.DataFrame(data)


def synchrony(run, start, stop, spike_mask):
    """Mean pairwise Pearson count correlation in 5 ms bins; discard zero variance cells."""
    use = spike_mask & (run.cells >= 50) & (run.cells < 90)
    n_bins = int(np.ceil((stop - start) / 5.0))
    bin_id = np.floor((run.times[use] - start) / 5.0).astype(int)
    indices = (run.cells[use].astype(int) - 50) * n_bins + bin_id
    counts = np.bincount(indices, minlength=40 * n_bins).reshape(40, n_bins)
    peak = np.max((counts > 0).sum(axis=0)) / 40
    centered = counts - counts.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(centered, axis=1)
    good = norms > 0
    n = int(good.sum())
    if n < 2:
        return np.nan, peak, n / 40
    summed = (centered[good] / norms[good, None]).sum(axis=0)
    mean_r = (np.dot(summed, summed) - n) / (n * (n - 1))
    return mean_r, peak, n / 40


def epoch_metrics(run, trial, name, i_start, i_stop, visible):
    data = {'epoch': name}
    sub = trial.iloc[i_start:i_stop]
    start = 0.0 if i_start == 0 else run.onsets[i_start] - WINDOW
    stop = run.duration if i_stop == len(trial) else run.onsets[i_stop] - WINDOW
    spike_mask = (run.times >= start) & (run.times < stop)
    data['l4_pair_r'], data['l4_peak_bin_fraction'], data['l4_variable_fraction'] = synchrony(run, start, stop, spike_mask)
    for pop, (first, end) in POPS.items():
        scale = 1000.0 / ((end - first) * WINDOW)
        total = np.sum((run.cells >= first) & (run.cells < end) & spike_mask)
        data[f'{pop}_mean_hz'] = total * 1000.0 / ((stop - start) * (end - first))
        for role in ROLES:
            rows = sub[sub.role == role]
            data['n_' + role] = len(rows)
            pre = rows[pop + '_pre'].mean() * scale
            post = rows[pop + '_post'].mean() * scale
            data[f'{pop}_{role}_pre_hz'] = pre
            data[f'{pop}_{role}_post_hz'] = post
            data[f'{pop}_{role}_hz'] = post - pre
        dev = data[f'{pop}_dev_hz']
        std = data[f'{pop}_std_hz']
        data[f'{pop}_dev_minus_std_hz'] = dev - std
        data[f'{pop}_selectivity'] = (dev - std) / (abs(dev) + abs(std)) if abs(dev) + abs(std) > 0 else np.nan
    # Across-phase endpoints are cumulative changes since the start of training.
    for role, group in zip(ROLES, (run.standard, run.deviant)):
        history = run.weight_history[:, group]
        data[f'dweight_{role}'] = history[i_stop] - history[0] if visible else np.nan
    data['dweight_dev_minus_std'] = data['dweight_dev'] - data['dweight_std']
    # Only final matrices are retained by the simulator, so bounds metrics are full-run endpoints.
    if name == 'all' and visible:
        weights = run.final_weights[run.mask]
        if len(weights):
            w = weights / run.max_weight
            data.update(weight_near_upper=np.mean(w >= 0.95), weight_near_lower=np.mean(w <= 0.05),
                        weight_min=weights.min(), weight_max=weights.max(), weight_mean=weights.mean(),
                        weight_sd=weights.std(), weight_q10=np.quantile(weights, 0.1), weight_q90=np.quantile(weights, 0.9))
    # Same physical frequent tone immediately following a deviant vs another standard.
    prev_roles = trial.role.shift().iloc[i_start:i_stop]
    for prior in ROLES:
        rows = sub[(sub.role == 'std') & (prev_roles == prior)]
        data['l4_std_after_' + prior + '_hz'] = (rows.l4_post - rows.l4_pre).mean() / (40 * WINDOW / 1000)
    return data


def trial_job(job):
    condition, regime, seed, swap, tokens = job
    cfg, protocol = configuration(regime, condition)
    run = simulate(cfg, seed=seed, n_tokens=tokens, protocol=protocol, swap=swap)
    trial = event_table(run)
    key = dict(condition=condition, regime=regime, seed=seed, swap=int(swap))
    for k, value in key.items():
        trial[k] = value
    visible = cfg.direct_scale > 0
    metrics = [dict(**key, **epoch_metrics(run, trial, name, start, end, visible))
               for name, start, end in [('all', 0, tokens), ('first_half', 0, tokens // 2),
                                        ('second_half', tokens // 2, tokens)]]
    trajectories = []
    if condition in ('intact', 'no_std', 'no_stdp', 'many'):
        for token in sorted(set(range(0, tokens + 1, 5)) | {tokens}):
            for role, group in zip(ROLES, (run.standard, run.deviant)):
                trajectories.append(dict(**key, token=token, time_ms=run.weight_times[token],
                                         role=role, efficacy=run.weight_history[token, group]))
    return metrics, trial, trajectories


def estimate(values):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    mean = a.mean() if len(a) else np.nan
    half = t.ppf(0.975, len(a) - 1) * a.std(ddof=1) / np.sqrt(len(a)) if len(a) >= 2 else np.nan
    return dict(n=len(a), mean=mean, lo=mean - half, hi=mean + half)


def collect_contrasts(table):
    """Use one independent value per seed, preserving matched designs in differences."""
    output = []
    metrics = ('l4_std_hz', 'l4_dev_hz', 'l4_dev_minus_std_hz', 'l4_selectivity', 'dweight_std',
               'dweight_dev', 'dweight_dev_minus_std', 'sp_dev_minus_std_hz', 'i_dev_minus_std_hz',
               'l4_mean_hz', 'l4_pair_r', 'l4_peak_bin_fraction', 'weight_near_upper', 'weight_near_lower')
    def record(cond, stage, epoch, contrast, metric, values):
        if np.isfinite(values).any():
            output.append(dict(condition=cond, regime=stage, epoch=epoch, contrast=contrast, metric=metric,
                               **estimate(values)))
    indexed = {(c, s, e): g.set_index('seed') for (c,s,e),g in table.groupby(['condition', 'regime', 'epoch'])}
    for (condition, regime, epoch), g in indexed.items():
        for metric in metrics:
            record(condition, regime, epoch, 'level', metric, g[metric])
            ref = indexed['intact', regime, epoch][metric]
            if condition not in ('intact', 'many', 'many_no_std'):
                record(condition, regime, epoch, 'condition_minus_intact', metric, g[metric] - ref)
            if regime == 'late' and (condition, 'early', epoch) in indexed:
                record(condition, 'late-early', epoch, 'late_minus_early', metric,
                       g[metric] - indexed[condition, 'early', epoch][metric])
            if epoch == 'second_half':
                record(condition, regime, 'second-first', 'second_minus_first', metric,
                       g[metric] - indexed[condition, regime, 'first_half'][metric])
        if condition in ('many', 'many_no_std'):
            odd = 'intact' if condition == 'many' else 'no_std'
            for metric in ('l4_dev_hz', 'sp_dev_hz', 'i_dev_hz', 'dweight_dev'):
                record(condition, regime, epoch, 'oddball_minus_many', metric,
                       indexed[odd, regime, epoch][metric] - g[metric])
        if condition == 'intact':
            record(condition, regime, epoch, 'std_after_deviant_minus_std_after_std', 'l4_std_hz',
                   g.l4_std_after_dev_hz - g.l4_std_after_std_hz)
    return pd.DataFrame(output)


def verify_matching(trials):
    """Assert matched schedules, rare identities and positions for all contextual comparisons."""
    cols = ['seed', 'swap', 'token']
    reference = trials.query("condition == 'intact' and regime == 'early'").set_index(cols)
    for (condition, regime), block in trials.groupby(['condition', 'regime']):
        group = block.set_index(cols)
        match = reference.loc[group.index]
        np.testing.assert_array_equal(group.onset_ms, match.onset_ms)
        if condition in ('many','many_no_std'):
            np.testing.assert_array_equal(group.role == 'dev', match.role == 'dev')
            rare = group.role == 'dev'
            np.testing.assert_array_equal(group.loc[rare,'tone'], match.loc[rare,'tone'])
        else:
            np.testing.assert_array_equal(group.tone, match.tone)


def write_csv(table, path):
    table.to_csv(path, index=False, float_format='%.9g')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, default=4, help='Independent worker processes')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'results')
    parser.add_argument('--seeds', type=int, default=8, choices=range(1, 9), help='Main paired seed count, up to 8')
    parser.add_argument('--tokens', type=int, default=100, help='Multiple of 20 for matched probabilities')
    parser.add_argument('--quick', action='store_true', help='Intact + many and a single seed for a pipeline check')
    args = parser.parse_args()
    if args.tokens < 20 or args.tokens % 20 or args.jobs < 1:
        parser.error('--tokens must be a positive multiple of 20; --jobs must be positive')
    seeds = SEEDS[:1 if args.quick else args.seeds]
    conditions = ('intact', 'many') if args.quick else (*MAIN, *SENSITIVITIES, *SWITCHES, *HISTORICAL)
    jobs, params = [], []
    for condition in conditions:
        stages = ('early', 'late')
        if condition in (*SWITCHES, 'sp_threshold_raised'):
            stages = ('early',)
        elif condition == 'l4_threshold_raised':
            stages = ('late',)
        subset = seeds if condition in MAIN else seeds[:4]
        for regime in stages:
            cfg, protocol = configuration(regime, condition)
            params.append(dict(condition=condition, stage=regime, protocol=protocol, **asdict(cfg)))
            jobs.extend((condition, regime, seed, swap, args.tokens) for seed, swap in itertools.product(subset, (False, True)))
    print(f'Running {len(jobs)} paired network runs across {len(seeds)} independent seeds', flush=True)
    if args.jobs == 1:
        results = list(map(trial_job, jobs))
    else:
        with ProcessPoolExecutor(args.jobs) as executor:
            results = list(executor.map(trial_job, jobs, chunksize=2))
    metrics = pd.DataFrame([m for job in results for m in job[0]])
    trials = pd.concat([job[1] for job in results], ignore_index=True)
    verify_matching(trials)
    trajectories = pd.DataFrame([v for job in results for v in job[2]])
    grouped = metrics.drop(columns='swap').groupby(['condition','regime','seed','epoch'])
    if not grouped.size().eq(2).all():
        raise ValueError('Each seed must have exactly two role assignments')
    # Require both assignments to contribute to a seed-level estimate, even
    # for conditional or correlation measures that can be undefined.
    aggregate = grouped.mean(numeric_only=True).where(grouped.count().eq(2)).reset_index()
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, table in [('parameters', pd.DataFrame(params)), ('run_metrics', metrics), ('seed_metrics',aggregate),
                            ('contrasts',collect_contrasts(aggregate)), ('weight_trajectories',trajectories)]:
        write_csv(table, args.output / (filename + '.csv'))
    trials.to_csv(args.output / 'token_counts.csv.gz', index=False, compression={'method':'gzip','mtime':0})
    print(f'Wrote {len(trials):,} token records and {len(aggregate):,} seed/epoch summaries to {args.output}', flush=True)


if __name__ == '__main__':
    main()
