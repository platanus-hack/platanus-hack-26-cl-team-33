"""Compara escenarios contra 'Como hoy' y pone a prueba las hipótesis del informe."""

from __future__ import annotations

import numpy as np

from . import catalog as C

# métrica -> (etiqueta, unidad, ¿más es mejor para la gente?)
METRICS = {
    "it_rm": ("Data centers operando en la RM", "MW", None),
    "it_chile": ("Data centers operando en Chile", "MW", None),
    "waitlist_mw": ("Proyectos esperando red", "MW", False),
    "water_ls_rm": ("Agua que usan los DC en la RM", "L/s", False),
    "water_peak_ls_rm": ("Agua en el peak de verano", "L/s", False),
    "peak_rm": ("Consumo eléctrico en el mes peak (RM)", "MW", False),
    "households_500m": ("Hogares a menos de 500 m de un DC grande", "hogares", False),
    "conflict_rm": ("Hogares movilizados contra DC (RM)", "%", False),
    "litigations": ("Litigios acumulados", "casos", False),
    "relocations": ("Proyectos que cambian de comuna", "proyectos", None),
    "cancellations": ("Proyectos que se van de Chile", "proyectos", False),
    "invest_realized": ("Inversión materializada", "MUS$", True),
    "invest_lost": ("Inversión perdida", "MUS$", False),
    "mw_antofagasta": ("Data centers en Antofagasta", "MW", None),
    "bill_pct": ("Alza de la cuenta de la luz", "%", False),
    "nox_t": ("NOx de generadores diésel", "t/año", False),
    "jobs_oper": ("Empleos de operación", "empleos", True),
}


def paired_delta(scen: dict, base: dict, key: str, idx: int) -> dict:
    a = np.array(scen["paired"][key])[:, idx]
    b = np.array(base["paired"][key])[:, idx]
    d = a - b
    mb = float(np.median(b))
    rel = float((np.median(a) - mb) / mb) if mb != 0 else 0.0
    return {"base": float(np.median(b)), "scen": float(np.median(a)),
            "delta": float(np.median(d)), "rel": rel, "p_up": float((d > 0).mean()),
            "p_down": float((d < 0).mean())}


def scenario_deltas(results: dict, year: int = 2035) -> dict:
    idx = 0 if year == 2030 else 1
    base = results["status_quo"]
    out = {}
    for sid, res in results.items():
        if sid == "status_quo":
            continue
        out[sid] = {k: paired_delta(res, base, k, idx) for k in METRICS}
        out[sid]["delay"] = {
            "base": base["extra"]["delay_months"]["mean"],
            "scen": res["extra"]["delay_months"]["mean"],
            "delta": res["extra"]["delay_months"]["mean"] - base["extra"]["delay_months"]["mean"]}
    return out


def _fmt(x: float, nd: int = 0) -> str:
    s = f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def _pct(x: float) -> str:
    nd = 1 if abs(x) < 0.1 else 0
    return f"{'+' if x >= 0 else ''}{_fmt(100 * x, nd)}%"


