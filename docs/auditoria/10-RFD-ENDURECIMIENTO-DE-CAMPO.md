# RFD — Endurecimiento del instrumental tras la primera campaña de campo

> **Estado:** **APROBADA (v3, 2026-08-07)** — auditada por Opus (los 7
> hallazgos incorporados, §9) y las 2 decisiones abiertas **resueltas por el
> usuario** (§0). Lista para el prompt de implementación; la auditoría
> externa de Cowork cierra el ciclo.
> **Fecha:** 2026-08-06 · **v3** 2026-08-07 (D1/D2 resueltas; la v2 con las
> opciones completas queda en git) · **Autor:** Cowork (auditor, nube) ·
> **Auditor del RFD:** Opus (laptop, con el código delante) — flujo
> invertido a propósito.
> **Origen — 3 reportes de campo** (jornadas 08-05/08-06 en
> `recomendador-cobranza`, otra laptop, full local): **(A)** retrospectiva
> instrumental (10 despachos, 6 ramas, 1 diseño devuelto) · **(B)**
> fricciones de cosecha y hooks (6 RFD→ADR, 118 referencias) · **(C)** bug
> de `sync-skills` (subenumeración silenciosa).
> **Contexto:** RFD 04 (workstreams) · RFD 12 (backlog) · doc
> `subagentes/05` · `ADR-20260801-bot-memoria-y-perfil` ·
> `ADR-20260801-higiene-vault` · `ADR-20260803-skills-fuente-unica`.

---

## 0. Las dos decisiones — RESUELTAS (arbitraje del usuario, 2026-08-07)

### D1 · Qué inyecta el bot: el CURADO + un EXTRACTO FRESCO del snapshot

Resolución del usuario: **la frescura importa** — el snapshot se regenera en
cada commit y el bot debe recibir el grafo actualizado "de la manera más
óptima". Forma óptima elegida (variante enriquecida de la opción (c) de la
v2):

1. `vaultio` inyecta **ambos, cada uno en su papel**:
   - **`codebase-map.md` (curado)** — la orientación destilada, con su
     presupuesto actual, anteponiendo su `updated:` para que el agente pese
     la edad de lo que lee.
   - **Extracto de `codebase-map-snapshot.md` (generado)** — tope
     **~800 caracteres**: fecha/sha de generación + la sección de RESUMEN
     del reporte (conteo de nodos, módulos top). **Nunca el volcado**
     (111 KB observados): la frescura viaja en el resumen, no en la
     topología completa.
   - Si el snapshot no existe → una línea honesta: *"snapshot ausente
     (hook post-commit no instalado)"* — que de paso delata F6 desde el
     propio briefing.
2. **Excepción declarada al alcance (§5):** esto añade UNA función pequeña a
   `vaultio.py` (leer el snapshot, extraer el resumen con tope). Es el
   cambio mínimo al daemon que el hallazgo B2 exigía declarar en vez de
   esconder.
3. **Enmienda al `ADR-20260801-bot-memoria-y-perfil`:** la frase "su
   frescura no depende del bot" se reescribe — la frescura la aporta el
   extracto del snapshot (hook); el curado aporta señal sin garantía de
   edad. Su criterio 6 declara que mide el briefing combinado.

### D2 · El contrato gana el campo: `Estado del repo: <sha corto> · <fecha>`

Resolución del usuario: **opción (a)**. Línea nueva en `_PROJECT.md`
(plantilla `project-note.md` + esqueleto), actualizada por `session-close`
al cierre — el mismo gesto que ya recalcula la N del backlog.
`project-resume` compara ese sha contra `origin/main`; en proyectos viejos
sin el campo, lo dice UNA vez y `session-close` lo añade al siguiente
cierre (auto-sanador, sin el ruido perpetuo que B3 señaló). La enmienda
formal al `ADR-20260801-higiene-vault` viaja con la cosecha del RFD 12, ya
liberada.

---

## 1. Problema

