"""Analytical and limiting cases for the kernels used by the network."""
import math
import unittest

from auditory import membrane_step, plastic_step, release_step


class MembraneTests(unittest.TestCase):
    def test_analytic_leak_at_multiple_steps(self):
        for dt in (0.25, 0.5, 1.0):
            with self.subTest(dt=dt):
                v = -49.0
                for _ in range(round(10.0 / dt)):
                    v = membrane_step(v, 0.0, 0.0, dt)
                expected = -65.0 + 16.0 * math.exp(-10.0 / 20.0)
                self.assertAlmostEqual(v, expected, places=11)

    def test_excitatory_and_inhibitory_conductances(self):
        for ge, gi in ((0.35, 0.0), (0.0, 0.7), (0.35, 0.7)):
            with self.subTest(ge=ge, gi=gi):
                gain = 1.0 + ge + gi
                steady = (-65.0 - 80.0 * gi) / gain
                expected = steady + (-65.0 - steady) * math.exp(-gain * 5.0 / 20.0)
                self.assertAlmostEqual(membrane_step(-65.0, ge, gi, 5.0), expected, places=12)
        self.assertGreater(membrane_step(-65.0, 0.35, 0.0, 1.0), -65.0)
        self.assertLess(membrane_step(-65.0, 0.0, 0.7, 1.0), -65.0)

    def test_inhibition_shunts_excitation(self):
        self.assertLess(membrane_step(-60.0, 0.5, 0.75, 2.0),
                        membrane_step(-60.0, 0.5, 0.0, 2.0))


class DepressionTests(unittest.TestCase):
    def test_recovery_and_event_mass_balance(self):
        x, U, dt, tau = 0.22, 0.35, 4.0, 180.0
        available = 1.0 - (1.0 - x) * math.exp(-dt / tau)
        for count in (0, 1, 2, 20):
            with self.subTest(count=count):
                after, release = release_step(x, count, U, dt, tau)
                self.assertAlmostEqual(after, available * (1.0 - U) ** count)
                self.assertAlmostEqual(after + release, available)
                self.assertGreaterEqual(after, 0.0)
                self.assertLessEqual(after, 1.0)

    def test_periodic_steady_release(self):
        U, dt, tau = 0.4, 15.0, 200.0
        x = 1.0
        releases = []
        for _ in range(200):
            x, amount = release_step(x, 1, U, dt, tau)
            releases.append(amount)
        q = math.exp(-dt / tau)
        expected = U * (1.0 - q) / (1.0 - (1.0 - U) * q)
        self.assertAlmostEqual(releases[0], U, places=13)
        self.assertGreater(releases[0], releases[1])
        self.assertAlmostEqual(releases[-1], expected, places=12)

    def test_ablation_preserves_isolated_event(self):
        U = 0.45
        self.assertAlmostEqual(release_step(1.0, 1, U, 1.0, 150.0, False)[1],
                               release_step(1.0, 1, U, 1.0, 150.0, True)[1])
        self.assertAlmostEqual(release_step(1.0, 3, U, 1.0, 150.0, False)[1], 3 * U)


class PlasticityTests(unittest.TestCase):
    def test_pre_then_post_and_reverse(self):
        w, ap, am, tau = 0.4, 0.015, 0.021, 20.0
        for lag in (5.0, 20.0, 50.0):
            with self.subTest(lag=lag):
                trace = math.exp(-lag / tau)
                self.assertAlmostEqual(plastic_step(w, trace, 0.0, 0, 1, ap, am),
                                       w + (1.0 - w) * ap * trace)
                self.assertAlmostEqual(plastic_step(w, 0.0, trace, 1, 0, ap, am),
                                       w - w * am * trace)

    def test_tie_and_old_history(self):
        w, ap, am = 0.55, 0.012, 0.016
        self.assertEqual(plastic_step(w, 0.0, 0.0, 1, 1, ap, am), w)
        pre, post = 1.3, 0.6
        self.assertAlmostEqual(plastic_step(w, pre, post, 1, 1, ap, am),
                               w + ap * (1.0 - w) * pre - am * w * post)

    def test_hard_bounds_after_large_trace_jump(self):
        args = (0.5, 0.5)
        self.assertEqual(plastic_step(0.5, 100.0, 0.0, 0, 1, *args), 1.0)
        self.assertEqual(plastic_step(0.5, 0.0, 100.0, 1, 0, *args), 0.0)


if __name__ == "__main__":
    unittest.main()
