# Skills de IA Agéntica: Investigación, Comparativa y Skills Propias
## Diseño de sistemas agénticos, optimización de tokens, meta-skills y benchmarks de modelos

> **Fecha:** Julio 2026
> **Método:** 4 líneas de investigación paralelas sobre fuentes primarias (repos clonados/fetcheados, docs oficiales de Anthropic, leaderboards vivos). Análisis comparativo por categoría y — donde la investigación confirmó huecos — **4 skills propias ya creadas** adaptadas al setup (§6).
> Aplica el protocolo de auditoría (`skills/10` §2) antes de instalar cualquier tercero de esta lista.

---

## 1. Resumen ejecutivo

| Categoría | Mejor opción externa | Veredicto | Skill propia creada |
|-----------|---------------------|-----------|---------------------|
| Diseño de sistemas agénticos | wshobson `agent-teams` (6 skills, MIT, activo) | Adoptar como plugin | ⭐ `agentic-system-design` — **nadie empaquetó los patrones canónicos de Anthropic**; la nuestra lo hace + reglas del setup |
| Optimización de tokens | alexgreensh/token-optimizer (el más completo) | ⚠️ NO adoptar: licencia PolyForm **Noncommercial** | ⭐ `token-audit` — nuestra vara son los presupuestos H3/H4 propios, medidos con ccusage//cost |
| Crear skills (meta) | `skill-creator` oficial de Anthropic + `writing-skills` de Superpowers (ya instalado) | Adoptar skill-creator en Code | ⭐ `skill-forge` — envuelve las prácticas oficiales con NUESTRAS convenciones (carpetas, sync, auditoría) |
| Benchmarks modelos/proveedores | **No existe ninguna skill mantenida** (hueco confirmado) | — | ⭐ `model-benchmark` — costo-por-tarea con fuentes vivas |
| Automatizaciones (n8n) | czlonkowski/n8n-skills (MIT, con evals) | Adoptar SOLO si usas n8n | — |
| Context engineering (teoría) | muratcankoylan/Agent-Skills-for-Context-Engineering (15 skills, MIT) | Cantera educativa, no instalar en bloque | — |

**Los dos hallazgos estructurales:** (1) los patrones de "Building Effective Agents" — el documento más citado del campo — no existen como skill en ningún repo verificado: gap que nuestra skill llena; (2) en benchmarking de modelos no hay skills porque el conocimiento caduca en semanas — la solución correcta es una skill de *metodología + fuentes vivas*, nunca una de datos.

---

## 2. Diseño de sistemas agénticos — comparativa

