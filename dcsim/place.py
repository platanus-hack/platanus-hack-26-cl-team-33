"""Coloca un data center: qué les pasa a sus vecinos, futuro por futuro.

El usuario elige un punto, un tamaño, un tipo de enfriamiento y un año de anuncio. El modelo
corre cada futuro dos veces con los mismos números aleatorios: con y sin ese data center. La
diferencia es efecto del data center.

Para mirar de cerca a los vecinos se agregan hogares de muestra dentro de 3 km. Se ubican según
la misma densidad de población que usa el modelo (un disco por comuna y sus barrios) y siguen
las mismas reglas de opinión, pero pesan cero: no mueven los totales de la comuna. La población
no crece ni se muda: el modelo no tiene datos para eso.
"""

from __future__ import annotations

import math
import os
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

import numpy as np

from . import catalog as C
from .model import (
    COMMUNE_AQ,
    COMMUNE_NODE,
    FRAME_T,
    NC,
    ST_CANCEL,
    ST_OPER,
    ST_WAIT,
    Run,
    _km,
    nominal_it_mw,
    population_view,
)
from .policy import SCENARIOS

RADIUS_KM = 3.0  # vecinos que se siguen
MAX_EDGE_KM = 8.0  # cuán lejos del área poblada de una comuna modelada se puede colocar
N_CAND = 4000  # puntos candidatos para ubicar hogares de muestra
MAX_PROBES = 360
NEAR_HOMES_MIN = 20  # hogares a menos de 300 m para contar como "casas al lado" (litigio)
YEARS = list(range(2027, 2033))
COOLINGS = ("evaporativo", "aire", "hibrido")
SIZES = (10, 30, 100, 300)
RULES = ("status_quo", "acumulativa", "aire", "mesa", "comunidad", "norte")
RING_KM = (0.3, 0.5, 1.0, 3.0)


# ---------------------------------------------------------------------------
# Densidad de hogares del modelo (la misma de _build_population)
# ---------------------------------------------------------------------------
def _components():
    """(comuna, lat, lon, radio_km, hogares/km²) de cada disco poblado."""
    comps = []
    for ci, c in enumerate(C.COMMUNES):
        n = 180 if c.region == "RM" else 60  # agentes por comuna, como en _build_population
        hh = c.pop / C.PEOPLE_PER_HOUSEHOLD
        placed = 0
        for _name, blat, blon, br, frac in c.barrios:
            k = int(round(n * frac))
            placed += k
            comps.append((ci, blat, blon, br, hh * k / n / (math.pi * br * br)))
        comps.append((ci, c.lat, c.lon, c.radius_km,
                      hh * (n - placed) / n / (math.pi * c.radius_km ** 2)))
    return comps


COMPS = _components()


def density_by_commune(lat, lon) -> np.ndarray:
    """Hogares por km² en cada punto, separados por comuna: (n_puntos, NC)."""
    lat, lon = np.atleast_1d(lat).astype(float), np.atleast_1d(lon).astype(float)
    out = np.zeros((len(lat), NC))
    for ci, clat, clon, r, dens in COMPS:
        out[_km(lat, lon, clat, clon) <= r, ci] += dens
    return out


def _overlap(d: float, r1: float, r2: float) -> float:
    """Área de la intersección de dos círculos de radios r1 y r2 a distancia d."""
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a1 = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
    a2 = r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    tri = 0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
    return a1 + a2 - tri


def households_within(lat: float, lon: float, rho: float) -> float:
    return sum(dens * _overlap(float(_km(lat, lon, clat, clon)), r, rho)
               for _ci, clat, clon, r, dens in COMPS)


