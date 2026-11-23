# Numerical validation

Run `python -m unittest discover -s tests -v` from the project root for analytical and deterministic regression tests. Run `python run_validation.py` to rebuild the empirical validation CSVs. The latter uses six new paired seeds (107, 211, 307, 401, 503, 601), 60 tone presentations per run, both developmental parameter sets, and no identity reversal. These runs diagnose the integrator and model state. The counterbalanced hypothesis tests are recorded separately in the experiment log.

## What the tests measure

- **Membrane.** For constant normalized conductances, with $g=1+g_E+g_I$ and $V_\infty=(E_L+g_E E_E+g_I E_I)/g$, an isolated subthreshold cell follows $V(t)=V_\infty+[V(0)-V_\infty]\exp(-gt/\tau_m)$. The tests evaluate the actual scalar integrator against this solution, including a multi-step passive decay. Excitation raises the potential from rest, inhibition lowers it, and concurrent inhibition reduces an EPSP. The recorded network spike times supply a separate minimum-interspike-interval check.
- **Depression.** If $x^-$ is available just before $n$ same-bin events, the expected post-event resource is $x^+(n)=x^-(1-U)^n$. The difference is the released fraction. The tests verify both terms and the event balance, including recovery with no release, repeated events and coincident spikes. For periodic input of period $T$, writing $q=\exp(-T/\tau_{rec})$ gives the steady isolated-event release $U(1-q)/[1-(1-U)q]$. Disabling depression keeps the first impulse size $U$ and releases $nU$ for $n$ coincident spikes. In this control vesicle availability is held constant.
- **Pairing.** For an isolated causal pair at lag $s>0$, the expected LTP is $A_+(1-w)\exp(-s/\tau_+)$. Reversed order gives LTD $-A_-w\exp(-s/\tau_-)$. The tests supply the analytical trace at three lags, check old-history terms for coincident spikes, and challenge both hard bounds with large traces. The corresponding network tests check seed replay, sparse absent connections, and effective weight limits at the public simulation entry point.
- **Fixed points and controls.** Silent afferents should leave the circuit at rest and the weights unchanged. Tone drive with STDP disabled should elicit L4 spikes with zero change in weights. A separate perturbation removes inhibition and measures changes in L4 activity. Fixed weights means STDP is off and depression is on.
- **Matched input.** Independent seeds change the realized presynaptic drive. Within a seed, changing regime or step size preserves the continuous timestamps, afferent IDs, token identities and onsets exactly. Threshold crossing, delays, collision within bins and discretized conductance transients can still change spike times. Agreement of individual spike rasters across step sizes is not required.

## Grid study and synchronization diagnostics

The integration steps are 1, 0.5, 0.25 and 0.125 ms. The smallest step supplies a common finite reference. For each age and for each of two input rates (nominal and 25% higher), the seed-specific differences compare identical draws within that rate. A two-sided 95% Student interval across the six paired differences describes simulation-seed uncertainty. Absolute differences across seeds supplement the signed mean, which can conceal cancellation. There are no multiplicity-adjusted significance tests in this diagnostic. The analysis examines population rates, net deviant-minus-standard L4 response and active direct-synapse weight drift. Rates for each role subtract its own 100-ms pre-onset count from its 100-ms post-onset count, then divide by the population, duration and number of presentations of that role.

Fine synchrony uses 1-ms bins over the first 100 ms of each presentation. In bin $b$, let $n_b$ be the number of active L4 cells. The spike-weighted number of coactive peers is $\sum_b n_b(n_b-1)/\sum_b n_b$. Each of 32 reference rasters independently permutes whole trials for each neuron within tone identity and early/late halves of the run. This preserves each neuron's time-locked firing profile, spike counts and within-trial pattern. Shared trial variability and coincidence across neurons are disrupted. Excess coincidence can reflect common afferents and trial history as well as precise coupling. Rare strata with one trial cannot be permuted. The unique-raster count checks for exact population duplication among cells firing at least once. It spans evoked windows only.

Startup perturbations vary all initial membrane voltages together and separately lower initial presynaptic resource availability. First-ten and last-ten averages compare each perturbation with its paired baseline. The 100-ms prestimulus interval permits some relaxation before the first tone.

## Executed regression and isolated-cell results

The original 16 tests passed. Stage 1 added four event-clock tests and fixed input binning at represented grid boundaries. All **20 tests passed** in the corrected implementation. [Event-clock and threshold checks](../../stage1/VALIDATION.md) The end-to-end STDP test obtains presynaptic arrivals and L4 spike times from a driven 20-token run with non-default learning amplitudes. For every existing contact, a separate Python calculation enumerates all earlier spikes at each update time, sums their exponentially discounted contributions, and updates the weight once for that time. The reconstructed final matrix agrees with the native output to an absolute tolerance of $2\times10^{-13}$. Seed replay produced exactly equal arrays. Oddball and many-standards controls retained the same target positions and the same arrival times and fiber identities during those target tones for both tone-role assignments.

