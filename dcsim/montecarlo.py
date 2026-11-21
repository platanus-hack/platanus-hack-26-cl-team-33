"""Corre muchas réplicas y resume la distribución de resultados.

Todas las políticas usan las mismas semillas (números aleatorios comunes), así la diferencia
entre dos escenarios en la misma réplica se debe a la política y no al azar.
"""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from . import catalog as C
from .model import NK, Run
from .policy import Policy

MODEL_VERSION = "1"
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"
SERIES_KEYS = [
    "it_chile", "it_rm", "n_dc", "demand_chile", "demand_rm", "peak_rm", "waitlist_mw",
    "waitlist_n", "water_ls_rm", "water_peak_ls_rm", "google_water_ml", "google_power_mw",
    "dc_share_national", "bill_pct", "nox_t", "diesel_hours", "litigations", "annulments",
    "relocations", "cancellations", "invest_realized", "invest_lost", "jobs_build", "jobs_oper",
    "households_500m", "conflict_rm", "mw_antofagasta", "mw_outside_rm", "wetland_stress",
    "wetland_stress_nodc", "demand_rm_dec", "demand_chile_dec", "it_chile_jun", "n_dc_jun",
    "it_rm_jun",
]
COMMUNE_KEYS = ["c_it", "c_demand", "c_share", "c_water_ls", "c_conflict", "c_h500",
                "c_jobs_local", "c_muni_usd", "c_fund_usd", "c_nox", "c_ndc", "c_waitlist"]
AQ_KEYS = ["aq_dc_drawdown", "aq_level"]


def _run_chunk(args):
    policy_dict, seeds, mode = args
    pol = Policy(**policy_dict)
    out = {k: [] for k in SERIES_KEYS + COMMUNE_KEYS + AQ_KEYS + ["p_status", "p_commune"]}
    extra = {"delays": [], "fuel": [], "routes": {}}
    for s in seeds:
        r = Run(pol, seed=s, mode=mode).run()
        for k in out:
            out[k].append(r.rec[k])
        extra["delays"].append(r.delays)
        extra["fuel"].append(r.fuel_declared)
        for k, v in r.routes_2027.items():
            extra["routes"][k] = extra["routes"].get(k, 0) + v
    return {k: np.array(v) for k, v in out.items()}, extra


