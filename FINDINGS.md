# Hallazgos: efecto acumulado de data centers en Chile

Simulador híbrido (agentes + stocks y flujos) de cómo los data centers que llegan a Chile,
sobre todo al corredor norte de la Región Metropolitana, afectan agua, red eléctrica,
conflicto y beneficios en cada comuna entre 2012 y 2035. Código en `dcsim/`, interfaz en `web/`.

Todos los números de este documento salen del código de este repositorio:

| Qué | Cómo se calcula | Simulaciones |
|---|---|---|
| Validación | `dcsim/validation.py`, modo `free` (el modelo genera la historia 2012–2026 sin conocerla) | 200 |
| Hallazgos | `dcsim/explore.py` + `dcsim/findings.py`, modo `anchored` (historia real hasta nov-2026, luego proyección); la historia alternativa de Cerrillos usa el modo `free` | 15.080 (185 configuraciones) y los 200 futuros por regla de la portada |
| Hipótesis del informe | `dcsim/insights.py`, escenarios predefinidos de `dcsim/policy.py` | 200 por escenario |
| Qué tan firmes son | `dcsim/sensitivity.py`: cada parámetro fijo en sus extremos y todos sorteados juntos (sección 4) | 76.500 |

Las comparaciones usan números aleatorios comunes: cada configuración corre con las mismas
semillas y los proyectos conocidos sortean de un flujo propio, así la diferencia entre dos
configuraciones se debe a la regla que cambia (también al cambiar la demanda: los proyectos
nuevos de una demanda baja son un subconjunto de los de una alta). Los valores son medianas;
los porcentajes "de los futuros" son la fracción de pares de réplicas donde se cumple la
afirmación. El modelo tiene 53 parámetros. En cada futuro se sortean 13, entre ellos el efecto
de la evaluación conjunta y de la transparencia, que no tienen dato chileno. Los otros 40
quedan en su valor central; la sección 4 los lleva uno a uno a sus extremos y luego los sortea
todos juntos.

## 1. El modelo reproduce lo observado (14/14 chequeos)

Sin ver la historia, el modelo genera 2012–2026 a partir de los proyectos reales (tamaño,
lugar, enfriamiento y fecha de anuncio) y se compara con datos observados. Banda = percentiles
5–95. 6 chequeos son validación (el modelo no se ajustó a ese dato) y 8 son calibración.

| Chequeo | Tipo | Observado | Modelo (mediana [banda]) |
|---|---|---|---|
| Consumo eléctrico DC de la RM, fin 2021 (MW) | validación | 90 | 104 [86–132] |
| Consumo eléctrico DC de la RM, fin 2025 (MW) | validación | 260 | 254 [185–338] |
| Consumo eléctrico DC de Chile, 2025 (MW) | validación | 325 | 285 [217–376] |
| Capacidad instalada en Santiago, mediados 2026 (MW TI) | calibración | 311 | 326 [251–401] |
| Data centers operando, mediados 2026 | calibración | 36–39 | 37 [35–39] |
| Agua de Google Quilicura, 2024 (ML) | calibración | 458 | 484 [407–565] |
| Potencia media de Google Quilicura, 2024 (MW) | calibración | 30 | 31,8 [27,4–35,3] |
| Parte del consumo de Quilicura que usan los DC (%) | calibración | 62 | 60 [53–64] |
| MW esperando conexión a la red, 2026 | calibración | 1.420 | 1.420 [1.192–1.447] |
| Proyectos en lista de espera, 2026 | calibración | 6 | 6 [6–7] |
| Litigios ambientales contra DC, 2012–2026 | calibración | 2 | 2 [1–4] |
| Parte del consumo eléctrico nacional (%) | validación | 2–3 | 2,5 [1,9–3,2] |
| Comunas con oposición organizada | validación | Cerrillos, Quilicura, Huechuraba, Lampa | las mismas 4 en el top 4 |
| Estado de cada proyecto conocido a nov-2026 | validación | 54 proyectos | acierta 96% (92% en los 25 con nombre) |