La primera campaña real del instrumental completo —W2 en un proyecto de
verdad, cosecha de 6 RFD, y el setup sincronizado en una laptop nueva—
funcionó (la predicción produjo el hallazgo en 5 de 10 frentes; el gate
rechazó una integración inválida real; decisiones-del-día evitó su caso
fundacional) y a la vez destapó **12 fallos concretos, 2 de los cuales
destruyen trabajo en silencio**. Todos tienen evidencia con el dedo puesto;
ninguno es hipotético. Este RFD decide qué se arregla, dónde y cómo — y qué
NO se toca aunque los reportes lo sugieran.

## 2. Los fallos, por daño

| # | Fallo | Fuente | Daño observado |
|---|---|---|---|
| F1 | `sync-skills` subenumera en silencio y la corrida siguiente **borra** lo que no vio | C | 29↔31 con doble `[OK]`; en orden inverso habría borrado las 2 skills de W2 sin un error |
| F2 | El hook del grafo hace `cp` sobre `codebase-map.md` **curado a mano** | B§2 | 3.152 bytes curados sobrescritos con 111.353 de volcado (restaurado del git del vault) |
| F3 | El brief no transporta el **aprovisionamiento** (artefactos fuera de git + flags) | A§2 | 4 frentes perdieron una corrida entera diagnosticando inventario ausente como daño (256/294 rojos) |
| F4 | Sin **scratchpad por frente**: un agente sobrescribió las predicciones de otro | A§2 | Fallo de montaje; parcheado a mano a media jornada |
| F5 | El **brief del coordinador metió datos falsos en 4/10** despachos | A§2 | El riesgo vive en el lado humano del traspaso, y hoy nada lo instrumenta |
| F6 | El hook del grafo tiene 3 referencias y **ningún instalador que corra** | B§1 | Mapa congelado 9 días mientras el repo pasaba de 1.796 a 4.705 nodos |
| F7 | `adr-writer` §4 ↔ `check-vault-updated` se **contradicen** en multi-agente | B§4 | Cada agente improvisa; el conteo de ADRs se desincronizó (36→43 real) |
| F8 | `design-doc-harvest` asume RFDs en el REPO; había 34 en el **vault** | B§5-6 | La skill no tiene rama para el caso; 118 referencias entrantes hacen inviable "reescribir cada cita" |
| F9 | `adr-writer` fecha con HOY; un ADR **cosechado** necesita la fecha de la decisión | B§7 | Rompe el orden del índice y miente sobre cuándo se decidió |
| F10 | `project-resume` no detecta un `_PROJECT.md` **desfasado** | A§3 | Arrancó sobre un estado de un día atrás (sha y conteo de suite equivocados) sin forma de saberlo |
| F11 | Nada pide **auditar el diseño antes del spec** | A§3 | El paso lo pidió el humano; fue el que tumbó un diseño con 3 afirmaciones de carga falsas |
| F12 | `graphify claude install` registra **PreToolUse no documentados** + guía de uso ausente | B§3, A§4 | Instrucción imperativa inyectada en cada búsqueda de cada sesión; hook reconstruyendo ~6 veces compitiendo por RAM con 3 frentes |

## 3. Objetivos

**O1.** Ningún camino del setup destruye trabajo en silencio (F1, F2).
**O2.** El despacho transporta el aprovisionamiento y sus afirmaciones son
verificables o están marcadas (F3, F4, F5).
**O3.** Las skills de cosecha y arranque funcionan en los dos mundos reales:
RFDs en vault y N agentes vivos (F7, F8, F9, F10).
**O4.** Cero regresiones: presupuestos de palabras respetados (session-close
está a 489/500), tests nuevos para lo destructivo, y las skills de
Superpowers **no se tocan**.

## 4. Casos de diseño

### C1 · `sync-skills`: el borrado deja de ser posible por accidente (F1) 🔴

El reporte C propone abortar si `conteo < manifest`. **Se adopta con un
endurecimiento: comparar CONJUNTOS por nombre, no conteos.**

| | (a) Guard por conteo (reporte C) | (b) **Guard por conjunto** (elegida) | (c) Solo avisar |
|---|---|---|---|
| Detecta | bajada neta | **cualquier faltante**: `faltantes = nombres(manifest) − nombres(fuente)` | nada bloquea |
| Agujero | +1 skill nueva y −1 subenumerada = conteo igual → **borra igual** | ninguno conocido | destruye |
| Costo | igual | igual (un diff de sets) | — |

