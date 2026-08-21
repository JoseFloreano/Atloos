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

Generaliza el gate de `ADR-20260801-puente-telegram` a sesiones normales: el
hook `merge-gate-guard` bloquea por máquina lo verificable —merge, `pull` y
`push` a `main` sin verde—; el resto lo pones tú.

La ley: **el código de salida no es el estado, y el reporte no es el artefacto.**

## Cuándo usar

- Integrar la rama de un frente a `main`.
- **Encadenar** una tarea sobre el trabajo de otro subagente (mismo paso 1).
- Saber si un frente está realmente listo.

## Requisitos

- **Comando de test declarado** en `.claude/settings.json` bajo
  `env.GATE_TEST_CMD`, como argv y **sin `&&` ni pipes**. Sin él **no hay verde
  posible y no se mergea**: `references/comando-de-test.md`.
- `git` y acceso al worktree del frente.

## Los 7 pasos

1. **Verifica el ARTEFACTO, no el reporte.** `git log -1 <rama>` y **compara el
   hash contra el que reportó el agente**; el fichero de reporte **existe** en
   la ruta que dijo; el worktree está **limpio**. Dos fallos en un solo día por
   saltarse esto: `references/por-que-cada-paso.md`.

2. **Verde DESPUÉS del último commit del frente**, y **corrido por el helper** —
   tu palabra no es evidencia:

   ```
   "$HOME/.claude/scripts/py" "$HOME/.claude/scripts/gate-test.py" <rama>
   ```

   Solo con exit 0 escribe `.claude/gate-verde.json`, que es lo que el hook
   exige para dejar pasar un merge **y también un `git push`** a `main`. Y con
   tests que el implementador **no escribió ni editó**; si los tocó, aplica
   antes los 3 criterios del revisor
   (`workstream-dispatch/references/revisor.md` §3).

3. **El reloj: una corrida sospechosamente RÁPIDA no es un verde.** Compárala
   contra el suelo **de ESTA máquina**; por debajo de ~⅔, cuenta cuántos tests
   corrieron. En campo cazó dos verdes falsos, **ninguno por exit code**.
   ⚠ Un suelo **sin máquina escrita no se usa**: se remide.
   ⚠ **Suelo, nunca techo**: lento no es sospechoso →
   `references/criterio-del-reloj.md`.

4. **Integración serializada: UN solo agente** corre la suite y mergea, **un
   frente a la vez**. Paraleliza lo que quieras; la validación pasa por un
   cuello único.

5. **Squash por defecto**, con mensaje que resuma el frente.

6. **Destino `main` ⇒ confirmación humana explícita.** Sin excepción.

7. **Limpieza**: quita el worktree y borra la rama ya mergeada, **local y
   remota**. Tras un squash, `git branch -d` no la reconoce. ⚠ Y `git worktree
   prune` **falla en OneDrive sin decir que hay otra vía** →
   `references/por-que-cada-paso.md`.

   Ya no es solo una instrucción: `setup/scripts/py setup/scripts/limpia-ramas.py
   --remotas` [repo] lista lo integrado (detecta el squash **por contenido**) y
   borra solo con `--borrar` → `references/por-que-cada-paso.md`.

## Cuando el gate rechaza

Rechazar es el trabajo del gate, no un fallo: devuelve **qué** falló y **qué
falta**, no un "no". Si el frente no puede dar verde, apárcalo con el motivo
escrito — **mal merge es peor que ningún merge**.

## Relación con otras piezas

- Despachar y coordinar los frentes: `workstream-dispatch`.
- Cerrar la sesión: cada frente escribe **su nota** en `sessions/`, nunca
  `_PROJECT.md`; `session-close` consolida.