Límites de estos chequeos:
- Los 1.420 MW en espera se cumplen casi por construcción: la capacidad libre de cada nodo se
  ajustó a ese dato y dos proyectos supuestos completan los 6 proyectos del CEN.
- El estado de cada proyecto se compara con una regla trivial (lista del CEN espera; anunciado
  hace 3 o más años opera), que acierta 91%. El chequeo pasa solo si el modelo la supera. En los
  25 proyectos con nombre público, que son la prueba más limpia, el modelo acierta 92% y la regla
  84%; los otros 29 son supuestos que cuadran el inventario y la lista del CEN.
- La potencia de Google Quilicura no es una prueba ciega: su tamaño (2 × 16 MW) sale de los 30 MW
  que declara Google y su factor de carga alto (0,92) es un supuesto. Por eso cuenta como
  calibración.
- Las comunas con oposición no son una prueba ciega: los barrios sintéticos se ubicaron donde
  hay viviendas junto a sitios conocidos (Valle Grande, La Pincoya, Lonquén).
- Los 2 juicios se reproducen en total, no proyecto por proyecto: en modo libre el modelo casi
  nunca demanda a AWS Huechuraba, que sí fue a tribunales.

## 2. Hallazgos

Paquete y transparencia usan los 200 futuros por regla de la portada; permisos y punto de
quiebre, barridos de 120 futuros; Cerrillos, Lampa y la comuna más afectada, 200 futuros de la
batería (Cerrillos en modo libre). La sección 4 revisa si cada uno resiste cambios en los
supuestos.

### No hay que elegir: 3 reglas mejoran a la vez agua, conflicto, juicios e inversión en 84% de los futuros
Enfriamiento por aire + fondo comunitario + incentivo al norte, frente a las reglas de hoy
(2035, 200 futuros, los mismos de la portada): 13% más MW de data centers operando, 12% más
inversión, 29% menos inversión perdida, 52% menos hogares movilizados, 33% menos juicios y
55% menos agua.
*La cuenta de la luz* no sube más: 1,8% en vez de 2,0%, porque parte de la demanda se va a
Antofagasta, donde sobra energía solar. Supone que esa demanda no presiona la tarifa; el rango
es amplio (en 9 de cada 10 futuros, entre +0,2% y +4,1%).

### El cuello de botella no es el permiso: permisos 4 veces más rápidos dan solo 0,4% más MW en Santiago al 2030
Con permisos 75% más cortos, la RM pasa de 836 a 840 MW en 2030 y el plazo medio entre
anuncio y operación baja apenas 3,8 meses. Los proyectos aprobados igual esperan conexión
eléctrica. Relevante para la Mesa Permanente (nov-2026), cuyo objetivo es acortar permisos.

### Punto de quiebre: el doble de proyectos conecta solo 19% más, pero los juicios se multiplican por 2,3
Con 10 proyectos nuevos al año en vez de 5, la lista de espera crece 3,0 veces y los hogares
movilizados pasan de 17% a 36%. Con 4 veces más proyectos: 30% más MW y 8 veces más juicios.
La red no crece al ritmo de los anuncios: cada proyecto extra suma espera, no MW, y los
proyectos que esperan red generan rechazo sin dejar beneficios.

### Historia alternativa: con aire en Cerrillos, la probabilidad de juicio baja de 83% a 2%
Se vuelve a correr 2012–2026 cambiando solo la decisión de enfriamiento de Google Cerrillos
(169 L/s de un acuífero en zona de prohibición). Con aire, a fines de 2023 el proyecto
estaría operando en 93% de los futuros. En la realidad hubo juicio, el tribunal anuló parcialmente el permiso
en 2024 y Google rediseñó con aire en 2026. La elección de enfriamiento pesa más que el
tamaño del proyecto.
*Supuestos clave:* usar agua de un acuífero en zona de prohibición da fundamento legal a un
juicio (`lit_w_water`) y aumenta el rechazo de los vecinos (`op_w_water`); la sección 4
muestra que el hallazgo no se sostiene si el peso del agua en la opinión baja a la mitad.

