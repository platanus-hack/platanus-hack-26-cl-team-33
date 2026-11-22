"""Lo que cada data center declaró al SEA (agua, energía, enfriamiento), con su fuente.

Solo se muestra en la calculadora: no entra al modelo ni a la huella del código. Las cifras del
modelo que vienen de aquí están en catalog.py (tamaño, diésel) y se citan en su campo ``src``.
Recopilado el 21-11-2026 desde el SEIA, el buscador de pertinencias, el Tribunal Ambiental y
prensa que cita los expedientes. Confianza alta: documento del SEA o resolución oficial; media:
prensa que cita la presentación. Los caudales promedio en L/s son conversiones nuestras de m³/año.
"""

SEA = {
    "google_quilicura_1": {
        "instrument": "Consulta de pertinencia (2012-2013) y DIA de combustible",
        "rca": "044/2016", "water_rights_ls": 50, "cooling": "torres evaporativas",
        "url": "https://infofirma.sea.gob.cl/DocumentosSEA/MostrarDocumento?docId=56%2F79%2F"
               "5da3b81f2f6e96f0e1740ab072571d17e39a",
        "confidence": "alta",
        "note": "El data center original no pasó por evaluación ambiental; solo su estanque de "
                "diésel (205,6 t, 23 generadores). No declara MW.",
    },
    "google_quilicura_2": {
        "instrument": "DIA", "rca": "074/2018", "water_avg_ls": 15, "water_rights_ls": 50,
        "cooling": "6 torres evaporativas",
        "url": "https://seia.sea.gob.cl/archivos/2018/03/07/1da_RCA_074-2018_PARAM.pdf",
        "confidence": "alta",
        "note": "Pozos con 15 L/s promedio dentro de 50 L/s de derechos, más agua de Aguas "
                "Andinas. "
                "Google informó 458 millones de litros en 2024 (~14,5 L/s). 438 t de diésel.",
    },
    "sonda_quilicura": {
        "instrument": "Pertinencia (2012) y DIA de ampliación", "rca": "404/2018",
        "facility_mw": 11.72, "water_max_ls": 1.52, "cooling": "agua helada en circuito cerrado",
        "url": "https://infofirma.sea.gob.cl/DocumentosSEA/MostrarDocumento?docId=2a%2F03%2F"
               "5da14508f961fc599e487a7b24d3cc26a091",
        "confidence": "alta", "note": "5 + 6,72 MW de capacidad de red; 343,5 t de diésel.",
    },
    "cirion_quilicura_2": {
        "instrument": "DIA", "rca": "20241300153", "cooling": "aire (132 equipos DX), sin agua",
        "url": "https://firma.sea.gob.cl/publicaciones/2024/01/12/1705094335_2161068247",
        "confidence": "alta",
        "note": "No declara MW: 16 generadores de 1,85 MW y 340 t de diésel. La prensa informa "
                "20 MW iniciales; el modelo usa 12 MW.",
    },
    "ascenty_scl1": {
        "instrument": "DIA", "rca": "113/2021", "it_mw": 6.3,
        "cooling": "chillers en circuito cerrado",
        "url": "https://seia.sea.gob.cl/expediente/ficha/fichaPrincipal.php?modo=ficha&"
               "id_expediente=2147377549",
        "confidence": "media", "note": "6,3 MW anunciados; el modelo usa 8 MW.",
    },
    "ascenty_scl2": {
        "instrument": "DIA", "rca": "486/2021",
        "cooling": "chillers por aire en circuito cerrado (llenado único de 440 m³)",
        "url": "https://firma.sea.gob.cl/publicaciones/45/39/2152199018",
        "confidence": "alta", "note": "No declara MW (la prensa dice 16 o 31 MW). 663 t de diésel.",
    },
    "ascenty_3": {
        "instrument": "sin expediente encontrado", "water_avg_ls": 0.1,
        "cooling": "circuito cerrado",
        "url": "https://blog.investchile.gob.cl/ascenty-third-data-center-chile",
        "confidence": "media",
        "note": "16 MW según InvestChile (2025); 70 m³/año para enfriar según El Desconcierto.",
    },
    "ascenty_data_hall": {
        "instrument": "DIA", "rca": "202513001408", "it_mw": 36, "facility_mw": 55.8,
        "cooling": "chillers por aire en circuito cerrado (llenado único de 447 m³)",
        "url": "https://firma.sea.gob.cl/publicaciones/2025/10/24/1761269762_2166707963",
        "confidence": "alta",
        "note": "36 MW de servidores y PUE estimado 1,55 (55,8 MW). Aprobado el 17-11-2025, "
                "condicionado a acreditar la factibilidad eléctrica (S/E Punta Verde). 765 t de "
                "diésel.",
    },
    "microsoft_scl03": {
        "instrument": "DIA", "rca": "202313001133", "it_mw": 19.2, "facility_mw": 24.9,
        "water_avg_ls": 0.48, "cooling": "evaporativo directo unas 600 h al año",
        "url": "https://seia.sea.gob.cl/archivos/2023/04/04/RCA_Proyecto_Microsoft_SCL03_firma.pdf",
        "confidence": "alta",
        "note": "19,2 MW para servidores más 5,7 MW auxiliares. El agua (7.632 a 15.264 m³/año) "
                "viene de prensa que cita la RCA.",
    },
    "google_cerrillos": {
        "instrument": "Consulta de pertinencia (2026)", "water_max_ls": 169, "water_rights_ls": 228,
        "cooling": "63 chillers por aire, sin agua (diseño 2026)",
        "url": "https://firma.sea.gob.cl/publicaciones/2026/10/16/1792184183_398EDC04-5B5E-4158-"
               "9D27-FFA37D459947",
        "confidence": "alta",
        "note": "Los 169 L/s eran la extracción continua del diseño de 2020 (RCA 127/2020, torres "
                "evaporativas), con derechos por 228 L/s. 120 MW son generadores de respaldo, no "
                "servidores. 696 t de diésel (871,8 t en 2020).",
    },
    "scala_lampa": {
        "instrument": "DIA", "rca": "202213001416", "water_avg_ls": 1.06,
        "cooling": "chillers en circuito cerrado (llenado único de 523,5 m³)",
        "url": "https://www.sea.gob.cl/tce/tabla-comision-de-evaluacion-1209",
        "confidence": "media",
        "note": "Campus de 120 MW según Scala; 48 MW de servidores en la fase en operación. "
                "El agua (33.434 m³/año) incluye usos sanitarios.",
    },
    "odata_lampa": {
        "instrument": "DIA", "rca": "098/2021", "it_mw": 16,
        "url": "https://seia.sea.gob.cl/expediente/ficha/fichaPrincipal.php?modo=normal&"
               "id_expediente=2147474024",
        "confidence": "media", "note": "16 MW en los módulos visibles; el total podría ser mayor.",
    },
    "campo_lampa": {
        "instrument": "Consulta de pertinencia", "rca": None, "expediente": "PERTI-2026-4755",
        "facility_mw": 100, "cooling": "90 chillers en circuito cerrado, sin evaporación",
        "url": "https://www.pincoyazo.cl/post/seis-centros-de-datos-podrian-no-evaluar-impactos-"
               "ambientales",
        "confidence": "media", "note": "511 t de diésel; a menos de 50 m de Valle Grande.",
    },
    "aws_huechuraba": {
        "instrument": "DIA", "rca": "202413001289", "water_max_ls": 3.5, "water_avg_ls": 0.17,
        "cooling": "aire exterior, con agua en días de calor (~3% del año)",
        "url": "https://www.sea.gob.cl/tce/tabla-comision-de-evaluacion-1623",
        "confidence": "media",
    },
    "edgeconnex_colina": {
        "instrument": "DIA", "rca": "20221300166", "it_mw": 7, "cooling": "aire (CRAC)",
        "url": "https://www.sea.gob.cl/tce/tabla-comision-de-evaluacion-1064",
        "confidence": "media", "note": "Tiene otras dos RCA de ampliación (2022 y 2024).",
    },
    "equinix_pudahuel": {
        "instrument": "DIA", "rca": "155/2015", "it_mw": 7.5, "cooling": "chillers",
        "url": "https://infofirma.sea.gob.cl/DocumentosSEA/MostrarDocumento?docId=19/07/"
               "338a09601698ecbb6ba0cdddc48bc5749912",
        "confidence": "media",
    },
    "dc_alto_jahuel": {
        "instrument": "Consulta de pertinencia", "expediente": "PERTI-2026-5962",
        "facility_mw": 92.7,
        "url": "https://firma.sea.gob.cl/publicaciones/2026/07/24/1784914495_42EC06A7-D626-4DCD-"
               "8456-E599CAEE7C3F",
        "confidence": "alta",
        "note": "Alto Jahuel, Buin: subestación propia de 92,7 MW y 990 t de diésel, bajo el "
                "umbral de 1.000 t. El SEA resolvió que no requiere evaluación (24-07-2026).",
    },
    "pertinencia_buin": {
        "instrument": "Consulta de pertinencia", "expediente": "PERTI-2026-7066",
        "url": "https://eldesconcierto.cl/actualidad/sea-autoriza-primer-data-center-evaluacion-"
               "ambiental-alto-jahuel-metros-la-casa-kast-n5461002",
        "confidence": "media",
        "note": "Alto Jahuel Campus Sur (GR Huiña SpA, Grenergy), ingresada el 29-05-2026. "
                "No se encontró su tamaño.",
    },
    "odata_san_bernardo": {
        "instrument": "DIA", "rca": "202113001320", "it_mw": 40.6, "water_avg_ls": 0.25,
        "cooling": "chillers en circuito cerrado",
        "url": "https://firma.sea.gob.cl/publicaciones/4b/49/2154310247",
        "confidence": "alta",
        "note": "40,6 MW según prensa; el modelo usa 18 MW (el inventario está calibrado con los "
                "311 MW instalados). 731 t de diésel.",
    },
    "aws_padre_hurtado": {
        "instrument": "DIA", "rca": "20241300136", "water_avg_ls": 0.09,
        "cooling": "evaporativo directo con paneles adiabáticos",
        "url": "https://firma.sea.gob.cl/publicaciones/2023/12/29/1703884418_2160968795",
        "confidence": "alta",
        "note": "Aprobado en enero de 2024 (no está en trámite). Agua de 788 a 2.888 m³/año; "
                "180 t de diésel.",
    },
    "stpa_puente_alto": {
        "instrument": "Consulta de pertinencia", "expediente": "PERTI-2026-10381",
        "url": "https://www.pincoyazo.cl/post/seis-centros-de-datos-podrian-no-evaluar-impactos-"
               "ambientales",
        "confidence": "media", "note": "756 t de diésel.",
    },
    "scala_curauma": {
        "instrument": "DIA", "rca": "202205001191", "it_mw": 30,
        "cooling": "chillers por aire en circuito cerrado",
        "url": "https://firma.sea.gob.cl/publicaciones/2024/12/24/1735051139_2164034208",
        "confidence": "alta", "note": "Ampliación aprobada en diciembre de 2024.",
    },
    "dci_la_polvora": {
        "instrument": "Consulta de pertinencia", "expediente": "PERTI-2026-9361",
        "url": "https://www.pincoyazo.cl/post/seis-centros-de-datos-podrian-no-evaluar-impactos-"
               "ambientales",
        "confidence": "media", "note": "990 t de diésel.",
    },
}

# Cerrillos: lo que de verdad declaró el proyecto de 2020 frente a cifras que circulan
CERRILLOS_WATER_NOTE = (
    "169 L/s es la extracción continua que declaró el diseño de 2020 (torres evaporativas) y 228 "
    "L/s sus derechos de agua. Los 7,6 millones de litros al día que circulan no aparecen en los "
    "documentos de Cerrillos: coinciden con el diseño de Google en Canelones, Uruguay."
)
