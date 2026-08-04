# Índice General de la Documentación

> Los docs están organizados en subseries temáticas. La numeración original
> (doc 00–12) se conserva en los nombres de archivo — las referencias tipo
> "doc 09" o "hallazgo H4" en el texto siguen siendo válidas.

## Subseries

### 📁 [`arquitectura-memoria/`](./arquitectura-memoria/) — La investigación fundacional (docs 00–11)

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
| [08 · Graphiti con DeepSeek: costo](./arquitectura-memoria/08-GRAPHITI-DEEPSEEK-COSTO.md) | Extracción barata cuando Graphiti se active |
| [08b · Resumen funcional DeepSeek](./arquitectura-memoria/08b-RESUMEN-FUNCIONAL-DEEPSEEK.md) | Complemento operativo del 08 |
| ~~09 · Higiene de contexto y ciclo de vida del vault~~ | ✅ **Implementado, auditado y cosechado** (2026-08-01) → la decisión vive en `ADR-20260801-higiene-vault` del vault. Tope de `_PROJECT.md`, índice de ADRs, ciclo de los RFDs |
| [RFD 10 · Graphiti + FalkorDB: errores de integración](./arquitectura-memoria/10-RFD-GRAPHITI-INTEGRACION-ERRORES.md) | 🔵 **Draft** — 8 errores encontrados y propuesta de solución con skills en vez de MCP HTTP |
| [11 · Graphiti: guía rápida de setup](./arquitectura-memoria/11-GRAPHITI-SETUP-GUIA-RAPIDA.md) | DeepSeek + Ollama; deriva del RFD 10 |

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
| [16 · Ahorro de tokens robado de ambos](./ecosistema/16-AHORRO-TOKENS-ROBADO-DE-HERMES-OPENCLAW.md) | Mecanismos minados de sus docs; fuente de R1/R5 (implementados) |

### 📁 [`bd-y-nube/`](./bd-y-nube/) — Subserie de datos e infraestructura

| Doc | Tema |
|-----|------|
| [00 · Índice de la subserie](./bd-y-nube/00-INDICE-Y-RESUMEN-EJECUTIVO.md) | Alcance y capas del dominio |
| [01 · Estrategias de uso con Claude](./bd-y-nube/01-ESTRATEGIAS-DE-USO-CON-CLAUDE.md) | Las 5 estrategias que estructuran la subserie |
| [02 · Skills de bases de datos](./bd-y-nube/02-SKILLS-BASES-DE-DATOS.md) | SQL, esquemas, migraciones, calidad, MCPs de DB |
| [03 · Skills de big data](./bd-y-nube/03-SKILLS-BIG-DATA.md) | dbt, Spark, warehouses, lineage, costos, PII |
| [04 · Skills de nube e IaC](./bd-y-nube/04-SKILLS-NUBE-E-IAC.md) | Terraform/OpenTofu, bibliotecas por proveedor, safety-first |
| [05 · Catálogo y plan de implementación](./bd-y-nube/05-CATALOGO-Y-PLAN-DE-IMPLEMENTACION.md) | Fases S0–S3, protocolo de importación, anti-patrones |
| [06 · Auditoría adversarial de las skills](./bd-y-nube/06-AUDITORIA-ADVERSARIAL-SKILLS.md) | Correcciones aplicadas y crítica a la investigación de origen |

### 📁 [`telegram/`](./telegram/) — El puente Telegram (T0–T5)

La línea de trabajo activa. Los RFDs llevan su estado en la cabecera Y aquí.

