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
mismas comunas, y nadie suma el efecto de todos. Aterriza simula ese efecto conjunto, comuna por
comuna: si se construye todo lo aprobado y en trámite, ¿alcanzan el agua y la red?, ¿y si los
proyectos que faltan enfrían con aire en vez de agua? No es una suma de planilla: en cada futuro
los proyectos compiten por la misma red, esperan en la fila del CEN, generan oposición y pueden
terminar en tribunales. Está pensada para que el
SEA, el municipio, los vecinos y la empresa discutan sobre los mismos números durante la
evaluación ambiental. Detrás hay una simulación del efecto acumulado, mes a mes de 2012 a 2035, con un modelo
híbrido de agentes y stocks: proyectos que eligen comuna y enfriamiento, el SEA, la fila de
conexión del CEN, tribunales y ~2.300 hogares sintéticos cuya oposición cambia permisos y
ubicaciones. Mide agua, electricidad, vecinos movilizados, juicios e inversión, comuna por
comuna, en 200 futuros por regla.

**Demo: https://aterriza.onrender.com** (plan gratis de Render: tras 15 minutos sin visitas, la
primera carga tarda 20 a 30 s; un cambio en la simulación por comuna o "Tu regla" tarda 40 a 60 s).

## Qué puedes hacer en la página

- **Sumar todos los data centers de una comuna** (Quilicura por defecto): los que operan, los
  que se construyen, los que están en trámite y los que esperan red, con lo que cada uno declaró
  al SEA y su fuente. Para los que aún no operan, elegir agua o aire desde 2027 y ver el agua, la
  electricidad, la red libre del nodo, los MW esperando conexión y los vecinos movilizados en 2030
  y 2035, comparados con lo declarado en los mismos 60 futuros. Cada proyecto muestra además su
  trade-off a plena carga: cuánta agua usa enfriando con agua y cuántos MW más pide con aire.
- **Elegir una regla** (como hoy, permisos rápidos, solo aire, evaluación conjunta, ir al norte
  o las tres que más ayudan) y ver el mapa y seis cifras de 2035.
- **Armar tu propia regla** con 8 palancas: umbral de diésel, plazo de permisos, incentivo al
  norte, fondo comunitario, proyectos por año, evaluación conjunta, enfriar sin agua y
  transparencia. Se compara con seguir como hoy en los mismos futuros: en cuántos queda mejor
  y en cuántos peor.
- **Mover el año** de 2012 a 2035 y pintar las comunas por vecinos movilizados, agua o MW, en
  valor o en cambio respecto de "Como hoy".
- **Tocar una comuna o un proyecto** para ver su detalle, su historia y su probabilidad de
  terminar operando, en tribunales o esperando red.
- **Revisar el modelo** en "Detalle técnico": chequeos, ecuaciones y supuestos con su fuente.

## Hallazgos principales

De una batería de 15.080 simulaciones, de los 200 futuros por regla de la portada y de la
simulación por comuna (60 futuros). El resto, con su método, en [FINDINGS.md](FINDINGS.md).

- **Quilicura, todo sumado.** Con lo que declaró cada proyecto, sus data centers usan en 2035
  17,9 L/s de agua (la de ~3.100 hogares) y 188 MW. Si los 4 que aún no operan enfriaran con
  agua desde 2027: 42,2 L/s (2,4 veces más), 18 MW menos de electricidad y 64% de vecinos
  movilizados en vez de 46%. Y cada uno de esos 4 opera en 2035 en 80% a 87% de los futuros, en
  vez de 92% a 98% con aire: la simulación muestra los juicios, anulaciones y esperas que una
  suma no ve.
- **El freno es la red, no el permiso.** Con permisos 4 veces más rápidos, la RM pasa de 818 a
  820 MW en 2030: solo 0,3% más. Los proyectos aprobados igual esperan conexión eléctrica.
- **No hay que elegir.** Aire + fondo comunitario + incentivo al norte mejoran a la vez agua,
  conflicto, juicios e inversión en 82% de los 200 futuros de la portada: 49% menos hogares
  movilizados, 33% menos juicios, 53% menos agua y 14% más inversión en 2035. La cuenta de la luz
  sube 1,8% en vez de 2,1% (supuesto: la demanda que se va a Antofagasta no presiona la tarifa).