# ---------------------------------------------------------------------------
# Sitio y hogares de muestra
# ---------------------------------------------------------------------------
def site_info(lat: float, lon: float) -> dict:
    """A qué comuna, nodo de red y acuífero queda conectado un punto, y cuántos vecinos tiene."""
    dens = density_by_commune(lat, lon)[0]
    inside = bool(dens.max() > 0)
    if inside:
        ci = int(dens.argmax())
    else:
        edge = np.array([_km(lat, lon, c.lat, c.lon) - c.radius_km for c in C.COMMUNES])
        ci = int(edge.argmin())
        if edge[ci] > MAX_EDGE_KM:
            return {"ok": False, "reason": "Este punto queda lejos de las comunas que modelamos. "
                    "Prueba en el norte o poniente de Santiago, Valparaíso, Concepción o "
                    "Antofagasta."}
    c = C.COMMUNES[ci]
    node = C.GRID_NODES[COMMUNE_NODE[ci]]
    aq = C.AQUIFERS[COMMUNE_AQ[ci]] if COMMUNE_AQ[ci] >= 0 else None
    rings = {str(r): round(households_within(lat, lon, r)) for r in RING_KM}
    near_dc = []
    for p in C.PROJECTS:
        d = float(_km(lat, lon, p.lat, p.lon))
        if d <= RADIUS_KM and (p.real_status or p.pre_existing):
            near_dc.append({"name": p.name, "it_mw": nominal_it_mw(p), "km": round(d, 2),
                            "status": p.real_status or "operando"})
    return {
        "ok": True, "lat": lat, "lon": lon, "commune": ci, "commune_id": c.id,
        "commune_name": c.name, "inside": inside, "rm": c.region == "RM",
        "households_commune": round(c.pop / C.PEOPLE_PER_HOUSEHOLD),
        "node": node.name, "node_headroom_mw": node.headroom_mw,
        "node_expansions": [list(e) for e in node.expansions],
        "aquifer": aq.name if aq else None, "prohibition": bool(aq and aq.prohibition),
        "households": rings, "near_homes": rings["0.3"] >= NEAR_HOMES_MIN,
        "near_dc": sorted(near_dc, key=lambda x: x["km"]),
    }


def build_probes(lat: float, lon: float) -> dict:
    """Hogares de muestra a menos de RADIUS_KM, repartidos según la densidad del modelo.

    Si hay muchos puntos poblados, se eligen con probabilidad proporcional a la densidad y cada
    uno representa la misma cantidad de hogares (un mapa de puntos). Si hay pocos, se usan todos
    y cada uno pesa su densidad × su área.
    """
    rng = np.random.default_rng([int(round(abs(lat) * 1e4)), int(round(abs(lon) * 1e4)), 11])
    r = RADIUS_KM * np.sqrt(rng.random(N_CAND))
    th = rng.random(N_CAND) * 2 * np.pi
    plat = lat + r * np.sin(th) / 110.57
    plon = lon + r * np.cos(th) / (111.32 * math.cos(math.radians(lat)))
    dens = density_by_commune(plat, plon)
    tot = dens.sum(axis=1)
    idx = np.nonzero(tot > 0)[0]
    cell = math.pi * RADIUS_KM ** 2 / N_CAND
    if len(idx) > MAX_PROBES:
        total_hh = float(tot[idx].sum() * cell)
        idx = np.sort(rng.choice(idx, MAX_PROBES, replace=False, p=tot[idx] / tot[idx].sum()))
        w = np.full(len(idx), total_hh / MAX_PROBES)
    else:
        w = tot[idx] * cell
    if len(idx):  # el total coincide con el conteo exacto de hogares a menos de RADIUS_KM
        w = w * households_within(lat, lon, RADIUS_KM) / w.sum()
    k = len(idx)
    return {
        "lat": plat[idx], "lon": plon[idx], "w": w, "commune": dens[idx].argmax(axis=1),
        "sens": rng.lognormal(0.0, 0.35, k), "val": rng.uniform(0.6, 1.4, k),
        "theta": rng.uniform(0.35, 0.7, k), "dist": _km(plat[idx], plon[idx], lat, lon),
    }


# ---------------------------------------------------------------------------
# Simulación con y sin el data center
# ---------------------------------------------------------------------------
def normalize(req: dict) -> dict:
    """Valida y redondea la solicitud (lat/lon a ~10 m para que el caché sirva)."""
    lat, lon = round(float(req["lat"]), 4), round(float(req["lon"]), 4)
    if not (-56 < lat < -17 and -76 < lon < -66):
        raise ValueError("El punto debe estar en Chile")
    it_mw = float(req.get("it_mw", 30))
    if not 3 <= it_mw <= 500:
        raise ValueError("El tamaño debe estar entre 3 y 500 MW")
    cooling = req.get("cooling", "evaporativo")
    if cooling not in COOLINGS:
        raise ValueError(f"Enfriamiento desconocido: {cooling}")
    year = int(req.get("year", 2027))
    if year not in YEARS:
        raise ValueError(f"El año debe estar entre {YEARS[0]} y {YEARS[-1]}")
    rule = req.get("rule", "status_quo")
    if rule not in RULES:
        raise ValueError(f"Regla desconocida: {rule}")
    return {"lat": lat, "lon": lon, "it_mw": it_mw, "cooling": cooling, "year": year,
            "hv_line": bool(req.get("hv_line", False)),
            "grid_priority": bool(req.get("grid_priority", False)), "rule": rule}


