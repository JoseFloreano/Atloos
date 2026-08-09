---
name: notify-telegram
description: >
  Envía al móvil por Telegram el resultado de la tarea que acaba de terminar.
  Use when the user says "mándamelo por telegram", "avísame por telegram cuando
  termine", "notifícame al terminar", "mándame el resultado por telegram",
  "ping me on telegram", o cuando lanza una tarea larga y pide que le avisen al
  acabar. NO usar para chatear desde Telegram (eso es el daemon, fase T1), ni
  por iniciativa propia: solo cuando el usuario lo pide explícitamente.
---

# Notify Telegram

Cierra el bucle de las tareas largas: el usuario se va del escritorio y recibe
el resultado en el móvil.

## Cuándo usar

- El usuario pidió aviso por Telegram al lanzar una tarea (aunque lo dijera al
  principio: recuérdalo y notifica **al terminar**, no antes).
- Terminó una tarea larga y el usuario ya no está mirando la sesión.

## Requisitos

- Script en **`~/.claude/scripts/notify_telegram.py`** (Windows:
  `%USERPROFILE%\.claude\scripts\notify_telegram.py`). Es la **misma ruta en
  toda máquina y no depende de dónde esté clonado el repo**: `sync-skills` lo
  instala ahí. Si falta, corre `sync-skills` una vez.
  *(Escape hatch: `TELEGRAM_NOTIFY_SCRIPT` gana si está definida — nada la
  define por defecto, es para instalaciones raras.)*

  > ⚠ **No busques el repo Atloos para ejecutarlo.** Esta skill corre desde
  > el cwd de cualquier proyecto y no hay relación de rutas que lleve de uno a
  > otro. El 2026-08-07 falló exactamente así: desde `alphadogs`, en la máquina
  > donde el puente estaba configurado, con las credenciales puestas — lo único
  > que faltaba era una ruta alcanzable.
- Credenciales en el entorno o en un `.env` local (el script las busca solo).
- **Fallback obligatorio**: si el script no existe o falla por falta de
  credenciales (exit 1), **dilo en una línea** y entrega la respuesta completa
  en el chat como siempre. Nunca dejes al usuario sin resultado por un fallo de
  notificación, y nunca pidas ni escribas el token tú.

## Pasos

1. **Termina la tarea primero.** La notificación es lo último; si la tarea
   falló, el aviso debe decir que falló.
2. **Compón un resumen corto** (≤15 líneas) con tres bloques:
   *qué se hizo* · *resultado* (✅/❌, números concretos: tests, archivos) ·
   *qué queda pendiente*. Sin markdown decorativo: se envía como texto plano.
3. **Ejecuta el script** (intérprete `py` en Windows):
   `py "$HOME/.claude/scripts/notify_telegram.py" "<resumen>"`
   (PowerShell: `py "$env:USERPROFILE\.claude\scripts\notify_telegram.py" "<resumen>"`)
   Si hay un artefacto que el usuario querrá leer entero (informe, log, diff),
   añade `--file <ruta>`. No hace falta trocear: el script manda resumen +
   adjunto solo si el texto pasa de 4096 caracteres.
4. **Verifica el resultado**: exit 0 e imprime `Enviado: ...` → confirma al
   usuario en una línea ("te lo mandé por Telegram"). Exit ≠ 0 → aplica el
   fallback del apartado anterior citando el error del script.

## Qué NO hacer

- No incluir secretos, tokens ni rutas absolutas de la máquina en el mensaje.
- No mandar el volcado completo de la sesión: el valor está en el resumen; lo
  extenso va como adjunto.
- No notificar cada paso intermedio — un aviso por tarea.
