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
from . import place as PL
from .insights import METRICS, hypotheses, scenario_deltas, winners_losers
from .model import STATUS_LABELS, SYNTH_RATE_MAX, nominal_it_mw
from .montecarlo import run_ensemble
from .params import PARAMS
from .policy import HYPOTHESIS_SCENARIOS, SCENARIOS, STATUS_QUO, Policy
from .validation import run_validation

N_PRESET = 200
N_CUSTOM = int(os.environ.get("DCSIM_N_CUSTOM", "100"))  # futuros por regla propia
N_PLACE = int(os.environ.get("DCSIM_N_PLACE", "40"))  # futuros (pares con/sin) por data center
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
_lock = threading.RLock()  # reentrante: story() e insights() piden escenarios dentro de _cached
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


def _baseline(n: int) -> dict:
    """Seguir como hoy en los mismos n futuros (semillas 0..n-1) que corre una regla propia.

    Se lee del disco (python -m dcsim.precompute) o se simula una sola vez.
    """
    return _cached(("baseline", n), lambda: run_ensemble(STATUS_QUO, n=n))


def _warm() -> None:
    def work():
        _cached("validation", lambda: run_validation(n=N_PRESET))
        _all_results()
        _baseline(N_CUSTOM)
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
                      "lat": p.lat, "lon": p.lon, "it_mw": nominal_it_mw(p),
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
        "place": {"years": PL.YEARS, "sizes": list(PL.SIZES), "coolings": list(PL.COOLINGS),
                  "radius_km": PL.RADIUS_KM, "n": N_PLACE,
                  "areas": [[round(la, 4), round(lo, 4), r, round(d)]
                            for _c, la, lo, r, d in PL.COMPS],
                  "rules": [{"id": k, "name": SCENARIOS[k]["name"]} for k in PL.RULES]},
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
# Cifras de la portada que se comparan futuro a futuro con seguir como hoy
COMPARE_KEYS = ["it_chile", "water_ls_rm", "conflict_rm", "litigations", "invest_lost",
                "bill_pct"]
_Y35 = 1  # columna de 2035 en "paired" (la otra es 2030)


def _versus(res: dict, base: dict) -> dict:
    """Compara una regla con seguir como hoy en los mismos futuros.

    run_raw ordena las réplicas por semilla (0..n-1), así la fila i de "paired" es el mismo
    futuro en las dos. Cuenta en cuántos futuros la regla queda mejor, peor o igual en 2035;
    si la cifra no tiene un lado bueno (MW operando), en cuántos queda con más o con menos.
    """
    n = res["meta"]["n"]
    yi = C.YEARS.index(2035)
    compare = {}
    for k in COMPARE_KEYS:
        pairs = list(zip(res["paired"][k], base["paired"][k], strict=True))
        more = sum(a[_Y35] > b[_Y35] for a, b in pairs)
        less = sum(a[_Y35] < b[_Y35] for a, b in pairs)
        good_up = METRICS[k][2]
        if good_up is None:
            c = {"more": more, "less": less}
        else:
            c = {"better": more, "worse": less} if good_up else {"better": less, "worse": more}
        compare[k] = {**c, "same": n - more - less, "n": n}
    values = {k: base["series"][k]["p50"][yi] for k in STORY_KEYS}
    return {"baseline": {"n": base["meta"]["n"], "values": values}, "compare": compare}


@app.post("/api/run")
def run_custom(req: RunRequest) -> dict:
    """Corre una regla propia y la compara con seguir como hoy en esos mismos futuros."""
    pol = Policy(**req.policy.model_dump())
    n = N_CUSTOM
    key = (tuple(sorted(pol.to_dict().items())), n)
    with _custom_lock:  # una simulación a la vez: la CPU es una sola
        if key not in _custom:
            _custom[key] = run_ensemble(pol, n=n, use_cache=False)
            while len(_custom) > _CUSTOM_MAX:
                _custom.popitem(last=False)
        _custom.move_to_end(key)
        res = _custom[key]
    # fuera del candado: comparar es barato y "como hoy" se lee del disco una sola vez
    return {**res, **_versus(res, _baseline(n))}


@app.get("/api/baseline")
def baseline() -> dict:
    """Seguir como hoy en los mismos futuros que corre «Tu regla»: el mapa compara contra esto."""
    return _baseline(N_CUSTOM)


@app.get("/api/place/site")
def place_site(lat: float, lon: float) -> dict:
    """Comuna, nodo de red, acuífero y hogares alrededor de un punto (rápido, sin simular)."""
    return PL.site_info(round(lat, 4), round(lon, 4))


class PlaceRequest(BaseModel):
    lat: float
    lon: float
    it_mw: float = 30
    cooling: str = "evaporativo"
    year: int = 2027
    hv_line: bool = False
    grid_priority: bool = False
    rule: str = "status_quo"


_place_lock = threading.Lock()
_place_memo: OrderedDict = OrderedDict()


@app.post("/api/place")
def place(req: PlaceRequest) -> dict:
    """Corre N_PLACE futuros con y sin el data center del usuario."""
    try:
        spec = PL.normalize(req.model_dump())
        key = (tuple(sorted(spec.items())), N_PLACE)
        with _place_lock:
            if key in _place_memo:
                _place_memo.move_to_end(key)
                return _place_memo[key]
        res = PL.simulate(spec, n=N_PLACE)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    with _place_lock:
        _place_memo[key] = res
        while len(_place_memo) > 24:
            _place_memo.popitem(last=False)
    return res


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
    return {"ready": ready, "validation": "validation" in _memo, "insights": "insights" in _memo,
            "baseline": ("baseline", N_CUSTOM) in _memo}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/explorar")
def explorar() -> RedirectResponse:
    """La vista experta se fusionó en la portada; los enlaces antiguos llevan al simulador."""
    return RedirectResponse("/#simular")


app.mount("/static", StaticFiles(directory=WEB), name="static")
