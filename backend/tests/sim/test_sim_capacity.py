"""Resource conservation, checked from the event trace and from patient records."""
import pytest

from sim_helpers import make_config, traced_run

CONFIGS = [
    make_config(),
    make_config(arrival_rate_per_hour=6.0, physicians=2, ed_spaces=4, ward_beds=10,
                initial_ward_occupied=10, admission_probability=0.5),
    make_config(ed_spaces=2, physicians=1, measurement_h=48),
]


def _max_concurrent(intervals):
    events = sorted([(s, 1) for s, e in intervals] + [(e, -1) for s, e in intervals],
                    key=lambda x: (x[0], x[1]))  # releases before acquisitions at ties
    cur = peak = 0
    for _, d in events:
        cur += d
        peak = max(peak, cur)
    return peak


@pytest.mark.parametrize("config", CONFIGS)
def test_trace_invariants(config):
    run = traced_run(config, 21)
    for _, c in run.trace:
        assert all(v >= 0 for v in c.values())
        assert c["ed_treatment"] + c["ed_boarding"] <= config.ed_spaces
        assert c["physicians_busy"] <= config.physicians
        assert c["ward_occupied"] + c["ward_turnover"] + c["ward_ready"] == config.ward_beds


@pytest.mark.parametrize("config", CONFIGS)
def test_record_intervals_respect_capacity(config):
    run = traced_run(config, 22)
    horizon = run.horizon
    bays = [(p.bay_enter, p.bay_exit if p.bay_exit is not None else horizon)
            for p in run.patients if p.bay_enter is not None]
    docs = [(p.physician_start, p.physician_end if p.physician_end is not None else horizon)
            for p in run.patients if p.physician_start is not None]
    assert _max_concurrent(bays) <= config.ed_spaces
    assert _max_concurrent(docs) <= config.physicians


@pytest.mark.parametrize("config", CONFIGS)
def test_snapshot_invariants(config):
    run = traced_run(config, 23)
    for _, c in run.snapshots:
        assert c["ed_treatment"] + c["ed_boarding"] <= config.ed_spaces
        assert c["ward_occupied"] + c["ward_turnover"] + c["ward_ready"] == config.ward_beds
        assert min(c.values()) >= 0


def test_no_bed_double_allocation():
    config = CONFIGS[1]
    run = traced_run(config, 24)
    by_bed: dict[int, list] = {}
    for stay in run.bed_stays:
        by_bed.setdefault(stay.bed_id, []).append(stay)
    assert set(by_bed) <= set(range(config.ward_beds))
    for stays in by_bed.values():
        stays.sort(key=lambda s: s.start)
        for prev, nxt in zip(stays, stays[1:]):
            assert prev.ready is not None and prev.ready <= nxt.start