def hypotheses(results: dict) -> list[dict]:
    d35 = scenario_deltas(results, 2035)
    d30 = scenario_deltas(results, 2030)
    out = []

    a = d35["aire"]
    water, peak, wait = a["water_ls_rm"], a["peak_rm"], a["waitlist_mw"]
    grid_worse = peak["delta"] > 0 or wait["delta"] > 0
    big_grid = peak["rel"] > 0.05 or wait["rel"] > 0.1
    verdict = ("Se confirma" if water["rel"] < -0.2 and big_grid
               else "Parcialmente" if water["rel"] < -0.2 and grid_worse else "No se confirma")
    out.append({
        "id": "aire", "scenario": "aire", "source": "Informe, S1",
        "claim": "Exigir enfriamiento por aire reduce el agua, pero satura antes la red.",
        "verdict": verdict,
        "evidence": (f"En 2035 los DC de la RM usan {_pct(water['rel'])} de agua "
                     f"({_fmt(water['base'])} → {_fmt(water['scen'])} L/s). El consumo eléctrico "
                     f"en el mes peak cambia {_pct(peak['rel'])} y la lista de espera "
                     f"{_pct(wait['rel'])}."),
        "takeaway": ("El agua sí baja a la mitad, pero la red casi no lo nota: ya estaba "
                     "saturada por la fila de proyectos grandes." if not big_grid else
                     "El agua que se ahorra se paga con más electricidad justo en verano."),
    })

    c = d35["acumulativa"]
    lit, delay, conf = c["litigations"], c["delay"], c["conflict_rm"]
    verdict = ("Se confirma" if lit["rel"] < -0.2 and delay["delta"] < -1 else
               "Parcialmente" if lit["rel"] < -0.2 else "No se confirma")
    out.append({
        "id": "acumulativa", "scenario": "acumulativa", "source": "Informe, S1",
        "claim": "Evaluar en conjunto acorta los plazos totales porque reduce los litigios.",
        "verdict": verdict,
        "evidence": (f"Los litigios a 2035 cambian {_pct(lit['rel'])} y los hogares movilizados "
                     f"{_pct(conf['rel'])}. Pero el tiempo medio entre anuncio y operación "
                     f"cambia {_fmt(delay['delta'], 1)} meses "
                     f"({_fmt(delay['base'], 1)} → {_fmt(delay['scen'], 1)})."),
        "takeaway": ("Menos conflicto, pero no más rapidez: las ventanas de evaluación y los "
                     "proyectos que no caben y deben moverse se comen lo que se ahorra en "
                     "tribunales." if delay["delta"] >= -1 else
                     "Menos tribunales compensa el tiempo de evaluar en conjunto."),
    })

    m = d30["mesa"]
    it, dl = m["it_rm"], d35["mesa"]["delay"]
    verdict = "Se confirma" if abs(it["rel"]) < 0.05 else "No se confirma"
    out.append({
        "id": "mesa", "scenario": "mesa", "source": "Informe, A3 (la red es el cuello de botella)",
        "claim": "Acelerar los permisos no conecta más data centers si la red está saturada.",
        "verdict": verdict,
        "evidence": (f"Con permisos al doble de rápido, en 2030 hay {_pct(it['rel'])} MW operando "
                     f"en la RM ({_fmt(it['base'])} → {_fmt(it['scen'])} MW) y el plazo medio "
                     f"baja solo {_fmt(-dl['delta'], 1)} meses."),
        "takeaway": "El cuello de botella es la red eléctrica, no el permiso ambiental.",
    })

    t = scenario_deltas({"status_quo": results["status_quo"],
                         "t": results["solo_transparencia"],
                         "f": results["solo_fondo"]}, 2035)
    ct, cf = t["t"]["conflict_rm"], t["f"]["conflict_rm"]
    close = abs(ct["rel"] - cf["rel"]) < 0.05
    verdict = ("Parcialmente" if close else
               "Se confirma" if ct["delta"] < cf["delta"] else "No se confirma")
    out.append({
        "id": "transparencia", "scenario": "comunidad", "source": "Informe, S2",
        "claim": "Transparentar el uso de agua reduce más el conflicto que pagar compensaciones.",
        "verdict": verdict,
        "evidence": (f"Solo transparencia: hogares movilizados {_pct(ct['rel'])}. Solo un fondo de "
                     f"US$20.000 por MW al año: {_pct(cf['rel'])}."),
        "takeaway": ("Las dos bajan el conflicto en una magnitud parecida; juntas suman." if close
                     else "La gente reacciona más al miedo por el agua que a la plata." if
                     ct["delta"] < cf["delta"] else
                     "El fondo pesa más que la información sobre el agua."),
    })

    def seia_share(res):
        r = res["extra"]["routes"]
        tot = sum(r.values())
        return (r.get("SEIA", 0) + r.get("acumulativa", 0)) / tot if tot else 0.0

    sq, u80 = seia_share(results["status_quo"]), seia_share(results["umbral_80"])
    out.append({
        "id": "bunching", "scenario": "umbral_80", "source": "Informe, S7 y A1",
        "claim": "Con el umbral de 1.000 t, casi ningún data center nuevo pasa por evaluación "
                 "con participación ciudadana.",
        "verdict": "Se confirma" if sq < 0.15 else "No se confirma",
        "evidence": (f"Desde 2027, con 1.000 t solo {_fmt(100 * sq)}% de los proyectos nuevos "
                     f"entra al SEIA; con 80 t, {_fmt(100 * u80)}%. El modelo supone que los "
                     "proyectos ajustan su diésel justo bajo el límite, como los 7 casos reales "
                     "tras el DS 17 (511 a 990 t)."),
        "takeaway": "El umbral define quién participa: los proyectos se diseñan a la medida de la "
                    "norma.",
    })

    n = d30["norte"]
    out.append({
        "id": "norte", "scenario": "norte", "source": "Informe, A3 y S8",
        "claim": "Un incentivo al norte descomprime la RM.",
        "verdict": "Se confirma" if n["mw_antofagasta"]["delta"] > 50 else "No se confirma",
        "evidence": (f"En 2030 Antofagasta pasa de {_fmt(n['mw_antofagasta']['base'])} a "
                     f"{_fmt(n['mw_antofagasta']['scen'])} MW; los MW esperando red cambian "
                     f"{_pct(n['waitlist_mw']['rel'])} y los MW operando en la RM "
                     f"{_pct(n['it_rm']['rel'])}."),
        "takeaway": ("Parte de la fila de Santiago se muda al norte y la RM sigue creciendo con "
                     "la capacidad que queda." if n["waitlist_mw"]["rel"] < -0.15 else
                     "Mueve inversión nueva al norte, pero no vacía la cola de Santiago: quienes "
                     "ya esperan prefieren seguir esperando."),
    })
    return out


def winners_losers(res: dict, year: int = 2035) -> list[dict]:
    """Balance por comuna: cargas y beneficios en el año indicado (mediana)."""
    yi = C.YEARS.index(year)
    cm = res["communes"]
    rows = []
    for i, c in enumerate(C.COMMUNES):
        hh = c.pop / C.PEOPLE_PER_HOUSEHOLD
        it = cm["c_it"]["p50"][i][yi]
        rows.append({
            "id": c.id, "name": c.name, "region": c.region, "households": round(hh),
            "it_mw": it, "n_dc": cm["c_ndc"]["p50"][i][yi],
            "share": cm["c_share"]["p50"][i][yi],
            "water_ls": cm["c_water_ls"]["p50"][i][yi],
            "water_households": cm["c_water_ls"]["p50"][i][yi] * 86400 / 500,
            "h500": cm["c_h500"]["p50"][i][yi],
            "conflict": cm["c_conflict"]["p50"][i][yi],
            "jobs_local": cm["c_jobs_local"]["p50"][i][yi],
            "muni_usd_hh": (cm["c_muni_usd"]["p50"][i][yi] + cm["c_fund_usd"]["p50"][i][yi]) / hh,
            "nox_t": cm["c_nox"]["p50"][i][yi],
            "waitlist_mw": cm["c_waitlist"]["p50"][i][yi],
        })
    return rows
