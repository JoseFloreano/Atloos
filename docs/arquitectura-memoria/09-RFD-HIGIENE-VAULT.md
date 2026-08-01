# RFD — Higiene de contexto y ciclo de vida del vault

> **Versión:** v1 (2026-08-01)
> **Estado:** propuesta — **pendiente de validación**. Nada implementado.
> **Contexto previo:** `01-OBSIDIAN-MEMORIA-EXTERNA.md` · `06-ARQUITECTURA-FINAL-RECOMENDADA.md` ·
> `07-HALLAZGOS-CRITICOS-REFERENCIA-RAPIDA.md` · skills `project-resume`,
> `session-close`, `adr-writer`, `design-doc-harvest`, `vault-drift-audit`
> **Método:** brainstorming de Superpowers, sobre medición del vault real (no estimaciones).
> **Nota:** este RFD se rige por la regla que él mismo propone (§3.5) — cuando lo
> aquí decidido esté implementado y auditado, se cosecha a ADR y este archivo se borra.

---

## 1. Problema

El vault funciona: tres capas operativas, hooks anti-drift, aislamiento por
proyecto. Lo que no tiene es **política de crecimiento**. Cada sesión añade y
ninguna quita, así que el archivo más leído del sistema es también el que más
engorda.

Medición del proyecto `claude-setup` a 2026-08-01 (9 días de vida, 13 notas):

| Señal | Valor |
|---|---|
| `_PROJECT.md` | **181 líneas / 11 931 bytes** |
| De eso, secciones `## Hecho` | **70 líneas (39%) en 6 secciones** |
| `ADRs/` | 17 486 bytes en 5 archivos |
| `sessions/` | 29 622 bytes en 4 archivos |
| Lectura de `project-resume` en cada arranque | `_PROJECT.md` + 3 ADRs ≈ **25 KB (~6-7k tokens)** |
| Ritmo de creación | ~1,3 notas/día |

Tres síntomas concretos, no hipotéticos:

1. **`_PROJECT.md` es un changelog disfrazado de estado.** Las seis secciones
   `## Hecho` están intercaladas entre las estables — "Convenciones" y
   "Pendientes" quedaron partidas entre bloques de historia — y ni siquiera en
   orden cronológico. El coste lo paga cada arranque de sesión.
2. **El frontmatter de los ADRs no es uniforme**: 3 usan `status:` (inglés), 2
   usan `estado:` (español, uno con comentario inline). `vault-drift-audit` busca
   literalmente ADRs con `status: accepted` → **dos ADRs son invisibles para la
   auditoría que debería vigilarlos**.
3. **Los RFDs no tienen final.** `02-RFD-T2-MODO-ESCRITURA.md` dice "no aprobado
   como fase" mientras `_PROJECT.md` da T2 por implementado. Dos fuentes de
   verdad sobre lo mismo, divergiendo — que es exactamente el fallo que el vault
   existe para evitar.

## 2. Objetivo

- El arranque de sesión cuesta **~8 KB en vez de ~25 KB**, sin perder el "por qué"
  de las decisiones (se recupera bajo demanda, no de entrada).
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

Esqueleto **fijo y cerrado**, tope de **~120 líneas**:

```
Qué es · Estado actual · Decisiones clave · Bugs abiertos ·
Convenciones · Pendientes · Próximo paso
```

- **Prohibidas las secciones `## Hecho`.** Lo que pasó va a `sessions/`.
- "Estado actual" es un **presente**, no un acumulado: describe cómo está el
  sistema hoy, no cómo llegó hasta aquí.
- `setup/templates/project-note.md` se actualiza para que los proyectos nuevos
  nazcan con este contrato.

### 3.2 Rotación en `session-close`

Paso nuevo en la skill: antes de cerrar, lo hecho en la sesión se escribe en
`sessions/<fecha>-<tarea>.md`, y de `_PROJECT.md` **solo** se tocan Estado
actual, Pendientes y Próximo paso.

Encaja con los hooks sin modificarlos: `check-vault-updated` y `memory-flush` ya
aceptan una nota de `sessions/` fresca como satisfacción del flag. La rotación
los alimenta en vez de pelearse con ellos.

### 3.3 `ADRs/_INDEX.md` generado + recuperación just-in-time

