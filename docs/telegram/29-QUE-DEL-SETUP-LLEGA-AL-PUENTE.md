---
title: Qué del setup llega al puente de Telegram, y qué no
fecha: 2026-08-17
sprint: 11
tipo: inventario
estado: medido
alcance: mapa — NO se implementó nada
---

# 29 · Qué del setup llega al puente — el mapa

El README del puente va T0 → T1 → T2 → T3, pero en ningún sitio estaba escrito
**qué capacidades del setup son alcanzables desde Telegram**. Esto es ese mapa.

**No se implementó nada.** Los agujeros encontrados están anotados, no tapados —
incluidos dos que son de seguridad.

---

## El hallazgo que gobierna todo el resto

> **El bot no ejecuta a través de la herramienta `Bash` de Claude Code para lo
> que importa.** `/test` corre con `gitops.run(cmd.split(), …)` y `/merge` con
> `gitops.git([...])`: **subprocesos directos**. Los hooks de `PreToolUse` —
> `merge-gate-guard` entre ellos— solo ven llamadas a herramientas del agente.
> Así que **no es que el gate falle en el puente: es que no puede verlo.**

Y el segundo, que lo dobla:

> **La sesión del bot corre con `CLAUDE_CONFIG_DIR` = `claude-tg-profile`**
> (`tg_daemon.py:156`, cableado en `:1250`). `sync-hooks` instala en `~/.claude`
> y en `~/.claude-*` — **`claude-tg-profile` no encaja en ninguno de los dos**.
> Cuando el perfil bot está activo, la sesión corre **con CERO hooks**.
> Y el fallback está al revés: si al perfil le falta algo, el daemon cae a la
> config normal — **la que sí tiene hooks**. O sea que el camino barato es el
> desprotegido, y funciona mejor cuando está peor protegido.

---

## Hooks

| Hook | ¿Llega al bot? | Cómo, o por qué no |
|---|---|---|
| `merge-gate-guard` | **NO** | Doble motivo. (1) Es `PreToolUse` sobre `Bash\|PowerShell`, y el `/merge` del bot va por `gitops` en subproceso. (2) Con perfil bot no hay hooks cableados. El daemon tiene su **propio** camino — comparado abajo |
| `check-vault-updated` | **NO** | Es `Stop`. Con perfil bot no está cableado. Sin perfil, se dispararía al cerrar la invocación no interactiva |
| `goal-evidence-guard` | **NO** | Ídem (`Stop`) |
| `memory-flush` | **NO** | Es `PreCompact`. Una invocación `-p` con `--max-turns` acotado rara vez compacta |
| `mark-code-dirty` | **a medias** | Es `PostToolUse` sobre `Write\|Edit\|MultiEdit`, que el bot SÍ usa en modo escritura. Se dispararía **solo si la sesión no usa el perfil bot**. Y aunque se dispare, escribe el flag en el **worktree**, no en el árbol del usuario: nadie lo lee luego |
| `validate-graphiti-group-id` | **NO** | `PreToolUse` sobre `mcp__graphiti`, y Graphiti está pospuesto |

**Resumen: 0 de 6 hooks gobiernan una sesión del bot con perfil activo.**

---

## El gate de merge: ¿el daemon cumple criterios equivalentes?

La skill `workstream-merge-gate` dice explícitamente que no se usa para el merge
del puente, *«ese lo gobierna el daemon»*. **Comprobado, criterio por criterio**
(`cmd_merge`, `tg_daemon.py:970-1021`):

| Criterio de la skill | ¿Lo cumple el daemon? | Evidencia |
|---|---|---|
| 1 · Artefacto verificado, worktree limpio | **Sí** | `head_sha()` + bloquea si `diff_summary()["has_changes"]` |
| 2 · Verde POSTERIOR al último commit | **Sí, y es su mejor parte** | Guarda `test_ok_sha` en `/test` y bloquea si `test_ok_sha != head`, diciendo los dos SHA |
| 2b · Tests que el implementador no escribió | **NO** | No se comprueba en ninguna parte |
| 3 · El reloj (una corrida rápida no es un verde) | **NO** | `/test` mira el exit code y nada más. Timeout de 1800 s, sin suelo |
| 4 · Integración serializada | **a medias** | `INFLIGHT` es **por chat**, no global. Dos chats podrían integrar a la vez |
| 5 · Squash | **Sí** | Es su modo por defecto y lo dice en el botón |
| 6 · Confirmación humana explícita | **Sí** | Botón inline con token y caducidad |
| 7 · Limpieza | **Sí** | `/done` quita worktree y rama |

