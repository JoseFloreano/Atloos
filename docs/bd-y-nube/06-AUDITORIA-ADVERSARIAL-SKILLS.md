# Auditoría Adversarial de las Skills bd-y-nube
## Hallazgos, correcciones aplicadas y crítica a la investigación de origen

> **Fecha:** Agosto 2026
> **Método:** 4 agentes independientes con lentes distintas — (1) fact-check contra documentación oficial de PostgreSQL/MySQL/SQLite, (2) code review adversarial del esqueleto ETL intentando romper sus garantías, (3) auditoría del sistema de skills (triggers, contradicciones, template, anti-patrones S1-S5), (4) practicante senior escéptico cuestionando también la investigación de origen (docs 02-05).
> **Resultado:** ~40 hallazgos; TODOS los de severidad alta y media aplicados a las 5 skills. Este doc registra qué se corrigió y por qué, para poder re-auditar upstream después.

---

## 1. Lo más grave: dos garantías del patrón ETL eran FALSAS

La primera versión de `etl-pattern.md` prometía cuatro garantías en su tabla de "caminos feos". La revisión adversarial demostró que dos no se cumplían tal como estaba escrito el código:

**Garantía "corte a mitad de batch reanuda sin huecos" — rota dos veces.** (a) El cursor se persistía dentro del generador `extraer()`, ANTES de que el consumidor cargara las filas: un crash entre ambos dejaba el cursor avanzado y las filas jamás cargadas — pérdida de datos silenciosa y permanente, exactamente lo que la tabla decía imposible. (b) psycopg 3 con `autocommit=False` (el default) abre una transacción implícita en la primera query, con lo que `conn.transaction()` degrada a SAVEPOINT y **nada se commiteaba nunca** (verificado contra psycopg.org/docs). *Fix:* conexión con `autocommit=True` explícito + el cursor se persiste EN LA MISMA transacción que su batch (filas + rechazos + verificación de salida + cursor, atómicos). Un crash deja todo o nada; la re-corrida re-descarga a lo sumo una página, que el upsert absorbe.

**Garantía "registro inválido no tira el batch" — rota en el caso límite.** El umbral de 5% de rechazos se evaluaba POR PÁGINA: 1 fila mala en una página final de 10 filas = 10% → abortaba la corrida entera, contradiciendo la garantía. Además `transformar` solo capturaba `ValueError` — un `KeyError` por campo faltante (el escenario canónico) mataba el batch. *Fix:* umbral sobre el acumulado de la corrida con mínimo de muestra (200) + techo absoluto (1.000 rechazos, porque 4.9% de 10M filas no es "todo bien") + captura de `(ValueError, KeyError, TypeError)`.

Otros fixes al patrón: reintentos de 5xx y errores de transporte (antes solo 429), `Retry-After` en formato HTTP-date ya no crashea el parser, `WHERE updated_at < EXCLUDED` reemplazado por `IS DISTINCT FROM` + manejo de NULL (el original congelaba el destino ante updated_at NULL y descartaba correcciones same-timestamp para siempre), advertencia de cardinality violation si se optimiza a multi-VALUES, validación del envelope de la API, y sección nueva "Límites del patrón" (hard deletes, timezones, late-arriving data, backfill inicial, portabilidad MySQL/SQLite).

## 2. Errores técnicos míos confirmados contra docs oficiales

El fact-check contra postgresql.org/dev.mysql.com/sqlite.org confirmó 13 afirmaciones y encontró estos errores/imprecisiones (todos corregidos):

| Error en v1 | Realidad (fuente oficial) |
|-------------|--------------------------|
| "`SET NOT NULL` sin validación previa **reescribe** la tabla" | NO reescribe: escanea bajo ACCESS EXCLUSIVE. El riesgo (lock) es real; el mecanismo era falso — llevaba a conclusiones erróneas sobre disco/bloat |
| "`VALIDATE CONSTRAINT` (lock **breve**)" | Al revés: lock DÉBIL durante TODO el escaneo (no frena DML pero sí otros DDL/VACUUM). Lo breve son los locks fuertes del ADD/SET final |
| "cambio de tipo con truncamiento = pérdida de datos" | En PG el cambio a tipo más corto FALLA con error; la pérdida silenciosa llega vía `USING` explícito o MySQL sin modo estricto |
| "Alembic: `op.execute` con autocommit" | La API real es `op.get_context().autocommit_block()` |
| "índice compuesto: la más selectiva primero" | Los docs dicen: columnas de IGUALDAD antes que las de rango; "selectividad primero" es heurística popular que falla |
| Sección "MySQL/MariaDB" con datos solo de MySQL 8.0 | DDL atómico en MariaDB llega en 10.6.1, no con "8.0" |

