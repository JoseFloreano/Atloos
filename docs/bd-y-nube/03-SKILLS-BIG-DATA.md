# Skills de Big Data
## Pipelines, dbt, Spark, warehouses, lineage, costos y PII

> **Fecha:** Julio 2026
> **Alcance:** Skills para el stack de datos moderno — transformación (dbt), procesamiento distribuido (Spark), orquestación (Airflow), warehouses (Snowflake/BigQuery) y las dimensiones transversales que distinguen a la ingeniería de datos: lineage, costo y datos sensibles.
> **Estrategias aplicadas:** 2 (trío), 3 (importar colecciones), 5 (disciplina MCP). Hallazgo central: B6 (validación semántica).

---

## 1. Por qué big data no es "software con más filas"

El punto de partida de las colecciones más serias del ecosistema: la ingeniería de datos parece desarrollo de software desde lejos, pero el riesgo real suele vivir **fuera del diff** — lineage downstream, corrección de métricas, costo de warehouse, drift de esquemas, exposición de PII y la confianza del negocio en los datos después de un cambio. Un cambio pequeño de modelo puede requerir revisar fuentes upstream, entender impacto downstream, actualizar docs, añadir tests, comparar salidas y verificar el manejo de datos sensibles.

Consecuencia para el diseño de skills: **cada skill de esta capa termina con un criterio de verificación semántica** (paridad de datos, conteos, lineage revisado), no con "el pipeline corrió".

---

## 2. Familias de skills

### 2.1 Transformación — dbt (`dbt-workflow`)

La colección de referencia es Altimate Skills, open-source y con métricas publicadas: +22% de velocidad de ejecución (TPC-H 1TB) con queries 100% lógicamente equivalentes en optimización SQL, y 53% en ADE-bench (43 tareas dbt reales). Su cobertura: desarrollo dbt, `dbt-troubleshoot` (fallos de compilación, errores de runtime, tests que fallan, datos incorrectos, rendimiento), revisión y traducción de SQL, chequeos de paridad, seguridad de migraciones de schema, análisis de costos de Snowflake, auditoría de PII y visualización.

El flujo validado con MCP: los dbt Agent Skills generan modelos en todas las capas siguiendo las prácticas del proyecto, con schema YAMLs, descripciones de columnas, docs de grano y tests generados junto al modelo — y validación de los modelos intermedios en vivo contra Postgres vía MCP.

Instalación (protocolo de importación en doc 05):

```
/plugin marketplace add AltimateAI/data-engineering-skills
/plugin install dbt-skills@data-engineering-skills
```

### 2.2 Procesamiento distribuido — Spark (`spark-optimizer`)

No existe (a julio 2026) una colección Spark del nivel de Altimate; aquí aplica la estrategia 1 (skill propia de convenciones + checklist). Contenido mínimo:

- Diagnóstico antes de tocar código: leer el plan (`explain`), identificar shuffles y skew.
- Reglas de particionado (tamaño objetivo de partición, cuándo `repartition` vs `coalesce`).
- Broadcast joins: umbral y cuándo forzarlo/deshabilitarlo.
- Skew: técnicas de salting y AQE antes de reescrituras heroicas.
- Prohibición de `collect()` sobre datasets grandes y de UDFs de Python donde exista función nativa.
- Verificación: comparar conteos y checksums de salida contra la versión previa (B6).

### 2.3 Orquestación — Airflow (`pipeline-designer`)

El stack de referencia del ecosistema es Airflow para orquestación, dbt para transformación, Snowflake o BigQuery como warehouse, pytest para calidad y Git para versionado, conectado a Claude vía el trío MCP/Skills/Hooks. La skill de diseño de pipelines codifica el patrón ETL/ELT completo que la práctica documenta: extracción con manejo de **paginación por cursor, rate limiting respetando headers, fallos parciales (log y continuar, no tirar el batch completo) y deduplicación por upsert sobre clave natural** — el ejemplo canónico (Stripe → Postgres) reduce a segundos lo que a mano toma 30–45 minutos.

Un consejo operativo del ecosistema que vale adoptar: pedir a Claude que cree una skill de "validación" que combine todas las verificaciones (tests, lint, chequeos) para correr antes de cada commit o edición — y respaldarla con un hook.

### 2.4 Warehouses — Snowflake / BigQuery (`warehouse-query-optimize`, `warehouse-cost-review`)

Dos skills separadas (optimizar ≠ auditar costo):

- **Optimización**: importable de Altimate (`query-optimize`) para razonar sobre SQL lento o ineficiente.
- **Costo**: Altimate incluye análisis de costos de Snowflake; para BigQuery, la skill propia debe imponer: estimar bytes escaneados antes de correr, prohibir `SELECT *` en tablas particionadas sin filtro de partición, y registrar el costo estimado en la respuesta.

