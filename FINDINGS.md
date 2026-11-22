# Hallazgos: efecto acumulado de data centers en Chile

Simulador híbrido (agentes + stocks y flujos) de cómo los data centers que llegan a Chile,
sobre todo al corredor norte de la Región Metropolitana, afectan agua, red eléctrica,
conflicto y beneficios en cada comuna entre 2012 y 2035. Código en `dcsim/`, interfaz en `web/`.
La página parte por una simulación de evaluación conjunta por comuna: simula juntos todos los
data centers de una comuna, con lo que cada uno declaró al SEA (sección 5).

Todos los números de este documento salen del código de este repositorio:

| Qué | Cómo se calcula | Simulaciones |
|---|---|---|
| Validación | `dcsim/validation.py`, modo `free` (el modelo genera la historia 2012–2026 sin conocerla) | 200 |
| Hallazgos | `dcsim/explore.py` + `dcsim/findings.py`, modo `anchored` (historia real hasta nov-2026, luego proyección); la historia alternativa de Cerrillos usa el modo `free` | 15.080 (185 configuraciones) y los 200 futuros por regla de la portada |
| Hipótesis del informe | `dcsim/insights.py`, escenarios predefinidos de `dcsim/policy.py` | 200 por escenario |
| Qué tan firmes son | `dcsim/sensitivity.py`: cada parámetro fijo en sus extremos y todos sorteados juntos (sección 4) | 76.500 |
| Simulación por comuna | `POST /api/calc` (`dcsim/server.py`), modo `anchored`, enfriamiento por proyecto desde 2027 (sección 5) | 60 por cálculo en el sitio (100 en local) |

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
| Consumo eléctrico DC de la RM, fin 2021 (MW) | validación | 90 | 105 [85–138] |
| Consumo eléctrico DC de la RM, fin 2025 (MW) | validación | 260 | 252 [184–345] |
| Consumo eléctrico DC de Chile, 2025 (MW) | validación | 325 | 283 [211–382] |
| Capacidad instalada en Santiago, mediados 2026 (MW TI) | calibración | 311 | 317 [249–393] |
| Data centers operando, mediados 2026 | calibración | 36–39 | 37 [35–39] |
| Agua de Google Quilicura, 2024 (ML) | calibración | 458 | 486 [394–567] |
| Potencia media de Google Quilicura, 2024 (MW) | calibración | 30 | 31,8 [27,4–35,4] |
| Parte del consumo de Quilicura que usan los DC (%) | calibración | 62 | 60 [53–64] |
| MW esperando conexión a la red, 2026 | calibración | 1.420 | 1.445 [1.264–1.479] |
| Proyectos en lista de espera, 2026 | calibración | 6 | 7 [6–9] |
| Litigios ambientales contra DC, 2012–2026 | calibración | 2 | 2 [0–5] |
| Parte del consumo eléctrico nacional (%) | validación | 2–3 | 2,4 [1,9–3,3] |
| Comunas con oposición organizada | validación | Cerrillos, Quilicura, Huechuraba, Lampa | las mismas 4 en el top 4 |
| Estado de cada proyecto conocido a nov-2026 | validación | 55 proyectos | acierta 93% (85% en los 26 con nombre); la regla trivial, 91% (85%) |

Límites de estos chequeos:
- Los 1.420 MW en espera se cumplen casi por construcción: la capacidad libre de cada nodo se
  ajustó a ese dato y dos proyectos supuestos completan los 6 proyectos del CEN.
- El estado de cada proyecto se compara con una regla trivial (lista del CEN espera; anunciado
  hace 3 o más años opera). El chequeo pasa solo si el modelo la supera, y la supera por poco:
  el modelo acierta 51 de los 55 proyectos (93%) y la regla 50 (91%). La diferencia es un solo
  proyecto, sin nombre público. En los 26 proyectos con nombre público, que son la prueba más
  limpia, empatan: 22 de 26 (85%) cada uno. El modelo acierta Scala Lampa y ODATA Lampa (en
  construcción), que la regla falla, y falla Grenergy Tiltil y Ascenty Data Hall Quilicura (en
  trámite), que la regla acierta; los dos fallan AWS Huechuraba y Google Cerrillos. Este
  chequeo no muestra que el modelo prediga el estado de un proyecto mejor que una regla simple.
  Los otros 29 son supuestos que cuadran el inventario y la lista del CEN.
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

