---
name: workstream-dispatch
description: >
  Despacha subagentes implementadores y revisores con el contrato que la
  evidencia local exige: estado del mundo generado, ownership por archivo,
  presupuesto y modelo por frente, predicción, destino de la rama y escalación
  por categoría de riesgo con el coordinador de juez. Use when the user says
  "despacha subagentes", "lanza implementadores", "reparte el plan", "monta los
  frentes", "coordina este plan", "revisa lo que hizo el subagente", or antes de
  mandar cualquier tarea a un subagente que vaya a escribir código. ÚSALA JUNTO
  A `superpowers:subagent-driven-development`, no en su lugar: SDD pone el CICLO
  (controller → implementer → reviewer, con revisor por tarea obligatorio) y
  esta pone el CONTRATO del despacho y los LÍMITES (8 bloques, 3 frentes con
  fecha). Donde discrepen en un número, gana el más restrictivo. NO usar para
  despachar investigación de solo lectura (eso es
  `superpowers:dispatching-parallel-agents`).
---

# Workstream Dispatch

**Añade lo que `superpowers:subagent-driven-development` (SDD) no trae**, medido
en 22 despachos reales (`docs/subagentes/05-LIMITACIONES-OBSERVADAS.md`): **el
desfase casi nunca vino del modelo, vino del traspaso.**

## Quién gobierna qué cuando SDD también está cargada

Decir *"capa delgada sobre SDD"* no bastó: el agente mezcló las dos y ninguna
avisó del conflicto.

| Materia | Manda |
|---|---|
| El ciclo, y **un revisor por tarea** | `superpowers:subagent-driven-development` |
| Los 8 bloques, ownership, escalación | esta skill |
| Los límites numéricos (3 frentes) | esta skill |
| Un número en el que discrepen | **el más restrictivo** |

`references/gobierno-vs-sdd.md`.

## Cuándo usar

- Un subagente que **escribe**, o un **revisor**.
- 2+ frentes con propiedad de archivos que repartir.
- Una **auditoría adversarial de un DISEÑO aprobado, ANTES del spec**: tumbó un
  diseño con 3 afirmaciones falsas a coste cero.

## Requisitos

- SDD instalado (`superpowers:sdd-workspace`, `superpowers:task-brief`); sin él,
  briefs a mano — nunca el plan entero.
- Workspace en `.superpowers/sdd/<plan>/`, **gitignorado**: lo que deba
  sobrevivir va al vault o al mensaje de commit.

## Pasos

1. **Presenta la partición al usuario** antes del primer despacho de 2+ frentes
   y espera su OK: es la decisión de mayor apalancamiento y la única barata.
2. **Genera el estado del mundo** con comandos (bloque 2): **manifiesto de lo
   que git no versiona** y **firma del fallo conocido con su conteo de skips**.
3. **Arma el despacho con los 8 bloques** → `references/plantilla-despacho.md`,
   con **modelo y núcleos por frente** (bloque 5) e higiene →
   `references/higiene-de-shell.md`, `references/higiene-de-salida.md`. El
   criterio de salida (bloque 7) **es** la
   condición de meta si el frente corre desatendido: fórjala con
   `claude-code:goal-forge`. El destino de la rama (bloque 8) se decide **aquí**.
4. **Al recibir `NEEDS_CONTEXT`**, actúa de juez →
   `references/protocolo-escalacion.md`, y registra la resolución **antes** de
   re-despachar.
5. **Revisor con contexto limpio** → `references/revisor.md`. Muta, no opina.
   Uno por tarea, que es de SDD y no es opcional.
6. **Verifica el artefacto, no el reporte**: hashes, worktree limpio, y ejecuta
   el destino de cada rama al cerrar su frente. Para mergear:
   `workstream-merge-gate`.
7. **Criterio de aceptación numérico → cláusula de NO-PÉRDIDA al lado**, y el
   frente entrega las dos medidas: `references/no-perdida.md`. Un número se
   cumple destruyendo; dos, no.

## Las tres prohibiciones del coordinador

- **No implementes tú lo que despachaste.** Tu contexto queda limpio para juzgar.
- **No paralelices implementadores dentro del mismo frente** (lo prohíbe SDD y
  lo confirmó el C compiler de 16 agentes).
- **3 frentes por defecto — dato con fecha, no dogma**: una medición
  autorreportada (2026-08-10, ×2,05 con 5) **de la suite de otra máquina**, cuyo
  tamaño no consta. Se sube **midiendo** → `references/medir-el-techo.md`.