### Dónde importa más que cuánto: alejar un solo proyecto de las casas baja 60% el conflicto de toda Lampa
Campo de Datos Lampa (100 MW) está a menos de 50 m de Valle Grande. El mismo proyecto en la
periferia de la comuna baja los hogares movilizados de 26% a 11% y los hogares a menos de
500 m de un DC grande de 3.968 a 1.701 (2035). Se cumple en 91% de los futuros.

### Información vs plata: publicar el uso real de agua baja el conflicto casi tanto como pagar US$38 millones al año
Transparentar el consumo: −30% hogares movilizados. Fondo comunitario de US$20.000 por MW al
año (≈ US$38 millones en 2035): −31% (2035, 200 futuros). Google Quilicura usa solo el 29% de
su derecho de agua, pero los vecinos temen el 100%.
*Supuesto:* depende de cuánto recupera la confianza la información (entre 0,05 y 0,25,
sorteado en cada futuro) y de cuánto pesa el agua en la opinión. Si ese peso baja a la mitad,
queda en el límite: la transparencia logra justo dos tercios de la baja del fondo (sección 4).

### No hay destino escrito: 6 comunas pueden terminar como la más afectada en 2035
En 200 futuros con las mismas reglas, la comuna con más hogares movilizados cambia según el
orden en que llegan los proyectos: Cerrillos (29%), Quilicura (20%), Tiltil (12%), Padre
Hurtado (12%); 6 comunas lo son en al menos 5% de los futuros. La "comuna de sacrificio" se
decide en el camino, no en el mapa, y por eso una evaluación proyecto por proyecto no puede
anticiparla.

## 3. Hipótesis del informe

| Hipótesis | Veredicto | Evidencia (2035 salvo que se indique) |
|---|---|---|
| Exigir enfriamiento por aire reduce el agua, pero satura antes la red (S1) | Se confirma | Agua de los DC de la RM −53% (57 → 26 L/s); consumo en el mes peak +2,2% y lista de espera +16%. El agua ahorrada se paga con más electricidad en verano. |
| Evaluar en conjunto acorta los plazos porque reduce los litigios (S1) | Parcialmente | Litigios −33% y hogares movilizados −39%, pero el plazo anuncio → operación sube 2,0 meses (44,7 → 46,7): las ventanas de evaluación y las reubicaciones se comen lo ahorrado en tribunales. Parte del efecto en litigios es supuesto (factor 0,2–0,5, sorteado). |
| Acelerar permisos no conecta más DC si la red está saturada (A3) | Se confirma | Permisos al doble de rápido: +0,0% MW en la RM en 2030 (829 → 829) y el plazo baja solo 2,4 meses. |
| Transparentar el agua reduce más el conflicto que compensar (S2) | Parcialmente | Solo transparencia: −30% hogares movilizados; solo fondo de US$20.000/MW/año: −31%. Magnitudes parecidas; juntas suman. |
| Con el umbral de 1.000 t casi ningún DC nuevo pasa por SEIA (S7, A1) | Se confirma | Desde 2027, con 1.000 t solo 2% de los proyectos nuevos entra al SEIA; con 80 t, 75%. Supone que los proyectos declaran diésel justo bajo el límite, como los 7 casos reales tras el DS 17 (511 a 990 t). |
| Un incentivo al norte descomprime la RM (A3, S8) | Se confirma | En 2030 Antofagasta pasa de 322 a 523 MW, los MW esperando red −53% y los MW operando en la RM −1,8%. |

Los barridos de una palanca (permisos, demanda) usan 120 futuros y los escenarios 200, por eso
la RM de 2030 "como hoy" aparece como 836 MW en la sección 2 y 829 MW en esta tabla.

## 4. Qué tan firmes son los hallazgos