### No hay que elegir: 3 reglas mejoran a la vez agua, conflicto, juicios e inversión en 82% de los futuros
Enfriamiento por aire + fondo comunitario + incentivo al norte, frente a las reglas de hoy
(2035, 200 futuros, los mismos de la portada): 13% más MW de data centers operando, 14% más
inversión, 34% menos inversión perdida, 49% menos hogares movilizados, 33% menos juicios y
53% menos agua.
*La cuenta de la luz* no sube más: 1,8% en vez de 2,1%, porque parte de la demanda se va a
Antofagasta, donde sobra energía solar. Supone que esa demanda no presiona la tarifa; el rango
es amplio (en 9 de cada 10 futuros, entre +0,2% y +4,3%).

### El cuello de botella no es el permiso: permisos 4 veces más rápidos dan solo 0,3% más MW en Santiago al 2030
Con permisos 75% más cortos, la RM pasa de 818 a 820 MW en 2030 y el plazo medio entre
anuncio y operación baja apenas 3,4 meses. Los proyectos aprobados igual esperan conexión
eléctrica. Relevante para la Mesa Permanente (nov-2026), cuyo objetivo es acortar permisos.

### Punto de quiebre: el doble de proyectos conecta solo 19% más, pero los juicios se multiplican por 2,3
Con 10 proyectos nuevos al año en vez de 5, la lista de espera crece 3,1 veces y los hogares
movilizados pasan de 18% a 36%. Con 4 veces más proyectos: 29% más MW y 8 veces más juicios.
La red no crece al ritmo de los anuncios: cada proyecto extra suma espera, no MW, y los
proyectos que esperan red generan rechazo sin dejar beneficios.

### Historia alternativa: con aire en Cerrillos, la probabilidad de juicio baja de 78% a 4%
Se vuelve a correr 2012–2026 cambiando solo la decisión de enfriamiento de Google Cerrillos.
El diseño de 2020 usaba torres evaporativas y declaraba una extracción continua de 169 L/s de
un acuífero en zona de prohibición. Con aire, a fines de 2023 el proyecto estaría operando en
90% de los futuros. En la realidad hubo juicio: Google pidió pasar a aire en feb-2022 (el SEA
respondió en jun-2022 que no requería evaluación), el tribunal anuló parcialmente el permiso
en feb-2024, Google renunció a él y anunció un rediseño por aire en sep-2024, y el SEA dejó
el nuevo diseño sin evaluación ambiental en oct-2026 (sección 5). La elección de enfriamiento
pesa más que el tamaño del proyecto.
*Supuestos clave:* usar agua de un acuífero en zona de prohibición da fundamento legal a un
juicio (`lit_w_water`) y aumenta el rechazo de los vecinos (`op_w_water`); la sección 4
muestra que el hallazgo no se sostiene si el peso del agua en la opinión baja a la mitad.

### Dónde importa más que cuánto: alejar un solo proyecto de las casas baja 56% el conflicto de toda Lampa
Campo de Datos Lampa (100 MW) está a menos de 50 m de Valle Grande. El mismo proyecto en la
periferia de la comuna baja los hogares movilizados de 28% a 12% y los hogares a menos de
500 m de un DC grande de 3.968 a 1.701 (2035). Se cumple en 92% de los futuros.

### Información vs plata: publicar el uso real de agua baja el conflicto casi tanto como pagar US$38 millones al año
Transparentar el consumo: −27% hogares movilizados. Fondo comunitario de US$20.000 por MW al
año (≈ US$38 millones en 2035): −30% (2035, 200 futuros). Google Quilicura usa solo el 29% de
su derecho de agua, pero los vecinos temen el 100%.
*Supuesto:* depende de cuánto recupera la confianza la información (entre 0,05 y 0,25,
sorteado en cada futuro) y de cuánto pesa el agua en la opinión. Si ese peso baja a la mitad,
queda en el límite: la transparencia logra justo dos tercios de la baja del fondo (sección 4).

### No hay destino escrito: 6 comunas pueden terminar como la más afectada en 2035
En 200 futuros con las mismas reglas, la comuna con más hogares movilizados cambia según el
orden en que llegan los proyectos: Quilicura (29%), Cerrillos (26%), Tiltil (15%), Padre
Hurtado (9%); 6 comunas lo son en al menos 5% de los futuros. La "comuna de sacrificio" se
decide en el camino, no en el mapa, y por eso una evaluación proyecto por proyecto no puede
anticiparla.

## 3. Hipótesis del informe

