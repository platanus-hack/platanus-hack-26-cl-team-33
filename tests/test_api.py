import subprocess
import sys
from pathlib import Path

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


def test_story_on_a_cold_server_does_not_hang():
    """La portada pide /api/story apenas parte el servidor, antes de que el precalentado cargue
    los escenarios: story() los pide dentro de _cached y con un candado simple se colgaba.
    Corre en otro proceso para que, si se cuelga, falle por tiempo sin trabar al resto."""
    code = ("from dcsim import server; "
            "assert [t['id'] for t in server.story()['tabs']] == server.STORY_TABS")
    root = Path(__file__).resolve().parent.parent
    subprocess.run([sys.executable, "-c", code], cwd=root, check=True, timeout=60)
