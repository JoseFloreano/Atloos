# RFD — Higiene de contexto y ciclo de vida del vault

> **Versión:** v2 (2026-08-01) — corregida tras revisión adversarial (agente Fable)
> **Estado:** propuesta validada, **lista para spec**. Nada implementado.
> **Contexto previo:** `01-OBSIDIAN-MEMORIA-EXTERNA.md` · `06-ARQUITECTURA-FINAL-RECOMENDADA.md` ·
> `07-HALLAZGOS-CRITICOS-REFERENCIA-RAPIDA.md` · **`../telegram/05-RFD-T3-MEMORIA-Y-TOKENS.md`** ·
> skills `project-resume`, `session-close`, `adr-writer`, `design-doc-harvest`, `vault-drift-audit`
> **Método:** brainstorming de Superpowers sobre medición del vault real, más una
> revisión adversarial independiente cuyos hallazgos están incorporados (§11).
> **Nota:** este RFD se rige por la regla que él mismo propone (§3.5) — cuando lo
> aquí decidido esté implementado y auditado, se cosecha al ADR correspondiente y
> este archivo se borra, redirigiendo antes sus referencias entrantes.
>
> **Qué cambió en v2:** la arquitectura (§3.0) se mantiene entera. Se corrigen la
> ruta del template (§5), la aritmética del presupuesto —que ignoraba `bugs/`
> (§1, §2)—, y se añaden tres piezas que faltaban: redirección de referencias al
> cosechar (§3.5), cosecha que enriquece un ADR existente en vez de duplicarlo
> (§3.5) y la dependencia con el RFD 05 (§3.1). Se suavizan dos argumentos
> exagerados (§1.2, §4.1). Detalle en §11.

---

## 1. Problema

El vault funciona: tres capas operativas, hooks anti-drift, aislamiento por
proyecto. Lo que no tiene es **política de crecimiento**. Cada sesión añade y
ninguna quita, así que el archivo más leído del sistema es también el que más
engorda.

Medición del proyecto `claude-setup` a 2026-08-01 (9 días de vida):

| Señal | Valor |
|---|---|
| `_PROJECT.md` | **186 líneas / 12 330 bytes** |
| De eso, secciones `## Hecho` | **70 líneas (39%) en 6 secciones** |
| `ADRs/` | 17 486 bytes en 5 archivos |
| `bugs/` | 10 059 bytes en 3 archivos — **los 3 cerrados** (`fixed`, `fixed`, `invalid`) |
| `sessions/` | 44 336 bytes en 5 archivos |
| **Lectura de `project-resume` en cada arranque** | `_PROJECT.md` + 3 ADRs + `bugs/` ≈ **36 KB (~9k tokens)** |
| Ritmo de creación | ~1,5 notas/día |

> La medición inicial de v1 daba 181 líneas / 11 931 bytes y un arranque de
> ~25 KB. Ambos números eran optimistas: el archivo creció en horas y el cálculo
> **omitía `bugs/`**, que `project-resume` también lee. La deriva en 9 días es
> parte de la evidencia, no ruido.

Tres síntomas concretos, no hipotéticos:

1. **`_PROJECT.md` es un changelog disfrazado de estado.** Las seis secciones
   `## Hecho` están intercaladas entre las estables — "Convenciones" y
   "Pendientes" quedaron partidas entre bloques de historia — y ni siquiera en
   orden cronológico. El coste lo paga cada arranque de sesión.
2. **El frontmatter de los ADRs no es uniforme**: 3 usan `status:` (inglés), 2
   usan `estado:` (español, uno con comentario inline). El chequeo de
   `vault-drift-audit` que busca *ADRs `accepted` contradichos sin marcarse
   `superseded`* **no ve 2 de los 5** — uno de ellos el del puente Telegram, el
   más activo del proyecto. (El resto de la skill no lee frontmatter de ADRs: el
   problema es ese chequeo, no la auditoría entera.)
3. **Los RFDs no tienen final.** `02-RFD-T2-MODO-ESCRITURA.md` dice "no aprobado
   como fase" mientras `_PROJECT.md` da T2 por implementado. Dos fuentes de
   verdad sobre lo mismo, divergiendo — que es exactamente el fallo que el vault
   existe para evitar.