- **El agua decide el juicio.** Si Google hubiera enfriado Cerrillos con aire en 2019, la
  probabilidad de juicio habría bajado de 78% a 4%. Es el hallazgo más frágil: depende de cuánto pesa
  el agua en la opinión de los vecinos (ver abajo).
- **Más proyectos, más espera.** Con el doble de proyectos se conecta solo 19% más, pero los
  juicios se multiplican por 2,3.

## ¿Le podemos creer?

- **Reproduce el pasado sin verlo.** En modo libre el modelo recibe cada proyecto (tamaño, lugar,
  enfriamiento, fecha de anuncio) y genera solo 2012–2026. Pasa 14 de 14 chequeos: 6 de
  validación (no se ajustó a ese dato) y 8 de calibración. Ejemplo: electricidad de los data
  centers de la RM a fines de 2025, 260 MW observados y 252 MW simulados (banda 5–95: 184–345).
- **Frente a una regla trivial, apenas.** El chequeo del estado de cada proyecto a noviembre de
  2026 solo pasa si el modelo supera a la regla "lista del CEN espera; anunciado hace 3 o más
  años opera". La supera por un solo proyecto, sin nombre público: 93% frente a 91% en los 55.
  En los 26 con nombre público empatan, 85% cada uno. El modelo no adivina el estado de cada
  proyecto mejor que esa regla; lo que agrega es sumar agua, red y vecinos.
- **Límites a la vista.** Los 1.420 MW en espera se cumplen casi por construcción, la potencia
  de Google sale de lo que Google declara y las comunas con oposición no son una prueba ciega. De
  los 63 proyectos, 34 tienen nombre público y 29 son supuestos que cuadran el inventario y la
  lista del CEN. Los efectos de la evaluación conjunta, la transparencia y la
  tarifa no tienen dato chileno: son supuestos con rango. De los 53 parámetros, 13 se sortean en
  cada futuro y los otros 40 se prueban en sus extremos.
- **Qué tan firmes son los hallazgos.** `dcsim/sensitivity.py` (76.500 simulaciones) lleva cada
  uno de los 40 parámetros fijos a sus dos extremos y luego los sortea todos juntos. Prueba los 6
  hallazgos que comparan reglas o historias (el séptimo, «No hay destino escrito», describe
  cuánto varían los futuros y no tiene un criterio de sí o no). 5 se mantienen en los 80 ajustes; el de Cerrillos, en 79: si el agua pesa la mitad en
  la opinión de los vecinos, la probabilidad de juicio con agua baja de 74% a 15% (en los 100
  futuros de esa prueba) y deja de cumplirse. Con todo sorteado a la vez se mantienen los 6. 7 de los 40 parámetros no mueven
  ninguna de estas cifras, así que sus ajustes se mantienen por construcción. Detalle en la sección 4 de
  [FINDINGS.md](FINDINGS.md).

## Cómo correrlo

Necesitas uv. Tiempos medidos en un computador de 10 núcleos.

```bash
uv sync --frozen                              # las versiones de uv.lock, igual que la CI
uv run uvicorn dcsim.server:app --port 8000   # la página en http://localhost:8000
uv run pytest -q                              # 43 tests, ~9 s
uv run ruff check .                           # estilo, igual que la CI
uv run python -m dcsim.validation             # los 14 chequeos
# si cambias el modelo, en este orden:
uv run python -m dcsim.precompute             # portada y "como hoy" de "Tu regla", ~40 s
uv run python -m dcsim.explore                # 15.080 simulaciones, ~3 min
uv run python -m dcsim.findings               # resume la salida de explore en cache/findings.json
uv run python -m dcsim.sensitivity            # 76.500 simulaciones, ~15 min
```