| Doc | Estado | Tema |
|-----|--------|------|
| [00 · Diseño del puente](./telegram/00-DISENO-TELEGRAM-BRIDGE.md) | Implementado (T0–T3) | Diseño original; lo vigente vive en los ADRs del vault (ver abajo) y en los RFDs 03 y 06 |
| [01 · Mini PC servidor 24/7](./telegram/01-MINIPC-SERVIDOR-24-7.md) | Cerrado | Investigación de compra (Beelink SER8) |
| ~~02 · RFD T2: modo escritura~~ | ✅ **Implementado, auditado y cosechado** (2026-08-01) → `ADR-20260801-puente-telegram`, sección «Modo escritura (T2)». Las 4 condiciones (A1/A2/A3 + pasada manual) cerradas | Worktrees, permisos ortogonales, merge con botón y verde |
| [03 · RFD T5: desarrollo paralelo](./telegram/03-RFD-T5-DESARROLLO-PARALELO.md) | Idea registrada | Multi-proyecto en vuelo (antes T4) |
| ~~04 · RFD: progreso en vivo~~ | ✅ **Implementado, auditado y cosechado** (2026-08-01) → `ADR-20260801-puente-telegram`, sección «Progreso en vivo» | Panel, alertas proactivas, stream-json |
| ~~05 · RFD T3: memoria y tokens~~ | ✅ **Implementado, auditado y cosechado** (2026-08-01) → `ADR-20260801-bot-memoria-y-perfil` (ADR nuevo) | vaultio, perfil bot de skills, E1/E3 refutados |
| [06 · RFD T4: continuar desde aviso](./telegram/06-RFD-T4-CONTINUAR-DESDE-AVISO.md) | Idea validada (3 huecos anotados) | /pickup con traspaso de contexto |

### 📁 [`subagentes/`](./subagentes/) — Workstreams paralelos con rama y worktree por frente

| Doc | Tema |
|-----|------|
| [00 · Índice y resumen ejecutivo](./subagentes/00-INDICE-Y-RESUMEN-EJECUTIVO.md) | Hallazgos S1–S5: el mecanismo ya existe en 4 capas |
| [01 · Mecanismos nativos y externos](./subagentes/01-MECANISMOS-NATIVOS-Y-EXTERNOS.md) | `--worktree`, Agent Teams, Superpowers instalado, plugin wshobson |
| [02 · Patrón propuesto y riesgos](./subagentes/02-PATRON-PROPUESTO-Y-RIESGOS.md) | Flujo en 4 pasos, gate de merge, costo y riesgos |
| [03 · Skills propuestas](./subagentes/03-SKILLS-PROPUESTAS.md) | `workstream-merge-gate`, `workstream-memory-briefing`, plan de adopción |
| [04 · RFD de adopción](./subagentes/04-RFD-ADOPCION-WORKSTREAMS.md) | ⭐ La ruta: fases W0–W3 con gates, dónde vive el gate de merge |

## Convenciones

- **Qué vive en `docs/`**: material cerrado y refinado, **y** RFDs en vuelo. El
  marcador de estado es la CABECERA del doc y la columna de estado de este
  índice — no la ubicación. El ciclo de cosecha (skill `design-doc-harvest`,
  precedente: RFD 09 → `ADR-20260801-higiene-vault`) retira los RFDs cuando
  quedan implementados y con auditoría cerrada.
- **Las skills viven en `setup/skills/` del repo**, fuente única desde el 08-03
  (`ADR-20260803-skills-fuente-unica`). Los docs anteriores dicen
  `claude-skills/`: es la carpeta de OneDrive ya retirada.
- **Subserie nueva** = carpeta kebab-case con su propio `00-INDICE-*.md` (el patrón lo fijó `bd-y-nube/`).
- **Citas entre docs: por RUTA** (`skills/10 §2`, `telegram/02 C4`), no por
  número a secas — hay números duplicados entre subseries (08, 10, 11, 16) y
  "doc 10" es ambiguo. El número del nombre de archivo es orden de lectura
  dentro de su carpeta, no identificador global. Los hallazgos H1–H10 sí son
  identificadores globales (viven en `arquitectura-memoria/07`).
- Docs temporales (reportes de bugs, notas de instalación) no entran a las subseries: se cosechan a donde corresponda y se retiran (precedente: el reporte de bugfixes de la instalación single-laptop).
