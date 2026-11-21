"""¿Se mantienen los hallazgos si cambian los supuestos?

    uv run python -m dcsim.sensitivity     # 76.500 simulaciones, ~16 min en 10 núcleos

Escribe cache/sensitivity.json, que lleva la huella del código como findings.json.

En cada futuro se sortean 13 parámetros (``sample=True`` en params.py). Los demás supuestos
quedan en su valor central. Este análisis los mueve:

* Uno a la vez: cada supuesto fijo va al extremo bajo y luego al alto de su rango, con todo lo
  demás igual (mismas semillas y los mismos 13 sorteos de cada futuro).
* Todos juntos: en cada futuro, además de los 13 de siempre, se sortean todos los supuestos
  fijos dentro de su rango, con un flujo aleatorio aparte (``[semilla, 9]``).

Para cada hallazgo de la portada se repite el cálculo de dcsim/findings.py (mismas políticas,
contrafactuales, años, medianas y comparaciones por semilla) y se ve si la afirmación se
mantiene. Un extremo puede dejar al modelo lejos de la historia observada; por eso cada ajuste
también corre la historia 2012–2026 sin anclar y se marca si sigue reproduciendo los datos.

Divisiones por cero: si la mediana de juicios con la demanda de hoy fuera 0, el "boom" divide
por 0,5 (menos de un juicio); en modo anclado no pasa, porque los dos juicios históricos ya
están. Las demás cifras de referencia (MW, conflicto) se acotan por debajo de forma parecida.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace

import numpy as np

from . import catalog as C
from .model import Run
from .montecarlo import CACHE_DIR, _code_hash
from .params import PARAMS, sample_values
from .policy import HYPOTHESIS_SCENARIOS, SCENARIOS, STATUS_QUO

OUT = CACHE_DIR / "sensitivity.json"
N_OAT = 100  # semillas por configuración en cada extremo
N_JOINT = 400  # semillas con todos los supuestos sorteados a la vez
CHUNK = 25  # semillas por tarea
FACTORS = [p for p in PARAMS if not p.sample]  # los supuestos que cada futuro deja fijos
FINDING_IDS = ["paquete", "permisos", "boom", "cerrillos", "lampa", "transparencia"]

CER = C.PROJECT_IDX["google_cerrillos"]
LAMPA = C.COMMUNE_IDX["lampa"]
Y25, Y26, Y30, Y35 = (C.YEARS.index(y) for y in (2025, 2026, 2030, 2035))

# Configuraciones que necesitan los seis hallazgos: (política, contrafactual, modo).
# "sq" sirve también como demanda de 5 proyectos al año: con demand_rate=5.0 la corrida es
# idéntica a la de STATUS_QUO (tests/test_sensitivity.py lo comprueba).
CONFIGS = {
    "sq": (STATUS_QUO, None, "anchored"),
    "paquete": (SCENARIOS["paquete"]["policy"], None, "anchored"),
    "permisos": (replace(STATUS_QUO, permit_speed=0.25), None, "anchored"),
    "boom": (replace(STATUS_QUO, demand_rate=10.0), None, "anchored"),
    "lampa": (STATUS_QUO, {"campo_lampa": {"generic_site": True}}, "anchored"),
    "transparencia": (HYPOTHESIS_SCENARIOS["solo_transparencia"], None, "anchored"),
    "fondo": (HYPOTHESIS_SCENARIOS["solo_fondo"], None, "anchored"),
    "libre": (STATUS_QUO, None, "free"),
    "cer_aire": (STATUS_QUO, {"google_cerrillos": {"cooling": "aire", "water_right_ls": 0}},
                 "free"),
}
METRICS = ["it_chile_2035", "invest_realized_2035", "invest_lost_2035", "conflict_rm_2035",
           "litigations_2035", "water_ls_rm_2035", "it_rm_2030", "lampa_conflict_2035",
           "cer_lit", "litigations_2026", "demand_rm_dec_2025", "waitlist_mw_2026",
           "it_rm_jun_2026"]
IX = {k: j for j, k in enumerate(METRICS)}
PAQUETE_KEYS = [("it_chile_2035", 1), ("invest_realized_2035", 1), ("invest_lost_2035", -1),
                ("conflict_rm_2035", -1), ("litigations_2035", -1), ("water_ls_rm_2035", -1)]

# Coherencia con la historia (modo libre, la misma corrida de cada ajuste)
OBS = C.OBSERVED
HINDCAST = {"litigations_2026": (1, 4),
            "demand_rm_dec_2025": (OBS["rm_demand_2025"]["value"], 0.25),
            "waitlist_mw_2026": (OBS["waitlist_2026"]["value"], 0.25),
            "it_rm_jun_2026": (OBS["rm_it_2026"]["value"], 0.25)}
HINDCAST_RULE = (
    "Un ajuste es coherente con la historia si, al correr 2012–2026 sin anclar (el modelo genera "
    "la historia solo), la mediana de los juicios a fines de 2026 queda entre 1 y 4 (hubo 2) y "
    "las medianas del consumo de los data centers de la RM a fines de 2025 (dato: 260 MW), de "
    "los MW esperando red en 2026 (1.420 MW) y de la capacidad instalada en Santiago a mediados "
    "de 2026 (311 MW) quedan a menos de 25% del dato.")

FINDINGS = {
    "paquete": {
        "fmt": "pct",
        "claim": "Enfriamiento por aire, fondo comunitario e incentivo al norte mejoran a la vez "
                 "MW operando, inversión, inversión perdida, conflicto, juicios y agua (2035).",
        "criterion": "Se mantiene si el paquete es igual o mejor en las seis cifras en al menos "
                     "la mitad de los futuros.",
        "metric": "Futuros en que el paquete es igual o mejor en las seis cifras"},
    "permisos": {
        "fmt": "pct",
        "claim": "Permisos 4 veces más rápidos casi no suman data centers en Santiago al 2030: "
                 "el cuello de botella es la red.",
        "criterion": "Se mantiene si los MW operando en la RM en 2030 suben menos de 5%.",
        "metric": "Cambio de los MW operando en la RM en 2030"},
    "boom": {
        "fmt": "ratio",
        "claim": "Con el doble de proyectos nuevos al año, los juicios crecen proporcionalmente "
                 "más que los MW conectados.",
        "criterion": "Se mantiene si los juicios a 2035 se multiplican por más que los MW "
                     "operando (cociente mayor que 1).",
        "metric": "Cuántas veces más crecen los juicios que los MW operando (2035)"},
    "cerrillos": {
        "fmt": "pair_pct",
        "claim": "Si Google hubiera enfriado Cerrillos con aire, la probabilidad de juicio habría "
                 "sido mucho menor.",
        "criterion": "Se mantiene si con aire la probabilidad de juicio baja al menos 25 puntos y "
                     "queda en la mitad o menos.",
        "metric": "Probabilidad de juicio contra Google Cerrillos: con agua y con aire"},
    "lampa": {
        "fmt": "pct",
        "claim": "Alejar Campo de Datos Lampa de las casas baja fuerte el conflicto de toda la "
                 "comuna.",
        "criterion": "Se mantiene si los hogares movilizados en Lampa (2035) bajan 25% o más.",
        "metric": "Baja de los hogares movilizados en Lampa (2035)"},
    "transparencia": {
        "fmt": "pair_pct",
        "claim": "Publicar el uso real de agua baja el conflicto en una magnitud parecida a la de "
                 "un fondo comunitario de US$20.000 por MW al año.",
        "criterion": "Se mantiene si las dos reglas bajan el conflicto y la transparencia logra "
                     "al menos dos tercios de la baja del fondo.",
        "metric": "Cambio de los hogares movilizados en la RM (2035): transparencia y fondo"},
}


# ---------------------------------------------------------------------------
# Parámetros de cada futuro
# ---------------------------------------------------------------------------
def params_for(seed: int, setting: tuple) -> dict:
    """Parámetros de un futuro: los 13 sorteos de siempre y luego el ajuste.

    ``("base",)`` deja todo como en una corrida normal, ``("oat", clave, valor)`` cambia un
    supuesto y ``("joint",)`` sortea todos los supuestos fijos en su rango con otro flujo.
    """
    v = sample_values(np.random.default_rng([seed, 1]))  # lo mismo que hace Run sin params
    if setting[0] == "oat":
        v[setting[1]] = setting[2]
    elif setting[0] == "joint":
        rng = np.random.default_rng([seed, 9])
        for p in FACTORS:
            v[p.key] = float(rng.uniform(p.low, p.high))
    elif setting[0] != "base":
        raise ValueError(f"Ajuste desconocido: {setting}")
    return v


def _metrics(r: Run) -> list[float]:
    rec = r.rec
    return [rec["it_chile"][Y35], rec["invest_realized"][Y35], rec["invest_lost"][Y35],
            rec["conflict_rm"][Y35], rec["litigations"][Y35], rec["water_ls_rm"][Y35],
            rec["it_rm"][Y30], rec["c_conflict"][LAMPA, Y35], float(r.n_lit[CER]),
            rec["litigations"][Y26], rec["demand_rm_dec"][Y25], rec["waitlist_mw"][Y26],
            rec["it_rm_jun"][Y26]]


def _task(args):
    skey, setting, cname, seeds = args
    pol, ov, mode = CONFIGS[cname]
    rows, errors = [], []
    for s in seeds:
        try:
            r = Run(pol, seed=s, mode=mode, params=params_for(s, setting), overrides=ov).run()
            rows.append(_metrics(r))
        except Exception as e:  # un extremo no debe botar todo el análisis: se informa
            errors.append(f"{skey} / {cname} / semilla {s}: {type(e).__name__}: {e}")
            rows.append([np.nan] * len(METRICS))
    return skey, cname, seeds, np.array(rows, dtype=float), errors


def run_settings(settings: dict[str, tuple[tuple, int]], workers: int | None = None,
                 progress: bool = True):
    """settings: clave -> (ajuste, n semillas). Devuelve clave -> config -> (n, métricas)."""
    tasks = []
    for skey, (setting, n) in settings.items():
        for cname in CONFIGS:
            for i in range(0, n, CHUNK):
                tasks.append((skey, setting, cname, list(range(i, min(n, i + CHUNK)))))
    out = {k: {c: np.full((n, len(METRICS)), np.nan) for c in CONFIGS}
           for k, (_, n) in settings.items()}
    errors: list[str] = []
    workers = workers or os.cpu_count() or 4
    t0, done, step = time.time(), 0, max(1, len(tasks) // 20)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_task, t) for t in tasks]
        for f in as_completed(futs):
            skey, cname, seeds, rows, errs = f.result()
            out[skey][cname][seeds] = rows
            errors += errs
            done += 1
            if progress and (done % step == 0 or done == len(tasks)):
                print(f"  {done}/{len(tasks)} tareas, {time.time() - t0:.0f} s", flush=True)
    return out, errors


# ---------------------------------------------------------------------------
# Hallazgos (las mismas cuentas de dcsim/findings.py)
# ---------------------------------------------------------------------------
def _med(x) -> float:
    return float(np.nanmedian(x))


def evaluate(res: dict[str, np.ndarray]) -> dict[str, tuple]:
    """Para cada hallazgo: (valor, escalar para ordenar, ¿se mantiene?).

    ``res`` trae las métricas por configuración, con las mismas semillas en el mismo orden.
    """
    def col(c, k):
        return res[c][:, IX[k]]

    out = {}
    # 1. Paquete: futuros (pareados por semilla) en que es igual o mejor en las seis cifras.
    # Se redondea a 3 decimales, como los valores pareados de la portada que usa findings.py.
    ok = np.ones(len(res["sq"]), bool)
    valid = np.ones(len(res["sq"]), bool)
    for k, sign in PAQUETE_KEYS:
        a, b = np.round(col("paquete", k), 3), np.round(col("sq", k), 3)
        valid &= np.isfinite(a) & np.isfinite(b)
        d = a - b
        ok &= (d >= 0) if sign > 0 else (d <= 0)
    share = float(ok[valid].mean()) if valid.any() else float("nan")
    out["paquete"] = (share, share, share >= 0.5)
    # 2. Permisos 4 veces más rápidos: cambio de la mediana de MW en la RM en 2030
    n30 = _med(col("sq", "it_rm_2030"))
    r30 = (_med(col("permisos", "it_rm_2030")) - n30) / max(n30, 1e-9)
    out["permisos"] = (r30, r30, r30 < 0.05)
    # 3. Boom: juicios (cociente de medianas) frente a MW operando (cambio relativo), 2035
    lo_mw, hi_mw = _med(col("sq", "it_chile_2035")), _med(col("boom", "it_chile_2035"))
    mw_rel = (hi_mw - lo_mw) / max(lo_mw, 1e-9)
    lit_ratio = _med(col("boom", "litigations_2035")) / max(_med(col("sq", "litigations_2035")),
                                                             0.5)
    ratio = lit_ratio / max(1 + mw_rel, 1e-9)
    out["boom"] = (ratio, ratio, lit_ratio > 1 + mw_rel)
    # 4. Cerrillos (historia libre): futuros con al menos un juicio, con agua y con aire
    w, a = col("libre", "cer_lit"), col("cer_aire", "cer_lit")
    p_w = float(np.mean(w[np.isfinite(w)] > 0))
    p_a = float(np.mean(a[np.isfinite(a)] > 0))
    out["cerrillos"] = ([p_w, p_a], p_w - p_a, p_w - p_a >= 0.25 and p_a <= 0.5 * p_w)
    # 5. Lampa: baja de la mediana del conflicto en Lampa (2035) al alejar el proyecto
    cb = _med(np.round(col("sq", "lampa_conflict_2035"), 4))  # explore.py guarda 4 decimales
    cf = _med(np.round(col("lampa", "lampa_conflict_2035"), 4))
    drop = 1 - cf / cb if cb > 0 else 0.0
    out["lampa"] = (drop, drop, drop >= 0.25)
    # 6. Transparencia vs fondo: cambio relativo de la mediana del conflicto en la RM (2035)
    c0 = _med(np.round(col("sq", "conflict_rm_2035"), 3))
    rt = (_med(np.round(col("transparencia", "conflict_rm_2035"), 3)) - c0) / max(c0, 1e-9)
    rf = (_med(np.round(col("fondo", "conflict_rm_2035"), 3)) - c0) / max(c0, 1e-9)
    out["transparencia"] = ([rt, rf], abs(rt) / max(abs(rf), 1e-3),
                            rt < 0 and rf < 0 and abs(rt) >= 2 / 3 * abs(rf))
    return out


def consistent(res: dict[str, np.ndarray]) -> bool:
    """¿La historia libre de este ajuste sigue reproduciendo los datos? (ver HINDCAST_RULE)"""
    lo, hi = HINDCAST["litigations_2026"]
    ok = lo <= _med(res["libre"][:, IX["litigations_2026"]]) <= hi
    for k in ("demand_rm_dec_2025", "waitlist_mw_2026", "it_rm_jun_2026"):
        obs, tol = HINDCAST[k]
        ok = ok and abs(_med(res["libre"][:, IX[k]]) / obs - 1) <= tol
    return bool(ok)


def consistent_seeds(res: dict[str, np.ndarray]) -> np.ndarray:
    """La misma regla, futuro por futuro (para filtrar el ajuste conjunto)."""
    m = res["libre"]
    lo, hi = HINDCAST["litigations_2026"]
    ok = (m[:, IX["litigations_2026"]] >= lo) & (m[:, IX["litigations_2026"]] <= hi)
    for k in ("demand_rm_dec_2025", "waitlist_mw_2026", "it_rm_jun_2026"):
        obs, tol = HINDCAST[k]
        ok &= np.abs(m[:, IX[k]] / obs - 1) <= tol
    return ok


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------
def _r(x, nd: int = 4):
    if isinstance(x, list | tuple):
        return [_r(y, nd) for y in x]
    x = float(x)
    return round(x, nd) if np.isfinite(x) else None


def _published() -> dict:
    """Los hallazgos de la portada (para copiar el kicker y la cifra que se muestra hoy)."""
    try:
        return {f["id"]: f for f in json.loads((CACHE_DIR / "findings.json").read_text())}
    except (OSError, ValueError):
        return {}


def assemble(results: dict, factors: list, n_oat: int, n_joint: int, n_sims: int,
             seconds: float) -> dict:
    base = evaluate(results["base"])
    oat = {(p.key, end): evaluate(results[f"{p.key}:{end}"]) for p in factors
           for end in ("low", "high")}
    cons = {(p.key, end): consistent(results[f"{p.key}:{end}"]) for p in factors
            for end in ("low", "high")}
    joint = evaluate(results["joint"]) if "joint" in results else None
    pub = _published()
    findings = []
    for fid in FINDING_IDS:
        spec, p_ = FINDINGS[fid], pub.get(fid, {})
        rows, scal = [], [base[fid][1]]
        for p in factors:
            lo, hi = oat[(p.key, "low")][fid], oat[(p.key, "high")][fid]
            rows.append({"key": p.key, "low": _r(lo[0]), "high": _r(hi[0]),
                         "holds_low": bool(lo[2]), "holds_high": bool(hi[2]),
                         "consistent_low": cons[(p.key, "low")],
                         "consistent_high": cons[(p.key, "high")]})
            scal += [lo[1], hi[1]]
        ends = [(p.key, end) for p in factors for end in ("low", "high")]
        holds = sum(bool(oat[e][fid][2]) for e in ends)
        holds_c = sum(bool(oat[e][fid][2]) and cons[e] for e in ends)

        def swing(p, fid=fid):
            s = [base[fid][1], oat[(p.key, "low")][fid][1], oat[(p.key, "high")][fid][1]]
            return max(s) - min(s)

        top = sorted(factors, key=swing, reverse=True)[:3]
        findings.append({
            "id": fid, "kicker": p_.get("kicker", ""), "claim": spec["claim"],
            "criterion": spec["criterion"], "metric": spec["metric"], "fmt": spec["fmt"],
            "base": _r(base[fid][0]),
            "headline": f"{p_['stat']} {p_['stat_label']}" if p_ else "",
            "oat": rows, "range": [_r(min(scal)), _r(max(scal))],
            "holds": holds, "total": len(ends),
            "holds_consistent": holds_c, "total_consistent": sum(cons[e] for e in ends),
            "top": [{"key": p.key, "label": p.label, "low": _r(oat[(p.key, "low")][fid][1]),
                     "high": _r(oat[(p.key, "high")][fid][1])} for p in top],
            "joint": {"value": _r(joint[fid][0]) if joint else None,
                      "holds": bool(joint[fid][2]) if joint else False, "n": n_joint},
        })
    keys = ("key", "label", "unit", "base", "low", "high", "kind", "group", "src")
    return {"model": _code_hash(), "n_oat": n_oat, "n_joint": n_joint, "n_sims": n_sims,
            "seconds": round(seconds, 1), "hindcast_rule": HINDCAST_RULE,
            "factors": [{k: asdict(p)[k] for k in keys} for p in factors],
            "findings": findings}


def _fmt(fid: str, v) -> str:
    fmt = FINDINGS[fid]["fmt"]
    if v is None:
        return "—"
    if fmt == "pair_pct":
        return " / ".join(_fmt_one(x) for x in v)
    return f"x{v:.2f}" if fmt == "ratio" else _fmt_one(v)


def _fmt_one(x) -> str:
    return "—" if x is None else f"{100 * x:+.1f}%" if x < 0 else f"{100 * x:.1f}%"


def report(out: dict, results: dict) -> None:
    """Tabla legible del resultado."""
    print(f"\n{len(out['factors'])} supuestos fijos x 2 extremos, {out['n_oat']} futuros por "
          f"extremo; conjunto: {out['n_joint']} futuros. {out['n_sims']:,} simulaciones en "
          f"{out['seconds']:.0f} s.")
    print(f"Base coherente con la historia: {consistent(results['base'])}")
    inc = [f"{r['key']}:{end}" for r in out["findings"][0]["oat"] for end in ("low", "high")
           if not r["consistent_" + end]]
    print("Extremos que ya no reproducen la historia:", ", ".join(inc) or "ninguno")
    jmask = consistent_seeds(results["joint"]) if "joint" in results else None
    jc = (evaluate({c: m[jmask] for c, m in results["joint"].items()})
          if jmask is not None and jmask.any() else None)
    if jmask is not None:
        print(f"Futuros cuya historia libre coincide con los datos: base "
              f"{consistent_seeds(results['base']).mean():.0%}, conjunto {jmask.mean():.0%}")
    head = f"\n{'hallazgo':14s} {'base':>15s} {'rango OAT':>17s} {'se mantiene':>12s} " \
           f"{'(coherentes)':>13s} {'conjunto':>20s}  más influyentes"
    print(head)
    for f in out["findings"]:
        j = f["joint"]
        rng = f"[{f['range'][0]:.2f}, {f['range'][1]:.2f}]"
        print(f"{f['id']:14s} {_fmt(f['id'], f['base']):>15s} {rng:>17s} "
              f"{f['holds']:>5d}/{f['total']:<6d} {f['holds_consistent']:>5d}/"
              f"{f['total_consistent']:<7d} {_fmt(f['id'], j['value']):>15s} "
              f"{'sí' if j['holds'] else 'NO':>4s}  {', '.join(t['key'] for t in f['top'])}")
        fails = [f"{r['key']}:{end}{'' if r['consistent_' + end] else '*'}="
                 f"{_fmt(f['id'], r[end])}"
                 for r in f["oat"] for end in ("low", "high") if not r["holds_" + end]]
        if fails:
            print(f"{'':14s} no se mantiene en: {'; '.join(fails)}")
        if jc is not None:
            v, _, h = jc[f["id"]]
            print(f"{'':14s} conjunto solo con futuros coherentes con la historia "
                  f"(n={int(jmask.sum())}): {_fmt(f['id'], _r(v))} {'sí' if h else 'NO'}")
    print("(* = extremo que ya no reproduce la historia)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n-oat", type=int, default=N_OAT)
    ap.add_argument("--n-joint", type=int, default=N_JOINT)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--factors", default="", help="solo estas claves (separadas por coma)")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    factors = [p for p in FACTORS if not a.factors or p.key in a.factors.split(",")]
    settings = {"base": (("base",), a.n_oat)}
    for p in factors:
        settings[f"{p.key}:low"] = (("oat", p.key, p.low), a.n_oat)
        settings[f"{p.key}:high"] = (("oat", p.key, p.high), a.n_oat)
    if a.n_joint:
        settings["joint"] = (("joint",), a.n_joint)
    n_sims = sum(n for _, n in settings.values()) * len(CONFIGS)
    print(f"{len(settings)} ajustes x {len(CONFIGS)} configuraciones = {n_sims:,} "
          "simulaciones…", flush=True)
    t0 = time.time()
    results, errors = run_settings(settings, workers=a.workers)
    seconds = time.time() - t0
    if errors:
        print(f"\n{len(errors)} simulaciones fallaron:")
        for e in errors[:30]:
            print("  ", e)
    out = assemble(results, factors, a.n_oat, a.n_joint, n_sims, seconds)
    with open(a.out, "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, allow_nan=False)
    report(out, results)
    print("guardado en", a.out)


if __name__ == "__main__":
    main()
