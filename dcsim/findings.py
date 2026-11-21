"""Hallazgos para la demo, calculados desde cache/explore_raw.json (ver explore.py).

    uv run python -m dcsim.explore     # 15.080 simulaciones, ~3 min en 10 núcleos
    uv run python -m dcsim.findings    # resume y guarda cache/findings.json

Cada hallazgo informa en qué fracción de los futuros simulados se cumple, comparando
réplicas con las mismas semillas. Los hallazgos de reglas que la portada muestra (paquete,
transparencia y fondo) salen de los mismos 200 futuros que la portada, así las cifras coinciden.
La historia alternativa de Cerrillos corre en modo libre; el resto, en modo anclado.

Después, ``python -m dcsim.sensitivity`` revisa si cada hallazgo se mantiene al mover los
parámetros fijos (lee de aquí el kicker y la cifra; FINDINGS.md, sección 4).
"""

from __future__ import annotations

import json
import os
from collections import Counter

import numpy as np

from . import catalog as C
from .explore import OUT as RAW
from .montecarlo import _code_hash, run_ensemble
from .policy import HYPOTHESIS_SCENARIOS, SCENARIOS

OUT = RAW.replace("explore_raw.json", "findings.json")


def _f(x: float, nd: int = 0) -> str:
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


N_ENS = 200  # los mismos futuros que la portada (server.N_PRESET)


def _ens(policy) -> dict:
    """Valores pareados (2030, 2035) por réplica, de los ensambles que usa la portada."""
    return run_ensemble(policy, n=N_ENS)["paired"]


