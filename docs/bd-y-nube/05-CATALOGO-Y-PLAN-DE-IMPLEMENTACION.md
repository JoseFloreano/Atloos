# Catálogo Propuesto y Plan de Implementación
## Decisión consolidada de la subserie bd-y-nube

> **Fecha:** Julio 2026
> **Insumos:** Docs 01–04 de esta subserie, reglas de `setup/skills/README.md` y `_template/SKILL.md`, anti-patrones del doc 06 y hallazgos R2/R4 de la auditoría (`auditoria/09`).
> **Formato:** Igual que el doc 06 de la serie principal — catálogo, protocolo, fases con checkboxes, métricas y anti-patrones.

> ## ⚠ Podado el 2026-08-09 (F0 del RFD 17)
>
> Este catálogo aprobó **17 piezas de golpe** y se construyeron 5. Las 12
> restantes siguieron listadas un año como si estuvieran vivas, hasta que dos
> skills maduras empezaron a citarlas: `sql-conventions` mandaba a
> `warehouse-query-optimize`, y ella y `migration-auditor` afirmaban que *"la
> garantía dura"* era un hook de la Fase S2 **que nunca se construyó**.
>
> **El criterio de la poda es la dependencia**: se borra lo que exige una
> herramienta o un MCP que no está en uso; sobrevive como *candidata* la
> metodología pura, que funciona con lo que ya hay.
>
> Lo borrado está abajo con su motivo, **no en una lista de pendientes**: un
> pendiente que nadie va a tocar y se lista como activo es lo que produjo esto.
> El ritual completo fue `borrar → grep de referencias entrantes → redirigir →
> grep final = 0`, el mismo que ya se usaba para cosechar RFDs. Lo vigila
> `setup/scripts/tests/test-skill-catalog.py`.

---

## 1. Catálogo consolidado

### `shared/` — metodología pura (funciona en Claude Code y Cowork, sin dependencias)

| Skill | Origen | Estado |
|-------|--------|:---------:|
| `sql-conventions` | Propia (nadie conoce tus convenciones) | ✅ **Construida** |
| `schema-designer` | Propia; patrón ERD-antes-de-SQL del ecosistema | ✅ **Construida** |
| `data-quality-gates` | Propia; patrón de 4 capas de validación | ✅ **Construida** |
| `migration-auditor` | Importada + adaptada (checklist locks/pérdida/rollback/índices) | ✅ **Construida** |
| `pipeline-designer` | Propia; patrón ETL canónico (paginación, rate limit, fallos parciales, upsert) | ✅ **Construida** |
| `pii-guard` | Propia (o extraída de Altimate) | 🕐 Candidata — metodología pura; aplica hoy (cobranza, recetas) |
| `<provider>-standards` | Plantilla del doc 04 §3 | 🕐 Plantilla condicional — se instancia si un proveedor entra en uso |

### `cowork/` — investigación, documentos, sandbox cloud

| Skill | Origen | Estado |
|-------|--------|------|
| `data-doc-writer` | Propia | 🕐 Candidata — diccionarios de datos y ERDs como entregable |
| `cloud-architecture-review` | Propia | 🕐 Candidata — comparativas con web research, sin dependencias |

**Las candidatas caducan.** Por R3 del RFD 17, una pieza propuesta y no
construida en **60 días** se borra o se re-justifica por escrito. Reloj desde
esta poda: **vencen el 2026-10-08.**

### Borradas el 2026-08-09 — exigen herramienta o MCP que no está en uso

| Pieza | Iba a ser | Dependencia que no existe |
|---|---|---|
| `dbt-workflow` | claude-code | dbt local + MCP de warehouse/dbt-core |
| `terraform-safe-apply` | claude-code | terraform/tofu local |
| `terraform-module-author` | claude-code | terraform local |
| `spark-optimizer` | claude-code | Spark local |
| `warehouse-query-optimize` | claude-code | MCP de warehouse read-only |
| `warehouse-cost-review` | shared | Warehouse con datos de coste |
| `lineage-check` | claude-code | MCP dbt-core/OpenMetadata |
| `db-explorer` | claude-code | MCP de DB read-only (Toolbox) |
| `cloud-cost-tagger` | shared | Cuenta de nube con facturación en uso |
| `validate-migration-review` | hook PreToolUse | Requería la Fase S1 completa |
| `block-terraform-apply-without-plan` | hook PreToolUse | terraform en uso |
| `tf-fmt-validate` | hook PostToolUse | terraform en uso |
| `sql-lint` | hook PostToolUse | (era opcional ya entonces) |