**Veredicto: 5 de 8, y la exclusión abrió DOS huecos reales** — el reloj y los
tests propios. No es un hueco teórico: los dos verdes falsos que el criterio del
reloj cazó en campo (117 s y 146 s contra un suelo de ~330 s) **habrían pasado
por el `/merge` del bot**, porque los dos salieron con exit 0.

Y uno estructural: **las dos evidencias no se hablan.** El gate escribe
`.claude/gate-verde.json` en el `.git` común; el daemon guarda `test_ok_sha` en
su propio `state`. Un verde producido por un lado no vale por el otro.

---

## Skills

El perfil bot lleva un recorte de skills (ADR-20260801-bot-memoria-y-perfil).
Lo que decide qué puede dispararse es **la superficie**:

| Superficie | ¿Llega al bot? | Por qué |
|---|---|---|
| `shared` | **Sí** | Va a las dos superficies |
| `claude-code` | **Sí** | El bot invoca Claude Code (`-p`) |
| `cowork` | **NO** | Cowork es otro árbol que el daemon no lanza. `project-resume`, `vault-drift-audit` y las demás de esa superficie no existen para el bot |

| Skill (por familia) | ¿Llega? | Detalle |
|---|---|---|
| `memory-keeper`, `adr-writer` | **a medias** | Están en la superficie correcta, pero escriben en el **vault**, y el vault no está montado en el worktree del bot. Escribirían en una ruta que nadie sincroniza |
| `workstream-merge-gate` | **NO, por diseño** | Su propia descripción excluye el merge del puente |
| `workstream-dispatch` | **NO** | Supone un humano delante que arbitra escalaciones. Es justo lo que el RFD 30 tiene que resolver |
| `notify-telegram` | **Sí** | Es la que existe para esto |
| `goal-forge` | **a medias** | La skill sí; el hook que la respalda (`goal-evidence-guard`) **no**, porque no hay hooks. Una meta lanzada desde el bot se cierra leyendo el transcript, que es exactamente lo que el ADR-20260809 prohíbe |
| `session-close` | **a medias** | Necesita el vault |
| Las de la superficie `cowork` | **NO** | Ver arriba |

---

## Comandos del bot: cuáles existen y cuáles dependen de Windows

Los **16** declarados en `BOT_COMMANDS` (`tg_daemon.py:167`):

| Comando | ¿Funciona en Linux? | Nota |
|---|---|---|
| `/p` `/status` `/new` `/chats` `/chat` `/model` `/help` | **Sí** | Estado puro |
| `/progress` | **Sí** | Lee `.tg/progress.md` del worktree |
| `/write` | **a medias** | Crea worktree bajo `LOCALAPPDATA or ~/.local/share` — **el fallback existe**, así que en Linux funciona. Lo que NO funciona son sus barreras: ver abajo |
| `/diff` `/commit` `/pull` `/push` | **Sí** | Van por `gitops` |
| `/test` | **NO, si el proyecto declara `py …`** | `gitops.run(cmd.split(), …)` es **argv, sin shell**: en Linux `argv[0]="py"` da `FileNotFoundError`. `projects.example.json:7` declara literalmente `"test": "py -m pytest -q"` |
| `/merge` | **Sí**, con los huecos de la tabla anterior | |
| `/done` | **Sí** | |

---

## ⚠ Los dos agujeros de seguridad que encontré haciendo el mapa

**No los tapé** — la orden de este sprint era no tocar el daemon. Están aquí y
en el inventario de portabilidad (doc 28, clase 4), con fichero y línea:

| Dónde | Qué pasa en Linux |
|---|---|
| `tg_daemon.py:111` | `f"Read({d}\\**)"` con separador `\` **hardcodeado**. En Linux la regla sale `Read(/home/floreano/.ssh\**)` y **no casa con nada**: las denegaciones de `.ssh`, `.aws`, `.gnupg`, `.config/gh` y los `.env` **dejan de aplicar**. No fallan cerrado — fallan abiertas y sin avisar |
| `tg_daemon.py:1229` | `f",Write({repo_path}\\**),Edit({repo_path}\\**)"`, misma causa. Es la **segunda barrera del aislamiento de T2**, la que protege el árbol del usuario en modo escritura. En Linux se evapora |

Los dos son inertes en Windows, que es donde el puente ha corrido siempre. **Se
activan justo al llevarlo a la SER8**, que es el plan.

---

## Lo que este mapa deja dicho, en una línea

De las tres capas del setup —skills, vault y hooks—, al puente le llega **una y
media**: las skills de dos superficies de tres, el vault **no**, y los hooks
**ninguno**. El puente no es una vista del setup: es un **segundo sistema** con
sus propias reglas, que hoy coinciden en 5 de 8 con las de la casa.
