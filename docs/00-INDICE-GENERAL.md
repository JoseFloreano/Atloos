# Índice General de la Documentación

> Los docs están organizados en subseries temáticas. La numeración original
> (doc 00–12) se conserva en los nombres de archivo — las referencias tipo
> "doc 09" o "hallazgo H4" en el texto siguen siendo válidas.

## Subseries

### 📁 [`arquitectura-memoria/`](./arquitectura-memoria/) — La investigación fundacional (docs 00–07)

La serie original: por qué esta arquitectura de memoria y no otra.

| Doc | Tema |
|-----|------|
| [00 · Índice y resumen ejecutivo](./arquitectura-memoria/00-INDICE-Y-RESUMEN-EJECUTIVO.md) | Visión general y hallazgos |
| [01 · Obsidian como memoria externa](./arquitectura-memoria/01-OBSIDIAN-MEMORIA-EXTERNA.md) | Vault, plugins, MCP |
| [02 · Grafos vs Markdown](./arquitectura-memoria/02-GRAFOS-VS-MARKDOWN.md) | Benchmarks honestos, cuándo cada uno |
| [03 · Graphiti + FalkorDB](./arquitectura-memoria/03-GRAPHITI-FALKORDB-MEMORIA-TEMPORAL.md) | Memoria temporal (pospuesto — ver setup/README) |
| [04 · OneDrive multi-laptop](./arquitectura-memoria/04-ONEDRIVE-SINCRONIZACION-MULTI-LAPTOP.md) | Estrategias A/B/C de sync |
| [05 · Skills y frameworks agénticos](./arquitectura-memoria/05-SKILLS-FRAMEWORKS-AGENTICOS.md) | Superpowers, Graphify, MCPs |
| [06 · Arquitectura final](./arquitectura-memoria/06-ARQUITECTURA-FINAL-RECOMENDADA.md) | Decisión consolidada y fases |
| [07 · Hallazgos críticos H1–H10](./arquitectura-memoria/07-HALLAZGOS-CRITICOS-REFERENCIA-RAPIDA.md) | ⭐ Leer antes de cualquier decisión |

### 📁 [`cowork-y-multiagente/`](./cowork-y-multiagente/) — Los dos productos y su convivencia

| Doc | Tema |
|-----|------|
| [08 · Cowork vs Claude Code](./cowork-y-multiagente/08-COWORK-VS-CLAUDE-CODE.md) | En qué es mejor cada uno; setup compartido |
| [12 · Vault con agentes concurrentes](./cowork-y-multiagente/12-VAULT-CONCURRENCIA-MULTIAGENTE.md) | El misterio de las "copias", patrones seguros |

### 📁 [`auditoria/`](./auditoria/) — Salud del setup

| Doc | Tema |
|-----|------|
| [09 · Auditoría del setup](./auditoria/09-AUDITORIA-SETUP.md) | Fortalezas, riesgos, matriz y mitigaciones (aplicadas) |

### 📁 [`skills/`](./skills/) — Catálogos de skills investigados

| Doc | Tema |
|-----|------|
| [10 · Diseño y desarrollo](./skills/10-SKILLS-DISENO-Y-DESARROLLO.md) | Seguridad, council, BD, diseño + **protocolo de auditoría §2** ⭐ |
| [11 · Testing y debugging](./skills/11-SKILLS-TESTING-Y-DEBUGGING.md) | Qué adoptar, qué duplica Superpowers, backlog propio |
| [13 · IA agéntica](./skills/13-SKILLS-IA-AGENTICA.md) | Diseño agéntico, tokens, meta-skills, benchmarks de modelos + 5 skills propias |
| [15 · APIs y despliegue](./skills/15-SKILLS-APIS-Y-DESPLIEGUE.md) | api-design, api-evolution (oasdiff) y deploy-planner con cuestionario |
| [16 · Python: clases, desarrollo y API design](./skills/16-SKILLS-PYTHON-Y-DESARROLLO.md) | python-conventions, python-api-design + plugin astral (uv/ruff/ty) |

### 📁 [`ecosistema/`](./ecosistema/) — Evaluaciones de herramientas externas

| Doc | Tema |
|-----|------|
| [14 · Hermes y OpenClaw](./ecosistema/14-HERMES-Y-OPENCLAW.md) | ¿Aditivos o estorbo? Veredicto: no adoptar hoy; criterios de re-evaluación |

### 📁 [`bd-y-nube/`](./bd-y-nube/) — Subserie de datos e infraestructura

| Doc | Tema |
|-----|------|
| [00 · Índice de la subserie](./bd-y-nube/00-INDICE-Y-RESUMEN-EJECUTIVO.md) | Alcance y capas del dominio |
| [01 · Estrategias de uso con Claude](./bd-y-nube/01-ESTRATEGIAS-DE-USO-CON-CLAUDE.md) | Las 5 estrategias (docs 02–05 pendientes) |

## Convenciones

- **Subserie nueva** = carpeta kebab-case con su propio `00-INDICE-*.md` (el patrón lo fijó `bd-y-nube/`).
- Los docs referencian entre sí por número ("doc 09", "H4") — estable ante movimientos de carpeta.
- Docs temporales (reportes de bugs, notas de instalación) no entran a las subseries: se cosechan a donde corresponda y se retiran (precedente: el reporte de bugfixes de la instalación single-laptop).
