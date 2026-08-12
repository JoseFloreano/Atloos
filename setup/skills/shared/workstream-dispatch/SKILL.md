---
name: workstream-dispatch
description: >
  Despacha subagentes implementadores y revisores con el contrato completo que
  la evidencia local exige: estado del mundo generado, ownership por archivo,
  presupuesto con número, predicción, destino de la rama y escalación por
  categoría de riesgo con el coordinador de juez. Use when the user says
  "despacha subagentes", "lanza implementadores", "reparte el plan", "monta los
  frentes", "coordina este plan", "revisa lo que hizo el subagente", or antes de
  mandar cualquier tarea a un subagente que vaya a escribir código. ÚSALA JUNTO
  A `superpowers:subagent-driven-development`, no en su lugar: SDD pone el CICLO
  (controller → implementer → reviewer, y el revisor por tarea, que sigue siendo
  obligatorio) y esta pone el CONTRATO del despacho y los LÍMITES (8 bloques,
  ownership por archivo, máximo 3 frentes). Donde discrepen en un número, gana
  el más restrictivo. NO usar para despachar investigación de solo lectura (eso
  es `superpowers:dispatching-parallel-agents`).
---

# Workstream Dispatch

**Añade lo que `superpowers:subagent-driven-development` (SDD) no trae**, y que
22 despachos reales demostraron necesario
(`docs/subagentes/05-LIMITACIONES-OBSERVADAS.md`). La conclusión que la
gobierna: **el desfase casi nunca vino del modelo, vino del traspaso.**

## Quién gobierna qué cuando SDD también está cargada

Decir *"capa delgada sobre SDD"* no bastó: el agente mezcló las dos sin que
ninguna mandara — **sin revisores por tarea** (los pide SDD) y con **5 frentes**
contra el máximo de 3, y ninguna avisó del conflicto.

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

- SDD instalado (`superpowers:sdd-workspace`, `superpowers:task-brief`); sin él
  los briefs se extraen a mano, nunca pegando el plan entero.
- Workspace en `.superpowers/sdd/<plan>/`, **gitignorado**: lo que deba
  sobrevivir va al vault o al mensaje de commit.

## Pasos

1. **Presenta la partición al usuario** antes del primer despacho de 2+ frentes
   y espera su OK: es la decisión de mayor apalancamiento y la única barata.
2. **Genera el estado del mundo** con comandos, no de memoria (bloque 2), con
   **la firma del fallo de entorno conocido** — sin ella seis frentes te
   devuelven el mismo rojo mal diagnosticado.
3. **Arma el despacho con los 8 bloques** → `references/plantilla-despacho.md`.
   El criterio de salida del bloque 7 **es** la condición de meta si el frente
   corre desatendido: fórjala con `claude-code:goal-forge`. Y el bloque 8, el
   destino de la rama, se decide **aquí**.
4. **Al recibir `NEEDS_CONTEXT`**, actúa de juez →
   `references/protocolo-escalacion.md`, y registra la resolución **antes** de
   re-despachar.
5. **Revisor con contexto limpio** → `references/revisor.md`. Muta, no opina.
   Uno por tarea, que es de SDD y no es opcional.
6. **Verifica el artefacto, no el reporte**: hashes, reporte, worktree limpio. Y
   ejecuta el destino de cada rama al cerrar su frente. Para mergear:
   `workstream-merge-gate`.

## Las tres prohibiciones del coordinador

- **No implementes tú lo que despachaste.** Tu contexto queda limpio para juzgar.
- **No paralelices implementadores dentro del mismo frente** (lo prohíbe SDD y
  lo confirmó el C compiler de 16 agentes).
- **Máximo 3 frentes**, ya no criterio sino **medición**: con 5 la suite pasó de
  ~330 s a **677 s (×2,05)** y una prueba de latencia falló **por carga, no por
  código**. El techo es la máquina.
