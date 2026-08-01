# RFD — Progreso en vivo de las invocaciones (`/progress`)

> **Estado:** **APROBADO por el auditor** con cambios, aplicados en esta versión.
> No implementado.
> **Fecha:** 2026-08-01 (v2 tras revisión)
> **Contexto:** `02-RFD-T2-MODO-ESCRITURA.md` v2 (checkpoints C2) · `00-DISENO…` §2
> **Origen:** al probar T2, una tarea de desarrollo de 6-7 min es una caja negra
> hasta que termina; el checkpoint de 30 min llega demasiado tarde para saber si
> va bien o se atascó.

---

## 1. Problema

Hoy `run_claude` bloquea en `proc.communicate()` con `--output-format json`: no
hay ni una señal hasta que el proceso termina. Los checkpoints de T2 (C2) mitigan
el silencio, pero dependen de que el agente escriba `.tg/progress.md` y solo
disparan cada 30 minutos.

El fallo del 2026-08-01 lo dejó claro: una investigación consumió sus 15 turnos
durante 6m40s sin que el usuario pudiera ver que iba camino del límite.

## 2. Objetivo

**O1.** Ver, mientras la tarea corre, **qué está haciendo** el agente.
**O2.** Poder **encender y apagar la vista a mitad de ejecución**.
**O3.** No ensuciar el chat: el progreso no puede competir con la conversación.
**O4.** Cero regresiones en T1/T2 — `run_claude` es núcleo compartido.

**No objetivo:** mostrar el *thinking* crudo del modelo. En un móvil son
párrafos de divagación por paso; lo útil es qué hace, no qué rumia.

## 3. Decisión central: capturar siempre, mostrar bajo demanda

`--output-format stream-json` emite eventos según ocurren. El daemon los parsea
**siempre** a un búfer en memoria por chat, aunque no se muestre nada.

Consecuencias, y es lo que hace viable O2:

- Encender el panel a mitad de tarea muestra **lo ya ocurrido**, no solo lo que
  venga después.
- `/progress` (puntual) y el panel (continuo) dejan de ser dos mecanismos: son
  **dos vistas del mismo búfer**.
- Apagar no pierde nada; volver a encender lo recupera.

El búfer es efímero (vive lo que dura la invocación) y acotado: se guardan los
últimos N eventos relevantes, no el stream entero.

## 4. Comandos

```
/progress          foto del estado AHORA (pull, un mensaje suelto)
/progress live     panel en vivo: UN mensaje que se reescribe (push)
/progress off      apaga el panel; /progress sigue disponible
```

Un solo comando con subcomandos, que es la gramática que ya usa el bot
(`/write on|off`, `/model <x>`). Se descartó `/progress_detail`: 16 caracteres
en un móvil, y sugiere "otra cosa" cuando es la misma información con más
detalle y automática.

El interruptor `live` **persiste por chat** en `state.json`, como `/model`.

## 5. Casos de diseño

### P1. Qué muestra el panel

```
🔨 tg/20260801-subagentes · 6 min · sonnet · turno 23/60
✔ Leído docs/telegram/00-DISENO.md
✔ Creada carpeta subagentes/
⏳ Editando subagentes/README.md
```

Cabecera (rama, tiempo, modelo, **turnos consumidos/límite**) + últimas ~6
acciones.

El límite del contador se lee de la **constante del modo en curso**
(`MAX_TURNS` o `MAX_TURNS_WRITE`), nunca hardcodeado: si mañana suben, el panel
debe seguir diciendo la verdad.

Los hitos de `.tg/progress.md` (C2 de T2) **no desaparecen**: son complementarios.
El stream dice lo que el agente *hace* (denso, mecánico); `progress.md` dice lo
que el agente *considera un hito* (escaso, semántico). El panel muestra ambos:
hitos arriba, actividad abajo.

### P2. Un mensaje que se reescribe, no N mensajes

`editMessageText` sobre un único mensaje por invocación. Evita el spam (O3).

Sobre los límites de Telegram, con la corrección del auditor: el tope de ~20
mensajes/minuto es de **grupos**; en **chat privado** la guía es ~1 mensaje por
segundo. Aun así el panel no se reescribe por evento: **throttle de ~8 segundos**
y solo si el contenido cambió. El motivo no es tanto el límite como la
legibilidad — un panel que parpadea es ruido, y las ediciones también cuentan
para el rate limit.

**Edición final al terminar** (P3/P5): el panel se cierra con un resumen en vez
de quedarse congelado en la última acción:

```
✅ tg/20260801-subagentes · terminado en 6 min
Turnos: 23/60 · Costo: 0.42 USD
Última acción: Editado subagentes/README.md
```

Estado (✅ éxito · ⏹ límite de turnos · ❌ error), turnos, **costo real
(`total_cost_usd` del evento `result`)** y duración. Ese resumen es lo que queda
en el chat como registro de la tarea.

### P3. Encendido y apagado a media ejecución

- `/progress live` con una tarea en curso: crea el panel **ya**, con el búfer
  acumulado hasta ese instante.
- `/progress off`: deja de editar y fija el panel en su último estado (no lo
  borra: sigue siendo el registro de lo que pasó).
