"""Batería de experimentos para buscar hallazgos robustos (y sorprendentes).

    uv run python -m dcsim.explore          # corre todo y guarda cache/explore_raw.json

185 configuraciones y 15.080 simulaciones, ~3 min en 10 núcleos. cache/explore_raw.json
(~32 MB) no se versiona: solo este comando lo rehace, y dcsim.findings lo lee para escribir
cache/findings.json.

Todas las configuraciones usan las mismas semillas (números aleatorios comunes), así las
diferencias entre configuraciones de un mismo experimento se deben a la palanca. La historia
contrafactual (E3) corre en modo libre; el resto, en modo anclado.
"""

from __future__ import annotations

import itertools
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import numpy as np

from . import catalog as C
from .model import NK, ST_OPER, Run
from .policy import STATUS_QUO, Policy

OUT = C.__file__.replace("dcsim/catalog.py", "cache/explore_raw.json")
Y = {2030: C.YEARS.index(2030), 2035: C.YEARS.index(2035)}
SERIES = ["it_chile", "it_rm", "waitlist_mw", "water_ls_rm", "water_peak_ls_rm", "conflict_rm",
          "litigations", "invest_realized", "invest_lost", "cancellations", "relocations",
          "households_500m", "mw_antofagasta", "bill_pct", "peak_rm", "jobs_oper",
          "demand_chile_dec", "demand_rm", "nox_t", "annulments", "wetland_stress",
          "wetland_stress_nodc"]
CER = C.PROJECT_IDX["google_cerrillos"]
SC2 = C.PROJECT_IDX["dc_sc2"]

LEVERS = {
    "conjunta": {"cumulative": True, "water_cap_ls": 60.0},
    "aire": {"air_cooling_rm": True},
    "transparencia": {"transparency": True},
    "fondo": {"community_fund_usd_mw": 20_000},
    "norte": {"north_incentive": 0.6},
    "rapido": {"permit_speed": 0.5},
    "umbral80": {"fuel_threshold_t": 80.0},
}


def _metrics(r: Run) -> dict:
    out = {}
    for y, yi in Y.items():
        for k in SERIES:
            out[f"{k}_{y}"] = float(r.rec[k][yi])
    out["delay_mean"] = float(np.mean(r.delays)) if r.delays else float("nan")
    tot = sum(r.routes_2027.values())
    out["seia_share"] = (r.routes_2027.get("SEIA", 0) + r.routes_2027.get("acumulativa", 0)) / tot \
        if tot else float("nan")
    conf = r.rec["c_conflict"][:, Y[2035]]
    out["top_conflict_2035"] = int(np.argmax(conf))
    out["c_conflict_2035"] = conf.round(4).tolist()
    out["c_it_2035"] = r.rec["c_it"][:, Y[2035]].round(1).tolist()
    out["c_h500_2035"] = r.rec["c_h500"][:, Y[2035]].round(0).tolist()
    out["cer_online"] = int(r.online[CER]) if r.online[CER] < 10**5 else -1
    out["cer_lit"] = int(r.n_lit[CER])
    out["cer_status_2026"] = int(r.rec["p_status"][CER, C.YEARS.index(2026)])
    out["sc2_online"] = int(r.online[SC2]) if r.online[SC2] < 10**5 else -1
    op26 = r.rec["p_status"][:NK, C.YEARS.index(2026)] == ST_OPER
    out["it_known_op_2026"] = float(r.it[:NK][op26].sum())
    return out


def _task(args):
    name, pol_dict, overrides, mode, seeds = args
    pol = Policy(**pol_dict)
    return name, [_metrics(Run(pol, seed=s, mode=mode, overrides=overrides).run()) for s in seeds]


