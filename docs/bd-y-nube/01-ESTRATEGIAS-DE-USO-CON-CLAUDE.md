# Estrategias de Uso con Claude
## Cinco estrategias para skills de bases de datos, big data y nube

> **Fecha:** Julio 2026
> **Método:** Investigación web sobre el ecosistema de Agent Skills (colecciones open-source, posts de proveedores, guías de práctica), cruzada contra las reglas ya establecidas en `setup/skills/README.md`, el `_template/SKILL.md` y los anti-patrones del doc 06.
> **Resultado:** 5 estrategias que estructuran los docs 02–04 y el catálogo del doc 05.

---

## Estrategia 1 — Skills como estándares propios, no como enciclopedias de dominio

La evidencia externa coincide con el hallazgo H4 de la serie principal: el valor no está en enseñarle SQL o Terraform a Claude (ya los conoce), sino en codificar **las convenciones que Claude no puede adivinar**. Las convenciones de bases de datos varían enormemente entre equipos; una skill que conoce el motor concreto, el naming, la estrategia de indexado y la herramienta de migraciones del proyecto produce resultados dramáticamente mejores que una que asume SQL genérico.

Aplicación en este repo:

- Cada skill de dominio empieza con una sección "Convenciones de este setup" (motor, dialecto, naming, herramienta de migraciones, proveedor de nube por defecto).
- La teoría extensa (guías de normalización, catálogos de patrones) va en `references/*.md` junto al SKILL.md — progressive disclosure, igual que la regla 3 del sistema de skills.
- El cuerpo se mantiene < 500 palabras (regla vigente del sistema).

**Por qué es la estrategia base:** es la única que no depende de MCPs, Docker ni de la Fase 3. Skills de pura metodología viven en `shared/` y sirven a Claude Code y Cowork desde el día uno.

---

## Estrategia 2 — El trío Skills + MCP + Hooks

El patrón que emerge como arquitectura estándar en el stack de datos moderno divide responsabilidades en tres mecanismos:

| Mecanismo | Rol | Ejemplos en el dominio |
|-----------|-----|------------------------|
| **MCP servers** | Conectar en tiempo real | Postgres/warehouse para validar queries, catálogo de metadata para lineage, orquestador |
| **Skills** | Codificar best practices que Claude sigue solo | Patrones de modelado dbt, estrategias de testing, guías de migración |
| **Hooks** | Garantizar (determinista) | Lint de SQL al guardar, pytest antes de commit, bloquear apply sin plan |

Un flujo real documentado del ecosistema: Claude Code genera modelos dbt en todas las capas siguiendo las prácticas del proyecto, produciendo en paralelo schema YAMLs, descripciones de columnas y tests, y validando los modelos intermedios **en vivo** contra PostgreSQL vía MCP.

Aplicación en este repo: es la extensión natural de lo que ya existe. El hook `validate-graphiti-group-id.py` demuestra el principio (*"las instrucciones son probabilísticas; los hooks son garantía"* — R2 de la auditoría). Las skills de datos de mayor riesgo (migraciones, apply de infraestructura) deben nacer con su hook de enforcement, no confiar solo en el texto de la skill.

---

## Estrategia 3 — Importar colecciones open-source probadas antes de escribir desde cero

El ecosistema ya produjo colecciones con resultados medidos:

| Colección | Dominio | Evidencia |
|-----------|---------|-----------|
| **Altimate Skills** (`AltimateAI/data-engineering-skills`) | dbt, Snowflake, SQL review/translate, paridad de datos, migraciones, costos, PII | Reportan +22% de velocidad de ejecución en SQL optimizado (TPC-H 1TB) con 100% de equivalencia lógica, y 53% en ADE-bench (43 tareas dbt reales). Instalable como plugin de marketplace. |
| **terraform-skill** (antonbabenko) | Terraform/OpenTofu: testing, módulos, CI/CD, patrones de producción | Skill comunitaria con frameworks de decisión ("cuándo y por qué", no solo "qué"); compatible con el estándar abierto Agent Skills |
| **Terramate agent-skills** | IaC: state splitting, drift, CI/CD | 37 reglas en 10 categorías priorizadas por impacto |
| **devops-skills** (fork con foco infra) | Terraform + AWS safety-first | terraform-plan-review con análisis de agentes en paralelo antes de cualquier apply, drift detection, cirugía segura de state |
| **Pulumi agent-skills** | Pulumi, migración desde Terraform/CDK/CFN | Repo oficial del proveedor; skills de ESC (secrets/config) y best practices |

Precaución obligatoria (R4 de la auditoría del repo): **toda skill que entre a `claude-skills/` se convierte en instrucciones auto-cargadas en todas las laptops.** Nunca importar una colección sin leerla completa; versionarla en git y revisar `git diff` ante cambios no reconocidos. El doc 05 define el protocolo de importación.

---

## Estrategia 4 — Bibliotecas de skills por proveedor de nube

