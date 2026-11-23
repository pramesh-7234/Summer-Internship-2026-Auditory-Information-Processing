"""Regression tests via the simulation entry point, with fixed small protocols."""
from dataclasses import replace
import unittest

import numpy as np

from auditory import Config, make_stimulus, simulate
from run_validation import isolated_cell_grid


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.cfg = Config.for_regime("early")

    def test_silent_fixed_point(self):
        result = simulate(self.cfg, seed=3, n_tokens=10, protocol="silent")
        self.assertEqual(len(result.times), 0)
        np.testing.assert_array_equal(result.initial_weights, result.final_weights)

    def test_frozen_weights_despite_evoked_activity(self):
        result = simulate(replace(self.cfg, stdp=False), seed=3, n_tokens=20)
        self.assertGreater(np.count_nonzero(result.cells >= 50), 0)
        np.testing.assert_array_equal(result.initial_weights, result.final_weights)
        mask = np.asarray(result.mask, dtype=bool)
        np.testing.assert_array_equal(result.final_weights[~mask], 0.0)
        self.assertTrue(mask.any())
        self.assertTrue((~mask).any())

    def test_seed_replay_refractory_bounds_and_sparsity(self):
        one = simulate(self.cfg, seed=29, n_tokens=20)
        two = simulate(self.cfg, seed=29, n_tokens=20)
        for name in ("times", "cells", "tones", "initial_weights", "final_weights"):
            np.testing.assert_array_equal(getattr(one, name), getattr(two, name))
        self.assertGreater(len(one.times), 0)
        self.assertTrue(np.all(np.isfinite(one.times)))
        self.assertTrue(np.all(np.isfinite(one.final_weights)))
        self.assertTrue(((one.cells >= 0) & (one.cells < 90)).all())
        self.assertTrue(((one.times >= 0.0) & (one.times <= one.duration)).all())
        self.assertTrue(((one.final_weights >= 0.0) & (one.final_weights <= one.max_weight)).all())
        mask = np.asarray(one.mask, dtype=bool)
        np.testing.assert_array_equal(one.final_weights[~mask], 0.0)
        spikes_with_intervals = []
        for i in np.unique(one.cells):
            spikes_with_intervals.extend(np.diff(np.sort(one.times[one.cells == i])))
        self.assertGreater(len(spikes_with_intervals), 0)
        self.assertGreaterEqual(min(spikes_with_intervals), 2.0 - 1e-9)

    def test_threshold_reset_and_refractory_against_independent_solver(self):
        # A physical TC impulse drives an otherwise independent SP cell with a
        # known exponential conductance. The reference locates continuous roots.
        rows = isolated_cell_grid(8, [1.0 / 128.0])
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(row["computed_spikes"], row["reference_spikes"])
            self.assertLess(abs(row["error_ms"]), 0.15)

    def test_learned_weights_match_independent_all_pairs_reconstruction(self):
        # Enumerate every strict-inequality pair from timestamped event lists.
        # This deliberately avoids recursion, native trace updates, and the
        # production plastic_step function.
        seed, cfg = 29, replace(self.cfg, ltp_amplitude=0.003, ltd_amplitude=0.005, learning_scale=1.2)
        stimulus = make_stimulus(cfg, seed, 20)
        result = simulate(cfg, seed=seed, stimulus=stimulus)
        pre_all = np.ceil(stimulus.input_times / cfg.dt) * cfg.dt
        matrix = result.initial_weights.copy()
        for j, i in zip(*np.nonzero(result.mask)):
            pre = pre_all[stimulus.input_cells == i]
            post = result.times[result.cells == j + 50]
            if not len(pre) or not len(post):
                continue
            weight = matrix[j, i]
            for instant in np.union1d(pre, post):
                prev_pre = pre[pre < instant]
                prev_post = post[post < instant]
                p = np.exp((prev_pre - instant) / 20.0).sum()
                q = np.exp((prev_post - instant) / 20.0).sum()
                ltp = cfg.learning_scale * cfg.ltp_amplitude * (1.0 - weight) * p * np.count_nonzero(post == instant)
                ltd = cfg.learning_scale * cfg.ltd_amplitude * weight * q * np.count_nonzero(pre == instant)
                weight = np.clip(weight + ltp - ltd, 0.0, 1.0)
            matrix[j, i] = weight
        self.assertGreater(np.max(np.abs(matrix - result.initial_weights)), 1e-4)
        np.testing.assert_allclose(matrix, result.final_weights, rtol=0, atol=2e-13)

    def test_matched_rare_positions_and_afferent_events(self):
        cfg = self.cfg
        for swap in (False, True):
            odd = make_stimulus(cfg, 5, 50, "oddball", swap)
            many = make_stimulus(cfg, 5, 50, "many", swap)
            target = odd.tones == odd.deviant
            self.assertEqual(np.count_nonzero(target), 5)
            np.testing.assert_array_equal(np.flatnonzero(target), np.flatnonzero(many.tones == many.deviant))
            np.testing.assert_array_equal(np.bincount(many.tones), np.full(10, 5))
            np.testing.assert_array_equal(odd.input_times, many.input_times)
            for onset in odd.onsets[target]:
                use = (odd.input_times >= onset) & (odd.input_times < onset + 50.0)
                np.testing.assert_array_equal(odd.input_cells[use], many.input_cells[use])

    def test_time_grid_and_regime_share_continuous_drive(self):
        def drive(cfg, seed):
            return make_stimulus(cfg, seed, 20, "oddball", False)
        one = drive(self.cfg, 3)
        two = drive(replace(self.cfg, dt=0.25), 3)
        three = drive(Config.for_regime("late"), 3)
        for other in (two, three):
            for name in ("input_times", "input_cells", "tones", "onsets"):
                np.testing.assert_array_equal(getattr(one, name), getattr(other, name))
        self.assertFalse(np.array_equal(one.input_times, drive(self.cfg, 4).input_times))


if __name__ == "__main__":
    unittest.main()
