# Ahorro de tokens: lo robable de Hermes y OpenClaw
## Mecanismos minados de sus docs oficiales, mapeados a NUESTRO setup

> **Fecha:** 2026-08-01
> **Contexto:** el doc 14 descartó adoptarlos; este doc extiende su §7 minando
> su mecánica interna de economía de tokens (fuentes primarias: docs.openclaw.ai,
> hermes-agent.nousresearch.com, repos) para construir lo que valga la pena
> en el setup propio y en el puente Telegram (ADR-20260801-puente-telegram).
> Números de terceros marcados; los auto-reportados de blogs NO son verificables.

---

## 1. Lo que YA tenemos (no construir — validación de nuestro diseño)

- **Progressive disclosure de skills**: el mecanismo estrella de ambos
  (Hermes: lista de metadata ~3K tokens, cuerpo on-demand; OpenClaw: bloque
  compacto ~24 tokens/skill) **es exactamente el modelo Agent Skills de Claude
  Code** que ya usamos — descripciones-trigger cortas, cuerpo <500 palabras,
  references/ bajo demanda. Confirmación externa de H3/H4 y de nuestra regla
  "la description es el trigger".
- **Memoria como archivos, no como transcript**: su MEMORY.md ≈ nuestro vault
  + CLAUDE.md <500 tokens (H4). Hermes además la inyecta *congelada* para no
  romper el prefix cache — refuerzo de nuestra regla de CLAUDE.md estable.
- **Caps de iteración**: `max_turns` de Hermes ≡ `--max-turns` de Claude Code
  (existente; solo hay que USARLO en el daemon).
- **Caps de gasto monetario**: no existen en ninguna de las dos (solo
  reportes de uso). No estamos atrás en nada aquí.

## 2. Qué construir — ranking ahorro × esfuerzo

### R1. Patrón "heartbeat barato" para scheduled tasks y daemon (ALTO ahorro, esfuerzo bajo)

Lo mejor documentado de OpenClaw: sus heartbeats evitan quemar tokens con
cuatro palancas — sesión aislada por corrida (docs: **~100K → 2-5K tokens por
run**), prompt mínimo, **skip total de la llamada API si HEARTBEAT.md está
vacío**, y respuesta-token `HEARTBEAT_OK` que se descarta sin entregar.

**Nuestra versión**: para cada scheduled task periódico de Cowork y para
cualquier cron con `claude -p`:
1. La tarea revisa PRIMERO (sin LLM: script/condición) si hay algo que hacer —
   archivo checklist no-vacío, git con cambios, inbox con items. Nada → **no
   se invoca a Claude en absoluto**.
2. Cuando sí corre: sesión fresca (sin `--resume` de un historial kilométrico),
   prompt corto, y convención "si no hay nada que reportar responde `OK` y
   nada más" — el daemon descarta los `OK`.

### R2. Triage con modelo barato en el puente Telegram (ALTO, medio)

Patrón compartido (utilityModel de OpenClaw / 11 slots auxiliares de Hermes:
"un chat model rápido hace el trabajo a 1/50 del costo"): **modelo barato
clasifica, frontier ejecuta**. En el daemon: un primer pase con Haiku
(`claude -p --model haiku`, o llamada API directa) decide si el mensaje es
(a) trivial/social/consulta al estado → lo responde el barato, (b) tarea real
→ pasa al modelo de la sesión. Comando `/model` para forzar. Regla de Hermes
que adoptamos tal cual: **no cambiar de modelo a mitad de sesión** (rompe el
prompt cache y re-lee todo el contexto).

### R3. TTL y reset de sesiones en el daemon (ALTO, bajo)

OpenClaw resetea sesiones por defecto (diario 4 AM o por idle) — un `--resume`
eterno arrastra contexto que pagas en cada turno. En el daemon: reset por
proyecto tras N horas de idle (propuesta: 24 h) o `/new` explícito; la
continuidad la da el vault (project-resume), NO el transcript. Es la misma
filosofía de nuestra arquitectura: la memoria durable vive en archivos.

### R4. Mention-gating y "observar sin despachar" (ALTO si hay grupos, bajo)

Ambos lo tienen: en grupos, sin mención explícita **no se invoca al agente**
(cero tokens); Hermes además anexa lo no-mencionado como contexto observado.
En el daemon v1 (chat privado) basta la allowlist; si algún día se mete a un
grupo, `require_mention` es innegociable.

### R5. Hook PreCompact "memory flush" (MEDIO, bajo — y es MUY nuestro)

