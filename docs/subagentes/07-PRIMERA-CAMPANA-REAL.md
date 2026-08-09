---
title: "Ventajas y desventajas del instrumental — jornada del 6 ago 2026"
project: recomendador-cobranza
fecha: 2026-08-06
tipo: retrospectiva-instrumental
alcance: "10 subagentes despachados · 6 ramas integradas · 1 diseño devuelto"
---
> **Promovido:** 2026-08-07 a `docs/subagentes/07` desde el reporte de campo
> del usuario (jornada del 2026-08-06 en `recomendador-cobranza`, otra laptop),
> **sin reescribir su contenido**. Es la evidencia que originó los fallos F3,
> F4, F5, F10 y F11 del RFD 10, cosechado el 2026-08-09 (sus decisiones viven
> en `ADR-20260801-bot-memoria-y-perfil`, `ADR-20260801-higiene-vault` y
> `ADR-20260803-skills-fuente-unica`; el RFD sigue en la historia de git).
>
> ⚠ **Evidencia de campo COMPLEMENTARIA de W2 — NO sustituye la condición 7 del
> RFD 04** (la prueba deliberada del merge-gate), que sigue abierta: en uso real
> no se distingue "el gate lo paró" de "la suite estaba roja de todos modos".

# Qué funcionó del instrumental, y qué no

> Retrospectiva de **una sola jornada**, no una evaluación general. Todo lo que
> afirmo aquí pasó hoy y se puede señalar con el dedo. Donde no medí, lo digo.
> Buena parte de esto es de `setup/`, no de este proyecto: si vale, **promociónalo
> a `brain/`**.

---

## 1 · El resumen, en una tabla

| pieza | ¿se usó? | veredicto |
|---|---|---|
| `workstream-dispatch` | 10 veces | 🟢 **La más rentable del día, con diferencia.** |
| `superpowers:brainstorming` | 1 | 🟢 Su compuerta dura evitó implementar un diseño roto. |
| `workstream-merge-gate` | 1 tanda | 🟢 Cazó un fallo real al integrar. |
| `session-close` | 1 | 🟢 Su paso 8 cazó una edición que yo rompí. |
| `project-resume` | 1 | 🟡 Funcionó, pero **no detecta que el vault esté desfasado**. |
| `adr-writer` / `memory-keeper` | **0** | 🟡 Dos decisiones grandes quedaron sin ADR. |
| **graphify** | **0 veces en todo el día** | 🔴 **Estaba disponible y no lo usé.** Ver §4. |

---

## 2 · `workstream-dispatch` — lo que de verdad movió la aguja

### Lo que funcionó, con evidencia

🔑 **El bloque 6, la predicción obligatoria, es el mecanismo más productivo que
tiene el sistema.** No es una formalidad de proceso: **cinco de diez frentes
fallaron su predicción, y las cinco veces la desviación ERA el hallazgo.**

- Predijo 0 fallos, encontró 1 → ese 1 era un bug de contrato disfrazado de fuente
  caída, que en producción se lee como «hoy no hay aviso».
- Predijo 70/22/8 en la clasificación, salió 32/44/24 → y explicar el −38 pp
  produjo la frase que reordenó el diseño: *el nombre no es un atributo del
  gestor, es su identificador*.
- Predijo 2 bloqueantes, salieron 4 → y la desviación era que dos problemas
  distintos eran el mismo visto dos veces.
- Predijo 4 afirmaciones falsas, salieron 6 → **y las dos que no vio venir eran
  justo las de carga**.

**Sin el bloque 6, cuatro de esos cinco hallazgos se habrían reportado como
éxitos.** Un agente que acierta su predicción entrega un resultado; uno que falla
entrega un resultado **y** una corrección del mapa.

✅ **El bloque 7 («abortar es legítimo») se cobró solo.** Tres frentes devolvieron
`NEEDS_CONTEXT` o `BLOCKED` en vez de forzar un verde. Uno paró teniendo **sus
propios tests en rojo** porque el diagnóstico apuntaba a otro lado — con la frase
correcta: *un pase estructural no debe cambiar ni un byte de lo que viaja al
servidor*.