def run_raw(policy: Policy, n: int = 200, mode: str = "anchored", seed0: int = 0,
            workers: int | None = None):
    """Devuelve los registros apilados de n réplicas: dict clave -> array (n, ...)."""
    seeds = list(range(seed0, seed0 + n))
    workers = workers or min(8, os.cpu_count() or 2)
    chunks = [seeds[i::workers] for i in range(workers) if seeds[i::workers]]
    tasks = [(policy.to_dict(), ch, mode) for ch in chunks]
    if workers == 1 or n <= 8:
        results = [_run_chunk(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=len(tasks)) as ex:
            results = list(ex.map(_run_chunk, tasks))
    order = np.argsort(np.concatenate([np.array(ch) for ch in chunks]))
    raw = {k: np.concatenate([r[0][k] for r in results])[order] for k in results[0][0]}
    extra = {"delays": [], "fuel": [], "routes": {}}
    for _, e in results:
        extra["delays"] += sum(e["delays"], [])
        extra["fuel"] += sum(e["fuel"], [])
        for k, v in e["routes"].items():
            extra["routes"][k] = extra["routes"].get(k, 0) + v
    return raw, extra


def _q(a, axis=0):
    p5, p50, p95 = np.percentile(a, [5, 50, 95], axis=axis)
    return {"p5": _r(p5), "p50": _r(p50), "p95": _r(p95), "mean": _r(a.mean(axis=axis))}


def _r(x, nd=3):
    return np.round(np.asarray(x, dtype=float), nd).tolist()


def summarize(raw, extra, policy: Policy, mode: str) -> dict:
    n = raw["it_chile"].shape[0]
    out = {
        "meta": {"n": n, "mode": mode, "policy": policy.to_dict(), "years": C.YEARS,
                 "version": MODEL_VERSION},
        "series": {k: _q(raw[k]) for k in SERIES_KEYS},
        "communes": {k: _q(raw[k]) for k in COMMUNE_KEYS},
        "aquifers": {k: _q(raw[k]) for k in AQ_KEYS},
    }
    st = raw["p_status"]  # (n, NK, NY)
    probs = np.stack([(st == k).mean(axis=0) for k in range(7)], axis=-1)  # (NK, NY, 7)
    com = raw["p_commune"]
    mode_com = np.zeros(com.shape[1:], dtype=int)
    for i in range(NK):
        for y in range(com.shape[2]):
            mode_com[i, y] = np.bincount(com[:, i, y]).argmax()
    moved = (com != com[:, :, :1]).any(axis=2).mean(axis=0)
    # A dónde se muda cada proyecto, año a año: fracción de futuros y comuna de destino más común
    home = np.array([C.COMMUNE_IDX[p.commune] for p in C.PROJECTS])[None, :, None]
    away = com != home  # (n, NK, NY)
    p_moved = away.mean(axis=0)
    dest = np.full(p_moved.shape, -1, dtype=int)
    for i, y in zip(*np.nonzero(p_moved >= 0.1), strict=True):
        dest[i, y] = int(np.bincount(com[away[:, i, y], i, y]).argmax())
    out["projects"] = {"status_prob": _r(probs, 2), "commune_mode": mode_com.tolist(),
                       "p_relocated": _r(moved, 2), "p_moved": _r(p_moved, 2),
                       "dest_mode": dest.tolist()}
    d = np.array(extra["delays"]) if extra["delays"] else np.array([0.0])
    f = np.array(extra["fuel"]) if extra["fuel"] else np.array([0.0])
    hist, edges = np.histogram(f, bins=[0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000,
                                        1200, 1500, 2000, 5000])
    out["extra"] = {
        "delay_months": {"p50": float(np.median(d)), "p90": float(np.percentile(d, 90)),
                         "mean": float(d.mean()), "n": int(len(extra["delays"]))},
        "fuel_hist": {"counts": hist.tolist(), "edges": edges.tolist()},
        "routes": extra["routes"],
    }
    # Valores por réplica (para comparar escenarios en pares)
    paired = {}
    for k in ["it_rm", "it_chile", "waitlist_mw", "water_ls_rm", "water_peak_ls_rm",
              "households_500m", "conflict_rm", "litigations", "invest_realized",
              "invest_lost", "relocations", "cancellations", "mw_antofagasta", "bill_pct",
              "nox_t", "jobs_oper", "peak_rm", "demand_rm", "mw_outside_rm"]:
        paired[k] = _r(raw[k][:, [C.YEARS.index(2030), C.YEARS.index(2035)]])
    out["paired"] = paired
    return out


def _cache_key(policy: Policy, n: int, mode: str) -> str:
    h = hashlib.sha1(json.dumps([policy.to_dict(), n, mode, MODEL_VERSION, _code_hash()],
                                sort_keys=True).encode()).hexdigest()[:16]
    return f"{mode}_{n}_{h}"


_CODE_HASH = None


def _code_hash() -> str:
    global _CODE_HASH
    if _CODE_HASH is None:
        root = Path(__file__).resolve().parent
        m = hashlib.sha1()
        for name in ("model.py", "catalog.py", "params.py", "policy.py", "montecarlo.py"):
            m.update((root / name).read_bytes())
        _CODE_HASH = m.hexdigest()[:10]
    return _CODE_HASH


def run_ensemble(policy: Policy, n: int = 200, mode: str = "anchored", use_cache: bool = True,
                 workers: int | None = None) -> dict:
    key = _cache_key(policy, n, mode)
    path = CACHE_DIR / f"{key}.json"
    if use_cache and path.exists():
        return json.loads(path.read_text())
    raw, extra = run_raw(policy, n, mode, workers=workers)
    res = summarize(raw, extra, policy, mode)
    if use_cache:
        CACHE_DIR.mkdir(exist_ok=True)
        path.write_text(json.dumps(res))
    return res
