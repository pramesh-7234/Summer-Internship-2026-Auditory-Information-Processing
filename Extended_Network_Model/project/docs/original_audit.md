# Audit of the internship models

The vectorised notebook can exhibit a large rare-versus-common response difference. Its 40 subplate neurons receive identical inputs and produce exactly one distinct spike train. Both stimulus channels merge before the first plastic projection, so the final SP → L4 matrix cannot identify which thalamic pathway strengthened. In three replays, 79–80% of its entries reached their upper bound. The smaller bilayer notebook retains the two thalamic identities. In that model, the sign of the early weight difference depends on the documented rate and threshold adjustments.

## Material and provenance

The input was `ffn_proj(2).zip`, SHA-256 `54f6491a27c51ed845b5e2abe1de93a790e626adab5ffe17729d19a069326de0`. All 27 files passed ZIP integrity checks. The project includes three original notebooks with their saved outputs, copied byte for byte from the archive. The remaining materials were reviewed in place.

| Item in archive | Evidence used |
|---|---|
| `Untitled.ipynb` | Main 40 SP, 10 IN, 40 L4 simulation. Source cells and fresh replays below. |
| `Bilayer Model/Two_Neuron_Auditory_Cortex_Model.ipynb` and sibling README | Two-neuron reference, explicit direct thalamic projections, independent initialisation with shared input across two regimes. Matched original results in a fresh execution. |
| `Bilayer _ without Near spike cancellation.ipynb` | Earlier non-consuming pairing rule and CSV export code. Its numeric results are a separate model variant. |
| `Notes.txt` | Identifies deliberate threshold/rate changes and choice of longer observation time after inspecting behaviour. |
| Eight non-checkpoint PNGs | Two MATLAB screenshots, two earlier early/late plots, two channel-silencing plots and the two revised bilayer outputs. Several use different recording lengths. Historical illustrations lack machine-readable run configurations and cannot provide independent replications. |
| `synaptic_weights_24hour_sim.csv` | Inspected every record. See the export diagnosis below. |
| Mehra and Mill PDFs | Compared the two primary articles' equations and parameter provenance against the notebooks. |
| Checkpoints and caches | Earlier 10-neuron, two-neuron and vector experiments, an instructional MOOSE notebook and LIF example, copied figures/notes, and two Python bytecode files. The revised two-neuron checkpoint matches its primary notebook byte for byte. None is used as an independent observation. |

## Vector model, reconstructed from execution order

Cell numbers below are zero-based, including Markdown cells. Time is a fixed 1 ms grid. For each of 350 tokens, cell 2 independently chooses a standard with probability 0.9. During the first 50 ms the matching channel has Bernoulli spike probability 0.05 per bin and the other 0.00015. Both have probability 0.0001 during the following 250 ms. On average the active channel contributes 2.5 spikes per token. Two scalar spike trains are shared across all SP cells. The loop processes `range(105000-1)` and stores cortical spikes at the right endpoint of the step.

**Cell 6 sets the anatomy.** Rows of each $W$ index receiving neurons and columns index sending neurons. $W_{ij}=a\exp[-(x_i-x_j)^2/(2\sigma^2)]$ uses equally spaced coordinates on $[0,1]$, including endpoints. Both thalamic channels enter every SP neuron with fixed gain 0.20. The cortical pathways are SP → L4 $(a=0.32,\sigma=0.5)$, SP → IN $(0.38,0.1)$ and IN → L4 $(-0.18,0.1)$. The default row sums span 7.65–10.87, 2.05–3.71 and −0.406 to −0.293, respectively. Edge location and population size therefore change the total available drive. All 52 of the 400 SP → IN weights above 0.30 are clipped on the first STDP pass, even without spikes. Cell 5's “initial” plot uses a separate 10×10 example with peak 0.5 and width 0.7. Cell 12 plots the actual 40×40 initialisation.

**Cell 8 advances the voltage.** Outside refractoriness, $v_{k+1}=0.9v_k+D_k$, with thresholds 0.10, 0.10 and 0.15 for SP, IN and L4. The 0.9 multiplier has an equivalent exponential leak time of $ -1/\log(0.9)=9.49$ ms, or an Euler interpretation with a 10 ms time constant. The code specifies drive as an abstract voltage increment per step. It provides no membrane capacitance, reversal potential or physical current scale. At threshold the cell records the right-end time $s=k+1$ and resets to −5. While $k-s<20$, the update is overwritten by $-5\exp[-(k-s)/2]$. The earliest next recorded spike is $s+21$ ms. The threshold test still executes during refractoriness, although the negative recovery voltage cannot cross the supplied positive thresholds. Scaling time step requires changing the input probabilities, decay, integration, spike and delay conventions together.

