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
semillas, así la diferencia entre dos configuraciones se debe a la regla que cambia. Los
valores son medianas; los porcentajes "de los futuros" son la fracción de pares de réplicas
donde se cumple la afirmación.

## 1. El modelo reproduce lo observado (14/14 chequeos)

Sin ver la historia, el modelo genera 2012–2026 a partir de los anuncios reales y se compara
con datos observados. Banda = percentiles 5–95.

| Chequeo | Tipo | Observado | Modelo (mediana [banda]) |
|---|---|---|---|
| Consumo eléctrico DC de la RM, fin 2021 (MW) | validación | 90 | 105 [85–133] |
| Consumo eléctrico DC de la RM, fin 2025 (MW) | validación | 260 | 252 [191–335] |
| Consumo eléctrico DC de Chile, 2025 (MW) | validación | 325 | 285 [217–368] |
| Capacidad instalada en Santiago, mediados 2026 (MW TI) | calibración | 311 | 321 [237–397] |
| Data centers operando, mediados 2026 | calibración | 36–39 | 37 [36–39] |
| Agua de Google Quilicura, 2024 (ML) | calibración | 458 | 488 [419–564] |
| Potencia media de Google Quilicura, 2024 (MW) | validación | 30 | 31,9 [28,5–35,3] |
| Parte del consumo de Quilicura que usan los DC (%) | calibración | 62 | 59 [53–65] |
| MW esperando conexión a la red, 2026 | calibración | 1.420 | 1.420 [1.207–1.447] |
| Proyectos en lista de espera, 2026 | calibración | 6 | 6 [6–8] |
| Litigios ambientales contra DC, 2012–2026 | calibración | 2 | 2 [1–4] |
| Parte del consumo eléctrico nacional (%) | validación | 2–3 | 2,5 [1,8–3,3] |
| Comunas con oposición organizada | validación | Cerrillos, Quilicura, Huechuraba, Lampa | las mismas 4 en el top 4 |
| Estado de cada proyecto conocido a nov-2026 | validación | 54 proyectos | 94% acierta (88% de los con nombre) |

## 2. Hallazgos (15.080 simulaciones)

### No hay que elegir: 3 reglas mejoran las 6 métricas a la vez en 92% de los futuros
Enfriamiento por aire + fondo comunitario + incentivo al norte, frente a las reglas de hoy
(2035): 17% más data centers operando, 14% más inversión, 32% menos inversión perdida, 53%
menos hogares movilizados, 33% menos juicios y 56% menos agua.
*Costo:* la cuenta de la luz sube 3,7% en vez de 3,1%, porque hay más data centers consumiendo.

### El cuello de botella no es el permiso: permisos 4 veces más rápidos dan solo 2% más MW en Santiago al 2030
Con permisos 75% más cortos, la RM pasa de 793 a 808 MW en 2030 y el plazo medio entre
anuncio y operación baja apenas 3,7 meses. Los proyectos aprobados igual esperan conexión
eléctrica. Relevante para la Mesa Permanente (nov-2026), cuyo objetivo es acortar permisos.

### Punto de quiebre: el doble de proyectos conecta solo 19% más, pero los juicios se multiplican por 2,6
Con 10 proyectos nuevos al año en vez de 5, la lista de espera crece 2,8 veces y los hogares
movilizados pasan de 18% a 35%. Con 4 veces más proyectos: 31% más MW y 8 veces más juicios.
La red no crece al ritmo de los anuncios: cada proyecto extra suma espera, no MW, y los
proyectos que esperan red generan rechazo sin dejar beneficios.

### Historia alternativa: con aire en Cerrillos, la probabilidad de juicio baja de 79% a 3%
Se vuelve a correr 2012–2026 cambiando solo la decisión de enfriamiento de Google Cerrillos
(169 L/s de un acuífero en zona de prohibición). Con aire, el proyecto estaría operando
desde 2022 en 92% de los futuros. En la realidad hubo juicio, el tribunal anuló el permiso
en 2024 y Google rediseñó con aire en 2026. La elección de enfriamiento pesa más que el
tamaño del proyecto.