| Hipótesis | Veredicto | Evidencia (2035 salvo que se indique) |
|---|---|---|
| Exigir enfriamiento por aire reduce el agua, pero satura antes la red (S1) | Se confirma | Agua de los DC de la RM −51% (54 → 26 L/s); consumo en el mes peak +3,3% y lista de espera +20%. El agua ahorrada se paga con más electricidad en verano. |
| Evaluar en conjunto acorta los plazos porque reduce los litigios (S1) | Parcialmente | Litigios −33% y hogares movilizados −37%, pero el plazo anuncio → operación sube 1,9 meses (45,7 → 47,7): las ventanas de evaluación y las reubicaciones se comen lo ahorrado en tribunales. Parte del efecto en litigios es supuesto (factor 0,2–0,5, sorteado). |
| Acelerar permisos no conecta más DC si la red está saturada (A3) | Se confirma | Permisos al doble de rápido: +0,1% MW en la RM en 2030 (819 → 820) y el plazo baja solo 2,3 meses. |
| Transparentar el agua reduce más el conflicto que compensar (S2) | Parcialmente | Solo transparencia: −27% hogares movilizados; solo fondo de US$20.000/MW/año: −30%. Magnitudes parecidas; juntas suman. |
| Con el umbral de 1.000 t casi ningún DC nuevo pasa por SEIA (S7, A1) | Se confirma | Desde 2027, con 1.000 t solo 2% de los proyectos nuevos entra al SEIA; con 80 t, 75%. Supone que los proyectos declaran diésel justo bajo el límite, como los 7 casos reales tras el DS 17 (511 a 990 t). |
| Un incentivo al norte descomprime la RM (A3, S8) | Se confirma | En 2030 Antofagasta pasa de 322 a 549 MW, los MW esperando red −52% y los MW operando en la RM −1,4%. |

Los barridos de una palanca (permisos, demanda) usan 120 futuros y los escenarios 200, por eso
la RM de 2030 "como hoy" aparece como 818 MW en la sección 2 y 819 MW en esta tabla.

## 4. Qué tan firmes son los hallazgos

De los 53 parámetros, 13 se sortean en cada futuro. Los otros 40 quedan en su valor central;
`dcsim/params.py` marca 26 como supuestos, 8 como datos y 6 como calibrados.
Se prueban los 6 hallazgos que comparan reglas o historias; el séptimo, «No hay destino
escrito», describe cuánto varían los futuros y no tiene un criterio de sí o no.
`dcsim/sensitivity.py` los mueve de dos formas. Uno a la vez: cada uno va al extremo bajo y
luego al alto de su rango (80 ajustes de 100 futuros), con las mismas semillas y los mismos 13
sorteos de una corrida normal. Todos juntos: 400 futuros en que, además de los 13 de siempre,
se sortean los 40 dentro de su rango. En cada ajuste se rehace la cuenta de cada hallazgo como
en `dcsim/findings.py` y se aplica el criterio de la tabla. Son 76.500 simulaciones (890 s en
10 núcleos); el resultado queda en `cache/sensitivity.json`.

Un extremo puede dejar al modelo lejos de lo observado. Por eso cada ajuste también corre
2012–2026 en modo libre y revisa que siga reproduciendo la historia: mediana de juicios a fines
de 2026 entre 1 y 4 (hubo 2) y, a menos de 25% del dato, el consumo de los data centers de la
RM a fines de 2025 (260 MW), los MW esperando red en 2026 (1.420) y la capacidad instalada en
Santiago a mediados de 2026 (311 MW). Los 80 ajustes pasan esa regla.

El valor central se calcula con 100 futuros, así que puede diferir un poco de la sección 2.

| Hallazgo | Qué se mide (se mantiene si…) | Supuestos centrales | Uno a la vez: rango | Se mantiene | Todos juntos (400 futuros) |
|---|---|---|---|---|---|
| No hay que elegir | Futuros en que aire + fondo + norte es igual o mejor en las seis cifras (al menos 50%) | 82% | 72% a 87% | 80 de 80 | 77% |
| El cuello de botella no es el permiso | Cambio de los MW en la RM en 2030 con permisos 4 veces más rápidos (menos de +5%) | +0,25% | 0% a +2,11% | 80 de 80 | +0,75% |
| Punto de quiebre | Cuántas veces más crecen los juicios que los MW operando con el doble de proyectos (más de 1) | 2,06 | 1,75 a 2,17 | 80 de 80 | 1,95 |
| Historia alternativa (Cerrillos) | Probabilidad de juicio con agua → con aire (baja al menos 25 puntos y queda en la mitad o menos) | 74% → 5% | con agua 15% a 88%; con aire 4% a 12% | 79 de 80 | 69,8% → 4,2% |
| Dónde importa más que cuánto | Baja del conflicto de Lampa en 2035 al alejar Campo de Datos Lampa (25% o más) | 54,2% | 36,5% a 69,7% | 80 de 80 | 55,8% |
| Información vs plata | Cambio del conflicto de la RM en 2035 con transparencia y con fondo (las dos bajan y la transparencia logra al menos dos tercios de la baja del fondo) | −25,3% y −27,9% (cociente 0,91) | cociente 0,67 a 1,18 | 80 de 80 | −28,4% y −27,3% (1,04) |

