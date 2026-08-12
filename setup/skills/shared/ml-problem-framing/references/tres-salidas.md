# Las tres salidas, en detalle

Cómo se reconoce cada una, qué se entrega y cuál es el error típico. La regla de
arriba de todo: **se pronuncia una sola, por escrito, y con su razón.**

## Salida 1 · No es ML

**Se reconoce por** cualquiera de estas:

- La decisión ya se toma hoy con un criterio que alguien sabe enunciar. Eso es
  una heurística, aunque viva en la cabeza de una persona.
- El objetivo es *contar*, *ordenar* o *comparar contra un umbral*, no estimar
  algo desconocido. `GROUP BY` no es un modelo.
- No hay etiqueta histórica, o hay menos de unos cientos de casos positivos.
  Sin etiquetas no hay aprendizaje supervisado, y lo que queda —clustering,
  anomalía no supervisada— rara vez responde la pregunta de negocio original.
- La promesa es explicable por ley o por contrato. Un umbral defendible gana a
  un modelo que hay que justificar caso por caso.

**Qué se entrega**: la regla escrita con sus números, dónde se aplica, y **cómo
se va a medir que funciona** — porque esa medición es la que, si algún día se
degrada, justifica la salida 2.

**El error típico**: descartar esta salida por aburrida. La *Rule #1* está
primera a propósito.

## Salida 2 · ML clásico tabular

**Se reconoce por**: hay etiqueta histórica suficiente, las features existen en
el momento de predecir (lo comprueba la salida 3), y la heurística que ya existe
se ha vuelto inmantenible — muchas ramas, muchas excepciones, nadie se atreve a
tocarla.

**Qué se entrega**: el traspaso a `ml-tabular-workflow` nombrando tres cosas —
la etiqueta y su ventana temporal, la heurística actual (que pasa a ser el
baseline obligatorio) y la decisión de negocio con su coste asimétrico, que es
lo que luego fija el umbral.

**El error típico**: saltar aquí sin haber medido la heurística. Sin ese número
no hay con qué comparar, y cualquier AUC parecerá buena.

## Salida 3 · ML con fuga de disponibilidad

**Se reconoce por** la pregunta que casi nadie hace: *para cada feature, ¿ese
valor existe y es consultable en el instante en que hay que predecir, o solo
aparece después?* Los tres casos que se repiten:

- **Dato que llega tarde.** Existe, pero con retraso de proceso (cierre
  contable, consolidación diaria). Sirve para entrenar y no para servir.
- **Dato que solo existe si el evento ya ocurrió.** `fecha_de_baja` predice el
  churn perfectamente y es inútil: es la etiqueta con otro nombre.
- **Dato que se rellena retroactivamente.** La tabla histórica se corrige a
  posteriori, así que el valor que ves hoy no es el que había entonces.

**Qué se entrega**: la auditoría feature a feature con veredicto
*disponible / tardía / imposible*, y el problema **reformulado con las que
sobreviven**. Casi siempre eso lo devuelve a la salida 2 con menos señal, y a
veces a la salida 1.

**El error típico**: descubrirlo después de entrenar, cuando el modelo da un
resultado sospechosamente bueno. Eso ya no es framing, es fuga — y su taxonomía
completa vive en `ml-tabular-workflow`.

## Si ninguna encaja

Entonces la pregunta de negocio todavía no está escrita. Vuelve al paso 1 y
escribe qué decisión cambia con la predicción; si no cambia ninguna, el trabajo
correcto es no hacer nada.
