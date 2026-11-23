"""Native event-clock regressions with an isolated, uniquely routed impulse."""
from unittest import TestCase
from unittest.mock import patch

import numpy as np

from auditory import Config, Stimulus, simulate


def fixture(dt, events, duration, relay_to_l4=False, inhibition=False, plastic=False):
    # Afferent 0 -> SP 2 -> I 4. Afferent 1 drives L4 3 directly.
    ts = np.zeros((40, 40))
    tl = np.zeros((40, 40))
    sl = np.zeros((40, 40))
    si = np.zeros((10, 40))
    il = np.zeros((40, 10))
    ts[2, 0] = si[4, 2] = 1500.0
    tl[3, 1] = 3000.0
    if relay_to_l4:
        sl[3, 2] = 1500.0
    if inhibition:
        il[3, 4] = 20000.0
    mask = tl > 0
    weights = mask.astype(float) * 0.5
    wiring = (ts, tl, sl, si, il, weights, np.full(90, -52.0), mask)
    stimulus = Stimulus(np.array([0]), np.array([0.0]),
                        np.array([time for time, _ in events]),
                        np.array([cell for _, cell in events], dtype=np.int32),
                        0, 5, duration)
    with patch("auditory.model._wiring", return_value=wiring):
        return simulate(Config(dt=dt, std=False, stdp=plastic), seed=0, stimulus=stimulus)


class EventClockTests(TestCase):
    def test_afferent_ceiling_at_representable_boundaries(self):
        dt = 0.1
        for k in (3, 9):
            boundary = k * dt
            for time, arrival in ((np.nextafter(boundary, -np.inf), k),
                                  (boundary, k),
                                  (np.nextafter(boundary, np.inf), k+1)):
                with self.subTest(k=k, time=time):
                    result = fixture(dt, [(time, 0)], 2.0)
                    self.assertEqual(result.times[result.cells == 2][0], (arrival+1)*dt)

    def test_excitatory_relays_wait_one_millisecond(self):
        for dt in (1.0, 0.5, 0.25, 0.125):
            with self.subTest(dt=dt):
                run = fixture(dt, [(0.0, 0)], 4.0, relay_to_l4=True)
                self.assertEqual(run.times[run.cells == 2][0], dt)
                for cell in (44, 53):
                    self.assertEqual(run.times[run.cells == cell][0], 2*dt+1.0)

    def test_inhibition_first_acts_on_its_delivery_boundary(self):
        for dt in (1.0, 0.5, 0.25, 0.125):
            delivery = 2*dt+2.0  # SP and I each cross after one active interval.
            for probe in (delivery-dt, delivery):
                with self.subTest(dt=dt, probe=probe):
                    events = [(0.0, 0), (probe, 1)]
                    for inhibited in (False, True):
                        run = fixture(dt, events, probe+dt, inhibition=inhibited)
                        self.assertEqual(run.times[run.cells == 44][0]+1, delivery)
                        expected = [] if inhibited and probe == delivery else [probe+dt]
                        np.testing.assert_array_equal(run.times[run.cells == 53], expected)

    def test_terminal_arrival_uses_prior_traces_without_an_extra_interval(self):
        # The first presynaptic impulse elicits a post spike at 0.5 ms.
        # At the final boundary the second presynaptic event induces LTD.
        cfg = Config()
        run = fixture(0.5, [(0.0, 1), (1.0, 1)], 1.0, plastic=True)
        np.testing.assert_array_equal(run.times[run.cells == 53], [0.5])
        decay = np.exp(-0.5/20)
        after_post = 0.5 + cfg.ltp_amplitude * 0.5 * decay
        expected = after_post - cfg.ltd_amplitude * after_post * decay
        self.assertAlmostEqual(run.final_weights[3, 1], expected, places=14)