El patrón empresarial consolidado en 2026: una biblioteca de skills por cloud (una para AWS, una para Azure, una para GCP), cada una codificando los defaults de seguridad del proveedor, reglas de naming de recursos, estándares de cost tagging y lista de servicios aprobados. Cambiar de contexto = intercambiar skills, no reescribir prompts.

Segundo componente del patrón: las skills se versionan en git **junto a la infraestructura que describen** — cuando se añade un módulo al monorepo de Terraform, la skill se actualiza en el mismo PR. Las skills se vuelven documentación viva sobre la que Claude puede actuar. Es la misma filosofía "el vault es la copia canónica" (R5) aplicada a infraestructura.

Aplicación en este repo: no crear una mega-skill "cloud", sino `aws-standards/`, `gcp-standards/`... solo para los proveedores realmente usados, cada una mínima y con su `references/`.

---

## Estrategia 5 — MCPs de datos con disciplina (anti-patrón 3 vigente)

La oferta de MCPs para el dominio es abundante (detalle por área en docs 02–04): MCP Toolbox de Google (multi-motor, open source), portafolio oficial de AWS por servicio de datos, Snowflake managed MCP con Cortex, MCP de dbt-core con lineage a nivel columna. La tentación de conectarlos todos repite el anti-patrón 3 del doc 06: 150,000–300,000 tokens de overhead de esquemas por conectar MCPs "por si acaso".

Reglas para esta subserie:

1. Un MCP se conecta cuando una skill concreta lo requiere para la sesión actual — no antes.
2. Toda skill que dependa de un MCP lo declara en "Requisitos" **con fallback** (regla 3 del `_template`): así la misma skill funciona en Cowork sin el MCP local.
3. Preferir MCPs read-only para exploración; el modo write de un MCP de warehouse es equivalente a darle DDL a un agente — solo con hook de enforcement.
4. El puente Cowork↔MCP local sigue siendo el del `cowork-y-multiagente/08` (desktop app); las skills de `cowork/` no pueden asumir localhost.

---

## Cómo se relacionan las estrategias

```
Estrategia 1 (estándares propios)      ← base, sin dependencias  → carpeta shared/
Estrategia 3 (importar colecciones)    ← acelera la 1            → protocolo doc 05
Estrategia 4 (biblioteca por cloud)    ← caso particular de la 1 → doc 04
Estrategia 2 (trío skill+MCP+hook)     ← eleva garantías          → skills de riesgo alto
Estrategia 5 (disciplina MCP)          ← limita el costo de la 2  → regla transversal
```

---

## Fuentes

| Fuente | Qué sustenta |
|--------|--------------|
| [Best Claude Code Skills for Data Engineering (Agensi)](https://www.agensi.io/learn/best-claude-code-skills-data-engineering) | Estrategia 1: convenciones > genérico; capas de validación de datos |
| [We Created Data Engineering Skills for Claude Code (Altimate)](https://www.altimate.ai/blog/we-created-data-engineering-skills-for-claude-code) | Estrategia 3: cobertura de skills de datos más allá del SQL |
| [Altimate Skills — anuncio y benchmarks](https://blog.altimate.ai/teaching-claude-code-the-art-of-data-engineering-introducing-altimate-skills) | Estrategia 3: métricas TPC-H y ADE-bench, instalación por marketplace |
| [Intro a Claude Code para Data Engineers (The Pipe & The Line)](https://thepipeandtheline.substack.com/p/intro-claude-code-for-data-engineers) | Estrategia 2: definición del trío MCP/Skills/Hooks en el stack de datos |
| [Data Modeling con dbt + Postgres MCP (The Pipe & The Line)](https://thepipeandtheline.substack.com/p/claude-code-for-data-engineers-data-modeling-dbt-miro-postgresql-skills-mcp) | Estrategia 2: flujo real skills + MCP de validación |
| [Agent Skills para SRE/DevOps 2026 (yisusvii)](https://yisusvii.github.io/posts/claude-code-codex-skills-devops-sre-cloud-2026/) | Estrategia 4: bibliotecas por proveedor, skills como documentación viva |
| [devops-skills (lgbarn)](https://github.com/lgbarn/devops-skills) · [terraform-skill (antonbabenko)](https://github.com/antonbabenko/terraform-skill) · [Terramate agent-skills](https://github.com/terramate-io/agent-skills) · [Pulumi blog](https://www.pulumi.com/blog/top-8-claude-skills-devops-2026/) | Estrategia 3: colecciones IaC disponibles |
| [10 MCP servers para bases de datos (InfoWorld)](https://www.infoworld.com/article/4181843/10-mcp-servers-to-connect-llms-with-databases.html) · [MCP Toolbox (googleapis)](https://github.com/googleapis/mcp-toolbox) | Estrategia 5: oferta de MCPs de datos |

---

*Siguiente: [Skills de Bases de Datos](./02-SKILLS-BASES-DE-DATOS.md)*