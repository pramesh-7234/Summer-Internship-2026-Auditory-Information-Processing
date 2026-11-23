# Equations, connectivity and event timing

## Circuit and what changes across stages

Forty thalamic fibers drive 40 subplate (SP) and 40 layer 4 (L4) cells. SP excites L4 directly and recruits 10 interneurons (I) that inhibit L4. This feedforward graph gives the same tone two routes into L4. It permits separate removal of the direct thalamic drive, SP excitation of L4, and inhibition. Only direct thalamus→L4 efficacy learns. The identity of the four thalamic fibers assigned to a tone is known, which makes a tone-conditioned weight change directly observable. Efficacy changes on the SP relay, recurrent cortical excitation, inhibition onto SP, spontaneous cortical currents and developmental rewiring are outside this model.

All contact matrices have receiving cells on rows. Tuning coordinates of each cortical population are equally spaced on the unit circle. Each class of four thalamic fibers sits at one of ten equally spaced positions. For width $s$ and circular distance $d$, eligible edges satisfy $d\le2.5s$. Each is kept with probability 0.85. A receiving cell with no contacts retains its closest source. Each retained edge is assigned $b_{ji}=u_{ji}\exp[-d_{ji}^2/(2s^2)]$ with $u_{ji}\sim\mathrm{Uniform}(0.85,1.15)$. The transmission template is

$$
B_{ji}=G\frac{b_{ji}}{\sum_k b_{jk}}.
$$

Thus $G$ fixes the sum of the row before any learned efficacy is applied. Changing the width redistributes drive across inputs while retaining this sum. Coordinates have no calibrated relation to acoustic frequency. Opposite points on the circle are a symmetric pair of distant categories. The circle removes an endpoint advantage at the cost of an artificial wraparound. Except for the predefined age gains, matched seeds give identical structure, thresholds and initial efficacy across stages.

| Projection | Source of current | Width $s$ | Early / late $G$, in units of leak conductance | Short-term depression | Long-term efficacy |
|---|---|---|---|---|---|
| Thalamus→SP | Excitatory | 0.09 | 8 / 8 | Afferent release | Fixed |
| Thalamus→L4 | Excitatory | 0.09 | 6.4 / 16 | Same afferent release | $w_{ji}\in[0,1]$, initially Uniform(0.45, 0.55) |
| SP→L4 | Excitatory | 0.09 | 8 / 3.2 | SP release | Fixed |
| SP→I | Excitatory | 0.12 | 9 / 9 | Same SP release | Fixed |
| I→L4 | Inhibitory | 0.16 | 5 / 5 | Fixed release | Fixed |

The third stage parameter is the recovery constant, 650 ms early and 350 ms late. These changes test stronger early SP support, stronger late direct input and faster late recovery. The numerical gains and time constants are design assumptions. Mehra et al. used 4200 and 100 ms for early and late recovery in their own model. Both extremes are exercised here, and the consequences differ from those at 650/350 ms. The threshold distribution and STDP rule are shared across stages, so the main comparison isolates a specified bundle of three changes. Independent options allow additive threshold perturbations for all cells, SP alone or L4 alone. The original paper and internship parameter units differ from ours. [Biological evidence](literature.md) · [Recovery and pathway study](mechanisms.md)

## Membrane and synaptic conductance

Use milliseconds and mV. The positive conductances $g_E$ and $g_I$ are measured relative to the leak conductance. A free cell satisfies

$$
\tau_m\dot V = (E_L-V) + g_E(E_E-V) + g_I(E_I-V),
\qquad \dot g_E=-g_E/5,\quad\dot g_I=-g_I/10 .
$$

Use $E_L=V_r=-65$ mV, $E_E=0$ mV and $E_I=-80$ mV. The membrane time constants are 20 ms in SP and L4 and 12 ms in I. The resting initial voltage is −65 mV. For each cell independently, draw a threshold from a normal distribution with mean −52 mV and SD 1 mV. A crossing at the end of a grid interval emits a spike at that boundary. Clamp $V=V_r$ for the following 2 ms. Conductances and synaptic resources continue evolving during this interval. Cortical transmission incurs a physical delay of 1 ms on each projection. Thalamic events are specified as local arrivals, so there is no additional thalamic delay.

Each incoming event increases the receiving conductance. Inhibition uses the negative driving force $E_I-V$. Within an event-free interval of length $h$, freeze both conductances at their exact mid-interval values $\bar g_E=g_E(0)e^{-h/10}$, $\bar g_I=g_I(0)e^{-h/20}$. Let $a=1+\bar g_E+\bar g_I$ and $V_\infty=(E_L+\bar g_E E_E+\bar g_I E_I)/a$. Advance with

$$
V_{k+1}=V_\infty+(V_k-V_\infty)\exp(-a h/\tau_m).
$$

This exponential midpoint step is exact for constant conductances and a second-order approximation on smooth subthreshold intervals with decaying conductances. Threshold location and arrival binning introduce errors of order one grid step. The main simulation uses $h=0.5$ ms. Other supported steps exactly divide 1 ms. See [grid and isolated-neuron results](validation.md) for numerical sensitivity.

## Depression and normalized first-event conductance

Each thalamic or SP source has an available fraction $x$ and an unavailable fraction $1-x$. Between events, $\dot x=(1-x)/\tau_{rec}$. For $n$ arrivals of the same source at one timestamp (a Poisson fiber may deliver more than one), apply

