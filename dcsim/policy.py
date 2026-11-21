"""Palancas de política y escenarios predefinidos.

La historia (2012 a dic-2026) es siempre la misma: umbral de 80 t hasta enero de 2026,
luego 1.000 t (DS 17), y evaluación proyecto por proyecto. Las palancas de un escenario
rigen desde enero de 2027.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class Policy:
    # Regulación ambiental
    fuel_threshold_t: float = 1000.0  # umbral de combustible que obliga a entrar al SEIA
    cumulative: bool = False  # evaluación acumulativa por zona (red + acuífero), con PAC
    window_months: int = 12  # cada cuánto se evalúa en conjunto una zona
    water_cap_ls: float | None = None  # tope de L/s de DC por acuífero (solo acumulativa)
    permit_speed: float = 1.0  # <1 acelera los permisos (Mesa Permanente)
    # Tecnología
    air_cooling_rm: bool = False  # exigir enfriamiento por aire en la RM
    # Territorio
    north_incentive: float = 0.0  # 0–1: subsidio a ubicarse en Antofagasta
    # Comunidad
    community_fund_usd_mw: float = 0.0  # fondo comunitario anual por MW operativo
    transparency: bool = False  # monitoreo público de agua y energía
    # Contexto (no es política, es incertidumbre del futuro)
    demand: str = "base"  # "baja" | "base" | "alta": llegada de nuevos proyectos 2027+
    climate: str = "base"  # "moderado" | "base" | "severo": recarga del acuífero
    demand_rate: float | None = None  # proyectos nuevos por año (reemplaza a `demand`)

    def to_dict(self) -> dict:
        return asdict(self)


STATUS_QUO = Policy()

SCENARIOS: dict[str, dict] = {
    "status_quo": {
        "name": "Como hoy",
        "short": "Uno por uno",
        "policy": STATUS_QUO,
        "summary": "Cada proyecto se evalúa solo. Desde el DS 17 casi todos pasan por "
                   "pertinencia (sin participación ciudadana) porque declaran menos de "
                   "1.000 t de combustible.",
        "question": "¿Qué pasa si seguimos aprobando data centers uno por uno?",
    },
    "acumulativa": {
        "name": "Evaluación conjunta por zona",
        "short": "Evaluación conjunta",
        "policy": replace(STATUS_QUO, cumulative=True, water_cap_ls=60.0),
        "summary": "Una vez al año el Estado evalúa juntos todos los proyectos de una zona: "
                   "cuánta red y agua quedan, con participación de los vecinos. Lo que no "
                   "cabe se entera de inmediato.",
        "question": "¿Y si el Estado mira la suma antes de aprobar?",
    },
    "aire": {
        "name": "Enfriamiento por aire obligatorio",
        "short": "Solo enfriamiento por aire",
        "policy": replace(STATUS_QUO, air_cooling_rm=True),
        "summary": "Los nuevos data centers de la RM no pueden usar agua para enfriar. "
                   "Ahorran agua, pero gastan más electricidad en verano.",
        "question": "¿Y si prohibimos usar agua para enfriar?",
    },
    "umbral_80": {
        "name": "Volver al umbral de 80 t",
        "short": "Volver a 80 t",
        "policy": replace(STATUS_QUO, fuel_threshold_t=80.0),
        "summary": "Se revierte el DS 17: todo data center con más de 80 t de diésel vuelve "
                   "a entrar al SEIA, con participación ciudadana.",
        "question": "¿Y si revertimos el DS 17?",
    },
    "mesa": {
        "name": "Acelerar permisos (Mesa Permanente)",
        "short": "Permisos rápidos",
        "policy": replace(STATUS_QUO, permit_speed=0.5),
        "summary": "Los permisos tardan la mitad, como busca la Mesa Permanente creada en "
                   "noviembre de 2026. La red eléctrica sigue igual.",
        "question": "¿Y si aprobamos todo el doble de rápido?",
    },
    "norte": {
        "name": "Incentivo al norte",
        "short": "Incentivo al norte",
        "policy": replace(STATUS_QUO, north_incentive=0.6),
        "summary": "Subsidio para instalarse en Antofagasta, donde sobra energía solar, a "
                   "cambio de más latencia.",
        "question": "¿Y si llevamos los data centers al norte?",
    },
    "comunidad": {
        "name": "Transparencia y fondo comunitario",
        "short": "Transparencia + fondo",
        "policy": replace(STATUS_QUO, transparency=True, community_fund_usd_mw=20_000),
        "summary": "Las empresas publican su consumo real de agua y energía y pagan un fondo "
                   "comunitario de US$20.000 por MW al año.",
        "question": "¿Y si las empresas transparentan y comparten beneficios?",
    },
}


def policy_from_dict(d: dict | None) -> Policy:
    if not d:
        return STATUS_QUO
    allowed = Policy.__dataclass_fields__.keys()
    return replace(STATUS_QUO, **{k: v for k, v in d.items() if k in allowed})


# Escenarios auxiliares para probar hipótesis (no se muestran como tarjetas)
HYPOTHESIS_SCENARIOS: dict[str, Policy] = {
    "solo_transparencia": replace(STATUS_QUO, transparency=True),
    "solo_fondo": replace(STATUS_QUO, community_fund_usd_mw=20_000),
}
