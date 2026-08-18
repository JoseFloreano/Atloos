<!-- Snippet para el CLAUDE.md de cada proyecto (Claude Code).
     Gemelo Cowork: cowork-project-instructions.md
     COPIA SINCRONIZADA de skills/claude-code/project-onboard/references/
     memory-snippet.md (la skill lo pega automaticamente) — editar ambas.
     NOTA: este archivo regreso a la v1 en un pull (2026-07-26, tercera
     divergencia detectada) — restaurado.

     PRESUPUESTO: 913 tokens MEDIDOS (tiktoken/o200k, 2026-08-16; 3 314
     caracteres, 3,63 char/token). Antes decia "~300 tokens (H4)" y era un
     numero que nadie habia medido: el real es x3,04 mayor. Se sube el numero
     al real en vez de recortar —cada regla de aqui es la defensa contra la
     alucinacion cruzada entre proyectos— y el tope queda en 950 tokens
     MEDIDOS, el mismo margen que la `description` de una skill tiene contra
     su 1024. Lo mide y BLOQUEA `test-claude-md-drift.py`, que ya leia este
     fichero.
     El sello de version cuesta 23 tokens; su primera redaccion costaba 51 y
     dejaba 9 de margen, asi que se recorto — el margen es la funcion, no el
     adorno.
     Si hay que recortar, NO se corta por la linea de higiene (147 tokens,
     17 %): se corta por el parentesis de codebase-map. -->

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
6. Tu avance y tus pendientes van SIEMPRE a tu nota
   `10-Projects/<project-name>/sessions/YYYY-MM-DD-<tu-tarea>.md`. NUNCA edites
   `_PROJECT.md` a mitad de trabajo: lo consolida `session-close` (un archivo,
   un escritor). Sin condicion, a proposito: si hay otra sesion viva no lo
   puedes observar.
7. Si `Edit` falla con "File has been modified since read": re-lee y reintenta
   UNA vez; si falla de nuevo hay otro escritor activo — PARA y avisa. NUNCA
   crees un archivo copia/variante (`X 2.md`, `-v2`, `(copia)`).

At session start: `search_facts("recent decisions and known issues", group_ids=["<project-name>", "dev-global"])`, then read `10-Projects/<project-name>/_PROJECT.md` (y `codebase-map.md` si existe — es el mapa CURADO; el `codebase-map-snapshot.md` que genera el hook es un recorte ~2 KB con la cabecera y el resumen — el volcado completo vive fuera del vault, en `%LOCALAPPDATA%\graphify-snapshots\`).

**Graphify — antes de la PRIMERA búsqueda de la sesión (`Grep`/`Glob`/`grep`/`rg`, por lo que sea) corre `graphify query "<lo que ibas a buscar>"`.** «La primera» es un contador, no una categoría: no clasifiques nada. Si el repo no lo tiene instalado, o sin grafo, el CLI falla — dilo una vez y sigue. Su salida es la LISTA DE CANDIDATOS: confírmala con `Read` y da por hecho que le faltan sitios (5 de 9 en campo, los 2 decisivos fuera). Si `graphify claude install` dejó aquí su línea, bórrala.

After completing each coding task, BEFORE reporting it done: update Pendientes/Estado en TU nota de sesión (regla 6) — el hook Stop la acepta. Cierre completo → "cerramos" (`session-close`), que es quien toca `_PROJECT.md`.

When saving decisions/bugs/conventions → `memory-keeper` skill. Architecture decisions → `adr-writer` skill.

**Para integrar CUALQUIER rama a `main`, el criterio es la skill `workstream-merge-gate`** — no otra. Vale igual si la rama la hizo un frente, un subagente o tú: `main` es rama protegida y su merge necesita verde posterior al último commit y OK humano explícito.

**Higiene de salida — pide la respuesta, no el material** (medido en Atloos: −91 % a −99 % de bytes): `git log --oneline -n 50`, `git diff --stat`, `git status --short`, `find -maxdepth N`, y `Grep` + `Read` con `offset`/`limit` en vez del fichero entero. Dos tiempos: la forma barata para todo, la cara **solo para lo que ya falló** — nunca recortes el comando cuya falla estás diagnosticando. Y el exit code se lee **sin tubería**: `cmd > /tmp/a.txt 2>&1; echo "exit=$?"`.

If the `graphiti-memory` MCP is unavailable, skip Graphiti silently — the vault is the primary record.

`snippet v6 · 2026-08-17` — si tu copia dice otra, va atrás.
