# RFD — T3: el bot y el sistema de memoria (¿lo usa o solo lo paga?)

> **Estado:** propuesta, pendiente de aprobación. NO implementado.
> **Fecha:** 2026-08-01 (mediciones de ese día, por el auditor Cowork)
> **Contexto:** RFD 02 v2 (T2) · `setup/memory-instructions.md` · doc 16 (tokens)
> **Cambio de alcance:** el T3 original (rate limit, tope de costo, systemd)
> se pospone; este RFD ataca primero la pregunta de fondo.

---

## 1. Problema y evidencia medida

Montamos un sistema de memoria (vault + 29-31 skills + Memory Rules + hooks) y
el bot de Telegram lo **paga en cada invocación sin obtener casi nada**:

| Medición (2026-08-01) | Valor | Fuente |
|---|---|---|
| Skills cargadas en sesión bot (shared+claude-code) | **29** | árbol `setup/skills/` |
| Overhead de sus descriptions | 13.269 chars ≈ **3.3-4K tokens** + envoltura (~25/skill) ≈ **4-5K tokens fijos/invocación** | medido sobre los SKILL.md |
| Costo real por invocación (18 en logs) | piso 1-turno **$0.05-0.46**; mediana ≈ $0.42; picos $3.71/$4.53/$5.50 | `logs/daemon-202608.log` |
| `--add-dir` en `run_claude` | **ausente** — pero **irrelevante**: E1 probó que la lectura funciona igual | tg_daemon.py |

Diagnóstico por pieza:

1. ~~**Memory Rules → vault: orden imposible.**~~ **CORREGIDO tras E1
   (2026-08-01): la premisa era FALSA.** Se suponía que leer el vault desde el
   worktree se denegaba por estar fuera del cwd. E1 lo desmintió: el agente
   leyó `_PROJECT.md` sin una sola denegación. **Las lecturas no tienen frontera
   de directorio en ningún modo** — un hallazgo que además destapó el agujero
   de aislamiento de T2 (ver `02-RFD…` C0).

   Lo que sí queda en pie: **coste de contexto sin control**. Las reglas ocupan
   ~300 tokens en cada invocación y el agente gasta turnos localizando y leyendo
   archivos completos del vault. C1(b) sigue siendo la respuesta correcta, pero
   por otro motivo: no porque leer sea imposible, sino porque **inyectar es
   determinista y acotado** (sin turnos, sin búsqueda, con presupuesto) y
   mantiene el vault fuera de la superficie del agente.
2. **`adr-writer` y `memory-keeper` ordenan escribir al vault.** Aquí el
   problema no es que no puedan —podrían—, sino que **no deben**: darle al LLM
   escritura sobre el vault reabre lo que T2 cerró. Por eso salen del perfil bot
   (C2) y la escritura la hace el daemon (C4).
3. **Graphiti**: no desplegado (ADR vigente); las reglas ya dicen "skip
   silencioso" — correcto, coste marginal.
4. **Skills irrelevantes en sesión bot** (±15 de 29): `notify-telegram` (ya
   estás EN Telegram), `session-close`, `project-onboard/resume`, `skill-forge`,
   `design-doc-harvest`, `token-audit`, `model-benchmark`, `deploy-planner`,
   `git-bisect-assist`, `gdb-sanitizers-runbook`… Relevantes: las de
   convenciones/diseño/seguridad (`sql-conventions`, `python-*`, `api-design`,
   `web-security-review`, `secrets-scan`, `data-quality-gates`, etc.).
5. **Matiz honesto del ahorro**: las descriptions son prefijo cacheable — con
   cache hit cuestan ~10%. Pero las invocaciones del bot son espaciadas
   (TTL de cache 5 min): en uso móvil real, muchos misses. El ahorro estimado
   del recorte es real pero menor que el bruto: ~1.5-3K tokens/invocación
   efectivos.

## 2. Objetivos

