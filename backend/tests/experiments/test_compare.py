import math
import statistics

import pytest
from conftest import fake_pct, fake_result

from bedflow.contracts import ScenarioVariant, SimulationConfig, SimulationMetrics
from bedflow.experiments.compare import ExperimentError, apply_overrides, compare

SEEDS = [0, 1, 2, 3]


def _variants(scenarios):
    return [ScenarioVariant.model_validate(s) for s in scenarios]


def _by_id(response):
    return {r.scenario_id: r for r in response.results}


def test_baseline_stats_and_ci(base_config, scenarios):
    cfg = SimulationConfig.model_validate(base_config)
    res = compare(cfg, _variants(scenarios), SEEDS, fake_result)
    base = _by_id(res)["baseline"]
    values = [fake_pct(cfg, s) for s in SEEDS]
    half = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    assert base.paired_delta_12h_pp is None
    assert base.summary.admitted_within_12h_pct.mean == pytest.approx(statistics.mean(values))
    assert base.summary.admitted_within_12h_pct.ci95_low == pytest.approx(
        statistics.mean(values) - half)
    assert base.summary.admitted_within_12h_pct.ci95_high == pytest.approx(
        statistics.mean(values) + half)
    assert res.seeds == SEEDS


def test_paired_deltas_in_percentage_points(base_config, scenarios):
    cfg = SimulationConfig.model_validate(base_config)
    out = _by_id(compare(cfg, _variants(scenarios), SEEDS, fake_result))
    # more_physicians delta per seed = 2 * (1 + seed % 2) -> [2, 4, 2, 4]
    d = out["more_physicians"].paired_delta_12h_pp
    assert d.mean == pytest.approx(3.0)
    half = 1.96 * statistics.stdev([2, 4, 2, 4]) / 2
    assert d.ci95_low == pytest.approx(3.0 - half)
    assert d.ci95_high == pytest.approx(3.0 + half)
    # constant deltas -> zero-width interval
    assert out["faster_turnover"].paired_delta_12h_pp.mean == pytest.approx(3.0)
    beds = out["more_ward_beds"].paired_delta_12h_pp
    assert beds.mean == beds.ci95_low == beds.ci95_high == pytest.approx(2.0)


def test_same_seeds_used_for_every_scenario(base_config, scenarios):
    calls = []

    def spy(config, seed):
        calls.append((config.physicians, config.ward_beds, config.bed_turnover_min, seed))
        return fake_result(config, seed)

    compare(SimulationConfig.model_validate(base_config), _variants(scenarios), SEEDS, spy)
    assert len(calls) == 4 * len(SEEDS)
    for seed in SEEDS:
        assert sum(1 for c in calls if c[3] == seed) == 4


def test_null_seeds_are_dropped(base_config, scenarios):
    def sparse(config, seed):
        result = fake_result(config, seed)
        if seed == 0:
            result.metrics = SimulationMetrics(
                eligible_admissions=0, admitted_within_12h_count=0,
                admitted_within_12h_pct=None, mean_wait_to_bed_capped_12h_min=None,
                p90_wait_to_bed_capped_12h_min=None, avg_ed_bay_utilization_pct=70.0,
                avg_ward_occupancy_pct=90.0, max_ed_boarding=0, ed_arrivals_measured=0)
        return result

    cfg = SimulationConfig.model_validate(base_config)
    out = _by_id(compare(cfg, _variants(scenarios), SEEDS, sparse))
    expected = [fake_pct(cfg, s) for s in SEEDS if s != 0]
    assert out["baseline"].summary.admitted_within_12h_pct.mean == pytest.approx(
        statistics.mean(expected))


def test_all_seeds_null_raises(base_config, scenarios):
    def empty(config, seed):
        result = fake_result(config, seed)
        result.metrics = SimulationMetrics(
            eligible_admissions=0, admitted_within_12h_count=0, admitted_within_12h_pct=None,
            mean_wait_to_bed_capped_12h_min=None, p90_wait_to_bed_capped_12h_min=None,
            avg_ed_bay_utilization_pct=0.0, avg_ward_occupancy_pct=0.0, max_ed_boarding=0,
            ed_arrivals_measured=0)
        return result

    with pytest.raises(ExperimentError):
        compare(SimulationConfig.model_validate(base_config), _variants(scenarios), SEEDS, empty)


def test_non_finite_value_rejected(base_config, scenarios):
    def bad(config, seed):
        result = fake_result(config, seed)
        result.metrics = SimulationMetrics.model_construct(
            **{**result.metrics.model_dump(), "avg_ed_bay_utilization_pct": math.nan})
        return result

    with pytest.raises(ExperimentError, match="non-finite"):
        compare(SimulationConfig.model_validate(base_config), _variants(scenarios), SEEDS, bad)


def test_rejects_bad_experiment_definitions(base_config, scenarios):
    cfg = SimulationConfig.model_validate(base_config)
    variants = _variants(scenarios)
    with pytest.raises(ExperimentError, match="seed"):
        compare(cfg, variants, [], fake_result)
    with pytest.raises(ExperimentError, match="seed"):
        compare(cfg, variants, [1, 1], fake_result)
    with pytest.raises(ExperimentError, match="baseline"):
        compare(cfg, variants[1:], SEEDS, fake_result)
    with pytest.raises(ExperimentError, match="duplicate"):
        compare(cfg, variants + [variants[1]], SEEDS, fake_result)


def test_apply_overrides_whitelist_and_validation(base_config):
    cfg = SimulationConfig.model_validate(base_config)
    assert apply_overrides(cfg, {"physicians": 6}).physicians == 6
    assert apply_overrides(cfg, {}) == cfg
    with pytest.raises(ExperimentError, match="not allowed"):
        apply_overrides(cfg, {"arrival_rate_per_hour": 9.0})
    with pytest.raises(ExperimentError, match="finite"):
        apply_overrides(cfg, {"bed_turnover_min": math.inf})
    with pytest.raises(ExperimentError, match="invalid configuration"):
        apply_overrides(cfg, {"ward_beds": 20})  # initial occupied 21 > 20
