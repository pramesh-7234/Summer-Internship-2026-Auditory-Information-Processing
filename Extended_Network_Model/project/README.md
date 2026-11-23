# Acute oddball responses and retained learning in a developmental auditory circuit

Does responding strongly to a rare tone during exposure predict which tone will gain the most response afterward? In this feedforward spiking model, each early layer 4 (L4) circuit fired more strongly to rare tones during training. All eight circuits subsequently gained more response to the formerly frequent tone on independent probes.

[Executed notebook](Auditory_Plasticity.ipynb) · [Scientific report (PDF)](Research_Report.pdf) · [Report source](docs/research_report.md) · [Figure gallery and data sources](figures/README.md)

![Seed-level direct efficacy and retained L4 responses on two numerical grids](../stage4/retained_learning.png)

Points joined by light lines are the same seed tested on two integration grids after 100 tones. Diamonds and bars give means and pointwise 95% intervals. Negative values favor the formerly frequent tone.

## Experimental design

Four thalamic afferents per frequency class drive a circuit of 40 subplate neurons, 10 interneurons and 40 L4 neurons. Inputs excite L4 directly and through the subplate. Short-term depression changes release during a stream. Spike-timing-dependent plasticity changes direct thalamic efficacies. The early and late parameter sets differ in direct and relay gains and resource recovery time. Developmental gains and learning constants are hypotheses. [Model equations and parameters](docs/methods.md)

The primary comparison uses eight independent circuit/input seeds, 90 frequent and 10 rare tones, and two assignments that exchange tone identity. Rates subtract pre-onset activity. Gain measures change from the initial to the learned weights on identical isolated test bursts. Each interval uses paired seed estimates. The 64 test bursts per physical tone reduce within-seed noise.

| Rare minus frequent after 100 tones | Early mean [95% interval] | Late mean [95% interval] |
|---|---:|---:|
| Acute L4 firing during training, Hz/cell | +1.503 [1.158, 1.848] | +0.463 [0.305, 0.620] |
| Change in direct efficacy, dimensionless | −0.01483 [−0.01828, −0.01139] | +0.00057 [−0.00308, +0.00422] |
| Held-out L4 gain, Hz/cell | −0.05762 [−0.08113, −0.03410] | +0.01587 [−0.02784, +0.05957] |

## What the controls establish

- Matching target events across oddball and many-standards streams gave an early context effect of +0.2734 Hz/cell. Restricting depression to the thalamic outputs reduced it to +0.0063. The preceding sound and the earlier sequence both contributed. [History experiment](../stage3/MECHANISM.md)
- Extending the same stream from 100 to 1,000 tones shifted the held-out contrast toward the frequent tone in both regimes. Four paired seeds supported the shift. The late endpoint remained imprecise. [Long exposure](../stage5/LONG_EXPOSURE.md)
- An alternative that allowed the SP→L4 relay to learn strengthened the early frequent-tone advantage in every seed. In the late circuit the frequent tone lost more response than the rare tone. [Relay experiment](../stage6/RELAY_EXPERIMENT.md)
- The early baseline preference persisted on a finer grid. The solver missed a fourth spike in an isolated near-threshold challenge even at 0.125 ms. Reporting that failure bounds what the population comparisons establish. [Numerical verification](../stage1/VALIDATION.md)

The circuit tests immediate readout at a fixed developmental stage. The persistence of early experience into adulthood remains an open biological question. A separate 32-seed cohort measured acute firing and direct efficacy. Its extra seeds do not narrow the functional probe intervals. [Verified primary and replication estimates](../stage2/VERIFICATION.md)

## Run the notebook

Extract the entire checkpoint, retaining the sibling stage directories. Use Python 3.12 and a C99 compiler. From the extracted checkpoint root on Linux or macOS:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r project/requirements.txt
python -m pip install ipykernel==6.29.5 nbformat==5.10.4 pillow
(cd project && python -B -m unittest discover -s tests -v)
python -B stage7/execute.py
```

The executed notebook includes all outputs for reading without installation. To inspect it interactively, install JupyterLab in the same environment and open `project/Auditory_Plasticity.ipynb`. For the optional rendering check, install Pandoc and run `python -B stage7/check_render.py`. [Notebook verification and dependencies](../stage7/NOTEBOOK_VERIFICATION.md)

## Reproduce individual results

| Location | Contents and entry point |
|---|---|
| [auditory/](auditory/) | Python API and double-precision C99 solver. Each Python process compiles the bundled kernel on demand. |
| [results/](results/), [experiment protocol](docs/experiments.md) | Per-token counts, trajectories, parameter sets and archived summaries. From project/, run `python run_experiments.py --quick --tokens 20 --output scratch/smoke` for a small trial. |
| [Stage 2](../stage2/VERIFICATION.md), [Stage 4](../stage4/RETENTION.md) | Raw replay checks, nominal and fine-grid probe counts, seed-level contrasts and commands. |
| [Figure gallery](figures/README.md) | Each figure's estimator, sample size, source measurements and generator. |
| [Original notebooks](originals/), [historical audit](docs/original_audit.md) | Preserved internship materials and evidence for revising the model. |
| [Methods](docs/methods.md), [literature](docs/literature.md) | Model equations, integration conventions and biological motivation. |

The historical 24-hour CSV had malformed records and implausible values. The revised scientific results use the audited model and the explicitly identified simulation outputs.

## Verify the release

The full audit also uses Pandoc and Poppler (pdftoppm and pdftotext) on the system path. From the extracted release root, install the optional dependencies with `python -m pip install -r project/requirements-audit.txt`. Verify the unmodified download with `sha256sum -c SHA256SUMS`. The notebook, validation and plotting commands can then be run in a working copy. The completion report records the tested platform, audit scope, scientific outcomes and remaining questions. [Completion report](../stage9/COMPLETION.md)
