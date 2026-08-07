# RFD — Endurecimiento del instrumental tras la primera campaña de campo

> **Estado:** PROPUESTA — pendiente de **auditoría por Opus** ANTES de
> implementar. Flujo invertido a propósito: este RFD lo escribió el auditor
> (Cowork, nube) a partir de evidencia de campo ajena; el implementador lo
> audita con el código real delante y disiente donde el diseño no case con
> lo que el código dice. El usuario arbitra las diferencias.
> **Fecha:** 2026-08-06 · **Autor:** Cowork.
> **Origen — 3 reportes de campo** (jornadas 08-05/08-06 en
> `recomendador-cobranza`, otra laptop, full local; el usuario los adjunta):
> **(A)** retrospectiva instrumental (10 despachos, 6 ramas, 1 diseño
> devuelto) · **(B)** fricciones de cosecha y hooks (6 RFD→ADR, 118
> referencias) · **(C)** bug de `sync-skills` (subenumeración silenciosa).
> **Contexto:** RFD 04 (workstreams) · RFD 12 (backlog) · doc
> `subagentes/05` · `ADR-20260803-skills-fuente-unica`.

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
nunca destruye. Además: **reintento único de enumeración** si hay faltantes
(cubre la hipótesis del flush tras `reset --hard`); **copia a `.tmp` +
rename** en vez de `Remove-Item`+`Copy-Item` (cierra el §3.3 del reporte);
el conteo se imprime SIEMPRE contrastado (`31 skills (manifest: 31)`); y
todo lo anterior **espejado en `sync-skills.sh` y `sync-hooks.ps1`** (el
guard de "fuente totalmente vacía" de sync-hooks no cubre la enumeración
parcial). **Test obligatorio** en `setup/scripts/tests/`: simular manifest
con 31 y fuente con 29 → el script debe abortar sin borrar; y el caso
"skill retirada de verdad + `-Prune`" → sí borra.

### C2 · El hook del grafo escribe SU archivo, nunca el curado (F2) 🔴

`git-post-commit-graph-report.sh` cambia su destino a
**`codebase-map-snapshot.md`** (generado, único escritor = el hook).
`codebase-map.md` queda **curado, único escritor = humano/sesión**. Es la
ley del único escritor aplicada a archivos: generado y curado no comparten
fichero jamás. Se actualizan las referencias que hoy nombran
`codebase-map.md` como generado (el propio `.sh`, `session-close` §5,
`project-onboard` §7 — grep para el censo real). **Canario**: repo de
laboratorio con mapa curado → commit → el hook dispara → el curado queda
byte-idéntico y el snapshot existe.

### C3 · La plantilla de despacho gana aprovisionamiento, scratchpad y `[SUPUESTO]` (F3, F4, F5)

Todo en `workstream-dispatch/references/plantilla-despacho.md` — **los 7
bloques no cambian de número** (ya están citados desde fuera):

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
y reporta el desfase medido ("mapa de hace N días, hook no instalado").
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

### C6 · `project-resume` detecta el desfase (F10)

Paso nuevo de dos comandos: comparar el sha real de `origin/main` contra el
que afirma `_PROJECT.md`; si difieren → *"el vault va N commits atrás —
tómalo como orientación, no como verdad"*. En la variante Cowork, si no hay
repo conectado para correr git: **reportar "no verificado" — un check que no
corrió no es un check que pasó** (mismo patrón que `checks.md`). Ambas
variantes, como en el RFD 12.

### C7 · "Auditar el diseño antes del spec" vive en NUESTRA capa (F11)

El reporte propone meterlo en `superpowers:brainstorming`. **Rechazado el
lugar, aceptada la necesidad**: las skills de Superpowers no se modifican
(regla de W2 — nuestras piezas van encima, no dentro). Casa elegida:
**`workstream-dispatch`** — "Cuándo usar" gana la línea *"también para
despachar una auditoría adversarial de un DISEÑO aprobado, ANTES del
spec"*, y `references/revisor.md` una nota de que el contrato del revisor
(contexto limpio, no confiar en el reporte) aplica igual a diseños. Es el
mismo patrón del crítico limpio, una fase antes — y hoy tumbó un diseño con
3 afirmaciones de carga falsas a costo de cero líneas escritas.

### C8 · Graphify: documentar, no tocar (F12)

La herramienta es externa (el sync no la gestiona — correcto). Tres avisos
por escrito en `project-onboard` §7 + el doc de graphify del repo:
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

## 5. Alcance

**Entra:** C1-C8, con sus tests/canarios; promover el reporte A a
`docs/subagentes/07-PRIMERA-CAMPANA-REAL.md` (banner, sin reescribir) como
evidencia de campo de W2. **No entra:** C9; las cosechas de los RFD 04 y 12
(liberadas, van en su propio encargo); cualquier cambio al daemon de
Telegram.

## 6. Criterios de éxito

1. Test de subenumeración: manifest 31 / fuente 29 → aborta sin borrar,
   listando las 2 faltantes; con `-Prune` y retirada real → borra. Doble
   corrida sana → conjuntos idénticos impresos con contraste.
2. Canario del hook: mapa curado byte-idéntico tras commit; snapshot creado.
3. `wc -w` de todo cuerpo de skill editado ≤500 (session-close ≤ su tamaño
   actual).
4. `grep` de `codebase-map.md` en el repo: ninguna referencia lo describe ya
   como generado por el hook.
5. Los 7 bloques de la plantilla conservan numeración y los docs que los
   citan no requieren cambio.
6. Reporte A promovido y citado desde el RFD 04 como evidencia de la
   condición 7 cumplida en uso real.

## 7. Riesgos

- **Sobre-endurecer el sync**: `-Prune` obligatorio añade fricción a una
  retirada legítima. Aceptado: es 1 flag una vez al mes contra un borrado
  silencioso.
- **La plantilla engorda**: el bloque 2 crece; vigilar que el despacho siga
  siendo generable en minutos, no un formulario. Si estorba en la próxima
  campaña, se poda con evidencia.
- **Este RFD lo escribió quien NO tiene el código delante**: por eso el
  gate es la auditoría de Opus — donde el diseño contradiga al código real
  (líneas, nombres de variables, presupuestos), gana el código y se anota
  el delta.

## 8. Trazabilidad (para la auditoría)

F1→C§3 · F2→B§2 · F3→A§2 · F4→A§2 · F5→A§2 · F6→B§1 · F7→B§4 · F8→B§5-6 ·
F9→B§7 · F10→A§3 · F11→A§3 · F12→B§3+A§4. Los reportes son los adjuntos;
toda cifra citada aquí sale de ellos y es verificable contra su texto.

---

*RFD 10 de la subserie `auditoria/`. Aprobarlo = auditoría de Opus sin
hallazgos bloqueantes + arbitraje del usuario sobre las diferencias.
Implementarlo = prompt aparte, con la auditoría externa de Cowork al final,
como siempre.*
