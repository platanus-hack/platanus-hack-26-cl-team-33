"""End-to-end smoke tests against Person A's real engine.

Skipped until ``bedflow.sim.engine`` exists. No fabricated engine output is used.
"""
import json
from pathlib import Path

import pytest

pytest.importorskip("bedflow.sim.engine")

from fastapi.testclient import TestClient  # noqa: E402

from bedflow.api.app import create_app  # noqa: E402
from bedflow.api.engine_adapter import MODE_REAL, load_engine  # noqa: E402
from bedflow.contracts import CompareResponse, SimulationResult  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app(load_engine("real")))


def _req(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_simulate_real_engine(client):
    r = client.post("/api/v1/simulate", json=_req("simulate_request.json"))
    assert r.status_code == 200
    assert r.headers["X-BedFlow-Mode"] == MODE_REAL
    result = SimulationResult.model_validate(r.json())
    assert result.timeline == sorted(result.timeline, key=lambda s: s.minute)
    cfg = _req("simulate_request.json")["config"]
    for s in result.timeline:
        assert s.ed_treatment + s.ed_boarding <= cfg["ed_spaces"]
        assert s.ward_occupied + s.ward_turnover + s.ward_ready == cfg["ward_beds"]


def test_simulate_is_deterministic(client):
    body = _req("simulate_request.json")
    a = client.post("/api/v1/simulate", json=body).json()
    b = client.post("/api/v1/simulate", json=body).json()
    assert a == b


def test_compare_real_engine(client):
    body = _req("compare_request.json")
    r = client.post("/api/v1/compare", json=body)
    assert r.status_code == 200
    res = CompareResponse.model_validate(r.json())
    assert [x.scenario_id for x in res.results] == [s["scenario_id"] for s in body["scenarios"]]
    assert res.results[0].paired_delta_12h_pp is None


def test_more_ward_beds_keeps_same_arrivals(client):
    """Same seed + exogenous inputs: ward capacity must not change the arrival cohort."""
    base = _req("simulate_request.json")
    more = json.loads(json.dumps(base))
    more["config"]["ward_beds"] = 28
    a = client.post("/api/v1/simulate", json=base).json()
    b = client.post("/api/v1/simulate", json=more).json()
    assert a["metrics"]["ed_arrivals_measured"] == b["metrics"]["ed_arrivals_measured"]