@lru_cache(maxsize=8)
def _context(key: tuple) -> dict:
    spec = dict(key)
    site = site_info(spec["lat"], spec["lon"])
    if not site["ok"]:
        raise ValueError(site["reason"])
    probes = build_probes(spec["lat"], spec["lon"])
    view = population_view((spec["lat"], spec["lon"]), probes)
    user = {"it_mw": spec["it_mw"], "cooling": spec["cooling"],
            "announce": C.ym(f"{spec['year']}-01"), "commune": site["commune"],
            "near_homes": site["near_homes"], "hv_line": spec["hv_line"],
            "grid_priority": spec["grid_priority"]}
    return {"spec": spec, "site": site, "probes": probes, "view": view, "user": user,
            "policy": SCENARIOS[spec["rule"]]["policy"]}


def _pair(ctx: dict, seed: int) -> dict:
    """Un futuro con y sin el data center; devuelve lo que se resume después."""
    a = Run(ctx["policy"], seed=seed, pop=ctx["view"], user_dc=ctx["user"]).run()
    b = Run(ctx["policy"], seed=seed, pop=ctx["view"]).run()
    ui, ci = a.user_i, ctx["site"]["commune"]
    th = ctx["probes"]["theta"]
    mob_a = np.array(a.frames["op"]) > th  # (cuadros, hogares de muestra)
    mob_b = np.array(b.frames["op"]) > th
    aq = COMMUNE_AQ[ci]
    node_c = COMMUNE_NODE == COMMUNE_NODE[ci]
    hh_c = ctx["site"]["households_commune"]
    own_mw = a.it[ui] if a.status[ui] == ST_OPER else 0.0
    ra, rb = a.rec, b.rec
    return {
        "mob_a": mob_a, "mob_b": mob_b,
        "status": np.array(a.frames["status"]), "mw": np.array(a.frames["mw"]),
        "wls": np.array(a.frames["wls"]), "jobs": np.array(a.frames["jobs"]),
        "conf_a": np.array(a.frames["conflict"])[:, ci],
        "conf_b": np.array(b.frames["conflict"])[:, ci],
        "sued": bool(a.n_lit[ui] > 0), "annulled": bool(a.annulled[ui]),
        "online": int(a.online[ui]), "final": int(a.status[ui]),
        "air_end": bool(a.frames["air"][-1]), "route": a.route[ui],
        "oper_end": bool(a.status[ui] == ST_OPER),
        "wls_end": float(np.mean(a.frames["wls"][-4:])),  # último año, promedio estacional
        "mw_end": float(np.mean(a.frames["mw"][-4:])),
        # lo que aporta el propio data center (no la diferencia de la comuna, que mezcla
        # efectos sobre otros proyectos)
        "jobs_local_end": float(a.frames["jobs"][-1] * a.v["local_hire_share"]),
        "muni_hh_end": float(a.frames["muni"][-1] / hh_c),
        "y": {
            "aq_drawdown_m": float(rb["aq_level"][aq, -1] - ra["aq_level"][aq, -1]) if aq >= 0
            else 0.0,
            "others_mw": float(ra["it_chile"][-1] - own_mw - rb["it_chile"][-1]),
            "others_lit": float(ra["litigations"][-1] - a.n_lit[ui] - rb["litigations"][-1]),
            "conflict_with": float(ra["c_conflict"][ci, -1]),
            "conflict_without": float(rb["c_conflict"][ci, -1]),
            "muni_usd_hh": float((ra["c_muni_usd"][ci, -1] - rb["c_muni_usd"][ci, -1]) / hh_c),
            "jobs_local": float(ra["c_jobs_local"][ci, -1] - rb["c_jobs_local"][ci, -1]),
            "nox_t": float(ra["c_nox"][ci, -1] - rb["c_nox"][ci, -1]),
            "share_pct": float(100 * (ra["c_share"][ci, -1] - rb["c_share"][ci, -1])),
            "waitlist_node_mw": float(ra["c_waitlist"][node_c, -1].sum()
                                      - rb["c_waitlist"][node_c, -1].sum()),
        },
    }


def _run_chunk(args):
    key, seeds = args
    ctx = _context(key)
    return [_pair(ctx, s) for s in seeds]


def _q(a, nd=2):
    a = np.asarray(a, dtype=float)
    p5, p50, p95 = np.percentile(a, [5, 50, 95], axis=0)
    r = lambda x: np.round(x, nd).tolist()  # noqa: E731
    return {"p5": r(p5), "p50": r(p50), "p95": r(p95)}


