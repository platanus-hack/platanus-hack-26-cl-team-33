"""simulate() honours the frozen SimulationResult contract for all four scenarios."""
from pathlib import Path

import pytest

from bedflow.contracts import SimulateRequest, SimulationResult
from bedflow.sim import simulate
from sim_helpers import SCENARIOS, make_config

FIXTURES = next(
    (parent / "fixtures" for parent in Path(__file__).resolve().parents
     if (parent / "fixtures" / "simulate_request.json").exists()),
    Path.cwd() / "fixtures",
)


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_result_matches_contract(scenario):
    config = make_config(**SCENARIOS[scenario])
    result = simulate(config, 101)
    SimulationResult.model_validate(result.model_dump())
    assert result.schema_version == "1.0"
    assert result.scenario_id == "custom"
    assert result.seed == 101

    minutes = [s.minute for s in result.timeline]
    w0 = config.warmup_h * 60
    w1 = w0 + config.measurement_h * 60
    step = config.snapshot_every_min
    assert minutes == [w0 + k * step for k in range(len(minutes))]
    assert minutes[-1] < w1 <= minutes[-1] + step
    for s in result.timeline:
        assert s.ed_treatment + s.ed_boarding <= config.ed_spaces
        assert s.ward_occupied + s.ward_turnover + s.ward_ready == config.ward_beds

    m = result.metrics
    assert m.admitted_within_12h_count <= m.eligible_admissions
    assert 0 <= m.avg_ed_bay_utilization_pct <= 100
    assert 0 <= m.avg_ward_occupancy_pct <= 100
    assert max(s.ed_boarding for s in result.timeline) <= m.max_ed_boarding <= config.ed_spaces


def test_canonical_fixture_request_runs():
    request = SimulateRequest.model_validate_json((FIXTURES / "simulate_request.json").read_text())
    result = simulate(request.config, request.seed)
    labelled = result.model_copy(update={"scenario_id": request.scenario_id})
    assert labelled.scenario_id == request.scenario_id
    SimulationResult.model_validate_json(labelled.model_dump_json())


def test_rejects_negative_seed(base_config):
    with pytest.raises(ValueError):
        simulate(base_config, -1)