El servidor parte al instante y los tests tardan segundos porque leen resultados versionados en
`cache/`. Los nombres de los ensambles y el campo `model` de `findings.json` y
`sensitivity.json` llevan una huella de `model.py`, `catalog.py`, `params.py`, `policy.py` y
`montecarlo.py`: si cambias uno de esos archivos, corre `precompute`, `explore`, `findings` y
`sensitivity`, en ese orden. Si no, el servidor vuelve a simular al partir y fallan
`test_findings_were_built_with_this_code` y `test_sensitivity_was_built_with_this_code`. Con el
mismo código y la misma máquina, `precompute` y `findings` rehacen byte a byte lo versionado, y
`sensitivity` repite sus resultados (solo cambia el tiempo que anota).

## Estructura

| Ruta | Qué hay |
|---|---|
| `dcsim/__init__.py` | Marca el paquete. |
| `dcsim/model.py` | El motor: agentes, hogares y stocks, paso mensual 2012–2035, modos `free` y `anchored`. |
| `dcsim/catalog.py` | Datos con su fuente: 15 comunas, 7 nodos de red, 2 acuíferos, 63 proyectos y lo observado. |
| `dcsim/params.py` | 53 parámetros con valor central, rango, fuente y tipo (dato, calibrado o supuesto); 13 se sortean en cada futuro. |
| `dcsim/policy.py` | Las palancas (`Policy`) y las 8 reglas predefinidas. |
| `dcsim/montecarlo.py` | N futuros en paralelo, mediana y percentiles 5–95, caché en disco. |
| `dcsim/validation.py` | Prueba con el pasado (hindcast): los 14 chequeos. |
| `dcsim/insights.py` | Cada regla contra "Como hoy" y 6 hipótesis del informe. |
| `dcsim/explore.py` | Batería de 185 configuraciones: factorial de 7 palancas, barridos, contrafactuales. |
| `dcsim/findings.py` | Resume la batería en 7 hallazgos (`cache/findings.json`). |
| `dcsim/sensitivity.py` | Qué tan firmes son los hallazgos: 40 parámetros fijos en sus extremos y sorteados juntos (`cache/sensitivity.json`). |
| `dcsim/sea.py` | Lo que cada data center declaró al SEA (agua, energía, enfriamiento, diésel) con su fuente; se muestra en la simulación por comuna. |
| `dcsim/precompute.py` | Rehace los resultados de la portada y "como hoy" con 60 y 100 futuros para "Tu regla"; borra los obsoletos. |
| `dcsim/server.py` | API (FastAPI) y archivos estáticos. |
| `web/` | La página: `index.html`, `story.js`, `calc.js` (la simulación por comuna), `story.css` e `img/`. |
| `tests/` | Determinismo, palancas, prueba con el pasado, invariantes del motor y de la API, "Tu regla" en las mismas semillas, la simulación por comuna (historia intacta, aire cuesta electricidad), sensibilidad. |
| `cache/` | Versionados: `findings.json`, `sensitivity.json`, los `*_200_*.json` de la portada y `anchored_60_*`/`anchored_100_*` ("como hoy" para "Tu regla"), así el servidor no simula en una CPU chica. `explore_raw.json` (~32 MB) no: solo lo rehace `explore`. |
| `render.yaml` | El servicio en Render. |
| `pyproject.toml`, `uv.lock` | Dependencias: NumPy, FastAPI, uvicorn; pytest, ruff y httpx para desarrollo. |
| `.github/workflows/ci.yml` | CI: ruff y pytest en cada push y pull request. |
| `FINDINGS.md` | Hallazgos, método y límites. |

## API

