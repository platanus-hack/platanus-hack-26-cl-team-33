from fastapi.testclient import TestClient

from dcsim.server import app


def test_meta_and_scenario_endpoints():
    with TestClient(app) as client:
        meta = client.get("/api/meta").json()
        assert len(meta["projects"]) > 50
        assert {s["id"] for s in meta["scenarios"]} >= {"status_quo", "acumulativa", "aire"}
        res = client.get("/api/scenario/status_quo").json()
        assert len(res["series"]["it_chile"]["p50"]) == len(meta["years"])
        assert client.get("/").status_code == 200