Reglas: si `faltantes ≠ ∅` → **no borrar NADA**, listar los nombres, abortar
con error. El borrado pasa a ser **siempre opt-in** (`-Prune`/`--prune`),
también sin discrepancia: retirar una skill es raro y deliberado; el default
nunca destruye. **Contra la acumulación (hallazgo I2): la corrida default
detecta huérfanas y las GRITA en cada ejecución** — lista de nombres + el
comando exacto para podarlas. El costo de una skill retirada que sigue
instalada (paga su description en cada sesión — el gasto que motivó el
perfil bot) no se acumula en silencio: se ve cada vez.

Además: **reintento único de enumeración** si hay faltantes (cubre la
hipótesis del flush tras `reset --hard`); **copia a `.tmp` → remove →
rename** — en Windows `Move-Item` falla con destino existente, así que la
ventana destructiva **se encoge, no desaparece** (corrección I2): queda
reducida a remove+rename locales, con el `.tmp` como recuperación si el
script muere en medio; el conteo se imprime SIEMPRE contrastado
(`31 skills (manifest: 31)`); y todo lo anterior **espejado en
`sync-skills.sh` y `sync-hooks.ps1`** (el guard de `sync-hooks.ps1:51` solo
cubre fuente totalmente vacía — verificado por la auditoría). **Test
obligatorio** en `setup/scripts/tests/`: manifest 31 / fuente 29 → aborta
sin borrar, listando las faltantes; retirada real + `-Prune` → sí borra;
doble corrida sana → conjuntos idénticos.

### C2 · El hook del grafo escribe SU archivo, nunca el curado (F2) 🔴

`git-post-commit-graph-report.sh` cambia su destino a
**`codebase-map-snapshot.md`** (generado, único escritor = el hook).
`codebase-map.md` queda **curado, único escritor = humano/sesión**. Ley del
único escritor aplicada a archivos: generado y curado no comparten fichero
jamás.

**El censo real de consumidores es de DIEZ, no tres** (hallazgo B1 — la v1
lo estimó en vez de greppearlo, el mismo pecado que C3 castiga). Destino
decidido por fila; la fila del daemon aplica **D1 resuelta**:

| Consumidor | Hoy | Tras C2 apunta a |
|---|---|---|
| `git-post-commit-graph-report.sh` | escribe `codebase-map.md` | **escribe `codebase-map-snapshot.md`** (el cambio core) |
| `vaultio.py:143` (briefing del bot) | inyecta `codebase-map.md` | **curado + extracto del snapshot (D1)** — función nueva pequeña en vaultio, declarada en §5 |
| `setup/memory-snippet.md:26` | ordena leerlo al arrancar | curado (orientación humana); menciona que existe el snapshot |
| `setup/memory-instructions.md:29` | ídem | curado, ídem |
| `setup/hooks/README.md:37` ("el canónico ahora es codebase-map.md") | — | reescribir: **curado = canónico humano; snapshot = generado por el hook** |
| `project-resume` (:31, ambas variantes) | lo lee para orientar | curado |
| `vault-drift-audit:36` | audita su frescura | **snapshot** (mide la salud del hook); la frescura del curado queda a juicio humano |
| `telegram-bridge/README.md:303` | lo menciona | redacción D1: "curado + extracto fresco del snapshot" |
| `session-close` §5 / `project-onboard` §7 | verifican el hook | edad del **snapshot** (C4) |

Enmienda al `ADR-20260801-bot-memoria-y-perfil` según D1 (§0). **Canario**:
repo de laboratorio con mapa curado → commit → el hook dispara → el curado
queda byte-idéntico y el snapshot existe.

### C3 · La plantilla de despacho gana aprovisionamiento, scratchpad y `[SUPUESTO]` (F3, F4, F5)

Todo en `workstream-dispatch/references/plantilla-despacho.md` — **los 7
bloques no cambian de número**. (Corrección de la auditoría: las citas a los
bloques son todas internas a la skill; no renumerar sigue siendo lo sano —
por estabilidad del contrato y el hábito ya adquirido en campo, no por citas
de fuera.)

