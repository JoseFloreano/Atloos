# Plantilla: prompt de tarea programada ("heartbeat barato")

Plantilla obligatoria para **todo** scheduled task periódico — de Cowork o de
cron/Programador de tareas con `claude -p`. Implementa R1 del doc
`docs/ecosistema/16-AHORRO-TOKENS-ROBADO-DE-HERMES-OPENCLAW.md`.

**El problema que resuelve:** una tarea periódica que arranca al agente "a ver
si hay algo" paga contexto completo cada corrida, la mayoría de las cuales no
tienen nada que hacer. Con sesión aislada + gate previo, OpenClaw documenta
bajar de **~100K a 2-5K tokens por corrida** (cifra suya, no verificada por
nosotros; el orden de magnitud sí es estructural: es la diferencia entre
arrastrar historial y arrancar en frío, o entre invocar al LLM y no invocarlo).

## Las 3 reglas

1. **Gate SIN LLM primero.** La condición barata se evalúa antes de que exista
   una llamada al modelo: archivo checklist no vacío, `git status` con cambios,
   inbox con items, mtime más nuevo que X. **Nada que hacer → no se invoca a
   Claude en absoluto.** En cron el gate vive en el script (coste real: 0
   tokens). En Cowork no hay wrapper, así que el gate son las **primeras líneas
   del prompt** y la orden de terminar de inmediato (coste: un turno mínimo).
2. **Sesión aislada y prompt corto.** Nunca `--resume` de un historial
   kilométrico: cada corrida arranca fresca. La continuidad la da el vault, no
   el transcript. Añade `--max-turns` para acotar el peor caso.
3. **Convención "nada que reportar → `OK`".** La tarea responde exactamente
   `OK` y nada más; quien la consume descarta los `OK` sin entregarlos. Así el
   canal de avisos solo suena cuando hay señal.

## Plantilla — cron / Programador de tareas (`claude -p`)

El gate va en el script; si no pasa, Claude nunca arranca:

```bash
#!/usr/bin/env bash
# <nombre-de-la-tarea> — corre cada <frecuencia>
set -euo pipefail

# ── GATE sin LLM ────────────────────────────────────────────────────────────
<comando barato que decide>   || exit 0   # nada que hacer → 0 tokens, se acabó

# ── Invocación: sesión fresca, prompt corto, turnos acotados ────────────────
out=$(cd "<repo>" && claude -p --max-turns 5 \
  --allowedTools "Read,Grep,Glob" \
  "<instrucción de una o dos frases>. Si no hay nada que reportar responde solo OK.")

[ "$(printf '%s' "$out" | tr -d '[:space:]')" = "OK" ] && exit 0   # se descarta
printf '%s\n' "$out" | "$HOME/.claude/scripts/py" "$HOME/…/setup/telegram-bridge/notify_telegram.py"
```

## Plantilla — scheduled task de Cowork (sin wrapper)

El gate es lo primero del prompt y **termina la corrida**, no la continúa:

```text
1. Verifica <condición barata> — SOLO eso, sin leer nada más.
2. Si <no se cumple>: responde exactamente `OK` y TERMINA. No investigues,
   no resumas, no propongas nada.
3. Solo si se cumple: <tarea real, 1-3 frases, con el alcance acotado>.
   Reporta en <=10 líneas: qué cambió y qué acción concreta pide.
```

## Ejemplo relleno — revisión quincenal de drift del vault

```bash
#!/usr/bin/env bash
# drift-check.sh — cada 15 días. Gate: ¿algún repo commiteó después de que su
# _PROJECT.md se actualizara por última vez?
set -euo pipefail
VAULT="$HOME/OneDrive/DevSetup/ObsidianVault/10-Projects"
stale=""
for p in "$VAULT"/*/; do
  name=$(basename "$p"); repo="$HOME/…/Proyectos/$name"
  [ -d "$repo/.git" ] || continue
  last_commit=$(git -C "$repo" log -1 --format=%ct 2>/dev/null || echo 0)
  vault_mtime=$(stat -c %Y "$p/_PROJECT.md" 2>/dev/null || echo 0)
  [ "$last_commit" -gt "$((vault_mtime + 604800))" ] && stale="$stale $name"
done
[ -n "$stale" ] || exit 0        # ← gate: sin drift, cero tokens

out=$(claude -p --max-turns 5 --allowedTools "Read,Grep,Glob" \
  "Proyectos con vault desfasado:$stale. Para cada uno, lee su _PROJECT.md y di
   en 1-2 líneas qué sección falta actualizar. Si ninguno lo necesita responde solo OK.")
[ "$(printf '%s' "$out" | tr -d '[:space:]')" = "OK" ] && exit 0
printf '%s\n' "$out" | "$HOME/.claude/scripts/py" "$HOME/…/setup/telegram-bridge/notify_telegram.py"
```

En Cowork, la misma tarea sin wrapper:

```text
1. Lista 10-Projects/*/_PROJECT.md y lee SOLO su frontmatter `updated`.
2. Si ninguno tiene `updated` de hace más de 15 días: responde `OK` y TERMINA.
3. Si alguno lo tiene: para ESOS (máximo 3), di en 1-2 líneas qué falta
   actualizar. No abras ADRs, no reorganices nada, no toques otros proyectos.
```

## Antipatrones

- "Revisa si hay algo pendiente y avísame" sin gate — paga contexto completo
  para responder "no hay nada", cada hora, para siempre.
- Reusar la misma sesión entre corridas (`--resume` fijo): el historial crece
  sin techo y se paga entero en cada turno.
- Dejar que la tarea "aproveche el viaje" (auditar de paso, refactorizar): un
  heartbeat que hace trabajo no solicitado es un heartbeat que no se puede
  correr seguido.
- Notificar el `OK`: entrena a ignorar el canal.