### Dónde importa más que cuánto: alejar un solo proyecto de las casas baja 56% el conflicto de toda Lampa
Campo de Datos Lampa (100 MW) está a menos de 50 m de Valle Grande. El mismo proyecto en la
periferia de la comuna baja los hogares movilizados de 25% a 11% y los hogares a menos de
500 m de un DC grande de 3.968 a 1.701 (2035). Se cumple en 92% de los futuros.

### Información vs plata: publicar el uso real de agua baja el conflicto tanto como pagar US$38 millones al año
Transparentar el consumo: −29% hogares movilizados. Fondo comunitario de US$20.000 por MW al
año (≈ US$38 millones en 2035): −29%. Google Quilicura usa solo el 29% de su derecho de
agua, pero los vecinos temen el 100%.
*Supuesto:* depende de cuánto cambia la percepción con información; es un parámetro con rango.

### No hay destino escrito: 12 comunas distintas pueden terminar como la más afectada en 2035
En 200 futuros con las mismas reglas, la comuna con más hogares movilizados cambia según el
orden en que llegan los proyectos: Cerrillos (20%), Padre Hurtado (20%), Quilicura (18%),
Tiltil (18%). La "comuna de sacrificio" se decide en el camino, no en el mapa, y por eso una
evaluación proyecto por proyecto no puede anticiparla.

## 3. Hipótesis del informe

| Hipótesis | Veredicto | Evidencia (2035 salvo que se indique) |
|---|---|---|
| Exigir enfriamiento por aire reduce el agua, pero satura antes la red (S1) | Se confirma | Agua de los DC de la RM −54% (58 → 27 L/s); consumo en el mes peak +3,8% y lista de espera +19%. El agua ahorrada se paga con más electricidad en verano. |
| Evaluar en conjunto acorta los plazos porque reduce los litigios (S1) | Parcialmente | Litigios −33% y hogares movilizados −44%, pero el plazo anuncio → operación sube 2,0 meses (44,6 → 46,6): las ventanas de evaluación y las reubicaciones se comen lo ahorrado en tribunales. |
| Acelerar permisos no conecta más DC si la red está saturada (A3) | Se confirma | Permisos al doble de rápido: +0,5% MW en la RM en 2030 (798 → 802) y el plazo baja solo 2,4 meses. |
| Transparentar el agua reduce más el conflicto que compensar (S2) | Parcialmente | Solo transparencia: −33% hogares movilizados; solo fondo de US$20.000/MW/año: −31%. Magnitudes parecidas; juntas suman. |
| Con el umbral de 1.000 t casi ningún DC nuevo pasa por SEIA (S7, A1) | Se confirma | Desde 2027, con 1.000 t solo 2% de los proyectos nuevos entra al SEIA; con 80 t, 75%. Supone que los proyectos declaran diésel justo bajo el límite, como los 7 casos reales tras el DS 17 (511 a 990 t). |
| Un incentivo al norte descomprime la RM (A3, S8) | Se confirma | En 2030 Antofagasta pasa de 312 a 537 MW, los MW esperando red −49% y los MW operando en la RM −2,1%. |

Las cifras de transparencia y fondo difieren levemente entre la sección 2 (−29%/−29%) y
esta tabla (−33%/−31%) porque vienen de baterías distintas (factorial de 7 palancas vs
escenarios predefinidos de 200 réplicas). La conclusión es la misma.

## Cómo reproducir

```bash
uv sync
uv run pytest                                  # 12 tests
uv run python -m dcsim.validation              # tabla de la sección 1
uv run python -m dcsim.explore                 # ~15.000 simulaciones, ~4 min
uv run python -m dcsim.findings                # sección 2, escribe cache/findings.json
uv run uvicorn dcsim.server:app --port 8000    # interfaz en http://localhost:8000
```

`cache/findings.json` va versionado para que la sección de hallazgos de la interfaz
funcione sin correr `explore`. El resto de `cache/` (ensambles y `explore_raw.json`,
~46 MB) se regenera solo.
