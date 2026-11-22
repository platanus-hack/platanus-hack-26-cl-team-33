"""Parámetros del modelo con su rango y fuente.

``Param.base`` es el valor central. Si ``sample`` es True, cada réplica Monte Carlo
sortea el parámetro uniformemente en [low, high], así la incertidumbre de los datos
se propaga a los resultados. Los demás quedan en su valor central en cada futuro, y
``python -m dcsim.sensitivity`` los lleva a cada extremo de su rango (uno a la vez y todos
juntos) para ver si los hallazgos se mantienen.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    key: str
    label: str
    base: float
    low: float
    high: float
    unit: str
    src: str
    kind: str  # "dato" (fuente chilena o extranjera), "calibrado" o "supuesto"
    sample: bool = False
    group: str = "general"


PARAMS: list[Param] = [
    # --- Energía
    Param("lf_max", "Factor de carga máximo de un DC", 0.75, 0.6, 0.9, "—",
          "Informe C: base 0,7 (0,5–0,9). Google 31,7/30 MW.", "calibrado", True, "energía"),
    Param("lf_ramp_months", "Meses para llenar un DC tras abrir", 30, 18, 42, "meses",
          "Supuesto: los colocation se llenan gradualmente.", "calibrado", True, "energía"),
    Param("pue_evap", "PUE con enfriamiento evaporativo", 1.2, 1.1, 1.3, "—",
          "LBNL 2024 (informe C)", "dato", True, "energía"),
    Param("pue_air", "PUE con enfriamiento por aire", 1.4, 1.3, 1.5, "—",
          "LBNL 2024 (informe C)", "dato", True, "energía"),
    Param("pue_hybrid", "PUE con enfriamiento híbrido", 1.25, 1.15, 1.35, "—",
          "Supuesto entre aire y evaporativo", "supuesto", False, "energía"),
    Param("peak_pue_ratio", "PUE de verano / PUE medio", 1.12, 1.08, 1.18, "—",
          "arXiv 2606.21760: evaporación reduce 25–35% la potencia pico de frío", "supuesto",
          False, "energía"),
    Param("noncd_mwh_per_person", "Consumo eléctrico comunal no-DC", 2.4, 2.0, 3.0,
          "MWh/persona/año", "Calibrado para que los DC sean ~62% del consumo de Quilicura",
          "calibrado", False, "energía"),
    Param("system_twh_2025", "Consumo eléctrico nacional 2025", 84, 80, 88, "TWh",
          "Supuesto (orden de magnitud SEN)", "supuesto", False, "energía"),
    Param("system_growth", "Crecimiento anual de la demanda nacional", 0.025, 0.015, 0.035,
          "1/año", "Supuesto", "supuesto", False, "energía"),
    Param("price_elasticity", "Traspaso a la tarifa del aumento de la parte de los DC en la "
          "demanda nacional", 0.25,
          0.0, 0.5, "—", "Yue & Zeng: +5% en EE.UU. (no transferible). Vacío A8. Sin la demanda "
          "de Antofagasta, donde sobra energía solar.", "supuesto",
          True, "energía"),
    Param("reg_alloc_share", "Fracción de obras de red pagada por clientes regulados", 0.2,
          0.0, 0.4, "—", "Hipótesis Neto (no cuantificada). Vacío A8.", "supuesto", True,
          "energía"),
    Param("grid_cost_musd_per_mw", "Costo de red atribuible a cada MW de DC", 0.25, 0.1, 0.4,
          "MUS$/MW", "Supuesto", "supuesto", False, "energía"),
    # --- Agua
    Param("wue_evap", "WUE evaporativo (agua por kWh)", 1.74, 1.55, 1.9, "L/kWh",
          "Google Quilicura 2024: 458 ML / 262.800 MWh (informe A2)", "calibrado", True, "agua"),
    Param("wue_air", "WUE por aire", 0.02, 0.0, 0.1, "L/kWh", "LBNL, Microsoft (informe C)",
          "dato", False, "agua"),
    Param("wue_hybrid", "WUE híbrido", 0.7, 0.5, 1.0, "L/kWh", "NREL (1,27 → 0,70)", "dato",
          False, "agua"),
    Param("wue_summer_factor", "WUE en verano / WUE medio", 1.45, 1.3, 1.7, "—",
          "arXiv 2606.21760: el agua se concentra en días calurosos", "supuesto", False, "agua"),
    Param("liters_household_day", "Consumo de agua por hogar", 500, 400, 600, "L/día",
          "Equivalencias de prensa (informe C)", "dato", False, "agua"),
    Param("recharge_cut", "Reducción de recarga por cambio climático a 2035", 0.2, 0.1, 0.4,
          "—", "Escenarios −10% a −40% (informe C)", "supuesto", False, "agua"),
    # --- Permisos y conflictos
    Param("seia_months", "Mediana de tramitación SEIA + permisos", 16, 10, 30, "meses",
          "Informe C: plazo 36 meses (6–48) incluyendo esperas", "calibrado", False, "permisos"),
    Param("pert_months", "Mediana de pertinencia + permisos sectoriales", 9, 4, 14, "meses",
          "Cerrillos 2026: 3 meses de pertinencia", "calibrado", False, "permisos"),
    Param("build_months", "Mediana de construcción", 20, 14, 30, "meses",
          "Supuesto (Google Quilicura: anuncio 2012 → 2015)", "calibrado", False, "permisos"),
    Param("fuel_t_per_mw", "Combustible diseñado por MW", 7.0, 5.0, 10.0, "t/MW",
          "Lampa 511 t/100 MW; Cerrillos 696 t/~120 MW", "dato", False, "permisos"),
    Param("fuel_min_t_per_mw", "Combustible mínimo viable por MW", 4.5, 4.0, 5.0, "t/MW",
          "Supuesto: autonomía mínima del respaldo", "supuesto", False, "permisos"),
    Param("p_bunch", "Prob. de ajustar el combustible bajo el umbral", 0.85, 0.6, 1.0, "—",
          "Informe S7: 7 pertinencias entre 511 y 990 t", "supuesto", False, "permisos"),
    Param("p_lit_base", "Prob. base de litigio por proyecto aprobado", 0.02, 0.01, 0.05, "—",
          "Calibrado: 2 litigios 2012–2026 (Cerrillos, Huechuraba)", "calibrado", False,
          "permisos"),
    Param("p_lit_conflict", "Aumento de la prob. de litigio por oposición local", 3.0, 2.0,
          4.0, "—", "Informe C: prob. de litigio 0,3 (0,1–0,6)", "calibrado", False,
          "permisos"),
    Param("lit_w_water", "Peso del agua de un acuífero como fundamento de un juicio", 1.5, 0.5,
          2.0, "—", "Supuesto del modelo, sin dato chileno. Con 1 pesa lo mismo que tener casas a "
          "menos de 300 m o una línea de alta tensión. El rango se prueba en el análisis de "
          "sensibilidad.", "supuesto", False, "permisos"),
    Param("lit_convexity", "Exponente de la oposición local en la prob. de litigio", 2.0, 1.0,
          3.0, "—", "Supuesto del modelo, sin dato chileno. Con 2 los juicios se concentran donde "
          "la oposición es intensa; con 1 crecen en proporción a ella. El rango se prueba en el "
          "análisis de sensibilidad.", "supuesto", False, "permisos"),
    Param("lit_months", "Mediana de duración de un litigio", 26, 18, 48, "meses",
          "Tribunal Ambiental: 2 a 4 años (informe A6)", "dato", False, "permisos"),
    Param("p_annul_base", "Prob. de que el tribunal anule el permiso", 0.25, 0.1, 0.4, "—",
          "Cerrillos ganó, Huechuraba perdió (informe A6)", "supuesto", False, "permisos"),
    Param("annul_w_water", "Aumento de la prob. de anulación si el proyecto usa agua de un "
          "acuífero", 2.0, 0.5, 3.0, "—", "Supuesto del modelo, sin dato chileno: la prob. se "
          "multiplica por 1 + este valor (2: se triplica). Solo dos fallos: Cerrillos (agua) se "
          "anuló y Huechuraba no. El rango se prueba en el análisis de sensibilidad.", "supuesto",
          False, "permisos"),
    Param("p_pause", "Prob. de que la empresa espere el fallo antes de construir", 0.85, 0.6,
          0.95, "—", "Google no construyó Cerrillos durante el litigio", "supuesto", False,
          "permisos"),
    Param("reloc_hazard", "Prob. mensual de mudarse de comuna mientras espera red, sin "
          "ampliación de red a la vista", 0.015, 0.0075, 0.03, "1/mes", "Supuesto del modelo, "
          "sin dato chileno. Corre desde el mes 12 de espera. El rango se prueba en el análisis "
          "de sensibilidad.", "supuesto", False, "permisos"),
    Param("reloc_hazard_exp", "Prob. mensual de mudarse de comuna mientras espera red, con una "
          "ampliación planificada en los próximos 4 años", 0.004, 0.002, 0.008, "1/mes",
          "Supuesto del modelo, sin dato chileno. El rango se prueba en el análisis de "
          "sensibilidad.", "supuesto", False, "permisos"),
    # --- Efectos de las reglas (sin dato chileno: se sortean para que su incertidumbre se vea)
    Param("lit_factor_cum", "Litigios con evaluación conjunta (factor sobre la prob. individual)",
          0.35, 0.2, 0.5, "—", "Supuesto: la participación temprana reduce los litigios "
          "(informe S1); sin dato chileno", "supuesto", True, "reglas"),
    Param("annul_factor_cum", "Anulaciones con evaluación conjunta (factor)", 0.4, 0.2, 0.6, "—",
          "Supuesto: una evaluación con participación deja menos vicios que reclamar",
          "supuesto", True, "reglas"),
    Param("trust_gain_cum", "Confianza que deja cada aprobación conjunta con participación",
          0.1, 0.0, 0.2, "—", "Supuesto (vacío A8)", "supuesto", True, "reglas"),
    Param("transparency_trust", "Confianza que recupera el monitoreo público de agua y energía",
          0.15, 0.05, 0.25, "—", "Supuesto (vacío A8: efecto de la información en la oposición)",
          "supuesto", True, "reglas"),
    # --- Opinión
    Param("opinion_speed", "Velocidad de cambio de opinión", 0.13, 0.06, 0.2, "1/mes",
          "Supuesto (vacío A8: elasticidad de la oposición)", "supuesto", True, "opinión"),
    Param("benefit_weight", "Peso de los beneficios locales en la opinión", 1.0, 0.5, 1.5,
          "—", "Supuesto (vacío A8)", "supuesto", True, "opinión"),
    Param("op_intercept", "Rechazo de partida de un hogar sin data centers cerca", -2.0, -2.5,
          -1.5, "—", "Supuesto del modelo, sin dato chileno. En escala logística: −2 equivale a "
          "12% de rechazo (−2,5: 8%; −1,5: 18%). El rango se prueba en el análisis de "
          "sensibilidad.", "supuesto", False, "opinión"),
    Param("op_w_nuisance", "Peso de las molestias cercanas (ruido, diésel, paisaje) en la "
          "opinión", 1.6, 1.0, 2.2, "—", "Supuesto del modelo, sin dato chileno. El rango se "
          "prueba en el análisis de sensibilidad.", "supuesto", False, "opinión"),
    Param("op_w_water", "Peso del agua que los vecinos ven usar en la opinión", 1.2, 0.6, 1.8,
          "—", "Supuesto del modelo, sin dato chileno. El rango se prueba en el análisis de "
          "sensibilidad.", "supuesto", False, "opinión"),
    Param("op_w_saturation", "Peso de la saturación (parte de la electricidad de la comuna que "
          "usan los DC) en la opinión", 1.5, 0.75, 2.25, "—", "Supuesto del modelo, sin dato "
          "chileno. El rango se prueba en el análisis de sensibilidad.", "supuesto", False,
          "opinión"),
    Param("op_contagion", "Contagio de la opinión entre vecinos de la misma comuna", 0.03, 0.0,
          0.06, "1/mes", "Supuesto del modelo, sin dato chileno. Con 0 no hay contagio. El rango "
          "se prueba en el análisis de sensibilidad.", "supuesto", False, "opinión"),
    Param("trust_decay", "Fracción de la desconfianza que queda cada mes", 0.99, 0.98, 0.995,
          "—", "Supuesto del modelo, sin dato chileno. Con 0,99 la desconfianza se reduce a la "
          "mitad en ~6 años (0,98: ~3 años; 0,995: ~11 años). El rango se prueba en el análisis "
          "de sensibilidad.", "supuesto", False, "opinión"),
    Param("trust_gain_pertinencia", "Desconfianza que deja cada aprobación por pertinencia "
          "(sin participación)", 0.15, 0.05, 0.25, "—", "Supuesto del modelo, sin dato chileno "
          "(una aprobación por SEIA deja 0,03). El rango se prueba en el análisis de "
          "sensibilidad.", "supuesto", False, "opinión"),
    Param("local_hire_share", "Fracción de empleos contratados en la comuna", 0.25, 0.1, 0.4,
          "—", "Supuesto: vecinos de Quilicura dicen no recibir empleo", "supuesto", False,
          "economía"),
    # --- Economía
    Param("capex_musd_per_mw", "Inversión por MW (si no se informa)", 7.0, 5.0, 9.0, "MUS$/MW",
          "Lampa: US$850 M / 100 MW", "dato", False, "economía"),
    Param("jobs_build_per_musd", "Empleos de construcción por MUS$", 3.0, 1.3, 7.0,
          "empleos/MUS$", "Google 2012: 200/US$150 M; 2018: 1.000/US$140 M", "dato", False,
          "economía"),
    Param("nox_g_per_kwh", "NOx de generadores diésel", 9.0, 6.0, 14.0, "g/kWh",
          "EPA AP-42 / Tier 2 (extranjero)", "dato", False, "aire"),
    Param("test_hours_year", "Horas de prueba anuales del respaldo diésel", 12, 6, 24,
          "h/año", "Pruebas mensuales (informe A4); vacío A8", "supuesto", False, "aire"),
    Param("outages_per_year", "Apagones de red que activan el diésel", 0.4, 0.1, 1.0,
          "eventos/año", "Supuesto (apagones 2024–2025 en la RM)", "supuesto", False, "aire"),
]
P = {p.key: p for p in PARAMS}


def base_values() -> dict[str, float]:
    return {p.key: p.base for p in PARAMS}


def sample_values(rng) -> dict[str, float]:
    vals = base_values()
    for p in PARAMS:
        if p.sample:
            vals[p.key] = float(rng.uniform(p.low, p.high))
    return vals
