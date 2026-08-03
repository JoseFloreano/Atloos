# Skills de Nube e IaC
## Terraform/OpenTofu, bibliotecas por proveedor y prácticas safety-first

> **Fecha:** Julio 2026
> **Alcance:** Skills para infraestructura como código y operación en nube (AWS/Azure/GCP), con foco en las garantías de seguridad — la capa donde un error del agente cuesta dinero o downtime reales.
> **Estrategias aplicadas:** 3 (importar colecciones), 4 (biblioteca por proveedor), 2 (hooks de garantía).

---

## 1. El diagnóstico del ecosistema

La crítica compartida por todas las fuentes: la IA genérica genera infraestructura que funciona hoy y se rompe mañana — el código compila, aplica, y seis meses después es monolítico, inseguro, intestable e imposible de refactorizar. Las skills existen precisamente para convertir a Claude de "ingeniero que conoce la sintaxis de Terraform" en "arquitecto que ha visto lo que sale mal en producción".

El resumen conceptual más útil: las skills son **conocimiento procedural** — un SOP (procedimiento operativo estándar) en `.claude/skills/` — a diferencia de los Projects (contexto estático) y los system prompts (siempre activos, consumen tokens). Empaquetada como skill, la infraestructura gana tres propiedades: *recuerda la seguridad* (no destruye recursos sin plan), *mantiene estándares* (no olvida cifrado ni tags) y *se auto-corrige* (corre `terraform validate` automáticamente).

---

## 2. Colecciones IaC disponibles (estrategia 3)

| Colección | Qué aporta | Estado |
|-----------|-----------|--------|
| **hashicorp/agent-skills** | Skills oficiales de HashiCorp para Terraform; base del "top 15" difundido en la comunidad | Oficial del proveedor |
| **antonbabenko/terraform-skill** | Testing, estructura de módulos, CI/CD, patrones de producción; frameworks de decisión ("cuándo y por qué"); integración opcional con terraform-ls; reglas concretas como "para renombrar un recurso usa `moved` block, no reemplazo de texto" | Comunidad madura, multi-agente (estándar Agent Skills) |
| **terramate-io/agent-skills** | 37 reglas en 10 categorías priorizadas por impacto: state splitting con stacks, testing, módulos, CI/CD, reconciliación de drift | Del proveedor Terramate |
| **lgbarn/devops-skills** | Safety-first para Terraform/OpenTofu + AWS: `terraform-plan-review` (análisis con agentes en paralelo **antes de cualquier apply**), `terraform-drift-detection`, `terraform-state-operations` (cirugía segura de state) | Fork comunitario con foco infra |
| **pulumi/agent-skills** | ComponentResource, Automation API, migración desde Terraform/CDK/CloudFormation/ARM, `pulumi-esc` (secrets/config con OIDC y stores externos) | Oficial de Pulumi |

Criterio de selección para este repo: si el IaC es Terraform/OpenTofu, la combinación mínima es **terraform-skill (base) + plan-review de devops-skills (garantía)**. Pulumi solo si se usa Pulumi. Todo pasa por el protocolo de importación del doc 05 (leer completa, versionar en git, revisar diffs — R4).

---

## 3. La skill-biblioteca por proveedor (estrategia 4)

El patrón empresarial consolidado: una biblioteca de skills por cloud, cada una codificando **defaults de seguridad del proveedor, reglas de naming de recursos, estándares de cost tagging y lista de servicios aprobados**. Los ingenieros cambian de contexto intercambiando skills, no reescribiendo prompts.

Plantilla de contenido para `<provider>-standards/SKILL.md` (aplicar solo a los proveedores en uso real):

1. **Identidad y acceso**: patrón de roles/OIDC por defecto; prohibición de credenciales estáticas en código (coherente con el anti-patrón 5 del doc 06: credenciales jamás en git/OneDrive).
2. **Naming y tagging**: convención de nombres de recursos; tags obligatorios (`project`, `env`, `owner`, `cost-center`).
3. **Defaults de seguridad**: cifrado en reposo activado, redes privadas por defecto, logging habilitado.
4. **Servicios aprobados**: lista corta; todo lo demás requiere justificación explícita en la respuesta.
5. **Costo**: instancias/clases por defecto para dev; regla de "estimar antes de crear" para recursos facturados por hora.

La regla complementaria del patrón: **las skills se versionan en git junto a la infraestructura que describen** — módulo nuevo en el monorepo ⇒ skill actualizada en el mismo PR. La skill se vuelve documentación viva sobre la que Claude puede actuar.

