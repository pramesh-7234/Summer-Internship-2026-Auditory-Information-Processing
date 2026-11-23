"""Feedforward auditory network with reproducible afferent events and explicit units."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import ctypes as ct
import os
import shlex
import subprocess
import sys
import tempfile

import numpy as np


@dataclass(frozen=True)
class Config:
    """All times in ms, voltages in mV, rates in Hz, conductances in leak units."""
    dt: float = 0.5
    input_rate: float = 50.0
    background_rate: float = 0.2
    sp_scale: float = 8.0
    direct_scale: float = 6.4
    inhibition_scale: float = 5.0
    tau_rec: float = 650.0
    threshold_shift: float = 0.0
    sp_threshold_shift: float = 0.0
    l4_threshold_shift: float = 0.0
    learning_scale: float = 1.0
    ltp_amplitude: float = 0.004
    ltd_amplitude: float = 0.0044
    width: float = 0.09
    stdp: bool = True
    std: bool = True
    thalamic_std: bool = True
    subplate_std: bool = True
    utilization: float = 0.35
    initial_resource: float = 1.0
    initial_voltage: float = -65.0

    @classmethod
    def for_regime(cls, regime):
        if regime == "early":
            return cls()
        if regime == "late":
            return cls(sp_scale=3.2, direct_scale=16.0, tau_rec=350.0)
        raise ValueError("regime must be 'early' or 'late'")

    def validate(self):
        values = [value for value in vars(self).values() if not isinstance(value, bool)]
        if not np.isfinite(values).all():
            raise ValueError("configuration values must be finite")
        if not 0 < self.dt <= 1 or not np.isclose(round(1/self.dt)*self.dt, 1, rtol=0, atol=1e-12):
            raise ValueError("dt must divide the 1 ms axonal delay")
        if self.tau_rec <= 0 or self.width <= 0 or not 0 < self.utilization <= 1:
            raise ValueError("invalid time constant, tuning width or utilization")
        if min(self.input_rate, self.background_rate, self.sp_scale, self.direct_scale,
               self.inhibition_scale, self.learning_scale, self.ltp_amplitude,
               self.ltd_amplitude) < 0 or not 0 <= self.initial_resource <= 1:
            raise ValueError("negative rate/gain or invalid initial resource")


@dataclass(frozen=True)
class Stimulus:
    tones: np.ndarray
    onsets: np.ndarray
    input_times: np.ndarray
    input_cells: np.ndarray
    standard: int
    deviant: int
    duration: float


def make_stimulus(cfg, seed, n_tokens=100, protocol="oddball", swap=False):
    """Construct continuous Poisson arrivals before selecting any integration grid.

    The two oddball roles use opposite points on a 10-class tuning circle.
    In the many-standards control the designated target has the very same
    positions, four-fiber bursts and background as in the oddball condition.
    """
    cfg.validate()
    if not isinstance(n_tokens, (int, np.integer)) or n_tokens < 1:
        raise ValueError("n_tokens must be a positive integer")
    if protocol not in {"oddball", "many", "balanced", "silent", "probe"}:
        raise ValueError(f"unknown protocol: {protocol}")
    if protocol in {"oddball", "many"} and n_tokens % 10:
        raise ValueError("exact 9:1 or 1:1:...:1 allocation needs a multiple of ten tokens")
    schedule, burst_stream, background = np.random.SeedSequence([seed, 3301]).spawn(3)
    rng = np.random.default_rng(schedule)
    standard, deviant = (5, 0) if swap else (0, 5)
    tones = np.full(n_tokens, standard, dtype=np.int32)
    order = rng.permutation(n_tokens)
    if protocol in {"oddball", "many"}:
        rare_count = n_tokens // 10
        tones[order[:rare_count]] = deviant
        if protocol == "many":
            other_tones = np.delete(np.arange(10), deviant)
            tones[order[rare_count:]] = np.repeat(other_tones, rare_count)
    elif protocol == "balanced":
        tones[order[:n_tokens//2]] = deviant
    elif protocol == "silent":
        tones.fill(-1)
    onsets = 100.0 + 300.0*np.arange(n_tokens)
    duration = 100.0 + 300.0*n_tokens
    if protocol == "silent":
        return Stimulus(tones, onsets, np.empty(0), np.empty(0, dtype=np.int32),
                        standard, deviant, duration)
    # Superposing four independent equal-rate processes is equivalent to one
    # Poisson process with independent uniform fiber marks (Poisson splitting).
    bg = np.random.default_rng(background)
    n_bg = bg.poisson(cfg.background_rate*40*duration/1000)
    times = [bg.uniform(0, duration, size=n_bg)]
    cells = [bg.integers(0, 40, n_bg, dtype=np.int32)]
    bursts = np.random.default_rng(burst_stream)
    for tone, onset in zip(tones, onsets):
        n_events = bursts.poisson(4*cfg.input_rate*0.050)
        times.append(onset + bursts.uniform(0, 50, size=n_events))
        cells.append(4*tone + bursts.integers(0, 4, n_events, dtype=np.int32))
    times, cells = np.concatenate(times), np.concatenate(cells)
    sort = np.argsort(times, kind="stable")
    return Stimulus(tones, onsets, times[sort], cells[sort], standard, deviant, duration)


def _topography(rng, post, pre, width, gain):
    distance = np.abs(post[:, None]-pre)
    distance = np.minimum(distance, 1.0-distance)
    local = (distance <= 2.5*width) & (rng.random(distance.shape) < 0.85)
    for row in np.flatnonzero(~local.any(axis=1)):
        local[row, distance[row].argmin()] = True
    with np.errstate(over="ignore"):
        matrix = local*np.exp(-0.5*(distance/width)**2)*rng.uniform(0.85, 1.15, distance.shape)
    # With extremely narrow Gaussians an entire row can underflow. Its nearest
    # eligible source has unit relative strength in that single-input limit.
    empty = np.flatnonzero(matrix.sum(axis=1) == 0)
    if len(empty):
        nearest = np.where(local[empty], distance[empty], np.inf).argmin(axis=1)
        matrix[empty, nearest] = 1.0
    return gain*matrix/matrix.sum(axis=1, keepdims=True)


def _wiring(cfg, seed):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 2107]))
    tc = np.repeat(np.arange(10)/10, 4)
    sp = l4 = np.arange(40)/40
    interneuron = np.arange(10)/10
    ts = _topography(rng, sp, tc, cfg.width, 8.0)
    template = _topography(rng, l4, tc, cfg.width, 1.0)
    sl = _topography(rng, l4, sp, cfg.width, cfg.sp_scale)
    si = _topography(rng, interneuron, sp, 0.12, 9.0)
    il = _topography(rng, l4, interneuron, 0.16, cfg.inhibition_scale)
    weights = np.where(template > 0, rng.uniform(0.45, 0.55, (40,40)), 0.0)
    threshold = -52.0 + cfg.threshold_shift + rng.normal(0, 1.0, 90)
    threshold[:40] += cfg.sp_threshold_shift
    threshold[50:] += cfg.l4_threshold_shift
    return ts, template*cfg.direct_scale, sl, si, il, weights, threshold, template > 0


class _Parameters(ct.Structure):
    _fields_ = [(name, ct.c_double) for name in (
        "dt", "tau_rec", "U", "a_plus", "a_minus", "initial_resource", "initial_voltage"
    )] + [(name, ct.c_int32) for name in ("thalamic_std", "subplate_std", "use_stdp")]


@lru_cache(maxsize=1)
def _library():
    """Compile bundled ISO C99 into a temporary file once per Python process."""
    build = tempfile.TemporaryDirectory(prefix="auditory-kernel-")
    libname = Path(build.name)/"kernel.so"
    compiler = shlex.split(os.environ.get("CC", "cc"))
    flag = "-dynamiclib" if sys.platform == "darwin" else "-shared"
    cmd = [*compiler, "-O3", "-std=c99", "-fPIC", flag, str(Path(__file__).with_name("kernel.c")),
           "-o", str(libname), "-lm"]
    subprocess.run(cmd, check=True)
    lib = ct.CDLL(str(libname))
    lib._build_dir = build
    d = ct.c_double
    lib.membrane_step.argtypes = [d]*5
    lib.membrane_step.restype = d
    lib.release_step.argtypes = [ct.POINTER(d), ct.c_int, d, d, d, ct.c_int]
    lib.release_step.restype = d
    lib.plastic_step.argtypes = [d, d, d, ct.c_int, ct.c_int, d, d]
    lib.plastic_step.restype = d
    f64 = np.ctypeslib.ndpointer(np.float64, flags="C_CONTIGUOUS")
    i32 = np.ctypeslib.ndpointer(np.int32, flags="C_CONTIGUOUS")
    u8 = np.ctypeslib.ndpointer(np.uint8, flags="C_CONTIGUOUS")
    lib.simulate_network.argtypes = [ct.POINTER(_Parameters), ct.c_int, i32,
                                     *([f64]*7), u8, ct.c_int, i32, f64]
    lib.simulate_network.restype = None
    return lib


def membrane_step(v, ge, gi, dt, tau_m=20.0):
    """Exact scalar LIF update for constant leak-normalized conductances."""
    return _library().membrane_step(v, ge, gi, dt, tau_m)


def release_step(x, n, U, dt, tau_rec, depression=True):
    """Recover for dt then apply n arrivals. Return (available, fraction released)."""
    value = ct.c_double(x)
    released = _library().release_step(ct.byref(value), n, U, dt, tau_rec, depression)
    return value.value, released


def plastic_step(w, pretrace, posttrace, npre, npost, a_plus, a_minus):
    """Update one existing contact from old decayed traces, before adding new events."""
    return _library().plastic_step(w, pretrace, posttrace, npre, npost, a_plus, a_minus)


@dataclass(frozen=True)
class Result:
    tones: np.ndarray
    onsets: np.ndarray
    standard: int
    deviant: int
    duration: float
    times: np.ndarray
    cells: np.ndarray
    weight_times: np.ndarray
    weight_history: np.ndarray
    initial_weights: np.ndarray
    final_weights: np.ndarray
    mask: np.ndarray
    direct_base: np.ndarray
    max_weight: float = 1.0


def simulate(cfg, seed=1, n_tokens=100, protocol="oddball", swap=False, *,
             stimulus=None, initial_weights=None):
    """Run one independent reset, optionally replaying supplied drive and learned weights.

    A network seed determines structural wiring and intrinsic thresholds. A supplied
    Stimulus can carry a different input seed. Spike times are right-boundary times.
    """
    cfg.validate()
    s = make_stimulus(cfg, seed, n_tokens, protocol, swap) if stimulus is None else stimulus
    if not np.isscalar(s.duration) or not np.isfinite(s.duration) or s.duration <= 0:
        raise ValueError("stimulus duration must be positive and finite")
    n_steps = round(s.duration/cfg.dt)
    if n_steps < 1 or n_steps >= np.iinfo(np.int32).max or not np.isclose(
            n_steps*cfg.dt, s.duration, rtol=0, atol=1e-9):
        raise ValueError("stimulus duration must be a positive multiple of dt")
    ts, tl, sl, si, il, initial, threshold, mask = _wiring(cfg, seed)
    if initial_weights is not None:
        initial = np.array(initial_weights, dtype=np.float64, copy=True)
        if (initial.shape != (40, 40) or not np.isfinite(initial).all() or
                (initial[~mask] != 0).any() or (initial < 0).any() or (initial > 1).any()):
            raise ValueError("initial_weights must respect this network's mask and [0,1] bounds")
    weights = np.ascontiguousarray(np.where(mask, initial, -1.0))  # absent sentinel only inside C
    inputs = np.zeros((n_steps+1,40), dtype=np.int32)
    times = np.asarray(s.input_times)
    cells = np.asarray(s.input_cells)
    if (times.shape != cells.shape or times.ndim != 1 or not np.isfinite(times).all()
            or (times < 0).any() or (times > s.duration).any() or (cells < 0).any()
            or (cells >= 40).any() or not np.issubdtype(cells.dtype, np.integer)):
        raise ValueError("invalid afferent events")
    # Compare with the represented grid boundary. Division alone can round
    # an exact k*dt above k, or round an event just after k*dt back to k.
    times = times.astype(np.float64, copy=False)
    nearest = np.rint(times / cfg.dt).astype(np.intp)
    arrivals = np.minimum(nearest + (nearest * cfg.dt < times), n_steps)
    np.add.at(inputs, (arrivals, cells), 1)
    # Snapshot immediately before training, then after each SOA. For the
    # canonical schedules that is 0, 400, 700, ... ms (100-ms preroll).
    onsets = np.asarray(s.onsets, dtype=float)
    tones = np.asarray(s.tones)
    if (tones.ndim != 1 or not np.issubdtype(tones.dtype, np.integer) or
            (tones < -1).any() or (tones > 9).any() or
            s.standard not in range(10) or s.deviant not in range(10) or s.standard == s.deviant):
        raise ValueError("tones and their designated roles need valid class IDs")
    if (onsets.ndim != 1 or len(onsets) != len(tones) or not len(onsets)
            or not np.isfinite(onsets).all() or onsets[0] < 0 or onsets[-1] >= s.duration
            or np.any(np.diff(onsets) < cfg.dt)):
        raise ValueError("onsets must be strictly ordered within the stimulus duration")
    snapshot_steps = np.rint(np.r_[0.0, onsets[1:], s.duration]/cfg.dt).astype(np.int32)
    if np.any(np.diff(snapshot_steps) <= 0):
        raise ValueError("each snapshot must occupy a distinct time-grid boundary")
    history = np.zeros((len(snapshot_steps),10))
    spikes = np.zeros((n_steps+1,90), dtype=np.uint8)
    p = _Parameters(cfg.dt, cfg.tau_rec, cfg.utilization, cfg.ltp_amplitude*cfg.learning_scale,
                    cfg.ltd_amplitude*cfg.learning_scale, cfg.initial_resource, cfg.initial_voltage,
                    cfg.std and cfg.thalamic_std, cfg.std and cfg.subplate_std, cfg.stdp)
    _library().simulate_network(ct.byref(p), n_steps, inputs, ts, tl, sl, si, il,
                                threshold, weights, spikes, len(history), snapshot_steps, history)
    ticks, neurons = np.nonzero(spikes)
    weights[~mask] = 0.0
    return Result(tones, onsets, s.standard, s.deviant, s.duration, ticks*cfg.dt,
                  neurons, snapshot_steps*cfg.dt, history, initial, weights, mask, tl)
