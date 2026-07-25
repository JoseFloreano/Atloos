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
| `check-vault-updated.py` | Stop | Anti-drift del vault: si hubo código editado y `_PROJECT.md` no se actualizó después, bloquea el cierre (exit 2) pidiendo SOLO pendientes/estado. **Una vez por sesión**, respeta `stop_hook_active`, silencio total en proyectos sin onboarding. El cierre completo es de la skill `session-close` |

Requiere Python 3 en el PATH (`python3` en macOS/Linux, `python` en Windows).

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
       ]
     }
   }
   ```

3. Verifica en una sesión nueva:
   - Graphiti: pide guardar un episodio **sin** group_id — debe bloquearse.
   - Anti-drift: en un proyecto enganchado, pide un cambio de código trivial y
     deja que termine — al final debe pedir actualizar pendientes UNA vez
     (y no repetirlo en el mismo chat tras cumplir).

> Añade `.claude/vault-dirty.json` al `.gitignore` de tus proyectos (es estado
> de sesión local, no se versiona).

## Diseño

- **Fail-open** ante entrada ilegible: si el JSON del hook no parsea, no
  bloquea (un bug del hook no debe tumbar el resto de herramientas).
- **Fail-closed** ante group_id ausente/prohibido: exit 2 + mensaje accionable.
- El multi-cuenta hereda el hook si copias `hooks/` + settings a cada
  `CLAUDE_CONFIG_DIR` (el sync de dotfiles ya contempla `settings.json`).
