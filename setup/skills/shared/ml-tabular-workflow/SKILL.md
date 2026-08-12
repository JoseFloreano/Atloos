---
name: ml-tabular-workflow
description: >
  Ejecuta un problema de ML clásico tabular en el único orden que impide los
  fallos caros: split correcto → baseline → auditoría de fuga → métrica de
  negocio con umbral justificado → entrega reproducible. Use when the user says
  "entrena el modelo", "haz el modelo de churn/fraude/demanda", "mejora el AUC",
  "¿qué métrica uso?", "valida el modelo", "¿hay fuga de datos?", "el modelo va
  demasiado bien", "elige el umbral", "¿árboles o red neuronal?", or cuando
  `ml-problem-framing` cerró en su salida 2. NO usar antes de decidir si el
  problema es de ML —eso es `ml-problem-framing`—, ni para LLMs, agentes o RAG
  (`agentic-system-design`).
---

# ML Tabular Workflow

**El orden es la mitad del método**: cada paso miente si va antes que el
anterior.

## Los 5 pasos

1. **Split correcto, antes de mirar nada.** Todo estadístico calculado sobre el
   conjunto entero —normalizar, imputar, seleccionar, codificar— antes de
   partir es fuga. Con tiempo, el split es temporal: `TimeSeriesSplit` con
   `gap`. Y si la etiqueta se forma sobre una ventana (*¿churn en los próximos
   90 días?* usa datos hasta t+90), hacen falta **purging y embargo** — el
   k-fold estándar asume i.i.d. y **filtra por los bordes** (López de Prado,
   cap. 7).
2. **Baseline obligatorio**, en este orden: (1) **la regla de negocio que ya
   existe**, que es el listón real; (2) `DummyClassifier` / `DummyRegressor`;
   (3) un lineal regularizado. Dacrema et al. (RecSys 2019): de 7 métodos
   neuronales de recomendación reproducidos, **6 quedaron por debajo de
   heurísticas simples**. ⚠ Es de recomendadores: extrapólalo con cautela y
   dilo así.
3. **Auditoría de fuga, por nombre**: **target leakage · train-test
   contamination · temporal leakage · group leakage**. El caso más subestimado
   es el target encoding sin out-of-fold. Taxonomía y fuentes:
   `references/fuga-de-datos.md`.
4. **Métrica de negocio y umbral justificado.** `accuracy` miente con desbalance
   por pura aritmética. Y *«ROC-AUC miente»* sin mecanismo es un eslogan: como
   *ranking*, ROC y PR son equivalentes (Davis & Goadrich, ICML 2006, Teorema
   3.2 — una curva domina en ROC **si y solo si** domina en PR). Lo que cambia
   es la **sensibilidad**: el FPR lleva los verdaderos negativos en el
   denominador y en desbalance son mayoría abrumadora, así que la curva ROC
   **absorbe** el error; en PR la precisión los compara contra los verdaderos
   positivos y reacciona de golpe. **El umbral es un hiperparámetro de negocio**,
   no una convención estadística: optimízalo contra una función de coste con
   `TunedThresholdClassifierCV`. `references/metrica-y-umbral.md`.
5. **Entrega reproducible**: semillas fijas · lockfile con versiones exactas ·
   hash o timestamp del snapshot de datos · **los índices exactos del split
   guardados** (`random_state=42` no protege si cambia el tamaño del dataset) ·
   una model card de una página · registro de experimentos ligero.
   `references/entrega-reproducible.md`.

## Qué modelo

**Boosting es el default operativo.** DL o foundation models se justifican con
dataset pequeño-mediano (<100K filas) sin tiempo de tunear, o con estructura no
tabular en las mismas filas — **nunca como default**. La
evidencia y por qué no hay ganador único: `references/modelos-tabulares.md`.

## Qué NO hacer

- **No mirar el test** hasta cerrar el modelo: mirarlo lo convierte en
  validación y te quedas sin test.
- **No celebrar un resultado sospechosamente bueno**: en tabular es fuga hasta
  demostrar lo contrario. Vuelve al paso 3.
- **No reportar la métrica sin el umbral y su coste**: así no dice qué se hará
  distinto.