✅ **El bloque 3 (decisiones del día) evitó el fallo para el que fue creado.** Un
frente chocó con una compuerta de perímetro y **no ensanchó el censo** —el fichero
no era suyo—: reescribió su instrumento y **los números salieron idénticos**. Ese
es exactamente el caso que originó el bloque (dos agentes ensanchando la misma
allow-list para que sus reportes pasaran).

### Lo que le falta, y hoy costó caro

🔴 **No tiene bloque de APROVISIONAMIENTO, y es su agujero más caro.** El proyecto
tiene **tres artefactos fuera de git** (`backend/.env`, `ml_gestiones/gestiones.csv`,
`backend/data/`) y **cuatro flags opt-in** que mueven el conteo de la suite.
Resultado medido: **cuatro frentes perdieron una corrida completa** diagnosticando
como daño lo que era inventario ausente. Uno reportó 256 rojos, otro 294.

> **Propuesta concreta:** el bloque 2 deja de pedir «el conteo actual de la suite»
> y pasa a pedir **los dos conteos (checkout principal y worktree limpio) más la
> lista de artefactos y flags**. El baseline **no es un número**: es un número más
> el estado de cuatro interruptores. Hoy, **42 de 51 skips son una sola variable**.

🔴 **Los briefs no dan ruta propia por frente en el scratchpad.** Un agente
**sobrescribió el fichero de predicciones de otro**. Fallo de montaje, no de
agente. Cada despacho debería llevar su subcarpeta — lo apliqué a mitad de jornada
y dejó de pasar.

🟡 **El ownership funciona como norma, no como barrera.** Dos frentes salieron de
su ownership (uno tocó un `__init__.py` ajeno, otro un `esquemas.py`). **Los dos lo
declararon**, que es lo que salva el mecanismo. Pero nada lo impide.

⚠ **Y el riesgo real no es el agente: es el brief.** De diez despachos, **el mío
metió información equivocada en cuatro**: un ranking de ocurrencias que no medía
dependencia, unas tasas que eran otra métrica, un ejemplo «bueno» que estaba
escrito a mano, y una carpeta de destino que resultó **cerrada con allow-list**.
La skill dice *«el desfase casi nunca vino de la capacidad del modelo, vino del
traspaso»* — hoy se confirmó **cuatro veces**, y siempre por mi lado del traspaso.

---

## 3 · Las otras skills

**`superpowers:brainstorming` 🟢.** Su compuerta dura —*no escribas código hasta
que el diseño esté aprobado*— es la razón de que hoy no se implementara un diseño
con **tres afirmaciones de carga falsas**. El coste de haberlo implementado habría
sido un día de trabajo tirado; el coste de la compuerta fue cero líneas escritas.
Y el formato de *una pregunta a la vez* forzó tres decisiones que yo habría dado
por supuestas.
🟡 **Lo que le falta:** nada en la skill pide **auditar el diseño antes del spec**.
Ese paso lo pidió el humano, y es el que tumbó el diseño. Debería estar dentro.

**`workstream-merge-gate` 🟢.** El paso 2 —verde **después** del último commit—
cazó que los cinco documentos de la jornada violaban una carpeta cerrada. Sin él
habrían entrado a `main` y el fallo aparecería mañana, sin dueño. Su encuadre
*«rechazar es el trabajo del gate»* es lo que hizo que la respuesta correcta fuera
**renombrar los ficheros y no ensanchar la allow-list**.

**`session-close` 🟢.** El paso 8 —*relee lo que editaste, el reporte de una
edición no es la edición*— cazó una frase que yo dejé partida a la mitad. Es un
paso que parece burocracia hasta que te salva.

**`project-resume` 🟡.** Su presupuesto de ~10 KB funcionó: detectó
`PENDIENTES.md` en 117 KB y **no lo abrió**, que era lo correcto. Pero arrancó
sobre un `_PROJECT.md` **desfasado un día entero** (decía `59b571a` / 2 309 verdes
cuando eran `604d1ed` / 2 560) y **la skill no tiene forma de detectarlo**.
> **Propuesta:** que el paso 2 compare `origin/main` real contra el que afirma
> `_PROJECT.md` y avise si no coinciden. Son dos comandos.

