# Hooks — Enforcement determinista (auditoría R2)

El aislamiento de memoria por proyecto NO puede depender solo de instrucciones
en CLAUDE.md (compliance probabilística que se degrada en sesiones largas).
Estos hooks lo convierten en garantía: la llamada inválida se **bloquea antes
de ejecutarse** y Claude recibe el motivo para autocorregirse.

> Solo aplica a **Claude Code** (los hooks de sesión no corren sobre tu disco
> en Cowork). En Cowork la mitigación equivalente es montar por proyecto solo
> `10-Projects/<proyecto>/` + `brain/`, no el vault completo.

## Hooks incluidos

| Hook | Evento | Qué garantiza |
|------|--------|---------------|
| `validate-graphiti-group-id.py` | PreToolUse sobre `mcp__graphiti*` | Ningún `add_episode` sin `group_id` válido; ninguna búsqueda sin `group_ids`. Bloquea `main`, vacío y placeholders |
| `mark-code-dirty.py` | PostToolUse sobre `Write\|Edit\|MultiEdit` | Marca flag cuando la sesión edita CÓDIGO (los .md no cuentan) — insumo del siguiente |
| `check-vault-updated.py` | Stop | Anti-drift del vault: si hubo código editado y `_PROJECT.md` no se actualizó después, bloquea el cierre (exit 2) pidiendo SOLO pendientes/estado. **Una vez por sesión**, respeta `stop_hook_active`, silencio total en proyectos sin onboarding. Sale en silencio si `CLAUDE_TG_BOT=1` (sesiones del daemon de Telegram: no hay humano para cerrar el vault y bloquear colgaría la respuesta del bot — ADR puente-telegram §7). El cierre completo es de la skill `session-close` |
| `memory-flush.py` | PreCompact (`manual` y `auto`) | Anti-drift en la compactación (R5 del doc 16): con el mismo flag, si el vault sigue desfasado **pausa la compactación una vez** y pide volcar pendientes/decisiones antes de que el contexto se resuma. Sin flag → silencio. PreCompact **no admite `additionalContext`**: su único canal hacia Claude es exit 2, que en este evento significa "blocks compaction" — de ahí la pausa. Marca `precompact_flushed` para no repetirla (una auto-compactación bloqueada en bucle ahogaría la sesión) |

Requiere Python 3 en el PATH (`python3` en macOS/Linux, `python` en Windows).

## Hook de git (aparte — no es hook de Claude Code)

| Hook | Evento | Qué garantiza |
|------|--------|---------------|
| `git-post-commit-graph-report.sh` | git `post-commit` (por repo) | El `codebase-map.md` del vault se regenera con Graphify en cada commit que toque código (commits solo de docs no disparan). El grafo deja de driftear entre cierres — `session-close` ya no regenera, solo verifica que este hook esté instalado |

Instalación por repo (solo donde corre Graphify):

```bash
cp setup/hooks/git-post-commit-graph-report.sh <repo>/.git/hooks/post-commit
chmod +x <repo>/.git/hooks/post-commit
```

Nota de migración: versiones previas copiaban `graph-report.md`; el nombre
canónico ahora es `codebase-map.md` (el que lee el snippet de memoria y
`project-resume`). El hook borra el nombre viejo automáticamente.

## Instalación

### La forma fácil (Windows) — `sync-hooks.ps1`

```powershell
.\sync-hooks.ps1
```

Copia los `.py` a `~/.claude/hooks/` (y a cada `~/.claude-*/hooks/` en multi-cuenta)
y **cablea `settings.json` de forma idempotente** (con backup). Elige `py` como
intérprete automáticamente (en Windows `python` suele ser el stub del Store). El
bootstrap `setup-new-machine.ps1` ya lo invoca. Corre este script tras editar
cualquier hook — no hay sync automático como el de las skills.

### Manual (para entender el cableado, o en macOS/Linux)

1. Copia el script a tu config de Claude Code (y a tu repo de dotfiles):

   ```bash
   mkdir -p ~/.claude/hooks && cp validate-graphiti-group-id.py ~/.claude/hooks/
   ```

2. Fusiona esto en `~/.claude/settings.json` (ajusta `python3`→`python`/`py` en
   Windows y `~` a tu ruta absoluta si tu shell no la expande):

   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "mcp__graphiti",
           "hooks": [
             { "type": "command",
               "command": "python3 ~/.claude/hooks/validate-graphiti-group-id.py" }
           ]
         }
       ],
       "PostToolUse": [
         {
           "matcher": "Write|Edit|MultiEdit",
           "hooks": [
             { "type": "command",
               "command": "python3 ~/.claude/hooks/mark-code-dirty.py" }
           ]
         }
       ],
       "Stop": [
         {
           "hooks": [
             { "type": "command",
               "command": "python3 ~/.claude/hooks/check-vault-updated.py" }
           ]
         }
       ],
       "PreCompact": [
         {
           "hooks": [
             { "type": "command",
               "command": "python3 ~/.claude/hooks/memory-flush.py" }
           ]
         }
       ]
     }
   }
   ```

3. Verifica en una sesión nueva:
   - Graphiti: pide guardar un episodio **sin** group_id — debe bloquearse.
   - Anti-drift: en un proyecto enganchado, pide un cambio de código trivial y
     deja que termine — al final debe pedir actualizar pendientes UNA vez
     (y no repetirlo en el mismo chat tras cumplir).
   - Memory flush: en esa misma sesión (con el flag ya puesto), corre `/compact`
     — debe pausarse una vez con el recordatorio; el segundo `/compact` pasa. En
     una sesión que solo tocó `.md`, `/compact` no dice nada.

> Añade `.claude/vault-dirty.json` al `.gitignore` de tus proyectos (es estado
> de sesión local, no se versiona).

## Diseño

- **Fail-open** ante entrada ilegible: si el JSON del hook no parsea, no
  bloquea (un bug del hook no debe tumbar el resto de herramientas).
- **Fail-closed** ante group_id ausente/prohibido: exit 2 + mensaje accionable.
- El multi-cuenta hereda el hook si copias `hooks/` + settings a cada
  `CLAUDE_CONFIG_DIR` (el sync de dotfiles ya contempla `settings.json`).