def simulate(req: dict, n: int = 40, workers: int | None = None) -> dict:
    spec = normalize(req)
    key = tuple(sorted(spec.items()))
    ctx = _context(key)  # valida el sitio antes de lanzar procesos
    seeds = list(range(n))
    workers = workers or int(os.environ.get("DCSIM_WORKERS", "0")) or min(8, os.cpu_count() or 2)
    if workers == 1 or n <= 8:
        pairs = [_pair(ctx, s) for s in seeds]
    else:
        chunks = [seeds[i::workers] for i in range(workers) if seeds[i::workers]]
        with ProcessPoolExecutor(max_workers=len(chunks)) as ex:
            parts = list(ex.map(_run_chunk, [(key, ch) for ch in chunks]))
        by_seed = {s: p for ch, part in zip(chunks, parts, strict=True)
                   for s, p in zip(ch, part, strict=True)}
        pairs = [by_seed[s] for s in seeds]
    return summarize(ctx, pairs)


def summarize(ctx: dict, pairs: list[dict]) -> dict:
    pr = ctx["probes"]
    w = pr["w"]
    stack = lambda k: np.array([p[k] for p in pairs])  # noqa: E731
    mob_a, mob_b = stack("mob_a"), stack("mob_b")  # (futuros, cuadros, hogares)
    hh_a = (mob_a * w).sum(axis=2)  # hogares movilizados por futuro y cuadro
    hh_b = (mob_b * w).sum(axis=2)
    status = stack("status")
    status_prob = np.stack([(status == k).mean(axis=0) for k in range(7)], axis=-1)
    online = np.array([p["online"] for p in pairs])
    came = online < C.N_MONTHS
    sued = np.array([p["sued"] for p in pairs])
    final = np.array([p["final"] for p in pairs])
    air_end = np.array([p["air_end"] for p in pairs])
    ys = {k: [p["y"][k] for p in pairs] for k in pairs[0]["y"]}
    oper = np.array([p["oper_end"] for p in pairs])
    # Si llega a operar en 2035: valores típicos entre los futuros en que opera
    if_oper = None
    if oper.any():
        sel = [p for p in pairs if p["oper_end"]]
        med = lambda xs: round(float(np.median(xs)), 2)  # noqa: E731
        if_oper = {"n": len(sel), "wls": med([p["wls_end"] for p in sel]),
                   "mw": med([p["mw_end"] for p in sel]),
                   "jobs_local": med([p["jobs_local_end"] for p in sel]),
                   "muni_usd_hh": med([p["muni_hh_end"] for p in sel])}
        if_oper.update({k: med([p["y"][k] for p in sel]) for k in
                        ("aq_drawdown_m", "nox_t", "share_pct")})
    routes = {}
    for p in pairs:
        routes[p["route"]] = routes.get(p["route"], 0) + 1
    pct = lambda m: np.round(100 * m.mean(axis=0)).astype(int).tolist()  # noqa: E731
    return {
        "spec": ctx["spec"], "site": ctx["site"], "n": len(pairs),
        "frames": [C.ym_str(int(t)) for t in FRAME_T],
        "probes": {"lat": np.round(pr["lat"], 5).tolist(), "lon": np.round(pr["lon"], 5).tolist(),
                   "w": np.round(w, 1).tolist(), "dist": np.round(pr["dist"], 2).tolist()},
        "households_followed": round(float(w.sum())),
        # % de futuros en que cada hogar de muestra está movilizado, por cuadro
        "p_mob_with": pct(mob_a), "p_mob_without": pct(mob_b),
        "mob_with": _q(hh_a, 0), "mob_without": _q(hh_b, 0), "mob_diff": _q(hh_a - hh_b, 0),
        "conflict_with": _q(stack("conf_a"), 3), "conflict_without": _q(stack("conf_b"), 3),
        "status_prob": np.round(status_prob, 3).tolist(),
        "mw": _q(stack("mw"), 1), "wls": _q(stack("wls"), 1), "jobs": _q(stack("jobs"), 0),
        "facts": {
            "p_sued": round(float(sued.mean()), 3),
            "p_annulled": round(float(np.mean([p["annulled"] for p in pairs])), 3),
            "p_online": round(float(came.mean()), 3),
            "online_p50": C.ym_str(int(np.median(online[came]))) if came.any() else None,
            "online_p10": C.ym_str(int(np.percentile(online[came], 10))) if came.any() else None,
            "online_p90": C.ym_str(int(np.percentile(online[came], 90))) if came.any() else None,
            "p_cancel": round(float((final == ST_CANCEL).mean()), 3),
            "p_waiting_2035": round(float((final == ST_WAIT).mean()), 3),
            "p_redesign_air": round(float(air_end.mean()), 3)
            if ctx["spec"]["cooling"] != "aire" else 0.0,
            "routes": routes,
        },
        "y2035": {k: _q(v, 2) for k, v in ys.items()},
        "if_operating": if_oper,
    }
