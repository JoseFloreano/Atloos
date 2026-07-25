# Skills de Bases de Datos
## SQL, esquemas, migraciones y calidad de datos

> **Fecha:** Julio 2026
> **Alcance:** Skills para trabajo con bases relacionales (PostgreSQL como caso principal, MySQL/SQLite/SQL Server como secundarios) y su pareja de MCPs.
> **Estrategias aplicadas:** 1 (estándares propios), 2 (trío skill+MCP+hook), 6 del resumen (validación semántica — B6).

---

## 1. Las cuatro familias de skills de base de datos

La investigación identifica cuatro familias de alto impacto, en orden de retorno:

### 1.1 Convenciones SQL (`sql-conventions`)

La familia de mayor impacto porque las convenciones varían enormemente entre equipos. Una skill que sabe que el proyecto usa PostgreSQL con convenciones específicas de naming, estrategias de indexado y herramienta de migraciones produce resultados dramáticamente mejores que SQL genérico.

Contenido mínimo de la skill:

- Motor y versión por defecto; dialecto a asumir cuando no se indique.
- Naming: snake_case vs camelCase, singular vs plural, prefijos de tablas puente, sufijos `_id`/`_at`.
- Patrones de constraints: foreign keys, checks, defaults — cuándo cada uno.
- Estrategia de indexado (qué se indexa por defecto, cuándo índices parciales/compuestos).
- Qué herramienta genera migraciones (nunca DDL suelto en producción).

### 1.2 Diseño de esquemas (`schema-designer`)

El diseño de esquemas es donde la asistencia de IA aporta más valor: estructuras normalizadas, detección temprana de problemas de rendimiento y generación de migraciones. La skill debe forzar el orden correcto: entidades → relaciones → grano → claves → índices → migración, y exigir un ERD (o descripción textual del modelo) **antes** del DDL — el flujo documentado del ecosistema valida el modelo con stakeholders antes de escribir SQL.

### 1.3 Seguridad de migraciones (`migration-auditor`)

El ecosistema ya destiló el checklist: revisar cambios de esquema por **riesgos de locking, pérdida de datos, rollbacks faltantes y problemas de índices**, cubriendo PostgreSQL, MySQL y SQLite — atrapando migraciones peligrosas antes de que lleguen a producción. Es la skill candidata #1 para el patrón skill+hook de la estrategia 2: un hook PreToolUse puede bloquear la ejecución de una migración que no pasó por la revisión.

Checklist mínimo que la skill impone:

1. ¿El DDL toma locks largos en tablas grandes? (ALTER que reescribe, índices sin CONCURRENTLY en Postgres)
2. ¿Hay pérdida potencial de datos? (DROP/cambio de tipo con truncamiento)
3. ¿Existe rollback documentado y probado?
4. ¿Los índices nuevos justifican su costo de escritura?
5. ¿La migración es compatible con la versión anterior del código (deploy sin downtime)?

### 1.4 Calidad de datos (`data-quality-gates`)

Las skills de calidad instruyen a Claude a añadir validación en cada etapa: **validación de entrada** (chequeo de schema, tipos, manejo de nulos), **de transformación** (verificación de conteo de filas, rangos de valores), **de salida** (integridad referencial, reglas de negocio) y **monitoreo** (alertas de frescura, detección de anomalías de volumen). Esta es la respuesta directa al hallazgo B6: en datos, "corre sin error" no significa "es correcto".

---

## 2. MCPs de bases de datos — el catálogo relevante

| MCP | Cobertura | Nota |
|-----|-----------|------|
| **MCP Toolbox** (googleapis, open source) | PostgreSQL, MySQL, MariaDB, SQL Server, Oracle, MongoDB, Redis, ClickHouse, Neo4j, Snowflake, Trino y los servicios GCP (AlloyDB, BigQuery, Cloud SQL, Spanner) | Un solo binario multi-motor con `--prebuilt=<db>`; opción por defecto recomendada para este setup |
| **Portafolio oficial AWS** | Aurora Postgres, Aurora DSQL, DynamoDB, ElastiCache, Redshift | Elección sensata solo si el proyecto es AWS-heavy |
| **Servidores Postgres read-only** (varios) | SELECT-only con enforcement a nivel de sesión | Preferibles para exploración; el write queda para la toolchain de migraciones |
| **FalkorDB MCP** | Grafos FalkorDB | Ya presente en el setup (Graphiti); no confundir su rol de memoria con un MCP de datos de proyecto |

