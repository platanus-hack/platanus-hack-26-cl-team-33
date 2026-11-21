"""Modelo híbrido de agentes con stocks y flujos del efecto acumulado de data centers.

Agentes:
  * Desarrolladores (un proyecto cada uno): eligen comuna, diseño de enfriamiento y cuánto
    combustible declarar; esperan red, se reubican o desisten.
  * Regulador (SEA): decide la vía (SEIA o pertinencia) según el umbral de combustible, o
    evalúa por zona en la política acumulativa.
  * Operador de red (CEN): cola de conexión por nodo, primero en llegar, primero en servirse.
  * Tribunales: los vecinos litigan según la oposición local; un fallo puede anular el permiso.
  * Hogares sintéticos (~2.300): exposición a ruido, diésel, agua y acumulación; reciben
    beneficios (empleo, patentes, fondos); su opinión se contagia dentro de la comuna.

Stocks: capacidad de red por nodo, nivel de acuíferos, oposición y confianza por comuna.

Modos:
  * ``free``: la historia 2012–2026 la genera el modelo a partir de los anuncios reales.
    Se usa para validar contra datos observados.
  * ``anchored``: los proyectos conocidos siguen su historia documentada hasta nov-2026 y
    luego el modelo proyecta. Se usa para comparar políticas desde el presente real.
"""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from . import catalog as C
from .params import base_values, sample_values
from .policy import STATUS_QUO, Policy

# Estados reportados por proyecto
ST_NONE, ST_PERMIT, ST_WAIT, ST_LITIG, ST_BUILD, ST_OPER, ST_CANCEL = range(7)
STATUS_LABELS = ["no anunciado", "en tramitación", "esperando red", "en litigio",
                 "en construcción", "operando", "desistido"]
REAL_STATUS_CODE = {"operando": ST_OPER, "construccion": ST_BUILD, "tramitacion": ST_PERMIT,
                    "lista_espera": ST_WAIT}

EVAP, AIR, HYBRID = 0, 1, 2
COOL_CODE = {"evaporativo": EVAP, "aire": AIR, "hibrido": HYBRID}
COOL_NAME = {v: k for k, v in COOL_CODE.items()}

NC = len(C.COMMUNES)
NN = len(C.GRID_NODES)
NA = len(C.AQUIFERS)
NY = len(C.YEARS)
NK = len(C.PROJECTS)
COMMUNE_NODE = np.array([C.NODE_IDX[c.node] for c in C.COMMUNES])
COMMUNE_AQ = np.array([C.AQUIFER_IDX[c.aquifer] if c.aquifer else -1 for c in C.COMMUNES])
COMMUNE_RM = np.array([c.region == "RM" for c in C.COMMUNES])
HOUSEHOLDS = np.array([c.pop / C.PEOPLE_PER_HOUSEHOLD for c in C.COMMUNES])
ANTOF = C.COMMUNE_IDX["antofagasta"]
SITING_CANDIDATES = [i for i, c in enumerate(C.COMMUNES) if c.id != "santiago"]
GOOGLE_Q = [C.PROJECT_IDX["google_quilicura_1"], C.PROJECT_IDX["google_quilicura_2"]]

# Estacionalidad (hemisferio sur): 1 en enero, -1 en julio
SEASON = np.cos(2 * np.pi * np.arange(12) / 12)
UTM_USD = 75.0  # 1 UTM ≈ US$75 (aprox. 2026)
PATENTE_CAP_USD = 8000 * UTM_USD  # tope legal de la patente municipal: 8.000 UTM/año
STAGE_WEIGHT = np.array([0.0, 0.45, 0.45, 0.45, 0.8, 1.0, 0.0])  # por estado
# Tope de proyectos nuevos por año. Las llegadas se sortean a este ritmo y se "adelgazan" según
# la demanda, así los proyectos de una demanda baja son un subconjunto de los de una alta.
SYNTH_RATE_MAX = 30.0


def _project_draws(rng, n: int) -> dict:
    """Números aleatorios propios de n proyectos (duraciones, decisiones, riesgos, preferencias)."""
    return {"lf": rng.standard_normal(n), "z": rng.standard_normal((n, 6)),
            "u": rng.random((n, 8)), "u_month": rng.random((n, C.N_MONTHS)),
            "gumbel": rng.gumbel(size=(n, NC))}


def nominal_it_mw(p: C.Project) -> float:
    """Potencia TI con valores centrales. La lista de espera del CEN trae potencia de conexión."""
    if p.extra.get("request_mw"):
        v = base_values()
        return round(p.it_mw / (v["pue_air"] * v["peak_pue_ratio"]), 1)
    return p.it_mw


# ---------------------------------------------------------------------------
# Geometría y población sintética (fija para todas las réplicas)
# ---------------------------------------------------------------------------
def _km(lat1, lon1, lat2, lon2):
    dy = (lat1 - lat2) * 110.57
    dx = (lon1 - lon2) * 111.32 * np.cos(np.radians((lat1 + lat2) / 2))
    return np.sqrt(dx * dx + dy * dy)


def _generic_site(c: C.Commune) -> tuple[float, float]:
    """Sitio industrial genérico en la periferia poniente de la comuna."""
    dlon = 0.9 * c.radius_km / (111.32 * math.cos(math.radians(c.lat)))
    return c.lat, c.lon - dlon


SITE_LATLON = [(p.lat, p.lon) for p in C.PROJECTS] + [_generic_site(c) for c in C.COMMUNES]
N_SITES = len(SITE_LATLON)


def _build_population(seed: int = 12345, per_commune_rm: int = 180, per_commune_other: int = 60):
    rng = np.random.default_rng(seed)
    lat, lon, com, w = [], [], [], []
    for ci, c in enumerate(C.COMMUNES):
        n = per_commune_rm if c.region == "RM" else per_commune_other
        placed = 0
        for _name, blat, blon, br, frac in c.barrios:
            k = int(round(n * frac))
            r = br * np.sqrt(rng.random(k))
            th = rng.random(k) * 2 * np.pi
            lat += list(blat + r * np.sin(th) / 110.57)
            lon += list(blon + r * np.cos(th) / (111.32 * math.cos(math.radians(blat))))
            placed += k
        k = n - placed
        r = c.radius_km * np.sqrt(rng.random(k))
        th = rng.random(k) * 2 * np.pi
        lat += list(c.lat + r * np.sin(th) / 110.57)
        lon += list(c.lon + r * np.cos(th) / (111.32 * math.cos(math.radians(c.lat))))
        com += [ci] * n
        w += [HOUSEHOLDS[ci] / n] * n
    lat, lon, com, w = map(np.array, (lat, lon, com, w))
    sens = rng.lognormal(0.0, 0.35, len(lat))  # sensibilidad a molestias
    val = rng.uniform(0.6, 1.4, len(lat))  # valoración de beneficios
    theta = rng.uniform(0.35, 0.7, len(lat))  # umbral para movilizarse
    slat = np.array([s[0] for s in SITE_LATLON])
    slon = np.array([s[1] for s in SITE_LATLON])
    dist = _km(lat[:, None], lon[:, None], slat[None, :], slon[None, :])
    dist = np.maximum(dist, 0.05)
    return {
        "lat": lat, "lon": lon, "commune": com, "w": w, "sens": sens, "val": val,
        "theta": theta, "dist": dist,
        "K": np.exp(-dist / 0.7),  # molestia por cercanía (ruido, diésel, paisaje)
        "K_local": np.exp(-dist / 1.5),  # quiénes cuentan como "vecinos" de un sitio
        "near500": dist < 0.5,
    }