OpenClaw corre un turno silencioso ANTES de compactar que guarda lo importante
a archivos de memoria, y luego compacta agresivo. Claude Code tiene hook
**PreCompact**: añadir `memory-flush.py` que inyecte el recordatorio "antes de
compactar: pendientes/decisiones nuevas → _PROJECT.md o nota de sesión (reglas
6-7)". Encaja con el anti-drift existente: la compactación deja de ser el
momento donde se pierde lo no registrado.

### R6. Búsqueda FTS sobre historial en vez de re-inyectar transcripts (MEDIO, medio)

Hermes indexa todas las sesiones en SQLite FTS5 y busca texto real en ~20 ms
con **costo LLM cero** — en vez de resumir o re-abrir conversaciones viejas.
Nuestra versión: skill/script que indexe los JSONL de sesiones de Claude Code
(`~/.claude/projects/`) en SQLite FTS5 → "¿en qué sesión arreglamos X?" se
responde con grep semántico barato, no cargando transcripts al contexto.
Candidata a skill `session-search` (Fase 2, cuando el server exista).

### R7. Analytics de uso de skills + poda estilo Curator, en manual (BAJO, bajo)

El Curator de Hermes poda skills sin uso (30 días stale, 90 archivo) y
consolida solapadas. Su lección negativa también: el pase LLM sin guardrails
quemó 91M tokens a un usuario (issue #44771). Nuestra versión manual y gratis:
al `vault-drift-audit` quincenal añadirle "¿qué skills no se han disparado
este mes?" y decidir poda/fusión con `skill-forge` — cero LLM recurrente.
(Complementa la regla ya adoptada del doc 14: 3+ repeticiones → skill.)

### R8. Budget-switch de modelo (BAJO hoy — somos suscripción, no API)

El "smart model manager" comunitario (presupuesto de horas + switch a modelo
barato al agotarse; ahorros auto-reportados 80-90%, NO verificables) solo paga
cuando facturas por token. Anotado para el futuro; su lección sí aplica hoy:
si copiamos el patrón fallback, el switch va **en estado/memoria, no
reescribiendo el config** (bug real de OpenClaw #47705: el fallback se vuelve
permanente).

## 3. Orden de implementación propuesto

| # | Pieza | Cuándo | Estado |
|---|-------|--------|--------|
| 1 | R1 en los scheduled tasks existentes (gate sin-LLM + sesión aislada + convención OK) | Ya — no depende del server | ✅ 2026-08-01 — `setup/templates/scheduled-task-prompt.md` (+ nota en `setup/README.md`) |
| 2 | R5 hook PreCompact memory-flush | Ya — media hora, entra con los hooks actuales | ✅ 2026-08-01 — `setup/hooks/memory-flush.py`, cableado en `sync-hooks.ps1`, probado E2E |
| 3 | R3 + R4 + `--max-turns` en el diseño del daemon | T1 del bridge (nacen dentro del código, gratis) | — |
| 4 | R2 triage Haiku + `/model` | T2 del bridge | — |
| 5 | R6 session-search FTS5 | Cuando el server esté operando | — |
| 6 | R7 en vault-drift-audit | Próxima revisión quincenal | ✅ 2026-08-01 — paso 6 del checklist de la skill |

> **Corrección de campo (2026-08-01, al implementar R5):** PreCompact **no puede
> "inyectar" contexto** — no admite `hookSpecificOutput.additionalContext`. Su
> único canal hacia Claude es `decision: "block"` / exit 2, que en este evento
> significa *blocks compaction*. El recordatorio se entrega, por tanto, pausando
> la compactación una vez (y solo una: marca `precompact_flushed`, porque una
> auto-compactación bloqueada en bucle ahogaría la sesión). Sale mejor de lo
> previsto: el volcado ocurre con el contexto todavía íntegro.

## 4. Fuentes

docs.openclaw.ai (concepts/models, gateway/heartbeat, reference/token-use,
concepts/memory, concepts/compaction, tools/skills, concepts/session,
concepts/usage-tracking) · hermes-agent.nousresearch.com (configuring-models,
features/memory, features/curator, features/skills, messaging/telegram,
configuration) · github: openclaw#47705, Hermes-Agent#44771 (anecdótico) ·
perelweb.be (smart model manager — comunidad, cifras no verificables).
Informe completo del agente minero en la sesión 2026-08-01.

---

*Extiende `14-HERMES-Y-OPENCLAW.md` (§7). El veredicto "no adoptar" no cambia;
esto es la cosecha. R1-R5 se referencian desde el ADR del puente Telegram.*
