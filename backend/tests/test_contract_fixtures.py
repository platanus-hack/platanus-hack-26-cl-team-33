"""Copy to backend/tests/. Verify the fixtures are valid, not clinical truth."""
import json
from pathlib import Path

from bedflow.contracts import (
    CompareRequest, CompareResponse, SimulateRequest, SimulationResult
)

FIXTURES = next(
    (parent / "fixtures" for parent in Path(__file__).resolve().parents
     if (parent / "fixtures" / "simulate_response.json").exists()),
    Path.cwd() / "fixtures",
)


def test_simulate_fixture_contracts():
    req = SimulateRequest.model_validate_json((FIXTURES / "simulate_request.json").read_text())
    res = SimulationResult.model_validate_json((FIXTURES / "simulate_response.json").read_text())
    assert req.config.initial_ward_occupied <= req.config.ward_beds
    assert res.metrics.admitted_within_12h_count <= res.metrics.eligible_admissions
    for s in res.timeline:
        assert s.ed_treatment + s.ed_boarding <= req.config.ed_spaces
        assert s.ward_occupied + s.ward_turnover + s.ward_ready == req.config.ward_beds


def test_compare_fixture_contracts():
    CompareRequest.model_validate_json((FIXTURES / "compare_request.json").read_text())
    res = CompareResponse.model_validate_json((FIXTURES / "compare_response.json").read_text())
    assert len(res.results) == 4
    assert next(v for v in res.results if v.scenario_id == "baseline").paired_delta_12h_pp is None
