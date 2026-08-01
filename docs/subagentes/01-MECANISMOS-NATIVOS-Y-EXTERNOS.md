# Mecanismos Nativos y Externos para Workstreams Paralelos
## Las cuatro capas que ya existen, verificadas antes de proponer nada nuevo

> **Fecha:** 2026-08-01. Fuentes web en §6 (blogs/guías de terceros, no
> documentación oficial salvo donde se indica — tratar como orientación,
> no como cifra exacta; disciplina H10 de la serie de memoria).

---

## 1. Nativo del producto: `--worktree` y Agent Teams

### 1.1 `claude --worktree <nombre>` (alias `-w`)

Documentado en `code.claude.com/docs/en/worktrees`: crea un worktree aislado
bajo `.claude/worktrees/<nombre>/` en la raíz del repo, en una rama nueva
`worktree-<nombre>`, y arranca Claude ahí. Cada sesión tiene su propio
directorio de trabajo — las ediciones de una nunca tocan los archivos de otra.
También se puede pedir "trabaja en un worktree" a mitad de sesión: Claude lo
crea con la tool `EnterWorktree` y puede saltar entre worktrees existentes con
la misma tool apuntando a otra ruta. Para VCS que no son git (SVN, Perforce,
Mercurial) el mecanismo se sustituye con hooks `WorktreeCreate`/`WorktreeRemove`
propios.

**Verificación directa en este entorno:** `EnterWorktree` y `ExitWorktree`
aparecen como tools disponibles (deferred) en esta misma sesión de Cowork —
no es solo documentación externa, es una capacidad presente aquí y ahora.

Es el mecanismo que el RFD 02 §4 ya adaptó a mano (worktree por conversación,
fuera de OneDrive) antes de que esta investigación confirmara que hay una
tool nativa para entrar/salir de worktrees sin reinventar el `git worktree add`.

### 1.2 Agent Teams (Opus 4.6, 5-feb-2026)

Una sesión actúa como *team lead* y lanza *teammates* independientes que se
comunican directamente entre sí, comparten una task list y se autocoordinan.
Requiere `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (sigue marcado experimental
— confirmado también en doc 13). Para equipos grandes o tareas largas, los
worktrees son el complemento recomendado: cada teammate en su propia rama y
directorio; al terminar, las ramas se integran. Buena práctica reportada:
correr un agente validador (o la suite de tests) antes de integrar el trabajo
de cualquier teammate.

## 2. Ya instalado en el repo: 4 skills de Superpowers

Ninguna de estas cuatro requiere instalar nada — ya están (doc 05). Mapeo a
las partes del flujo que pregunta esta investigación:

| Skill (Superpowers) | Cubre |
|---|---|
| `using-git-worktrees` | Garantiza un workspace aislado por frente vía tools nativas o `git worktree` de respaldo — la base de "cada workstream en su rama" |
| `dispatching-parallel-agents` | Cuándo tiene sentido lanzar 2+ tareas independientes sin estado compartido — el criterio de "¿de verdad son frentes separados?" |
| `subagent-driven-development` | Ejecuta un plan con tareas independientes dentro de la sesión actual — el "orquestador" que reparte el trabajo entre workstreams |
| `finishing-a-development-branch` | Qué hacer cuando la implementación está completa y los tests pasan: decidir cómo integrar — el asiento natural del gate de merge |

## 3. Externo evaluado (no instalado): plugin `agent-teams` de wshobson

Ya catalogado en doc 13 §2 y no re-investigado a fondo aquí (evitar
duplicar). Lo nuevo confirmado hoy: su skill `parallel-feature-development`
está pensada exactamente para esto — descompone una feature grande en
workstreams independientes con **límites de propiedad de archivo** (nunca dos
implementadores en el mismo archivo) y **contratos de interfaz** en los
bordes, para que los frentes puedan construir contra la API del otro antes de
que exista. Trae presets (`/team-spawn feature|review|debug|fullstack|
research|security|migration`) y `--plan-first` para revisar la descomposición
antes de lanzar implementadores. MIT, plugin activo a jul-2026.

## 4. Ya escrito en este repo (atado al puente Telegram): RFD 02

El RFD 02 (§4 y C4) diseñó — para el puente, no en general — el mismo patrón:

- Worktree por conversación, creado perezoso, fuera de OneDrive.
- `CLAUDE.md` copiado al worktree al crearlo (está gitignorado como artefacto
  de instancia; sin copiarlo el agente pierde las Memory Rules).
- Reconciliación de worktrees huérfanos al reiniciar (nunca borrar solo).
- `/merge`: deshabilitado si no hay test verde después del último commit;
  squash por defecto; botón de confirmación que caduca a 5 minutos.
- Los git ops los ejecuta el orquestador (el daemon), nunca el agente — así
  una inyección de prompt no puede publicar nada por su cuenta.

Es la pieza más cercana a "nuestras reglas" de las cuatro — el detalle en
doc 02 de esta subserie es cómo generalizarla fuera del contexto Telegram.

## 5. Lo que ninguna de las cuatro capas sabe

Ni Agent Teams, ni las tools nativas, ni Superpowers, ni el plugin de
wshobson conocen las Memory Rules de este repo (`group_ids`, aislamiento de
vault por proyecto). Un teammate o subagente lanzado a un workstream sin ese
briefing puede escribir memoria al `group_id` equivocado o leer/editar fuera
de `10-Projects/<su-proyecto>/`. Ver doc 00 §S4 y la propuesta en doc 03.

## 6. Fuentes

**Nativo:** [Run parallel sessions with worktrees — Claude Code Docs](https://code.claude.com/docs/en/worktrees) (oficial).
**Agent Teams:** [MindStudio: Claude Code Agent Teams](https://www.mindstudio.ai/blog/claude-code-agent-teams-parallel-workflows) ·
[Claude Directory: Worktrees Guide 2026](https://www.claudedirectory.org/blog/claude-code-worktrees-guide) ·
[Developers Digest: Git Worktrees + Claude Code 2026 Playbook](https://www.developersdigest.tech/blog/git-worktrees-claude-code-parallel-agents-guide) ·
[laozhang.ai: Claude 4.6 Agent Teams](https://blog.laozhang.ai/en/posts/claude-4-6-agent-teams).
**wshobson agent-teams:** [repo](https://github.com/wshobson/agents/tree/main/plugins/agent-teams) ·
[README del plugin](https://github.com/wshobson/agents/blob/main/plugins/agent-teams/README.md).
**Costo y riesgo (§S3 de doc 00, detalle en doc 02):** [CloudZero: Claude Code Agents 2026](https://www.cloudzero.com/blog/claude-code-agents/) ·
[Medium — Markus Sandelin: Your AI Agent Teams Are Burning Money](https://medium.com/@mrsandelin/your-ai-agent-teams-are-burning-money-heres-the-math-939e3b3b9d88) ·
[HackerNoon: Agent Teams in Practice](https://hackernoon.com/navigating-claude-code-agent-teams-in-practice).

**No verificable / a tratar como estimación:** las cifras de costo son de
blogs individuales sin auditoría independiente (mismo caveat H10 de la serie
de memoria) — órdenes de magnitud, no presupuesto exacto.
