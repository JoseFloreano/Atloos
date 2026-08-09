---
name: goal-forge
description: >
  Convierte un objetivo difuso en una condición de `/goal` que no se puede
  fingir: un estado final medible MÁS el comando que lo prueba, con cláusula de
  corte. Use when the user says "pon una meta", "forja la condición", "/goal",
  "déjalo corriendo hasta que", "que no pare hasta", "arranca el bucle",
  "condición de salida", or ANTES de escribir cualquier `/goal` en este setup.
  También al cerrar un despacho de `workstream-dispatch`, porque el criterio de
  salida del subagente y la condición de la meta son el mismo objeto.
---

# Goal Forge

El evaluador de `/goal` **no ejecuta herramientas**: juzga solo lo que apareció
en la conversación. Si el turno dice *"corrí los tests y pasaron"*, lo cree y
cierra la meta. Una condición mal forjada no es un detalle de estilo: es la ley
1 rota, corriendo sola de noche.

## Requisitos

- Claude Code **v2.1.139+**. Sin `/goal`, el fallback es un Stop hook propio
  (`hooks/README.md`); no lo emules pidiéndole al modelo que "siga hasta".
- Un comando que **produzca evidencia en disco**. El de la casa es
  `gate-test.py`, que solo con exit 0 escribe un JSON con el `sha`.

## El contrato — los 5 puntos, todos

1. **Un solo estado final medible**: un exit code, un conteo, una cola vacía.
   Dos condiciones unidas por "y" son dos metas; parte el trabajo.
2. **El comando que lo prueba, nombrado DENTRO de la condición.** No *"el arnés
   pasa"*, sino: [repo]
   *"`py setup/hooks/tests/test-merge-gate-guard.py` imprime `23/23 casos OK`"*. [repo]
3. **Las restricciones que no deben cambiar** por el camino: qué no se toca,
   qué no se mergea, qué sigue verde.
4. **Cláusula de corte, obligatoria**: `o para a los 20 turnos`. Sin fondo, un
   bucle que no converge gasta hasta que alguien mira.
5. **Rechaza lo que solo puede satisfacer una afirmación.** *"El código queda
   limpio"* no es condición; *"`ruff check .` sale 0"* sí. Si no sabes qué
   comando la prueba, el objetivo aún no está entendido — eso es lo que la
   skill acaba de descubrir, y decirlo vale más que forjar algo vacío.

## Pasos

1. Reformula el objetivo hasta que cumpla los 5 puntos. Si no puedes, **párate
   y dilo**: mal forjada es peor que sin forjar.
2. Escribe `.claude/goal.json` con `condicion`, `artefacto` (ruta del fichero
   de evidencia), `cmd`, `turnos` y `forjada_ts`. Es lo que lee el hook
   `goal-evidence-guard`, que cierra la meta contra el disco.
3. Entrega la línea `/goal …` lista para pegar, y di qué artefacto vigilará.
4. Verifica: ¿la condición nombra un comando? ¿tiene corte? ¿la puede satisfacer
   una frase? Si sí, vuelve al 1.

## Límites duros — dilos, no los descubras

- **Una meta activa por sesión**; una nueva reemplaza a la anterior.
- **4.000 caracteres** de condición.
- **`--resume` reinicia el contador de turnos**: tras un kill, la cláusula de
  corte deja de acotar. Detalle y ejemplos en `references/mecanica-goal.md`.
