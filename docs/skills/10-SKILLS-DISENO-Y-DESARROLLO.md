# Skills de Diseño y Desarrollo: Investigación y Selección
## Ciberseguridad, Council, Base de Datos, Diseño UI/UX y complementos a Superpowers

> **Fecha:** Julio 2026
> **Contexto:** Continúa la investigación de `_archive/OptimalClaudeCode.md` (junio 2026) y se apoya en la infraestructura ya montada: sistema de skills en `claude-skills/{shared,claude-code,cowork}` (doc `setup/skills/README.md`), Superpowers instalado, skills propias (adr-writer, memory-keeper, project-onboard/resume).
> **Método:** 5 líneas de investigación paralelas sobre fuentes primarias (repos GitHub fetcheados directamente, docs de Anthropic, blogs de autores). Todo lo no verificable está marcado. **Este doc solo documenta — no instala nada.**
> **Alcance:** solo skills; los MCPs correspondientes se mencionan cuando el patrón oficial es skill+MCP.

---

## 1. Resumen ejecutivo

El ecosistema de skills maduró desde la investigación de junio: ahora hay **vendors de primera línea publicando skills oficiales** (Trail of Bits, Supabase, Neon, Vercel, shadcn, Anthropic), lo que cambia la recomendación — ya no hay que pescar en mega-marketplaces: casi todo lo que necesitas viene de autores con reputación.

**El set recomendado (12 skills/colecciones, detalle por sección):**

| Categoría | Adopción recomendada | Fuente | Licencia |
|-----------|---------------------|--------|----------|
| Ciberseguridad | `trailofbits/skills` (subset curado) + `/security-review` de Anthropic + `claude-code-owasp` | Trail of Bits / Anthropic / agamm | CC BY-SA 4.0 / MIT / MIT |
| Council | `council` de Everything Claude Code (adaptada) | affaan-m (ECC) | MIT |
| Base de datos | `supabase-postgres-best-practices` + `postgres-best-practices` (Neon) + `sql-optimization-patterns` | Supabase / Neon / wshobson | MIT / Apache-2.0 / MIT |
| Diseño | `frontend-design` + `web-artifacts-builder` (Anthropic), skill oficial de shadcn, `superdesign-skill`, `material-3-skill` (Flutter) | Anthropic / shadcn / superdesign / hamen | Apache-2.0 / MIT |
| Desarrollo general | `react-best-practices` + `web-design-guidelines` (Vercel), `comprehensive-review` + `performance-optimization` (wshobson) | Vercel / wshobson | MIT |

**El hallazgo que gobierna todo lo demás:** las skills de terceros son el npm de 2016. Snyk analizó 3,984 skills públicas y encontró **36% con fallos de seguridad y 13.4% con al menos un issue crítico**, con prompt injection como vector dominante (91% de las maliciosas). Antes de instalar cualquier skill aplica el protocolo de auditoría de la sección 2 — sin excepciones, incluso para las de esta lista.

---

## 2. Protocolo de seguridad para adoptar skills (LEER PRIMERO)

Esto extiende el hallazgo R4 de la auditoría (`auditoria/09`): una skill es texto auto-cargado como instrucciones — quien escribe tu SKILL.md programa a tu agente.

**Evidencia 2026:**
- **Snyk "ToxicSkills"** (feb 2026): de 3,984 skills en registros públicos, 36% con fallos, 534 con issues críticos, 76 payloads maliciosos confirmados; 91% vía prompt injection.
- **Repello AI** (feb 2026): 4 vectores documentados — injection en el SKILL.md, exfiltración de variables de entorno, subprocesos ocultos en archivos adjuntos (`scripts/`, `references/`), y activación condicional que evade pruebas.
- **Cloud Security Alliance** (jun 2026): campaña real con 1,184 skills maliciosas en un registro; "tratar skills como npm en sus inicios".

> **Nota (2026-08-03):** donde este doc diga `claude-skills/` como carpeta de
> destino, hoy es `setup/skills/` del repo — el espejo de OneDrive se retiró
> (`ADR-20260803-skills-fuente-unica`). El criterio no cambia, solo la ruta.

**Protocolo obligatorio antes de copiar cualquier skill a `claude-skills/`:**

