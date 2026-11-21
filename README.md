# team-33 Platanus Hack 26: Santiago ft. Buk Project

**Current project logo:** project-logo.png

<img src="./project-logo.png" alt="Project Logo" width="200" />

Track: 🌐 Simulations

team-33

- Anish Samtani ([@chimera-z](https://github.com/chimera-z))
- Alejandro Lorca Acevedo ([@rooniejr](https://github.com/rooniejr))
- Andrés Alonso Faúndez Ortega ([@andresfaundez](https://github.com/andresfaundez))

## Aterriza

Chile aprueba los data centers de a uno, pero se suman en la misma red, el mismo acuífero y las
mismas comunas. Aterriza simula ese efecto acumulado mes a mes, de 2012 a 2035, con un modelo
híbrido de agentes y stocks: proyectos que eligen comuna y enfriamiento, el SEA, la fila de
conexión del CEN, tribunales y ~2.300 hogares sintéticos cuya oposición cambia permisos y
ubicaciones. Mide agua, electricidad, vecinos movilizados, juicios e inversión, comuna por
comuna, en 200 futuros por regla.

**Demo: https://aterriza.onrender.com** (plan gratis de Render: tras 15 minutos sin visitas, la
primera carga tarda 20 a 30 s; "Tu regla" tarda 40 a 60 s y "Coloca un data center", unos 35 s).

## Qué puedes hacer en la página

- **Elegir una regla** (como hoy, permisos rápidos, solo aire, evaluación conjunta, ir al norte
  o las tres que más ayudan) y ver el mapa y seis cifras de 2035.
- **Armar tu propia regla** con 8 palancas: umbral de diésel, plazo de permisos, incentivo al
  norte, fondo comunitario, proyectos por año, evaluación conjunta, enfriar sin agua y
  transparencia.
- **Mover el año** de 2012 a 2035 y pintar las comunas por vecinos movilizados, agua o MW, en
  valor o en cambio respecto de "Como hoy".
- **Colocar un data center** (sitio, tamaño, enfriamiento, año y regla). Cada futuro se corre
  con y sin él, y se siguen sus vecinos a menos de 3 km: cuántos se movilizan, si llega a operar,
  si va a tribunales y a cuántos proyectos les quita red.
- **Tocar una comuna o un proyecto** para ver su detalle, su historia y su probabilidad de
  terminar operando, en tribunales o esperando red.
- **Revisar el modelo** en "Detalle técnico": chequeos, ecuaciones y supuestos con su fuente.

## Hallazgos principales

De una batería de 15.080 simulaciones y de los 200 futuros por regla de la portada. El resto,
con su método, en [FINDINGS.md](FINDINGS.md).

- **El freno es la red, no el permiso.** Con permisos 4 veces más rápidos, la RM pasa de 836 a
  840 MW en 2030: solo 0,4% más. Los proyectos aprobados igual esperan conexión eléctrica.
- **No hay que elegir.** Aire + fondo comunitario + incentivo al norte mejoran a la vez agua,
  conflicto, juicios e inversión en 84% de los 200 futuros de la portada: 52% menos hogares
  movilizados, 33% menos juicios, 55% menos agua y 12% más inversión en 2035. La cuenta de la luz
  sube 1,8% en vez de 2,0% (supuesto: la demanda que se va a Antofagasta no presiona la tarifa).
- **El agua decide el juicio.** Si Google hubiera enfriado Cerrillos con aire en 2019, la
  probabilidad de juicio bajaba de 83% a 2%.
- **Más proyectos, más espera.** Con el doble de proyectos se conecta solo 19% más, pero los
  juicios se multiplican por 2,3.

## ¿Le podemos creer?

- **Reproduce el pasado sin verlo.** En modo libre el modelo recibe cada proyecto (tamaño, lugar,
  enfriamiento, fecha de anuncio) y genera solo 2012–2026. Pasa 14 de 14 chequeos: 7 de
  validación (no se ajustó a ese dato) y 7 de calibración. Ejemplo: electricidad de los data
  centers de la RM a fines de 2025, 260 MW observados y 254 MW simulados (banda 5–95: 185–338).
- **Le gana a una regla trivial.** El chequeo del estado de los 54 proyectos conocidos a
  noviembre de 2026 solo pasa si el modelo supera a la regla "lista del CEN espera; anunciado hace
  3 o más años opera", que acierta 91%. El modelo acierta 96%.
- **Límites a la vista.** Los 1.420 MW en espera se cumplen casi por construcción, y las comunas
  con oposición no son una prueba ciega. 29 de los 62 proyectos no tienen nombre público: cuadran
  el inventario y la lista del CEN. Los efectos de la evaluación conjunta, la transparencia y la
  tarifa no tienen dato chileno: son supuestos con rango (13 de los 41 parámetros se sortean en
  cada futuro).
- **Qué tan firmes son los hallazgos:** `uv run python -m dcsim.sensitivity` escribe
  `cache/sensitivity.json`; el resultado está en la sección 4 de [FINDINGS.md](FINDINGS.md).

## Cómo correrlo

Necesitas uv. Tiempos medidos en un computador de 10 núcleos.

```bash
uv sync                                       # dependencias fijadas en uv.lock
uv run uvicorn dcsim.server:app --port 8000   # la página en http://localhost:8000
uv run pytest                                 # 28 tests, ~8 s
uv run ruff check .                           # estilo, igual que la CI
uv run python -m dcsim.validation             # los 14 chequeos
uv run python -m dcsim.explore                # 15.080 simulaciones, ~3 min
uv run python -m dcsim.findings               # resume la batería en cache/findings.json
uv run python -m dcsim.sensitivity            # qué tan firmes son los hallazgos
uv run python -m dcsim.precompute             # 2.200 futuros de la portada, ~40 s
```

El servidor parte al instante y los tests tardan segundos porque leen resultados versionados en
`cache/`. Sus nombres llevan una huella de `model.py`, `catalog.py`, `params.py`, `policy.py` y
`montecarlo.py`: si cambias uno de esos archivos, corre `precompute`, `explore` y `findings`.
Si no, el servidor vuelve a simular al partir y `test_findings_were_built_with_this_code` falla.
Con el mismo código y la misma máquina, esos comandos rehacen byte a byte lo versionado.

## Estructura

| Ruta | Qué hay |
|---|---|
| `dcsim/__init__.py` | Marca el paquete. |
| `dcsim/model.py` | El motor: agentes, hogares y stocks, paso mensual 2012–2035, modos `free` y `anchored`. |
| `dcsim/catalog.py` | Datos con su fuente: 15 comunas, 7 nodos de red, 2 acuíferos, 62 proyectos y lo observado. |
| `dcsim/params.py` | 41 parámetros con valor central, rango, fuente y tipo (dato, calibrado o supuesto). |
| `dcsim/policy.py` | Las palancas (`Policy`) y las 8 reglas predefinidas. |
| `dcsim/montecarlo.py` | N futuros en paralelo, mediana y percentiles 5–95, caché en disco. |
| `dcsim/validation.py` | Hindcast: los 14 chequeos. |
| `dcsim/insights.py` | Cada regla contra "Como hoy" y 6 hipótesis del informe. |
| `dcsim/explore.py` | Batería de 185 configuraciones: factorial de 7 palancas, barridos, contrafactuales. |
| `dcsim/findings.py` | Resume la batería en 7 hallazgos (`cache/findings.json`). |
| `dcsim/sensitivity.py` | Qué tan firmes son los hallazgos (`cache/sensitivity.json`). |
| `dcsim/place.py` | "Coloca un data center": cada futuro con y sin el data center del usuario. |
| `dcsim/precompute.py` | Rehace los resultados de la portada y borra los obsoletos. |
| `dcsim/server.py` | API (FastAPI) y archivos estáticos. |
| `web/` | La página: `index.html`, `story.js`, `place.js`, `story.css` e `img/`. |
| `tests/` | Determinismo, palancas, hindcast, invariantes del motor y de la API, coloca un data center. |
| `cache/` | Versionados: `findings.json` y los `*_200_*.json`, así el servidor no simula en una CPU chica. `explore_raw.json` (~32 MB) no. |
| `render.yaml` | El servicio en Render. |
| `pyproject.toml`, `uv.lock` | Dependencias: NumPy, FastAPI, uvicorn; pytest, ruff y httpx para desarrollo. |
| `.github/workflows/ci.yml` | CI: ruff y pytest en cada push y pull request. |
| `FINDINGS.md` | Hallazgos, método y límites. |

## API

| Ruta | Qué devuelve |
|---|---|
| `GET /api/story` | Lo que usa la portada: 6 reglas con sus cifras de 2035, chequeos y hallazgos. |
| `GET /api/meta` | Comunas, proyectos, nodos, reglas, parámetros y datos observados. |
| `GET /api/scenario/{sid}` | Los 200 futuros resumidos de una regla predefinida. |
| `POST /api/run` | Simula `{"policy": {...}}` (campos de `Policy`, 422 si no valen); `baseline`/`compare` comparan con las mismas semillas. |
| `GET /api/baseline` | La línea base con las mismas semillas que `POST /api/run`. |
| `GET /api/place/site?lat=&lon=` | Comuna, nodo, acuífero y hogares alrededor de un punto, sin simular. |
| `POST /api/place` | Los futuros con y sin el data center del usuario (400 si el sitio no sirve). |
| `GET /api/validation` | Los 14 chequeos con sus bandas y fuentes. |
| `GET /api/insights` | Las 6 hipótesis y el efecto de cada regla en 2030 y 2035. |
| `GET /api/communes/{sid}/{year}` | Balance por comuna en un año. |
| `GET /api/findings` | Los hallazgos de `cache/findings.json`. |
| `GET /api/status` | Qué resultados están en memoria (health check). |

## Despliegue

Render, con `render.yaml` (plan free): `uv sync --frozen --no-dev`, arranque con `uvicorn` y
health check en `/api/status`. Al partir no simula: lee de `cache/` los 2.200 futuros de la
portada (10 reglas × 200 y la validación). "Tu regla" y "Coloca un data center" sí simulan.

| Variable | En Render | Si falta | Qué controla |
|---|---|---|---|
| `DCSIM_WORKERS` | 1 | hasta 8 | Procesos que simulan; 1 porque el plan free tiene 512 MB. |
| `DCSIM_N_CUSTOM` | 60 | 100 | Futuros de "Tu regla". |
| `DCSIM_N_PLACE` | 20 | 40 | Futuros de "Coloca un data center", cada uno con y sin él. |

## Fuentes de datos

Cada dato trae su fuente en el campo `src` de `catalog.py` y `params.py`; lo que no tiene dato
dice "Supuesto". Las principales: un informe de investigación de noviembre de 2026; el CEN y el
Ministerio de Energía (consumo de los data centers, lista de espera); la DGA (acuíferos y zonas
de prohibición); el SEA y el Tribunal Ambiental (permisos y litigios); el Censo 2017; reportes de
empresas y del mercado (Google, Colliers, GPS Property); y LBNL, NREL y EPA para parámetros
técnicos. Las cifras de prensa no son fuentes primarias y las coordenadas son aproximadas.

## Historia del proyecto

- **Sábado 21-nov-2026, 01:07 a 02:51 (hora de Chile).** El repo parte de la plantilla del
  hackathon. El equipo construye primero BedFlow Chile, un simulador del paso de pacientes de
  urgencia a camas de hospital. Sus PR #4 (motor), #5 (API, tests y CI) y #6 (interfaz) se
  fusionan en `main`.
- **Cerca de las 05:00, cambio de tema.** `795fde9` (05:04) vuelve el repo a la plantilla, y en
  `main` el commit `3e7dfd4` (05:18) borra todos los archivos.
- **Desde las 05:30.** `5c62800` es el primer commit del simulador de data centers y ya trae el
  motor completo y la validación. Desde ahí la historia es incremental: interfaz y API, batería
  de simulaciones, hallazgos, despliegue, correcciones de una revisión y "Coloca un data center".

> Nota del 21-nov-2026: desde `3e7dfd4`, la rama por defecto de GitHub (`main`) está vacía.
> Aterriza vive en las ramas `person-a/*` hasta que se fusione en `main` (ver `git log --all`).

## Créditos

Equipo 33 (arriba). Fotos de Wikimedia Commons (CC BY-SA 4.0, CC BY-SA 2.0 y CC0), con autor y
licencia en `web/img/credits.json` y al pie de la página. Mapa © OpenStreetMap.