**Cells 9 and 12 advance transmission.** Let $r,e,i$ be recovered, effective and inactive fractions. Per update the flows are $F=s\min(r/0.9,r)=sr$, $G=e/\tau_{ei}$, $H=i/4200$. The state increments are $H-F,F-G,G-H$. Thalamic $\tau_{ei}=10$ ms and cortical $\tau_{ei}=27$ ms. The sum is conserved algebraically and the listed unit-step parameters preserve nonnegativity. The stored integer-bin dynamics release *all* available resource on every spike. For comparison, a continuous 1 ms square pulse with $\tau_{re}=0.9$ ms gives a recovered-pool loss of $1-e^{-1/0.9}=0.671$ if recovery into that pool is negligible during the pulse. The forward-Euler estimate 1.111 is capped at 1. The handling of release thus matters even when every invariant passes.

The raw spike train separately drives $g_k=e^{-1/10}g_{k-1}+s_k$, truncated at 100 samples on the thalamic paths. Synaptic drive is the weighted product $g_ke_k$. Cortical resources and conductance use the previous cortical spikes. The input is current-like and signed, independent of postsynaptic voltage. Multiplying the two filtered states creates history-dependent cross-products; an isolated input's current decays according to both filters. Mehra's published computational model also uses a $g\,w\,e$ product. Replacing it with a single release-proportional current is a change of synaptic model. Mill's conductance-based variant uses $e$ to scale a reversal-potential current. [Mehra et al., 2022, p. 1458](https://doi.org/10.1523/JNEUROSCI.0431-21.2021) · [Mill et al., 2011, Methods](https://doi.org/10.1371/journal.pcbi.1002117)

**Cells 10 and 12 update plasticity.** For a current presynaptic spike, column weights are multiplied by $1-0.021\exp[-\max(k-s_{\rm post},0)/20]$. For a current postsynaptic spike, row weights are then multiplied by $1+0.015\exp[-\max(k-s_{\rm pre},0)/13]$. The entire matrix is clipped after both operations. Only one opposite spike timestamp per neuron is retained. Previous spikes can be reused, but an earlier history cannot contribute as an all-pairs sum. Initialising last times to −1000 approximates an empty history by an exponentially small contribution.

Cortical trackers have already been written with $k+1$ for current events, whereas the weight function compares against $k$. A real 1 ms separation therefore appears as zero; same-bin events yield a separation of −1 before clipping. For two simultaneous spikes both updates fire, giving $0.979\times1.015=0.993685$ times the previous weight in the absence of a binding cap. This coincidence convention follows from update order. Bounds are [0, 0.45] for SP → L4, [0, 0.30] for SP → IN and [−0.50, 0] for IN → L4. The same multiplicative window applied to a negative weight changes inhibitory magnitude; the notebook offers no pathway-specific justification.

**What can be identified.** Induction from equal initial states, input weights, resource pools, thresholds and incoming spike trains gives identical SP voltages and spikes at every step. There is no mechanism that labels an SP cell as standard- or deviant-preferring. Each input channel still has its own resource state, so unequal histories can produce different token-evoked responses before both drives merge. The network has no age selector, direct thalamus → L4 path, channel-labelled plastic weights, or independent frequency-swap or rate-matched controls. The saved final heatmap uses its own colour scaling and the raster displays the first 5 s of a 105 s experiment. Neither measures change relative to the initial weights or responses conditioned on stimulus history.

## Re-execution of the vector model

We seeded the legacy NumPy generator immediately before executing the supplied source cells in a fresh namespace. There were no changes to parameters or equations. Each row covers 350 tokens. The response is mean spikes per L4 cell per presentation during [0, 50) ms minus the preceding 50 ms. The first token is omitted because there is no complete baseline. The synchrony fraction counts spikes in 1 ms bins in which *all* 40 L4 cells fired, divided by the total L4 spike count.

