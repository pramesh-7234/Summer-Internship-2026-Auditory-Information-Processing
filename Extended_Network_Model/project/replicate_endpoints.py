"""Disjoint-seed replication chosen after the small initial experiment.

Keep the first experiment's parameters, windows and estimands fixed. Save
one row per seed, stage, and condition, and select the explicitly named contrasts.
"""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import argparse
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from auditory import make_stimulus, simulate
from run_experiments import configuration, event_table, estimate, write_csv


CONDITIONS = ('intact', 'many', 'no_std', 'many_no_std', 'no_stdp')


def run_pair(job):
    condition, regime, seed, dt = job
    cfg, protocol = configuration(regime, condition)
    cfg = replace(cfg, dt=dt)
    records = []
    for swap in (False, True):
        stimulus = make_stimulus(cfg, seed, 100, protocol, swap)
        network = simulate(cfg, seed=seed, stimulus=stimulus)
        table = event_table(network)
        table['net_l4_hz'] = (table.l4_post - table.l4_pre) / 4.0
        # Realized spikes on the four matching fibers during the 50 ms burst,
        # including rare background arrivals. Conditioned exposure uses this
        # physical count and has units of input spikes per presentation.
        counts = np.empty(len(table), dtype=int)
        for j, (tone, onset) in enumerate(zip(stimulus.tones, stimulus.onsets)):
            a,b = np.searchsorted(stimulus.input_times, (onset, onset + 50.0))
            counts[j] = np.sum(stimulus.input_cells[a:b] // 4 == tone)
        table['input_count'] = counts
        stats = table.groupby('role')[['net_l4_hz', 'input_count']].mean()
        weight_change = network.weight_history[-1] - network.weight_history[0]
        records.append(dict(response_std=stats.loc['std', 'net_l4_hz'], response_dev=stats.loc['dev', 'net_l4_hz'],
                            efficacy_std=weight_change[stimulus.standard], efficacy_dev=weight_change[stimulus.deviant],
                            input_std=stats.loc['std', 'input_count'], input_dev=stats.loc['dev', 'input_count']))
    means = pd.DataFrame(records).mean().to_dict()
    return dict(condition=condition, regime=regime, seed=seed, **means)


def summaries(table):
    output = []
    indexed = {(c, r): group.set_index('seed') for (c, r), group in table.groupby(['condition', 'regime'])}
    def add(condition, stage, name, values):
        output.append(dict(condition=condition, regime=stage, metric=name, **estimate(values)))
    for (cond, stage), group in indexed.items():
        for name in ('response', 'efficacy', 'input'):
            diff = group[name + '_dev'] - group[name + '_std']
            add(cond,stage,name + '_dev_minus_std',diff)
            if stage == 'late':
                early = indexed[cond, 'early']
                age_diff = diff - (early[name + '_dev'] - early[name + '_std'])
                add(cond,'late-early',name + '_dev_minus_std',age_diff)
        if cond in ('many', 'many_no_std'):
            ref = indexed['intact' if cond == 'many' else 'no_std', stage]
            add(cond,stage,'response_target_oddball_minus_many',ref.response_dev - group.response_dev)
    return pd.DataFrame(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--fine', action='store_true', help='Repeat intact endpoints at 0.125 ms')
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'results')
    args = parser.parse_args()
    conditions = ('intact',) if args.fine else CONDITIONS
    dt = 0.125 if args.fine else 0.5
    jobs = product(conditions, ('early','late'), range(2001, 2033), (dt,))
    with ProcessPoolExecutor(args.jobs) as executor:
        table = pd.DataFrame(executor.map(run_pair,jobs,chunksize=2))
    args.output.mkdir(exist_ok=True, parents=True)
    suffix = '_fine' if args.fine else ''
    write_csv(table, args.output / f'replication_seeds{suffix}.csv')
    write_csv(summaries(table), args.output / f'replication_intervals{suffix}.csv')
    print(f'{len(table) * 2} runs across {table.seed.nunique()} new seeds')


if __name__ == '__main__':
    main()