- Estos comandos **no** están sujetos al lock de un vuelo por chat: son de
  lectura y su utilidad es precisamente durante el vuelo.

### P4. Riesgo y contención (O4)

Cambiar el formato de salida toca el núcleo probado y afecta **también al modo
lectura**. Contención:

1. El último evento del stream (`type: result`) tiene **la misma forma** que el
   JSON de hoy — el parseo final no cambia, solo se añade lectura incremental
   por delante.
2. Se acumula el stream crudo: si no aparece un `result` válido, se cae al
   comportamiento actual con el texto acumulado.
3. El fix del 08-01 se mantiene: parsear siempre antes de mirar el `returncode`.

### P5. Qué eventos se muestran y cuáles no

| Evento | Panel |
|---|---|
| Uso de herramienta (`Read`, `Edit`, `Bash`…) | Sí — verbo + objeto corto |
| Resultado de herramienta | Solo si es error |
| Texto del asistente | Solo la primera línea, recortada |
| Thinking / deltas parciales | **No** (no objetivo) |
| `permission_denials` | Sí, destacado: es señal de que algo se bloqueó |

### P6. Alertas proactivas de anomalía *(añadido por el auditor)*

**El panel es opcional; las alertas no.** Van siempre, estén el panel y `live`
encendidos o apagados, porque son la respuesta real al fallo del 08-01: aquella
tarea murió tras 6m40s y el usuario no tuvo forma de saber que se acercaba al
límite. Un panel que hay que acordarse de encender no habría evitado nada.

| Alerta | Disparo | Mensaje |
|---|---|---|
| **Turnos** | Turnos consumidos ≥ **80%** del límite del modo | Una línea: «⚠️ 48/60 turnos; puede cortarse pronto» |
| **Silencio** | **>5 min** sin ningún evento del stream | Una línea: «⚠️ 5 min sin actividad del agente» |

Reglas comunes:

- **Máximo una de cada tipo por invocación.** Sin esto, una tarea larga que
  cruza el 80% mandaría una alerta por turno — el ruido que O3 prohíbe.
- Son **mensajes sueltos**, no ediciones del panel: deben notificar en el móvil
  aunque el panel esté apagado o enterrado en el historial.
- No interrumpen ni cancelan nada: informan. La decisión sigue siendo del
  usuario (esperar, o mandar «continúa» cuando termine).

La alerta de silencio se apoya en el mismo búfer: si no llega ningún evento en
5 minutos, o el agente está pensando muy largo o algo se atascó — en ambos casos
saberlo vale más que el silencio.

## 6. Alcance

**Entra:** `stream-json --verbose` con búfer por chat · los tres comandos ·
panel con throttle y **edición final con resumen** · contador de turnos leído
del modo · **alertas de P6 (siempre activas)** · fallback de P4 · pruebas de
no-regresión de T1/T2.

**No entra:** thinking crudo · progreso de varias tareas a la vez (eso llega con
el paralelismo del RFD 03) · notificaciones push fuera del chat.

## 7. Criterios de éxito

1. Modo lectura y escritura funcionan **igual que antes** (no-regresión).
2. Con una tarea en curso, `/progress` responde en <2 s con el estado real.
3. `/progress live` a mitad de tarea muestra lo ocurrido **antes** de encenderlo.
4. `/progress off` detiene las ediciones y deja el panel legible.
5. El panel no supera una edición cada ~8 s, y al terminar se cierra con el
   resumen (estado, turnos, costo, duración).
6. Si el stream se corrompe, la respuesta final **igual llega** (fallback).
7. El contador de turnos refleja el consumo real y el límite del modo en curso.
8. **Con el panel apagado**, una tarea que cruza el 80% de turnos genera **una**
   alerta (y solo una). Lo mismo con 5 minutos de silencio.
9. Reproducir el fallo del 08-01 (tarea que agota turnos) **con el panel
   apagado** produce aviso previo, en vez del silencio de 6m40s.

## 8. Decisiones cerradas (eran las preguntas abiertas de v1)

1. **El panel arranca APAGADO**, también en modo escritura. Encenderlo es
   `/progress live`. Lo que cubre el caso desatendido son las **alertas de P6**,
   que van siempre: el panel es para cuando estás mirando, las alertas para
   cuando no.
2. **`/progress` sin tarea en curso muestra la última invocación**, etiquetada
   con **«terminó hace X»** para que no se confunda con algo en marcha. Es más
   útil que un "nada en curso" — normalmente preguntas justo después de que algo
   acabó.

## 9. Hallazgos técnicos verificados (2026-08-01)

- **`--output-format stream-json` con `-p` EXIGE `--verbose`**: sin él el CLI
  sale con código 1 y `Error: When using --print, --output-format=stream-json
  requires --verbose`. Comprobado; hay que añadir el flag al construir el comando.
- **Eventos que emite**: `system` (varios, al inicio), `assistant` (con bloques
  `text` y `tool_use`), `user` (resultados de herramienta), `rate_limit_event`
  y `result` (final).
- **El evento `result` trae `subtype`, `num_turns`, `total_cost_usd`,
  `session_id` y `result`** — la misma forma que el JSON de hoy. Es lo que hace
  barata la contención de P4: el parseo final no cambia.