Script `setup/scripts/adr-index.py` (stdlib, **sin LLM**, en la línea del "gate
sin LLM" de las scheduled tasks): lee el frontmatter de cada ADR y emite una
línea por decisión — `fecha · status · título · una frase`. Lo invoca
`adr-writer` justo después de crear un ADR.

`project-resume` pasa a leer **el índice** en el arranque, y abre un ADR completo
solo cuando la tarea de hoy lo roza. Es recuperación just-in-time: el agente
mantiene identificadores ligeros y carga el contenido cuando lo necesita.

Ahorro: ~13 KB por arranque (los 3 ADRs suman 13,7 KB; el índice ~1 KB), sin
perder trazabilidad — el índice dice qué existe
y dónde, que es lo que hace falta para decidir si vale la pena abrirlo.

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
| Implementado **y auditado** | **cosecha** → ADR → `git rm` del RFD |
| Abandonado | se borra sin ADR, con confirmación |

El ADR de cosecha absorbe lo que hay que conservar: decisión, **alternativas
rechazadas y su porqué**, trade-offs aceptados y **deltas diseño↔implementación**
(donde suele estar el aprendizaje), citando el sha. Borrar es seguro: git
conserva la historia completa.

Cada RFD lleva su estado en la cabecera para que se vea de un vistazo cuál está
listo para cosecha. Contraste deliberado con el proceso RFD de Oxide, donde los
RFD **nunca** se borran: allí el RFD *es* el registro durable y no hay ADR
aparte. Aquí existen las dos capas, y mantener ambas vivas produce justamente la
divergencia del §1.3.

### 3.6 Archivo de `sessions/`

**Nada se borra.** Una nota de sesión cuyo contenido ya está en un ADR o en un
bug se marca como cosechada; `vault-drift-audit` propone moverla a
`_archive/` **dentro de la carpeta del proyecto** pasados ~30 días.

`_archive/` es local al proyecto a propósito: usar `40-Archive/` del vault
obligaría a modificar la regla de aislamiento ("solo `10-Projects/<proyecto>/`,
`brain/`, `daily/`"), y ese precio no compensa por mover archivos que nadie lee.

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
- **Rompe dos skills**: `project-resume` de Code y de Cowork hacen "lista
  `ADRs/`, ordena por la fecha del nombre, coge los 3 últimos". Con subcarpetas
  eso pasa a listado recursivo, a cambio de nada con 5 ADRs.
- **MADR** contempla subcarpetas solo para repositorios con *cientos* de ADRs, y
  avisa del coste: la numeración deja de ser única global.
- El beneficio real —que es humano y legítimo— lo da el índice del §3.3 más
  barato y sin coste para el agente.

**Umbral para reabrirlo:** ~25-30 ADRs en un proyecto, o la aparición de un
segundo eje real (p. ej. el servidor 24/7 como subsistema con vida propia). Aun
entonces, primero tags + índice; carpetas solo si eso se queda corto.

### 4.2 Borrar el RFD en cuanto nace el ADR — rechazada

Un RFD sigue siendo útil mientras la decisión está viva pero sin implementar (el
`03-RFD-T3-T4` (ahora T5) es un registro de ideas, no hay nada que cosechar). El disparador
correcto es "implementado **y auditado**", no "decidido".

### 4.3 Archivar en `40-Archive/` del vault — rechazada

PARA-correcto sobre el papel, pero obliga a ampliar la regla de aislamiento de
memoria por un beneficio cosmético. Ver §3.6.

### 4.4 Un hook que imponga el tope de `_PROJECT.md` — rechazada por ahora

El sistema ya tiene tres hooks anti-drift y **acaba de cerrarse un bug de falso
positivo** en ellos (`bug-mark-code-dirty-falso-positivo`). Un aviso que salta
cuando no toca entrena a ignorarlo. El tope es convención; `vault-drift-audit`
lo reporta en su ciclo quincenal, que es la frecuencia adecuada para esto.

### 4.5 Índice escrito a mano o generado por un pase LLM — rechazada

A mano driftea; con LLM se paga por algo que es parseo de frontmatter. El script
determinista es la opción correcta, coherente con la lección del §R7 del doc 16
(el Curator de Hermes: 91M tokens quemados en un pase masivo).

## 5. Impacto

| Archivo / skill | Cambio |
|---|---|
| `setup/templates/project-note.md` | Esqueleto nuevo con el contrato del §3.1 |
| `setup/scripts/adr-index.py` | **Nuevo**: genera `ADRs/_INDEX.md` desde el frontmatter |
| `session-close` | Paso de rotación (§3.2) |
| `project-resume` (Code y Cowork) | Lee `_INDEX.md`; abre ADRs completos bajo demanda |
| `adr-writer` | Frontmatter del §3.4 + invoca el script del índice |
| `design-doc-harvest` | Cubre RFDs de `docs/**` con la tabla del §3.5 |
| `vault-drift-audit` | Verifica índice↔archivos, tope de `_PROJECT.md`, notas cosechadas >30 días |
| Vault de `claude-setup` | Migración del §6 |
| ADR nuevo | Esta decisión de convención merece su registro |

Sin cambios: los 4 hooks, `sync-hooks.ps1`, `sync-skills.ps1`, `memory-keeper`,
`project-onboard` (hereda el template nuevo sin tocarse).

## 6. Plan de migración (solo `claude-setup`)

1. Los tres bloques `## Hecho` **con nota de sesión existente** se fusionan en
   ella (ahorro de tokens R1/R5/R7, registro de secretos, Telegram T2).
2. Los tres **huérfanos** pasan a notas retroactivas con su fecha real:
   Telegram T0, bloque de Cowork del 07-26, onboarding del 07-24.
3. El bloque del fix de `mark-code-dirty` se resume en una línea con wikilink al
   bug, que ya tiene el detalle completo.
4. `_PROJECT.md` se reescribe con el esqueleto del §3.1 → de 181 a ~110 líneas.
5. Frontmatter de los 5 ADRs unificado; `_INDEX.md` generado por el script.
6. Verificación: correr `project-resume` en sesión nueva y comprobar que el
   arranque baja a ~8 KB sin perder nada que hiciera falta.

Los otros dos proyectos del vault se migran cuando les toque sesión, no ahora.

## 7. Criterios de aceptación

- [ ] `_PROJECT.md` ≤ 120 líneas y sin ninguna sección `## Hecho`.
- [ ] Ningún dato del histórico se perdió: cada bloque migrado es localizable por
      fecha en `sessions/` (verificable con grep de una frase de cada bloque).
- [ ] `ADRs/_INDEX.md` existe, tiene 5 líneas y el script lo regenera **idéntico**
      al correrlo dos veces (idempotencia).
- [ ] Los 5 ADRs tienen `status:` legible por máquina; `vault-drift-audit` los ve
      todos (antes veía 3).
- [ ] Arranque de `project-resume` ≈ 8 KB (medido, no estimado).
- [ ] `design-doc-harvest` documenta el ciclo de RFDs y se aplica al caso real
      pendiente: cosechar el RFD 02 (T2) cuando pase su auditoría.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| El índice driftea si alguien escribe un ADR a mano | `vault-drift-audit` compara índice↔archivos; el script regenera en un comando |
| El tope de 120 líneas no tiene enforcement | Deliberado (§4.4). Se reporta en la auditoría quincenal |
| `project-resume` con solo el índice pierde matiz al arrancar | Abre el ADR completo en cuanto la tarea lo roza; el índice lleva `summary` para decidir |
| Migrar 6 bloques a mano puede perder algo | Criterio de aceptación explícito con verificación por grep |
| Cosechar un RFD borra contexto que aún se usaba | El disparador exige auditoría pasada, y git conserva todo |

## 9. Preguntas abiertas — a validar antes de implementar

1. **¿120 líneas es el tope correcto para `_PROJECT.md`?** Con el esqueleto
   propuesto, hoy quedaría en ~110. Si se prefiere más aire, 150 sigue siendo
   sano; por encima de eso vuelve el problema.
2. **¿`project-resume` debe leer solo el índice, o índice + el ADR más reciente?**
   La segunda es más conservadora (+3 KB) y quizá más cómoda al retomar.
3. **¿Se migran también `alphadogs` y `tt1-revisor-chatbot` ahora?** La propuesta
   es no: cada uno cuando le toque sesión, con el trabajo repartido.
4. **¿El ciclo de cosecha de RFDs aplica retroactivamente al RFD 02 (T2)?**
   Depende de si la auditoría de Cowork se considera requisito o ya se da por
   buena la evidencia de las 8 pruebas.

## 10. Evidencia y fuentes

- Medición local del vault (§1), 2026-08-01.
- [MADR](https://adr.github.io/madr/) — vocabulario de `status`, subcarpetas solo
  a escala de cientos de ADRs, numeración local vs global.
- [adr.github.io](https://adr.github.io/) y
  [AWS Prescriptive Guidance: ADR process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
  — convenciones de organización y ciclo de vida.
- [Oxide RFD 1](https://rfd.shared.oxide.computer/rfd/0001) — estados del proceso
  RFD y por qué allí no se borran (contraste del §3.5).
- [Effective context engineering for AI agents (Anthropic)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
  — recuperación just-in-time, identificadores ligeros y el papel de la jerarquía
  de carpetas y los nombres en cómo un agente infiere propósito.