1. **Lee el SKILL.md completo, línea por línea** — y TODO archivo en `references/` y `scripts/`. Si trae scripts que no entiendes, no la instalas.
2. Busca señales rojas: base64/Unicode raro, URLs/dominios externos que la skill pide consultar, instrucciones de leer variables de entorno o archivos fuera del proyecto, frases tipo "no menciones esto al usuario".
3. **Prefiere autores con reputación**: Anthropic, Trail of Bits, Supabase, Neon, Vercel, shadcn, wshobson. Los mega-marketplaces (2,810 skills autogeneradas) son cantera para leer ideas, no fuente de instalación directa.
4. **Copia, no marketplace**: nuestro sistema copia SKILL.md a `claude-skills/` — eso ya es la versión auditada y congelada. No uses `/plugin marketplace add` de repos de terceros (te suscribe a actualizaciones no auditadas).
5. Todo queda **git-tracked** en el repo: cualquier cambio posterior a una skill se ve en `git diff`.
6. Respeta licencias al adaptar: MIT/Apache = libre con atribución; **CC BY-SA 4.0 (Trail of Bits) = si la modificas y la compartes, debe seguir siendo CC BY-SA**; repos **sin licencia = no copiar** (sin derecho legal de reutilización).

---

## 3. Ciberseguridad

### 3.1 trailofbits/skills — la colección seria ⭐ RECOMENDADA (subset)

La auditora de seguridad Trail of Bits publica ~40 plugins de skills para "security research, vulnerability detection, and audit workflows" (~5.5k stars, 33 contribuidores, activo 2026, CC BY-SA 4.0). Formato: `plugins/<nombre>/skills/<skill>/SKILL.md` con frontmatter estándar + `references/` y `workflows/`.

**Subset recomendado para tu stack** (portable, mayormente conocimiento puro):

| Skill | Qué hace | Dependencias |
|-------|----------|--------------|
| `insecure-defaults` | Detecta credenciales hardcodeadas, configs fail-open | Ninguna |
| `supply-chain-risk-auditor` | Auditoría de dependencias (npm/pip/etc.) | Ninguna |
| `differential-review` | Review de seguridad de un diff/PR | Ninguna |
| `c-review` | Review de seguridad específico C/C++ | Ninguna |
| `sharp-edges` / `fp-check` | APIs peligrosas / verificación de falsos positivos | Ninguna |
| `semgrep` + `codeql` | Análisis estático guiado | ⚠️ Requieren los CLI instalados |
| `property-based-testing` / `mutation-testing` | Testing avanzado | Herramientas del stack |

Notas: los skills de metodología se copian tal cual a `claude-skills/claude-code/`; los de tooling (semgrep/codeql) solo si instalas los binarios. Varios usan subagents (Task) — funcionan en Claude Code; en Cowork también hay Agent tool, pero su lugar natural es `claude-code/` (operan sobre repos locales). **No incluye** threat modeling dedicado ni secrets-scanning puro (gap real; `insecure-defaults` es lo más cercano).

### 3.2 /security-review de Anthropic

`anthropics/claude-code-security-review` (MIT, ~4.5k stars): el comando `/security-review` viene por defecto en Claude Code (personalizable copiando `security-review.md` a `.claude/commands/`), y el GitHub Action revisa PRs automáticamente (diff-aware, filtra falsos positivos). Costo de adopción cero — ya lo tienes; el Action es candidato para cuando tengas repos con CI.

### 3.3 agamm/claude-code-owasp

Un solo SKILL.md (MIT, ~179 stars) con OWASP Top 10:2025, ASVS 5.0, LLM Top 10 y quirks de 20+ lenguajes. Markdown puro sin dependencias — máxima portabilidad. Bueno como skill de conocimiento OWASP complementaria a las de ToB (que son de workflow). Repo joven (10 commits): auditar con especial cuidado y congelar la copia.

---

## 4. Council — toma de decisiones

### 4.1 La recomendada: `council` de Everything Claude Code (adaptada) ⭐

Del repo `affaan-m/everything-claude-code` (MIT, muy activo; el conteo de stars varía según la fuente entre ~82k y ~185k — no verificable con precisión). **Mecánica verificada en su SKILL.md:** la voz principal (Architect) fija posición primero; luego lanza **3 subagents en paralelo** — Skeptic, Pragmatist, Critic — que reciben solo la pregunta y contexto esencial **sin historial** (anti-anchoring); síntesis final con veredicto compacto, el disenso más fuerte y los gaps de consenso. Una sola ronda — barato y rápido.

**Por qué esta:** MIT, un archivo, mecánica simple y bien diseñada (el aislamiento de contexto de los críticos es la parte inteligente), y encaja exactamente en el flujo que ya tienes:

