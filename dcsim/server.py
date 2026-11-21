"""API y servidor de la interfaz.

    uv run uvicorn dcsim.server:app --port 8000
"""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import catalog as C
from .insights import METRICS, hypotheses, scenario_deltas, winners_losers
from .model import STATUS_LABELS
from .montecarlo import run_ensemble
from .params import PARAMS
from .policy import HYPOTHESIS_SCENARIOS, SCENARIOS, policy_from_dict
from .validation import run_validation

N_PRESET = 200
N_CUSTOM = 100
WEB = Path(__file__).resolve().parent.parent / "web"

@asynccontextmanager
async def _lifespan(_app):
    _warm()
    yield


app = FastAPI(title="Simulador de data centers en Chile", lifespan=_lifespan)


@app.middleware("http")
async def _no_cache_static(request, call_next):
    resp = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp
_lock = threading.Lock()
_memo: dict = {}


def _cached(key, fn):
    if key in _memo:
        return _memo[key]
    with _lock:
        if key not in _memo:
            _memo[key] = fn()
    return _memo[key]


def _scenario(sid: str) -> dict:
    if sid in SCENARIOS:
        pol = SCENARIOS[sid]["policy"]
    elif sid in HYPOTHESIS_SCENARIOS:
        pol = HYPOTHESIS_SCENARIOS[sid]
    else:
        raise HTTPException(404, f"Escenario desconocido: {sid}")
    return _cached(("scen", sid), lambda: run_ensemble(pol, n=N_PRESET))


def _all_results() -> dict:
    ids = list(SCENARIOS) + list(HYPOTHESIS_SCENARIOS)
    return {sid: _scenario(sid) for sid in ids}


def _warm() -> None:
    def work():
        _cached("validation", lambda: run_validation(n=N_PRESET))
        _all_results()
        _cached("insights", _insights)

    threading.Thread(target=work, daemon=True).start()


@app.get("/api/meta")
def meta() -> dict:
    return {
        "years": C.YEARS, "now": C.ym_str(C.NOW), "policy_start": C.ym_str(C.POLICY_START),
        "status_labels": STATUS_LABELS,
        "communes": [{"id": c.id, "name": c.name, "region": c.region, "pop": c.pop,
                      "households": round(c.pop / C.PEOPLE_PER_HOUSEHOLD), "lat": c.lat,
                      "lon": c.lon, "node": c.node, "aquifer": c.aquifer,
                      "radius_km": c.radius_km}
                     for c in C.COMMUNES],
        "projects": [{"id": p.id, "name": p.name, "operator": p.operator, "commune": p.commune,
                      "lat": p.lat, "lon": p.lon, "it_mw": p.it_mw, "cooling": p.cooling,
                      "fuel_t": p.fuel_t, "real_status": p.real_status,
                      "anonymous": p.anonymous, "pre_existing": p.pre_existing,
                      "announce": p.announce, "water_right_ls": p.water_right_ls,
                      "dist_homes_m": p.dist_homes_m, "hist": list(p.hist), "src": p.src}
                     for p in C.PROJECTS],
        "nodes": [{"id": n.id, "name": n.name, "headroom_mw": n.headroom_mw,
                   "expansions": [list(e) for e in n.expansions], "src": n.src}
                  for n in C.GRID_NODES],
        "scenarios": [{"id": k, "name": v["name"], "short": v["short"], "summary": v["summary"],
                       "question": v["question"], "policy": v["policy"].to_dict()}
                      for k, v in SCENARIOS.items()],
        "params": [asdict(p) for p in PARAMS],
        "metrics": {k: {"label": v[0], "unit": v[1], "good_up": v[2]} for k, v in METRICS.items()},
        "observed": C.OBSERVED,
    }


@app.get("/api/scenario/{sid}")
def scenario(sid: str) -> dict:
    return _scenario(sid)


class RunRequest(BaseModel):
    policy: dict


@app.post("/api/run")
def run_custom(req: RunRequest) -> dict:
    pol = policy_from_dict(req.policy)
    key = ("custom", tuple(sorted(pol.to_dict().items())))
    return _cached(key, lambda: run_ensemble(pol, n=N_CUSTOM))


@app.get("/api/validation")
def validation() -> dict:
    return _cached("validation", lambda: run_validation(n=N_PRESET))


def _insights() -> dict:
    res = _all_results()
    return {"hypotheses": hypotheses(res),
            "deltas_2030": scenario_deltas({k: res[k] for k in SCENARIOS}, 2030),
            "deltas_2035": scenario_deltas({k: res[k] for k in SCENARIOS}, 2035)}


@app.get("/api/insights")
def insights() -> dict:
    return _cached("insights", _insights)


@app.get("/api/communes/{sid}/{year}")
def communes(sid: str, year: int) -> list[dict]:
    if year not in C.YEARS:
        raise HTTPException(400, "Año fuera de rango")
    return winners_losers(_scenario(sid), year)


@app.get("/api/status")
def status() -> dict:
    ready = [sid for sid in list(SCENARIOS) + list(HYPOTHESIS_SCENARIOS)
             if ("scen", sid) in _memo]
    return {"ready": ready, "validation": "validation" in _memo, "insights": "insights" in _memo}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


app.mount("/static", StaticFiles(directory=WEB), name="static")
