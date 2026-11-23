# Where does the matched-target response arise?

The same rare afferent bursts evoke a larger early L4 response in the oddball stream than in the many-standards stream. The circuit permits two kinds of short-term memory. Depression of a thalamic fiber changes both its direct L4 drive and its SP drive. Depression of an SP output changes both its excitation of L4 and its recruitment of inhibition. Selectively holding one source population's release fixed isolates these two loci while preserving its fully recovered EPSC. This comparison leaves long-term plasticity active.

## Selective depression

The main role contrast is the oddball deviant response minus the standard response, both expressed as baseline-corrected Hz per cell per presentation. The context contrast instead compares the *same rare tone*, at the same positions and with the same afferent events, in oddball versus many standards. Distractor identities and the resulting short-term resources differ. The table gives means over eight independent network/input seeds with both physical assignments averaged inside each seed. Brackets give two-sided 95% Student intervals across seeds. Each run used 100 tokens.

| Stage | Depressing output | L4 role contrast (Hz) | L4 matched-target context contrast (Hz) | SP index minus L4 index |
|---|---|---:|---:|---:|
| Early | Thalamus and SP | 1.503 [1.158, 1.848] | 0.273 [0.157, 0.390] | 0.166 [0.121, 0.211] |
| Early | Thalamus only | 1.662 [1.221, 2.103] | 0.006 [−0.022, 0.035] | 0.199 [0.151, 0.246] |
| Early | SP only | 1.115 [0.683, 1.547] | 0.506 [0.320, 0.692] | −0.134 [−0.200, −0.068] |
| Early | Neither | 0.281 [−0.501, 1.064] | −0.002 [−0.005, 0.002] | 0.004 [−0.045, 0.053] |
| Late | Thalamus and SP | 0.463 [0.305, 0.620] | 0.025 [−0.012, 0.062] | 0.147 [0.103, 0.191] |
| Late | Thalamus only | 0.510 [0.339, 0.681] | 0.000 [−0.030, 0.030] | 0.138 [0.094, 0.181] |
| Late | SP only | 0.042 [−0.203, 0.288] | −0.009 [−0.043, 0.024] | 0.016 [−0.040, 0.072] |
| Late | Neither | 0.166 [−0.117, 0.449] | 0.000 [−0.006, 0.006] | −0.002 [−0.057, 0.054] |

Early thalamic depression by itself generated a substantial rare-over-frequent difference, with little residual response to oddball context once target probability was matched. Adding depression to the SP outputs generated a context difference at L4. Indeed, SP output depression acting alone yielded a larger early context difference than the intact circuit. The paired factorial interaction (both − thalamus only − SP only + neither) was −0.241 Hz [−0.376, −0.106]. The corresponding early role-contrast interaction was −0.992 Hz [−1.444, −0.541]. Nonlinearity and feedforward inhibition prevent additive attribution of these effects. Selective depression on SP→I versus SP→L4 was not resolved because both projections share an SP resource.

For the intact early network, the SP selectivity index was 0.456 and the L4 index was 0.289. Both decreased in the late network, to 0.234 and 0.087. The paired late-minus-early change in the **layer difference** was −0.019 [−0.044, 0.006]. The modeled SP advantage consequently persists across the stage switch. Mehra et al. reported that the relative layer ordering changed after ear-canal opening, with details depending on the stimulus and index. Their neuronal CSI distributions and this population role index have different denominators, windows and aggregations. The simulation captures an early ordering but fails to show the reported change in ordering. [Mehra et al. (2022)](https://doi.org/10.1523/JNEUROSCI.0431-21.2021)

## Recovery-time extremes

A second intervention replaces recovery at both depressing loci with either 100 or 4200 ms while retaining every other parameter at that stage. The three columns distinguish per-presentation rate differences, matched-target context modulation and cumulative learned efficacy. Positive efficacy contrast means the deviant pathway changed more than the standard pathway.

| Stage | Recovery (ms) | L4 role contrast (Hz) | L4 context contrast (Hz) | Deviant minus standard efficacy change |
|---|---:|---:|---:|---:|
| Early | 100 | 0.333 [0.016, 0.650] | 0.014 [−0.002, 0.030] | +0.01034 [0.00560, 0.01508] |
| Early | 650 (nominal) | 1.503 [1.158, 1.848] | 0.273 [0.157, 0.390] | −0.01483 [−0.01828, −0.01139] |
| Early | 4200 | 1.566 [1.329, 1.803] | 0.242 [0.179, 0.306] | +0.00025 [−0.00141, 0.00190] |
| Late | 100 | 0.219 [0.055, 0.383] | −0.002 [−0.015, 0.011] | +0.01425 [0.01065, 0.01786] |
| Late | 350 (nominal) | 0.463 [0.305, 0.620] | 0.025 [−0.012, 0.062] | +0.00057 [−0.00308, 0.00422] |
| Late | 4200 | 1.599 [1.344, 1.853] | 0.061 [−0.008, 0.130] | +0.00025 [−0.00108, 0.00158] |

At 4200 ms, SP/L4 role indices are about 0.90 in both populations and both stages, and cumulative weight asymmetry is close to zero. At 100 ms, the early efficacy ordering reverses relative to the nominal run. The sign of preferential learning therefore depends on recovery. Per-presentation novelty preference alone does not predict accumulated learning. These two extremes come from a published binary model with a different release law. Transferring just this parameter does not reproduce its model.

## Reproduce the calculations

Run `python run_mechanisms.py --jobs 4` from the project root. The design comprises 6 conditions × 2 stages × 8 seeds × 2 role assignments × 2 contexts = 384 simulations. The stage-specific recovery extremes, plus the four selective-depression conditions, all retain the same background, full-recovery gain and STDP rule. The code writes `results/mechanism_seeds.csv` and `results/mechanism_summary.csv`. For the interaction, pivot seed rows on condition, evaluate the four-term contrast within each seed, then compute its mean and Student interval. The SP-minus-L4 gap uses each population's baseline-corrected role index $(D-S)/(|D|+|S|)$. The stage comparison differences those gaps within each seed. These intervals quantify uncertainty over model realizations. The stage parameter sets and anatomical assumptions contribute additional uncertainty.