```
brainstorming (Superpowers)  →  council (ECC)         →  adr-writer (tuya)
explora el espacio CON el       genera disenso SIN el     registra la decisión
usuario                         usuario y da veredicto    en el vault
```

Verificado: **no duplica** a Superpowers — obra/superpowers no incluye council; brainstorming es diálogo socrático con el usuario, council es debate adversarial sin él. Son complementarias por diseño.

**Adaptación sugerida al copiarla:** añadir al final del SKILL.md un paso "si la decisión se toma, ofrece registrarla con `adr-writer`" — integra el veredicto con tu memoria.

### 4.2 Alternativas evaluadas

| Opción | Veredicto |
|--------|-----------|
| `ngmeyer/council-review` (MIT) | Plan B interesante: 5 advisors con métodos de razonamiento distintos (inversión, primeros principios, analogía...), base metodológica citada (DMAD, ICLR 2025), modos Quick/Full/Adversarial. Casi sin tracción (0 stars) pero SKILL.md puro |
| `karpathy/llm-council` | NO es skill: app web local multi-proveedor vía OpenRouter; "Saturday hack" explícitamente no mantenido y sin licencia visible. Valioso como concepto, no como pieza |
| `aiwithremy/claude-skills-llm-council` (~609 stars) | El port más popular de la idea de Karpathy, pero **sin licencia** → descartado por el protocolo §2.6 |
| `wan-huiyan/agent-review-panel` (MIT, activo) | La versión heavy: 4-6 reviewers, 1-3 rondas de debate, juez, blind scoring, anti-sycophancy. $3-20 y 6-15 min por corrida — overkill como default; anotar para decisiones de altísimo riesgo |
| `itshussainsprojects/Claude-Council-Skill` (MIT) | 7 personas sin subagents (funciona hasta en claude.ai) — candidata curiosa para la carpeta `cowork/` si quisieras council sin Task tool, pero 5 stars/6 commits: auditar fuerte |

**Ubicación:** `shared/` — council es metodología pura; funciona en Code y en Cowork (ambos tienen subagents).

---

## 5. Base de datos

### 5.1 El patrón oficial 2026: skill (conocimiento) + MCP (ejecución)

Supabase lo formuló explícitamente (blog, enero 2026): el MCP da la *capacidad* de tocar la base; la skill enseña a hacerlo *correctamente*. Complementarios, no alternativos.

### 5.2 Las recomendadas ⭐

| Skill | Fuente | Qué cubre | Formato |
|-------|--------|-----------|---------|
| `supabase-postgres-best-practices` | supabase/agent-skills (oficial, MIT, v1.1.1 ene-2026) | 30 reglas en 8 categorías: query performance, pooling, schema design, RLS, concurrencia/locking, monitoring | SKILL.md + references/, puro markdown |
| `postgres-best-practices` | neondatabase/postgres-skills (oficial, Apache-2.0) | Schema design, indexing, optimización, pitfalls. Revisada por Jonathan Katz (PostgreSQL Core Team) | SKILL.md puro, progressive disclosure |
| `sql-optimization-patterns` | wshobson/agents (MIT) | EXPLAIN/ANALYZE, indexing, N+1 — Postgres y MySQL | SKILL.md puro |
| `migration-architect` | alirezarezvani/claude-skills (MIT, v2.9.0 may-2026) | Zero-downtime migrations, validación de compatibilidad, rollback | SKILL.md (+scripts Python opcionales) |

Nota: Supabase y Neon se solapan parcialmente (ambas son "Postgres best practices") — adoptar **una** como principal (Supabase si usas Supabase en proyectos; Neon si es Postgres genérico: la revisión del PostgreSQL Core Team pesa) y guardar la otra como referencia. `migration-architect` viene de un mega-marketplace: aplicar protocolo §2 con rigor extra.

**Gaps verificados:** no existe skill mantenida dedicada a expand-contract puro (migration-architect es lo más cercano) ni skills NoSQL oficiales (MongoDB no publica; solo agregadores). anthropics/skills no tiene nada de DB.

**Ubicación:** `shared/` (conocimiento válido en ambos productos). El MCP de Supabase, cuando lo necesites, es `supabase-community/supabase-mcp` — recordando H3/anti-patrón 3: conectarlo solo en sesiones que tocan la base.

---

## 6. Diseño (UI/UX/frontend)

### 6.1 Las oficiales de Anthropic (anthropics/skills) ⭐