De los 53 parámetros, 13 se sortean en cada futuro. Los otros 40 quedan en su valor central;
`dcsim/params.py` marca 26 como supuestos, 8 como datos y 6 como calibrados.
Se prueban los 6 hallazgos que comparan reglas o historias; el séptimo, «No hay destino
escrito», describe cuánto varían los futuros y no tiene un criterio de sí o no.
`dcsim/sensitivity.py` los mueve de dos formas. Uno a la vez: cada uno va al extremo bajo y
luego al alto de su rango (80 ajustes de 100 futuros), con las mismas semillas y los mismos 13
sorteos de una corrida normal. Todos juntos: 400 futuros en que, además de los 13 de siempre,
se sortean los 40 dentro de su rango. En cada ajuste se rehace la cuenta de cada hallazgo como
en `dcsim/findings.py` y se aplica el criterio de la tabla. Son 76.500 simulaciones (933 s en
10 núcleos); el resultado queda en `cache/sensitivity.json`.

Un extremo puede dejar al modelo lejos de lo observado. Por eso cada ajuste también corre
2012–2026 en modo libre y revisa que siga reproduciendo la historia: mediana de juicios a fines
de 2026 entre 1 y 4 (hubo 2) y, a menos de 25% del dato, el consumo de los data centers de la
RM a fines de 2025 (260 MW), los MW esperando red en 2026 (1.420) y la capacidad instalada en
Santiago a mediados de 2026 (311 MW). Los 80 ajustes pasan esa regla.

El valor central se calcula con 100 futuros, así que puede diferir un poco de la sección 2.

| Hallazgo | Qué se mide (se mantiene si…) | Supuestos centrales | Uno a la vez: rango | Se mantiene | Todos juntos (400 futuros) |
|---|---|---|---|---|---|
| No hay que elegir | Futuros en que aire + fondo + norte es igual o mejor en las seis cifras (al menos 50%) | 84% | 73% a 86% | 80 de 80 | 79% |
| El cuello de botella no es el permiso | Cambio de los MW en la RM en 2030 con permisos 4 veces más rápidos (menos de +5%) | +0,38% | 0% a +2,15% | 80 de 80 | +0,69% |
| Punto de quiebre | Cuántas veces más crecen los juicios que los MW operando con el doble de proyectos (más de 1) | 2,15 | 1,80 a 2,29 | 80 de 80 | 1,96 |
| Historia alternativa (Cerrillos) | Probabilidad de juicio con agua → con aire (baja al menos 25 puntos y queda en la mitad o menos) | 83% → 1% | con agua 8% a 90%; con aire 1% a 6% | 79 de 80 | 69% → 3,5% |
| Dónde importa más que cuánto | Baja del conflicto de Lampa en 2035 al alejar Campo de Datos Lampa (25% o más) | 61,8% | 52,6% a 75,0% | 80 de 80 | 57,8% |
| Información vs plata | Cambio del conflicto de la RM en 2035 con transparencia y con fondo (las dos bajan y la transparencia logra al menos dos tercios de la baja del fondo) | −28,1% y −30,4% (cociente 0,92) | cociente 0,67 a 1,14 | 80 de 80 | −28,9% y −29,2% (0,99) |

Con todos los parámetros sorteados juntos, los seis hallazgos se mantienen. En ese sorteo, 196
de los 400 futuros reproducen la historia cada uno por su cuenta (con los supuestos centrales,
70 de 100); con solo esos 196, los seis también se mantienen (estas cifras las imprime
`uv run python -m dcsim.sensitivity` al terminar).

8 de los 40 parámetros no mueven ninguna de estas seis cifras: el consumo y el crecimiento
eléctrico del país, el costo de red, el factor de verano del agua, la recarga del acuífero, el
NOx, las horas de prueba del diésel y los apagones. Mueven otras (la cuenta de la luz, el
acuífero, el diésel), y sus 16 ajustes se mantienen por construcción.

