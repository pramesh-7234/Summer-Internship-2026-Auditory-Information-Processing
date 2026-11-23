# Held-out tone responses after learning

Each trained circuit was challenged with a single tone after resetting all fast state variables. This tests whether the learned direct thalamus→L4 efficacies change the response to the tone after the adapting stream has ended. The probe captures immediate synaptic memory in the simulation. Persistence over a mouse’s development would require modeling the intervening maturation and comparing responses with subsequent recordings [Mehra et al., Fig. 7](https://doi.org/10.1523/JNEUROSCI.0431-21.2021).

## Design

Train in each developmental regime with exactly 90% standards and 10% deviants, reversing roles of physical tones 0 and 5 on the same network. Test with initial and trained direct efficacy matrices, STDP disabled and STD enabled. Each probe starts at rest with full resources and zero plasticity traces. Background activity begins 100 ms before the 50-ms tone. The baseline-corrected rate is the spike count in the first 100 ms after onset minus the preceding 100-ms count, divided by 0.1 s. Gain is the trained-minus-initial difference for identical held-out afferent events, averaged over 64 fresh draws per physical tone. Both networks receive the same background and probe, with the same wiring and thresholds. Only the supplied initial efficacy matrix changes between these paired tests.

The population estimate averages 40 L4 neurons. The tuned group comprises the four cells receiving the greatest summed direct input strength from that physical tone **at initialization**. This ranking measures anatomical input and does not use the outcome of exposure. The two role assignments enter each network seed with equal weight. Brackets below give two-sided 95% paired Student intervals over independent seeds. The 100-token experiment uses seeds 1001–1008. The 1,000-token experiment uses 1001–1004. The two horizons use the same circuit for shared seeds but generate fresh schedules and background for their respective durations. They are separate exposures. The 64 probe draws measure responses within a circuit and do not add degrees of freedom to the intervals.

## Results at the nominal 0.5-ms step

D and S refer to the test tone’s earlier training role. All gains are in spikes/s per L4 neuron. Column D−S first contrasts within seed, then averages across seeds.

| Training | Regime | Neurons | D gain | S gain | D−S gain [95% interval] |
|---|---|---|---:|---:|---:|
| 100 tokens | Early | All 40 | −0.0037 | +0.0540 | −0.0576 [−0.0811, −0.0341] |
| 100 tokens | Early | Four tuned | −0.0293 | +0.3442 | −0.3735 [−0.4914, −0.2556] |
| 100 tokens | Late | All 40 | −0.0269 | −0.0427 | +0.0159 [−0.0278, +0.0596] |
| 100 tokens | Late | Four tuned | −0.1953 | −0.4858 | +0.2905 [−0.0165, +0.5976] |
| 1,000 tokens | Early | All 40 | −0.0332 | +0.1465 | −0.1797 [−0.2669, −0.0925] |
| 1,000 tokens | Early | Four tuned | −0.2246 | +0.7520 | −0.9766 [−1.2692, −0.6839] |
| 1,000 tokens | Late | All 40 | −0.1777 | −0.0825 | −0.0952 [−0.1984, +0.0079] |
| 1,000 tokens | Late | Four tuned | −1.3037 | −0.9424 | −0.3613 [−0.9748, +0.2522] |

Before 100-token exposure, mean L4 responses to isolated tones were 3.729 Hz early and 2.847 Hz late. At 100 tokens, the early standard gain was +0.0540 Hz [+0.0354, +0.0725], while the early deviant gain was −0.0037 Hz [−0.0151, +0.0078]. All eight early seeds favored the standard in the population probe. The late population mean favored the deviant weakly at 100 tokens and the standard weakly at 1,000 tokens, with intervals spanning zero on both horizons. A relative advantage can arise when responses to both roles decline.

| Training | Regime | Cumulative D−S mean edge change [95% interval] | D−S mean edge change per own-tone interval | Range of final connected efficacies |
|---|---|---:|---:|---:|
| 100 tokens | Early | −0.01483 [−0.01828, −0.01139] | −0.0002564 | 0.43761–0.63550 |
| 100 tokens | Late | +0.00057 [−0.00308, +0.00422] | −0.0002044 | 0.42654–0.56901 |
| 1,000 tokens | Early | −0.04593 [−0.06398, −0.02788] | −0.0001408 | 0.43119–0.67356 |
| 1,000 tokens | Late | −0.00770 [−0.01717, +0.00176] | −0.0001586 | 0.41259–0.59806 |

Weights are dimensionless. Cumulative change averages all extant direct edges from a tone’s four afferents. The interval-specific statistic compares mean changes in those edges during intervals assigned to that same tone, giving its 10 or 90 occurrences at 100 tokens equal status as averages. Background input, residual traces and ongoing spiking can all contribute during an interval. At both horizons, **0%** of final connected efficacies were at a bound or within 0.01 of either bound in every age, seed and role assignment. These finite-duration diagnostics do not establish a long-time equilibrium.

## Paired grid refinement

We reran **both training and readout** for the entire 100-token cohort at 0.125 ms. Wiring, continuous thalamic events, token order, role swaps, anatomical ranking and 64 held-out input draws were shared between grids. Pairing within seed separates a systematic grid shift from heterogeneity across networks.

| D−S outcome | Regime | Fine estimate [95% interval] | Fine minus nominal [95% paired interval] | Mean absolute paired difference |
|---|---|---:|---:|---:|
| Population probe gain (Hz) | Early | −0.06104 [−0.08114, −0.04093] | −0.00342 [−0.01743, +0.01059] | 0.01416 |
| Population probe gain (Hz) | Late | +0.01685 [−0.02409, +0.05778] | +0.00098 [−0.01023, +0.01219] | 0.01123 |
| Tuned probe gain (Hz) | Early | −0.40039 [−0.51878, −0.28200] | −0.02686 [−0.08536, +0.03165] | 0.05615 |
| Tuned probe gain (Hz) | Late | +0.28809 [−0.03031, +0.60648] | −0.00244 [−0.11705, +0.11217] | 0.10986 |
| Mean direct-edge change | Early | −0.01410 [−0.01757, −0.01063] | +0.000729 [+0.000318, +0.001141] | 0.000729 |
| Mean direct-edge change | Late | +0.00130 [−0.00239, +0.00498] | +0.000732 [+0.000405, +0.001059] | 0.000734 |

The early standard-favoring probe contrast persists in all eight seeds at both grids. Refinement shifts the weight contrast toward the deviant by roughly 0.00073 in both stages. This is about 5% of the magnitude of the early estimate and exceeds the small late nominal mean. The late weight ranking remains unresolved. Fine-grid final weights ranged from 0.43296 to 0.63184 early and 0.42577 to 0.56702 late, with zero at or within 0.01 of either bound. The longer 1,000-token exposure was evaluated at the nominal step only.

## Reproduction and tables

Run the following from the project root using the same output directory for both commands.

```sh
python run_probes.py --jobs 4
python run_probes.py --refine --jobs 4
```

The nominal outputs in `results/` are `probe_runs.csv` (one physical tone, seed and exposure assignment), `probe_seeds.csv`, `probe_summary.csv` and `exposure_termini.csv` (all connected direct efficacies). The four `*_fine.csv` companions contain the corresponding 100-token results at 0.125 ms. `probe_refinement.csv` records paired fine-minus-nominal estimates including the mean absolute difference. `probe_runs.csv` also records the fraction of probe trials for which the total L4 count difference changed, which can miss opposing changes in different cells.
