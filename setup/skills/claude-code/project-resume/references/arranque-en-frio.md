# Arranque en frío — el detalle de los pasos 2 y 3

Extraído del `SKILL.md` de `project-resume` (sprint 4), literal. El cuerpo se
queda con qué leer; aquí está el cómo.

## El backlog no se abre al arrancar

Si `_PROJECT.md` trae la línea `Backlog: N ítems → [[pendientes]]`, **menciónala
sin abrir el archivo** ("hay N más en el backlog"): el arranque debe costar lo
mismo que antes. Solo cárgalo si el usuario pregunta por el backlog.

## El campo `Estado del repo:` cuando falta

Compara **`Estado del repo:`** contra `origin/main`: si difieren, avisa *"el
vault va atrás — tómalo como orientación, no como verdad"*. Si el campo no está
(proyecto anterior a la convención), **dilo UNA vez**: `session-close` lo
añadirá al cerrar.

## El índice de ADRs, y qué hacer si no existe

Si `_INDEX.md` no existe, el proyecto aún no está migrado: lee los ~3 ADRs más
recientes como antes y avisa al usuario de que falta generar el índice.

El script se invoca por ruta absoluta —`sync-skills` lo instala en
`~/.claude/scripts/`, misma ruta en toda máquina y sin depender de OneDrive:

```
py "$HOME/.claude/scripts/adr-index.py" <ruta ADRs>
```
```powershell
py "$env:USERPROFILE\.claude\scripts\adr-index.py" <ruta ADRs>
```

Si no está, corre `sync-skills` primero.
