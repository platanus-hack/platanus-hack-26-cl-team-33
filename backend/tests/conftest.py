"""Shared test helpers.

``fake_simulate`` is a TEST-ONLY deterministic stand-in for the engine with
hand-checkable outputs. It is never served as a result by the application.
"""
import pytest

from bedflow.contracts import SimulationConfig, SimulationMetrics, SimulationResult

BASE_CONFIG = {
    "arrival_rate_per_hour": 3.0, "physicians": 4, "ed_spaces": 8, "ward_beds": 24,
    "initial_ward_occupied": 21, "admission_probability": 0.20,
    "mean_physician_service_min": 35.0, "mean_inpatient_los_h": 36.0,
    "bed_turnover_min": 120.0, "warmup_h": 72, "measurement_h": 168, "followup_h": 12,
    "snapshot_every_min": 15,
}

SCENARIOS = [
    {"scenario_id": "baseline", "label": "Baseline", "overrides": {}},
    {"scenario_id": "more_physicians", "label": "More physicians", "overrides": {"physicians": 6}},
    {"scenario_id": "faster_turnover", "label": "Faster bed turnover",
     "overrides": {"bed_turnover_min": 30.0}},
    {"scenario_id": "more_ward_beds", "label": "More staffed ward beds",
     "overrides": {"ward_beds": 28}},
]


def fake_pct(config: SimulationConfig, seed: int) -> float:
    return (
        60 + 2 * (seed % 3) + (config.physicians - 4) * (1 + seed % 2)
        + 0.5 * (config.ward_beds - 24) + (120 - config.bed_turnover_min) / 30
    )


def fake_result(config: SimulationConfig, seed: int) -> SimulationResult:
    pct = fake_pct(config, seed)
    metrics = SimulationMetrics(
        eligible_admissions=100,
        admitted_within_12h_count=int(pct),
        admitted_within_12h_pct=pct,
        mean_wait_to_bed_capped_12h_min=300 - pct,
        p90_wait_to_bed_capped_12h_min=600.0,
        avg_ed_bay_utilization_pct=70.0 + seed % 2,
        avg_ward_occupancy_pct=90.0,
        max_ed_boarding=3,
        ed_arrivals_measured=500,
    )
    return SimulationResult(
        scenario_id="custom", seed=seed, metrics=metrics, timeline=[], patient_examples=[]
    )


@pytest.fixture
def base_config() -> dict:
    return dict(BASE_CONFIG)


@pytest.fixture
def scenarios() -> list[dict]:
    return [dict(s, overrides=dict(s["overrides"])) for s in SCENARIOS]
