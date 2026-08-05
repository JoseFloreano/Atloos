---
name: workstream-merge-gate
description: >
  El criterio verificable para integrar la rama de un frente a main: artefacto
  verificado (no el reporte), verde posterior al último commit con tests que el
  implementador no escribió, integración serializada en un solo agente, squash,
  confirmación humana y limpieza. Use when the user says "mergea el frente",
  "integra la rama", "ya está listo para main", "cierra el workstream", "puedo
  mergear esto", or antes de integrar cualquier rama de trabajo paralelo. NO
  usar para el merge del puente Telegram (ese lo gobierna el daemon).
---

# Workstream Merge Gate

Generaliza el gate de `ADR-20260801-puente-telegram` para sesiones normales de
Claude Code, donde **no hay daemon que lo garantice**. Aquí el criterio es
probabilístico hasta que exista el hook de W3, así que la disciplina la pones tú.

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

2. **Verde DESPUÉS del último commit del frente**, no antes. Y con tests que el
   implementador **no escribió ni editó en esa tarea**. Si los tocó, aplica los
   3 criterios del revisor **antes** de aceptar el verde:
   ¿fijaba el borde de lo cambiado? ¿pierde poder de discriminación? ¿tocó dato
   o lógica? (`workstream-dispatch/references/revisor.md` §3).

3. **La duración de la suite también es señal.** Si el verde llegó en un tiempo
   imposible contra el histórico, **no es verde**: investiga. Un instrumento sin
   `load_dotenv()` "midió" 1,5 M de filas en 3,6 s.

4. **Integración serializada: UN solo agente** —el coordinador o un integrador
   único— corre la suite de integración y mergea. **Un frente a la vez, en orden
   explícito.** Paraleliza lo que quieras; la validación pasa por un cuello único.

5. **Squash por defecto**, con mensaje que resuma el frente (no el histórico de
   commits del subagente).

6. **Destino `main` ⇒ confirmación humana explícita.** Siempre; `main` es la rama
   protegida, sin configuración por repo.

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