POP = _build_population()
NAG = len(POP["w"])
W_BY_COMMUNE = np.bincount(POP["commune"], weights=POP["w"], minlength=NC)
_KLW = POP["K_local"] * POP["w"][:, None]
K_LOCAL_DEN = _KLW.sum(axis=0)

# Vista de la población que usa una corrida. Sin data center del usuario son los arreglos globales.
BASE_VIEW = {
    "n": NAG, "n_real": NAG, "n_sites": N_SITES, "commune": POP["commune"], "w": POP["w"],
    "sens": POP["sens"], "val": POP["val"], "theta": POP["theta"], "K": POP["K"],
    "KLW": _KLW, "kl_den": K_LOCAL_DEN, "near500": POP["near500"],
}


def population_view(site: tuple[float, float], probes: dict | None = None) -> dict:
    """Agrega un sitio (el data center del usuario) y, opcionalmente, hogares de muestra.

    El sitio nuevo es la columna ``N_SITES``. Los hogares de muestra (``probes``: lat, lon,
    commune, sens, val, theta) siguen las mismas reglas de opinión que el resto, pero pesan
    cero: no cambian la oposición de la comuna, los litigios ni ningún total. Sirven para ver
    con detalle qué les pasa a los vecinos de un punto.
    """
    slat = np.array([s[0] for s in SITE_LATLON] + [site[0]])
    slon = np.array([s[1] for s in SITE_LATLON] + [site[1]])
    d_new = np.maximum(_km(POP["lat"], POP["lon"], site[0], site[1]), 0.05)
    K = np.hstack([POP["K"], np.exp(-d_new / 0.7)[:, None]])
    K_local = np.hstack([POP["K_local"], np.exp(-d_new / 1.5)[:, None]])
    near = np.hstack([POP["near500"], (d_new < 0.5)[:, None]])
    com, w = POP["commune"], POP["w"]
    sens, val, theta = POP["sens"], POP["val"], POP["theta"]
    if probes is not None and len(probes["lat"]):
        plat, plon = np.asarray(probes["lat"]), np.asarray(probes["lon"])
        dp = np.maximum(_km(plat[:, None], plon[:, None], slat[None, :], slon[None, :]), 0.05)
        K = np.vstack([K, np.exp(-dp / 0.7)])
        K_local = np.vstack([K_local, np.exp(-dp / 1.5)])
        near = np.vstack([near, dp < 0.5])
        com = np.concatenate([com, np.asarray(probes["commune"], dtype=com.dtype)])
        w = np.concatenate([w, np.zeros(len(plat))])
        sens = np.concatenate([sens, probes["sens"]])
        val = np.concatenate([val, probes["val"]])
        theta = np.concatenate([theta, probes["theta"]])
    klw = K_local * w[:, None]
    return {"n": len(w), "n_real": NAG, "n_sites": N_SITES + 1, "commune": com, "w": w,
            "sens": sens, "val": val, "theta": theta, "K": K, "KLW": klw,
            "kl_den": np.maximum(klw.sum(axis=0), 1e-12), "near500": near}


# Cuadros que se guardan para seguir a un data center del usuario: cada 3 meses desde oct-2026
FRAME_T = np.arange(C.POLICY_START - 3, C.N_MONTHS, 3)


