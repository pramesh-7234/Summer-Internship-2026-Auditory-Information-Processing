# Figure captions

The numbered figures use the model's simulation clock and its dimensionless efficacies. Their PNG and PDF versions contain the same data. Each error bar or shaded band in Figures 3–7 is a pointwise 95% Student interval over independent simulation seeds, with both physical-tone assignments averaged within each seed first. Intervals describe Monte Carlo uncertainty under this model. They neither measure biological variation nor adjust for simultaneous comparisons.

**1. Circuit and direct connectivity.** Thalamic fibers drive subplate (SP) and layer 4 (L4). SP drives L4 both through direct excitation and through an inhibitory population (IN). Thalamic and SP outputs depress. Pair-based long-term plasticity acts on direct thalamic input to L4. Both heatmaps show the same virtual circuit at initialization (seed 1001), with neurons and fibers sorted by tuning position. Color gives the conductance jump from one fully recovered input spike divided by leak conductance. The late regime gives this pathway a larger initial gain. Gray pixels are structurally absent edges. The corner bands follow from the assumed circular tuning map.

**2. Population spike rasters.** Eight consecutive presentations surround the first deviant in the unswapped seed-1001 schedule. Each tick is one output spike. Horizontal lines delimit the populations, and shaded regions span the 50-ms input bursts. The two panels share the same continuous presynaptic event realization. This fixed example illustrates timing and tuning within one block.

**3. Responses to stimulus role and context.** The intact-circuit results use eight seeds. Each rate subtracts the mean rate during the 100 ms before onset from the mean rate during the first 100 ms after onset. Each standard and deviant is weighted equally within its own role. A compares L4 responses to both roles. Faint lines connect measurements from the same seed. B gives the deviant-minus-standard difference for each population. C compares the same rare L4 target at matched positions in oddball and ten-tone equiprobable blocks. Each point in B and C represents one seed, apart from the larger mean markers. Differences between the two blocks can also arise from the recent sequence of neighboring tones and adaptation.

**4. Direct thalamic-to-L4 plasticity.** A–B plot the mean efficacy change on connected edges from the four fibers of the physical tone assigned each role. Trajectories are centered on each run’s initial efficacy, sampled every five stimuli, then averaged across assignments and eight seeds. Both panels use a common vertical scale. C compares cumulative deviant-minus-standard efficacy changes from initialization to the midpoint and endpoint of exposure. D shows the empirical cumulative distribution of edgewise final-minus-initial efficacy in the unswapped seed-1001 example, including connections from all ten tone groups. It describes variability across contacts in one circuit.

**5. Pathway and plasticity ablations.** Each point is a paired difference, ablation minus intact, averaged across eight seeds. A positive value in A means the ablation increases the L4 deviant-minus-standard response; in B it increases deviant-minus-standard direct efficacy gain. Removing SP→L4 leaves SP-driven inhibition intact. B omits the direct-path deletion because the effective pathway has zero gain. The two panels have different units.

**6. One-parameter sensitivity.** Every comparison changes one parameter from its default for that regime. The input-rate adjustment scales the burst rate, the threshold shifts all population thresholds, and the width adjustment changes thalamus→SP, thalamus→L4 and SP→L4 tuning widths. Recovery time pertains to depression. Learning rate scales both STDP amplitudes. The LTP-only perturbation scales potentiation with fixed depression amplitude. Each point is a perturbed-minus-intact difference within seed, averaged across the four paired seeds used for sensitivity runs.

**7. Held-out single-tone probes.** After either 100 or 1,000 training presentations the simulator resets membrane, conductance and short-term resource states and freezes the synaptic efficacies. It compares training-end with initial weights on the same 64 independently drawn single-token test bursts per physical tone and seed. The plotted gain is the difference in baseline-corrected probe response under the two weight states. A–B average over all L4 cells. C–D average over the four cells with strongest direct input from the tested frequency at initialization. Faint lines join the two training roles within a seed. The two rows use different scales. The source table is `results/probe_seeds.csv`.