- **Bloque 2 (estado del mundo)** incorpora el inventario: el baseline son
  **DOS conteos** (checkout principal y worktree recién creado) **+ la lista
  de artefactos fuera de git** (`.env`, datasets, carpetas de datos: ruta y
  cómo obtenerlos) **+ las flags opt-in** que mueven la suite. La frase del
  reporte A es la spec: *"el baseline no es un número: es un número más el
  estado de cuatro interruptores"* (42 de 51 skips eran una sola variable).
- **Bloque 1** añade: cada frente recibe **subcarpeta propia** de scratchpad
  (`.superpowers/sdd/<plan>/frentes/<n>/`) para predicciones y reportes — un
  agente sobrescribió las predicciones de otro por compartir ruta.
- **Regla nueva del brief** (cierre del bloque 2): **toda afirmación de
  hecho lleva su comando de verificación, o se marca `[SUPUESTO]`** y el
  frente la verifica antes de construir encima. Generaliza el "greppea quién
  consume" del doc 05 §1.1 al lado del coordinador — que es donde la
  evidencia puso 4 de 4 briefs con datos falsos.

### C4 · `session-close`: la verificación del hook se vuelve incondicional (F6)

El paso 5 deja de estar condicionado a "hubo cambios estructurales": si el
repo usa Graphify, **siempre** verifica hook instalado + edad del snapshot,
y reporta el desfase medido ("snapshot de hace N días, hook no instalado").
*"Una condición que casi nunca se cumple es indistinguible de una que no
existe"* (reporte B). ⚠ Presupuesto: la skill está a **489/500** — la
redacción nueva no puede ser más larga que la actual; si no cabe, el detalle
va a una reference y el paso queda en una línea.

### C5 · Cosecha: rama de vault, cartel, y fecha de decisión (F7, F8, F9)

- **`design-doc-harvest`**: rama explícita *"RFD residente en el vault"* ⇒
  cosechar a ADR y **archivar en `RFDs/_archive/` con cartel apuntando al
  ADR — nunca `git rm`** (el vault es memoria, no andamiaje). Y el patrón
  del cartel entra como **vía aceptada cuando las referencias entrantes
  pasan de ~20** (118 citas lo probaron; los wikilinks sobreviven al cambio
  de carpeta, solo las citas por RUTA se reescriben).
- **`adr-writer`**: (1) excepción de fecha — un ADR cosechado se fecha con
  la **fecha de la decisión** + línea *"🌾 Cosechado el YYYY-MM-DD de …"*;
  (2) §4 en multi-agente — si hay otros agentes vivos, el wikilink **queda
  pendiente en la nota de sesión y `session-close` consolida** (resuelve la
  contradicción con `check-vault-updated`, y es la doctrina C7 del RFD 04).

### C6 · `project-resume` detecta el desfase (F10) — forma fijada por D2(a)

Paso nuevo: comparar el sha de `origin/main` contra el campo
`Estado del repo:` de `_PROJECT.md`; si difieren → *"el vault va atrás —
tómalo como orientación, no como verdad"*; si el campo no existe (proyecto
viejo), decirlo UNA vez — `session-close` lo añade al siguiente cierre.
`session-close` gana ese gesto: actualizar `Estado del repo: <sha corto> ·
<fecha>` al cierre, junto al recálculo de la N del backlog. La plantilla
`project-note.md` gana la línea. En la variante Cowork, si no hay repo
conectado: **reportar "no verificado" solo cuando el campo exista y no se
pueda comparar** — un check que no corrió no es un check que pasó, pero
tampoco se fabrica ruido perpetuo (B3). Ambas variantes de ambas skills.

### C7 · "Auditar el diseño antes del spec" vive en NUESTRA capa (F11)

El reporte propone meterlo en `superpowers:brainstorming`. **Rechazado el
lugar, aceptada la necesidad**: las skills de Superpowers no se modifican
(regla de W2 — nuestras piezas van encima, no dentro). Casa elegida:
**`workstream-dispatch`** — "Cuándo usar" gana la línea *"también para
despachar una auditoría adversarial de un DISEÑO aprobado, ANTES del
spec"*, y `references/revisor.md` una nota de que el contrato del revisor
(contexto limpio, no confiar en el reporte) aplica igual a diseños. Es el
mismo patrón del crítico limpio, una fase antes — y en campo tumbó un
diseño con 3 afirmaciones de carga falsas a costo de cero líneas escritas.