Con todos los parámetros sorteados juntos, los seis hallazgos se mantienen. En ese sorteo, 188
de los 400 futuros reproducen la historia cada uno por su cuenta (con los supuestos centrales,
61 de 100); con solo esos 188, los seis también se mantienen (estas cifras las imprime
`uv run python -m dcsim.sensitivity` al terminar).

7 de los 40 parámetros no mueven ninguna de estas seis cifras: el consumo y el crecimiento
eléctrico del país, el costo de red, la recarga del acuífero, el NOx, las horas de prueba del
diésel y los apagones. Mueven otras (la cuenta de la luz, el acuífero, el diésel), y sus 14
ajustes se mantienen por construcción.

**Lo que no se sostiene.** La historia alternativa de Cerrillos falla en 1 de los 80 ajustes:
si el peso del agua que los vecinos ven usar en su opinión (`op_w_water`) baja a la mitad
(0,6 en vez de 1,2), la probabilidad de juicio con agua cae de 74% a 15% y con aire queda en 5%.
Con ese peso, el juicio es poco probable aun con agua, y enfriar con aire lo baja solo 10
puntos, menos de los 25 que pide el criterio. El ajuste que le sigue en debilidad, un rechazo
de partida más bajo (`op_intercept` = −2,5), deja 45% con agua y 5% con aire, y cumple. En el
mismo ajuste de `op_w_water`, información vs plata queda en el límite: la transparencia baja el
conflicto 17,8% y el fondo 26,6%, un cociente de 0,67 frente al mínimo de dos tercios.

Ese ajuste pasa la regla de historia, pero la regla cuenta juicios, no a qué proyecto se
demanda. Con él, el juicio real contra Google Cerrillos (2020) pasa a ser un evento de 15%
(74% con el peso central): ese juicio es unas 5 veces más probable con el peso central que con
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

## 5. La simulación por comuna y lo declarado al SEA

Hoy cada data center se evalúa solo. Esta parte hace la pregunta que esa evaluación no hace,
como un "qué pasaría si" simulado y no como una suma de planilla: con todo lo que opera, se construye, está en trámite o espera red en una comuna,
¿alcanzan el agua y la red? La página la hace para Quilicura, con un solo interruptor: los
proyectos que aún no operan enfrían con aire, como lo declararon, o con agua desde 2027. Los dos
escenarios están precalculados (`python -m dcsim.precompute`). La API (`POST /api/calc`) hace
lo mismo para cualquier comuna y cualquier proyecto que aún no opera. Está pensada
para la evaluación ambiental, que es donde hoy se discute cada proyecto:

- **SEA y servicios:** ¿alcanzan el agua y la red con todo lo ya aprobado?
- **Municipio y vecinos:** ¿cuánto es todo junto, no solo este proyecto?
- **Empresa:** ¿enfriar con agua o con aire?

Cada escenario corre 60 futuros en el sitio (100 en local), los mismos de "Tu regla", en modo
anclado: la historia real hasta nov-2026 y, desde 2027, el enfriamiento elegido. Se compara
futuro por futuro con lo declarado. Las cifras incluyen los proyectos nuevos que llegan a la
comuna en cada futuro, no solo los conocidos. El código está en `POST /api/calc`
(`dcsim/server.py`), `web/calc.js` y `dcsim/sea.py`.

### Quilicura, todo sumado

En 2035, con 60 futuros. Entre paréntesis, el rango donde cae el 90% de los futuros. Los 4
proyectos de Quilicura que aún no operan son Microsoft SCL03 (19,2 MW), Cirion Quilicura nuevo
(12 MW), Ascenty Santiago 3 (16 MW) y Ascenty Data Hall Quilicura (36 MW). Todos declararon
enfriamiento por aire o en circuito cerrado (Microsoft SCL03 usa agua solo unas 600 horas al
año).

