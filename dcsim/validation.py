"""¿Reproduce el modelo lo que ya pasó?

Corre la historia 2012–2026 en modo libre (el modelo decide cuándo se aprueba, se
construye, se litiga o espera cada proyecto) y compara con datos observados.

Cada chequeo dice si es *validación* (el modelo no fue ajustado para ese dato) o
*calibración* (un parámetro se ajustó para reproducirlo), para no inflar la confianza.
"""

from __future__ import annotations

import numpy as np

from . import catalog as C
from .model import REAL_STATUS_CODE, ST_LITIG, ST_PERMIT
from .montecarlo import run_ensemble
from .policy import STATUS_QUO

OBS = C.OBSERVED


def _yi(y: int) -> int:
    return C.YEARS.index(y)


def _band(series, y):
    return {k: series[k][_yi(y)] for k in ("p5", "p50", "p95")}


def _check(id_, label, question, observed, sim, unit, src, kind, passed, note=""):
    return {"id": id_, "label": label, "question": question, "observed": observed, "sim": sim,
            "unit": unit, "src": src, "kind": kind, "pass": bool(passed), "note": note}


def _within(obs, sim, tol):
    return abs(sim["p50"] - obs) <= tol * obs or sim["p5"] <= obs <= sim["p95"]


def run_validation(n: int = 200, use_cache: bool = True) -> dict:
    res = run_ensemble(STATUS_QUO, n=n, mode="free", use_cache=use_cache)
    S = res["series"]
    checks = []

    o = OBS["rm_demand_2021"]["value"]
    sim = _band(S["demand_rm_dec"], 2021)
    checks.append(_check(
        "rm_2021", "Consumo eléctrico de los data centers de la RM, fin de 2021",
        "¿Cuánta electricidad usaban los DC de Santiago en 2021?", o, sim, "MW",
        OBS["rm_demand_2021"]["src"], "validación", _within(o, sim, 0.2)))
    o = OBS["rm_demand_2025"]["value"]
    sim = _band(S["demand_rm_dec"], 2025)
    checks.append(_check(
        "rm_2025", "Consumo eléctrico de los data centers de la RM, fin de 2025",
        "¿Cuánta electricidad usaban a fines de 2025?", o, sim, "MW",
        OBS["rm_demand_2025"]["src"], "validación", _within(o, sim, 0.2)))
    o = OBS["chile_demand_2025"]["value"]
    sim = _band(S["demand_chile_dec"], 2025)
    checks.append(_check(
        "chile_2025", "Consumo eléctrico de los data centers de todo Chile, 2025",
        "¿Y en todo el país?", o, sim, "MW", OBS["chile_demand_2025"]["src"], "validación",
        _within(o, sim, 0.2), "Las fuentes miden distinto: el CEN incluye más que la RM."))
    o = OBS["rm_it_2026"]["value"]
    sim = _band(S["it_rm_jun"], 2026)
    checks.append(_check(
        "it_2026", "Capacidad instalada de data centers en Santiago, mediados de 2026",
        "¿Cuántos MW de servidores había instalados en la RM?", o, sim, "MW TI",
        OBS["rm_it_2026"]["src"], "calibración", _within(o, sim, 0.15),
        "Colliers cuenta 255 MW para todo Chile con otra definición. Parte del inventario son "
        "DC sin nombre público dimensionados para cuadrar. El modelo construye Google "
        "Cerrillos antes de 2026 en parte de las corridas; en la realidad un fallo lo detuvo."))
    lo, hi = OBS["n_dc_2026"]["low"], OBS["n_dc_2026"]["high"]
    sim = _band(S["n_dc_jun"], 2026)
    checks.append(_check(
        "ndc_2026", "Número de data centers operando, mediados de 2026",
        "¿Cuántos data centers había?", {"low": lo, "high": hi}, sim, "DC",
        OBS["n_dc_2026"]["src"], "calibración", lo - 2 <= sim["p50"] <= hi + 2,
        "El inventario incluye DC sin nombre público para cuadrar con Colliers/GPS."))
    o = OBS["google_water_2024"]["value"]
    sim = _band(S["google_water_ml"], 2024)
    checks.append(_check(
        "google_water", "Agua usada por Google Quilicura en 2024",
        "¿Cuánta agua consumió el DC de Google en Quilicura?", o, sim, "millones de litros",
        OBS["google_water_2024"]["src"], "calibración", _within(o, sim, 0.1),
        "El agua por kWh (1,74 L/kWh) se calibró con este mismo dato."))
    o = OBS["google_power_2024"]["value"]
    sim = _band(S["google_power_mw"], 2024)
    checks.append(_check(
        "google_power", "Potencia media de Google Quilicura en 2024",
        "¿Cuánta electricidad usó en promedio?", o, sim, "MW",
        OBS["google_power_2024"]["src"], "validación", _within(o, sim, 0.1)))
    o = OBS["quilicura_share"]["value"]
    q = C.COMMUNE_IDX["quilicura"]
    cs = res["communes"]["c_share"]
    sim = {k: round(100 * cs[k][q][_yi(2025)], 1) for k in ("p5", "p50", "p95")}
    checks.append(_check(
        "quilicura_share", "Parte del consumo eléctrico de Quilicura que usan los DC",
        "¿Qué fracción de la electricidad de Quilicura se la llevan los data centers?", o, sim,
        "%", OBS["quilicura_share"]["src"], "calibración", _within(o, sim, 0.1),
        "El consumo comunal sin DC se calibró con este dato."))
    o = OBS["waitlist_2026"]["value"]
    sim = _band(S["waitlist_mw"], 2026)
    checks.append(_check(
        "waitlist", "Data centers esperando conexión a la red, 2026",
        "¿Cuántos MW quedaron en lista de espera del CEN?", o, sim, "MW",
        OBS["waitlist_2026"]["src"], "calibración", _within(o, sim, 0.15),
        "La capacidad libre de cada nodo es un supuesto ajustado a este dato."))
    o = OBS["waitlist_2026"]["n"]
    sim = _band(S["waitlist_n"], 2026)
    checks.append(_check(
        "waitlist_n", "Número de proyectos en lista de espera, 2026",
        "¿Cuántos proyectos esperaban?", o, sim, "proyectos", OBS["waitlist_2026"]["src"],
        "calibración", abs(sim["p50"] - o) <= 1))
    o = OBS["litigations_2012_2026"]["value"]
    sim = _band(S["litigations"], 2026)
    checks.append(_check(
        "litigations", "Litigios ambientales contra data centers, 2012–2026",
        "¿Cuántas veces los vecinos llevaron un DC a tribunales?", o, sim, "casos",
        OBS["litigations_2012_2026"]["src"], "calibración", sim["p5"] <= o <= sim["p95"]))
    share = S["dc_share_national"]
    sim = {k: round(100 * share[k][_yi(2025)], 2) for k in ("p5", "p50", "p95")}
    checks.append(_check(
        "national_share", "Parte del consumo eléctrico nacional que usan los DC, 2025",
        "¿Qué fracción de la electricidad de Chile usan los data centers?",
        {"low": 2, "high": 3}, sim, "%", "Ministerio de Energía: 2–3% del consumo nacional",
        "validación", 1.8 <= sim["p50"] <= 3.3))
    # Patrón de conflicto: ¿dónde surgió oposición organizada?
    conf = np.array(res["communes"]["c_conflict"]["p50"])[:, _yi(2026)]
    top = [C.COMMUNES[i].id for i in np.argsort(-conf)[:4]]
    real = OBS["organized_opposition"]["communes"]
    hits = len(set(top) & set(real))
    checks.append(_check(
        "conflict_pattern", "Comunas donde surge oposición organizada",
        "¿El modelo identifica dónde se organizaron los vecinos?",
        [C.COMMUNES[C.COMMUNE_IDX[c]].name for c in real],
        {"top4": [C.COMMUNES[C.COMMUNE_IDX[c]].name for c in top], "hits": hits}, "comunas",
        OBS["organized_opposition"]["src"], "validación", hits >= 3,
        "El modelo no sabe dónde hubo conflicto: lo deduce de la cercanía, el agua y la "
        "acumulación."))
    # Estado de cada proyecto conocido
    probs = np.array(res["projects"]["status_prob"])[:, _yi(2026), :]
    rows, ok = [], 0
    for i, p in enumerate(C.PROJECTS):
        if p.real_status is None:
            continue
        real_code = REAL_STATUS_CODE[p.real_status]
        mode_code = int(probs[i].argmax())
        hit = mode_code == real_code or (real_code == ST_PERMIT and mode_code == ST_LITIG)
        ok += hit
        rows.append({"id": p.id, "name": p.name, "real": p.real_status, "model": mode_code,
                     "p_real": round(float(probs[i, real_code]), 2), "hit": bool(hit),
                     "anonymous": p.anonymous})
    acc = ok / len(rows)
    named = [r for r in rows if not r["anonymous"]]
    acc_named = sum(r["hit"] for r in named) / len(named)
    checks.append(_check(
        "status", "Estado de cada proyecto conocido a noviembre de 2026",
        "¿Acierta el modelo qué proyectos están operando, en obra, en trámite o esperando?",
        len(rows), {"accuracy": round(100 * acc, 1), "accuracy_named": round(100 * acc_named, 1),
                    "rows": rows}, "%", "Informe (estado a nov-2026)", "validación", acc >= 0.8,
        "Se compara el estado más probable en 200 simulaciones con el estado real."))
    return {"checks": checks, "n": res["meta"]["n"],
            "passed": sum(c["pass"] for c in checks), "total": len(checks),
            "series": {k: res["series"][k] for k in ("demand_rm_dec", "it_chile_jun",
                                                      "waitlist_mw", "litigations")}}


if __name__ == "__main__":
    out = run_validation()
    for c in out["checks"]:
        flag = "OK  " if c["pass"] else "FAIL"
        sim = c["sim"]
        if isinstance(sim, dict) and "p50" in sim:
            s = f"{sim['p50']} [{sim['p5']}–{sim['p95']}]"
        elif isinstance(sim, dict) and "accuracy" in sim:
            s = f"{sim['accuracy']}% (con nombre: {sim['accuracy_named']}%)"
        else:
            s = str(sim)
        print(f"{flag} [{c['kind']:11s}] {c['label']}: observado={c['observed']} modelo={s}")
    print(f"{out['passed']}/{out['total']} chequeos OK")