---

## 4. Safety-first: dónde son obligatorios los hooks (estrategia 2)

La infraestructura es la capa donde el texto de una skill no basta como garantía. Mapa mínimo:

| Regla de la skill | Hook que la garantiza |
|-------------------|----------------------|
| "Nunca `apply` sin plan revisado" | PreToolUse: bloquear `terraform apply` si no existe artefacto de plan-review reciente |
| "Nunca `destroy` sin confirmación explícita del usuario" | PreToolUse: bloquear `destroy`/`state rm` salvo flag manual |
| "Validate + fmt siempre" | PostToolUse: correr `terraform fmt -check && terraform validate` tras editar `.tf` |
| "Sin secretos en `.tf`/tfvars versionados" | PreToolUse/pre-commit: scan de patrones de credenciales |

Nota de alcance: el modo headless (Claude Code agendado o disparado por webhooks de alertas, con la skill como runbook) existe en el ecosistema SRE 2026, pero queda **fuera del alcance** de esta subserie — contradiría el espíritu de las garantías anteriores adoptarlo antes de que los hooks estén probados.

---

## 5. Nube más allá de IaC

Dos piezas complementarias, ambas de bajo esfuerzo:

- **`cloud-architecture-review`** (`cowork/`): comparativas de servicios y decisiones de arquitectura con web research y documentos como entregable — trabajo de investigación, no de toolchain, exactamente la división del `cowork-y-multiagente/08` (Code toca la máquina; Cowork investiga y redacta).
- **Inventario de assets vía MCP** (opcional): CloudQuery expone el inventario de assets cloud por MCP (modos CLI/PostgreSQL/Snowflake) para consultarlo en lenguaje natural. Útil para auditorías; conectar solo en sesiones de auditoría (estrategia 5).

---

## 6. Ubicación en el sistema de skills del repo

| Skill | Carpeta | Nota |
|-------|---------|------|
| `<provider>-standards` (una por proveedor usado) | `shared/` | Convenciones puras; sirven también para revisar docs/propuestas en Cowork |
| `terraform-safe-apply` (importada + adaptada) | `claude-code/` | Ejecuta toolchain local; pareja obligada de sus hooks |
| `terraform-module-author` | `claude-code/` | Estructura de módulos, testing, CI/CD |
| `cloud-architecture-review` | `cowork/` | Web research + documentos |
| `cloud-cost-tagger` | `shared/` | Naming/tagging multi-cloud, aplicable desde cualquier superficie |

---

## Fuentes

| Fuente | Qué sustenta |
|--------|--------------|
| [Top 15 Claude Code Skills para Terraform (Medium)](https://medium.com/@jdiegobonp/the-top-15-claude-code-skills-every-terraform-developer-should-be-using-1a0f6abf0aa7) | §1: diagnóstico "funciona hoy, se rompe mañana"; referencia a hashicorp/agent-skills |
| [Guía de skill Terraform (LAXIMA)](https://laxima.tech/blog/building-the-ultimate-terraform-skill-for-claude-code-a-devops-guide) | §1: skills como conocimiento procedural/SOP; propiedades de seguridad; campo `allowed-tools` |
| [terraform-skill (antonbabenko)](https://github.com/antonbabenko/terraform-skill) | §2: contenido, frameworks de decisión, regla del `moved` block |
| [Terramate agent-skills](https://github.com/terramate-io/agent-skills) | §2: 37 reglas / 10 categorías |
| [devops-skills (lgbarn)](https://github.com/lgbarn/devops-skills) | §2, §4: plan-review paralelo pre-apply, drift, state ops |
| [Pulumi — Claude Skills para DevOps](https://www.pulumi.com/blog/top-8-claude-skills-devops-2026/) | §2: pulumi/agent-skills, pulumi-esc |
| [Agent Skills para SRE/DevOps 2026 (yisusvii)](https://yisusvii.github.io/posts/claude-code-codex-skills-devops-sre-cloud-2026/) | §3: bibliotecas por proveedor, skills en el mismo PR, modo headless |
| [CloudQuery MCP Server](https://www.cloudquery.io/docs/platform/features/mcp-server) | §5: inventario de assets vía MCP |

---

*Siguiente: [Catálogo Propuesto y Plan de Implementación](./05-CATALOGO-Y-PLAN-DE-IMPLEMENTACION.md)*