| Cifra | Como se declaró | Si esos 4 enfrían con agua desde 2027 |
|---|---|---|
| Agua de sus data centers | 17,9 L/s (15,5–20,6): el agua de ~3.100 hogares, 4,4% de lo que usan sus hogares | 42,2 L/s (28,0–60,8): 2,4 veces más, el agua de ~7.300 hogares (10,4%). Más alta en 60 de 60 futuros |
| Electricidad de sus data centers | 188 MW (160–220): 76,5% de la electricidad de la comuna | 170 MW: 18 MW menos. Más baja en 59 de 60 |
| Vecinos movilizados | 46% (36–68%) | 64% (54–88%). Más alto en 59 de 60 |
| Futuros en que cada uno opera en 2035 | Microsoft SCL03 93%, Cirion nuevo 95%, Ascenty Santiago 3 92%, Data Hall 98% | 87%, 80%, 80% y 85%: con agua hay más oposición, juicios, anulaciones y proyectos que desisten o siguen esperando red |

Esa última fila es lo que una suma no puede dar: no sale de multiplicar MW por un factor, sino
de que en cada futuro los proyectos compiten por la misma red y la oposición los lleva a
tribunales. Por eso el cambio de electricidad (−18 MW) es mayor que el puro efecto del
enfriamiento: parte viene de proyectos que no llegan a operar.

Con lo declarado, la red libre del nodo Norte, que Quilicura comparte con Lampa, Colina y
Huechuraba, queda en 12 MW (1–48) a fines de 2035 (23 MW en 2030). En la mediana, ningún
proyecto de Quilicura espera red (0 MW).

Enfriar con agua ahorra 18 MW, pero multiplica el agua por 2,4 y sube los vecinos movilizados.
Esa suma no aparece en ninguna evaluación de un solo proyecto.

En Cerrillos, pasar Google Cerrillos a agua desde 2027 da un resultado ruidoso: los juicios y
las anulaciones a menudo lo devuelven a aire. La mediana del agua queda en 3,2 L/s, con un
rango de 0 a 42,7 L/s, y los vecinos movilizados en 54% frente a 36% con lo declarado.

### Lo que cambió en el modelo con lo declarado al SEA

| Proyecto | Antes | Ahora | Fuente |
|---|---|---|---|
| Microsoft SCL03 (Quilicura) | 24,9 MW de servidores | 19,2 MW; los 24,9 MW incluían 5,7 MW auxiliares | RCA 202313001133 (abr-2023) |
| Ascenty Data Hall Quilicura | no estaba | 36 MW, chillers en circuito cerrado, 765 t de diésel, en trámite | RCA 202513001408 (nov-2025), condicionada a acreditar la factibilidad eléctrica |
| Cirion Quilicura (nuevo) | diésel estimado por MW | 340 t de diésel; enfriamiento DX, sin agua | RCA 20241300153 (feb-2024) |
| AWS Padre Hurtado | diésel estimado por MW | 180 t de diésel | RCA 20241300136 (ene-2024) |
| DC Alto Jahuel (Buin) | diésel estimado por MW | 990 t de diésel, justo bajo el umbral de 1.000 t | PERTI-2026-5962 (jul-2026) |
| Pertinencia Buin | sin operador | Es otro proyecto, Alto Jahuel Campus Sur (Grenergy); tamaño y diésel siguen supuestos | PERTI-2026-7066 (may-2026, prensa) |
| Google Cerrillos | "subestación de 120 MW"; "Google desiste (jul-2024)" | Los 120 MW son generadores de respaldo, no servidores (se mantienen 80 MW de servidores, supuestos); historia según el SEA y el Tribunal (abajo) | RCA 127/2020, SEA y 2° Tribunal Ambiental |

Solo se muestra, sin cambiar el modelo: `dcsim/sea.py` guarda lo declarado por 23 proyectos
(agua promedio o máxima, derechos de agua, MW, enfriamiento, diésel), con enlace al documento y
su confianza (12 alta: documento del SEA o resolución oficial; 11 media: prensa que cita el
expediente). La página lo muestra junto a lo que usa el modelo. Donde difieren, el modelo
mantiene su valor y lo dice. Por ejemplo, ODATA San Bernardo tiene 40,6 MW según prensa y el
modelo usa 18 MW, porque el inventario está calibrado con los 311 MW instalados. Microsoft SCL03
usa agua unas 600 horas al año y el modelo lo trata como aire. AWS Padre Hurtado fue aprobado
en enero de 2024 y el modelo lo deja como pendiente.

