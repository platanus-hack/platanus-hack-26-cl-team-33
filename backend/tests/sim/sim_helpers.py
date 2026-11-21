"""Shared helpers for Person A's simulation tests (unique module name on purpose)."""
from __future__ import annotations

from bedflow.contracts import SimulationConfig
from bedflow.sim.cohort import generate_cohort
from bedflow.sim.model import ModelRun, run_model

BASE = {
    "arrival_rate_per_hour": 3.0,
    "physicians": 4,
    "ed_spaces": 8,
    "ward_beds": 24,
    "initial_ward_occupied": 21,
    "admission_probability": 0.20,
    "mean_physician_service_min": 35.0,
    "mean_inpatient_los_h": 36.0,
    "bed_turnover_min": 120.0,
    "warmup_h": 72,
    "measurement_h": 168,
    "followup_h": 12,
    "snapshot_every_min": 15,
}
SCENARIOS = {
    "baseline": {},
    "more_physicians": {"physicians": 6},
    "faster_turnover": {"bed_turnover_min": 30.0},
    "more_ward_beds": {"ward_beds": 28},
}


def make_config(**overrides) -> SimulationConfig:
    return SimulationConfig(**{**BASE, **overrides})


def traced_run(config: SimulationConfig, seed: int) -> ModelRun:
    return run_model(config, generate_cohort(config, seed), trace=True)