**O1.** La primera invocación de cada conversación arranca CON el estado del
proyecto (resumen/pendientes), sin órdenes imposibles ni tools denegadas.
**O2.** El trabajo del bot deja rastro en el vault (hoy: cero memoria durable).
**O3.** Recortar el overhead fijo por invocación ≥40% sin perder las skills que
sí disparan en sesiones de desarrollo.
**O4.** Cero cambios en el comportamiento de las sesiones normales de laptop.

## 3. Casos de diseño

### C1. Cómo llega el contexto del proyecto al bot

| | (a) `--add-dir` al vault | (b) **El daemon inyecta** *(recomendada)* | (c) Nada |
|---|---|---|---|
| Cómo | Añadir el vault como dir adicional | El daemon (proceso normal, acceso pleno a OneDrive) lee `_PROJECT.md` y antepone un extracto (~2K chars máx) al prompt de la 1ª invocación de cada conversación | Quitar las órdenes de vault y ya |
| Riesgo | En modo escritura, Edit/Write aplicarían TAMBIÉN al vault → el sandbox se rompe | Cero permisos nuevos; código determinista; tamaño controlado | — |
| Frescura | Siempre viva | Snapshot al abrir conversación (suficiente: la conversación es corta) | — |

**Recomendación: (b)**, con (c) parcial: el CLAUDE.md que se copia al worktree
pasa a ser una **versión bot** sin las órdenes de vault/Graphiti (ver C3).
(a) se rechaza: reabre por la puerta trasera el aislamiento que T2 cerró.

### C2. Dieta de skills para el bot

| | (a) **Perfil propio** *(recomendada)* | (b) Flags del CLI | (c) Aceptar el costo |
|---|---|---|---|
| Cómo | `CLAUDE_CONFIG_DIR` del daemon con solo las ~14 skills relevantes; `sync-skills.ps1` gana un target `bot` (misma fuente, subset por lista) | `--setting-sources` o equivalente para no cargar skills de usuario (verificar E2 qué existe hoy) | — |
| Ahorro | ~2-2.5K tokens/inv efectivos | Igual o mayor, pero pierde TODAS (también las útiles) | 0 |
| Riesgo | Lista que mantener (se añade al registro del README) | Sin convenciones de datos en el bot | pagar ~$X/mes de ruido |

**Recomendación: (a).** La lista inicial vive en este RFD y se revisa en el
`vault-drift-audit` quincenal (misma mecánica que la poda R7).

### C3. CLAUDE.md versión bot

`create_worktree` copia hoy el CLAUDE.md íntegro. Propuesta: generar
`CLAUDE.md` bot-specific al crear el worktree — conserva convenciones del
proyecto y reglas de aislamiento de código; ELIMINA: órdenes de leer/escribir
vault (las cubre C1b/C4), reglas Graphiti (sin MCP en el bot), ancla de
Pendientes (la cubre C4). Menos órdenes imposibles = menos contexto y menos
intentos fallidos.

### C4. La memoria del bot la escribe EL DAEMON (no el agente)

En `/done` (y tras `/merge`), el daemon escribe una nota corta y determinista a
`10-Projects/<proyecto>/sessions/YYYY-MM-DD-tg-<slug>.md`: rama, commits
(shas+subjects), estado (mergeada/abandonada), y las líneas de
`.tg/progress.md` como resumen de etapas. Cumple O2 por la vía segura: el
agente nunca toca el vault; el proceso del daemon sí puede (es código nuestro,
no LLM). Compatible con las reglas 6-7 (nota de sesión propia, un escritor).

### C5. Experimentos previos (en la laptop, ~15 min, ANTES de implementar)

- **E1**: invocación desde un worktree pidiendo leer `_PROJECT.md` del vault →
  confirmar denegación (si NO se deniega, C1 cambia de urgencia, no de diseño).
- **E2**: `claude -p "lista las skills disponibles"` → confirmar que las skills
  cargan en headless y cuáles ve; probar el flag de fuentes de settings vigente.
