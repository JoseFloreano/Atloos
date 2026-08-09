---
name: workstream-dispatch
description: >
  Despacha subagentes implementadores y revisores con el contrato completo que
  la evidencia local exige: estado del mundo generado, ownership por archivo,
  presupuesto con número, predicción, y escalación por categoría de riesgo con
  el coordinador de juez. Capa DELGADA sobre subagent-driven-development de
  Superpowers — no lo reemplaza. Use when the user says "despacha subagentes",
  "lanza implementadores", "reparte el plan", "monta los frentes", "coordina
  este plan", "revisa lo que hizo el subagente", or antes de mandar cualquier
  tarea a un subagente que vaya a escribir código. NO usar para despachar
  investigación de solo lectura (eso es dispatching-parallel-agents).
---

# Workstream Dispatch

Superpowers ya trae el ciclo controller → implementer → reviewer
(`superpowers:subagent-driven-development`, SDD). **Esta skill no lo repite: añade lo que
SDD no trae** y que 22 despachos reales del 2026-08-04 demostraron que hace
falta (`docs/subagentes/05-LIMITACIONES-OBSERVADAS.md`).

La conclusión que la gobierna: **el desfase casi nunca vino de la capacidad del
modelo, vino del traspaso.** Un modelo mejor con el mismo brief incompleto hace
el mismo trabajo inútil, más caro.

## Cuándo usar

- Vas a despachar un subagente que **escribe** (implementador, arreglador).
- Vas a despachar un **revisor** de trabajo ya hecho.
- Coordinas 2+ frentes en paralelo y hay que repartir propiedad de archivos.
- **También para despachar una auditoría adversarial de un DISEÑO aprobado,
  ANTES del spec** — el crítico limpio, una fase antes. En campo tumbó un diseño
  con 3 afirmaciones de carga falsas a costo de cero líneas escritas.

## Requisitos

- SDD de Superpowers instalado (`superpowers:sdd-workspace`, `superpowers:task-brief`). Sin él, el flujo
  sigue valiendo pero los briefs se extraen a mano — nunca pegando el plan entero.
- Workspace de la jornada: `.superpowers/sdd/<plan>/`. **Está gitignorado**
  (`*`), así que es andamiaje por máquina, no registro auditable: lo que deba
  sobrevivir va al vault o al mensaje de commit.

## Pasos

1. **Antes del primer despacho de 2+ frentes, presenta la partición al usuario**
   (qué frentes y qué archivos posee cada uno) y espera su OK. Es la decisión de
   mayor apalancamiento y la única barata de corregir antes de gastar.
2. **Genera el estado del mundo** — no lo escribas de memoria. Es el bloque 2 de
   la plantilla y lo que más desfases evitó.
3. **Arma el despacho con los 7 bloques obligatorios** →
   [`references/plantilla-despacho.md`](references/plantilla-despacho.md).
   Ninguno es opcional: cada uno corresponde a un fallo que ya ocurrió.
4. **Al recibir `NEEDS_CONTEXT`**, actúa de juez →
   [`references/protocolo-escalacion.md`](references/protocolo-escalacion.md).
   Registra la resolución **antes** de re-despachar.
5. **Despacha el revisor con contexto limpio** →
   [`references/revisor.md`](references/revisor.md). El revisor muta, no opina.
6. **Verifica el artefacto, no el reporte**: `git log -1` contra los hashes
   reportados, el fichero de reporte existe, el worktree está limpio. Dos fallos
   ese día por saltarse esto. Para mergear: `workstream-merge-gate`.

## Las tres prohibiciones del coordinador

- **No implementes tú lo que despachaste.** Tu contexto queda limpio para juzgar.
- **No paralelices implementadores dentro del mismo frente** (conflictos; lo
  prohíbe SDD y lo confirmó el C compiler de 16 agentes).
- **Máximo 3 frentes simultáneos** (RFD 04 C5). El techo real observado no fue el
  modelo ni la coordinación: fue la **RAM de la máquina**.

## Referencias

- `references/plantilla-despacho.md` — los 7 bloques de todo despacho.
- `references/protocolo-escalacion.md` — disparadores, `NEEDS_CONTEXT` y el juez.
- `references/revisor.md` — el contrato del revisor.
