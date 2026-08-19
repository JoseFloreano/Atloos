#!/usr/bin/env python3
"""
progress.py — Seguimiento en vivo de una invocación.
Decisión: ADR-20260801-puente-telegram, sección "Progreso en vivo" (vault).

Consume los eventos de `claude -p --output-format stream-json --verbose` y
mantiene el estado de la tarea en curso. No sabe nada de Telegram: el daemon le
pregunta qué mostrar y cuándo.

Principio del RFD: **capturar siempre, mostrar bajo demanda**. El tracker se
alimenta aunque el panel esté apagado, así que encenderlo a media tarea muestra
lo que YA pasó.

El panel es opcional; **las alertas de P6 no** — van siempre, porque el caso que
motivó todo esto (una tarea que agotó turnos en silencio) ocurre justamente
cuando nadie está mirando.
"""
import time
from collections import deque

MAX_ACTIONS = 6           # últimas acciones visibles en el panel
EDIT_THROTTLE = 8         # segundos mínimos entre ediciones del panel
TURN_ALERT_RATIO = 0.8    # avisar al 80% del límite de turnos
TIMEOUT_ALERT_RATIO = 0.8 # avisar al 80% del TECHO DE TIEMPO (sprint 16)
SILENCE_ALERT = 300       # 5 min sin eventos del stream

# Verbo legible por herramienta; lo que no esté aquí sale con su nombre crudo.
VERBS = {"Read": "Leído", "Write": "Escrito", "Edit": "Editado",
         "MultiEdit": "Editado", "Grep": "Buscado", "Glob": "Listado",
         "Bash": "Ejecutado", "WebFetch": "Descargado", "Task": "Subagente",
         "TodoWrite": "Plan actualizado", "NotebookEdit": "Notebook"}


def _short(value: str, n: int = 46) -> str:
    value = " ".join(str(value or "").split())
    return value if len(value) <= n else value[: n - 1] + "…"


def fraccion_turnos(n: int, tope: int) -> str:
    """`n/tope` cuando la fracción se puede leer; si no, se dice qué pasa.

    POR QUÉ (auditoría 39 §3.3 y §13.3). El humano recibía «Turnos: 30/15», un
    numerador que dobla a su denominador. El sprint 16 lo movió de un contador
    a otro, y el auditor demostró que **seguía pudiendo pasar**: 20 eventos
    contra un tope de 15 imprimían «Turnos: 20/15». Anclar el arnés en 15
    eventos —justo el valor que lo hace pasar— fue mi error, y era el mismo
    patrón que este sprint persigue.

    LO QUE ESTÁ MEDIDO (2026-08-19), y por qué NINGÚN contador vale de
    numerador fiable:

      · `claude -p … --max-turns 1`  → `subtype=error_max_turns`, `num_turns=2`
        El flag SÍ corta. Pero devuelve 2 con un tope de 1.
      · `claude -p … --max-turns 4` (tarea terminada) → eventos `assistant`= 3,
        `num_turns` = 2. Los tres números difieren, y sin razón fija.
      · `--resume` NO acumula `num_turns` (2 → 2): esa hipótesis queda refutada.
      · En campo (SER8, 08-18) el aviso saltó con **12** eventos y el cierre
        declaró `num_turns=10`: se cruzan en las dos direcciones.

    Conclusión: `--max-turns` acota de verdad, pero ni el contador de eventos ni
    `num_turns` están garantizados en su unidad. Así que la fracción se imprime
    mientras se sostiene, y cuando no, se dice — nunca una fracción imposible.

    Queda un dato SIN explicar y se deja escrito en vez de taparlo: el log de la
    Legion tiene una lectura del 08-01 18:00 con `turnos=30` contra un tope de
    15 y `subtype=success`. (El otro caso, `turnos=32` de la 01:23, sí está
    explicado: `--max-turns` entró en el daemon a las 02:18 de ese mismo día,
    55 min después — esa invocación corrió SIN tope.)
    """
    if not tope:
        return str(n)
    if n <= tope:
        return f"{n}/{tope}"
    return f"{n} (el límite del modo era {tope}; el contador va en otra unidad)"


def _describe(name: str, tool_input: dict) -> str:
    """Una línea por uso de herramienta: verbo + objeto reconocible."""
    verb = VERBS.get(name, name)
    data = tool_input or {}
    obj = ""
    if "file_path" in data:
        obj = str(data["file_path"]).replace("\\", "/").split("/")[-1]
    elif "command" in data:
        obj = str(data["command"])
    elif "pattern" in data:
        obj = str(data["pattern"])
    elif "description" in data:
        obj = str(data["description"])
    return f"{verb} {_short(obj)}".strip()