A more stringent isolated-cell check delivered simultaneous inputs from fiber 0, switched off both forms of plasticity, and observed the SP neuron with the strongest connection from that fiber. The feedforward architecture gives this cell the single known drive $g_E(t)=g_E(0)\exp[-t/(5\,\mathrm{ms})]$. An independent DOP853 solver located upward threshold crossings continuously, restarted at reset after each 2-ms absolute refractory period, and integrated to 40 ms. For eight inputs the reference produced four spikes at 0.513, 3.401, 7.168 and 16.363 ms. The production 0.5-ms grid gave spikes at 1.0, 4.0 and 8.5 ms and missed the fourth. The 0.125-ms grid also missed it. At 0.03125 ms all four appeared, with the last 1.325 ms late. At 0.0078125 ms the maximum error was 0.122 ms. Five inputs produced three reference spikes. Here the 0.25-ms grid retained the third spike, while the 0.5-ms grid missed it. Spike counts can change discontinuously as repeated threshold delays alter subsequent resets. The fine-grid diagnostic below therefore addresses population estimands directly.

## Held-out network diagnostics

Across 96 grid-study runs, active final direct weights ranged from 0.4260 to 0.5761. None approached either bound within 0.01. At the nominal rate the early and late whole-run L4 rate on the finest grid averaged 0.660 and 0.766 Hz per cell. The working grid (0.5 ms) increased them by 0.0214 [0.0135, 0.0293] and 0.0223 [0.0129, 0.0317] Hz respectively. Coarse minus fine changes in the unswapped deviant-minus-standard contrast averaged +0.0517 [0.0125, 0.0909] Hz early and −0.0409 [−0.1383, 0.0565] late. At 25% higher input rate the corresponding absolute changes averaged 0.137 and 0.092 Hz per seed, with a maximum of 0.324 Hz. Effects of roughly this size warrant endpoint-specific refinement.

| Diagnostic at 0.5 ms | Early | Late |
| --- | ---: | ---: |
| L4 whole-run rate with inhibition, Hz/cell | 0.681 | 0.788 |
| L4 whole-run rate without inhibition, Hz/cell | 2.131 | 2.920 |
| L4 whole-run rate with fixed weights, Hz/cell | 0.678 | 0.791 |
| Observed coactive peers per evoked L4 spike | 2.168 | 1.295 |
| Trial-shuffled coactive peers | 0.372 | 0.347 |
| Mean largest 1-ms simultaneous fraction of L4 | 0.196 | 0.150 |
| Mean active cells / unique active evoked rasters | 27.33 / 26.50 | 27.50 / 26.67 |

The largest evoked coincidence across the 12 reference runs was 10/40 cells. The layers retain shared timing well above trial-shuffled values. Sparse neurons can share a few identical output events. Spike trains differ across most active cells. Their common afferents, delays, tuning, and finite timing bins all constrain this result. Lowering initial resources to 0.5 shifted mean first-ten evoked net L4 rates by −0.129 Hz early and −0.113 Hz late. The last-ten means matched the reference in both regimes to the precision of these spike-count summaries. Starting somata at −58 mV shifted the corresponding first-ten means by 0.000 and +0.008 Hz. These startup effects were smaller than those of removing inhibition in these runs.

## Direct refinement of the primary conclusions

A separate 256-run repetition used the primary eight seeds (1001–1008), both tone-role assignments, both regimes and all 100 tokens at each of 0.5 and 0.125 ms. Each step included oddball and probability-matched many-standards protocols with and without depression. Each CI uses eight role-averaged paired seed estimates. A value in brackets is the between-seed 95% interval at the fine step.

| Endpoint | Early, 0.5 ms | Early, 0.125 ms [95% CI] | Late, 0.5 ms | Late, 0.125 ms [95% CI] |
| --- | ---: | ---: | ---: | ---: |
| L4 deviant minus standard, Hz/cell | 1.503 | 1.404 [1.088, 1.719] | 0.463 | 0.438 [0.298, 0.577] |
| Same target in oddball minus many standards, Hz/cell | 0.273 | 0.273 [0.157, 0.390] | 0.025 | 0.006 [−0.030, 0.042] |
| Without depression, same target in oddball minus many standards, Hz/cell | −0.002 | −0.002 [−0.005, 0.002] | 0.000 | −0.005 [−0.014, 0.005] |
| Change in deviant minus standard direct efficacy, dimensionless | −0.01483 | −0.01410 [−0.01757, −0.01063] | 0.00057 | 0.00130 [−0.00239, 0.00498] |
| SP minus L4 role contrast, Hz/cell | 1.733 | 1.909 [1.252, 2.566] | 1.800 | 1.881 [1.238, 2.524] |

At 0.125 ms the paired late-minus-early effect on the L4 role contrast was −0.966 [−1.192, −0.739] Hz/cell. The early frequency-matched context difference persisted, with the late estimate near zero. The early direct weight contrast continued to favor the standard. The late interval included both signs. The relative layer ordering at each age survived refinement. Single spikes, precise timings, small late effects and individual-seed changes remain grid dependent.

## Files

| Result | Contents |
| --- | --- |
| `results/validation_isolated.csv` | Ordinal spike times at eight steps for both isolated impulses, with missing spikes recorded as NaN. |
| `results/validation_grids.csv`, `results/validation_refinement.csv` | Held-out seed outcomes and paired differences relative to 0.125 ms. |
| `results/validation_diagnostics.csv` | Per-seed perturbations, endpoint state, active-cell and synchrony measures. |
| `results/validation_primary_seeds.csv`, `results/validation_primary.csv` | Primary seed aggregates, two-grid estimates, intervals and matched coarse-minus-fine changes. |