### C8 · Graphify: documentar, no tocar (F12)

La herramienta es externa (el sync no la gestiona — correcto). Tres avisos
por escrito, con destino corregido por la auditoría (no existe "doc de
graphify" en el repo — no se crea uno para tres párrafos): van a
**`setup/hooks/README.md`** y **`project-onboard` §7**:
(1) `graphify claude install` registra **PreToolUse** en
`.claude/settings.json` — con agentes en paralelo, instalar SOLO la sección
de CLAUDE.md; (2) uso: primera media hora para orientarse ("¿dónde vive esto
y qué lo toca?"), **no esperar respuestas semánticas** de un grafo AST;
(3) su hook reconstruye en cada cambio de rama y **cuenta en el presupuesto
de máquina del bloque 5** del despacho.

### C9 · Lo que NO se hace, y por qué

- **Ownership como barrera dura**: los 2 frentes que salieron lo
  **declararon** — el mecanismo-norma funcionó 2/2. Barrera = W3-style cuyo
  disparador (salida NO declarada) no ha ocurrido. Se documenta el criterio
  y se espera.
- **Tocar `superpowers:brainstorming`** (ver C7).
- **Empujar `adr-writer`/`memory-keeper` a automáticos**: quedaron
  "ofrecidos, no hechos" por decisión humana — avisa-no-bloquea es el
  contrato correcto.
- **Cambiar DELIVERY_RULE del bridge**: nada de esta campaña lo toca (P6
  sigue descartado por su propio razonamiento).
- **Cerrar la condición 7 del RFD 04 con la evidencia de campo** (hallazgo
  I1, concedido completo): en uso real no se distingue "el gate lo paró" de
  "la suite estaba roja de todos modos". **La prueba deliberada SIGUE siendo
  LA condición de la cosecha del RFD 04**; el reporte A se cita como
  evidencia complementaria, sin desbloquear nada.

## 5. Alcance

**Entra:** C1-C8 con sus tests/canarios; **la excepción mínima y declarada
al daemon**: una función en `vaultio.py` que lee el snapshot y extrae su
resumen con tope (~800 chars) para el briefing (D1) — ningún otro cambio de
código del bridge; la línea `Estado del repo:` en la plantilla (D2); la
enmienda puntual al `ADR-20260801-bot-memoria-y-perfil` (D1); promover el
reporte A a `docs/subagentes/07-PRIMERA-CAMPANA-REAL.md` (banner, sin
reescribir) como evidencia de campo **complementaria** de W2. **No entra:**
C9; las cosechas de los RFD 04 y 12 (van en su propio encargo; la enmienda
al ADR higiene por D2 viaja con la del RFD 12); cualquier otro cambio al
daemon.

## 6. Criterios de éxito

1. Test de subenumeración: manifest 31 / fuente 29 → aborta sin borrar,
   listando las 2 faltantes; con `-Prune` y retirada real → borra; corrida
   default con huérfanas → las grita con el comando exacto. Doble corrida
   sana → conjuntos idénticos impresos con contraste.
2. Canario del hook: mapa curado byte-idéntico tras commit; snapshot creado.
3. `grep -rn "codebase-map" setup/ docs/` tras implementar: **los diez
   consumidores** del censo de C2 apuntan cada uno a su destino declarado;
   ninguno describe ya el curado como generado por el hook.
4. **Briefing de prueba del bot** (D1): con snapshot presente → curado (con
   `updated:`) + extracto ≤800 chars con fecha/sha del snapshot, dentro del
   presupuesto total; sin snapshot → la línea honesta de ausencia. Medir
   chars, no estimarlos.
5. `wc -w` de todo cuerpo de skill editado ≤500 (session-close ≤ su tamaño
   actual).
6. Los 7 bloques de la plantilla conservan numeración.
7. Reporte A promovido y citado desde el RFD 04 como evidencia
   complementaria — **la condición 7 (prueba deliberada) permanece abierta
   tal cual**.
8. D2: un cierre de sesión en un proyecto sin campo lo añade; el siguiente
   arranque compara contra él sin avisos espurios.

## 7. Riesgos

- **`-Prune` opt-in — el riesgo real es la acumulación, no la fricción**
  (corregido por I2): una skill retirada que nadie poda sigue pagando su
  description en cada sesión. Mitigación elegida: el aviso gritón en cada
  corrida; si en la práctica se ignora, el siguiente paso es un hallazgo de
  `vault-drift-audit`, no volver al borrado automático.
- **La ventana destructiva del sync se encoge, no desaparece** (Windows:
  `Move-Item` con destino existente): remove+rename locales con `.tmp` de
  recuperación. Riesgo residual aceptado y documentado en el script.
- **El briefing del bot crece** (~800 chars más por conversación nueva):
  aceptado a cambio de frescura; si el criterio 6 del ADR bot-memoria
  concluye que no se paga, el extracto es lo primero que se poda.
- **La plantilla engorda**: el bloque 2 crece; vigilar que el despacho siga
  siendo generable en minutos. Si estorba en la próxima campaña, se poda con
  evidencia.
- **Este RFD lo escribió quien NO tiene el código delante**: mitigado — la
  auditoría de Opus contra el código real ya corrió y sus deltas están
  incorporados (§9). Donde la implementación encuentre otra contradicción,
  gana el código y se anota.

## 8. Trazabilidad (reportes de campo)

F1→C§3 · F2→B§2 · F3→A§2 · F4→A§2 · F5→A§2 · F6→B§1 · F7→B§4 · F8→B§5-6 ·
F9→B§7 · F10→A§3 · F11→A§3 · F12→B§3+A§4. Los reportes son los adjuntos;
toda cifra citada aquí sale de ellos y es verificable contra su texto.

## 9. Registro de la auditoría del RFD (Opus, 2026-08-06)

| Hallazgo | Qué encontró | Resolución |
|---|---|---|
| **B1** 🔴 | El censo de consumidores de `codebase-map.md` era 10, no 3 — incluido el daemon (`vaultio.py:143`); el criterio "ninguna referencia" era incumplible | Concedido. Censo completo con destino por fila en C2; criterio 3 reescrito sobre los diez |
| **B2** 🔴 | C2 cambiaba la ENTRADA del daemon con el daemon declarado fuera de alcance; la justificación del ADR bot-memoria quedaba falsa | Concedido. D1 abierta en v2 → **resuelta en v3** (§0): curado + extracto fresco; excepción al daemon declarada en §5 |
| **B3** 🔴 | C6 comparaba contra un campo de sha que el contrato NO define (era convención local de recomendador); riesgo de "no verificado" perpetuo; duplicaba `vault-drift-audit:30-33` | Concedido. D2 abierta en v2 → **resuelta en v3** (§0): el contrato gana el campo; anti-ruido explícito en C6 |
| **I1** 🟠 | El criterio de éxito cerraba la condición 7 del RFD 04 con evidencia distinta a la pactada — "sustituir la evidencia desbloquea una cosecha por la puerta de atrás" | **Concedido completo, con mea culpa del autor.** La prueba deliberada sigue siendo LA condición; el reporte A es complementario (C9, criterio 7) |
| **I2** 🟠 | El costo real de `-Prune` es acumulación silenciosa, no fricción; y en Windows tmp+rename NO elimina la ventana (Move-Item falla con destino existente) | Concedido con refinamiento: aviso gritón por corrida (C1) + redacción honesta "se encoge, no desaparece" (C1, §7) |
| Menor 1 | "Los 7 bloques ya están citados desde fuera" era falso (las 6 citas son internas) | Corregido el porqué en C3; la decisión (no renumerar) se sostiene sola |
| Menor 2 | "El doc de graphify del repo" no existe | Destino real en C8: `setup/hooks/README.md` + `project-onboard` §7 |

De las 9 cifras del RFD que la auditoría contrastó contra los reportes,
9 casaron; las 3 citas de código del reporte C son exactas contra el código
actual. El flujo invertido (auditor escribe, implementador audita, usuario
arbitra) queda validado: los tres bloqueantes salieron de tener el código
delante — exactamente el riesgo que la v1 declaró de sí misma.

---

*RFD 10 de la subserie `auditoria/`, v3 APROBADA. Implementarla = prompt
aparte, con la auditoría externa de Cowork al final, como siempre.*
