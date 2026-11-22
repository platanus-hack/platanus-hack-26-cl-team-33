# Aterriza

**Con todo lo aprobado y en trámite en tu comuna, ¿alcanzan el agua y la red?**

Chile aprueba los data centers de a uno, y desde el DS 17 casi siempre sin participación ciudadana. Pero se suman en la misma red eléctrica, el mismo acuífero y las mismas comunas: Quilicura, Lampa, Cerrillos, Tiltil. En Santiago ya hay 1.420 MW de proyectos esperando conexión a una red saturada.

Cada data center se evalúa por separado y nadie suma el efecto de todos. Aterriza simula ese efecto conjunto, comuna por comuna, para el momento en que se pelea hoy, la evaluación ambiental: el SEA, el municipio, los vecinos y la empresa miran los mismos números. Suma todos los data centers de una comuna, con lo que cada uno declaró al SEA, y deja cambiar la palanca que más pesa: enfriar con agua o con aire (menos agua es más electricidad). Detrás hay una simulación mes a mes hasta 2035, con permisos, la fila de conexión del CEN, tribunales y vecinos.

## Qué puedes hacer

- **Sumar todos los data centers de una comuna** (Quilicura por defecto) y ver su agua, su electricidad, la red libre del nodo y los vecinos movilizados en 2030 y 2035. Para los que aún no operan, elegir agua o aire desde 2027 y compararlo con lo declarado en los mismos 60 futuros. Cada proyecto muestra lo que declaró al SEA, con enlace, y cuánta agua usaría con agua y cuántos MW más pediría con aire.
- **Elegir una regla** (seguir como hoy, permisos más rápidos, solo enfriamiento por aire, evaluar por zona con los vecinos, irse al norte o las tres que más ayudan) y ver cómo cambian el mapa y las cifras de 2035.
- **Armar tu propia regla** palanca por palanca y compararla con seguir como hoy en los mismos 60 futuros (hasta un minuto en el sitio).
- **Mover el año** de 2012 a 2035 y ver cómo se llena cada comuna, o cuánto cambia respecto de seguir como hoy.
- **Tocar una comuna o un proyecto** para ver su detalle, su historia y su probabilidad de terminar operando, en tribunales o esperando red.

## Lo que encontramos

En una batería de 15.080 simulaciones, en los 200 futuros de cada regla y en la simulación por comuna (60 futuros):

- **Quilicura, todo sumado.** Con lo que declaró cada proyecto, sus data centers usan en 2035 17,9 L/s de agua (la de ~3.100 hogares) y 188 MW. Si los 4 que aún no operan enfriaran con agua desde 2027, usarían 2,4 veces más agua (42,2 L/s) y 18 MW menos de electricidad, y los vecinos movilizados subirían de 46% a 64%. Con más oposición y juicios, cada uno de esos 4 llegaría a operar en 80% a 87% de los futuros, en vez de 92% a 98% con aire.
- **El freno es la red, no el permiso.** Con permisos cuatro veces más rápidos, Santiago tendría solo 0,3% más MW de data centers en 2030. Los proyectos aprobados igual esperan conexión eléctrica.
- **No hay que elegir entre inversión y comunidad.** Enfriamiento por aire, un fondo comunitario y un incentivo al norte mejoran a la vez agua, conflicto, juicios e inversión en 82% de los futuros, y la cuenta de la luz no sube más (1,8% en vez de 2,1%) porque parte de la demanda se va al norte, donde sobra energía solar (si allá no presiona la tarifa).
- **El agua decide el juicio.** Si Google hubiera enfriado Cerrillos con aire en 2019, la probabilidad de juicio habría bajado de 78% a 4%, y a fines de 2023 habría estado operando en 90% de los futuros.
- **Dónde importa más que cuánto.** Alejar un solo proyecto de las casas baja 56% el conflicto de toda Lampa.
- **Más proyectos, más espera.** Si llegan el doble de proyectos, se conecta solo 19% más, pero los juicios se multiplican por 2,3.

## ¿Le podemos creer?

Al modelo le dimos cada proyecto real (tamaño, lugar, enfriamiento) y cuándo se anunció; él decidió cuándo se aprobaba, se construía, se iba a tribunales o quedaba esperando red. Reproduce **14 de 14 datos reales** de 2012 a 2026. 6 son validación (ningún parámetro se ajustó con ese dato), por ejemplo:

- el consumo eléctrico de los data centers de Santiago: 105 MW en 2021 y 252 MW en 2025 (el dato: 90 y 260 MW), y 2,4% de la electricidad de Chile (el dato: 2 a 3%);
- el estado de cada proyecto a noviembre de 2026: acierta 93%, apenas más que el 91% de una regla trivial. En los 26 con nombre público empatan (85%), así que aquí el modelo no muestra más que esa regla.

Los otros 8 son calibración (un parámetro se ajustó con ese dato, o el dato entró al modelo), como el agua y la potencia de Google en Quilicura, los 1.420 MW en lista de espera del CEN y los 2 juicios ambientales. Cada chequeo muestra sus límites en "Detalle técnico".

**¿Y si los supuestos fallan?** Movimos a sus extremos, uno por uno, los 40 parámetros que no se sortean, y luego los sorteamos juntos (76.500 simulaciones). 5 de los 6 hallazgos que comparan reglas o historias resisten los 80 casos, y los 6 resisten el sorteo conjunto. El de Cerrillos depende de cuánto pesa el agua en la opinión de los vecinos: si pesa la mitad, no se cumple.

## Cómo funciona

Un modelo de agentes con stocks y flujos que avanza mes a mes desde 2012:

- **63 proyectos**: 34 reales con nombre público y 29 supuestos que reproducen el inventario de Santiago y la lista del CEN; además, unos 5 nuevos al año que eligen comuna, enfriamiento y cuánto diésel declarar.
- **El SEA**, que manda cada proyecto al SEIA o a pertinencia según el umbral de 1.000 t del DS 17, y **la fila de conexión del CEN**, nodo por nodo.
- **2.300 hogares sintéticos.** Su oposición crece con la cercanía, el diésel, el miedo por el agua y la acumulación, y baja con empleo y beneficios. Se contagia dentro de la comuna y lleva proyectos a tribunales.
- **200 futuros por regla**, con números aleatorios comunes y 13 parámetros inciertos sorteados en cada uno. Se reporta la mediana y el rango del 90%.

Hecho con Python (NumPy, FastAPI) y HTML/JS con Leaflet. Los datos vienen de un informe de investigación de noviembre de 2026, el CEN, la DGA, el SEA y el Censo 2017. Las ecuaciones, los supuestos y lo que no sabemos están a la vista en la sección "Detalle técnico".

## Equipo 33 · Track Simulations

Anish Samtani, Alejandro Lorca Acevedo y Andrés Faúndez Ortega.