| Opción | Qué trae | Formato/Licencia | Veredicto |
|--------|----------|------------------|-----------|
| **wshobson `agent-teams`** ⭐ | 6 SKILL.md de calidad: team-composition (heurísticas 1-5 agentes), task-coordination, communication-protocols, multi-reviewer, parallel-debugging, parallel-feature-development + comandos `/team-*` | Plugin MIT, commit jul-2026; requiere `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | **Adoptar como plugin** cuando uses Agent Teams; es la mejor pieza del nicho |
| ECC (affaan-m) | `team-agent-orchestration`, `agent-architecture-audit`, `autonomous-agent-harness`, `agentic-engineering` | MIT, muy activo, 279 skills heterogéneas | Cantera: piezas buenas, auditar duro; `agent-architecture-audit` es la más interesante para revisar automatizaciones ya construidas |
| Superpowers (ya instalado) | `dispatching-parallel-agents`, `subagent-driven-development` | — | Ya cubre el "cuándo fan-out" básico — nuestra skill NO lo duplica: cubre el nivel de arquitectura |
| anthropics/skills | Nada de multi-agente | — | N/A |
| Docs oficiales Agent Teams | Subagents vs Teams, límites (3-5 miembros, file-ownership, plan approval) | code.claude.com/docs | Fuente de nuestra skill |

**Gap confirmado:** grep sobre los clones de wshobson, ECC y anthropics/skills — cero empaquetados de prompt-chaining/routing/parallelization/orchestrator-workers/evaluator-optimizer. Nuestra `agentic-system-design` los trae como *escalera de decisión* (el patrón más simple que funcione) + reglas del setup (dónde corre qué, costo primero, R2).

Para n8n: `czlonkowski/n8n-skills` (autor de n8n-mcp, MIT, con carpeta `evaluations/` — rareza valiosa) es la elección si algún día montas automatizaciones n8n; hasta entonces, no instalar. Zapier/Make: sin skills mantenidas.

## 3. Optimización de tokens — comparativa

| Opción | Qué trae | Problema | Veredicto |
|--------|----------|----------|-----------|
| alexgreensh/token-optimizer | Lo más completo: auditoría 6-agentes de CLAUDE.md/MCPs/skills/settings, `measure.py`, 16 fixes | **PolyForm Noncommercial 1.0.0** — incompatible con trabajo comercial | No adoptar; leer como referencia de técnica |
| hamzafarooq/token-optimizer | El origen del benchmark H4 (3,847→312 = 91.9%); trae skill + benchmark.py | 1 estrella, 3 commits — demo abandonada | No adoptar; rescatar la idea de `.claudeignore` (85.5% de ahorro reportado) |
| ECC continuous-learning-v2 | Aprendizaje "instinct-based" vía hooks con confidence scores | Complejo, hooks-pesado, estilo propio | Observar; no adoptar aún |
| muratcankoylan (15 skills) | Empaquetado educativo de la doctrina oficial de context engineering | Educativo más que operativo | Destilado a nuestra skill `context-engineering` (§6) — las 15 quedan como lectura de profundización |

**Nuestra respuesta:** `token-audit` (creada) — pequeña, operativa, con la vara de NUESTROS presupuestos ya investigados (H3, H4, límites del `skills/10` §8.3) y medición real (`/context`, `/cost`, ccusage — v18, 14.2k stars, MIT, el estándar de facto para gasto local). Medir → recortar → re-medir, nunca estimar.

## 4. Meta-skills (crear/evaluar skills) — comparativa

| Opción | Qué trae | Veredicto |
|--------|----------|-----------|
| `skill-creator` (Anthropic, oficial) ⭐ | Proceso completo: entrevista → SKILL.md → **evals con agentes de contexto limpio, comparadores A/B ciegos, benchmark con análisis de varianza**, optimizador de descripciones (mejoró triggering en 5/6 skills públicas según el blog oficial) | **Adoptar en Claude Code** (en Cowork ya viene). Es LA herramienta de evals |
| `writing-skills` (Superpowers — ya instalado) | TDD para docs: observa cómo falla el agente SIN la skill, escribe lo mínimo que corrige. Hallazgo clave: **la descripción dice cuándo, jamás resume el cómo** (si resume, el agente sigue el atajo y no lee la skill) | Ya lo tienes; su hallazgo quedó embebido en `skill-forge` |
| Spec oficial Agent Skills | agentskills.io + `spec/agent-skills-spec.md` — el estándar abierto (frontmatter mínimo, discovery/activation/execution) | Referencia; nuestro `_template` ya cumple |
| MLflow skill evals | Tracing de ejecuciones headless + LLM judges + auto-refinamiento | Para cuando las evals se vuelvan serias; hoy es overkill |
| `plugin-dev` (anthropics/claude-code, oficial) | Skill + comando para crear plugins (plugin.json, marketplace.json) | Adoptar si empaquetas plugins para terceros; nuestro sync ya genera el de Cowork |

**Nuestra respuesta:** `skill-forge` (creada) — no compite con skill-creator: lo *envuelve* con lo que él no sabe: nuestras carpetas shared/claude-code/cowork, la decisión skill-vs-CLAUDE.md, el protocolo de auditoría de terceros, atribución CC BY-SA, el flujo sync→zip→commit, y la prueba mínima de triggers (3 positivas + 2 negativas). Para evals con varianza delega explícitamente en skill-creator.

## 5. Benchmarks de modelos y proveedores

**No existe skill mantenida** — verificado en marketplaces y GitHub (lo más cercano evalúa *tu app*, no compara proveedores; 0 stars). Tiene lógica: cualquier skill con datos de precios muere en semanas. La solución es metodología + fuentes vivas:

| Fuente | Qué da | Acceso |
|--------|--------|--------|
| Artificial Analysis | Intelligence Index, velocidad, **Cost per Task** (la métrica clave para agentes), Terminal-Bench Hard, Coding Agent Index | Web gratis; API de pago |
| OpenRouter `/api/v1/models` | Precios unificados de todos los proveedores | **API pública sin auth** |
| arena.ai (ex-LMArena) | Elo humano por categoría | Gratis |
| swebench.com / tbench.ai | Benchmarks agénticos de código/terminal (Terminal-Bench 2.1 es el estándar 2026) | Gratis |
| τ³-bench (Sierra) / ADE-bench (dbt) | Agentes con políticas/tools; data engineering | Open source |
| ccusage | Gasto real local de Claude Code (cache reads separados) | MIT, gratis |

**Nuestra respuesta:** `model-benchmark` (creada) — perfil de tarea → 3-5 candidatos → datos del día → **fórmula de costo-por-tarea** (input no cacheado + cache×0.1 + output, × turnos × retry) → tabla + recomendación con criterio de cambio → ADR fechado (para re-evaluar cuando muevan precios). Las reglas anti-H10 embebidas: cruzar 2+ fuentes, nunca el benchmark de un solo vendor, ojo con TPM en free tiers (la lección Groq).

---

## 6. Las 4 skills creadas (resumen)

| Skill | Carpeta | Qué aporta sobre lo externo |
|-------|---------|------------------------------|
| `agentic-system-design` | `shared/` | Los 5 patrones canónicos como escalera de decisión + reglas del setup (subagents vs Teams, Code vs Cowork, costo primero, R2, doc 12). Se encadena con `council`, `model-benchmark` y `adr-writer` |
| `model-benchmark` | `shared/` | Metodología costo-por-tarea con fuentes vivas; cierra en ADR fechado |
| `skill-forge` | `shared/` | skill-creator oficial + hallazgo de obra + nuestras convenciones de carpetas/sync/auditoría/licencias |
| `token-audit` | `claude-code/` | Auditoría contra NUESTROS presupuestos (H3/H4) con medición real; sin la licencia restrictiva del líder del nicho |
| `context-engineering` | `shared/` | *(añadida post-reporte)* Destila la doctrina oficial de Anthropic + lo mejor de muratcankoylan: presupuesto de contexto, tools mínimas, compaction/notas/subagents para horizonte largo, y el `system-prompt-blueprint.md` para automatizaciones de **puro system prompt** (escalón 1 de la escalera) |

Cadena natural que queda armada para automatizaciones:
`agentic-system-design` (diseño) → `context-engineering` (el contexto/prompt de cada pieza) → `model-benchmark` (elegir modelo por etapa) → `council` (si hay duda) → `adr-writer` (registrar) → construir → `token-audit` (afinar el gasto).

## 7. Plan de adopción externa (con protocolo `skills/10` §2)

1. **Ya**: instalar `skill-creator` de anthropics/skills en Claude Code (oficial, Apache-2.0).
2. **Cuando uses Agent Teams**: plugin `agent-teams` de wshobson (marketplace, no a claude-skills/).
3. **Cantera para leer, no instalar**: muratcankoylan (context engineering), ECC (`agent-architecture-audit`, `continuous-learning-v2`), alexgreensh (técnica de medición — respetando su licencia no-comercial: leer, no copiar).
4. **Solo si aparece el caso de uso**: n8n-skills (czlonkowski), plugin-dev (anthropics).

**No verificado / vigilar:** conteos de stars de ECC (cifras contradictorias entre fuentes); contenido interno completo de plugin-dev (API 403); estado 2026 de HELM y GAIA (envejecidos); free tiers exactos de Langfuse/Helicone.

## 8. Fuentes primarias

[Building Effective Agents](https://www.anthropic.com/research/building-effective-agents) · [Agent Teams docs](https://code.claude.com/docs/en/agent-teams) · [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) · [Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) · [Improving skill-creator (blog oficial)](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills) · [wshobson/agents](https://github.com/wshobson/agents) · [everything-claude-code](https://github.com/affaan-m/everything-claude-code) · [anthropics/skills](https://github.com/anthropics/skills) · [agentskills.io](https://agentskills.io) · [obra/superpowers writing-skills](https://github.com/obra/superpowers) · [alexgreensh/token-optimizer](https://github.com/alexgreensh/token-optimizer) · [hamzafarooq/token-optimizer](https://github.com/hamzafarooq/token-optimizer) · [muratcankoylan/Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) · [czlonkowski/n8n-skills](https://github.com/czlonkowski/n8n-skills) · [Artificial Analysis](https://artificialanalysis.ai) · [OpenRouter models API](https://openrouter.ai/docs/api-reference/list-available-models) · [arena.ai](https://arena.ai/leaderboard) · [swebench.com](https://www.swebench.com) · [tbench.ai](https://www.tbench.ai/leaderboard) · [tau2-bench](https://github.com/sierra-research/tau2-bench) · [ccusage](https://github.com/ryoppippi/ccusage) · [MLflow skill evals](https://mlflow.org/blog/evaluating-skills-mlflow/)

---

*Doc 13 de la serie (subserie skills/). Las 4 skills creadas están en `setup/skills/` — para activarlas: copiar a claude-skills, sync sin `-NoCoworkBuild` (3 son shared → re-subir dev-skills.zip), probar triggers con la técnica de `skill-forge` §5.*
