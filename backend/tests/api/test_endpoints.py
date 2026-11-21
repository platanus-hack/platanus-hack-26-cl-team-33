import json
from pathlib import Path

import pytest
from conftest import fake_result
from fastapi.testclient import TestClient

from bedflow.api.app import create_app
from bedflow.api.engine_adapter import MODE_REAL, MODE_STUB, Engine, load_engine
from bedflow.contracts import CompareResponse, SimulationResult

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"


def _fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def stub_client():
    return TestClient(create_app(load_engine("stub")))


@pytest.fixture
def real_client():
    # fake engine labeled as "real" to exercise the experiment path; test-only
    return TestClient(create_app(Engine(MODE_REAL, fake_result)), raise_server_exceptions=False)


def test_simulate_stub_returns_valid_result_and_mode_header(stub_client):
    r = stub_client.post("/api/v1/simulate", json=_fixture("simulate_request.json"))
    assert r.status_code == 200
    assert r.headers["X-BedFlow-Mode"] == MODE_STUB
    result = SimulationResult.model_validate(r.json())
    assert result.scenario_id == _fixture("simulate_request.json")["scenario_id"]


def test_simulate_sets_external_scenario_id_and_seed(real_client):
    body = _fixture("simulate_request.json") | {"scenario_id": "more_physicians", "seed": 7}
    r = real_client.post("/api/v1/simulate", json=body)
    assert r.status_code == 200
    assert r.json()["scenario_id"] == "more_physicians"
    assert r.json()["seed"] == 7
    assert r.headers["X-BedFlow-Mode"] == MODE_REAL


def test_compare_stub_serves_fixture(stub_client):
    r = stub_client.post("/api/v1/compare", json=_fixture("compare_request.json"))
    assert r.status_code == 200
    assert r.headers["X-BedFlow-Mode"] == MODE_STUB
    CompareResponse.model_validate(r.json())


def test_compare_real_path_computes_from_engine(real_client):
    r = real_client.post("/api/v1/compare", json=_fixture("compare_request.json"))
    assert r.status_code == 200
    body = CompareResponse.model_validate(r.json())
    assert [x.scenario_id for x in body.results][0] == "baseline"
    assert body.results[0].paired_delta_12h_pp is None
    assert all(x.paired_delta_12h_pp is not None for x in body.results[1:])


def test_simulate_invalid_occupancy_is_422(stub_client):
    body = _fixture("simulate_request.json")
    body["config"]["initial_ward_occupied"] = body["config"]["ward_beds"] + 1
    assert stub_client.post("/api/v1/simulate", json=body).status_code == 422


def test_simulate_negative_seed_and_extra_field_are_422(stub_client):
    body = _fixture("simulate_request.json")
    assert stub_client.post("/api/v1/simulate", json=body | {"seed": -1}).status_code == 422
    assert stub_client.post("/api/v1/simulate", json=body | {"extra": 1}).status_code == 422


def test_compare_invalid_requests_are_422(stub_client):
    body = _fixture("compare_request.json")
    assert stub_client.post("/api/v1/compare", json=body | {"seeds": [1]}).status_code == 422
    assert stub_client.post("/api/v1/compare", json=body | {"seeds": [1, 1]}).status_code == 422
    bad = json.loads(json.dumps(body))
    bad["scenarios"][1]["overrides"] = {"physicians": 99}
    assert stub_client.post("/api/v1/compare", json=bad).status_code == 422


def test_engine_failure_is_500_without_leaking_details():
    def boom(config, seed):
        raise RuntimeError("secret internal detail")

    client = TestClient(create_app(Engine(MODE_REAL, boom)), raise_server_exceptions=False)
    r = client.post("/api/v1/simulate", json=_fixture("simulate_request.json"))
    assert r.status_code == 500
    assert "secret" not in r.text


def test_health_reports_mode(stub_client):
    assert stub_client.get("/health").json() == {"ok": True, "mode": MODE_STUB}


def test_invalid_mode_rejected():
    with pytest.raises(ValueError):
        load_engine("bogus")