**Lo que no se sostiene.** La historia alternativa de Cerrillos falla en 1 de los 80 ajustes:
si el peso del agua que los vecinos ven usar en su opinión (`op_w_water`) baja a la mitad
(0,6 en vez de 1,2), la probabilidad de juicio con agua cae de 83% a 8% y con aire queda en 1%.
Con ese peso, el juicio es raro aun con agua y enfriar con aire casi no cambia nada. El ajuste
que le sigue en debilidad, un rechazo de partida más bajo (`op_intercept` = −2,5), deja 49% con
agua y 1% con aire, y cumple. En el mismo ajuste de `op_w_water`, información vs plata queda en
el límite: la transparencia baja el conflicto 19,4% y el fondo 29,0%, un cociente de 0,67
frente al mínimo de dos tercios.

Ese ajuste pasa la regla de historia, pero la regla cuenta juicios, no a qué proyecto se
demanda. Con él, el juicio real contra Google Cerrillos (2020) pasa a ser un evento de 8%
(83% con el peso central): ese juicio es unas 10 veces más probable con el peso central que con
la mitad, aunque la regla de historia no lo incorpora.

Límites de este análisis:
- Con 100 futuros por ajuste hay ruido de muestreo: el error estándar de una probabilidad es de
  hasta 5 puntos (±10 con 95% de confianza); en Cerrillos, de unos 4.
- Uno a la vez no ve interacciones entre parámetros; solo el sorteo conjunto las mezcla.
- `outages_per_year` cambia cuántos números aleatorios usa el flujo del entorno, así que en sus
  dos ajustes las horas de apagón no conservan los números aleatorios comunes. Solo afecta las
  horas de diésel y el NOx, que no entran en ningún hallazgo.
- Quedan supuestos de comportamiento escritos como números en el código, fuera de este
  análisis, entre otros: los pesos con que un proyecto elige comuna, los componentes de las
  molestias, las distancias de 0,7 y 1,5 km de los núcleos de cercanía, la diversidad de los
  hogares (sorteada una vez al cargar el modelo), cuánto sube la desconfianza con un juicio, una
  anulación o una aprobación por SEIA (0,03), cuánto pesa el agua percibida según haya acuífero
  (×1,5 o ×0,5), la opinión inicial (0,12), el tope de 90% a la probabilidad de juicio, la
  probabilidad de rediseñar con aire tras una anulación (70%), la de desistir tras 36 meses de
  espera y las probabilidades de decisión de la evaluación por zona.
- La regla de historia cuenta juicios, no a qué proyectos se demanda (ver AWS Huechuraba en
  la sección 1).

## Cómo reproducir

Tiempos medidos en un computador de 10 núcleos.

```bash
uv sync --frozen
uv run pytest -q                               # 48 tests, ~9 s
uv run python -m dcsim.validation              # tabla de la sección 1
uv run python -m dcsim.precompute              # portada y "como hoy" de "Tu regla", ~40 s
uv run python -m dcsim.explore                 # 15.080 simulaciones, ~3 min
uv run python -m dcsim.findings                # sección 2, escribe cache/findings.json
uv run python -m dcsim.sensitivity             # sección 4, 76.500 simulaciones, ~16 min
uv run uvicorn dcsim.server:app --port 8000    # interfaz en http://localhost:8000
```

Van versionados `cache/findings.json`, `cache/sensitivity.json` y los ensambles de la portada,
así el servidor parte sin simular. `precompute` también deja, versionado, "como hoy" con 60 y
100 futuros: las semillas con que se compara "Tu regla" (60 en Render, 100 en local). Todos
llevan la huella del código: si cambias `model.py`, `catalog.py`, `params.py`, `policy.py` o
`montecarlo.py`, corre `precompute`, `explore`, `findings` y `sensitivity`, en ese orden (dos
tests fallan si `findings.json` o `sensitivity.json` quedaron desactualizados).
`cache/explore_raw.json` (~32 MB) no se versiona: solo lo rehace `explore`, y `findings` lo
necesita.
