<!-- Snippet para el CLAUDE.md de cada proyecto (Claude Code). ~300 tokens (H4).
     Gemelo Cowork: cowork-project-instructions.md
     ⚠ COPIA SINCRONIZADA de skills/claude-code/project-onboard/references/
       memory-snippet.md (la skill lo pega automáticamente) — editar ambas a la vez.
     NOTA: este archivo regresó a la v1 en un pull (2026-07-26, tercera
     divergencia detectada) — restaurado. El detalle de Graphiti (formato de
     episodios, qué guardar) vive en la skill memory-keeper, no aquí. -->

## Active Project: `<project-name>`   ← reemplazar al copiar

## Memory Rules — NON-NEGOTIABLE (anti cross-project hallucination)

1. Graphiti searches: ALWAYS `group_ids: ["<project-name>", "dev-global"]`.
   Never omit, never broaden, never `"main"`.
2. `add_episode`: ALWAYS `group_id: "<project-name>"`.
   Personal/cross-stack preferences → `"dev-global"`. Unsure → ask, don't guess.
3. Vault: only `10-Projects/<project-name>/`, `brain/`, `daily/`.
   Other projects' folders are OFF-LIMITS unless the user explicitly asks.
4. Memory from another project seems relevant → say so and ask; never import silently.
5. Stored fact contradicts current code/user → trust the present, update the memory.
6. **Multi-agent** (2+ sesiones en este proyecto a la vez): escribe SOLO en tu
   nota `10-Projects/<project-name>/sessions/YYYY-MM-DD-<tu-tarea>.md` (avance
   y pendientes ahí); NO edites `_PROJECT.md` a mitad de trabajo — solo
   `session-close` lo consolida (un archivo = un escritor).
7. Si `Edit` falla con "File has been modified since read": re-lee y reintenta
   UNA vez; si falla de nuevo hay otro escritor activo — PARA y avisa. NUNCA
   crees un archivo copia/variante (`X 2.md`, `-v2`, `(copia)`).

At session start: `search_facts("recent decisions and known issues", group_ids=["<project-name>", "dev-global"])`, then read `10-Projects/<project-name>/_PROJECT.md` (y `codebase-map.md` si existe — es el mapa CURADO; el `codebase-map-snapshot.md` que genera el hook es un recorte ~2 KB con la cabecera y el resumen — el volcado completo vive fuera del vault, en `%LOCALAPPDATA%\graphify-snapshots\`).

After completing each coding task, BEFORE reporting it done: update Pendientes/Estado — en `_PROJECT.md` (2-5 líneas) si trabajas solo, o en TU nota de sesión si hay multi-agente (regla 6). El hook Stop acepta ambas. Cierre completo → "cerramos" (`session-close`).

When saving decisions/bugs/conventions → `memory-keeper` skill. Architecture decisions → `adr-writer` skill.

**Para integrar CUALQUIER rama a `main`, el criterio es la skill `workstream-merge-gate`** — no otra. Vale igual si la rama la hizo un frente, un subagente o tú: `main` es rama protegida y su merge necesita verde posterior al último commit y OK humano explícito.

If the `graphiti-memory` MCP is unavailable, skip Graphiti silently — the vault is the primary record.