**`adr-writer` / `memory-keeper` 🟡 — no se usaron, y se notará.** Hoy se tomaron
**dos decisiones de arquitectura** (la lectura desde el store, y el eje por lift)
que solo existen como línea en `_PROJECT.md` y en la nota de sesión. La segunda
cambia **cuál tramo señala un aviso que nombra personas**. Quedan ofrecidas, no
hechas.

---

## 4 · Graphify — la respuesta honesta

### Lo que pasó

**No lo usé ni una sola vez en toda la jornada**, teniéndolo instruido en el
`CLAUDE.md` del proyecto (*«For codebase questions, first run `graphify query`»*).
Todo el trabajo de exploración salió de `grep`, `Read` y despachar agentes.

Y **no fue porque no estuviera**: `graphify --version` responde **0.9.15**, y
`graphify-out/graph.json` pesa **7,3 MB**, reconstruido hoy mismo por el hook de
post-commit. Es un incumplimiento mío de una instrucción del proyecto, no un fallo
del montaje.

### Lo que habría dado — probado después, no supuesto

Le lancé una consulta real de las de hoy (*quién consume `GestionesRepo` y dónde se
usa el nombre del gestor*):

- ✅ **Devolvió los anclajes correctos con fichero y línea**: `GestionesRepo`
  (`repo.py:86`), `get_repo()` (`:375`), `store.py`, `CsvRepo`, `MySqlRepo`.
  **Eso me habría ahorrado el `grep` con el que encontré que `store.py` es el
  cuello por donde pasa el pipeline entero.**
- ❌ **Devolvió 255 nodos en BFS de profundidad 2**, con mucho ruido: componentes
  del frontend, tests sin relación, comunidades sin nombre. La señal está, pero hay
  que cribarla.
- ❌ **No habría contestado la pregunta del día.** «¿Quién *necesita* el nombre y
  quién solo lo *transporta*?» exige **leer el código**, no ver la topología. Y eso
  no es opinión: es la lección que el propio frente devolvió — *un conteo de
  ocurrencias no mide dependencia*. Un grafo de llamadas es un conteo de
  ocurrencias con mejor presentación.

### Veredicto

🟢 **Útil para orientarse**: «¿dónde vive esto y qué lo toca?» en un repo que no
conoces. Ahí gana al `grep` y **debí usarlo en la primera media hora**.
🔴 **Inútil para decidir**: «¿esto depende de aquello, y qué pasa si cambia?» no
lo contesta ningún grafo AST, porque la respuesta está en la semántica.
⚠ **Y un efecto colateral que conviene saber**: el grafo **indexa los `.md`
commiteados**, así que ya contiene los reportes de hoy. Ayuda a encontrar
documentos y añade ruido a las consultas de código, las dos cosas a la vez.

**Coste**: cero de API (solo AST), pero el hook **reconstruye en cada cambio de
rama** — hoy se disparó unas seis veces, compitiendo por RAM con tres subagentes.
Con el presupuesto de máquina apretado, conviene saberlo.

---

## 5 · Lo que me llevaría a la siguiente jornada

1. **El bloque de predicción no se negocia.** Es el mecanismo con mejor relación
   coste/hallazgo de todo el sistema.
2. **El aprovisionamiento entra en el brief**, con los dos baselines y las flags.
   Cuatro corridas perdidas es un precio que ya se pagó.
3. **Auditar el diseño antes del spec** debería ser parte de `brainstorming`, no
   una idea que se le ocurra al humano. Hoy salvó el día.
4. **Usar graphify en la primera media hora y no después**, y no esperar de él
   respuestas semánticas.
5. **Verificar el artefacto, nunca el reporte.** Cazó dos titulares falsos, un
   renombrado que rompía `/v1` en silencio, y una premisa entera (*«no eran dos
   historias»*) que un solo `git cherry` cerró.
