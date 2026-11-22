"""Pre-generated synthetic cohort (exogenous inputs), independent of policy.

Every random quantity in a run is drawn here, before the SimPy model starts, so
the arrivals and per-patient attributes are identical across policy variants
that share a seed (common random numbers). Nothing in this module reads
physicians, ed_spaces, ward_beds or bed_turnover_min.

Each attribute has its own NumPy stream spawned from ``SeedSequence(seed)``.
Streams draw *standard* variates in fixed-size chunks and are then scaled by the
config, so patient ``i`` keeps the same underlying draw even when the arrival
rate (and therefore the cohort size) or a mean parameter changes.

Synthetic assumptions (fictional, uncalibrated; see spec/PROJECT_SPEC.md):
- arrivals: homogeneous Poisson at ``arrival_rate_per_hour``;
- admission indication: Bernoulli(``admission_probability``) per patient;
- physician service: Gamma(shape=3, scale=mean/3);
- inpatient length of stay: lognormal with the configured mean and CV 0.7;
- residual stay of initial ward occupants: exponential with mean LOS.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from bedflow.contracts import SimulationConfig

LOS_CV = 0.7
PHYSICIAN_GAMMA_SHAPE = 3.0
_CHUNK = 256
_STREAMS = ("arrivals", "admit", "service", "los", "initial_residual")


@dataclass(frozen=True)
class Cohort:
    """Exogenous inputs for one seed. All times in simulated minutes."""

    arrival_min: np.ndarray  # sorted arrival times in [0, horizon)
    admit: np.ndarray  # bool: hospitalization indicated after physician care
    service_min: np.ndarray  # physician treatment duration
    los_min: np.ndarray  # inpatient stay if admitted (drawn for everyone)
    initial_residual_min: np.ndarray  # residual stay of initial ward occupants

    @property
    def n_patients(self) -> int:
        return int(self.arrival_min.shape[0])


def horizon_min(config: SimulationConfig) -> float:
    """End of the simulated run: warm-up + measurement + follow-up."""
    return float((config.warmup_h + config.measurement_h + config.followup_h) * 60)


def measurement_window(config: SimulationConfig) -> tuple[float, float]:
    """Half-open evaluation window ``[warmup_end, measurement_end)`` in minutes."""
    start = float(config.warmup_h * 60)
    return start, start + float(config.measurement_h * 60)


def _chunked(rng: np.random.Generator, n: int,
             draw: Callable[[np.random.Generator, int], np.ndarray]) -> np.ndarray:
    """Draw ``n`` variates in fixed-size chunks so prefixes are stable in ``n``."""
    if n <= 0:
        return np.empty(0, dtype=float)
    chunks = -(-n // _CHUNK)
    return np.concatenate([draw(rng, _CHUNK) for _ in range(chunks)])[:n]


def _arrival_times(rng: np.random.Generator, mean_gap_min: float, horizon: float) -> np.ndarray:
    out: list[np.ndarray] = []
    t = 0.0
    while True:
        cum = t + np.cumsum(rng.standard_exponential(_CHUNK) * mean_gap_min)
        inside = cum[cum < horizon]
        out.append(inside)
        if inside.shape[0] < _CHUNK:
            return np.concatenate(out)
        t = float(cum[-1])


def generate_cohort(config: SimulationConfig, seed: int) -> Cohort:
    rng_arrivals, rng_admit, rng_service, rng_los, rng_initial = (
        np.random.default_rng(s)
        for s in np.random.SeedSequence(seed).spawn(len(_STREAMS))
    )

    arrivals = _arrival_times(
        rng_arrivals, 60.0 / config.arrival_rate_per_hour, horizon_min(config)
    )
    n = int(arrivals.shape[0])

    admit_u = _chunked(rng_admit, n, lambda r, s: r.random(s))
    service = _chunked(
        rng_service, n, lambda r, s: r.standard_gamma(PHYSICIAN_GAMMA_SHAPE, s)
    ) * (config.mean_physician_service_min / PHYSICIAN_GAMMA_SHAPE)

    sigma2 = math.log1p(LOS_CV**2)
    mu = math.log(config.mean_inpatient_los_h * 60.0) - sigma2 / 2.0
    los = np.exp(mu + math.sqrt(sigma2) * _chunked(rng_los, n, lambda r, s: r.standard_normal(s)))

    initial = _chunked(
        rng_initial, config.initial_ward_occupied, lambda r, s: r.standard_exponential(s)
    ) * (config.mean_inpatient_los_h * 60.0)

    return Cohort(
        arrival_min=arrivals,
        admit=admit_u < config.admission_probability,
        service_min=service,
        los_min=los,
        initial_residual_min=initial,
    )
