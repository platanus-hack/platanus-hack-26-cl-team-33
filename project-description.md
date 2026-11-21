# Aterriza

**Simula el impacto de los data centers en tu comuna.**

Chile aprueba los data centers de a uno, y desde el DS 17 casi siempre sin participación ciudadana. Pero se suman en la misma red eléctrica, el mismo acuífero y las mismas comunas: Quilicura, Lampa, Cerrillos, Tiltil. En Santiago ya hay 1.420 MW de proyectos esperando conexión a una red saturada.

Aterriza pone todos los proyectos reales en un solo modelo y proyecta qué le pasa a la gente hasta 2035: agua, electricidad, vecinos movilizados, juicios e inversión, comuna por comuna.

## Qué puedes hacer

- **Elegir una regla** (seguir como hoy, permisos más rápidos, solo enfriamiento por aire, evaluar por zona con los vecinos, irse al norte o las tres que más ayudan) y ver cómo cambian el mapa y las cifras de 2035.
- **Armar tu propia regla** palanca por palanca y compararla con seguir como hoy en los mismos 60 futuros (hasta un minuto en el sitio).
- **Colocar un data center** en el mapa (tamaño, enfriamiento, año y regla) y seguir a sus vecinos a menos de 3 km hasta 2035: cuántos se movilizan en contra, si llega a operar, si va a tribunales y a cuántos otros proyectos les quita red. Cada futuro se corre con y sin ese data center.
- **Mover el año** de 2012 a 2035 y ver cómo se llena cada comuna, o cuánto cambia respecto de seguir como hoy.
- **Tocar una comuna o un proyecto** para ver su detalle, su historia y su probabilidad de terminar operando, en tribunales o esperando red.

## Lo que encontramos

En una batería de 15.080 simulaciones y en los 200 futuros de cada regla:

- **El freno es la red, no el permiso.** Con permisos cuatro veces más rápidos, Santiago tendría solo 0,4% más MW de data centers en 2030. Los proyectos aprobados igual esperan conexión eléctrica.
- **No hay que elegir entre inversión y comunidad.** Enfriamiento por aire, un fondo comunitario y un incentivo al norte mejoran a la vez agua, conflicto, juicios e inversión en 84% de los futuros, y la cuenta de la luz no sube más (1,8% en vez de 2,0%) porque parte de la demanda se va al norte, donde sobra energía solar (si allá no presiona la tarifa).
- **El agua decide el juicio.** Si Google hubiera enfriado Cerrillos con aire en 2019, la probabilidad de juicio bajaba de 83% a 2%, y a fines de 2023 estaría operando en 93% de los futuros.
- **Dónde importa más que cuánto.** Alejar un solo proyecto de las casas baja 60% el conflicto de toda Lampa.
- **Más proyectos, más espera.** Si llegan el doble de proyectos, se conecta solo 19% más, pero los juicios se multiplican por 2,3.

## ¿Le podemos creer?

Al modelo le dimos cada proyecto real (tamaño, lugar, enfriamiento) y cuándo se anunció; él decidió cuándo se aprobaba, se construía, se iba a tribunales o quedaba esperando red. Reproduce **14 de 14 datos reales** de 2012 a 2026. 7 son validación (ningún parámetro se ajustó con ese dato), por ejemplo:

- el consumo eléctrico de los data centers de Santiago: 90 MW en 2021 y 260 MW en 2025;
- las 4 comunas con vecinos organizados;
- el estado de los 54 proyectos conocidos a noviembre de 2026: acierta 96%, más que el 91% de una regla trivial.

Los otros 7 son calibración (un parámetro se ajustó con ese dato), como el agua de Google en Quilicura (458 millones de litros en 2024), los 1.420 MW en lista de espera del CEN y los 2 juicios ambientales. Cada chequeo muestra sus límites.

**¿Y si los supuestos fallan?** Movimos a sus extremos, uno por uno, los 40 parámetros que no se sortean, y luego los sorteamos juntos (76.500 simulaciones). 5 de los 6 hallazgos revisados resisten los 80 casos, y los 6 resisten el sorteo conjunto. El de Cerrillos depende de cuánto pesa el agua en la opinión de los vecinos: si pesa la mitad, no se cumple.

## Cómo funciona

Un modelo de agentes con stocks y flujos que avanza mes a mes desde 2012:

- **62 proyectos reales** (33 con nombre público) y unos 5 nuevos al año, que eligen comuna, enfriamiento y cuánto diésel declarar.
- **El SEA**, que manda cada proyecto al SEIA o a pertinencia según el umbral de 1.000 t del DS 17, y **la fila de conexión del CEN**, nodo por nodo.
- **2.300 hogares sintéticos.** Su oposición crece con la cercanía, el diésel, el miedo por el agua y la acumulación, y baja con empleo y beneficios. Se contagia dentro de la comuna y lleva proyectos a tribunales.
- **200 futuros por regla**, con números aleatorios comunes y 13 parámetros inciertos sorteados en cada uno. Se reporta la mediana y el rango del 90%.

Hecho con Python (NumPy, FastAPI) y HTML/JS con Leaflet. Los datos vienen de un informe de investigación de noviembre de 2026, el CEN, la DGA, el SEA y el Censo 2017. Las ecuaciones, los supuestos y lo que no sabemos están a la vista en la sección "Detalle técnico".

## Equipo 33 · Track Simulations

Anish Samtani, Alejandro Lorca Acevedo y Andrés Faúndez Ortega.