Y un cuarto, estructural: **todo lo que se lee al arrancar se lee entero, esté o
no vivo**. Los 10 KB de `bugs/` son hoy tres bugs cerrados.

## 2. Objetivo

- El arranque de sesión cuesta **~8-9 KB en vez de ~36 KB**, sin perder el "por
  qué" de las decisiones: se recupera bajo demanda, no de entrada.
- Cada pieza de conocimiento tiene **un destino inequívoco y un final**: nada
  vive por inercia en el archivo equivocado.
- El sistema aguanta 6 meses de uso sin que nadie tenga que "ordenar el vault".

**No objetivos:** reorganizar carpetas por temas, tocar los hooks anti-drift
(funcionan), añadir enforcement automático nuevo, ni migrar los otros dos
proyectos del vault en esta ronda (`alphadogs`, `tt1-revisor-chatbot`).

## 3. Decisión propuesta

### 3.0 El principio: tres capas con caducidad distinta

| Capa | Qué es | Dónde vive | Final |
|---|---|---|---|
| **Durable** | decisiones, convenciones, bugs con causa raíz | `ADRs/`, `bugs/`, `_PROJECT.md` | permanente |
| **Episódico** | qué pasó en una sesión, evidencia de pruebas | `sessions/` | se archiva o se cosecha |
| **Andamiaje** | RFDs, specs, planes | repo (`docs/`) | se borra al cosechar |

Todo lo que sigue son consecuencias de esta tabla.

### 3.1 Contrato de `_PROJECT.md`

Esqueleto **fijo y cerrado**, tope blando de **120 líneas** y tope duro de **150**:

```
Qué es · Estado actual · Decisiones clave · Bugs abiertos ·
Convenciones · Pendientes · Próximo paso
```

- **Prohibidas las secciones `## Hecho`.** Lo que pasó va a `sessions/`.
- "Estado actual" es un **presente**, no un acumulado: describe cómo está el
  sistema hoy, no cómo llegó hasta aquí.
- El orden del esqueleto **no es cosmético** (ver abajo): lo más valioso va arriba.
- La plantilla del vault se actualiza para que los proyectos nuevos nazcan con
  este contrato (ruta exacta en §5).

**Dependencia con el RFD 05 (T3), descubierta en revisión:** ese RFD hace que el
daemon de Telegram inyecte **un extracto de ~2K chars de `_PROJECT.md`** al
principio de cada conversación. Truncar a 2K un archivo de 12 KB donde el 39% es
historial intercalado tira lo importante casi al azar. Con este contrato, los
primeros 2K **son** el estado del proyecto. No es sinergia: es **precondición**
para que el §C1b del RFD 05 funcione. Ambos documentos deben citarse.

### 3.2 Rotación en `session-close`

Paso nuevo en la skill: antes de cerrar, lo hecho en la sesión se escribe en
`sessions/<fecha>-<tarea>.md`, y de `_PROJECT.md` **solo** se tocan Estado
actual, Pendientes y Próximo paso. La skill **cuenta las líneas** del archivo al
cerrar y **avisa** si pasa de 120 — informa, no bloquea (§4.4).

Encaja con los hooks sin modificarlos: `check-vault-updated` y `memory-flush` ya
aceptan una nota de `sessions/` fresca como satisfacción del flag. La rotación
los alimenta en vez de pelearse con ellos.

### 3.3 Índice generado y recuperación just-in-time

**(a) `ADRs/_INDEX.md`.** Script `setup/scripts/adr-index.py` (stdlib, **sin
LLM**, en la línea del "gate sin LLM" de las scheduled tasks): lee el frontmatter
de cada ADR y emite una línea por decisión — `fecha · status · título · summary`.
Lo invoca `adr-writer` justo después de crear un ADR.

Requisito no negociable en Windows: **UTF-8 sin BOM y `\n` explícito**. En este
repo el BOM ya se perdió dos veces (bugs B1/B4) y aquí rompería la idempotencia
del criterio de aceptación entre laptops.

