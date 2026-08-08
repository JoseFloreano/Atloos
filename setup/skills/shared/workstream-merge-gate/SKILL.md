---
name: workstream-merge-gate
description: >
  El criterio verificable para integrar CUALQUIER rama a main: artefacto
  verificado (no el reporte), verde posterior al último commit con tests que el
  implementador no escribió, integración serializada en un solo agente, squash,
  confirmación humana y limpieza. Use when the user says "integra la rama a
  main", "integra X a main", "mergea esta rama", "mergea el frente", "la rama ya
  está lista, intégrala", "mete esto a main", "ya está listo para main", "cierra
  el workstream", "puedo mergear esto", or antes de integrar cualquier rama —
  venga o no de trabajo paralelo. ÚSALA EN VEZ DE
  `superpowers:finishing-a-development-branch` siempre que el destino sea `main`
  o la rama protegida: esa skill no tiene confirmación humana ni squash por
  defecto, y en prueba deliberada dejó pasar 2 merges a main sin OK. NO usar
  para el merge del puente Telegram (ese lo gobierna el daemon).
---

# Workstream Merge Gate

Generaliza el gate de `ADR-20260801-puente-telegram` a sesiones normales. El
hook `merge-gate-guard` ya bloquea por máquina el merge a `main` sin verde
verificable; el resto del criterio lo pones tú.

La ley que lo gobierna: **el código de salida no es el estado, y el reporte no
es el artefacto.**

## Cuándo usar

- Vas a integrar la rama de un frente a `main`.
- Vas a **encadenar** una tarea sobre el trabajo de otro subagente (mismo paso 1).
- Quieres saber si un frente está realmente listo.

## Requisitos

- **Comando de test declarado** para el proyecto. Sin él **no hay verde posible
  y no se mergea** — redefine el verde (build? lint?) o el patrón no aplica aquí.
- `git` y acceso al worktree del frente.

## Los 7 pasos

1. **Verifica el ARTEFACTO, no el reporte.** Antes de encadenar o mergear:
   - `git log -1 <rama>` y **compara el hash contra el que reportó el agente**;
   - el fichero de reporte **existe** en la ruta que dijo;
   - el worktree está **limpio** (`git status --porcelain` vacío).

   Dos fallos en un solo día por saltarse esto: uno reportó un fichero que nunca
   escribió; otro reportó 23 arreglos y suite verde, y **nunca commiteó**.

2. **Verde DESPUÉS del último commit del frente**, no antes, y **corrido por el
   helper** — tu palabra no es evidencia:

   ```
   py "$HOME/.claude/scripts/gate-test.py" <rama>
   ```

   Solo con exit 0 escribe `.claude/gate-verde.json`, que es lo que el hook
   `merge-gate-guard` exige para dejar pasar un merge a `main`. Y con tests que
   el implementador **no escribió ni editó en esa tarea**. Si los tocó, aplica
   los 3 criterios del revisor **antes** de aceptar el verde:
   ¿fijaba el borde de lo cambiado? ¿pierde poder de discriminación? ¿tocó dato
   o lógica? (`workstream-dispatch/references/revisor.md` §3).

3. **La duración de la suite también es señal.** Si el verde llegó en un tiempo
   imposible contra el histórico, **no es verde**: investiga. Un instrumento sin
   `load_dotenv()` "midió" 1,5 M de filas en 3,6 s.

4. **Integración serializada: UN solo agente** corre la suite de integración y
   mergea, **un frente a la vez**. Paraleliza lo que quieras; la validación pasa
   por un cuello único.

5. **Squash por defecto**, con mensaje que resuma el frente (no el histórico de
   commits del subagente).

6. **Destino `main` ⇒ confirmación humana explícita.** Siempre, sin excepción.

7. **Limpieza tras integrar**: quitar el worktree y borrar la rama local ya
   mergeada. Ojo: tras un squash, `git branch -d` no la reconoce como integrada.

## Cuando el gate rechaza

Rechazar es el trabajo del gate, no un fallo. Devuelve **qué** falló y **qué
falta**, no un "no". Si el frente no puede dar verde, la salida legítima es
aparcarlo con el motivo escrito: **mal merge es peor que ningún merge**.

## Relación con otras piezas

- Despachar y coordinar los frentes: `workstream-dispatch`.
- Cerrar la sesión del frente en el vault: cada frente escribe **su nota** en
  `sessions/`, nunca `_PROJECT.md` (RFD 04 C7); `session-close` consolida.
