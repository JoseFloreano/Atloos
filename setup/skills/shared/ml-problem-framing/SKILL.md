---
name: ml-problem-framing
description: >
  Decide si un problema es de machine learning ANTES de construir nada, y
  termina siempre en una de tres salidas: no es ML (una regla, un SQL o un
  umbral), es ML clásico tabular, o es ML con fuga de disponibilidad que hay que
  auditar antes de seguir. Use when the user says "¿esto se puede predecir?",
  "quiero un modelo que X", "hagamos ML para esto", "entrena un modelo",
  "¿machine learning para X?", "un algoritmo que detecte X", "predice el
  churn/la demanda/el fraude", "¿esto lo resuelve una IA?", or antes de
  cualquier trabajo de modelado. La ejecución —split, baseline, fuga, métrica,
  umbral— es `ml-tabular-workflow`; esta decide si hay que llegar ahí. NO usar
  para LLMs, agentes o RAG: eso es `agentic-system-design`.
---

# ML Problem Framing

**Tu mejor respuesta posible es «no es ML».** No es la salida de emergencia: es
la que más veces acierta.

## Las tres salidas — no hay una cuarta

1. **No es ML** → una regla, un SQL o un umbral.
2. **ML clásico tabular** → el caso por defecto. Entrega a `ml-tabular-workflow`.
3. **ML con fuga de disponibilidad** → el dato que usarías **no existe en el
   momento de predecir**. Audita las features antes de seguir; lo que no
   sobreviva devuelve el problema a la salida 1 o 2 con menos features.

Pronuncia una, por escrito, con su razón. Un «depende» no es una salida.

## El criterio, y no es «sería interesante»

Google, *Rules of Machine Learning* (Zinkevich), las tres que gobiernan:

> **Rule #1: Don't be afraid to launch a product without machine learning.**
>
> **Rule #3: Choose machine learning over a complex heuristic.** *"A simple
> heuristic can get your product out the door. A complex heuristic is
> unmaintainable."*
>
> **Rule #4: Keep the first model simple and get the infrastructure right.**

Combinadas: **ML se justifica cuando la heurística se volvió tan compleja que ya
no se mantiene**, no cuando sería interesante. Si todavía no hay heurística, la
respuesta es la salida 1 — constrúyela y mide cuánto aguanta.

## Por qué el listón está tan alto

Sculley et al., *Hidden Technical Debt in Machine Learning Systems* (NeurIPS
2015): el código de modelado es una fracción minúscula del sistema real, y el
resto es deuda que no se ve al decidir.

- **CACE**, *changing anything changes everything*: no hay entradas
  independientes; mover una feature mueve el modelo entero.
- **Dependencias ocultas** sobre datos que otro cambia sin avisarte.
- **Código glue** y pipelines en jungla, que es donde vive el coste real.

Una regla o un SQL no tienen nada de esto. Ese es el descuento que la salida 1
te ofrece, y por eso se evalúa primero.

## Pasos

1. **Escribe la decisión de negocio que cambia** con la predicción. Si no cambia
   ninguna, para: no es un problema de modelado.
2. **Busca la heurística que ya existe**, aunque sea humana y esté en la cabeza
   de alguien. Es el listón real, y luego es el baseline obligatorio.
3. **Audita la disponibilidad** de cada feature: ¿ese dato existe cuando toca
   predecir, o solo después? El que llega a T+1 no sirve para decidir en T.
4. **Aplica la Rule #3**: ¿heurística simple (déjala) o ya inmantenible
   (entonces sí)?
5. **Pronuncia la salida** y, si es la 2, entrega a `ml-tabular-workflow`.

Cómo se reconoce cada salida y qué se entrega en cada una:
`references/tres-salidas.md`.