$$
x^-=1-(1-x_{\rm old})e^{-h/\tau_{rec}},\qquad
x^+=x^-(1-U)^n,\qquad q=x^--x^+,\qquad U=0.35 .
$$

At the initial boundary use zero elapsed time. Full recovery sets $x=1$. The unavailable pool gains exactly $q$, so the sum of the two pools remains one. Two thalamic projections sharing a fiber receive the same release amplitude. Two SP projections sharing a source similarly share release. This is a reduced, depressing-only resource model, with instantaneous release and a separate postsynaptic conductance decay. It omits facilitation and a finite active-resource state. Projection-specific vesicle pools would require an additional modeling assumption. [Tsodyks & Markram (1997)](https://doi.org/10.1073/pnas.94.2.719)

On a fixed excitatory contact the conductance jump is $B_{ji}q/U$. On a plastic one it is $B_{ji}w_{ji}q/U$. One fully recovered isolated event with $n=1$ therefore delivers $B_{ji}$ or $B_{ji}w_{ji}$. With depression disabled, replace $q$ by $nU$. This control preserves the isolated-event conductance while removing history dependence. Global `std=False` applies it to both source populations. `thalamic_std=False` removes depression on both thalamic projections and `subplate_std=False` removes depression on both SP projections independently. Inhibitory conductance increments by its own fixed matrix column per delivered interneuron spike.

## Direct-pathway learning

At each extant thalamus→L4 contact, two all-to-all traces accumulate the number of earlier presynaptic arrivals on its fiber and earlier postsynaptic spikes from its L4 cell. Both trace constants are 20 ms. For concurrent multiplicities $n_i,n_j$, first decay the traces $P_i,Q_j$ to the event time, then update from the old weight.

$$
w^+_{ji}=\operatorname{clip}_{[0,1]}\!\left[
w^-_{ji}+A_+(1-w^-_{ji})P_i n_j-A_-w^-_{ji}Q_j n_i\right].
$$

Finally set $P_i\leftarrow P_i+n_i$ and $Q_j\leftarrow Q_j+n_j$. The default amplitudes are $A_+=0.004$ and $A_-=0.0044$. Exact ties carry no pairwise contribution with each other. They may interact with earlier events. Presynaptic events enter the learning rule once even when their released fraction is small. This release-independent pairing is an assumption about induction. The chosen rule separates soft distance-to-bound factors from the weakly larger LTD coefficient. Hard clipping handles large trace updates. Only the efficacy multiplier on each direct contact is plastic. Absent contacts stay absent. A zero direct gain disconnects transmission. Internal efficacies on such contacts have no measured synaptic effect. [Bi & Poo (1998)](https://doi.org/10.1523/JNEUROSCI.18-24-10464.1998) · [van Rossum et al. (2000)](https://doi.org/10.1523/JNEUROSCI.20-23-08812.2000)

The reported dimensionless efficacy is the arithmetic mean of $w$ on extant contacts from a named class. A group lacking any structural contact would have an undefined mean (NaN). The effective first-event conductance uses $B_{ji}w_{ji}$. A weight measured before/after training describes a change within one network and one stage. Direct-stage comparisons of transmission must include $B$.

## Stimulus, timing and implementation

After 100 ms of background, present 50-ms tokens every 300 ms. Four independent Poisson fibers of the active class receive 50 Hz of additional drive each during a tone. All 40 fibers independently receive 0.2 Hz throughout. Inactive classes have only background. Stimulus generation samples the count and uniformly distributes the event times within their interval, assigning independent uniform fiber identities. This gives independent Poisson processes by thinning. Sharing realized fibers across cells and through branching creates structured correlations downstream. Initial conditions are quiescent cells, zero traces and conductances, and fully available synaptic resources.

A random permutation selects exactly 10% rare-token slots per 100-token oddball block. Token roles exchange between IDs 0 and 5 on reversal. The matched many-standards control keeps every rare slot, fills the other slots with equal counts of the other nine identities and replays the rare input events and background. Frequency identities of distractors differ, so their effects on overlapping receptive fields can differ. The balanced protocol allocates half the slots to each test identity (the extra slot goes to the designated standard if the length is odd). The silent protocol removes the background and the extra drive. Single-tone probes may supply a separate held-out stimulus seed and a trained initial matrix.

Independent SeedSequence streams determine anatomy/thresholds and drive. Schedule, burst times and background have separate child streams. Seed pairing across stage, ablation, and step size reproduces the same continuous drive. Changing the input rate preserves the token sequence but draws a different count of events, so paired rate sweeps share schedules rather than literal spike lists. At each grid boundary $t_k$, the simulation performs the following updates.

1. Receive external events at the first boundary at or after their continuous time. Deliver delayed cortical events and recover and release resources at that boundary.
2. Add conductance using weights in force just before the events. Update direct weights using surviving traces and cortical spikes emitted at this boundary. Then increment the traces.
3. Record any scheduled boundary snapshot. Conductance evolution and the exponential midpoint voltage step determine threshold crossings at the next boundary.

Python handles configuration, topography, analysis and replay. The ISO C99 kernel implements the sequential time axis and short fan-out loops in float64. A temporary shared library is compiled once per Python process. The package requires a C99 compiler available as `cc` or set through `CC`. No native binary is distributed. Arrays for dense binned input multiplicities and cortical spike flags scale linearly with run duration. Dense contact matrices are small at the chosen population sizes. The model records spike IDs/times and per-class weight trajectories at the end of each token period. All diagnostic primitives and the production simulation use the same C implementations. The tests also compare these paths with independent analytical or event-list calculations.
