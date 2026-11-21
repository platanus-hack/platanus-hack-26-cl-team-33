"""API y servidor de la interfaz.

    uv run uvicorn dcsim.server:app --port 8000
"""

from __future__ import annotations

import json
import os
import threading
from collections import Counter, OrderedDict
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from . import catalog as C
from .insights import METRICS, hypotheses, scenario_deltas, winners_losers
from .model import STATUS_LABELS, SYNTH_RATE_MAX
from .montecarlo import run_ensemble
from .params import PARAMS, P
from .policy import HYPOTHESIS_SCENARIOS, SCENARIOS, Policy
from .validation import run_validation

N_PRESET = 200
N_CUSTOM = int(os.environ.get("DCSIM_N_CUSTOM", "100"))  # futuros por regla propia
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


def _it_mw(p: C.Project) -> float:
    """Potencia TI. Para la lista de espera del CEN el catálogo trae la potencia de conexión."""
    if p.extra.get("request_mw"):
        return round(p.it_mw / (P["pue_air"].base * P["peak_pue_ratio"].base), 1)
    return p.it_mw


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
                      "lat": p.lat, "lon": p.lon, "it_mw": _it_mw(p),
                      "request_mw": p.it_mw if p.extra.get("request_mw") else None,
                      "cooling": p.cooling,
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


class PolicyIn(BaseModel):
    """Regla propia: los mismos campos que ``Policy``, con tipos y rangos acotados."""

    model_config = ConfigDict(extra="forbid")
    fuel_threshold_t: float = Field(1000.0, ge=0, le=10_000)
    cumulative: StrictBool = False
    window_months: int = Field(12, ge=1, le=60)
    water_cap_ls: float | None = Field(None, ge=0, le=1_000)
    permit_speed: float = Field(1.0, ge=0.1, le=3.0)
    air_cooling_rm: StrictBool = False
    north_incentive: float = Field(0.0, ge=0, le=1)
    community_fund_usd_mw: float = Field(0.0, ge=0, le=200_000)
    transparency: StrictBool = False
    demand: Literal["baja", "base", "alta"] = "base"
    climate: Literal["moderado", "base", "severo"] = "base"
    demand_rate: float | None = Field(None, ge=0, le=SYNTH_RATE_MAX)


class RunRequest(BaseModel):
    policy: PolicyIn


_CUSTOM_MAX = 16  # reglas propias en memoria (el plan free tiene 512 MB)
_custom: OrderedDict = OrderedDict()
_custom_lock = threading.Lock()


@app.post("/api/run")
def run_custom(req: RunRequest) -> dict:
    pol = Policy(**req.policy.model_dump())
    key = tuple(sorted(pol.to_dict().items()))
    with _custom_lock:  # una simulación a la vez: la CPU es una sola
        if key not in _custom:
            _custom[key] = run_ensemble(pol, n=N_CUSTOM, use_cache=False)
            while len(_custom) > _CUSTOM_MAX:
                _custom.popitem(last=False)
        _custom.move_to_end(key)
        return _custom[key]


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


@app.get("/api/findings")
def findings() -> list:
    """Hallazgos precalculados (uv run python -m dcsim.explore && python -m dcsim.findings)."""
    path = Path(__file__).resolve().parent.parent / "cache" / "findings.json"
    return json.loads(path.read_text()) if path.exists() else []


STORY_TABS = ["status_quo", "mesa", "aire", "acumulativa", "norte", "paquete"]
STORY_KEYS = ["it_chile", "dc_share_national", "water_ls_rm", "conflict_rm", "litigations",
              "invest_lost", "invest_realized", "bill_pct", "waitlist_mw"]
STORY_CHECKS = ["rm_2021", "google_water", "rm_2025", "waitlist", "litigations",
                "conflict_pattern"]


@app.get("/api/story")
def story() -> dict:
    """Lo justo para la portada: 6 reglas × pocas cifras en 2035, y la prueba resumida."""
    def build():
        yi = C.YEARS.index(2035)
        tabs = []
        for sid in STORY_TABS:
            s = _scenario(sid)["series"]
            sc = SCENARIOS[sid]
            tabs.append({
                "id": sid, "name": sc["name"], "short": sc["short"], "summary": sc["summary"],
                "values": {k: {q: s[k][q][yi] for q in ("p5", "p50", "p95")}
                           for k in STORY_KEYS},
            })
        val = _cached("validation", lambda: run_validation(n=N_PRESET))
        checks = {c["id"]: c for c in val["checks"]}
        kinds = Counter(c["kind"] for c in val["checks"])
        return {"year": 2035, "tabs": tabs, "passed": val["passed"], "total": val["total"],
                "n_validation": kinds["validación"], "n_calibration": kinds["calibración"],
                "n_custom": N_CUSTOM,
                "checks": [checks[i] for i in STORY_CHECKS if i in checks],
                "findings": findings()}
    return _cached("story", build)


@app.get("/api/status")
def status() -> dict:
    ready = [sid for sid in list(SCENARIOS) + list(HYPOTHESIS_SCENARIOS)
             if ("scen", sid) in _memo]
    return {"ready": ready, "validation": "validation" in _memo, "insights": "insights" in _memo}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/explorar")
def explorar() -> RedirectResponse:
    """La vista experta se fusionó en la portada; los enlaces antiguos llevan al simulador."""
    return RedirectResponse("/#simular")


app.mount("/static", StaticFiles(directory=WEB), name="static")
