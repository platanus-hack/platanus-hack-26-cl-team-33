"""Invariantes del motor y de la API. Corren el modelo: no dependen de resultados en caché."""

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from dcsim import catalog as C
from dcsim import model as M
from dcsim.montecarlo import _code_hash
from dcsim.params import base_values
from dcsim.policy import SCENARIOS, STATUS_QUO, Policy
from dcsim.server import PolicyIn, app


def _pending_verdicts(r: M.Run) -> set[int]:
    return {i for evs in r.events.values() for kind, i, ver in evs
            if (kind == "verdict" and ver == r.version[i]) or kind == "script_verdict"}


def test_relocating_drops_the_lawsuit():
    r = M.Run(STATUS_QUO, seed=0, params=base_values())
    i = C.PROJECT_IDX["dc_iris"]
    r._file_lawsuit(i, C.NOW, paused=True)
    r._relocate(i, C.NOW, C.COMMUNE_IDX["antofagasta"])
    assert not r.lit_active[i] and not r.paused[i]


def test_no_project_stays_in_litigation_without_a_pending_verdict():
    for sid in ("status_quo", "norte"):
        for seed in range(20):
            r = M.Run(SCENARIOS[sid]["policy"], seed=seed).run()
            pending = _pending_verdicts(r)
            stuck = [i for i in range(r.N) if r.status[i] == M.ST_LITIG and i not in pending]
            assert not stuck, (sid, seed, stuck)


def test_known_projects_draw_the_same_numbers_at_any_demand():
    a = M.Run(STATUS_QUO, seed=5)
    b = M.Run(replace(STATUS_QUO, demand_rate=10.0), seed=5)
    for k in ("z", "u", "u_month", "gumbel", "lfmax"):
        assert np.array_equal(getattr(a, k)[:M.NK], getattr(b, k)[:M.NK]), k

    def arrivals(r):
        return {(int(r.announce[i]), round(float(r.it[i]), 6)) for i in range(M.NK, r.N)}

    # los proyectos nuevos con demanda base son un subconjunto de los de demanda alta
    assert arrivals(a) < arrivals(b)


def test_waitlist_capex_uses_server_mw():
    v = base_values()
    r = M.Run(STATUS_QUO, seed=0, params=v)
    for i, p in enumerate(C.PROJECTS):
        if p.extra.get("request_mw"):
            assert r.it[i] < p.it_mw, p.id
            assert np.isclose(r.capex[i], r.it[i] * v["capex_musd_per_mw"]), p.id


def test_policy_input_mirrors_policy():
    assert set(PolicyIn.model_fields) == set(Policy.__dataclass_fields__)


def test_run_endpoint_rejects_bad_policies():
    client = TestClient(app)
    for bad in ({"cumulative": "false"}, {"demand": "foo"}, {"demand_rate": 1e6},
                {"permit_speed": 0}, {"unknown": 1}):
        assert client.post("/api/run", json={"policy": bad}).status_code == 422, bad


def test_findings_were_built_with_this_code():
    path = Path(__file__).resolve().parent.parent / "cache" / "findings.json"
    findings = json.loads(path.read_text())
    assert findings and all(f.get("model") == _code_hash() for f in findings), (
        "cache/findings.json está desactualizado: corre dcsim.explore y dcsim.findings")