| Ruta | Qué devuelve |
|---|---|
| `GET /api/story` | Lo que usa la portada: 6 reglas con sus cifras de 2035, chequeos, hallazgos y un resumen de la sensibilidad (`sensitivity`). |
| `GET /api/meta` | Comunas, proyectos, nodos, reglas, parámetros y datos observados. |
| `GET /api/scenario/{sid}` | Los 200 futuros resumidos de una regla predefinida. |
| `POST /api/run` | Simula `{"policy": {...}}` (campos de `Policy`; 422 si no valen) en `DCSIM_N_CUSTOM` futuros, semillas 0 a N−1 (422 también si sobran campos o llega un NaN). Suma `baseline` (`n` y medianas de 2035 de seguir como hoy en esas semillas) y `compare`: por cifra, en cuántos futuros la regla queda mejor, peor o igual (`better`, `worse`, `same`, `n`); para los MW operando, con más o con menos (`more`, `less`). |
| `GET /api/baseline` | Seguir como hoy en esas mismas semillas, completo (el mapa de "Tu regla" compara contra esto). |
| `GET /api/sensitivity` | El análisis de sensibilidad completo (`cache/sensitivity.json`). |
| `POST /api/calc` | La simulación por comuna: `{"cooling": {"<proyecto>": "aire" \| "evaporativo"}}` para los proyectos que aún no operan (cambio desde 2027). Devuelve el ensamble de los mismos futuros que "Tu regla" (por comuna, por proyecto y la red libre de cada nodo) y `compare`: por comuna, en cuántos futuros queda mejor, peor o igual que lo declarado. Sin cambios responde al instante. |
| `GET /api/validation` | Los 14 chequeos con sus bandas y fuentes. |
| `GET /api/insights` | Las 6 hipótesis y el efecto de cada regla en 2030 y 2035. |
| `GET /api/communes/{sid}/{year}` | Balance por comuna en un año. |
| `GET /api/findings` | Los hallazgos de `cache/findings.json`. |
| `GET /api/status` | Qué resultados están en memoria (health check). |

## Despliegue

Render, con `render.yaml` (plan free): `uv sync --frozen --no-dev`, arranque con `uvicorn` y
health check en `/api/status`. Al partir no simula: lee de `cache/` los 2.200 futuros de la
portada (10 reglas × 200 y la validación) y "como hoy" con los futuros de "Tu regla", que es
también lo declarado en la simulación por comuna. "Tu regla" y sus cambios sí simulan al pedirlos.

| Variable | En Render | Si falta | Qué controla |
|---|---|---|---|
| `DCSIM_WORKERS` | 1 | hasta 8 | Procesos que simulan; 1 porque el plan free tiene 512 MB. |
| `DCSIM_N_CUSTOM` | 60 | 100 | Futuros de "Tu regla" y de la simulación por comuna, comparados con lo declarado en esas mismas semillas. |
| `UV_COMPILE_BYTECODE` | 1 | — | Compila el bytecode al construir: el plan free parte de la imagen tras dormir y así no recompila al despertar. |

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
  fusionan en `main`. Los 5 commits del motor de BedFlow (`a59fa4d` a `8d4e1a3`) aparecen con
  fecha 22-nov porque el reloj de ese computador iba adelantado: GitHub los fusionó en el PR #4 el
  21-nov a las 02:38.
- **Cerca de las 05:00, cambio de tema.** `795fde9` (05:04) vuelve el repo a la plantilla, y en
  `main` un commit de reinicio, `3e7dfd4` (05:18), borra todos los archivos.
- **Desde las 05:30.** `5c62800` es el primer commit del simulador de data centers y ya trae el
  motor completo y la validación. Desde ahí la historia es incremental: interfaz y API, batería
  de simulaciones, hallazgos, despliegue, correcciones de una revisión y el análisis de
  sensibilidad. Tras el feedback del mentor (21-nov, noche) la página se centra en la
  simulación de evaluación conjunta por comuna y el modelo se calibra con lo declarado al SEA. La sección
  "Coloca un data center" quedó fuera; está guardada en la rama `person-a/coloca-un-dc-archivo`.
- **Integración.** Mientras `main` estuvo vacía, el trabajo siguió en las ramas `person-a/*`;
  después se integró a `main` por PR. Las ramas `judge/*` de los merges son las correcciones de
  una revisión hecha con la rúbrica del jurado (sensibilidad, "Tu regla" en las mismas semillas,
  README y CI).

## Créditos

Equipo 33 (arriba). Fotos de Wikimedia Commons (CC BY-SA 4.0, CC BY-SA 2.0 y CC0), con autor y
licencia en `web/img/credits.json` y al pie de la página. Mapa © OpenStreetMap.
