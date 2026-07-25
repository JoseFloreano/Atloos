# Catálogo Propuesto y Plan de Implementación
## Decisión consolidada de la subserie bd-y-nube

> **Fecha:** Julio 2026
> **Insumos:** Docs 01–04 de esta subserie, reglas de `setup/skills/README.md` y `_template/SKILL.md`, anti-patrones del doc 06 y hallazgos R2/R4 de la auditoría (doc 09).
> **Formato:** Igual que el doc 06 de la serie principal — catálogo, protocolo, fases con checkboxes, métricas y anti-patrones.

---

## 1. Catálogo consolidado

### `shared/` — metodología pura (funciona en Claude Code y Cowork, sin dependencias)

| Skill | Origen | Prioridad |
|-------|--------|:---------:|
| `sql-conventions` | Propia (nadie conoce tus convenciones) | 🔴 Alta |
| `schema-designer` | Propia; patrón ERD-antes-de-SQL del ecosistema | 🔴 Alta |
| `data-quality-gates` | Propia; patrón de 4 capas de validación | 🔴 Alta |
| `migration-auditor` | Importada + adaptada (checklist locks/pérdida/rollback/índices) | 🟠 Media |
| `pipeline-designer` | Propia; patrón ETL canónico (paginación, rate limit, fallos parciales, upsert) | 🟠 Media |
| `<provider>-standards` (solo proveedores en uso) | Propia con plantilla del doc 04 §3 | 🟠 Media |
| `cloud-cost-tagger` | Propia | 🟡 Baja |
| `pii-guard` | Propia (o extraída de Altimate) | 🟡 Baja |
| `warehouse-cost-review` | Parcialmente importable de Altimate | 🟡 Baja |

### `claude-code/` — toolchain local y MCPs localhost

| Skill | Origen | Dependencias declaradas (con fallback) |
|-------|--------|----------------------------------------|
| `dbt-workflow` | Importar Altimate (`dbt-skills`) | dbt local; warehouse/dbt-core MCP → fallback `dbt compile` |
| `terraform-safe-apply` | Importar terraform-skill + plan-review de devops-skills | terraform/tofu local; **hooks obligatorios** (doc 04 §4) |
| `spark-optimizer` | Propia (doc 03 §2.2) | spark local — fallback: análisis estático del código |
| `warehouse-query-optimize` | Importar Altimate (`query-optimize`) | MCP warehouse read-only → fallback: análisis del plan pegado |
| `lineage-check` | Propia | dbt-core/OpenMetadata MCP → fallback: grep de refs |
| `db-explorer` | Propia | MCP DB read-only (Toolbox) → fallback: generar SQL para ejecución manual |

### `cowork/` — investigación, documentos, sandbox cloud

| Skill | Origen | Nota |
|-------|--------|------|
| `data-doc-writer` | Propia | Diccionarios de datos, ERDs, docs de lineage como entregables |
| `cloud-architecture-review` | Propia | Comparativas de servicios con web research |

### Hooks nuevos (garantías — mismo principio que `validate-graphiti-group-id.py`)

| Hook | Garantiza | Tipo |
|------|-----------|------|
| `validate-migration-review` | Ninguna migración se ejecuta sin pasar el checklist | PreToolUse |
| `block-terraform-apply-without-plan` | Ningún apply sin plan-review reciente; destroy siempre bloqueado | PreToolUse |
| `tf-fmt-validate` | fmt + validate tras editar `.tf` | PostToolUse |
| `sql-lint` (opcional) | Lint de SQL al guardar | PostToolUse |

---

## 2. Protocolo de importación de skills de terceros

Motivación: R4 de la auditoría — todo lo que entra a `claude-skills/` son instrucciones auto-cargadas en ambos productos y todas las laptops; quien pueda escribir ahí puede inyectar comportamiento.

1. Clonar la colección **fuera** de `claude-skills/` y leer completo cada SKILL.md y sus `references/`/`scripts/` (jamás instalar sin leer).
2. Copiar solo las skills que se van a usar (no la colección entera — anti-patrón 3 aplicado a skills: cada description compite por el trigger).
3. Adaptar: motor/dialecto propio, rutas del setup, sección "Requisitos" con fallback (regla 3 del `_template`), descripción-trigger en el idioma en que pides las cosas.
4. Registrar procedencia al final del SKILL.md: repo origen + commit + fecha (permite auditar upstream después).
5. Commit en el repo git de `claude-skills/` (excluyendo `_build/`) y revisar `git diff` ante cualquier cambio no reconocido.
6. Correr `sync-skills` y verificar el trigger con una petición real.

