"""Datos de entrada: comunas, nodos de red, acuíferos y proyectos de data centers.

Cada valor lleva su fuente. Donde el informe de investigación no da un dato,
el valor se marca como supuesto (``src`` empieza con "Supuesto").
Las coordenadas son aproximadas y sirven solo para calcular distancias y dibujar el mapa.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Tiempo: el modelo avanza en meses desde enero de 2012.
# ---------------------------------------------------------------------------
YEAR0 = 2012
YEAR_END = 2035


def ym(s: str) -> int:
    """'YYYY-MM' -> índice de mes desde enero de 2012."""
    y, m = s.split("-")
    return (int(y) - YEAR0) * 12 + int(m) - 1


def ym_str(t: int) -> str:
    return f"{YEAR0 + t // 12}-{t % 12 + 1:02d}"


N_MONTHS = (YEAR_END - YEAR0 + 1) * 12
YEARS = list(range(YEAR0, YEAR_END + 1))
NOW = ym("2026-11")  # fecha del informe
DS17 = ym("2026-01")  # DS 17/2025 publicado el 21-01-2026: umbral 80 t -> 1.000 t
POLICY_START = ym("2027-01")  # las políticas alternativas rigen desde aquí


# ---------------------------------------------------------------------------
# Comunas
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Commune:
    id: str
    name: str
    region: str  # "RM" o nombre de región
    pop: int  # Censo 2017 (INE)
    lat: float  # centroide poblado aproximado
    lon: float
    radius_km: float  # radio del área poblada (para ubicar hogares sintéticos)
    node: str  # nodo de red al que se conectan los DC de la comuna
    aquifer: str | None  # acuífero del que extraen agua los DC evaporativos
    latency: float  # 1 = Santiago; preferencia de los desarrolladores por cercanía
    land_cost: float  # índice relativo de costo de suelo industrial (supuesto)
    # Barrios con hogares cerca de sitios de DC: (nombre, lat, lon, radio_km, fracción)
    barrios: tuple = ()


COMMUNES: list[Commune] = [
    Commune("quilicura", "Quilicura", "RM", 210_410, -33.360, -70.730, 3.0,
            "norte", "stgo_norte", 1.0, 0.7,
            (("Sector industrial Quilicura", -33.352, -70.748, 1.0, 0.15),)),
    Commune("lampa", "Lampa", "RM", 102_034, -33.300, -70.800, 5.0,
            "norte", "stgo_norte", 0.95, 0.4,
            (("Valle Grande", -33.336, -70.760, 1.2, 0.35),)),
    Commune("colina", "Colina", "RM", 146_207, -33.240, -70.660, 6.0,
            "norte", "stgo_norte", 0.95, 0.6, ()),
    Commune("huechuraba", "Huechuraba", "RM", 98_671, -33.370, -70.640, 2.5,
            "norte", "stgo_norte", 1.0, 0.9,
            (("La Pincoya", -33.355, -70.650, 0.9, 0.30),)),
    Commune("tiltil", "Tiltil", "RM", 19_312, -33.090, -70.930, 5.0,
            "polpaico", "stgo_norte", 0.85, 0.3,
            (("Polpaico", -33.160, -70.880, 1.0, 0.25),)),
    Commune("pudahuel", "Pudahuel", "RM", 230_293, -33.440, -70.760, 3.0,
            "poniente", "stgo_central", 1.0, 0.7, ()),
    Commune("cerrillos", "Cerrillos", "RM", 80_832, -33.495, -70.715, 2.0,
            "poniente", "stgo_central", 1.0, 0.8,
            (("Villas Camino a Lonquén", -33.515, -70.712, 0.8, 0.30),)),
    Commune("padre_hurtado", "Padre Hurtado", "RM", 63_250, -33.570, -70.810, 2.5,
            "poniente", "stgo_central", 0.95, 0.5, ()),
    Commune("santiago", "Santiago (centro)", "RM", 404_495, -33.450, -70.660, 2.5,
            "poniente", "stgo_central", 1.0, 1.5, ()),
    Commune("san_bernardo", "San Bernardo", "RM", 301_313, -33.595, -70.700, 3.5,
            "sur", "stgo_central", 0.95, 0.6, ()),
    Commune("buin", "Buin", "RM", 96_614, -33.730, -70.740, 3.0,
            "sur", "stgo_central", 0.9, 0.4, ()),
    Commune("puente_alto", "Puente Alto", "RM", 568_106, -33.610, -70.575, 4.0,
            "sur", "stgo_central", 0.95, 0.6,
            (("Bajos de Mena", -33.628, -70.592, 1.0, 0.20),)),
    Commune("valparaiso", "Valparaíso / Curauma", "Valparaíso", 296_655, -33.050, -71.610, 4.0,
            "valparaiso", None, 0.85, 0.6, ()),
    Commune("concepcion", "Concepción y otras", "Biobío", 223_574, -36.820, -73.050, 4.0,
            "sur_sen", None, 0.7, 0.5, ()),
    Commune("antofagasta", "Antofagasta", "Antofagasta", 361_873, -23.650, -70.400, 5.0,
            "antofagasta", None, 0.35, 0.3, ()),
]
COMMUNE_IDX = {c.id: i for i, c in enumerate(COMMUNES)}
PEOPLE_PER_HOUSEHOLD = 3.0  # ~3 personas por hogar (informe A2: 3 × 170 L ≈ 500 L/día)


# ---------------------------------------------------------------------------
# Nodos de red (capacidad para nuevas cargas grandes)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GridNode:
    id: str
    name: str
    headroom_mw: float  # capacidad disponible para DC desde 2012 (MW de solicitud)
    expansions: tuple  # ((fecha 'YYYY-MM', +MW, nombre), ...)
    src: str


GRID_NODES: list[GridNode] = [
    GridNode("norte", "Norte RM (Quilicura, Lampa, Colina, Huechuraba)", 640,
             (("2029-06", 400, "Nueva S/E 220 kV zona norte"),),
             "Supuesto calibrado: saturado hacia 2025 ('ya no hay capacidad en Quilicura', "
             "Systep: Lampa 'podría agotarse rápido'; DC Iris y DC STM en lista de espera)."),
    GridNode("polpaico", "S/E Polpaico 500 kV (Tiltil)", 110,
             (("2030-09", 600, "Ampliación Polpaico / enlace HVDC"),),
             "Supuesto: DC SC2 (500 MW) quedó 'sin espacio' y pidió operar en sept. 2030 (CEN)."),
    GridNode("poniente", "Poniente RM (Pudahuel, Cerrillos, Padre Hurtado, centro)", 380,
             (("2030-06", 500, "Kimal–Lo Aguirre HVDC y refuerzos Lo Aguirre"),),
             "Supuesto calibrado: Transmisoras de Chile advierte rechazos en Pudahuel."),
    GridNode("sur", "Sur RM (San Bernardo, Buin, Puente Alto)", 300,
             (("2029-12", 300, "Refuerzo S/E Alto Jahuel"),),
             "Supuesto calibrado: DC Alto Jahuel (200 MW) en lista de espera (CEN)."),
    GridNode("valparaiso", "Valparaíso", 150, (("2030-01", 100, "Refuerzo regional"),),
             "Supuesto."),
    GridNode("sur_sen", "Biobío y otras regiones", 200, (), "Supuesto."),
    GridNode("antofagasta", "Antofagasta (norte grande)", 800, (),
             "Supuesto: vertimiento solar y holgura de generación en el norte (A3)."),
]
NODE_IDX = {n.id: i for i, n in enumerate(GRID_NODES)}


# ---------------------------------------------------------------------------
# Acuíferos (modelo de caja: nivel relativo en metros)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Aquifer:
    id: str
    name: str
    storage_mm3_per_m: float  # millones de m3 por metro de nivel (área × coef. almacenamiento)
    base_trend_m_yr: float  # descenso sin data centers (DGA: 'descensos sostenidos')
    recharge_m_yr: float  # recarga natural expresada en metros de nivel por año
    prohibition: bool  # zona de prohibición/restricción DGA
    src: str


AQUIFERS: list[Aquifer] = [
    Aquifer("stgo_norte", "Acuífero Santiago Norte (humedal de Quilicura)", 40.0, -0.30, 1.0,
            True, "Supuesto: recarga sin cifra primaria (vacío A8). DGA reporta descensos "
            "sostenidos 25 años (DARH 346/2011)."),
    Aquifer("stgo_central", "SHAC Santiago Central", 120.0, -0.25, 1.0, True,
            "Zona de prohibición Res. DGA 22/2019 (DARH 53/2019). Recarga supuesta (vacío A8)."),
]
AQUIFER_IDX = {a.id: i for i, a in enumerate(AQUIFERS)}
WETLAND_HA = 468  # humedal de Quilicura, hectáreas protegidas


# ---------------------------------------------------------------------------
# Proyectos de data centers
# ---------------------------------------------------------------------------
@dataclass
class Project:
    id: str
    name: str
    operator: str
    commune: str
    lat: float
    lon: float
    it_mw: float  # potencia TI nominal
    cooling: str  # "evaporativo" | "aire" | "hibrido"
    announce: str  # 'YYYY-MM': solicitud de conexión / ingreso a tramitación
    fuel_t: float | None = None  # toneladas de combustible declaradas (None = derivar del tamaño)
    capex_musd: float | None = None
    water_right_ls: float | None = None
    dist_homes_m: float | None = None
    hv_line: bool = False  # requiere nueva línea de alta tensión visible
    pre_existing: bool = False  # operando antes de 2012
    anonymous: bool = False  # DC agregado para cuadrar el inventario (sin nombre público)
    real_status: str | None = None  # estado a nov-2026 según el informe (solo para validar)
    real_online: str | None = None  # fecha real de operación aproximada (solo para validar)
    site: str | None = None  # agrupa fases de un mismo campus
    hist: tuple = ()  # eventos históricos documentados (solo informativo)
    src: str = ""
    extra: dict = field(default_factory=dict)


def _p(**kw) -> Project:
    return Project(**kw)


ANON_SRC = ("Supuesto: DC sin nombre público, agregado para reproducir el inventario "
            "Colliers 1S-2026 (36 DC, 255 MW) / GPS (39 DC, 311 MW en Santiago).")

PROJECTS: list[Project] = [
    # ------------------------------------------------------------------ Quilicura (6 DC)
    _p(id="google_quilicura_1", name="Google Quilicura (fase 1)", operator="Google",
       commune="quilicura", lat=-33.356, lon=-70.752, it_mw=16, cooling="evaporativo",
       announce="2012-09", capex_musd=150, water_right_ls=50, dist_homes_m=400,
       real_status="operando", real_online="2015-10", site="google_quilicura",
       src="Anuncio 2012 (200 empleos construcción, 20 operación). Derecho de agua 50 L/s."),
    _p(id="google_quilicura_2", name="Google Quilicura (ampliación)", operator="Google",
       commune="quilicura", lat=-33.357, lon=-70.754, it_mw=16, cooling="evaporativo",
       announce="2018-09", capex_musd=140, dist_homes_m=400, real_status="operando",
       real_online="2021-06", site="google_quilicura",
       src="Ampliación 2018 (1.000 empleos construcción, >200 operación). "
           "Total declarado 30 MW; CEN registró 31,7 MW (abr-2025)."),
    _p(id="sonda_quilicura", name="Sonda Quilicura", operator="Sonda", commune="quilicura",
       lat=-33.365, lon=-70.742, it_mw=6, cooling="aire", announce="2012-03",
       real_status="operando", real_online="2014-06",
       src="Operador citado en el informe; tamaño y fecha supuestos."),
    _p(id="cirion_quilicura", name="Cirion Quilicura", operator="Cirion", commune="quilicura",
       lat=-33.368, lon=-70.738, it_mw=6, cooling="aire", announce="2011-09",
       real_status="operando", real_online="2013-06",
       src="Operador citado en el informe; tamaño y fecha supuestos."),
    _p(id="ascenty_scl1", name="Ascenty Santiago 1", operator="Ascenty", commune="quilicura",
       lat=-33.348, lon=-70.745, it_mw=8, cooling="aire", announce="2017-03",
       real_status="operando", real_online="2019-06",
       src="Operador citado en el informe; tamaño y fecha supuestos."),
    _p(id="ascenty_scl2", name="Ascenty Santiago 2", operator="Ascenty", commune="quilicura",
       lat=-33.346, lon=-70.748, it_mw=20, cooling="aire", announce="2020-06",
       real_status="operando", real_online="2022-09",
       src="Operador citado en el informe; tamaño y fecha supuestos."),
    _p(id="microsoft_scl01", name="Microsoft SCL01", operator="Microsoft", commune="quilicura",
       lat=-33.350, lon=-70.760, it_mw=30, cooling="aire", announce="2021-01",
       real_status="operando", real_online="2023-09",
       src="Operador citado en Quilicura; tamaño y fecha supuestos."),
    # ------------------------------------------------------------------ Resto norte RM
    _p(id="edgeconnex_colina", name="EdgeConneX Colina", operator="EdgeConneX",
       commune="colina", lat=-33.250, lon=-70.690, it_mw=10, cooling="aire",
       announce="2019-09", real_status="operando", real_online="2022-06",
       src="Citado en el informe (Colina); tamaño y fecha supuestos."),
    _p(id="anon_colina_1", name="DC empresarial Colina", operator="(anónimo)", commune="colina",
       lat=-33.230, lon=-70.680, it_mw=3, cooling="aire", announce="2016-01", anonymous=True,
       real_status="operando", src=ANON_SRC),
    _p(id="anon_colina_2", name="DC colocation Colina", operator="(anónimo)", commune="colina",
       lat=-33.265, lon=-70.700, it_mw=8, cooling="aire", announce="2020-02", anonymous=True,
       real_status="operando", src=ANON_SRC),
    _p(id="anon_colina_3", name="DC colocation Colina 2", operator="(anónimo)",
       commune="colina", lat=-33.270, lon=-70.705, it_mw=8, cooling="aire",
       announce="2023-09", anonymous=True, real_status="operando", src=ANON_SRC),
    *[_p(id=f"anon_huechuraba_{i}", name=f"DC empresarial Ciudad Empresarial {i}",
         operator="(anónimo)", commune="huechuraba", lat=-33.385 + 0.002 * i,
         lon=-70.625, it_mw=mw, cooling="aire", announce=a, anonymous=True,
         real_status="operando", pre_existing=pre, src=ANON_SRC)
      for i, (a, pre, mw) in enumerate([("2010-01", True, 2), ("2013-05", False, 2),
                                        ("2017-08", False, 3)], start=1)],
    _p(id="anon_lampa_1", name="DC empresarial Lampa", operator="(anónimo)", commune="lampa",
       lat=-33.290, lon=-70.840, it_mw=2, cooling="aire", announce="2019-03", anonymous=True,
       real_status="operando", src=ANON_SRC),
    # ------------------------------------------------------------------ Poniente / centro
    _p(id="equinix_pudahuel", name="Equinix (ex-Entel) Pudahuel", operator="Equinix",
       commune="pudahuel", lat=-33.430, lon=-70.790, it_mw=5, cooling="aire",
       announce="2009-01", pre_existing=True, real_status="operando",
       src="Supuesto: centro de datos de Entel adquirido por Equinix (2022)."),
    _p(id="anon_enea_1", name="DC colocation ENEA 1", operator="(anónimo)", commune="pudahuel",
       lat=-33.405, lon=-70.795, it_mw=8, cooling="aire", announce="2017-06", anonymous=True,
       real_status="operando", src=ANON_SRC),
    _p(id="microsoft_scl02", name="Microsoft SCL02", operator="Microsoft", commune="pudahuel",
       lat=-33.400, lon=-70.800, it_mw=30, cooling="aire", announce="2022-09",
       real_status="operando", real_online="2025-03",
       src="Supuesto: segundo sitio de la región Azure; ubicación y tamaño supuestos."),
    _p(id="anon_enea_2", name="DC colocation ENEA 2", operator="(anónimo)", commune="pudahuel",
       lat=-33.410, lon=-70.800, it_mw=12, cooling="aire", announce="2022-06",
       anonymous=True, real_status="operando", src=ANON_SRC),
    *[_p(id=f"anon_centro_{i}", name=f"DC telco/empresa centro {i}", operator="(anónimo)",
         commune="santiago", lat=-33.44 - 0.004 * (i % 5), lon=-70.65 - 0.004 * (i // 5),
         it_mw=mw, cooling="aire", announce=a, anonymous=True, pre_existing=a < "2012-01",
         real_status="operando", src=ANON_SRC)
      for i, (a, mw) in enumerate([
          ("2005-01", 2), ("2007-01", 2), ("2008-01", 3), ("2009-01", 2), ("2010-01", 3),
          ("2011-01", 2), ("2013-03", 3), ("2015-09", 3), ("2017-01", 3), ("2018-06", 4),
          ("2020-09", 5), ("2022-08", 6), ("2024-03", 6)], start=1)],
    # ------------------------------------------------------------------ Sur RM
    _p(id="odata_san_bernardo", name="ODATA San Bernardo", operator="ODATA (Aligned)",
       commune="san_bernardo", lat=-33.580, lon=-70.720, it_mw=18, cooling="aire",
       announce="2021-01", real_status="operando", real_online="2023-03",
       src="Citado en el informe (San Bernardo); tamaño y fecha supuestos."),
    _p(id="anon_sb_1", name="DC colocation San Bernardo", operator="(anónimo)",
       commune="san_bernardo", lat=-33.585, lon=-70.725, it_mw=10, cooling="aire",
       announce="2023-03", anonymous=True, real_status="operando", src=ANON_SRC),
    # ------------------------------------------------------------------ Otras regiones
    _p(id="anon_valpo_1", name="DC Valparaíso", operator="(anónimo)", commune="valparaiso",
       lat=-33.045, lon=-71.600, it_mw=6, cooling="aire", announce="2009-01",
       pre_existing=True, anonymous=True, real_status="operando", src=ANON_SRC),
    _p(id="anon_valpo_2", name="DC Curauma", operator="(anónimo)", commune="valparaiso",
       lat=-33.130, lon=-71.560, it_mw=8, cooling="aire", announce="2019-01",
       anonymous=True, real_status="operando", src=ANON_SRC),
    _p(id="anon_conce_1", name="DC Concepción 1", operator="(anónimo)", commune="concepcion",
       lat=-36.820, lon=-73.040, it_mw=8, cooling="aire", announce="2008-01",
       pre_existing=True, anonymous=True, real_status="operando", src=ANON_SRC),
    _p(id="anon_antof_1", name="DC minero Antofagasta", operator="(anónimo)",
       commune="antofagasta", lat=-23.640, lon=-70.390, it_mw=6, cooling="aire",
       announce="2010-01", pre_existing=True, anonymous=True, real_status="operando",
       src=ANON_SRC),
    # ================================================================== En construcción
    _p(id="aws_huechuraba", name="AWS Huechuraba", operator="Amazon (AWS)",
       commune="huechuraba", lat=-33.352, lon=-70.655, it_mw=30, cooling="aire",
       announce="2023-01", capex_musd=205, dist_homes_m=300, hv_line=True,
       real_status="construccion",
       hist=("DIA aprobada 12-07-2024", "Reclamación rechazada por 2° Tribunal Ambiental "
             "06-04-2026"),
       src="US$205 M, 10,9 ha, enfriamiento de bajo consumo de agua. Línea AT desistida."),
    _p(id="scala_lampa", name="Scala Lampa", operator="Scala Data Centers", commune="lampa",
       lat=-33.320, lon=-70.790, it_mw=40, cooling="aire", announce="2024-01",
       real_status="construccion", src="En construcción según el informe; tamaño supuesto."),
    _p(id="odata_lampa", name="ODATA Lampa", operator="ODATA (Aligned)", commune="lampa",
       lat=-33.325, lon=-70.800, it_mw=30, cooling="aire", announce="2024-03",
       real_status="construccion", src="En construcción según el informe; tamaño supuesto."),
    # ================================================================== Tramitación / anunciados
    _p(id="google_cerrillos", name="Google Cerrillos", operator="Google (Dataluna)",
       commune="cerrillos", lat=-33.513, lon=-70.706, it_mw=80, cooling="evaporativo",
       announce="2019-05", fuel_t=696, capex_musd=200, water_right_ls=169,
       dist_homes_m=250, real_status="tramitacion",
       hist=("RCA 127/2020: hasta 169 L/s (derechos 228 L/s)",
             "2° Tribunal Ambiental anula parcialmente la RCA (feb-2024)",
             "Google desiste (jul-2024)", "Reingresa como pertinencia, 63 chillers por aire "
             "(jul-2026)", "SEA RM: no requiere SEIA (oct-2026)"),
       src="Subestación de 120 MW (TI supuesta 80 MW), 44 generadores, ~696 t de combustible."),
    _p(id="campo_lampa", name="Campo de Datos Lampa", operator="Copenhagen Infrastructure "
       "Partners", commune="lampa", lat=-33.337, lon=-70.763, it_mw=100, cooling="aire",
       announce="2024-06", fuel_t=511, capex_musd=850, dist_homes_m=50,
       real_status="tramitacion", extra={"permit_start": "2026-04"},
       src="US$850 M, 100 MW, 22 ha, >112 MW de generadores, 511 t, <50 m de Valle Grande."),
    _p(id="stpa_puente_alto", name="Inmobiliaria STPA Puente Alto", operator="Inmobiliaria STPA",
       commune="puente_alto", lat=-33.630, lon=-70.595, it_mw=120, cooling="aire",
       announce="2024-06", fuel_t=756, dist_homes_m=250, real_status="tramitacion",
       extra={"permit_start": "2026-05"},
       src="756 t de combustible, ~250 m de Bajos de Mena (pertinencia). TI supuesta."),
    _p(id="polpaico_campus_norte", name="Polpaico Campus Norte", operator="(no informado)",
       commune="tiltil", lat=-33.165, lon=-70.885, it_mw=60, cooling="aire",
       announce="2026-09", fuel_t=880, real_status="tramitacion",
       src="Ingresó pertinencia el 17-09-2026. Tamaño y combustible supuestos."),
    _p(id="grenergy_tiltil", name="Grenergy Tiltil", operator="Grenergy", commune="tiltil",
       lat=-33.150, lon=-70.900, it_mw=5, cooling="aire", announce="2026-03", capex_musd=25,
       real_status="tramitacion", src="Proyecto de US$25 M; tamaño supuesto."),
    _p(id="aws_padre_hurtado", name="AWS Padre Hurtado", operator="Amazon (AWS)",
       commune="padre_hurtado", lat=-33.565, lon=-70.830, it_mw=30, cooling="aire",
       announce="2025-06", real_status="tramitacion", extra={"permit_start": "2025-11"},
       src="DIA en tramitación; tamaño supuesto."),
    _p(id="pertinencia_buin", name="Pertinencia Buin", operator="(no informado)",
       commune="buin", lat=-33.720, lon=-70.720, it_mw=30, cooling="aire",
       announce="2025-03", fuel_t=600, real_status="tramitacion",
       extra={"permit_start": "2026-06"},
       src="Informe: pertinencias en Buin. Tamaño y combustible supuestos."),
    _p(id="microsoft_scl03", name="Microsoft SCL03", operator="Microsoft", commune="quilicura",
       lat=-33.352, lon=-70.765, it_mw=24.9, cooling="aire", announce="2025-01",
       src="24,9 MW en Quilicura (Neto/DataCenterBoom 2026)."),
    _p(id="cirion_quilicura_2", name="Cirion Quilicura (nuevo)", operator="Cirion",
       commune="quilicura", lat=-33.369, lon=-70.736, it_mw=12, cooling="aire",
       announce="2025-09", src="12 MW en Quilicura (Neto/DataCenterBoom 2026)."),
    _p(id="ascenty_3", name="Ascenty Santiago 3", operator="Ascenty", commune="quilicura",
       lat=-33.344, lon=-70.750, it_mw=16, cooling="aire", announce="2026-03",
       src="16 MW en Quilicura (Neto/DataCenterBoom 2026)."),
    _p(id="scala_curauma", name="Scala Curauma", operator="Scala Data Centers",
       commune="valparaiso", lat=-33.135, lon=-71.555, it_mw=30, cooling="aire",
       announce="2025-09", src="Citado en el informe (Valparaíso/Curauma); tamaño supuesto."),
    _p(id="dci_la_polvora", name="DCI La Pólvora", operator="(no informado)",
       commune="valparaiso", lat=-33.040, lon=-71.640, it_mw=20, cooling="aire",
       announce="2026-03", src="Citado en el informe; tamaño supuesto."),
    *[_p(id=f"antofagasta_concesion_{i}", name=f"Concesión fiscal Antofagasta {i}",
         operator="(varios)", commune="antofagasta", lat=-23.60 - 0.03 * i,
         lon=-70.35 + 0.02 * i, it_mw=100, cooling="aire", announce="2026-06",
         capex_musd=1000, src="Bienes Nacionales tramita ≥10 concesiones (>US$3.000 M). "
         "Agregadas en 3 lotes de 100 MW (supuesto).")
      for i in (1, 2, 3)],
    # ================================================================== Lista de espera CEN
    _p(id="dc_sc2", name="DC SC2 (RTB Energy)", operator="RTB Energy", commune="tiltil",
       lat=-33.158, lon=-70.892, it_mw=500, cooling="aire", announce="2024-09",
       real_status="lista_espera", src="500 MW en S/E Polpaico 500 kV, operación pedida "
       "sept-2030; lista de espera 'sin espacio' (CEN)."),
    _p(id="dc_stm", name="DC STM", operator="(no informado)", commune="colina",
       lat=-33.200, lon=-70.700, it_mw=220, cooling="aire", announce="2024-11",
       real_status="lista_espera", src="220 MW en lista de espera (CEN)."),
    _p(id="dc_alto_jahuel", name="DC Alto Jahuel", operator="(no informado)", commune="buin",
       lat=-33.735, lon=-70.690, it_mw=200, cooling="aire", announce="2024-09",
       real_status="lista_espera", src="200 MW en lista de espera (CEN)."),
    _p(id="dc_iris", name="DC Iris", operator="(no informado)", commune="lampa",
       lat=-33.310, lon=-70.820, it_mw=100, cooling="aire", announce="2025-02",
       real_status="lista_espera", src="100 MW en lista de espera (CEN)."),
    _p(id="espera_pudahuel", name="Proyecto en espera Pudahuel", operator="(no informado)",
       commune="pudahuel", lat=-33.395, lon=-70.810, it_mw=200, cooling="aire",
       announce="2025-04", anonymous=True, real_status="lista_espera",
       src="Supuesto: completa los 6 proyectos / 1.420 MW en espera del CEN."),
    _p(id="espera_lampa", name="Proyecto en espera Lampa", operator="(no informado)",
       commune="lampa", lat=-33.280, lon=-70.830, it_mw=200, cooling="aire",
       announce="2025-05", anonymous=True, real_status="lista_espera",
       src="Supuesto: completa los 6 proyectos / 1.420 MW en espera del CEN."),
]
PROJECT_IDX = {p.id: i for i, p in enumerate(PROJECTS)}


# ---------------------------------------------------------------------------
# Datos observados (para validar el modelo)
# ---------------------------------------------------------------------------
OBSERVED = {
    "rm_demand_2021": {"value": 90, "unit": "MW", "src": "Ministerio de Energía citando al CEN"},
    "rm_demand_2025": {"value": 260, "unit": "MW", "src": "Ministerio de Energía citando al CEN"},
    "chile_demand_2025": {"value": 325, "unit": "MW", "src": "CEN"},
    "chile_it_2025": {"value": 228, "unit": "MW", "src": "Colliers 2025 (33 DC)"},
    "chile_it_2026": {"low": 255, "high": 311, "unit": "MW",
                      "src": "Colliers 1S-2026 (todo Chile) a GPS 1S-2026 (solo Santiago)"},
    "rm_it_2026": {"value": 311.4, "unit": "MW", "src": "GPS Property 1S-2026 (Santiago, 39 DC)"},
    "n_dc_2026": {"low": 36, "high": 39, "unit": "DC",
                  "src": "Colliers 1S-2026 (36) a GPS 1S-2026 (39 en Santiago)"},
    "google_water_2024": {"value": 458, "unit": "ML/año", "src": "Google Quilicura 2024"},
    "google_power_2024": {"value": 30.0, "unit": "MW medio",
                          "src": "~262.800 MWh declarados en 2024 (30 MW medios); CEN 31,7 MW"},
    "quilicura_share": {"value": 62, "unit": "%", "src": "Neto/DataCenterBoom 2026"},
    "waitlist_2026": {"value": 1420, "unit": "MW", "n": 6, "src": "CEN: 6 proyectos en espera"},
    "litigations_2012_2026": {"value": 2, "unit": "casos",
                              "src": "Cerrillos (R-270/271-2020) y Huechuraba (2024-2026)"},
    "organized_opposition": {"communes": ["cerrillos", "quilicura", "huechuraba", "lampa"],
                             "src": "Mosacat (Cerrillos), Resistencia Socioambiental Quilicura, "
                                    "El Pincoyazo (Huechuraba), vecinos de Valle Grande (Lampa)"},
}