⚠ **Ninguna de estas se cita ya desde una skill viva.** Las dos citas que
existían se cerraron en la misma poda: la de `sql-conventions` se borró, y las
dos que prometían la "garantía dura" del hook ahora dicen la verdad —que
ningún hook impone ese paso—. El porqué, en
`setup/skills/shared/migration-auditor/references/procedencia.md`.

Si alguna dependencia entra en uso, la pieza se re-propone **desde cero y con
fecha**. Resucitarla desde esta tabla sería volver a aprobar 17 de golpe.

---

## 2. Protocolo de importación de skills de terceros

> **Nota (2026-08-03):** donde este doc diga `claude-skills/` como carpeta de
> destino, hoy es `setup/skills/` del repo — el espejo de OneDrive se retiró
> (`ADR-20260803-skills-fuente-unica`). El criterio no cambia, solo la ruta.

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

### Fases S1, S2 y S3 — **canceladas el 2026-08-09**

Las tres dependían de herramientas que nunca entraron en uso: dbt, Snowflake,
terraform, Spark, MCPs de warehouse. De la S1 solo se hizo lo que no dependía
de nada —adaptar `migration-auditor` al motor propio—, y está hecho.

La **S2 merece una nota**, porque es la que hizo daño. Prometía *"apply y
migraciones imposibles de ejecutar saltándose la revisión"*, y dos skills
maduras acabaron citando ese resultado como si existiera. **Nunca se escribió
una línea de esos hooks.** Un resultado prometido en un plan no es una
garantía; una skill que lo cita como tal miente con la mejor intención.

Si mañana entra terraform o un warehouse, se abre una propuesta nueva con su
fecha. **No se reanuda esta.**

---

## 4. Métricas de éxito

| Métrica | Baseline (sin skills) | Objetivo |
|---------|----------------------|----------|
| Correcciones de convenciones por sesión de datos | Recurrentes | ≈ 0 |
| MCPs conectados por defecto en una sesión | — | Solo los que la tarea requiere |

⚠ Las tres métricas de "0, bloqueado por hook" **se retiraron el 2026-08-09**:
medían hooks que no existen. Una métrica cuyo mecanismo no se construyó no
mide nada — se lee como cumplida porque nadie la comprueba.

---

## 5. Anti-patrones específicos de esta subserie

**Anti-patrón S1 — La mega-skill "data-engineering":** una skill que intenta cubrir SQL + dbt + Spark + nube dispara con todo y no especializa nada. Skills chicas con triggers precisos; la relación entre ellas vive en este doc, no en el contexto.

**Anti-patrón S2 — Importar colecciones completas:** instalar 15 skills de una colección "por si acaso" contamina el espacio de triggers y multiplica la superficie de inyección (R4). Solo lo que se usa.

**Anti-patrón S3 — MCP de warehouse con write habilitado sin hook:** equivale a DDL sin revisión. Read-only por defecto; write solo detrás de enforcement.

**Anti-patrón S4 — Confiar la seguridad de infraestructura al texto de la skill:** las instrucciones son probabilísticas (R2); apply/destroy/migraciones requieren hook. *"La skill dice qué hacer; el hook lo garantiza."*

**Anti-patrón S5 — Skills con credenciales o rutas de máquina:** regla 5 del sistema de skills, vigente: las skills viajan por OneDrive y se empaquetan en plugins; keys y rutas van en `.env`/settings.

---

*Este documento cierra la subserie bd-y-nube (00–05). Extiende la serie principal 00–09; revisar tras implementar la Fase S1, y re-auditar el catálogo (protocolo §2, paso 5) cada vez que se actualice una colección importada.*