### Cerrillos: qué dicen los documentos

- **2020.** El SEA aprueba el diseño con torres evaporativas (RCA 127/2020). Declaraba una
  extracción continua de 169 L/s (unos 14,6 millones de litros al día) de un acuífero en zona
  de prohibición, con derechos de agua por 228 L/s. El proyecto llega al 2° Tribunal Ambiental
  (R-270/271-2020).
- **Feb-2022.** Google consulta al SEA para pasar a chillers por aire. En jun-2022 el SEA
  responde que el cambio no requiere evaluación ambiental.
- **Feb-2024.** El 2° Tribunal Ambiental anula parcialmente el permiso.
- **Sep-2024.** Google renuncia al permiso y anuncia un rediseño por aire.
- **Jul-2026.** Reingresa como consulta de pertinencia, con 63 chillers por aire y sin agua.
- **Oct-2026.** El SEA RM resuelve que no requiere evaluación ambiental.

Los "120 MW" que se citan son 120,25 MW de generadores de respaldo (44 grupos), no de
servidores. Declara 696 t de diésel (871,8 t en el diseño de 2020). Los "7,6 millones de litros
al día" que circulan no aparecen en los documentos de Cerrillos: coinciden con el diseño de
Google en Canelones, Uruguay (confianza media).

### Límites de la simulación por comuna

- Usa 60 futuros: los rangos del 90% son aproximados. "En 59 de 60" cuenta pares de futuros
  con las mismas semillas.
- El cambio de enfriamiento rige desde 2027. La historia documentada hasta nov-2026 queda como
  fue, también la de Cerrillos. Después de su último evento documentado, una nueva anulación
  sigue la regla de todos (rediseñar con aire o desistir): por eso Cerrillos con agua es ruidoso.
- Lo declarado al SEA suele ser el máximo de diseño, no el promedio: derechos de agua, caudales
  máximos, potencia de la subestación o de los generadores. Google Quilicura usa cerca del 29%
  de su derecho de agua.
- Los proyectos sin presentación encontrada quedan como supuestos marcados: el tamaño de Alto
  Jahuel Campus Sur, Ascenty Santiago 3 (sin expediente encontrado) y los 29 sin nombre público.
- La red libre es la del nodo, que comparten varias comunas.

## Cómo reproducir

Tiempos medidos en un computador de 10 núcleos.

```bash
uv sync --frozen
uv run pytest -q                               # 43 tests, ~9 s
uv run python -m dcsim.validation              # tabla de la sección 1
uv run python -m dcsim.precompute              # portada y "como hoy" de "Tu regla", ~40 s
uv run python -m dcsim.explore                 # 15.080 simulaciones, ~3 min
uv run python -m dcsim.findings                # sección 2, escribe cache/findings.json
uv run python -m dcsim.sensitivity             # sección 4, 76.500 simulaciones, ~15 min
uv run uvicorn dcsim.server:app --port 8000    # interfaz en http://localhost:8000
```

La sección 3 es `GET /api/insights` (`hypotheses` en `dcsim/insights.py`). Para la sección 5,
con los mismos 60 futuros del sitio:

```bash
DCSIM_N_CUSTOM=60 uv run uvicorn dcsim.server:app --port 8000
curl -s -X POST localhost:8000/api/calc -H 'content-type: application/json' \
  -d '{"cooling": {"microsoft_scl03": "evaporativo", "cirion_quilicura_2": "evaporativo",
       "ascenty_3": "evaporativo", "ascenty_data_hall": "evaporativo"}}'
```

Van versionados `cache/findings.json`, `cache/sensitivity.json` y los ensambles de la portada,
así el servidor parte sin simular. `precompute` también deja, versionado, "como hoy" con 60 y
100 futuros: las semillas con que se compara "Tu regla" (60 en Render, 100 en local). Todos
llevan la huella del código: si cambias `model.py`, `catalog.py`, `params.py`, `policy.py` o
`montecarlo.py`, corre `precompute`, `explore`, `findings` y `sensitivity`, en ese orden (dos
tests fallan si `findings.json` o `sensitivity.json` quedaron desactualizados).
`cache/explore_raw.json` (~32 MB) no se versiona: solo lo rehace `explore`, y `findings` lo
necesita.