**(b) `project-resume` lee el índice, no los ADRs.** Y abre un ADR completo solo
cuando la tarea lo roza, con una condicional barata: **abrir el ADR más reciente
solo si su fecha ≥ la de la última nota de sesión** (significa "se decidió algo
que aún no viviste"); si no, el `summary` decide. Pagar +3 KB siempre por el 10%
de los arranques no compensa.

**(c) `bugs/` se lee filtrado por estado.** Vocabulario cerrado:
`open | fixed | invalid | wontfix`. En el arranque solo entran los `open`; el
resto se abre cuando la tarea lo pida. Los 3 bugs actuales ya llevan `status:` en
el frontmatter y están cerrados, así que **no hay migración que hacer**: es una
regla de lectura, y el ahorro (10 KB) es inmediato.

Ahorro conjunto: ~13 KB de ADRs + ~10 KB de bugs, sin perder trazabilidad — el
índice dice qué existe y dónde, que es lo que hace falta para decidir si vale la
pena abrirlo.

### 3.4 Frontmatter unificado en ADRs

```yaml
title: <título>
date: YYYY-MM-DD
status: proposed | accepted | rejected | superseded-by: ADR-YYYYMMDD-<tema>
summary: <la frase que va al índice>
tags: [...]
```

Se migran los dos ADRs con `estado:` en español. `status` sigue el vocabulario de
MADR, que es el que `vault-drift-audit` ya presupone. El ADR del servidor Debian
se queda en `proposed` hasta que se apruebe — el objetivo es que el estado sea
legible por máquina, no cambiarlo.

**La plantilla `templates/adr.md` del vault cambia con esto** (§5): si no, el
siguiente ADR nace con el frontmatter viejo y la unificación dura una semana.

**Los tags sustituyen a las subcarpetas** como eje temático (§4.1): Obsidian
filtra por tag y el agente hace grep, sin obligar a decidir una carpeta única
para un ADR que toca tres temas.

### 3.5 Ciclo de vida de los RFDs

Se extiende `design-doc-harvest` — que ya hace esto con specs y planes de
Superpowers — para cubrir los RFDs de `docs/**`:

| Estado del RFD | Qué se hace |
|---|---|
| Propuesta abierta / en discusión | se queda |
| Aprobado pero **no** implementado | se queda |
| Implementado **y con las condiciones de auditoría cerradas** | **cosecha** → ADR → `git rm` |
| Abandonado | se borra sin ADR, con confirmación |

El ADR de cosecha absorbe lo que hay que conservar: decisión, **alternativas
rechazadas y su porqué**, trade-offs aceptados y **deltas diseño↔implementación**
(donde suele estar el aprendizaje), citando el sha.

Dos reglas que faltaban en v1 y que la revisión destapó:

1. **Redirigir antes de borrar.** `grep -rl` de las referencias al RFD en `docs/`
   y actualizarlas al ADR **antes** del `git rm`. Medido hoy: el RFD 02 lo citan
   **9 documentos**. "Git conserva la historia" es cierto para el contenido y
   falso para los enlaces entrantes — quedarían 9 citas a un archivo inexistente,
   justo la referencia rota que el vault existe para evitar.
2. **Si la decisión ya tiene ADR, la cosecha lo enriquece; no crea otro.** El
   RFD 02 ya tiene `ADR-20260801-puente-telegram`. Dos ADRs sobre el puente
   reproducirían la divergencia del §1.3 en la capa durable, que es peor.

"Auditado" significa **condiciones de auditoría cerradas**, no "hubo auditoría".
La historia de T2 lo justifica: 6 bugs aparecieron usando lo que 9/9 pruebas
automatizadas daban por bueno.

Cada RFD lleva su estado en la cabecera para que se vea de un vistazo cuál está
listo. Contraste deliberado con el proceso RFD de Oxide, donde los RFD **nunca**
se borran: allí el RFD *es* el registro durable y no hay ADR aparte. Aquí existen
las dos capas, y mantener ambas vivas produce la divergencia del §1.3.

### 3.6 Archivo de `sessions/`

**Nada se borra.** Una nota de sesión cuyo contenido ya está en un ADR o en un
bug se marca como cosechada; `vault-drift-audit` propone moverla a
`_archive/` **dentro de la carpeta del proyecto** pasados ~30 días.

`_archive/` es local al proyecto a propósito: usar `40-Archive/` del vault
obligaría a modificar la regla de aislamiento ("solo `10-Projects/<proyecto>/`,
`brain/`, `daily/`"), y ese precio no compensa por mover archivos que nadie lee.

### 3.7 Lo que queda fuera del presupuesto y hay que vigilar

`codebase-map.md` (que genera Graphify por hook `post-commit`) **hoy no existe**
para `claude-setup`, pero `project-resume` lo lee si aparece y el RFD 05 le
reserva otros ~2K chars. Cuenta contra el presupuesto de arranque; mantenerlo
acotado es responsabilidad de Graphify, no de este contrato — pero si un día el
arranque vuelve a dispararse, mirar ahí primero.

## 4. Alternativas rechazadas

### 4.1 Subcarpetas temáticas dentro de `ADRs/` — **rechazada**

Era la pregunta que originó este RFD. Contra:

- **Para el agente es neutro tirando a negativo.** No navega el vault: hace glob
  y grep, y el tema ya está en el nombre (`ADR-20260801-deepseek-extraccion-graphiti`).
  La carpeta no añade señal; añade profundidad y un **problema de clasificación**
  — ese ADR ¿va en `llm/`, `graphiti/` o `costes/`? Cada colocación dudosa es un
  fallo de recuperación futuro. La jerarquía ayuda cuando distingue *clase*
  (`ADRs/` vs `bugs/` vs `sessions/`, que ya existe), no cuando parte una clase
  en subtemas solapados.
- **Coste real, aunque menor del que decía v1**: `project-resume` de Code y de
  Cowork tendrían que pasar a listado recursivo. Son instrucciones a un LLM, no
  código con glob rígido, así que **no se "romperían"** — pero son dos skills a
  editar, en dos productos, más el sync del zip. Trivial, no nulo, a cambio de
  nada con 5 ADRs.
- **MADR** contempla subcarpetas solo para repositorios con *cientos* de ADRs, y
  avisa del coste: la numeración deja de ser única global.
- El beneficio real —que es humano y legítimo— lo da el índice del §3.3 más
  barato y sin coste para el agente.

**Umbral para reabrirlo:** ~25-30 ADRs en un proyecto, o la aparición de un
segundo eje real (p. ej. el servidor 24/7 como subsistema con vida propia). Aun
entonces, primero tags + índice; carpetas solo si eso se queda corto.

### 4.2 Borrar el RFD en cuanto nace el ADR — rechazada

Un RFD sigue siendo útil mientras la decisión está viva pero sin implementar (el
`03-RFD-T5-DESARROLLO-PARALELO.md` es un registro de ideas, no hay nada que
cosechar). El disparador correcto es "implementado **y con las condiciones de
auditoría cerradas**", no "decidido".

### 4.3 Archivar en `40-Archive/` del vault — rechazada

PARA-correcto sobre el papel, pero obliga a ampliar la regla de aislamiento de
memoria por un beneficio cosmético. Ver §3.6.

### 4.4 Un hook que imponga el tope de `_PROJECT.md` — rechazada

El sistema ya tiene tres hooks anti-drift y **acaba de cerrarse un bug de falso
positivo** en ellos (`bug-mark-code-dirty-falso-positivo`). Un aviso que salta
cuando no toca entrena a ignorarlo. El tope vive en dos sitios blandos que ya
existen: `session-close` lo cuenta y avisa (§3.2), `vault-drift-audit` reporta la
reincidencia en su ciclo quincenal. Convención con dientes, sin fricción dura.

### 4.5 Índice escrito a mano o generado por un pase LLM — rechazada

A mano driftea; con LLM se paga por algo que es parseo de frontmatter. El script
determinista es la opción correcta, coherente con la lección del §R7 del doc 16
(el Curator de Hermes: 91M tokens quemados en un pase masivo).

## 5. Impacto

| Archivo / skill | Repo | Cambio |
|---|---|---|
| `ObsidianVault/templates/project-note.md` | **vault** | Esqueleto nuevo con el contrato del §3.1 |
| `ObsidianVault/templates/adr.md` | **vault** | Frontmatter del §3.4 |
| `setup/scripts/adr-index.py` | repo | **Nuevo**: genera `ADRs/_INDEX.md` (UTF-8 sin BOM, `\n`) |
| `session-close` | repo | Rotación (§3.2) + conteo de líneas con aviso |
| `project-resume` (Code y Cowork) | repo | Lee `_INDEX.md`; ADR reciente condicional; `bugs/` solo `open` |
| `adr-writer` | repo | Frontmatter del §3.4 + invoca el script del índice |
| `design-doc-harvest` | repo | RFDs de `docs/**`: tabla del §3.5, redirección de referencias, "enriquece, no duplica" |
| `vault-drift-audit` | repo | 3 deberes nuevos; **está en 452 palabras** — mover detalle a `references/` para no pasar de 500 |
| `docs/telegram/05-RFD-T3-MEMORIA-Y-TOKENS.md` | repo | Referencia cruzada a este RFD (§3.1) |
| Vault de `claude-setup` | vault | Migración del §6 |
| ADR nuevo | vault | Esta decisión de convención merece su registro |

**Ojo: son dos repos.** Las plantillas viven en el git del vault
(`JoseFloreano/obsidian-vault`), no en el de `ClaudeSetup`. El spec debe tratarlos
como dos entregas con su propio commit.

Sin cambios: los 4 hooks, `sync-hooks.ps1`, `sync-skills.ps1`, `memory-keeper`,
`project-onboard` (hereda la plantilla corregida sin tocarse).

## 6. Plan de migración (solo `claude-setup`)

1. Los tres bloques `## Hecho` **con nota de sesión existente** se fusionan en
   ella (ahorro de tokens R1/R5/R7, registro de secretos, Telegram T2).
2. Los tres **huérfanos** pasan a notas retroactivas con su fecha real:
   Telegram T0, bloque de Cowork del 07-26, onboarding del 07-24.
3. El bloque del fix de `mark-code-dirty` se resume en una línea con wikilink al
   bug, que ya tiene el detalle completo.
4. `_PROJECT.md` se reescribe con el esqueleto del §3.1 → de 186 a ~110 líneas.
5. Frontmatter de los 5 ADRs unificado; `templates/adr.md` actualizado;
   `_INDEX.md` generado por el script.
6. Verificación: correr `project-resume` en sesión nueva y medir el arranque.

Los otros dos proyectos del vault se migran cuando les toque sesión: con el
proceso ya rodado y las plantillas corregidas, sale más barato después que ahora.

## 7. Criterios de aceptación

- [ ] `_PROJECT.md` ≤ 120 líneas y sin ninguna sección `## Hecho`.
- [ ] Ningún dato del histórico se perdió: cada bloque migrado es localizable por
      fecha en `sessions/` (verificable con grep de una frase de cada bloque).
- [ ] `ADRs/_INDEX.md` existe con **una línea por ADR de la carpeta** (5 hoy, 6
      cuando se escriba el de esta decisión) y el script lo regenera **byte a
      byte idéntico** al correrlo dos veces — comprobado por hash, en Windows.
- [ ] Los 5 ADRs tienen `status:` legible por máquina; el chequeo de
      `vault-drift-audit` los ve todos (antes veía 3).
- [ ] Arranque de `project-resume` ≈ **8-9 KB**, medido y no estimado, contando
      `_PROJECT.md` + `_INDEX.md` + bugs `open` (hoy cero).
- [ ] `design-doc-harvest` documenta el ciclo de RFDs **con el paso de
      redirección de referencias**, y se prueba en seco: `grep -rl` del RFD 02
      devuelve los 9 documentos que habría que actualizar.
- [ ] La plantilla del vault produce un `_PROJECT.md` conforme al contrato en un
      `project-onboard` de prueba.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| El índice driftea si alguien escribe un ADR a mano | `vault-drift-audit` compara índice↔archivos; el script regenera en un comando |
| El tope de 120 líneas no tiene enforcement duro | Deliberado (§4.4): aviso en `session-close` + reincidencia en la quincenal |
| `project-resume` con solo el índice pierde matiz al arrancar | Condicional del §3.3(b) y `summary` en cada línea |
| Migrar 6 bloques a mano puede perder algo | Criterio de aceptación explícito, verificación por grep |
| Cosechar un RFD borra contexto que aún se usaba | Disparador exige condiciones de auditoría cerradas + redirección previa de referencias |
| El script escribe con BOM y la idempotencia falla entre laptops | Requisito explícito (§3.3a) y criterio de aceptación por hash |
| Los cambios de plantilla viven en otro repo y se quedan sin commitear | §5 los trata como entrega aparte con su commit |

## 9. Decisiones cerradas

Las cuatro preguntas abiertas de v1, resueltas:

1. **Tope de `_PROJECT.md`**: 120 líneas blando, **150 duro**. Con dientes
   blandos: `session-close` cuenta y avisa; la auditoría quincenal reporta
   reincidencia. Sin hook nuevo.
2. **Qué lee `project-resume`**: el índice, más el ADR más reciente **solo si su
   fecha ≥ la última nota de sesión**. El `summary` decide en el resto de casos.
3. **Otros dos proyectos del vault**: no se migran ahora. Cuando les toque
   sesión, con el proceso rodado.
4. **Cosecha retroactiva del RFD 02 (T2)**: **todavía no**. Su auditoría se
   aprobó *con condiciones* (2 fixes + pasada manual) y siguen abiertas.

## 10. Evidencia y fuentes

- Medición local del vault (§1), 2026-08-01, re-verificada en la revisión.
- [MADR](https://adr.github.io/madr/) — vocabulario de `status`, subcarpetas solo
  a escala de cientos de ADRs, numeración local vs global.
- [adr.github.io](https://adr.github.io/) y
  [AWS Prescriptive Guidance: ADR process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
  — convenciones de organización y ciclo de vida.
- [Oxide RFD 1](https://rfd.shared.oxide.computer/rfd/0001) — estados del proceso
  RFD y por qué allí no se borran (contraste del §3.5).
- [Effective context engineering for AI agents (Anthropic)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  — recuperación just-in-time e identificadores ligeros.

## 11. Qué cambió en v2 y por qué

Revisión adversarial independiente (agente Fable, 2026-08-01), verificada punto
por punto antes de incorporarla:

| # | Hallazgo | v1 | v2 | Verificación |
|---|---|---|---|---|
| H1 | Ruta del template | `setup/templates/project-note.md` | `ObsidianVault/templates/` + `adr.md` + aviso de dos repos (§5) | `setup/templates/` solo tiene `scheduled-task-prompt.md`; `project-onboard:34` copia del vault |
| H2 | Presupuesto de arranque | ~25 KB → ~8 KB | **~36 KB → ~8-9 KB**, con regla de bugs `open` (§3.3c) | `bugs/` = 10 059 B y `project-resume` los lee; los 3 están cerrados |
| H3 | Borrado de RFDs | "git conserva la historia" | + redirección previa de referencias (§3.5.1) | `grep -rl` del RFD 02 → **9 documentos** |
| H4 | "Invisibles para la auditoría" | afirmación global | acotado a *un* chequeo concreto (§1.2) | el resto de `vault-drift-audit` no lee frontmatter de ADRs |
| H5 | Subcarpetas "rompen" las skills | argumento de ruptura | coste real de edición ×2 productos (§4.1) | las skills son instrucciones a un LLM, no glob rígido |
| H6 | Mediciones del §1 | 181 líneas / 4 notas | 186 líneas / 5 notas, deriva declarada (§1) | re-medido; la deriva refuerza la tesis |
| H7 | Cosecha del RFD 02 | ADR nuevo implícito | "enriquece el ADR existente, no duplica" (§3.5.2) | ya existe `ADR-20260801-puente-telegram` |
| — | RFD 05 (T3) | no contemplado | dependencia explícita (§3.1) | el RFD 05 trunca `_PROJECT.md` a ~2K chars |
| — | `codebase-map.md` | no contemplado | §3.7 | no existe hoy; `project-resume` lo leería |
| — | Tamaño de `vault-drift-audit` | no contemplado | mover detalle a `references/` (§5) | **452 palabras**, cerca del tope de 500 |
| — | Encoding del script | no contemplado | UTF-8 sin BOM + hash (§3.3a, §7) | el BOM ya se perdió 2 veces en este repo |