| Seed | Standard / deviant tokens | Mean SP / L4 rate (Hz per cell) | Distinct SP / L4 spike trains | L4 standard / deviant response | L4 full-population synchrony | SP → L4 at 0.45 |
|---:|---:|---:|---:|---:|---:|---:|
| 2026 | 315 / 35 | 0.505 / 0.990 | 1 / 15 | 0.099 / 1.343 | 83.7% | 78.6% |
| 2027 | 316 / 34 | 0.533 / 1.033 | 1 / 12 | 0.098 / 1.500 | 82.9% | 80.1% |
| 2028 | 319 / 31 | 0.514 / 0.979 | 1 / 15 | 0.100 / 1.433 | 86.6% | 78.6% |

The legacy circuit therefore has a reproducible descriptive oddball contrast in these three sequences. Its deterministic symmetry and imposed caps co-occur with that contrast. The results cannot separate adaptation and deviance or assign learning to one of the two thalamic identities.

## Two-neuron reference and parameter provenance

The revised bilayer model explicitly stores separate standard → L4 and deviant → L4 weights in addition to SP → L4. It consumes the most recent eligible pre/post event after pairing within 100 ms. Equal timestamps potentiate and all three weights have bounds [0, 1]. Within a step it adds the *current* SP spike to filtered conductance while the SP resource update still uses the *previous* SP spike. Its ordering differs from the vector network. Seed 2026, 1,000 tokens and both age presets reproduce the saved outputs to the displayed precision.

| Regime | SP spikes | L4 spikes | Final standard → L4 | Final deviant → L4 | Final SP → L4 | Fraction of time standard / SP at cap |
|---|---:|---:|---:|---:|---:|---:|
| Early | 152 | 126 | 0.03056 | 0.05410 | 1.00000 | 0.0% / 5.7% |
| Late | 1,288 | 2,060 | 1.00000 | 0.73360 | 1.00000 | 75.8% / 33.9% |

The two-neuron initial direct weights (0.02/0.12), SP → L4 weights (0.22/0.04), and early/late recovery times (4,200/100 ms) are parameter choices in Mehra's published simulation. The methods cite developmental trends as motivation. The original internship raised the active input rate from 8 to 50 Hz, the early SP threshold from 0.05 to 0.10, and the L4 threshold from 0.10 to 0.15. `Notes.txt` explains that these adjustments made particular response patterns easier to obtain. These are two different sources of parameter uncertainty. [Mehra et al., 2022, pp. 1458–1459](https://doi.org/10.1523/JNEUROSCI.0431-21.2021)

**Paired historical sensitivity check.** We crossed the two active rates with two threshold bundles, in both regimes, across seeds 2026–2028 (24 runs of 300 s). Holding the seed fixed gave identical tokens, background events and uniform variates for active spikes. The paper-threshold bundle sets early SP to 0.05, late SP to 0.15 and L4 to 0.10. The internship bundle uses 0.10, 0.15 and 0.15, respectively. Only the rate and thresholds changed. We retained the notebook's pairing, drive and integration, so this exercise tests the notebook's sensitivity. Each column gives the mean final $w_{\rm dev}-w_{\rm std}$ and the range of the three individual contrasts. Both direct pathways have equal starting weights within each regime.

| Active rate | Thresholds | Early contrast [range] | Late contrast [range] |
|---:|---|---:|---:|
| 8 Hz | Paper | −0.221 [−0.225, −0.212] | −0.747 [−0.775, −0.709] |
| 8 Hz | Internship | −0.059 [−0.069, −0.048] | −0.756 [−0.783, −0.719] |
| 50 Hz | Paper | −0.566 [−0.740, −0.464] | −0.140 [−0.198, −0.106] |
| 50 Hz | Internship | +0.026 [+0.024, +0.029] | −0.190 [−0.266, −0.147] |

Only the combined internship adjustments gave deviant-favouring early weights in these runs. Late standard weights hit the cap in every run. The threshold bundle tests their joint effect and does not isolate which threshold causes the interaction.

## Alternative notebook and the long run

The “without Near spike cancellation” notebook reuses the most recent opposite timestamp on each event. It caps only the standard → L4 weight at 1. Deviant → L4 and SP → L4 can grow geometrically under repeated potentiation. A displayed 47 Hz terminal rate is labelled under-responsive against a target of 80–120 Hz. The model's 21 ms minimum interspike interval allows about 47.6 Hz sustained firing and at most 48 spikes in a one-second window. That diagnostic cannot reach its target under the stated dynamics.