Verificado el contenido real del repo (~149k stars, activo): `frontend-design` (dirección estética, tipografía, evitar UI "templated"), `canvas-design` (arte estático PNG/PDF), `brand-guidelines`, `webapp-testing`, `web-artifacts-builder` (ojo: ese es el nombre real — `artifacts-builder` a secas no existe), `theme-factory`, `algorithmic-art`. **Licencia mixta:** las de diseño son Apache 2.0 (copiables sin restricción); las de documentos (docx/pdf/pptx/xlsx) son source-available, no open source.

Para tu caso: `frontend-design` a `shared/` (aplica a React en Code y a artifacts/HTML en Cowork), `web-artifacts-builder` y `canvas-design` a `cowork/` (su hábitat natural es generar entregables visuales).

### 6.2 shadcn: skill oficial del vendor ⭐ (para React/Next.js)

shadcn mantiene su propia skill (`pnpm dlx skills add shadcn/ui`, se autoactiva al detectar `components.json`): CLI, theming OKLCH/dark mode, registries, y el patrón registry-MCP+skill oficial. Primera parte, activa (CLI v4, marzo 2026). A `claude-code/` (asume el CLI y el repo local). Complemento opcional: `mattbx/shadcn-skills` (discovery de 1,500+ componentes comunitarios; MIT pero joven — auditar).

### 6.3 superdesign-skill (MIT)

`superdesigndev/superdesign-skill` — skill real (verificada), para diseñar features/páginas/flujos con design system e iteración de drafts. Dependencia opcional de su CLI. Interesante para `shared/` si haces mucho diseño exploratorio; el producto hermano (extensión de IDE con canvas) es independiente y no lo necesitas.

### 6.4 Flutter / Material 3

`hamen/material-3-skill` (MIT): tokens, componentes, theming, auditoría MD3 — pero **primario Jetpack Compose, Flutter secundario**, y el autor advierte drift vs el spec de Google. Adoptar con expectativas moderadas a `claude-code/`. `Harishwarrior/flutter-claude-skills` (MIT) cubre testing Flutter (unit/widget/integration con Riverpod), no diseño. **Gap real verificado:** no existe skill mantenida de golden tests visuales de Flutter — candidata a skill propia tuya más adelante (tienes el template).

---

## 7. Desarrollo general (complementos a Superpowers)

Superpowers ya cubre metodología (TDD, brainstorm, planes, verificación, worktrees, debugging). Los huecos reales y quién los llena:

| Hueco | Skill/colección | Fuente | Nota |
|-------|----------------|--------|------|
| Performance React/Next | `react-best-practices` (40+ reglas priorizadas) | vercel-labs/agent-skills (MIT, ~27.6k stars, activo) | Primera parte del framework ⭐ |
| Review de UI/accesibilidad | `web-design-guidelines` (100+ reglas) | vercel-labs/agent-skills | ⭐ |
| Review multi-dimensión | plugin `comprehensive-review` (architect + code-reviewer + security-auditor en paralelo) | wshobson/agents (MIT, 35.7k stars, push may-2026) | Formato agents, no skills — instalar como plugin o portar los .md a `.claude/agents/` |
| Performance profiling general | plugin `performance-optimization` | wshobson/agents | Ídem |
| Disciplina de código minimalista | `andrej-karpathy-skills` (multica-ai) | ⚠️ **Sin licencia declarada** y es un CLAUDE.md, no skill → leerlo como inspiración, no copiar |

**Sobre los mega-marketplaces** (alirezarezvani 355 skills, jeremylongshore ~2,810): el segundo es mayormente **generación automatizada desde REST APIs** con rubric autodeclarado; del primero solo rescatamos piezas puntuales (§5). Ninguno tiene reviews independientes. Confirman la regla: **cantera sí, fuente de instalación no.**

**Gap verificado:** no hay skill de release/changelog bien mantenida — otra candidata a skill propia (es corta: conventional commits + changelog + tag).

---

## 8. Mapa de adopción para TU sistema

### 8.1 Dónde va cada cosa

```
claude-skills/
├── shared/
│   ├── council/                        ← ECC, adaptada (+ paso adr-writer)
│   ├── postgres-best-practices/        ← Supabase o Neon (elegir una)
│   ├── sql-optimization-patterns/      ← wshobson
│   ├── migration-architect/            ← alirezarezvani (auditar extra)
│   ├── frontend-design/                ← Anthropic
│   └── owasp-security/                 ← agamm (auditar extra)
├── claude-code/
│   ├── tob-insecure-defaults/          ┐
│   ├── tob-supply-chain-audit/         │ Trail of Bits (subset §3.1,
│   ├── tob-differential-review/        │ prefijo tob- para atribución
│   ├── tob-c-review/                   ┘ CC BY-SA)
│   ├── shadcn/                         ← skill oficial del vendor
│   └── material-3/                     ← hamen (Flutter)
└── cowork/
    ├── web-artifacts-builder/          ← Anthropic
    └── canvas-design/                  ← Anthropic
```

