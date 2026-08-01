---
name: pipeline-designer
description: >
  Diseña pipelines ETL/ELT con el patrón canónico: cursor persistido
  atómicamente con la carga, rate limiting, fallos parciales con umbral,
  upsert idempotente y manejo de deletes. Use when the user says "haz un
  pipeline", "trae los datos de la API de X a la base", "sincroniza X con Y",
  "un ETL para", "automatiza esta carga", or when writing any recurring data
  extraction/load job. NO para pipelines/orquestación de agentes LLM — eso es
  agentic-system-design. Las validaciones las pone data-quality-gates; el
  destino sigue sql-conventions.
---

# Pipeline Designer

Un pipeline no es un script que corre una vez: corre mil veces, se cae a la
mitad, se reintenta y no debe duplicar ni perder nada. El patrón completo
(detalle en `references/etl-pattern.md`) aplica a todo job RECURRENTE; para
una extracción one-off basta idempotencia + capas 1-3 de data-quality-gates.

## Requisitos

- Ninguno para diseñar. Con orquestador (Airflow/cron), genera para él; sin
  él, script + instrucciones de programación.
- Paso 7 (probar caminos feos): en Claude Code ejecuta el test/dry-run; en
  Cowork entrega los casos como tests escritos + instrucciones, y dilo.

## Pasos

1. **Contrato**: fuente, destino, clave natural, frecuencia, ventana
   (incremental por defecto; full refresh solo justificado). Pregunta
   OBLIGATORIA: ¿la fuente hace hard deletes? El cursor incremental nunca
   los ve — elige y documenta: flags/eventos de borrado, reconciliación
   periódica de claves, o full refresh programado como red de seguridad
   (eso NO es el anti-patrón del full refresh por pereza).
2. **Extracción robusta**:
   - Cursor cuando exista, persistido EN LA MISMA transacción que el batch
     que lo cubre — nunca antes de cargar, o el corte pierde datos.
   - Cursor de timestamp: extrae desde `cursor − ventana de solape`
     (5-15 min; el upsert absorbe el retrabajo — cubre late-arriving data y
     empates), campo en UTC/timestamptz, u opta por cursor compuesto
     `(updated_at, id)`.
   - Si la API solo ofrece offset: orden por clave inmutable, solape de una
     página, dedup vía upsert, reconciliar conteos al final — y anota que la
     fuente no garantiza consistencia entre páginas.
   - Rate limiting: respeta `Retry-After`/`X-RateLimit-*` con backoff
     exponencial + jitter; reintenta también 5xx y errores de red.
3. **Fallos parciales**: fila mala → rechazados con motivo, y se continúa.
   Umbral doble sobre el ACUMULADO de la corrida (no por página): aborta si
   rechazos >5% (con mínimo de muestra) O >1.000 absolutos — defaults
   configurables. Rechazos >0 donde históricamente eran 0 se reportan aunque
   no aborten.
4. **Carga idempotente**: upsert sobre la clave natural (`INSERT ... ON
   CONFLICT DO UPDATE`). Correr dos veces = correr una. Prohibido `INSERT` a
   secas en cargas recurrentes. Trampas del upsert (multi-VALUES, updated_at
   NULL) en references.
5. **Compuertas**: las 4 capas de `data-quality-gates` — la query de
   anomalías programada JUNTO al job (mismo orquestador), no como tarea
   manual.
6. **Registra decisiones**: full vs incremental, clave natural, manejo de
   deletes, umbral distinto del default → `adr-writer` o `memory-keeper`.
7. **Prueba el camino feo** antes de entregar: página duplicada, registro
   inválido, corte a mitad de batch, segunda corrida completa — los cuatro
   deben quedar consistentes.

## Qué NO hacer

- No entregues un pipeline sin responder "¿qué pasa si corre dos veces?" y
  "¿qué pasa con los borrados de la fuente?".
- No guardes credenciales en el código (`.env`/secrets del orquestador). En
  Claude Code, corre `secrets-scan` antes de commitear.
- Las tablas auxiliares (`_pipeline_runs`, etc.) también salen por migración
  (sql-conventions §6 y §12).

## Referencias

- `references/etl-pattern.md` — esqueleto anotado (API → Postgres) con las
  4 garantías, sus trampas y los límites del patrón; portabilidad
  MySQL/SQLite al final.