class Run:
    """Una réplica de la simulación."""

    def __init__(self, policy: Policy = STATUS_QUO, seed: int = 0, mode: str = "anchored",
                 params: dict | None = None, overrides: dict | None = None,
                 user_dc: dict | None = None, pop: dict | None = None):
        self.policy = policy
        # Contrafactuales: {id_proyecto: {"cooling": ..., "water_right_ls": ..., "exclude": True}}
        self.overrides = overrides or {}
        # Data center del usuario: {"it_mw", "cooling", "announce" (mes), "commune" (índice),
        # "near_homes", "hv_line", "grid_priority"}. Usa la columna de sitio N_SITES de `pop`.
        self.user_dc = user_dc
        self.P = pop if pop is not None else BASE_VIEW
        if user_dc is not None and self.P["n_sites"] <= N_SITES:
            raise ValueError("Un data center del usuario necesita population_view(sitio)")
        self.mode = mode
        self.seed = seed
        v = params if params is not None else sample_values(np.random.default_rng([seed, 1]))
        self.v = v
        self._init_projects(np.random.default_rng([seed, 2]), np.random.default_rng([seed, 3]))
        self._init_environment(np.random.default_rng([seed, 4]))
        self._init_records()

    # ------------------------------------------------------------------ inicialización
    def _init_projects(self, rng_p, rng_s):
        v, pol = self.v, self.policy
        # Llegadas sintéticas 2027+ (mismas para todas las políticas con igual demanda)
        rate = pol.demand_rate if pol.demand_rate is not None else {
            "baja": 2.0, "base": 5.0, "alta": 10.0}[pol.demand]
        if not 0 <= rate <= SYNTH_RATE_MAX:
            raise ValueError(f"demand_rate debe estar entre 0 y {SYNTH_RATE_MAX:g}")
        cand = []
        for year in range(2027, C.YEAR_END + 1):
            for _ in range(rng_s.poisson(SYNTH_RATE_MAX)):
                month = (year - C.YEAR0) * 12 + int(rng_s.integers(12))
                # tamaño típico 30 MW, rango 3–500 MW (informe, parte C)
                mw = float(np.clip(rng_s.lognormal(math.log(30), 0.9), 3, 500))
                u = rng_s.random()
                cool = EVAP if u < 0.3 else (AIR if u < 0.8 else HYBRID)
                cand.append((month, mw, cool, rng_s.random()))
        # Cada candidato trae sus propios números: un proyecto sintético ve lo mismo con
        # cualquier demanda, y los conocidos (otro flujo) no cambian cuando cambia la demanda.
        cand_draws = _project_draws(rng_s, len(cand))
        kept = np.array([j for j, c in enumerate(cand) if c[3] * SYNTH_RATE_MAX < rate], dtype=int)
        synth = [cand[j][:3] for j in kept]
        draws = {k: np.concatenate([d, cand_draws[k][kept]])
                 for k, d in _project_draws(rng_p, NK).items()}
        self.n_synth = len(synth)
        nb = NK + self.n_synth  # proyectos que sortean del flujo común de números aleatorios
        has_u = self.user_dc is not None
        N = self.N = nb + int(has_u)
        self.user_i = nb if has_u else -1
        # El data center del usuario sortea de su propio flujo: así los demás proyectos ven
        # exactamente los mismos números con y sin él, y la diferencia es efecto del data center.
        rng_u = np.random.default_rng([self.seed, 5])
        user_draws = _project_draws(rng_u, N - nb)
        draws = {k: np.concatenate([d, user_draws[k]]) for k, d in draws.items()}
        self.it = np.zeros(N)
        self.cool = np.zeros(N, dtype=int)
        self.commune = np.zeros(N, dtype=int)
        self.site = np.zeros(N, dtype=int)
        self.capex = np.zeros(N)
        self.fuel = np.zeros(N)
        self.water_plan = np.zeros(N)  # L/s que la comunidad percibe (derecho o caudal de diseño)
        self.hv = np.zeros(N, dtype=bool)
        self.near_homes = np.zeros(N, dtype=bool)
        self.announce = np.zeros(N, dtype=int)
        self.permit_start = np.zeros(N, dtype=int)
        self.status = np.full(N, ST_NONE)
        self.online = np.full(N, 10**6)
        self.build_start = np.full(N, 10**6)
        self.lfmax = np.clip(v["lf_max"] + 0.08 * draws["lf"], 0.45, 0.97)
        self.fixed_site = np.zeros(N, dtype=bool)  # no se muda de comuna aunque espere red
        self.known = np.zeros(N, dtype=bool)
        self.known[:NK] = True
        for i, p in enumerate(C.PROJECTS):
            ov = self.overrides.get(p.id, {})
            self.it[i] = p.it_mw
            self.cool[i] = COOL_CODE[ov.get("cooling", p.cooling)]
            self.commune[i] = C.COMMUNE_IDX[p.commune]
            self.site[i] = i
            if p.extra.get("request_mw"):
                # El CEN informa la potencia de conexión pedida (total), no la potencia TI
                self.it[i] = p.it_mw / (v["pue_air"] * v["peak_pue_ratio"])
            self.capex[i] = p.capex_musd or self.it[i] * v["capex_musd_per_mw"]
            self.fuel[i] = p.fuel_t if p.fuel_t is not None else -1.0
            self.water_plan[i] = ov.get("water_right_ls", p.water_right_ls) or 0.0
            self.hv[i] = p.hv_line
            self.near_homes[i] = p.dist_homes_m is not None and p.dist_homes_m <= 300
            if ov.get("generic_site"):  # contrafactual: el mismo proyecto en la periferia
                self.site[i] = NK + self.commune[i]
                self.near_homes[i] = False
            self.announce[i] = C.ym(p.announce)
            ps = p.extra.get("permit_start")
            self.permit_start[i] = C.ym(ps) if ps else self.announce[i]
            if ov.get("exclude"):  # el proyecto nunca se anuncia
                self.announce[i] = self.permit_start[i] = 10**6
            if p.operator == "Google":  # hiperescala propia: carga alta y estable
                self.lfmax[i] = 0.92
        for j, (month, mw, cool) in enumerate(synth):
            i = NK + j
            self.it[i] = mw
            self.cool[i] = cool
            self.commune[i] = -1  # se decide al llegar
            self.capex[i] = mw * v["capex_musd_per_mw"]
            self.fuel[i] = -1.0
            self.announce[i] = self.permit_start[i] = month
        if has_u:
            d, i = self.user_dc, nb
            self.it[i] = d["it_mw"]
            self.cool[i] = COOL_CODE[d["cooling"]]
            self.commune[i] = d["commune"]
            self.site[i] = N_SITES  # su propia columna en la vista de población
            self.capex[i] = d["it_mw"] * v["capex_musd_per_mw"]
            self.fuel[i] = -1.0  # el desarrollador lo decide al diseñar (con el umbral vigente)
            self.hv[i] = bool(d.get("hv_line", False))
            self.near_homes[i] = bool(d.get("near_homes", False))
            self.announce[i] = self.permit_start[i] = int(d["announce"])
            self.fixed_site[i] = True
        # Números aleatorios por proyecto (números aleatorios comunes entre políticas)
        self.z = draws["z"]  # duraciones
        self.u = draws["u"]  # decisiones discretas
        self.u_month = draws["u_month"]  # riesgos mensuales (reubicar/desistir)
        self.gumbel = draws["gumbel"]
        # Estado dinámico de cada proyecto
        self.route = [""] * N
        self.grid = np.zeros(N, dtype=int)  # 0 sin pedir, 1 en cola, 2 reservada
        self.req = np.zeros(N)
        self.queued_t = np.full(N, -1)
        self.permit_ok = np.zeros(N, dtype=bool)
        self.lit_active = np.zeros(N, dtype=bool)
        self.paused = np.zeros(N, dtype=bool)
        self.pac = np.zeros(N, dtype=bool)
        self.version = np.zeros(N, dtype=int)
        self.relocated = np.zeros(N, dtype=bool)
        self.orig_commune = self.commune.copy()
        self.n_lit = np.zeros(N, dtype=int)
        self.annulled = np.zeros(N, dtype=bool)
        self.lit_filed_t = np.full(N, -1)
        self.queue_wait = np.zeros(N)  # meses acumulados esperando red
        self.in_zone = np.zeros(N, dtype=bool)
        self.events = defaultdict(list)
        for i in range(N):
            self.events[max(0, int(self.announce[i]))].append(("announce", i, 0))
        self._forced = {}
        if self.mode == "anchored":
            self._anchor_history()
        if has_u and self.user_dc.get("grid_priority"):
            self._forced[self.user_i] = {"force_grid": True}  # se salta la fila del CEN

    def _init_environment(self, rng_e):
        v = self.v
        self.headroom = np.array([n.headroom_mw for n in C.GRID_NODES], dtype=float)
        self.queue = [[] for _ in range(NN)]
        # Fechas reales de ampliaciones de red (con atrasos inciertos)
        self.expansions = defaultdict(list)
        self.planned_exp = [[] for _ in range(NN)]
        for ni, n in enumerate(C.GRID_NODES):
            for date, mw, _name in n.expansions:
                planned = C.ym(date)
                delay = int(max(0, rng_e.lognormal(math.log(10), 0.8) - 4))
                self.expansions[planned + delay].append((ni, mw))
                self.planned_exp[ni].append(planned)
        # Acuíferos: anomalías anuales de recarga (sequías/años lluviosos)
        self.aq_level = np.zeros(NA)
        self.aq_level_nodc = np.zeros(NA)
        anomalies = np.zeros((NA, NY))
        for a in range(NA):
            x = 0.0
            for y in range(NY):
                x = 0.6 * x + 0.25 * rng_e.standard_normal()
                anomalies[a, y] = x
        self.aq_anom = anomalies
        cut = {"moderado": 0.1, "base": v["recharge_cut"], "severo": 0.4}[self.policy.climate]
        self.recharge_cut = cut
        # Apagones: meses en que el respaldo diésel opera por horas
        self.outage_hours = np.zeros((NN, C.N_MONTHS))
        for ni in range(NN):
            for t in np.nonzero(rng_e.random(C.N_MONTHS) < v["outages_per_year"] / 12)[0]:
                self.outage_hours[ni, t] = rng_e.lognormal(math.log(4), 0.7)
        # Opinión de los hogares
        self.opinion = np.full(self.P["n"], 0.12)
        self.trust = np.zeros(NC)  # >0: desconfianza acumulada
        self.conflict = np.zeros(NC)
        self.transparency_on = False

    def _init_records(self):
        z = lambda *s: np.zeros(s)  # noqa: E731
        self.rec = {
            "it_chile": z(NY), "it_rm": z(NY), "n_dc": z(NY), "demand_chile": z(NY),
            "demand_rm": z(NY), "peak_rm": z(NY), "waitlist_mw": z(NY), "waitlist_n": z(NY),
            "water_ls_rm": z(NY), "water_peak_ls_rm": z(NY), "google_water_ml": z(NY),
            "google_power_mw": z(NY), "dc_share_national": z(NY), "bill_pct": z(NY),
            "nox_t": z(NY), "diesel_hours": z(NY), "litigations": z(NY), "annulments": z(NY),
            "relocations": z(NY), "cancellations": z(NY), "invest_realized": z(NY),
            "invest_lost": z(NY), "jobs_build": z(NY), "jobs_oper": z(NY),
            "households_500m": z(NY), "conflict_rm": z(NY), "mw_antofagasta": z(NY),
            "mw_outside_rm": z(NY), "aq_dc_drawdown": z(NA, NY), "aq_level": z(NA, NY),
            "demand_rm_dec": z(NY), "demand_chile_dec": z(NY), "it_chile_jun": z(NY),
            "it_rm_jun": z(NY),
            "n_dc_jun": z(NY),
            "wetland_stress": z(NY), "wetland_stress_nodc": z(NY),
            "px_mw": z(NY), "px_share": z(NY),  # demanda DC que presiona la tarifa
            "c_it": z(NC, NY), "c_demand": z(NC, NY), "c_share": z(NC, NY),
            "c_water_ls": z(NC, NY), "c_conflict": z(NC, NY), "c_h500": z(NC, NY),
            "c_jobs_local": z(NC, NY), "c_muni_usd": z(NC, NY), "c_fund_usd": z(NC, NY),
            "c_nox": z(NC, NY), "c_ndc": z(NC, NY), "c_waitlist": z(NC, NY),
            "p_status": np.zeros((NK, NY), dtype=np.int8),
            "p_commune": np.zeros((NK, NY), dtype=np.int16),
        }
        self.cum = defaultdict(float)
        self.delays = []  # meses entre anuncio y operación (proyectos que abren 2027+)
        self.fuel_declared = []  # combustible declarado por proyectos 2027+ (efecto 'bunching')
        self.routes_2027 = defaultdict(int)
        self.frames = defaultdict(list)  # seguimiento trimestral (solo con data center del usuario)

    # ------------------------------------------------------------------ historia anclada
    def _anchor_history(self):
        """Fija la trayectoria documentada de los proyectos conocidos hasta nov-2026."""
        f = self._forced
        for i, p in enumerate(C.PROJECTS):
            a = self.announce[i]
            rs = p.real_status
            if p.id in self.overrides:  # contrafactual: no se fuerza su historia
                continue
            if p.pre_existing:
                continue
            if rs == "operando":
                online = C.ym(p.real_online) if p.real_online else min(a + 30, C.NOW - 1)
                build = max(10, int(self.v["build_months"]))
                permit_done = max(a + 2, online - build)
                f[i] = {"permit_t": permit_done, "online_t": online,
                        "no_lit": True, "force_grid": True}
            elif rs == "construccion":
                permit_done = min(a + int(self.v["pert_months"]) + 6, C.NOW - 4)
                rem = 6 + int(14 * self.u[i, 7])
                f[i] = {"permit_t": permit_done, "online_t": C.NOW + rem,
                        "no_lit": True, "force_grid": True}
            elif rs in ("tramitacion", "lista_espera"):
                f[i] = {"min_permit_t": C.NOW + 1, "no_lit_before": C.NOW,
                        "no_move_before": C.NOW}
                if rs == "lista_espera":
                    f[i]["no_grid_before"] = C.NOW
            elif rs is None and a <= C.NOW:
                f[i] = {"no_lit_before": C.NOW, "no_move_before": C.NOW}
        # Historia documentada con litigios
        scripts = {
            "google_cerrillos": {"script": [("litigate", C.ym("2020-02"), True),
                                            ("approve", C.ym("2020-02"), ("SEIA", False)),
                                            ("verdict", C.ym("2024-02"), True),
                                            ("redesign", C.ym("2026-07"), "pertinencia"),
                                            ("approve", C.ym("2026-10"), ("pertinencia", True))]},
            "aws_huechuraba": {"script": [("litigate", C.ym("2024-07"), True),
                                          ("approve", C.ym("2024-07"), ("SEIA", False)),
                                          ("verdict", C.ym("2026-04"), False)],
                               "force_grid": True},
        }
        for pid, spec in scripts.items():
            if pid not in self.overrides:
                f[C.PROJECT_IDX[pid]] = spec
        for i, spec in f.items():
            for kind, t, arg in spec.get("script", []):
                self.events[t].append(("script_" + kind, i, arg))

    # ------------------------------------------------------------------ utilidades
    def _threshold(self, t: int) -> float:
        if t >= C.POLICY_START:
            return self.policy.fuel_threshold_t
        return 80.0 if t < C.DS17 else 1000.0

    def _pue(self, cool):
        v = self.v
        return np.choose(cool, [v["pue_evap"], v["pue_air"], v["pue_hybrid"]])

    def _req(self, i) -> float:
        return float(self.it[i] * self._pue(self.cool[i]) * self.v["peak_pue_ratio"])

    def _dur(self, median: float, sigma: float, z: float) -> int:
        return max(1, int(round(median * math.exp(sigma * z))))

    def _schedule(self, t, kind, i):
        self.events[t].append((kind, i, int(self.version[i])))

    def _rm(self, i) -> bool:
        return bool(COMMUNE_RM[self.commune[i]])

    # ------------------------------------------------------------------ decisiones
    def _design(self, i, t):
        """El desarrollador fija enfriamiento y combustible declarado."""
        v, pol = self.v, self.policy
        if t >= C.POLICY_START and pol.air_cooling_rm and self._rm(i) and self.cool[i] != AIR:
            self.cool[i] = AIR
        if not self.known[i] or self.fuel[i] < 0:
            design = self.it[i] * v["fuel_t_per_mw"]
            thr = self._threshold(t)
            min_feasible = self.it[i] * v["fuel_min_t_per_mw"]
            if design >= thr and min_feasible < thr and self.u[i, 0] < v["p_bunch"]:
                design = max(min_feasible, thr * (0.5 + 0.49 * self.u[i, 1]))
            self.fuel[i] = design
        if self.cool[i] != AIR and self.water_plan[i] == 0:
            # Caudal de diseño ~ 3,4 veces el promedio (Quilicura: 50 L/s de derecho, 14,5 usados)
            avg = self.it[i] * 0.9 * 1.2 * 1000 * v["wue_evap"] / 3600
            self.water_plan[i] = avg / 0.29 * (1.0 if self.cool[i] == EVAP else 0.4)
        if self.cool[i] == AIR:
            self.water_plan[i] = 0.0

    def _route(self, i, t) -> str:
        if t >= C.POLICY_START and self.policy.cumulative and self._rm(i):
            return "acumulativa"
        return "SEIA" if self.fuel[i] >= self._threshold(t) else "pertinencia"

    def _permit_months(self, route, i, t) -> int:
        v = self.v
        med = v["seia_months"] if route == "SEIA" else v["pert_months"]
        speed = self.policy.permit_speed if t >= C.POLICY_START else 1.0
        return self._dur(med * speed, 0.45, self.z[i, 0])

    def _choose_commune(self, i, t, exclude_node=None) -> int | None:
        pol = self.policy
        req = self._req(i) if self.commune[i] >= 0 else self.it[i] * 1.6
        best, best_u = None, -1e9
        queued = np.array([sum(self.req[j] for j in q) for q in self.queue])
        for c in SITING_CANDIDATES:
            n = COMMUNE_NODE[c]
            if exclude_node is not None and n == exclude_node:
                continue
            com = C.COMMUNES[c]
            free = self.headroom[n] - queued[n]
            grid = float(np.clip(free / req, 0, 1))
            if grid < 0.5 and any(t < pe <= t + 48 for pe in self.planned_exp[n]):
                grid = max(grid, 0.4)
            u = (2.5 * com.latency + 2.5 * grid - 1.0 * com.land_cost - 3.0 * self.conflict[c]
                 + self.gumbel[i, c])
            if c == ANTOF and t >= C.POLICY_START:
                u += 4.0 * pol.north_incentive
            if self.cool[i] != AIR and com.aquifer is not None:
                u -= 0.5
            if u > best_u:
                best, best_u = c, u
        return best

    # ------------------------------------------------------------------ red eléctrica
    def _request_grid(self, i, t):
        self.req[i] = self._req(i)
        self.grid[i] = 1
        self.queued_t[i] = t
        self.queue[COMMUNE_NODE[self.commune[i]]].append(i)
        self._allocate(COMMUNE_NODE[self.commune[i]], t)

    def _release_grid(self, i, t):
        n = COMMUNE_NODE[self.commune[i]]
        if self.grid[i] == 2:
            self.headroom[n] += self.req[i]
        elif self.grid[i] == 1 and i in self.queue[n]:
            self.queue[n].remove(i)
        self.grid[i] = 0
        self._allocate(n, t)

    def _allocate(self, n, t):
        """Asigna capacidad a la cola del nodo (primero el más antiguo que quepa)."""
        changed = True
        while changed:
            changed = False
            for i in list(self.queue[n]):
                fz = self._forced.get(i, {})
                if t < fz.get("no_grid_before", -1):
                    continue
                if self.req[i] <= self.headroom[n] or fz.get("force_grid"):
                    self.queue[n].remove(i)
                    self.headroom[n] -= self.req[i]
                    self.grid[i] = 2
                    if self.status[i] == ST_WAIT:
                        self.status[i] = ST_PERMIT
                    self._try_start(i, t)
                    changed = True
                    break

    # ------------------------------------------------------------------ ciclo de vida
    def _announce(self, i, t):
        if self.commune[i] < 0:  # proyecto sintético: elige comuna
            c = self._choose_commune(i, t)
            self.commune[i] = self.orig_commune[i] = c
            self.site[i] = NK + c
        self._design(i, t)
        fz = self._forced.get(i, {})
        if "script" in fz:  # historia documentada: el guion manda
            self.status[i] = ST_PERMIT
            self.route[i] = "SEIA"
            self._request_grid(i, t)
            return
        if C.PROJECTS[i].pre_existing if i < NK else False:
            self.status[i] = ST_OPER
            self.online[i] = -60
            self.grid[i] = 2
            self.req[i] = self._req(i)
            self.headroom[COMMUNE_NODE[self.commune[i]]] -= self.req[i]
            self.permit_ok[i] = True
            return
        self._start_permit(i, max(t, int(self.permit_start[i])), t)
        self._request_grid(i, t)

    def _start_permit(self, i, t_permit, t):
        route = self._route(i, t_permit)
        self.route[i] = route
        self.status[i] = ST_PERMIT
        if route == "acumulativa":
            self.in_zone[i] = True
            return
        if t_permit >= C.POLICY_START:
            self.routes_2027[route] += 1
            self.fuel_declared.append(float(self.fuel[i]))
        fz = self._forced.get(i, {})
        if "permit_t" in fz:
            done = int(fz["permit_t"])
        else:
            done = t_permit + self._permit_months(route, i, t_permit)
            done = max(done, int(fz.get("min_permit_t", -1)))
        self._schedule(max(done, t + 1), "permit_done", i)

    def _permit_done(self, i, t, route=None, allow_lit=True):
        self.permit_ok[i] = True
        route = route or self.route[i]
        c = self.commune[i]
        # Señal a la comunidad: sin participación crece la desconfianza
        salience = min(1.0, math.sqrt(self.it[i] / 50))
        self.trust[c] += salience * {"pertinencia": self.v["trust_gain_pertinencia"], "SEIA": 0.03,
                                     "acumulativa": -self.v["trust_gain_cum"]}.get(route, 0)
        fz = self._forced.get(i, {})
        litigate = False
        if allow_lit and not fz.get("no_lit") and t >= fz.get("no_lit_before", -1):
            P = self.P
            local = float((P["KLW"][:, self.site[i]] * self._active).sum()
                          / P["kl_den"][self.site[i]])
            # fundamentos legales: agua de un acuífero en zona de prohibición pesa más
            water_ground = self.v["lit_w_water"] * float(self.cool[i] != AIR and COMMUNE_AQ[c] >= 0)
            grounds = 0.3 + 0.7 * max(water_ground, float(self.near_homes[i]),
                                      float(self.hv[i]))
            # convexo: los litigios se concentran donde la oposición local es intensa
            p = (self.v["p_lit_base"]
                 + self.v["p_lit_conflict"] * local ** self.v["lit_convexity"] * grounds)
            if route == "acumulativa":
                p *= self.v["lit_factor_cum"]
            u = self.u[i, 2] if self.n_lit[i] == 0 else (self.u[i, 2] + 0.618 * self.n_lit[i]) % 1
            litigate = u < min(p, 0.9)
        if litigate:
            self._file_lawsuit(i, t, paused=self.u[i, 3] < self.v["p_pause"])
            lit_t = self._dur(self.v["lit_months"], 0.4, self.z[i, 2])
            self._schedule(t + lit_t, "verdict", i)
        self._try_start(i, t)

    def _file_lawsuit(self, i, t, paused: bool):
        self.lit_active[i] = True
        self.paused[i] = paused
        self.n_lit[i] += 1
        self.lit_filed_t[i] = t
        self.cum["litigations"] += 1
        self.trust[self.commune[i]] += 0.15
        if paused and self.status[i] in (ST_PERMIT, ST_WAIT):
            self.status[i] = ST_LITIG

    def _verdict(self, i, t, annul: bool | None = None):
        self.lit_active[i] = False
        self.paused[i] = False
        c = self.commune[i]
        if annul is None:
            water_flag = self.cool[i] != AIR and COMMUNE_AQ[c] >= 0
            p = self.v["p_annul_base"] * (1 + self.v["annul_w_water"] * water_flag)
            if self.route[i] == "acumulativa":
                p *= self.v["annul_factor_cum"]
            annul = self.u[i, 4] < p
        if not annul:
            if self.status[i] == ST_LITIG:
                self.status[i] = ST_PERMIT if self.grid[i] == 2 else ST_WAIT
            self._try_start(i, t)
            return
        # Permiso anulado
        self.annulled[i] = True
        self.cum["annulments"] += 1
        self.trust[c] += 0.3
        self.trust[COMMUNE_RM] += 0.1  # efecto red: otras comunidades se envalentonan
        if self.status[i] == ST_OPER:
            self.cool[i] = AIR  # adapta la operación existente
            self.water_plan[i] = 0.0
            return
        self.permit_ok[i] = False
        self.version[i] += 1
        self._release_grid(i, t)
        fz = self._forced.get(i, {})
        if "script" in fz:
            self.status[i] = ST_PERMIT
            return
        if self.u[i, 5] < 0.7:  # rediseña con enfriamiento por aire y vuelve a tramitar
            self.status[i] = ST_PERMIT
            self.cool[i] = AIR
            self.water_plan[i] = 0.0
            self._schedule(t + self._dur(24, 0.4, self.z[i, 3]), "redesign_done", i)
        else:
            self._cancel(i, t)

    def _try_start(self, i, t):
        if self.status[i] in (ST_BUILD, ST_OPER, ST_CANCEL):
            return
        if not self.permit_ok[i]:
            return
        if self.grid[i] != 2:
            self.status[i] = ST_WAIT
            return
        if self.lit_active[i] and self.paused[i]:
            self.status[i] = ST_LITIG
            return
        self.status[i] = ST_BUILD
        self.build_start[i] = t
        self.cum["invest_realized"] += self.capex[i]
        fz = self._forced.get(i, {})
        if "online_t" in fz:
            self._schedule(max(t + 1, int(fz["online_t"])), "build_done", i)
            return
        bt = self._dur(self.v["build_months"] * (1 + 0.1 * math.log(max(self.it[i], 3) / 30)),
                       0.25, self.z[i, 1])
        self._schedule(t + bt, "build_done", i)

    def _build_done(self, i, t):
        self.status[i] = ST_OPER
        self.online[i] = t
        if t >= C.POLICY_START:
            self.delays.append(t - int(self.announce[i]))

    def _cancel(self, i, t):
        self.version[i] += 1
        self._release_grid(i, t)
        self.status[i] = ST_CANCEL
        self.in_zone[i] = False
        self.cum["cancellations"] += 1
        self.cum["invest_lost"] += self.capex[i]

    def _relocate(self, i, t, c_new):
        self.version[i] += 1
        self._release_grid(i, t)
        self.relocated[i] = True
        self.commune[i] = c_new
        self.site[i] = NK + c_new
        self.permit_ok[i] = False
        # el juicio era contra el permiso del sitio anterior: al mudarse queda sin objeto
        self.lit_active[i] = False
        self.paused[i] = False
        self.in_zone[i] = False
        self.cum["relocations"] += 1
        self._design(i, t)
        self._start_permit(i, t, t)
        self._request_grid(i, t)

    def _waiting_decisions(self, t):
        """Proyectos esperando red: pueden reubicarse o desistir."""
        for n in range(NN):
            for i in list(self.queue[n]):
                fz = self._forced.get(i, {})
                if t < fz.get("no_move_before", -1) or self.status[i] == ST_CANCEL:
                    continue
                waited = t - self.queued_t[i]
                if waited < 12:
                    continue
                expansion_soon = any(t < pe <= t + 48 for pe in self.planned_exp[n])
                h = self.v["reloc_hazard_exp"] if expansion_soon else self.v["reloc_hazard"]
                if t >= C.POLICY_START:
                    h += 0.02 * self.policy.north_incentive
                h *= 3  # se revisa cada 3 meses
                u = self.u_month[i, t]
                if u < h and not self.fixed_site[i]:
                    c_new = self._choose_commune(i, t, exclude_node=n)
                    if c_new is not None:
                        n2 = COMMUNE_NODE[c_new]
                        q2 = sum(self.req[j] for j in self.queue[n2])
                        if self.headroom[n2] - q2 >= self._req(i):
                            self._relocate(i, t, c_new)
                            continue
                if waited > 36 and u > 1 - 0.012:
                    self._cancel(i, t)

    # ------------------------------------------------------------------ política acumulativa
    def _policy_switch(self, t):
        pol = self.policy
        if pol.transparency:
            self.transparency_on = True
            self.trust[COMMUNE_RM] -= self.v["transparency_trust"]
        for i in range(self.N):
            if self.status[i] != ST_PERMIT or self.permit_ok[i] or not self._rm(i):
                continue
            if self.announce[i] > t:
                continue
            if pol.air_cooling_rm and self.cool[i] != AIR:
                self.cool[i] = AIR
                self.water_plan[i] = 0.0
                if self.grid[i] in (1, 2):  # la solicitud (o la reserva) crece por el mayor PUE
                    new = self._req(i)
                    if self.grid[i] == 2:
                        self.headroom[COMMUNE_NODE[self.commune[i]]] -= new - self.req[i]
                    self.req[i] = new
            if pol.cumulative and "script" not in self._forced.get(i, {}):
                self.version[i] += 1  # cancela la resolución individual pendiente
                self.route[i] = "acumulativa"
                self.in_zone[i] = True
        if pol.cumulative:
            for k in range(1, 20):
                tt = C.POLICY_START + k * pol.window_months - 1
                if tt < C.N_MONTHS:
                    self.events[tt].append(("zone_eval", -1, 0))

    def _zone_eval(self, t):
        """Evaluación conjunta: cuánta red y agua quedan en cada zona."""
        pol = self.policy
        water_used = np.zeros(NA)
        for i in range(self.N):
            a = COMMUNE_AQ[self.commune[i]] if self.commune[i] >= 0 else -1
            if a >= 0 and self.cool[i] != AIR and self.permit_ok[i] and self.status[i] != ST_CANCEL:
                water_used[a] += self._avg_water_ls(i)
        for n in range(NN):
            pend = [i for i in range(self.N) if self.in_zone[i] and not self.permit_ok[i]
                    and self.status[i] != ST_CANCEL and COMMUNE_NODE[self.commune[i]] == n]
            if not pend:
                continue
            pend.sort(key=lambda i: self.announce[i])
            queued_other = sum(self.req[j] for j in self.queue[n] if j not in pend)
            future = sum(mw for date, mw, _ in C.GRID_NODES[n].expansions
                         if C.ym(date) <= t + 24 and C.ym(date) > t)
            avail = self.headroom[n] - queued_other + future
            for i in pend:
                own = self.req[i] if self.grid[i] == 2 else 0.0
                a = COMMUNE_AQ[self.commune[i]]
                water_ok = True
                if a >= 0 and self.cool[i] != AIR and pol.water_cap_ls is not None:
                    water_ok = water_used[a] + self._avg_water_ls(i) <= pol.water_cap_ls
                    if not water_ok and self.u[i, 6] < 0.8:
                        self.cool[i] = AIR
                        self.water_plan[i] = 0.0
                        water_ok = True
                need = self._req(i)
                if need <= avail + own and water_ok:
                    avail -= need - own
                    if a >= 0 and self.cool[i] != AIR:
                        water_used[a] += self._avg_water_ls(i)
                    self.in_zone[i] = False
                    self.pac[i] = True
                    self.routes_2027["acumulativa"] += 1
                    self.fuel_declared.append(float(self.fuel[i]))
                    self._schedule(t + max(1, int(6 * pol.permit_speed)), "permit_done", i)
                    if self.grid[i] == 2 and need > self.req[i]:
                        self.headroom[n] -= need - self.req[i]
                        self.req[i] = need
                    elif self.grid[i] == 1:  # prioridad en la cola: ya está planificado
                        self.queue[n].remove(i)
                        self.queue[n].insert(0, i)
                else:
                    u = self.u_month[i, t]
                    if u < 0.55 and not self.fixed_site[i]:
                        c_new = self._choose_commune(i, t, exclude_node=n)
                        if c_new is not None:
                            self._relocate(i, t, c_new)
                            continue
                    if u > 0.85:
                        self._cancel(i, t)

    def _avg_water_ls(self, i) -> float:
        v = self.v
        wue = {EVAP: v["wue_evap"], AIR: v["wue_air"], HYBRID: v["wue_hybrid"]}[int(self.cool[i])]
        return float(self.it[i] * self.lfmax[i] * self._pue(self.cool[i]) * 1000 * wue / 3600)

    # ------------------------------------------------------------------ bucle principal
    def run(self) -> Run:
        v, pol, P = self.v, self.policy, self.P
        self._active = np.zeros(P["n"])
        frame_set = set(FRAME_T.tolist()) if self.user_dc is not None or P["n"] > NAG else set()
        y_acc = defaultdict(lambda: np.zeros(NC))
        y_flat = defaultdict(float)
        wue_base = np.array([v["wue_evap"], v["wue_air"], v["wue_hybrid"]])
        pue_amp = np.array([(v["peak_pue_ratio"] - 1) * 0.6, v["peak_pue_ratio"] - 1,
                            (v["peak_pue_ratio"] - 1) * 0.8])
        b = v["wue_summer_factor"] - 1
        noncd_mwh = np.array([c.pop for c in C.COMMUNES]) * v["noncd_mwh_per_person"]
        nuis_base = None
        for t in range(C.N_MONTHS):
            m = t % 12
            yi = t // 12
            if t == C.POLICY_START:
                self._policy_switch(t)
            for ni, mw in self.expansions.get(t, []):
                self.headroom[ni] += mw
                self._allocate(ni, t)
            for kind, i, ver in self.events.pop(t, []):
                self._handle(kind, i, ver, t)
            if t % 3 == 0:
                self._waiting_decisions(t)
            # ---- física mensual (vectorizada)
            st = self.status
            op = st == ST_OPER
            age = np.maximum(t - self.online, 0)
            lf = np.where(op, self.lfmax * (1 - 0.65 * np.exp(-age / v["lf_ramp_months"])), 0.0)
            pue_m = self._pue(self.cool) * (1 + pue_amp[self.cool] * SEASON[m])
            fac = self.it * lf * pue_m  # MW eléctricos
            wls = fac * 1000 * wue_base[self.cool] * (1 + b * SEASON[m]) / 3600  # L/s
            com = np.where(self.commune >= 0, self.commune, 0)
            mw_c = np.bincount(com, weights=fac, minlength=NC)
            wl_c = np.bincount(com, weights=wls, minlength=NC)
            y_acc["mwh"] += mw_c * 730
            y_acc["water_m3"] += wl_c * 730 * 3.6
            rm_mw = float(mw_c[COMMUNE_RM].sum())
            y_flat["peak_rm"] = max(y_flat["peak_rm"], rm_mw)
            rm_ls = float(wl_c[COMMUNE_RM].sum())
            y_flat["water_peak_ls_rm"] = max(y_flat["water_peak_ls_rm"], rm_ls)
            y_flat["google_m3"] += float(wls[GOOGLE_Q].sum()) * 730 * 3.6
            y_flat["google_mwh"] += float(fac[GOOGLE_Q].sum()) * 730
            # diésel: pruebas mensuales + apagones del nodo
            gen_mw = np.where(op, 1.1 * self.it, 0.0)
            out_h = self.outage_hours[COMMUNE_NODE[com], t]
            diesel_mwh = gen_mw * 0.5 * v["test_hours_year"] / 12 + fac * out_h
            y_acc["nox_t"] += np.bincount(com, weights=diesel_mwh * v["nox_g_per_kwh"] / 1000,
                                          minlength=NC)
            y_flat["diesel_hours"] += float(v["test_hours_year"] / 12 * op.sum()
                                            + (out_h * op).sum())
            # ---- acuíferos
            for a in range(NA):
                aq = C.AQUIFERS[a]
                ramp = max(0.0, min(1.0, (t - C.NOW) / (C.N_MONTHS - C.NOW)))
                trend = (aq.base_trend_m_yr + self.aq_anom[a, yi]
                         - self.recharge_cut * ramp * aq.recharge_m_yr) / 12
                dc_m3 = float(wl_c[COMMUNE_AQ == a].sum()) * 730 * 3.6
                self.aq_level[a] += trend - dc_m3 / (aq.storage_mm3_per_m * 1e6)
                self.aq_level_nodc[a] += trend
            seas = 0.4 * math.cos(2 * math.pi * (m - 8) / 12)
            hq = self.aq_level[0] + seas
            y_flat["wetland_stress"] += float(hq < -2.5)
            y_flat["wetland_stress_nodc"] += float(self.aq_level_nodc[0] + seas < -2.5)
            # ---- beneficios y opinión
            build = st == ST_BUILD
            jobs_b = np.where(build, np.minimum(self.capex * v["jobs_build_per_musd"], 1500), 0)
            jobs_o = np.where(op, np.clip(20 + 0.5 * self.it, 20, 200), 0)
            jobs_c = np.bincount(com, weights=jobs_b + jobs_o, minlength=NC)
            muni = np.where(op, np.minimum(0.0035 * 0.4 * self.capex * 1e6, PATENTE_CAP_USD)
                            + 0.4 * 0.011 * 0.15 * self.capex * 1e6, 0.0)
            muni_c = np.bincount(com, weights=muni, minlength=NC)
            fund_c = np.zeros(NC)
            if t >= C.POLICY_START and pol.community_fund_usd_mw > 0:
                fund_c = np.bincount(com, weights=np.where(op, self.it, 0)
                                     * pol.community_fund_usd_mw, minlength=NC)
            benefit = (jobs_c * v["local_hire_share"] / HOUSEHOLDS * 1000 * 0.04
                       + (muni_c + fund_c) / HOUSEHOLDS / 100)
            nuis_base = (1 + 0.5 * np.minimum(np.maximum(self.fuel, 0) / 700, 2.0)
                         + 1.5 * self.hv + 0.3 * (self.cool == AIR))
            size_f = np.where(self.it < 30, self.it / 30, np.sqrt(self.it / 30))
            size_f = np.minimum(size_f, 4.0)
            inten = STAGE_WEIGHT[st] * size_f * nuis_base
            site_i = np.bincount(self.site, weights=inten, minlength=P["n_sites"])
            exposure = P["K"] @ site_i
            # agua percibida: derecho o caudal de diseño (o el real si hay transparencia)
            live = (st != ST_NONE) & (st != ST_CANCEL) & (self.cool != AIR)
            if self.transparency_on:
                perceived = np.where(op, wls, np.where(live, self.water_plan * 0.29, 0))
            else:
                perceived = np.where(live, np.maximum(self.water_plan, wls), 0)
            perc_c = np.bincount(com, weights=perceived, minlength=NC)
            res_ls = HOUSEHOLDS * v["liters_household_day"] / 86400
            water_c = perc_c / res_ls * np.where(COMMUNE_AQ >= 0, 1.5, 0.5)
            share_c = mw_c * 730 / (mw_c * 730 + noncd_mwh / 12)
            sac_c = 0.4 * share_c
            ca = P["commune"]
            zz = (v["op_intercept"] + v["op_w_nuisance"] * P["sens"] * exposure
                  + v["op_w_water"] * P["sens"] * water_c[ca]
                  + v["op_w_saturation"] * sac_c[ca] - v["benefit_weight"] * P["val"] * benefit[ca]
                  + self.trust[ca])
            target = 1 / (1 + np.exp(-zz))
            mean_c = np.bincount(ca, weights=self.opinion * P["w"], minlength=NC) / W_BY_COMMUNE
            self.opinion += v["opinion_speed"] * (target - self.opinion) + v["op_contagion"] * (
                mean_c[ca] - self.opinion)
            self._active = (self.opinion > P["theta"]).astype(float)
            self.conflict = np.bincount(ca, weights=self._active * P["w"],
                                        minlength=NC) / W_BY_COMMUNE
            if t in frame_set:
                self._record_frame(fac, wls, muni, jobs_b + jobs_o)
            self.trust = np.clip(self.trust * v["trust_decay"], -0.5, 1.2)
            # ---- registros de mitad y fin de año
            if m == 5:
                self.rec["it_chile_jun"][yi] = float(self.it[op].sum())
                self.rec["it_rm_jun"][yi] = float(self.it[op & COMMUNE_RM[com]].sum())
                self.rec["n_dc_jun"][yi] = self._count_sites(op)
            if m == 11:
                self.rec["demand_rm_dec"][yi] = rm_mw
                self.rec["demand_chile_dec"][yi] = float(mw_c.sum())
                self._record_year(yi, t, y_acc, y_flat, mw_c, wl_c, jobs_c, jobs_b, jobs_o,
                                  muni_c, fund_c, op, build, com)
                y_acc = defaultdict(lambda: np.zeros(NC))
                y_flat = defaultdict(float)
        return self

    def _record_frame(self, fac, wls, muni, jobs):
        """Cuadro trimestral: opinión de los hogares de muestra y estado del data center."""
        f, ui = self.frames, self.user_i
        f["op"].append(self.opinion[self.P["n_real"]:].astype(np.float32))
        f["conflict"].append(self.conflict.copy())
        if ui >= 0:
            st = int(self.status[ui])
            if self.lit_active[ui] and st in (ST_PERMIT, ST_WAIT):
                st = ST_LITIG  # en tribunales manda sobre "esperando red" para este seguimiento
            f["status"].append(st)
            f["mw"].append(float(fac[ui]))
            f["wls"].append(float(wls[ui]))
            f["jobs"].append(float(jobs[ui]))
            f["muni"].append(float(muni[ui]))
            f["air"].append(bool(self.cool[ui] == AIR))

    def _handle(self, kind, i, ver, t):
        if kind == "zone_eval":
            self._zone_eval(t)
            return
        if kind == "announce":
            self._announce(i, t)
            return
        if kind.startswith("script_"):
            self._script(kind[7:], i, ver, t)
            return
        if ver != self.version[i] or self.status[i] == ST_CANCEL:
            return
        if kind == "permit_done":
            self._permit_done(i, t)
        elif kind == "verdict":
            self._verdict(i, t)
        elif kind == "build_done":
            self._build_done(i, t)
        elif kind == "redesign_done":
            self._design(i, t)
            self._start_permit(i, t, t)
            self._request_grid(i, t)

    def _script(self, kind, i, arg, t):
        """Eventos documentados (modo anclado)."""
        if kind == "approve":
            route, allow_lit = arg
            self.route[i] = route
            self.version[i] += 1
            self._permit_done(i, t, route=route, allow_lit=allow_lit)
        elif kind == "litigate":
            self._file_lawsuit(i, t, paused=arg)
        elif kind == "verdict":
            self._verdict(i, t, annul=arg)
        elif kind == "redesign":
            self.cool[i] = AIR
            self.water_plan[i] = 0.0
            self.status[i] = ST_PERMIT
            self.route[i] = arg
            self._request_grid(i, t)

    def _count_sites(self, op) -> int:
        """Cuenta campus (las fases de un mismo sitio son 1 DC)."""
        sites = set()
        for i in np.nonzero(op)[0]:
            key = C.PROJECTS[i].site if i < NK and C.PROJECTS[i].site else f"p{i}"
            sites.add(key)
        return len(sites)

    def _record_year(self, yi, t, y_acc, y_flat, mw_c, wl_c, jobs_c, jobs_b, jobs_o, muni_c,
                     fund_c, op, build, com):
        r, v = self.rec, self.v
        st = self.status
        it_op = np.where(op, self.it, 0.0)
        it_c = np.bincount(com, weights=it_op, minlength=NC)
        r["c_it"][:, yi] = it_c
        r["it_chile"][yi] = it_c.sum()
        r["it_rm"][yi] = it_c[COMMUNE_RM].sum()
        r["n_dc"][yi] = self._count_sites(op)
        r["c_ndc"][:, yi] = np.bincount(com, weights=op.astype(float), minlength=NC)
        demand_c = y_acc["mwh"] / 8760
        r["c_demand"][:, yi] = demand_c
        r["demand_chile"][yi] = demand_c.sum()
        r["demand_rm"][yi] = demand_c[COMMUNE_RM].sum()
        r["peak_rm"][yi] = y_flat["peak_rm"]
        noncd = np.array([c.pop for c in C.COMMUNES]) * v["noncd_mwh_per_person"]
        r["c_share"][:, yi] = y_acc["mwh"] / (y_acc["mwh"] + noncd)
        water_ls_c = y_acc["water_m3"] / (365 * 86400) * 1000
        r["c_water_ls"][:, yi] = water_ls_c
        r["water_ls_rm"][yi] = water_ls_c[COMMUNE_RM].sum()
        r["water_peak_ls_rm"][yi] = y_flat["water_peak_ls_rm"]
        r["google_water_ml"][yi] = y_flat["google_m3"] / 1000
        r["google_power_mw"][yi] = y_flat["google_mwh"] / 8760
        waiting = (self.grid == 1) & (st != ST_CANCEL) & (st != ST_NONE)
        r["waitlist_mw"][yi] = self.req[waiting].sum()  # MW de conexión pedidos, como el CEN
        r["waitlist_n"][yi] = waiting.sum()
        r["c_waitlist"][:, yi] = np.bincount(com, weights=np.where(waiting, self.req, 0),
                                             minlength=NC)
        year = C.YEAR0 + yi
        sys_twh = v["system_twh_2025"] * (1 + v["system_growth"]) ** (year - 2025)
        share = r["demand_chile"][yi] * 8.76 / 1000 / sys_twh
        r["dc_share_national"][yi] = share
        # Presión sobre la tarifa: la demanda de Antofagasta no cuenta, porque allí sobra energía
        # solar (vertimiento, informe A3), la misma premisa del incentivo al norte.
        y25 = 2025 - C.YEAR0
        r["px_mw"][yi] = r["demand_chile"][yi] - demand_c[ANTOF]
        r["px_share"][yi] = r["px_mw"][yi] * 8.76 / 1000 / sys_twh
        base_px = r["px_share"][y25] if year > 2025 else r["px_share"][yi]
        d_mw = max(0.0, r["px_mw"][yi] - r["px_mw"][min(yi, y25)])
        grid_pct = 0.1 * v["reg_alloc_share"] * 0.1 * v["grid_cost_musd_per_mw"] * d_mw / 700
        r["bill_pct"][yi] = 100 * (0.7 * v["price_elasticity"]
                                   * max(0.0, r["px_share"][yi] - base_px) + grid_pct)
        r["c_nox"][:, yi] = y_acc["nox_t"]
        r["nox_t"][yi] = y_acc["nox_t"].sum()
        r["diesel_hours"][yi] = y_flat["diesel_hours"]
        for k in ("litigations", "annulments", "relocations", "cancellations",
                  "invest_realized", "invest_lost"):
            r[k][yi] = self.cum[k]
        r["jobs_build"][yi] = jobs_b.sum()
        r["jobs_oper"][yi] = jobs_o.sum()
        r["c_jobs_local"][:, yi] = jobs_c * v["local_hire_share"]
        r["c_muni_usd"][:, yi] = muni_c
        r["c_fund_usd"][:, yi] = fund_c
        r["c_conflict"][:, yi] = self.conflict
        r["conflict_rm"][yi] = float((self.conflict * HOUSEHOLDS)[COMMUNE_RM].sum()
                                     / HOUSEHOLDS[COMMUNE_RM].sum())
        P = self.P
        active_sites = np.zeros(P["n_sites"], dtype=bool)
        big = ((st == ST_OPER) | (st == ST_BUILD)) & (self.it >= 10)
        active_sites[self.site[big]] = True
        near = P["near500"][:, active_sites].any(axis=1)
        h500 = np.bincount(P["commune"], weights=near * P["w"], minlength=NC)
        r["c_h500"][:, yi] = h500
        r["households_500m"][yi] = h500[COMMUNE_RM].sum()
        r["mw_antofagasta"][yi] = it_c[ANTOF]
        r["mw_outside_rm"][yi] = it_c[~COMMUNE_RM].sum()
        r["aq_level"][:, yi] = self.aq_level
        r["aq_dc_drawdown"][:, yi] = self.aq_level_nodc - self.aq_level
        r["wetland_stress"][yi] = y_flat["wetland_stress"]
        r["wetland_stress_nodc"][yi] = y_flat["wetland_stress_nodc"]
        rep = st[:NK].copy()
        rep[(self.grid[:NK] == 1) & (rep == ST_PERMIT)] = ST_WAIT
        r["p_status"][:, yi] = rep
        r["p_commune"][:, yi] = self.commune[:NK]


def simulate(policy: Policy = STATUS_QUO, seed: int = 0, mode: str = "anchored",
             params: dict | None = None) -> Run:
    return Run(policy, seed, mode, params).run()


def base_run(policy: Policy = STATUS_QUO, seed: int = 0, mode: str = "anchored") -> Run:
    return Run(policy, seed, mode, base_values()).run()