Los plugins de wshobson (`comprehensive-review`, `performance-optimization`) son formato agents — se instalan como plugin de Claude Code (`/plugin marketplace add wshobson/agents`) o se portan sus .md a `.claude/agents/` del dotfiles; no entran a la carpeta de skills.

### 8.2 Orden de adopción sugerido (cuando decidas implementar)

1. **Tanda 1 (una tarde):** council + frontend-design + una de Postgres — las tres de mayor uso diario, tres autores distintos de máxima reputación.
2. **Tanda 2:** subset Trail of Bits + owasp — el set de seguridad completo.
3. **Tanda 3:** shadcn + Vercel (cuando toque proyecto React), material-3 (cuando toque Flutter), web-artifacts-builder/canvas-design (Cowork).
4. Cada tanda: protocolo §2 → copiar a la carpeta → `sync-skills.ps1` → re-subir dev-skills.zip si tocó shared/cowork → probar el trigger con 2-3 frases.

### 8.3 Presupuesto de contexto

12-15 skills nuevas NO infla el contexto: progressive disclosure carga solo name+description (~40-60 tokens por skill al inicio; el cuerpo solo cuando dispara). El riesgo real es de *precisión de trigger* con descripciones que se solapan (p.ej. dos skills de Postgres) — por eso se elige una principal por tema. Regla de mantenimiento: si en un mes una skill nunca disparó, o dispara cuando no debe, se ajusta la descripción o se saca (mismo criterio de salida que todo lo demás del setup).

---

## 9. Fuentes primarias

| Categoría | Fuentes |
|-----------|---------|
| Seguridad de skills | [Snyk ToxicSkills](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/) · [Repello AI](https://repello.ai/blog/claude-code-skill-security) · [CSA](https://cloudsecurityalliance.org/blog/2026/06/25/5-claude-agent-skills-risks-every-ciso-should-know) |
| Ciberseguridad | [trailofbits/skills](https://github.com/trailofbits/skills) · [anthropics/claude-code-security-review](https://github.com/anthropics/claude-code-security-review) · [agamm/claude-code-owasp](https://github.com/agamm/claude-code-owasp) |
| Council | [ECC council SKILL.md](https://github.com/affaan-m/everything-claude-code/blob/main/skills/council/SKILL.md) · [karpathy/llm-council](https://github.com/karpathy/llm-council) · [ngmeyer/council-review](https://github.com/ngmeyer/council-review) · [agent-review-panel](https://github.com/wan-huiyan/agent-review-panel) |
| Base de datos | [supabase/agent-skills](https://github.com/supabase/agent-skills) · [blog Supabase](https://supabase.com/blog/postgres-best-practices-for-ai-agents) · [neondatabase/postgres-skills](https://github.com/neondatabase/postgres-skills) · [supabase-mcp](https://github.com/supabase-community/supabase-mcp) |
| Diseño | [anthropics/skills](https://github.com/anthropics/skills) · [shadcn skills](https://ui.shadcn.com/docs/skills) · [shadcn MCP](https://ui.shadcn.com/docs/mcp) · [superdesign-skill](https://github.com/superdesigndev/superdesign-skill) · [material-3-skill](https://github.com/hamen/material-3-skill) |
| Desarrollo | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) · [wshobson/agents](https://github.com/wshobson/agents) · [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) · [jeremylongshore](https://github.com/jeremylongshore/claude-code-plugins-plus-skills) |

**Marcado como no verificable:** conteos exactos de stars de ECC y andrej-karpathy-skills (fuentes discrepan); fechas de último commit de varios repos (feeds bloqueados); existencia de skill NoSQL oficial de MongoDB (404); skill de threat modeling dedicada en ToB.

---

*Doc 10 de la serie. Siguiente paso natural cuando lo decidas: ejecutar la Tanda 1 aplicando el protocolo §2. Revisar este catálogo trimestralmente — el ecosistema se mueve rápido (el digest mensual de Cowork propuesto en `cowork-y-multiagente/08` §7 puede vigilar estos repos).*
