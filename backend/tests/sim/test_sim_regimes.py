"""Low vs high demand behaviour, edge configs, and a loose speed bound."""
import time

from sim_helpers import make_config

from bedflow.sim import simulate


def test_low_demand_admits_nearly_everyone():
    config = make_config(arrival_rate_per_hour=0.5, ward_beds=40, initial_ward_occupied=5)
    m = simulate(config, 1).metrics
    assert m.eligible_admissions > 0
    assert m.admitted_within_12h_pct >= 95
    assert m.max_ed_boarding <= 2


def test_starved_ward_fails_target():
    m = simulate(make_config(ward_beds=4, initial_ward_occupied=4, mean_inpatient_los_h=120.0,
                             admission_probability=0.3), 1).metrics
    assert m.admitted_within_12h_pct < 50
    assert m.avg_ward_occupancy_pct > 80


def test_more_demand_raises_bay_utilization():
    low = simulate(make_config(arrival_rate_per_hour=1.0), 2).metrics
    high = simulate(make_config(arrival_rate_per_hour=5.0), 2).metrics
    assert high.avg_ed_bay_utilization_pct > low.avg_ed_bay_utilization_pct


def test_no_admissions_gives_null_target_metrics():
    m = simulate(make_config(admission_probability=0.0), 3).metrics
    assert m.eligible_admissions == 0 and m.admitted_within_12h_count == 0
    assert m.admitted_within_12h_pct is None
    assert m.mean_wait_to_bed_capped_12h_min is None
    assert m.p90_wait_to_bed_capped_12h_min is None
    assert m.max_ed_boarding == 0


def test_edge_configs_run():
    simulate(make_config(warmup_h=0), 4)
    simulate(make_config(bed_turnover_min=0.0), 4)
    simulate(make_config(initial_ward_occupied=0), 4)
    simulate(make_config(initial_ward_occupied=24), 4)


def test_baseline_is_fast():
    config = make_config()
    simulate(config, 0)  # warm caches
    started = time.perf_counter()
    simulate(config, 1)
    assert time.perf_counter() - started < 5.0