Reglas de esta subserie (estrategia 5):

- **Read-only por defecto.** El modo write de un MCP de DB equivale a darle DDL directo a un agente; los propios servidores lo marcan como no recomendado.
- La skill declara el MCP en "Requisitos" con fallback: *"si no hay MCP de DB conectado, genera el SQL y pide al usuario ejecutarlo/validarlo manualmente"*. Así la misma skill sirve en Cowork.
- Un patrón emergente a considerar cuando el modelo es capaz: un único tool `execute_sql` y dejar que el agente explore el esquema, escriba queries y se auto-corrija iterativamente — sin RAG ni capa semántica. Potente para exploración; incompatible con producción sin read-only + hooks.

---

## 3. Qué importar vs qué escribir (aterrizaje de la estrategia 3)

| Necesidad | Fuente | Acción |
|-----------|--------|--------|
| Revisión de migraciones | Skill comunitaria `migration-auditor` (Postgres/MySQL/SQLite) | Importar, leer completa, adaptar al motor propio |
| Optimización de queries | `query-optimize` de Altimate | Importar si el stack coincide; si no, extraer el checklist a skill propia |
| Traducción de dialectos | `sql-translate` de Altimate (preserva la intención de la query entre dialectos) | Importar solo si hay migración de warehouse activa |
| Convenciones propias | — | **Escribir desde cero** (nadie más conoce tus convenciones) |
| Calidad de datos | Patrón de 4 capas del ecosistema | Escribir propia, es corta |
| Datos de prueba | Skills tipo `data-faker` (JSON/CSV realistas desde descripción del esquema) | Opcional, baja prioridad |

---

## 4. Ubicación en el sistema de skills del repo

| Skill | Carpeta | Justificación (tabla de decisión de `skills/README.md`) |
|-------|---------|--------------------------------------------------------|
| `sql-conventions` | `shared/` | Pura metodología/convención |
| `schema-designer` | `shared/` | Metodología; el ERD puede ser texto/mermaid en ambos productos |
| `migration-auditor` | `shared/` (skill) + `claude-code/` (hook) | La revisión es metodología; el enforcement requiere hooks locales |
| `data-quality-gates` | `shared/` | Metodología |
| `db-explorer` (uso de MCP read-only) | `claude-code/` | Depende de MCP en localhost; fallback documentado |

---

## Fuentes

| Fuente | Qué sustenta |
|--------|--------------|
| [Best Claude Code Skills for Data Engineering (Agensi)](https://www.agensi.io/learn/best-claude-code-skills-data-engineering) | §1.1, §1.2, §1.4: familias de skills, convenciones, capas de validación |
| [Catálogo de skills de data engineering (Agensi)](https://www.agensi.io/skills/data-engineering) | §1.3: checklist de `migration-auditor`; `data-faker`; patrón text2sql |
| [Altimate — skills de data engineering](https://www.altimate.ai/blog/we-created-data-engineering-skills-for-claude-code) | §3: query-optimize, sql-translate |
| [Data Modeling con dbt + Postgres MCP](https://thepipeandtheline.substack.com/p/claude-code-for-data-engineers-data-modeling-dbt-miro-postgresql-skills-mcp) | §1.2: ERD antes del SQL, validación en vivo vía MCP |
| [MCP Toolbox (googleapis)](https://github.com/googleapis/mcp-toolbox) | §2: cobertura multi-motor y prebuilt tools |
| [10 MCP servers para bases de datos (InfoWorld)](https://www.infoworld.com/article/4181843/10-mcp-servers-to-connect-llms-with-databases.html) | §2: portafolio AWS, estado del MCP de Postgres |
| [TensorBlock awesome-mcp-servers — databases](https://github.com/TensorBlock/awesome-mcp-servers/blob/main/docs/databases.md) | §2: servidores read-only, patrón execute_sql iterativo |

---

*Siguiente: [Skills de Big Data](./03-SKILLS-BIG-DATA.md)*