# Investigación Técnica: Skills de Bases de Datos, Big Data y Nube para Claude
## Índice General y Resumen Ejecutivo — Subserie `bd-y-nube`

> **Fecha de investigación:** Julio 2026
> **Alcance:** Estrategias de uso de Claude (Code + Cowork) con skills orientadas a bases de datos, big data y nube, integradas al sistema de skills existente (`setup/skills/`, carpetas `shared/ claude-code/ cowork/`).
> **Relación con la serie principal:** Esta subserie extiende los docs 00–09. Asume como vigentes los hallazgos H1–H10, los anti-patrones del doc 06 y las reglas del sistema de skills (`setup/skills/README.md` y `_template/SKILL.md`).

---

## Índice de Documentos

| # | Documento | Tema central |
|---|-----------|--------------|
| 01 | [Estrategias de Uso con Claude](./01-ESTRATEGIAS-DE-USO-CON-CLAUDE.md) | Las 5 estrategias que estructuran toda la subserie |
| 02 | [Skills de Bases de Datos](./02-SKILLS-BASES-DE-DATOS.md) | SQL, esquemas, migraciones, calidad de datos, MCPs de DB |
| 03 | [Skills de Big Data](./03-SKILLS-BIG-DATA.md) | dbt, Spark, orquestación, warehouses, lineage, costos, PII |
| 04 | [Skills de Nube e IaC](./04-SKILLS-NUBE-E-IAC.md) | Terraform/OpenTofu, bibliotecas por proveedor, safety-first |
| 05 | [Catálogo Propuesto y Plan de Implementación](./05-CATALOGO-Y-PLAN-DE-IMPLEMENTACION.md) | Skills concretas por carpeta, fases, riesgos y verificación |

---

## Resumen Ejecutivo

### El problema que resuelve esta investigación

El sistema de skills del repo ya funciona (carpeta única en OneDrive, sync a Claude Code, plugin para Cowork), pero está vacío de contenido de dominio. Para trabajo con bases de datos, big data y nube, Claude sin skills se comporta como un ingeniero que conoce toda la sintaxis pero ninguna convención: genera SQL genérico que ignora el dialecto y el naming del proyecto, propone migraciones sin evaluar locks ni rollbacks, escribe Terraform que aplica hoy y se vuelve inmantenible en seis meses, y repite en cada sesión los mismos errores que ya se le corrigieron.

La investigación externa converge en el mismo diagnóstico que la serie principal ya estableció para memoria (H4, doc 05): **el conocimiento de dominio debe empaquetarse como skills con progressive disclosure, no como prompts repetidos ni como CLAUDE.md enciclopédico.**

### Las tres capas del dominio

```
Capa 1: BASES DE DATOS (doc 02)
"Crea una migración para añadir esta columna"
→ Sin skill: ALTER TABLE genérico, sin evaluar locks ni rollback
→ Con skill: revisión de riesgo (locking, pérdida de datos, índices) antes del DDL

Capa 2: BIG DATA / PIPELINES (doc 03)
"Crea el staging model de la fuente Stripe"
→ Sin skill: modelo dbt que compila pero ignora capas, tests y docs del proyecto
→ Con skill + MCP: modelo validado en vivo contra la DB, con schema YAML y tests

Capa 3: NUBE / IaC (doc 04)
"Levanta la infraestructura para este servicio"
→ Sin skill: Terraform monolítico, sin tagging, sin plan-review
→ Con skill: módulos, plan revisado antes de apply, estándares del proveedor
```

### Hallazgos críticos de esta subserie

**Hallazgo B1 — Las skills de convenciones ganan a las skills genéricas:**
El consenso del ecosistema es que las skills de mayor impacto en datos son las que codifican convenciones propias (dialecto, naming, indexado, herramienta de migraciones), porque las convenciones de bases de datos varían enormemente entre equipos. Una skill "sabe SQL" no aporta nada; una skill "sabe *nuestro* SQL" cambia el resultado. (Detalle en doc 01, estrategia 1.)

**Hallazgo B2 — El patrón dominante es el trío Skills + MCP + Hooks:**
MCPs conectan (bases de datos, orquestadores, catálogos), skills codifican metodología, hooks garantizan (lint de SQL, tests antes de commit). Es exactamente el principio del doc 05 de la serie principal — *"CLAUDE.md dice qué hacer; los hooks lo garantizan"* — aplicado al dominio de datos. (Doc 01, estrategia 2.)

**Hallazgo B3 — Ya existen colecciones open-source maduras; escribir todo desde cero es un error:**
Altimate (dbt/Snowflake, con benchmarks publicados), HashiCorp/antonbabenko/Terramate (Terraform), Pulumi (agent-skills oficiales). La estrategia correcta es importar + adaptar, con la precaución de seguridad R4 de la auditoría: leer completa toda skill de terceros antes de instalarla. (Docs 01 y 05.)

**Hallazgo B4 — En nube, el patrón empresarial es "biblioteca de skills por proveedor":**
Una skill-biblioteca por cloud (AWS/Azure/GCP) que codifica defaults de seguridad, naming, cost tagging y servicios aprobados; cambiar de contexto = cambiar de skill, no reescribir prompts. Y las skills se versionan en git junto a la infraestructura que describen (documentación viva). (Doc 04.)

**Hallazgo B5 — Los MCPs de datos multiplican a las skills, pero el anti-patrón 3 sigue vigente:**
Existe oferta abundante (MCP Toolbox de Google, portafolio oficial de AWS, Snowflake managed MCP, dbt-core MCP). Conectarlos todos "por si acaso" repite el anti-patrón 3 del doc 06 (overhead de esquemas). La regla: cada skill declara en "Requisitos" qué MCP necesita y su fallback, como ya exige `_template/SKILL.md`. (Docs 02–04.)

**Hallazgo B6 — Las skills de datos necesitan validación distinta a las de código:**
En software, los tests dicen si algo se rompió; en datos, un modelo puede correr, una query devolver filas y una migración aplicar con éxito mientras el *significado* de los datos se corrompió silenciosamente. Las skills de este dominio deben incluir criterios de verificación semántica (paridad de datos, conteos, lineage), no solo "compila". (Docs 02 y 03.)

### Decisión consolidada (adelanto del doc 05)

Empezar por 2–3 skills de `shared/` (metodología pura, cero dependencias, máximo retorno), pilotear la importación de una colección externa (Altimate si el stack incluye dbt; terraform-skill para IaC), y solo entonces añadir skills de `claude-code/` que dependan de MCPs locales — respetando el orden de fases de la serie principal (las skills de esta subserie no requieren la Fase 3/Graphiti para funcionar).

---

*Siguiente: [Estrategias de Uso con Claude](./01-ESTRATEGIAS-DE-USO-CON-CLAUDE.md)*