def run_configs(configs: list[tuple], workers: int | None = None) -> dict:
    """configs: (nombre, Policy, overrides|None, modo, n). Devuelve nombre -> lista de métricas."""
    workers = workers or os.cpu_count() or 4
    tasks = []
    for name, pol, ov, mode, n in configs:
        seeds = list(range(n))
        step = max(5, n // 4)
        for i in range(0, n, step):
            tasks.append((name, pol.to_dict(), ov, mode, seeds[i:i + step]))
    out: dict[str, list] = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for name, rows in ex.map(_task, tasks, chunksize=1):
            out.setdefault(name, []).extend(rows)
    return out


def experiments(n_fact: int = 60, n_sweep: int = 120, n_cf: int = 200) -> list[tuple]:
    cfg = []
    # E1: diseño factorial completo de 7 palancas (128 combinaciones)
    names = list(LEVERS)
    for bits in itertools.product([0, 1], repeat=len(names)):
        on = [nm for nm, b in zip(names, bits, strict=True) if b]
        kw = {}
        for nm in on:
            kw.update(LEVERS[nm])
        cfg.append(("F:" + ("+".join(on) or "como_hoy"), replace(STATUS_QUO, **kw), None,
                    "anchored", n_fact))
    # E2: barridos de una palanca
    sweeps = {
        "permit_speed": [0.25, 0.5, 0.75, 1.0, 1.25, 1.5],
        "fuel_threshold_t": [80.0, 200.0, 400.0, 700.0, 1000.0, 2000.0, 5000.0],
        "community_fund_usd_mw": [0, 5_000, 10_000, 20_000, 40_000, 80_000],
        "north_incentive": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        "demand_rate": [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0],
    }
    for key, vals in sweeps.items():
        for v in vals:
            cfg.append((f"S:{key}={v}", replace(STATUS_QUO, **{key: v}), None, "anchored", n_sweep))
    for v in [10.0, 30.0, 60.0, 120.0, 400.0]:
        cfg.append((f"S:water_cap_ls={v}", replace(STATUS_QUO, cumulative=True, water_cap_ls=v),
                    None, "anchored", n_sweep))
    for v in ["moderado", "base", "severo"]:
        cfg.append((f"S:climate={v}", replace(STATUS_QUO, climate=v), None, "anchored", n_sweep))
    for v in [5.0, 10.0, 15.0]:
        for lever in ("como_hoy", "conjunta", "rapido"):
            kw = {"demand_rate": v, **({} if lever == "como_hoy" else LEVERS[lever])}
            cfg.append((f"D:{lever}@{v}", replace(STATUS_QUO, **kw), None, "anchored", n_sweep))
    # E3: historia contrafactual (modo libre)
    cfg.append(("H:real", STATUS_QUO, None, "free", n_cf))
    cfg.append(("H:cerrillos_aire", STATUS_QUO,
                {"google_cerrillos": {"cooling": "aire", "water_right_ls": 0}}, "free", n_cf))
    # E4: quitar proyectos (anclado)
    cfg.append(("P:base", STATUS_QUO, None, "anchored", n_cf))
    cfg.append(("P:sin_sc2", STATUS_QUO, {"dc_sc2": {"exclude": True}}, "anchored", n_cf))
    cfg.append(("P:sin_campo_lampa", STATUS_QUO, {"campo_lampa": {"exclude": True}}, "anchored",
                n_cf))
    cfg.append(("P:campo_lampa_lejos", STATUS_QUO, {"campo_lampa": {"generic_site": True}},
                "anchored", n_cf))
    waitlisted = [p.id for p in C.PROJECTS if p.real_status == "lista_espera"]
    cfg.append(("P:sin_lista_espera", STATUS_QUO, {pid: {"exclude": True} for pid in waitlisted},
                "anchored", n_cf))
    return cfg


def main():
    cfg = experiments()
    n_runs = sum(c[4] for c in cfg)
    print(f"{len(cfg)} configuraciones, {n_runs} simulaciones…", flush=True)
    t0 = time.time()
    res = run_configs(cfg)
    print(f"listo en {time.time() - t0:.0f} s")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f)
    print("guardado en", OUT)


if __name__ == "__main__":
    main()