The source for Figures 1–7 is `make_figures.py`. For Figures 1, 2 and 4D it executes the fixed example through `auditory.simulate`. Population, ablation and sensitivity summaries come from `results/seed_metrics.csv`. The learning curves come from `results/weight_trajectories.csv`.

**8. Numerical validation.** Left, the within-seed difference between the indicated time step and 0.125 ms for the acute rare-minus-frequent L4 contrast. Both regimes use the six diagnostic seeds at the nominal input rate. Markers show means and bars give pointwise 95% Student intervals. Right, a deterministic eight-impulse challenge with one SP recipient. Each marker gives the time of its fourth spike. Shading identifies steps with only three spikes. The reference is a continuous threshold-crossing solution.

**9. Held-out responses before and after exposure.** Mean evoked-minus-baseline firing over all 40 L4 cells on 64 independent probe bursts per physical tone, using the 100-presentation standalone protocol. Each thin line follows a single seed. Diamonds and bars show means and pointwise 95% intervals across eight seeds for the individual states. The paired gains and their uncertainty are in Figure 7 and the Stage 4 report. Both physical tones contribute equally to each role.

## Files and provenance

Paths in the source column are relative to the extracted checkpoint root. Each PNG has an adjacent vector PDF with the same stem.

| Figure | Source measurements | Rebuild |
|---|---|---|
| [1 · Circuit](01_circuit.png) | Seed 1001 initial `direct_base × initial_weights` on connected edges and the implemented topology | `project/make_figures.py --only circuit` |
| [2 · Population rasters](02_example_activity.png) | Exact spike times and cell IDs from the unswapped seed-1001 runs | `project/make_figures.py --only raster` |
| [3 · Acute role and context](03_role_responses.png) | `project/results/seed_metrics.csv`, intact and many-standards conditions | `project/make_figures.py --only responses` |
| [4 · Efficacy trajectories](04_plasticity.png) | `project/results/weight_trajectories.csv`, `seed_metrics.csv`, seed-1001 edge distributions | `project/make_figures.py --only plasticity` |
| [5 · Ablations](05_ablations.png) | `project/results/seed_metrics.csv`, ablation minus corresponding intact seed | `project/make_figures.py --only ablations` |
| [6 · Sensitivity](06_sensitivity.png) | Same table, each perturbation paired with the matching four intact seeds | `project/make_figures.py --only sensitivity` |
| [7 · Probe gains](07_held_out.png) | `project/results/probe_seeds.csv`, 8 short and 4 long seeds | `project/make_figures.py --only held_out` |
| [8 · Numerical validation](08_numerical_validation.png) | `stage1/paired_grid_checks.csv` and `stage1/threshold_spikes.csv` | `stage8/figures.py` |
| [9 · Before and after](09_probe_responses.png) | `stage4/assignment_results.csv`, nominal grid, pooled within seed and training role | `stage8/figures.py` |
| [Target history](../../stage3/history_effects.png) | `stage3/seed_contrasts.csv` and `estimates.csv`. Eight early seeds, mean and 95% intervals for L4 firing and pretarget availability. | `stage3/figure.py` |
| [Grid refinement of retained gain](../../stage4/retained_learning.png) | `stage4/seed_results.csv` and `estimates.csv`. Connected dots follow the same seed across grids, diamonds and bars show eight-seed means and 95% intervals. | `stage4/figure.py` |
| [Long exposure](../../stage5/long_exposure.png) | `stage5/timecourse_seeds.csv` and `horizon_seeds.csv`. Light lines show four individual seeds, heavy lines their mean. Left panels show 100-tone blocks, right panels the two measured functional endpoints. | `stage5/figure.py` |
| [Plastic relay](../../stage6/relay_gain.png) | Count matrices in `stage6/raw/` paired with the initial and baseline matrices in `stage4/raw/`. Each thin line follows one of eight seeds, diamonds mark the mean. | `stage6/analyze.py` |

Run a listed Python script with `python -B` from the extracted root. For a graphics replay in an isolated directory, install Pillow, pypdf and Poppler's pdftoppm, then run `python -B stage8/review_figures.py`. Its comparison covers all 13 PNGs and all 13 single-page PDFs.
