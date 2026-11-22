"""Boarding holds the ED bay but releases the physician; beds free only via turnover."""
from sim_helpers import make_config, traced_run


def test_full_ward_waits_for_real_turnover():
    config = make_config(ward_beds=1, initial_ward_occupied=1, admission_probability=1.0,
                         arrival_rate_per_hour=1.0, warmup_h=0, measurement_h=48)
    run = traced_run(config, 3)
    initial = next(s for s in run.bed_stays if s.patient_id is None)
    admitted = [p for p in run.patients if p.ward_admitted is not None]
    assert admitted, "expected at least one admission within the horizon"
    first = min(admitted, key=lambda p: p.ward_admitted)
    assert initial.ready is not None
    assert initial.ready == initial.discharged + config.bed_turnover_min
    assert first.ward_admitted >= initial.ready
    # Every admission coincides with or follows a BED_READY of the same bed.
    ready_times = sorted(s.ready for s in run.bed_stays if s.ready is not None)
    for p in admitted:
        assert any(t <= p.ward_admitted for t in ready_times)


def test_boarder_holds_bay_not_physician():
    config = make_config(ward_beds=1, initial_ward_occupied=1, admission_probability=1.0,
                         physicians=1, ed_spaces=2, mean_inpatient_los_h=200.0,
                         warmup_h=0, measurement_h=24)
    run = traced_run(config, 4)
    boarders = [p for p in run.patients if p.indicated is not None]
    assert len(boarders) >= 2
    first = boarders[0]
    board_end = first.ward_admitted if first.ward_admitted is not None else run.horizon
    # The physician is free while patient 0 boards: someone else starts care then.
    assert any(first.indicated <= p.physician_start < board_end
               for p in run.patients if p.physician_start is not None and p is not first)
    # Boarders block bays: at some point both bays hold boarders and people wait.
    assert any(c["ed_boarding"] == 2 and c["ed_waiting"] > 0 for _, c in run.trace)
    # Boarding patients are never counted in treatment.
    for _, c in run.trace:
        assert c["ed_treatment"] + c["ed_boarding"] <= 2