---

## 3. Plan de implementación por fases

### Fase S0 — Núcleo shared (½ día)

**Objetivo**: valor inmediato sin dependencias; validar el flujo completo del sistema de skills con contenido real.

- [ ] Escribir `sql-conventions`, `schema-designer`, `data-quality-gates` desde `_template/`
- [ ] Descripciones-trigger con frases literales ("crea una tabla", "diseña el esquema", "optimiza esta query", "valida este pipeline")
- [ ] `sync-skills` + verificación de trigger en Claude Code y en Cowork (re-subir `dev-skills.zip`)

**Resultado**: Claude aplica tus convenciones de datos en ambos productos.

### Fase S1 — Importaciones (1 día)

**Objetivo**: capitalizar el trabajo del ecosistema.

- [ ] Ejecutar el protocolo §2 sobre Altimate (si el stack incluye dbt/Snowflake) → `dbt-workflow`, `warehouse-query-optimize`
- [ ] Ejecutar el protocolo §2 sobre terraform-skill (+ plan-review de devops-skills) → `terraform-safe-apply`, `terraform-module-author`
- [ ] Adaptar `migration-auditor` al motor propio → `shared/`

**Resultado**: skills probadas por terceros, adaptadas y auditadas, en el catálogo propio.

### Fase S2 — Garantías (½ día, requiere Fase S1)

**Objetivo**: convertir las reglas de mayor riesgo en garantías deterministas.

- [ ] `block-terraform-apply-without-plan` + `tf-fmt-validate` en `hooks/`
- [ ] `validate-migration-review`
- [ ] Documentar los hooks en `hooks/README.md` (mismo formato que el existente)

**Resultado**: apply y migraciones imposibles de ejecutar saltándose la revisión.

### Fase S3 — MCPs y skills dependientes (según necesidad, no antes)

**Objetivo**: conectar datos en vivo solo cuando una skill lo requiera.

- [ ] MCP Toolbox read-only para la DB principal → habilita `db-explorer` y validación en `dbt-workflow`
- [ ] `spark-optimizer`, `lineage-check` según stack activo
- [ ] `<provider>-standards` del proveedor realmente en uso
- [ ] `data-doc-writer` y `cloud-architecture-review` en `cowork/`

**Resultado**: el trío completo skill+MCP+hook operando, sin MCPs ociosos.

---

## 4. Métricas de éxito

| Métrica | Baseline (sin skills) | Objetivo |
|---------|----------------------|----------|
| Correcciones de convenciones por sesión de datos | Recurrentes | ≈ 0 |
| Migraciones que llegan a producción sin checklist | Posible | 0 (bloqueado por hook) |
| `terraform apply` sin plan revisado | Posible | 0 (bloqueado por hook) |
| Modelos dbt sin tests ni docs generados | Habitual | Raro (skill los genera en paralelo) |
| MCPs conectados por defecto en una sesión | — | Solo los que la tarea requiere |

---

## 5. Anti-patrones específicos de esta subserie

**Anti-patrón S1 — La mega-skill "data-engineering":** una skill que intenta cubrir SQL + dbt + Spark + nube dispara con todo y no especializa nada. Skills chicas con triggers precisos; la relación entre ellas vive en este doc, no en el contexto.

**Anti-patrón S2 — Importar colecciones completas:** instalar 15 skills de una colección "por si acaso" contamina el espacio de triggers y multiplica la superficie de inyección (R4). Solo lo que se usa.

**Anti-patrón S3 — MCP de warehouse con write habilitado sin hook:** equivale a DDL sin revisión. Read-only por defecto; write solo detrás de enforcement.

**Anti-patrón S4 — Confiar la seguridad de infraestructura al texto de la skill:** las instrucciones son probabilísticas (R2); apply/destroy/migraciones requieren hook. *"La skill dice qué hacer; el hook lo garantiza."*

**Anti-patrón S5 — Skills con credenciales o rutas de máquina:** regla 5 del sistema de skills, vigente: las skills viajan por OneDrive y se empaquetan en plugins; keys y rutas van en `.env`/settings.

---

*Este documento cierra la subserie bd-y-nube (00–05). Extiende la serie principal 00–09; revisar tras implementar la Fase S1, y re-auditar el catálogo (protocolo §2, paso 5) cada vez que se actualice una colección importada.*