MCPs relevantes: Snowflake ofrece MCP gestionado con acceso gobernado (Cortex Analyst para analítica estructurada, Cortex Search para documentos), con el patrón recomendado de empezar read-only antes de habilitar acciones; BigQuery tiene MCP remoto para generar/ejecutar queries y devolver metadata de datasets, tablas y esquemas; y el MCP Toolbox cubre ambos más Trino/ClickHouse para stacks OSS.

### 2.5 Lineage y metadata (`lineage-check`)

Antes de modificar un modelo, Claude puede consultar el catálogo de metadata (OpenMetadata MCP) para saber qué dashboards dependen de él, quién es dueño de los datos downstream y si hay PII involucrado. Para dbt-core (sin dbt Cloud) existe MCP con metadata del proyecto y lineage a nivel de modelo **y de columna**. La skill correspondiente convierte esto en un paso obligatorio: *ningún cambio a un modelo con dependientes sin listar el impacto downstream primero*.

### 2.6 PII (`pii-guard`)

Altimate incluye auditoría de PII como skill. La versión propia mínima: clasificar columnas nuevas (identificadores directos/indirectos), exigir enmascaramiento o exclusión en capas de exposición, y bloquear ejemplos de datos reales en docs y tests (usar `data-faker` o equivalente).

---

## 3. Mapa skill → MCP → hook (estrategia 2 aplicada)

| Skill | MCP (con fallback) | Hook de garantía |
|-------|--------------------|------------------|
| `dbt-workflow` | dbt-core MCP / warehouse read-only — fallback: `dbt compile` local | pytest/dbt test antes de commit |
| `spark-optimizer` | — (opera sobre código y planes) | — |
| `pipeline-designer` | orquestador si existe — fallback: generar DAG + instrucciones | lint + tests pre-commit |
| `warehouse-*` | Toolbox/Snowflake/BigQuery **read-only** | bloquear write sin confirmación |
| `lineage-check` | OpenMetadata / dbt-core MCP — fallback: grep de refs en el repo dbt | — |
| `pii-guard` | — | opcional: scan de patrones en diffs |

---

## 4. Ubicación en el sistema de skills del repo

| Skill | Carpeta | Nota |
|-------|---------|------|
| `pipeline-designer`, `pii-guard` | `shared/` | Metodología pura |
| `dbt-workflow`, `spark-optimizer`, `warehouse-query-optimize`, `lineage-check` | `claude-code/` | Asumen toolchain local (dbt, spark-submit) o MCP localhost |
| `warehouse-cost-review` | `shared/` | La revisión de costo es análisis; Cowork la puede hacer sobre exports |
| `data-doc-writer` (diccionarios, ERDs, docs de lineage) | `cowork/` | Asume documentos y web research |

---

## Fuentes

| Fuente | Qué sustenta |
|--------|--------------|
| [Altimate — We Created Data Engineering Skills](https://www.altimate.ai/blog/we-created-data-engineering-skills-for-claude-code) | §1, §2.1, §2.4, §2.6: naturaleza del riesgo en datos, cobertura de la colección |
| [Altimate — anuncio open source y benchmarks](https://blog.altimate.ai/teaching-claude-code-the-art-of-data-engineering-introducing-altimate-skills) | §2.1: métricas TPC-H/ADE-bench, comandos de instalación |
| [Intro a Claude Code para Data Engineers](https://thepipeandtheline.substack.com/p/intro-claude-code-for-data-engineers) | §2.3, §2.5: stack de referencia, OpenMetadata MCP, skill de validación combinada |
| [Data Modeling con dbt, Miro y Postgres MCP](https://thepipeandtheline.substack.com/p/claude-code-for-data-engineers-data-modeling-dbt-miro-postgresql-skills-mcp) | §2.1: generación por capas con YAMLs/tests y validación MCP |
| [Claude Code for Data Engineers: SQL, ETL, Debugging](https://www.aibuilderclub.com/blog/claude-code-for-data-engineers) | §2.3: patrón ETL completo (paginación, rate limit, fallos parciales, upsert) |
| [Snowflake Managed MCP Servers](https://www.snowflake.com/en/blog/managed-mcp-servers-secure-data-agents/) | §2.4: MCP gobernado, Cortex, patrón read-only primero |
| [InfoWorld — 10 MCP servers para DBs](https://www.infoworld.com/article/4181843/10-mcp-servers-to-connect-llms-with-databases.html) · [MCP Toolbox](https://github.com/googleapis/mcp-toolbox) · [awesome-mcp-servers/databases](https://github.com/TensorBlock/awesome-mcp-servers/blob/main/docs/databases.md) | §2.4, §2.5: BigQuery MCP, Toolbox, dbt-core MCP con lineage de columna |

---

*Siguiente: [Skills de Nube e IaC](./04-SKILLS-NUBE-E-IAC.md)*