The CSV header declares three weights. **Every one of its 86,400 data rows contains two values.** The commented exporter stacks standard and deviant weights, subsamples every 1,000 bins, writes three labels and rounds to six decimals. The file has no timestamps, seed, revision or SP weight trace. Its first column ranges from 0.000000 to 0.043062. A printed zero may be rounding. Its second ranges from 0.016021 to $7.79234\times10^{46}$ and finishes at $6.49283\times10^{46}$. Row index 2,561 (zero-based) is the first above 1. The inactive code is consistent with the mismatch, but cannot authenticate the generating run. It is inappropriate to compare that series to bounded weights from the other notebooks.

## Corrections and choices for the redesign

| Issue | Action justified by the audit | Status |
|---|---|---|
| Event timestamps, hidden coincidence rule, and inaccurate all-to-all label | Define a physical clock, update from prior traces, document ties and test pair/triplet sequences. | Correct alignment and semantics. Selecting a pairing model changes the learning rule. |
| Initially out-of-bound weights and terminal-only heatmap | Initialise within declared bounds, record changes from baseline and fractions near limits. | Numerical and reporting corrections. |
| Duplicated SP cells and absent direct thalamic plastic pathways | Assign frequency-tuned inputs and provide direct thalamic → L4 pathways that can be individually measured and ablated. | Architecture changes needed to identify pathway-selective learning. |
| Unscaled input and arbitrary-unit voltage | State units or dimensionless conventions, control fan-in, document a consistent solver and compare step sizes on common inputs. | Numerical specification and revised calibration. |
| Full depletion and $g\,e$ product | Model a release fraction explicitly and drive transmission from released resource. Validate single-spike responses, recovery and high-frequency behaviour. | New synaptic assumption relative to Mehra's phenomenological rule. |
| Inhibitory timing rule copied from excitatory synapses | Keep inhibition fixed in the core comparison or supply and test a separate inhibitory learning rule. | Biological modelling decision. |
| Tuned parameters and rarity/exposure confounds | Share stochastic inputs between paired conditions, counterbalance tone identities, run exposure controls, ablations and threshold/rate sensitivity. Distinguish evoked spikes from accumulated weight change. | Experimental design. |

## Replaying the historical checks

Vectors were tested under Python 3.12.14 and NumPy 2.3.5. In a fresh kernel, run `import numpy as np; np.random.seed(2026)` before running `originals/Untitled.ipynb`. Repeat with seeds 2027 and 2028. Within this notebook the following cell computes the two most informative pathologies and both stimulus-conditioned responses.

```python
times = np.concatenate(spiketimes["l4"]).astype(int)
bins = np.bincount(times, minlength=simulation_time_length)
l4_size = len(spiketimes["l4"])
token_bins = bins.reshape(-1, 300)
evoked = token_bins[:, :50].sum(axis=1)
baseline = np.r_[np.nan, token_bins[:-1, -50:].sum(axis=1)]
response = (evoked - baseline) / l4_size
print("L4 synchronous spike fraction", bins[bins == l4_size].sum() / len(times))
print("SP to L4 fraction at cap", np.mean(weights["W_sp_l4"] == 0.45))
for label, code in [("standard", 1), ("deviant", 0)]:
    print(label, np.nanmean(response[token_train == code]))
```

For the bilayer check, run `Two_Neuron_Auditory_Cortex_Model.ipynb` top to bottom to obtain the default case. In a working copy, change `p_high` in `thalamic_input_generator` and `sp_thresh`/`l4_thresh` in `initialize_params` to each exact combination above. Set `RNG_SEED` to each of 2026–2028, keep `NUM_TOKENS = 1000`, run clean kernels, and compute `result["w_dev"][-1] - result["w_std"][-1]` in each regime. No changes to the random draw order or stochastic generator are required.

| Reference notebook (relative to `originals`) | SHA-256 |
|---|---|
| `Untitled.ipynb` | `c61422ad5effa2fad720962c5d729bfe72ef601398bc2715173351e61d5e9c6e` |
| `Bilayer Model/Two_Neuron_Auditory_Cortex_Model.ipynb` | `b454b301f708b3bf0eebb3d018a91659ac96201690c6f9c13d92e835dca4e9ba` |
| `Bilayer _ without Near spike cancellation.ipynb` | `f5f50f87e3bd2c056de18526e3d836f3412e95e2344b06667458b790b87a9ad9` |