class ProgressTracker:
    """Estado vivo de UNA invocación."""

    def __init__(self, branch: str = "", model: str = "", max_turns: int = 0,
                 write_mode: bool = False, timeout: int = 0):
        self.branch = branch
        self.model = model or "default"
        self.max_turns = max_turns          # límite REAL del modo, no hardcodeado
        self.timeout = timeout              # techo REAL del modo, por lo mismo
        self.write_mode = write_mode
        self.started = time.time()
        self.last_event = time.time()
        self.actions = deque(maxlen=MAX_ACTIONS)
        self.turns = 0                      # unidad del FLAG `--max-turns`
        self.turns_cli = 0                  # unidad del CLI (`num_turns`): NO
                                            # es la misma, ver `feed`
        self.cost = 0.0
        self.subtype = ""
        self.denials = 0
        self.finished = False
        self.milestone = ""                 # última línea de .tg/progress.md
        self._alerts_sent = set()           # una alerta de cada tipo por invocación
        self._last_edit = 0.0
        self._last_text = ""
        self.panel_msg_id = None            # id del mensaje-panel, si está vivo

    # ── Ingesta ───────────────────────────────────────────────────────────
    def feed(self, event: dict) -> None:
        """Consume un evento del stream. Nunca lanza: un evento raro no puede
        tumbar la invocación."""
        try:
            self.last_event = time.time()
            etype = event.get("type")
            if etype == "assistant":
                for block in (event.get("message") or {}).get("content") or []:
                    if block.get("type") == "tool_use":
                        self.actions.append(_describe(block.get("name", "?"),
                                                      block.get("input")))
                    elif block.get("type") == "text":
                        text = (block.get("text") or "").strip()
                        if text:
                            self.actions.append(f"💬 {_short(text.splitlines()[0], 60)}")
                self.turns += 1
            elif etype == "result":
                self.finished = True
                self.subtype = event.get("subtype") or ""
                # ⚠ `num_turns` NO viene en la unidad de `--max-turns`, y este
                # campo lo sobrescribia con ella. Resultado: el humano recibia
                # «Turnos: 30/15», un numerador que dobla a su denominador.
                #
                # MEDIDO (auditoria 39 §3.2, resuelto el 2026-08-19 con una
                # invocacion deliberada):
                #   claude -p ... --max-turns 1  ->  subtype=error_max_turns
                #                                    num_turns=2
                # El flag SI corta —ahi esta el `error_max_turns`— pero el
                # contador que devuelve va en otra unidad, ~2x. En el log de la
                # Legion eso explica las dos lecturas cerradas con `turnos=30` y
                # `turnos=32` contra un tope de 15 SIN un solo `error_max_turns`
                # en 46 invocaciones: nunca se corto, y lo que se imprimia no
                # era comparable con el tope.
                #
                # Se guardan por separado: `turns` (el contador de eventos, que
                # SI comparte unidad con el flag) manda en todo lo que se
                # compara con `max_turns`; `turns_cli` queda para el registro.
                self.turns_cli = event.get("num_turns") or 0
                self.cost = event.get("total_cost_usd") or self.cost
                self.denials = len(event.get("permission_denials") or [])
        except Exception:
            pass

    # ── Alertas proactivas (P6) — independientes del panel ────────────────
    def pending_alerts(self) -> list:
        """Alertas que tocan AHORA. Máximo una de cada tipo por invocación."""
        out = []
        if self.finished:
            return out

        if ("turnos" not in self._alerts_sent and self.max_turns
                and self.turns >= self.max_turns * TURN_ALERT_RATIO):
            self._alerts_sent.add("turnos")
            out.append(f"⚠️ {fraccion_turnos(self.turns, self.max_turns)} turnos consumidos: "
                       f"la tarea puede cortarse pronto."
                       + (" Si se corta, escribe «continúa»." if self.write_mode else ""))

        # Techo de tiempo. Misma forma que el aviso de turnos y por la misma
        # razón: morir sin previo aviso convierte un límite en una sorpresa.
        # El caso que lo motivó (sprint 16): una lectura murió a los 600 s en la
        # SER8 sin que hubiera salido un solo mensaje al chat.
        transcurrido = time.time() - self.started
        if ("techo" not in self._alerts_sent and self.timeout
                and transcurrido >= self.timeout * TIMEOUT_ALERT_RATIO):
            self._alerts_sent.add("techo")
            quedan = max(1, int((self.timeout - transcurrido) / 60))
            aviso = (f"⏳ {self._elapsed()} de un techo de {self.timeout // 60} min: "
                     f"si no termina en ~{quedan} min se cancela.")
            if self.last_action():
                aviso += f"\nAhora mismo: {self.last_action()}"
            out.append(aviso)

        silencio = time.time() - self.last_event
        if "silencio" not in self._alerts_sent and silencio >= SILENCE_ALERT:
            self._alerts_sent.add("silencio")
            out.append(f"⚠️ {int(silencio / 60)} min sin actividad del agente "
                       f"(sigue corriendo; puede estar en un paso largo).")
        return out

    # ── Vistas ────────────────────────────────────────────────────────────
    def _elapsed(self) -> str:
        mins = int((time.time() - self.started) / 60)
        secs = int(time.time() - self.started) % 60
        return f"{mins} min" if mins else f"{secs}s"

    def _header(self) -> str:
        partes = [p for p in (self.branch or "", self._elapsed(), self.model) if p]
        turnos = f"turno {self.turns}/{self.max_turns}" if self.max_turns else ""
        if turnos:
            partes.append(turnos)
        return "🔨 " + " · ".join(partes)

    def last_action(self) -> str:
        """Última acción observada, o cadena vacía. El tracker SIEMPRE la tiene:
        se alimenta del stream, no del worktree — que en lectura no existe."""
        return self.actions[-1] if self.actions else ""

    def checkpoint_text(self) -> str:
        """Sigo vivo, y esto es lo último que hice.

        En escritura la etapa la elige el agente (`.tg/progress.md`); en lectura
        NO HAY worktree donde escribirla, así que cae a la última acción del
        stream. Antes del sprint 16 el checkpoint ni siquiera se disparaba sin
        worktree y el modo lectura no mandaba nada hasta el timeout.
        """
        mins = int((time.time() - self.started) / 60)
        etapa = self.milestone or self.last_action() or "(aún sin acciones)"
        return f"⏱ {mins} min trabajando · último: {_short(etapa, 60)}"

    def death_text(self) -> str:
        """En qué estaba cuando la mataron. La diferencia entre un error y un
        diagnóstico: «superó N minutos» no dice qué se perdió."""
        partes = [f"iba por el turno {fraccion_turnos(self.turns, self.max_turns)}"]
        if self.milestone:
            partes.append(f"etapa «{_short(self.milestone, 60)}»")
        if self.last_action():
            partes.append(f"última acción: {self.last_action()}")
        return "Se perdió lo que llevaba: " + " · ".join(partes) + "."

    def panel_text(self) -> str:
        lines = [self._header()]
        if self.milestone:
            lines.append(f"🏁 {_short(self.milestone, 60)}")
        for i, act in enumerate(self.actions):
            ultimo = (i == len(self.actions) - 1)
            lines.append(f"{'⏳' if ultimo else '✔'} {act}")
        if not self.actions:
            lines.append("⏳ Arrancando…")
        return "\n".join(lines)

    def final_text(self) -> str:
        icono = {"success": "✅", "error_max_turns": "⏹"}.get(self.subtype, "❌")
        estado = {"success": "terminado",
                  "error_max_turns": "detenido por límite de turnos"}.get(
                      self.subtype, "terminado con error")
        lines = [f"{icono} {self.branch or 'tarea'} · {estado} en {self._elapsed()}"]
        detalle = [f"Turnos: {fraccion_turnos(self.turns, self.max_turns)}"]
        if self.turns_cli and self.turns_cli != self.turns:
            detalle[0] += f" · el CLI cuenta {self.turns_cli}"
        if self.cost:
            detalle.append(f"Costo: {self.cost:.2f} USD")
        lines.append(" · ".join(detalle))
        if self.denials:
            lines.append(f"🔒 {self.denials} acción(es) bloqueada(s)")
        if self.actions:
            lines.append(f"Última acción: {self.actions[-1]}")
        return "\n".join(lines)

    def snapshot_text(self, ended_ago: float = 0) -> str:
        """Respuesta a /progress puntual."""
        if self.finished:
            cola = (f"\n(terminó hace {int(ended_ago / 60)} min)" if ended_ago >= 60
                    else "\n(recién terminada)")
            return self.final_text() + cola
        return self.panel_text()

    # ── Throttle del panel ────────────────────────────────────────────────
    def should_edit(self) -> bool:
        """True si toca reescribir el panel: pasó el throttle y cambió algo."""
        text = self.panel_text()
        if text == self._last_text:
            return False
        if time.time() - self._last_edit < EDIT_THROTTLE:
            return False
        self._last_edit = time.time()
        self._last_text = text
        return True
