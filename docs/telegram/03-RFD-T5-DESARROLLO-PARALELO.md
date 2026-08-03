# RFD — Desarrollo paralelo multi-proyecto desde Telegram

> **Estado:** IDEA REGISTRADA — no diseñada, no aprobada. Horizonte: T3 tardío
> o T5 (renumerado 2026-08-01: T4 pasó a ser "continuar en Telegram tras un
> aviso", ver `06-RFD-T4-CONTINUAR-DESDE-AVISO.md`), después de que T2 lleve
> semanas estable y exista la mini PC.
> **Origen:** idea del usuario (2026-08-01) al aprobar el modelo de worktrees
> de T2.
> **Contexto:** `02-RFD-T2-MODO-ESCRITURA.md` (v2, worktrees) · ADR del puente.

---

## 1. La idea, en palabras del usuario

En T2 el flujo es secuencial y basta: terminas de desarrollar algo, cambias de
conversación con `/chat` o `/p` y sigues con otro proyecto de inmediato — sin
tema. La idea futura es más ambiciosa: **hacer `/chat` A MITAD de un
desarrollo** y ponerte a trabajar en OTRO proyecto mientras el primero sigue
corriendo — dos (o más) desarrollos avanzando en paralelo, gobernados desde el
mismo chat de Telegram.

## 2. Por qué es factible (lo que T2 ya deja pagado)

- **El disco ya está aislado**: 1 conversación = 1 rama = 1 worktree. Dos
  desarrollos simultáneos no comparten archivos ni árbol — el problema duro
  del paralelismo quedó resuelto en T2 sin buscarlo.
- Las invocaciones `claude -p` son procesos independientes; los subagentes de
  cada uno son llamadas API concurrentes. La mini PC (8C/16T, 32 GB) se
  dimensionó exactamente para esto (doc 01).
- Los checkpoints de 30 min (T2) ya dan visibilidad por tarea larga.

## 3. Lo que SÍ hay que construir (por eso no es T2)

1. **El lock cambia de grano**: hoy es "un vuelo por chat" (INFLIGHT por
   chat_id); pasaría a "un vuelo por CONVERSACIÓN", con N conversaciones en
   vuelo a la vez. `/chat` a mitad de vuelo deja de bloquearse: cambia el foco
   y el desarrollo anterior sigue en background.
2. **Atribución de mensajes**: con 2+ tareas corriendo, toda salida del bot
   (respuestas, checkpoints, errores) debe llegar prefijada
   `[proyecto/rama]` — sin eso, el chat se vuelve ilegible. Probablemente
   también `/status` global (qué corre, desde cuándo, última etapa de cada uno).
3. **Enrutamiento del mensaje entrante**: un texto normal ¿va a la conversación
   en foco? ¿y si la en-foco está en vuelo? (¿cola por conversación, o
   rechazo con ⏳ por-conversación?). Es la decisión de diseño central.
4. **Presupuesto**: N tareas paralelas = N consumos simultáneos de
   tokens/costo. El tope de costo por tarea (ya planeado para T3) pasa de
   recomendable a obligatorio ANTES de esto.
5. **Recursos de la máquina**: 2-3 invocaciones pesadas + sus tests
   simultáneos en la mini PC — dimensionar `SEMAPHORE`/nº máximo de vuelos
   (2-3) y RAM por proceso (los leaks documentados de Claude Code multiplican).

## 4. Qué NO es esta idea

- NO es multi-agente sobre el MISMO repo (eso ya lo gobiernan las reglas 6-7
  del memory-snippet y no cambia): es multi-PROYECTO, un desarrollo por
  worktree.
- NO reemplaza el trabajo en la laptop: es la extensión del caso "estoy fuera
  y quiero que avancen dos cosas a la vez".

## 5. Prerrequisitos antes de diseñarla en serio

- [ ] T2 estable en uso real ≥2-3 semanas (worktrees, merge con botón, checkpoints).
- [ ] Mini PC operando 24/7 con el daemon bajo systemd (T3 base).
- [ ] Tope de costo por tarea implementado (T3).
- [ ] Las mejoras sencillas de T3 primero: triage con modelo barato (R2 `ecosistema/16`),
      rate limiting, session-search (R6) — más valor por menos riesgo que el
      paralelismo.

## 6. Criterio para promoverla a diseño

Cuando en el uso real de T2 te descubras ≥3 veces en una semana esperando a
que termine un desarrollo para arrancar otro que no tenía nada que ver — ese
es el síntoma de que la cola secuencial ya cuesta más que el diseño de esto.

---

*RFD de captura: registra la idea y sus fronteras para no re-pensarla desde
cero. Promoverla a diseño = sesión de brainstorming + actualización de este
doc a "propuesta" con los casos C del formato del RFD 02.*