**Omisiones de alta severidad añadidas a engine-notes:** `ADD FOREIGN KEY` bloquea TAMBIÉN la tabla referenciada (SHARE ROW EXCLUSIVE — "solo afecta a la hija" es falso); `ALGORITHM=INSTANT` de MySQL faltaba por completo (recomendar INPLACE a secas convertía un cambio gratuito en rebuild); `CREATE INDEX CONCURRENTLY` espera a TODAS las transacciones abiertas (se cuelga con idle-in-transaction); `PRAGMA foreign_keys` de SQLite es no-op dentro de una transacción (el paso 1 del patrón de 12 pasos va ANTES del BEGIN); reescrituras necesitan ~2× disco; UNIQUE online vía `CREATE UNIQUE INDEX CONCURRENTLY` + `USING INDEX`; réplicas/WAL/replicación lógica (el DDL no viaja).

**Al checklist de migration-auditor se le añadió un punto 6** (objetos dependientes: vistas/MVs/triggers/policies/particiones/réplicas) — el "checklist destilado del ecosistema" no lo tenía, y un `ALTER COLUMN TYPE` sobre columna usada por una vista falla en PG y suele terminar en `DROP VIEW ... CASCADE` improvisado.

## 3. Contradicciones entre las 5 skills (resueltas)

- **Fallos parciales con defaults opuestos**: pipeline-designer decía "registra y continúa"; data-quality-gates decía "una compuerta rota detiene el batch, continuar solo si el usuario lo pide". Resuelto con vocabulario compartido en ambas: FILA inválida → rechazados y sigue (con umbral); COMPUERTA rota (schema/conteos/integridad) → detiene SIEMPRE.
- **¿Auditar siempre o solo tablas existentes?**: schema-designer contradecía el "ALWAYS" de migration-auditor. Ahora: SIEMPRE.
- **`_pipeline_runs` con dos esquemas distintos** en dos skills → unificada (`pipeline, run_at, rows_loaded, rows_rejected, status`).
- **Verificación de salida "después del commit"** en el código vs "antes de dar por cargado" en la skill → movida DENTRO de la transacción.
- **"±X%" sin valor** → default operativo: >30% vs mediana de últimas 7 corridas; con <7 corridas, registrar sin alertar.

## 4. Huecos de práctica real (lente practicante)

Añadidos: **tipos** en sql-conventions (`timestamptz` siempre, `numeric` para dinero — el error de producción #1 no estaba), **tipo de PK decidido** (`bigint GENERATED ALWAYS AS IDENTITY`, no `serial`; UUID solo justificado — antes el agente elegía al azar), **FKs por rol** (`manager_id` — la regla literal reventaba con self-joins), **transversales de schema-designer** (multi-tenancy/soft-delete/auditoría: lo más caro de retrofitear, nadie lo preguntaba), **criterio de alcance** ("el usuario pide 2 tablas y recibe 9" — ahora el pedido fija el alcance), **fallback desatendido** del "espera acuerdo del ERD" (entregar ERD+supuestos+DDL marcado NO VALIDADO, jamás ejecutar), **hard deletes** como pregunta obligatoria del contrato del pipeline, **offset como fallback legítimo** cuando la API no da cursor (mitigado, no prohibido), **capa 4 solo para recurrentes** (el import one-off de 300 filas ya no recibe infraestructura de monitoreo), y **construir sobre registros existentes** (Airflow/dbt artifacts) antes de inventar `_pipeline_runs`.

## 5. Crítica a la investigación de origen (docs 02-05) — no confiar al 100%

- El checklist de migration-auditor viene del **catálogo/blog de Agensi (vendor, contenido SEO)**, no de postmortems: por eso omitía dependientes, réplicas y WAL. Los benchmarks de Altimate (+22% TPC-H, 53% ADE-bench) son **autopublicados sin réplica externa** — el doc 03 los llama "métricas publicadas" sin escepticismo; tratarlos como afirmación del vendor (coherente con H10).
- La promesa "reduce a segundos lo que toma 30-45 min" (doc 03 §2.3) es métrica de velocidad de *generación de código* de un blog de curso, no de calidad del pipeline; la v1 la heredó como absolutismo ("el costo de añadirlo después es 10×", cifra inventada) — eliminado.
- "Cursor, no offset" del ecosistema es dogma: media industria solo expone offset. Lo correcto es mitigar su defecto (drift entre páginas), no prohibirlo.
- Regla general adoptada: **cada checklist importado se contrasta contra documentación oficial del motor antes de darlo por completo** — protocolo §2 del doc 05, paso nuevo implícito.

## 6. Pendientes que salieron de la auditoría

- [ ] Una línea en `deploy-planner` (skill existente): paso de DB/migraciones → "toda migración del release auditada con migration-auditor".
- [ ] El anti-patrón S4 sigue vivo hasta la Fase S2: "toda migración pasa por migration-auditor" es texto; el hook `validate-migration-review` es la garantía. Las skills ya lo advierten en su salida.
- [ ] Al importar `warehouse-query-optimize` (Fase S1), revisar que su trigger no colisione: sql-conventions ya le cedió "optimiza esta query".

---

*Extiende la subserie bd-y-nube (00-05). Las 5 skills auditadas viven en `setup/skills/shared/`; las correcciones de este doc están aplicadas en la versión commiteada junto a él.*
