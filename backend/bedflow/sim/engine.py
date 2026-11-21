"""Public entry point for Person C: ``simulate(config, seed) -> SimulationResult``."""
from __future__ import annotations

from bedflow.contracts import SimulationConfig, SimulationResult, TimelineSnapshot
from bedflow.sim.cohort import generate_cohort
from bedflow.sim.journeys import select_patient_examples
from bedflow.sim.metrics import compute_metrics
from bedflow.sim.model import run_model

_SNAPSHOT_FIELDS = (
    "ed_waiting", "ed_treatment", "ed_boarding",
    "ward_occupied", "ward_turnover", "ward_ready",
)


def simulate(config: SimulationConfig, seed: int) -> SimulationResult:
    """One complete reproducible simulated run, no file or network side effects.

    Returns ``scenario_id="custom"``; the API sets the external scenario label
    with ``model_copy(update={"scenario_id": ...})``.
    """
    if not isinstance(config, SimulationConfig):
        config = SimulationConfig.model_validate(config)
    if seed < 0:
        raise ValueError("seed must be a nonnegative integer")

    run = run_model(config, generate_cohort(config, seed))
    timeline = [
        TimelineSnapshot(minute=minute, **{k: counts[k] for k in _SNAPSHOT_FIELDS})
        for minute, counts in run.snapshots
    ]
    return SimulationResult(
        schema_version="1.0",
        scenario_id="custom",
        seed=int(seed),
        metrics=compute_metrics(run),
        timeline=timeline,
        patient_examples=select_patient_examples(run),
    )