def build(raw: dict) -> list[dict]:
    def A(n, k):
        return np.array([r[k] for r in raw[n]], dtype=float)

    def E(ens, k):  # 2035
        return np.array(ens[k], dtype=float)[:, 1]

    def med(n, k):
        return float(np.nanmedian(A(n, k)))

    def share(cond):
        return float(np.mean(cond))

    out = []

    # 1. Paquete que mejora todo a la vez
    eb, es = _ens(SCENARIOS["status_quo"]["policy"]), _ens(SCENARIOS["paquete"]["policy"])
    keys = [("it_chile_2035", 1), ("invest_realized_2035", 1), ("invest_lost_2035", -1),
            ("conflict_rm_2035", -1), ("litigations_2035", -1), ("water_ls_rm_2035", -1)]
    ok = np.ones(len(eb["it_chile"]), bool)
    rel = {}
    for k, sign in keys:
        k0 = k.removesuffix("_2035")
        d = E(es, k0) - E(eb, k0)
        ok &= (d >= 0) if sign > 0 else (d <= 0)
        rel[k] = (np.median(E(es, k0)) - np.median(E(eb, k0))) / np.median(E(eb, k0))
    bill_b, bill_s = np.median(E(eb, "bill_pct")), np.median(E(es, "bill_pct"))
    out.append({
        "id": "paquete", "kicker": "No hay que elegir",
        "headline": (f"3 reglas mejoran a la vez agua, conflicto, juicios e inversión en "
                     f"{_f(100 * share(ok))}% de los futuros"),
        "body": (f"Enfriamiento por aire + fondo comunitario + incentivo al norte: "
                 f"{_f(100 * rel['it_chile_2035'], 0)}% más data centers operando, "
                 f"{_f(100 * rel['invest_realized_2035'])}% más inversión, "
                 f"{_f(-100 * rel['invest_lost_2035'])}% menos inversión perdida, "
                 f"{_f(-100 * rel['conflict_rm_2035'])}% menos hogares movilizados, "
                 f"{_f(-100 * rel['litigations_2035'])}% menos juicios y "
                 f"{_f(-100 * rel['water_ls_rm_2035'])}% menos agua (2035)."),
        "cost": (f"El costo: la cuenta de la luz sube {_f(bill_s, 1)}% en vez de "
                 f"{_f(bill_b, 1)}%, porque hay más data centers consumiendo." if bill_s > bill_b
                 else f"Y la cuenta de la luz no sube más: {_f(bill_s, 1)}% en vez de "
                 f"{_f(bill_b, 1)}%, porque parte de la demanda se va a Antofagasta, donde "
                 "sobra energía solar (supuesto: allí no presiona la tarifa)."),
        "stat": f"{_f(100 * share(ok))}%",
        "stat_label": "de los futuros mejora en todo salvo la cuenta de la luz",
        "action": {"type": "custom", "policy": {"air_cooling_rm": True,
                                                "community_fund_usd_mw": 20000,
                                                "north_incentive": 0.6}},
        "action_label": "Simular este paquete",
    })

    # 2. Permisos más rápidos no conectan más
    f, n = "S:permit_speed=0.25", "S:permit_speed=1.0"
    r30 = (med(f, "it_rm_2030") - med(n, "it_rm_2030")) / med(n, "it_rm_2030")
    nd30 = 1 if abs(100 * r30) < 1.5 else 0  # "+0,5%", no "+0%"
    out.append({
        "id": "permisos", "kicker": "El cuello de botella no es el permiso",
        "headline": (f"Permisos 4 veces más rápidos: solo {_f(100 * r30, nd30)}% más data centers "
                     "en Santiago al 2030"),
        "body": (f"Con permisos 75% más cortos, la RM pasa de {_f(med(n, 'it_rm_2030'))} a "
                 f"{_f(med(f, 'it_rm_2030'))} MW en 2030, y el plazo medio entre anuncio y "
                 "operación baja apenas "
                 f"{_f(med(n, 'delay_mean') - med(f, 'delay_mean'), 1)} meses. "
                 "Los proyectos aprobados igual esperan conexión eléctrica."),
        "cost": "Relevante para la Mesa Permanente (nov-2026), cuyo objetivo es acortar permisos.",
        "stat": f"+{_f(100 * r30, nd30)}%", "stat_label": "MW en la RM con permisos 4× más rápidos",
        "action": {"type": "scenario", "id": "mesa"}, "action_label": "Ver “Permisos rápidos”",
    })

    # 3. Boom de IA
    lo, hi = "S:demand_rate=5.0", "S:demand_rate=10.0"
    mw = (med(hi, "it_chile_2035") - med(lo, "it_chile_2035")) / med(lo, "it_chile_2035")
    lit = med(hi, "litigations_2035") / med(lo, "litigations_2035")
    wait = med(hi, "waitlist_mw_2035") / med(lo, "waitlist_mw_2035")
    x4 = "S:demand_rate=20.0"
    out.append({
        "id": "boom", "kicker": "Punto de quiebre",
        "headline": f"Si llegan el doble de proyectos, se conecta solo {_f(100 * mw)}% más, pero "
                    f"los juicios se multiplican por {_f(lit, 1)}",
        "body": (f"Con 10 proyectos nuevos al año en vez de 5, la lista de espera crece "
                 f"{_f(wait, 1)} veces y los hogares movilizados pasan de "
                 f"{_f(100 * med(lo, 'conflict_rm_2035'))}% a "
                 f"{_f(100 * med(hi, 'conflict_rm_2035'))}%. Con 4 veces más proyectos: "
                 f"{_f(100 * (med(x4, 'it_chile_2035') / med(lo, 'it_chile_2035') - 1))}% más MW "
                 f"y {_f(med(x4, 'litigations_2035') / med(lo, 'litigations_2035'))} veces más "
                 "juicios. Los proyectos que esperan red generan rechazo sin dejar beneficios."),
        "cost": "La red no crece al ritmo de los anuncios: cada proyecto extra suma espera, no MW.",
        "stat": f"×{_f(lit, 1)}", "stat_label": "juicios con el doble de proyectos",
        "mw_pct": round(100 * mw),
        "action": {"type": "custom", "policy": {"demand": "alta"}},
        "action_label": "Simular el boom de IA",
    })

    # 4. Cerrillos contrafactual
    real, air = "H:real", "H:cerrillos_aire"
    on_a = A(air, "cer_online")
    by23 = lambda on: share((on >= 0) & (on <= C.ym("2023-12")))  # noqa: E731
    out.append({
        "id": "cerrillos", "kicker": "Historia alternativa",
        "headline": (f"Si Google hubiera enfriado Cerrillos con aire en 2019, a fines de 2023 "
                     f"estaría operando en {_f(100 * by23(on_a))}% de los futuros"),
        "body": (f"El modelo vuelve a correr 2012–2026 cambiando solo esa decisión. Con agua "
                 f"(169 L/s de un acuífero en zona de prohibición) la probabilidad de juicio es "
                 f"{_f(100 * share(A(real, 'cer_lit') > 0))}%; con aire, "
                 f"{_f(100 * share(A(air, 'cer_lit') > 0))}%. En la realidad hubo juicio, el "
                 "tribunal anuló el permiso en 2024 y Google rediseñó con aire en 2026."),
        "cost": "La elección de enfriamiento pesa más que el tamaño del proyecto. Supuesto clave: "
                "cuánto pesa en la opinión de los vecinos el agua que ven usar; si pesa la mitad, "
                "la diferencia casi desaparece.",
        "stat": f"{_f(100 * share(A(real, 'cer_lit') > 0))}% → "
                f"{_f(100 * share(A(air, 'cer_lit') > 0))}%",
        "stat_label": "probabilidad de juicio: agua → aire",
        "action": {"type": "project", "id": "google_cerrillos", "year": 2024},
        "action_label": "Ver Cerrillos en el mapa",
    })

    # 5. Campo de Datos Lampa
    li = C.COMMUNE_IDX["lampa"]
    cb = np.array([r["c_conflict_2035"][li] for r in raw["P:base"]])
    cf = np.array([r["c_conflict_2035"][li] for r in raw["P:campo_lampa_lejos"]])
    hb = np.median([r["c_h500_2035"][li] for r in raw["P:base"]])
    hf = np.median([r["c_h500_2035"][li] for r in raw["P:campo_lampa_lejos"]])
    drop = 1 - np.median(cf) / np.median(cb)
    out.append({
        "id": "lampa", "kicker": "Dónde importa más que cuánto",
        "headline": f"Alejar un solo proyecto de las casas baja {_f(100 * drop)}% el conflicto de "
                    "toda Lampa",
        "body": (f"Campo de Datos Lampa (100 MW) está a menos de 50 m de Valle Grande. El mismo "
                 f"proyecto en la periferia de la comuna reduce los hogares movilizados de "
                 f"{_f(100 * np.median(cb))}% a {_f(100 * np.median(cf))}% y los hogares a "
                 "menos de "
                 f"500 m de un DC grande de {_f(hb)} a {_f(hf)} (2035). Se cumple en "
                 f"{_f(100 * share(cf < cb))}% de los futuros."),
        "cost": "El informe registra proyectos a menos de 50 m (Lampa) y a ~250 m (Puente Alto) "
                "de viviendas.",
        "stat": f"−{_f(100 * drop)}%", "stat_label": "conflicto en Lampa",
        "action": {"type": "project", "id": "campo_lampa", "year": 2030},
        "action_label": "Ver Campo de Datos Lampa",
    })

    # 6. Transparencia vs dinero
    et = _ens(HYPOTHESIS_SCENARIOS["solo_transparencia"])
    ef = _ens(HYPOTHESIS_SCENARIOS["solo_fondo"])
    cb = np.median(E(eb, "conflict_rm"))
    rt = (np.median(E(et, "conflict_rm")) - cb) / cb
    rf = (np.median(E(ef, "conflict_rm")) - cb) / cb
    cost = 20_000 * np.median(E(eb, "it_rm")) / 1e6
    out.append({
        "id": "transparencia", "kicker": "Información vs plata",
        "headline": f"Publicar el uso real de agua baja el conflicto casi tanto como pagar "
                    f"US${_f(cost)} millones al año",
        "body": (f"Transparentar el consumo: {_f(100 * rt)}% hogares movilizados. Un fondo "
                 f"comunitario de US$20.000 por MW al año (≈ US${_f(cost)} millones en 2035): "
                 f"{_f(100 * rf)}%. Google Quilicura usa solo el 29% de su derecho de agua, pero "
                 "los vecinos temen el 100%."),
        "cost": "Depende de dos supuestos con rango: cuánta confianza recupera la información y "
                "cuánto pesa el agua en la opinión de los vecinos.",
        "stat": f"US${_f(cost)} M", "stat_label": "al año, lo que 'vale' la transparencia",
        "action": {"type": "custom", "policy": {"transparency": True}},
        "action_label": "Simular solo transparencia",
    })

    # 7. Dependencia de la trayectoria
    cnt = Counter(C.COMMUNES[int(r["top_conflict_2035"])].name for r in raw["P:base"])
    top = cnt.most_common(4)
    n = len(raw["P:base"])
    common = [k for k, c in cnt.items() if c >= 0.05 * n]  # descarta casos de 1 en 200
    out.append({
        "id": "trayectoria", "kicker": "No hay destino escrito",
        "headline": (f"{len(common)} comunas distintas pueden terminar como la más afectada en "
                     "2035 (cada una en al menos 5% de los futuros)"),
        "body": ("En 200 futuros con las mismas reglas, la comuna con más hogares movilizados "
                 "cambia según el orden en que llegan los proyectos: " +
                 ", ".join(f"{name} ({_f(100 * k / n)}%)" for name, k in top) +
                 ". La 'comuna de sacrificio' se decide en el camino, no en el mapa."),
        "cost": "Por eso una evaluación proyecto por proyecto no puede anticiparla.",
        "stat": str(len(common)), "stat_label": "comunas posibles de sacrificio",
        "action": {"type": "scenario", "id": "status_quo", "metric": "c_conflict"},
        "action_label": "Ver el conflicto en el mapa",
    })
    n_sims = sum(len(v) for v in raw.values())
    for x in out:
        x["n_sims"] = n_sims
        x["model"] = _code_hash()  # tests/test_invariants.py exige que coincida con el código
    return out


def main():
    with open(RAW) as fh:
        raw = json.load(fh)
    findings = build(raw)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(findings, fh, ensure_ascii=False, indent=1)
    for x in findings:
        print(f"[{x['kicker']}] {x['headline']}\n   {x['body']}\n   {x['cost']}\n")
    print("guardado en", OUT)


if __name__ == "__main__":
    main()
