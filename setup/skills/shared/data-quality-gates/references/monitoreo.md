# Capa 4 · Monitoreo — el detalle

Extraído del paso 4 del `SKILL.md` de `data-quality-gates` (sprint 4), literal.
Solo aplica a pipelines **recurrentes**: una carga puntual no tiene de qué
desviarse.

- **Frescura**: alerta si la última carga excede su periodo esperado.
- **Volumen**: alerta si las filas se desvían >30% de la mediana de las
  últimas 7 corridas (default — ajústalo por pipeline y documenta). Con
  menos de 7 corridas de historia, registra sin alertar.
- **Antes de crear tabla propia**, revisa qué YA registra corridas (Airflow
  metadata, dbt artifacts/elementary, Great Expectations): la capa 4 se
  construye sobre eso. `_pipeline_runs (pipeline, run_at, rows_loaded,
  rows_rejected, status)` — misma definición que `pipeline-designer` — es
  el mínimo viable cuando no hay nada.
- **Una alerta necesita un canal que llegue solo** (cron/orquestador que corre
  la query de anomalías y notifica). Si solo entregas la query, dilo:
  "monitoreo pasivo, requiere revisión manual".
