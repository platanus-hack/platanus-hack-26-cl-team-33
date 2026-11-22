"""Evaluation window, denominator and 720-minute follow-up rules."""
import numpy as np
import pytest

from bedflow.sim.metrics import compute_metrics
from sim_helpers import make_config, traced_run

STARVED = make_config(ward_beds=4, initial_ward_occupied=4, mean_inpatient_los_h=120.0,
                      admission_probability=0.3)


@pytest.mark.parametrize("config", [make_config(), STARVED])
def test_denominator_and_success_recount(config):
    run = traced_run(config, 31)
    m = compute_metrics(run)
    w0, w1 = run.window
    eligible = [p for p in run.patients if p.indicated is not None and w0 <= p.indicated < w1]
    assert m.eligible_admissions == len(eligible)
    assert all(w0 <= p.indicated < w1 for p in eligible)
    assert all(run.horizon - p.indicated >= 720 for p in eligible)

    waits = [p.admission_wait for p in eligible]
    success = sum(1 for w in waits if w is not None and w <= 720)
    capped = [720.0 if w is None else min(w, 720.0) for w in waits]
    assert m.admitted_within_12h_count == success
    assert m.admitted_within_12h_pct == pytest.approx(100 * success / len(eligible))
    assert m.mean_wait_to_bed_capped_12h_min == pytest.approx(np.mean(capped))
    assert m.p90_wait_to_bed_capped_12h_min == pytest.approx(np.percentile(capped, 90))
    assert m.ed_arrivals_measured == sum(1 for p in run.patients if w0 <= p.arrival < w1)


def test_unresolved_indications_count_as_failures():
    run = traced_run(STARVED, 32)
    m = compute_metrics(run)
    w0, w1 = run.window
    unresolved = [p for p in run.patients
                  if p.indicated is not None and w0 <= p.indicated < w1 and p.ward_admitted is None]
    assert unresolved, "starved config should leave indications unresolved at the horizon"
    assert m.eligible_admissions - m.admitted_within_12h_count >= len(unresolved)


def test_arrivals_continue_through_followup():
    run = traced_run(make_config(), 33)
    w1 = run.window[1]
    assert any(w1 <= p.arrival < run.horizon for p in run.patients)
    assert max(p.arrival for p in run.patients) < run.horizon


def test_longer_followup_only_extends_run():
    short = traced_run(make_config(), 34)
    long = traced_run(make_config(followup_h=24), 34)
    assert long.horizon == short.horizon + 12 * 60
    assert compute_metrics(long).eligible_admissions == compute_metrics(short).eligible_admissions
