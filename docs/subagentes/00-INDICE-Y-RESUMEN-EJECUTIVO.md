# Subagentes en Workstreams Paralelos
## Índice y resumen ejecutivo

> **Fecha:** 2026-08-01 (investigado ese día; fuentes web fechadas en el propio texto)
> **Origen:** pregunta del usuario — cómo implementar en el repo un flujo "estilo
> Claude Code": varios subagentes trabajando cada uno en su workstream y su
> rama, y un agente principal que hace el merge a `main`.
> **Estado:** investigación CERRADA (docs finales). La ADOPCIÓN es lo que sigue
> en propuesta (RFD 04 de esta carpeta). **Actualización 2026-08-05:** ya NO
> es solo investigación — W2 dejó `workstream-dispatch` y
> `workstream-merge-gate` instaladas en `setup/skills/shared/`.
> **Método:** primero se agotó lo que el propio repo ya sabe (RFDs del puente
> Telegram, doc 12, skill `agentic-system-design`, doc 13); solo después se
> buscó afuera para llenar los huecos reales. Aplica el protocolo de auditoría
> de skills de terceros del `skills/10` §2 a cualquier adopción.

---

## Índice de documentos

| # | Documento | Tema |
|---|-----------|------|
| 00 | Este índice | Resumen ejecutivo y hallazgos |
| 01 | [Mecanismos nativos y externos](./01-MECANISMOS-NATIVOS-Y-EXTERNOS.md) | Qué existe ya: producto, Superpowers, plugin externo, lo propio |
| 02 | [Patrón propuesto y riesgos](./02-PATRON-PROPUESTO-Y-RIESGOS.md) | Cómo componerlo, con qué gate se mergea, qué cuesta y qué rompe |
| 03 | [Skills propuestas](./03-SKILLS-PROPUESTAS.md) | Qué NO crear (ya existe), qué sí, y el plan de adopción |
| 04 | [RFD de adopción](./04-RFD-ADOPCION-WORKSTREAMS.md) | ⭐ La ruta W0–W3. **W1 ✓ de facto (08-04) · W2 ejecutada (08-05) · W3 no disparado**; sin cosechar hasta la auditoría |
| 05 | [Limitaciones observadas](./05-LIMITACIONES-OBSERVADAS.md) | Evidencia empírica: 22 despachos (2026-08-04); su §3 = spec de las skills de W2 |
| 06 | [Investigación externa](./06-INVESTIGACION-EXTERNA-MULTIAGENTE.md) | Implementaciones, fallos y éxitos externos; enriquecimientos ①–⑩ para W2 |

---

## El hallazgo que gobierna esta investigación

**El mecanismo casi no hay que construirlo — ya existe en cuatro capas
distintas.** Lo que falta no es aislamiento ni orquestación: es una capa
delgada propia que conecte esas cuatro capas con NUESTRAS reglas (memoria por
`group_id`, criterio de merge, presupuesto). Construir el mecanismo desde cero
sería repetir exactamente el error que el doc 02 de la serie de memoria
advierte para grafos: sofisticación que ya resolvió otro, pagada dos veces.

Las cuatro capas, de más nativa a más nuestra:

```
1. PRODUCTO       claude --worktree <nombre> · Agent Teams (feb-2026)
                   → aislamiento de archivos y coordinación, ya en el CLI

2. FRAMEWORK       Superpowers ya instalado: using-git-worktrees,
   INSTALADO       dispatching-parallel-agents, subagent-driven-development,
                   finishing-a-development-branch
                   → metodología del ciclo completo, cero instalación nueva

3. PLUGIN          wshobson `agent-teams` (evaluado en doc 13, NO instalado)
   EXTERNO         → presets de equipo + file-ownership + interface contracts

4. PROPIO          `ADR-20260801-puente-telegram` (worktree + gate de merge) del puente Telegram (worktree por conversación,
   (YA ESCRITO)     gate de /merge con test verde + squash + botón caduco)
                   → la única pieza que ya resuelve ESTE problema con
                     NUESTRAS reglas, aunque hoy vive atada al bot
```

## Hallazgos (S1–S5)

**S1 — El repo ya diseñó esto una vez, para otro canal.** El `ADR-20260801-puente-telegram` (worktree por conversación)
(worktree por conversación, fuera de OneDrive, `CLAUDE.md` copiado al
worktree) y su C4 (`/merge` con test verde obligatorio + squash + botón que
caduca a 5 min) son exactamente el patrón "workstream aislado → un agente
coordinador mergea" que pregunta esta investigación. Está atado al puente
Telegram; generalizarlo fuera de él es más barato que rediseñarlo.

**S2 — Agent Teams (nativo, feb-2026) y el Workflow/subagents de este entorno
NO son el mismo mecanismo**, aunque el vocabulario se mezcle en la calle.
Agent Teams = teammates que se comunican entre sí y comparten una task list
(máx. recomendado ~5, doc 13 ya lo fijaba). El patrón subagents/Workflow de
este entorno (y el `dispatching-parallel-agents`/`subagent-driven-development`
de Superpowers) = agentes que **solo reportan al principal**, sin chat lateral
— más barato y más fácil de auditar. La distinción ya está en
`agentic-system-design` (§"Reglas de nuestro setup"); esta investigación
solo la aterriza a workstreams con rama.

**S3 — El costo escala con el número de frentes, no es gratis paralelizar.**
Fuentes 2026 (no verificadas por terceros, ver Fuentes en doc 01) reportan
$13 USD/día por agente activo como base, y un caso límite de 16 agentes
corriendo 2 semanas con costo cercano a $20,000 USD. La causa #1 de conflictos
reportada es la misma que el doc 12 ya diagnosticó para el vault: dos
escritores sobre el mismo archivo sin ownership.

**S4 — Nadie externo conoce nuestras Memory Rules.** Ni Agent Teams, ni el
plugin de wshobson, ni Superpowers saben que este repo exige `group_ids`
concretos y aislamiento de vault por proyecto (CLAUDE.md, reglas 1-5). Un
teammate lanzado a un workstream sin ese contexto puede escribir memoria al
`group_id` equivocado o tocar carpetas fuera de su proyecto. Es el único hueco
que ninguna pieza externa cierra — y el argumento más fuerte para escribir
algo propio en vez de solo instalar un plugin.

**S5 — El protocolo de importación (`skills/10` §2, doc 05 §2) sigue vigente sin
excepciones**, incluida esta investigación: el plugin `agent-teams` de
wshobson se lee completo antes de instalarlo, aunque doc 13 ya lo haya
evaluado favorablemente.

## Decisión propuesta (detalle en docs 02–03)

No construir un mecanismo de aislamiento nuevo. Usar `claude --worktree` /
Agent Teams (nativo) + los 4 skills de Superpowers ya instalados como base;
evaluar instalar el plugin `agent-teams` de wshobson cuando el caso de uso
aparezca de verdad; y escribir **dos piezas propias delgadas**:
`workstream-merge-gate` (generaliza el `/merge` del `ADR-20260801-puente-telegram` fuera del puente) y
`workstream-memory-briefing` (cierra el hueco S4). Ninguna reemplaza lo que ya
existe — rellenan exactamente lo que falta.

---

*Carpeta nueva `docs/subagentes/`, numeración local (00–03) como el resto de
subseries del repo (patrón fijado por `bd-y-nube/`).*
