#!/usr/bin/env python3
"""
progress.py — Seguimiento en vivo de una invocación (RFD 04).

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
SILENCE_ALERT = 300       # 5 min sin eventos del stream

# Verbo legible por herramienta; lo que no esté aquí sale con su nombre crudo.
VERBS = {"Read": "Leído", "Write": "Escrito", "Edit": "Editado",
         "MultiEdit": "Editado", "Grep": "Buscado", "Glob": "Listado",
         "Bash": "Ejecutado", "WebFetch": "Descargado", "Task": "Subagente",
         "TodoWrite": "Plan actualizado", "NotebookEdit": "Notebook"}


def _short(value: str, n: int = 46) -> str:
    value = " ".join(str(value or "").split())
    return value if len(value) <= n else value[: n - 1] + "…"


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
                 write_mode: bool = False):
        self.branch = branch
        self.model = model or "default"
        self.max_turns = max_turns          # límite REAL del modo, no hardcodeado
        self.write_mode = write_mode
        self.started = time.time()
        self.last_event = time.time()
        self.actions = deque(maxlen=MAX_ACTIONS)
        self.turns = 0
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
                self.turns = event.get("num_turns") or self.turns
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
            out.append(f"⚠️ {self.turns}/{self.max_turns} turnos consumidos: "
                       f"la tarea puede cortarse pronto."
                       + (" Si se corta, escribe «continúa»." if self.write_mode else ""))

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
        detalle = [f"Turnos: {self.turns}" + (f"/{self.max_turns}" if self.max_turns else "")]
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
