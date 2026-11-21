# Hallazgos: efecto acumulado de data centers en Chile

Simulador híbrido (agentes + stocks y flujos) de cómo los data centers que llegan a Chile,
sobre todo al corredor norte de la Región Metropolitana, afectan agua, red eléctrica,
conflicto y beneficios en cada comuna entre 2012 y 2035. Código en `dcsim/`, interfaz en `web/`.

Todos los números de este documento salen del código de este branch:

| Qué | Cómo se calcula | Simulaciones |
|---|---|---|
| Validación | `dcsim/validation.py`, modo `free` (el modelo genera la historia 2012–2026 sin conocerla) | 200 |
| Hallazgos | `dcsim/explore.py` + `dcsim/findings.py`, modo `anchored` (historia real hasta nov-2026, luego proyección) | 15.080 (185 configuraciones) |
| Hipótesis del informe | `dcsim/insights.py`, escenarios predefinidos de `dcsim/policy.py` | 200 por escenario |

Las comparaciones usan números aleatorios comunes: cada configuración corre con las mismas
semillas y los proyectos conocidos sortean de un flujo propio, así la diferencia entre dos
configuraciones se debe a la regla que cambia (también al cambiar la demanda: los proyectos
nuevos de una demanda baja son un subconjunto de los de una alta). Los valores son medianas;
los porcentajes "de los futuros" son la fracción de pares de réplicas donde se cumple la
afirmación. En cada futuro se sortean 13 de los 41 supuestos, entre ellos el efecto de la
evaluación conjunta y de la transparencia, que no tienen dato chileno.

## 1. El modelo reproduce lo observado (14/14 chequeos)

Sin ver la historia, el modelo genera 2012–2026 a partir de los proyectos reales (tamaño,
lugar, enfriamiento y fecha de anuncio) y se compara con datos observados. Banda = percentiles
5–95. 7 chequeos son validación (el modelo no se ajustó a ese dato) y 7 son calibración.

| Chequeo | Tipo | Observado | Modelo (mediana [banda]) |
|---|---|---|---|
| Consumo eléctrico DC de la RM, fin 2021 (MW) | validación | 90 | 104 [86–132] |
| Consumo eléctrico DC de la RM, fin 2025 (MW) | validación | 260 | 254 [185–338] |
| Consumo eléctrico DC de Chile, 2025 (MW) | validación | 325 | 285 [217–376] |
| Capacidad instalada en Santiago, mediados 2026 (MW TI) | calibración | 311 | 326 [251–401] |
| Data centers operando, mediados 2026 | calibración | 36–39 | 37 [35–39] |
| Agua de Google Quilicura, 2024 (ML) | calibración | 458 | 484 [407–565] |
| Potencia media de Google Quilicura, 2024 (MW) | validación | 30 | 31,8 [27,4–35,3] |
| Parte del consumo de Quilicura que usan los DC (%) | calibración | 62 | 60 [53–64] |
| MW esperando conexión a la red, 2026 | calibración | 1.420 | 1.420 [1.192–1.447] |
| Proyectos en lista de espera, 2026 | calibración | 6 | 6 [6–7] |
| Litigios ambientales contra DC, 2012–2026 | calibración | 2 | 2 [1–4] |
| Parte del consumo eléctrico nacional (%) | validación | 2–3 | 2,5 [1,9–3,2] |
| Comunas con oposición organizada | validación | Cerrillos, Quilicura, Huechuraba, Lampa | las mismas 4 en el top 4 |
| Estado de cada proyecto conocido a nov-2026 | validación | 54 proyectos | 96% acierta (92% de los con nombre) |

Límites de estos chequeos:
- Los 1.420 MW en espera se cumplen casi por construcción: la capacidad libre de cada nodo se
  ajustó a ese dato y dos proyectos supuestos completan los 6 proyectos del CEN.
- El estado de cada proyecto se compara con una regla trivial (lista del CEN espera; anunciado
  hace 3 o más años opera), que acierta 91%. El chequeo pasa solo si el modelo la supera.
- Las comunas con oposición no son una prueba ciega: los barrios sintéticos se ubicaron donde
  hay viviendas junto a sitios conocidos (Valle Grande, La Pincoya, Lonquén).

## 2. Hallazgos (15.080 simulaciones)

### No hay que elegir: 3 reglas mejoran a la vez agua, conflicto, juicios e inversión en 84% de los futuros
Enfriamiento por aire + fondo comunitario + incentivo al norte, frente a las reglas de hoy
(2035, 200 futuros, los mismos de la portada): 13% más data centers operando, 12% más
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
(169 L/s de un acuífero en zona de prohibición). Con aire, el proyecto estaría operando
desde 2022 en 93% de los futuros. En la realidad hubo juicio, el tribunal anuló el permiso
en 2024 y Google rediseñó con aire en 2026. La elección de enfriamiento pesa más que el
tamaño del proyecto.

### Dónde importa más que cuánto: alejar un solo proyecto de las casas baja 60% el conflicto de toda Lampa
Campo de Datos Lampa (100 MW) está a menos de 50 m de Valle Grande. El mismo proyecto en la
periferia de la comuna baja los hogares movilizados de 26% a 11% y los hogares a menos de
500 m de un DC grande de 3.968 a 1.701 (2035). Se cumple en 91% de los futuros.

### Información vs plata: publicar el uso real de agua baja el conflicto tanto como pagar US$38 millones al año
Transparentar el consumo: −30% hogares movilizados. Fondo comunitario de US$20.000 por MW al
año (≈ US$38 millones en 2035): −31%. Google Quilicura usa solo el 29% de su derecho de agua,
pero los vecinos temen el 100%.
*Supuesto:* depende de cuánto recupera la confianza la información (entre 0,05 y 0,25,
sorteado en cada futuro).

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

## Cómo reproducir

```bash
uv sync
uv run pytest                                  # 19 tests
uv run python -m dcsim.precompute              # ensambles de la portada (cache/, ~40 s)
uv run python -m dcsim.validation              # tabla de la sección 1
uv run python -m dcsim.explore                 # ~15.000 simulaciones, ~3 min
uv run python -m dcsim.findings                # sección 2, escribe cache/findings.json
uv run uvicorn dcsim.server:app --port 8000    # interfaz en http://localhost:8000
```

`cache/findings.json` y los ensambles de la portada van versionados, así el servidor parte sin
simular. Llevan la huella del código: si cambias el modelo, vuelve a correr `precompute`,
`explore` y `findings` (un test falla si `findings.json` quedó desactualizado). El resto de
`cache/` (`explore_raw.json`, ~32 MB) se regenera solo.
