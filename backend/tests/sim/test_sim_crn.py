"""Common random numbers: policy levers never change the exogenous cohort."""
import numpy as np
import pytest
from sim_helpers import SCENARIOS, make_config, traced_run

from bedflow.sim.cohort import generate_cohort

FIELDS = ("arrival_min", "admit", "service_min", "los_min", "initial_residual_min")


@pytest.mark.parametrize("scenario", ["more_physicians", "faster_turnover", "more_ward_beds"])
def test_policy_overrides_keep_cohort(scenario):
    base = generate_cohort(make_config(), 101)
    variant = generate_cohort(make_config(**SCENARIOS[scenario]), 101)
    for name in FIELDS:
        assert np.array_equal(getattr(base, name), getattr(variant, name)), name


def test_only_turnover_change_keeps_arrivals_and_attributes():
    a = generate_cohort(make_config(bed_turnover_min=120.0), 5)
    b = generate_cohort(make_config(bed_turnover_min=17.0), 5)
    for name in FIELDS:
        assert np.array_equal(getattr(a, name), getattr(b, name)), name


def test_patient_draws_survive_arrival_rate_change():
    slow = generate_cohort(make_config(arrival_rate_per_hour=2.0), 3)
    fast = generate_cohort(make_config(arrival_rate_per_hour=4.0), 3)
    n = min(slow.n_patients, fast.n_patients)
    assert slow.n_patients < fast.n_patients
    assert np.array_equal(slow.admit[:n], fast.admit[:n])
    assert np.array_equal(slow.service_min[:n], fast.service_min[:n])
    assert np.array_equal(slow.los_min[:n], fast.los_min[:n])
    # Same exponential draws, rescaled by the rate.
    assert np.allclose(slow.arrival_min[:n] * 2.0, fast.arrival_min[:n] * 4.0)


def test_simulated_patients_are_stable_across_scenarios():
    runs = {s: traced_run(make_config(**o), 101) for s, o in SCENARIOS.items()}
    base = runs["baseline"]
    for run in runs.values():
        assert [(p.patient_id, p.arrival, p.admit) for p in run.patients] == [
            (p.patient_id, p.arrival, p.admit) for p in base.patients
        ]
    cohort = generate_cohort(make_config(), 101)
    for p in base.patients:
        if p.physician_end is not None:
            service = cohort.service_min[p.patient_id]
            assert p.physician_end - p.physician_start == pytest.approx(service)


def test_more_ward_beds_keeps_initial_occupancy():
    run = traced_run(make_config(ward_beds=28), 9)
    initial = run.trace[0][1]
    assert initial["ward_occupied"] == 21 and initial["ward_ready"] == 7
    assert initial["ward_turnover"] == 0