- **E3**: invocación 1-turno trivial con `--output-format json` → leer `usage`
  (input_tokens, cache_read) para fijar la línea base real del overhead y
  validar la estimación de 4-5K.

## 4. Alcance

**Entra:** C1b (inyección por daemon) · C2a (perfil de skills bot) · C3
(CLAUDE.md bot) · C4 (nota de /done al vault) · E1-E3 · actualización del
README/registro. **No entra** (T3-bis, después): rate limit, tope de costo por
tarea, systemd/mini PC, triage con modelo barato (R2), session-search (R6).

## 5. Criterios de éxito

1. E3 antes/después: overhead fijo por invocación **−40% o más**.
2. Primera invocación de una conversación nueva menciona correctamente el
   estado/pendientes reales del proyecto (inyectados), sin tool denegada.
3. `/done` deja la nota en el vault y `project-resume` (laptop) la ve.
4. Una sesión normal de laptop no cambia en nada (mismas skills, mismo CLAUDE.md).
5. Las skills de convenciones siguen disparando en el bot (probar una petición
   de SQL → sql-conventions responde).
6. **El `codebase-map.md` inyectado se paga solo**: la primera invocación de una
   conversación nueva usa **menos turnos y menos costo** con mapa que sin él (la
   exploración que evita debe superar lo que cuesta). Si no baja, se revierte la
   decisión 3 del §6 — es una apuesta de ahorro y hay que medirla.
7. Ninguna skill fuera del registro de `setup/skills/README.md` llega al perfil
   bot (la ausencia de fila excluye por defecto).

## 6. Decisiones cerradas (respuestas del usuario, 2026-08-01)

**1. La lista de skills se mantiene**, pero necesitaba un sitio donde vivir. El
registro es ahora una **tabla en `setup/skills/README.md`** ("El cuarto
consumidor: el perfil `bot`"): una fila por skill, con ✓/✗ y el motivo.
**15 de 29** entran. Reglas: toda skill nueva añade su fila en el **mismo PR**;
se revisa en el `vault-drift-audit` quincenal; **si falta la fila, se excluye por
defecto** — mejor perder una skill que colar ruido en cada invocación.

El RFD fija el criterio, no la lista: entra si sirve para *leer o escribir código
desde un worktree aislado*; queda fuera si toca el vault, necesita herramientas
fuera de la lista blanca, o no tiene sentido ahí (notificar por Telegram desde
Telegram, dar de alta proyectos, cerrar sesiones, mantener el propio setup).

**2. La nota de C4 se escribe SOLO en `/done`.** No en `/write off` sin merge.
Motivo: `/write off` es una pausa, no un final — la conversación puede retomarse
con `/chat` y seguir en su rama. Escribir una nota ahí generaría entradas de
sesión para trabajo que aún no terminó, y el vault se llenaría de ruido. `/done`
es el único punto donde la conversación se declara acabada (mergeada o
abandonada), y por eso es el único que produce registro.

**3. El extracto de C1b incluye `codebase-map.md` cuando exista**, además de
`_PROJECT.md`.

El argumento del usuario, que es el correcto a plazo: **el mapa ahorra más
tokens de los que cuesta**. Sin él, el agente explora el repo con `Glob`/`Grep`/
`Read` para orientarse — y esa exploración se paga en cada conversación nueva,
en turnos y en tokens de salida. El mapa es un coste fijo pequeño que sustituye
un coste variable grande.

Condición para que el argumento se sostenga: **presupuesto separado y explícito**
—~2K chars para `_PROJECT.md` y ~2K para `codebase-map.md`, truncando por
secciones, no a mitad de línea—. Si el mapa creciera sin control dejaría de
ahorrar. Como el mapa lo regenera el hook git `post-commit` de Graphify, su
frescura no depende del bot.

Métrica para verificarlo (va a criterios de éxito): comparar turnos y costo de la
primera invocación de una conversación **con y sin** mapa inyectado. Si no baja,
la decisión se revierte — el argumento es de ahorro, así que debe medirse.
