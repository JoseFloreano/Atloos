#!/usr/bin/env python3
"""
tg_daemon.py — Fase T1 del puente Telegram: CHAT desde el móvil, SOLO LECTURA.

Long polling (`getUpdates`): cero URL pública, cero túnel, funciona detrás de
NAT (diseño §0 y decisión 3 del ADR). Cada mensaje invoca al CLI headless
`claude -p ... --output-format json` desde el cwd del proyecto activo, así que
la sesión hereda el CLAUDE.md y las Memory Rules de ESE proyecto (decisión 4).

Alcance T1 (duro): leer y conversar. NADA de escritura, triage, /model ni
botones inline — eso es T2.

Seguridad (diseño §2.4):
  1. Allowlist de user_id ANTES de procesar nada, con descarte SILENCIOSO
     (no confirmamos ni que el bot existe).
  2. Solo lectura de verdad: --allowedTools Read,Grep,Glob + --permission-mode
     dontAsk. JAMÁS --dangerously-skip-permissions.
  3. Una invocación en vuelo por chat (dos resumes concurrentes entrelazan el
     transcript).
  4. El token nunca se loggea; los logs guardan eventos, no contenidos.

Arranque:  py tg_daemon.py       (Ctrl+C para parar)
Config:    .env (credenciales) + projects.json (nombre → ruta del repo)
"""
import asyncio
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from telegram import Update
    from telegram.ext import (Application, ApplicationBuilder, CommandHandler,
                              ContextTypes, MessageHandler, filters)
except ImportError:
    sys.exit("Falta python-telegram-bot. Instala:  py -m pip install \"python-telegram-bot>=21\"")

# Reutilizamos la política de entrega de T0 (troceo >4096 + sendDocument):
# una sola implementación para el CLI y para el daemon.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from notify_telegram import deliver_text, load_env_file, _env_candidates  # noqa: E402

BASE = Path(__file__).resolve().parent
PROJECTS_FILE = BASE / "projects.json"
STATE_FILE = BASE / "state.json"
LOG_DIR = BASE / "logs"

SESSION_TTL_H = 24        # R3 del doc 16: la continuidad durable la da el vault
CLAUDE_TIMEOUT = 600      # 10 min: mata el proceso y avisa
MAX_TURNS = "15"          # cap de turnos por mensaje (R del doc 16)
READ_ONLY_TOOLS = "Read,Grep,Glob"

INFLIGHT: dict = {}       # chat_id -> timestamp de inicio (un vuelo por chat)

# Modelos ofrecidos por /model. Lista BLANCA a propósito: lo que llega de
# Telegram nunca se pasa tal cual como argumento al CLI.
MODELS = {
    "opus":   "el más capaz; caro (~0.1-1.9 USD por consulta observado)",
    "sonnet": "equilibrio capacidad/costo",
    "haiku":  "el más barato y rápido; ideal para consultas simples",
    "fable":  "rápido, orientado a escritura",
}
DEFAULT_MODEL = ""        # vacío = el que tenga configurado Claude Code

log = logging.getLogger("tg_daemon")


# ── Configuración ─────────────────────────────────────────────────────────
def load_config() -> dict:
    """Credenciales del .env/entorno. El token nunca se imprime."""
    file_env = {}
    for candidate in _env_candidates():
        if candidate.is_file():
            file_env = load_env_file(candidate)
            break

    def val(key):
        return os.environ.get(key) or file_env.get(key)

    cfg = {"token": val("TELEGRAM_BOT_TOKEN"),
           "allowed_user_id": val("TELEGRAM_ALLOWED_USER_ID") or val("TELEGRAM_CHAT_ID")}
    if not cfg["token"]:
        sys.exit("Falta TELEGRAM_BOT_TOKEN (entorno o .env). Ver README.")
    if not cfg["allowed_user_id"]:
        sys.exit("Falta TELEGRAM_ALLOWED_USER_ID en el .env — sin allowlist NO se arranca "
                 "(cualquiera puede escribirle a un bot de Telegram).")
    try:
        cfg["allowed_user_id"] = int(str(cfg["allowed_user_id"]).strip())
    except ValueError:
        sys.exit("TELEGRAM_ALLOWED_USER_ID debe ser numérico.")
    return cfg


def load_projects() -> dict:
    """nombre → ruta absoluta del repo. Rutas de ESTA máquina: no se versiona."""
    if not PROJECTS_FILE.is_file():
        sys.exit(f"Falta {PROJECTS_FILE.name}. Copia projects.example.json y edítalo.")
    try:
        data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"{PROJECTS_FILE.name} no es JSON válido: {exc}")
    valid = {}
    for name, path in data.items():
        if Path(path).is_dir():
            valid[name] = path
        else:
            log.warning("Proyecto '%s' ignorado: la ruta no existe (%s)", name, path)
    if not valid:
        sys.exit("Ningún proyecto de projects.json apunta a una carpeta existente.")
    return valid


# ── Estado persistente ────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("state.json corrupto; se arranca de cero")
    return {"chats": {}}


def save_state(state: dict) -> None:
    """Escritura atómica: un corte a mitad no deja el estado ilegible (prueba 9)."""
    try:
        tmp = STATE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(STATE_FILE)
    except OSError as exc:
        log.error("No se pudo guardar el estado: %s", exc)


def chat_state(state: dict, chat_id: int) -> dict:
    cs = state["chats"].setdefault(str(chat_id), {"active_project": None, "projects": {}})
    cs.setdefault("model", DEFAULT_MODEL)   # compat: estados creados antes de /model
    return cs


def project_state(state: dict, chat_id: int, project: str) -> dict:
    cs = chat_state(state, chat_id)
    return cs["projects"].setdefault(project, {"current": None, "last_activity": 0,
                                               "history": []})


# ── Utilidades ────────────────────────────────────────────────────────────
def now_ts() -> float:
    return time.time()


def human_age(ts: float) -> str:
    if not ts:
        return "nunca"
    mins = (now_ts() - ts) / 60
    if mins < 60:
        return f"hace {int(mins)} min"
    if mins < 60 * 48:
        return f"hace {int(mins / 60)} h"
    return f"hace {int(mins / 1440)} días"


async def reply(cfg: dict, chat_id: int, text: str) -> None:
    """Respuesta con la política de T0 (>4096 → resumen + adjunto .md)."""
    try:
        desc = await asyncio.to_thread(deliver_text, cfg["token"], str(chat_id),
                                       text, "claude-tg")
        log.info("respuesta enviada (%s)", desc)
    except SystemExit as exc:          # deliver_text usa die() → SystemExit
        log.error("fallo al responder al chat %s: %s", chat_id, exc)


def guard(update: Update, cfg: dict) -> bool:
    """ALLOWLIST — lo primero de todo. Silencio absoluto ante desconocidos:
    responder confirmaría que el bot existe y está activo."""
    user = update.effective_user
    uid = user.id if user else None
    if uid != cfg["allowed_user_id"]:
        log.warning("DESCARTADO update de user_id=%s (no está en la allowlist)", uid)
        return False
    return True


def projects_list_text(projects: dict) -> str:
    lines = [f"  • {name}" for name in sorted(projects)]
    return "Proyectos disponibles:\n" + "\n".join(lines) + "\n\nActiva uno con /p <nombre>"


# ── Comandos ──────────────────────────────────────────────────────────────
async def cmd_start(update, context):
    cfg = context.bot_data["cfg"]
    if not guard(update, cfg):
        return
    await reply(cfg, update.effective_chat.id,
                "Puente Telegram ↔ Claude Code (T1, solo lectura).\n\n"
                "/p <proyecto>  activar proyecto\n"
                "/new           empezar conversación nueva\n"
                "/chats         listar conversaciones del proyecto\n"
                "/chat <n>      retomar una conversación\n"
                "/model [m]     ver o cambiar el modelo\n"
                "/status        estado actual\n\n"
                "Luego escribe normal y te respondo leyendo ese repo.\n"
                "Escritura y comandos avanzados: fase T2.")


async def cmd_p(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    args = context.args or []

    if not args:
        await reply(cfg, chat_id, projects_list_text(projects))
        return
    name = args[0].strip()
    if name not in projects:
        await reply(cfg, chat_id, f"No existe el proyecto '{name}'.\n\n"
                                  f"{projects_list_text(projects)}")
        return

    chat_state(state, chat_id)["active_project"] = name
    save_state(state)
    ps = project_state(state, chat_id, name)
    extra = ("conversación en curso" if ps["current"] else "sin conversación previa")
    log.info("chat %s activó proyecto '%s'", chat_id, name)
    await reply(cfg, chat_id, f"✅ Proyecto activo: {name}\n({extra}; /new para empezar limpio)")


async def cmd_new(update, context):
    cfg, state = context.bot_data["cfg"], context.bot_data["state"]
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    project = chat_state(state, chat_id)["active_project"]
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo. Usa /p <proyecto>.")
        return
    ps = project_state(state, chat_id, project)
    ps["current"] = None
    save_state(state)
    await reply(cfg, chat_id, f"🆕 Conversación nueva en {project}. "
                              f"La anterior sigue en /chats.")


async def cmd_chats(update, context):
    cfg, state = context.bot_data["cfg"], context.bot_data["state"]
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    project = chat_state(state, chat_id)["active_project"]
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo. Usa /p <proyecto>.")
        return
    hist = project_state(state, chat_id, project)["history"]
    if not hist:
        await reply(cfg, chat_id, f"Sin conversaciones guardadas en {project}.")
        return
    current = project_state(state, chat_id, project)["current"]
    lines = []
    for i, h in enumerate(hist, 1):
        mark = " ← activa" if h["session_id"] == current else ""
        lines.append(f"{i}. {h['started'][:16]} — {h['label']}{mark}")
    await reply(cfg, chat_id, f"Conversaciones de {project}:\n" + "\n".join(lines) +
                              "\n\nRetomar: /chat <n>")


async def cmd_chat(update, context):
    cfg, state = context.bot_data["cfg"], context.bot_data["state"]
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    project = chat_state(state, chat_id)["active_project"]
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo. Usa /p <proyecto>.")
        return
    hist = project_state(state, chat_id, project)["history"]
    args = context.args or []
    if not args or not args[0].isdigit() or not (1 <= int(args[0]) <= len(hist)):
        await reply(cfg, chat_id, f"Uso: /chat <n>, con n entre 1 y {len(hist)}. "
                                  f"Mira la lista con /chats.")
        return
    chosen = hist[int(args[0]) - 1]
    ps = project_state(state, chat_id, project)
    ps["current"] = chosen["session_id"]
    ps["last_activity"] = now_ts()      # retomada explícita: no la mates por TTL
    save_state(state)
    await reply(cfg, chat_id, f"↩️ Retomada: {chosen['label']}\n"
                              f"(iniciada {chosen['started'][:16]})")


async def cmd_model(update, context):
    """Ver o cambiar el modelo. Aplica a las invocaciones siguientes de ESTE chat."""
    cfg, state = context.bot_data["cfg"], context.bot_data["state"]
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    cs = chat_state(state, chat_id)
    args = context.args or []

    if not args:
        actual = cs["model"] or "(el de Claude Code por defecto)"
        opciones = "\n".join(f"  • {k} — {v}" for k, v in MODELS.items())
        await reply(cfg, chat_id,
                    f"Modelo actual: {actual}\n\nDisponibles:\n{opciones}\n\n"
                    f"Cambiar: /model <nombre>   ·   /model default para volver al de Code")
        return

    elegido = args[0].strip().lower()
    if elegido in ("default", "reset", "auto"):
        cs["model"] = DEFAULT_MODEL
        save_state(state)
        await reply(cfg, chat_id, "✅ Modelo: el que tenga configurado Claude Code.")
        return
    if elegido not in MODELS:
        await reply(cfg, chat_id, f"'{elegido}' no está en la lista.\n\n"
                                  f"Opciones: {', '.join(MODELS)} (o 'default').")
        return

    cs["model"] = elegido
    save_state(state)
    log.info("chat %s cambió el modelo a '%s'", chat_id, elegido)
    await reply(cfg, chat_id, f"✅ Modelo: {elegido} — {MODELS[elegido]}\n"
                              f"Aplica desde el próximo mensaje (la conversación sigue igual).\n"
                              f"⚠️ Cambiar de modelo a media conversación conserva el contexto "
                              f"pero invalida el prompt cache: el próximo mensaje re-lee todo "
                              f"a precio de cache-miss (R2 del doc 16).")


async def cmd_status(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    project = chat_state(state, chat_id)["active_project"]
    lines = [f"Proyecto activo: {project or '— ninguno —'}"]
    if project:
        ps = project_state(state, chat_id, project)
        lines.append(f"Ruta: {projects.get(project, '?')}")
        lines.append(f"Conversación: {'sí' if ps['current'] else 'ninguna (se creará al escribir)'}")
        lines.append(f"Última actividad: {human_age(ps['last_activity'])}")
        lines.append(f"Guardadas: {len(ps['history'])}")
    started = INFLIGHT.get(chat_id)
    lines.append(f"En vuelo: {'sí, ' + str(int(now_ts() - started)) + 's' if started else 'no'}")
    lines.append(f"Modelo: {chat_state(state, chat_id)['model'] or '(por defecto de Claude Code)'}")
    lines.append(f"Modo: solo lectura ({READ_ONLY_TOOLS}), máx {MAX_TURNS} turnos")
    await reply(cfg, chat_id, "\n".join(lines))


# ── Invocación de Claude Code ─────────────────────────────────────────────
async def run_claude(prompt: str, cwd: str, session_id, model: str = "") -> dict:
    """`claude -p` headless en el cwd del proyecto. Devuelve el JSON parseado.

    Solo lectura: --allowedTools acotado + --permission-mode dontAsk (deniega
    en vez de preguntar; en headless una pregunta colgaría el proceso).
    """
    exe = shutil.which("claude") or "claude"
    cmd = [exe, "-p", prompt, "--output-format", "json",
           "--allowedTools", READ_ONLY_TOOLS,
           "--permission-mode", "dontAsk",
           "--max-turns", MAX_TURNS]
    if session_id:
        cmd += ["--resume", session_id]
    if model in MODELS:          # lista blanca: nunca un valor arbitrario del chat
        cmd += ["--model", model]

    env = {**os.environ, "CLAUDE_TG_BOT": "1"}   # el hook anti-drift lo respeta
    log.info("invocando claude (cwd=%s, resume=%s, modelo=%s, prompt=%d chars)",
             Path(cwd).name, bool(session_id), model or "default", len(prompt))

    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd, env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=CLAUDE_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"La consulta superó {CLAUDE_TIMEOUT // 60} minutos y se canceló.")

    if proc.returncode != 0:
        err = (stderr or b"").decode("utf-8", "replace").strip()[:400]
        raise RuntimeError(f"claude terminó con código {proc.returncode}: {err or 'sin detalle'}")
    try:
        return json.loads((stdout or b"").decode("utf-8", "replace"))
    except json.JSONDecodeError:
        raise RuntimeError("La respuesta de claude no es JSON válido.")


# ── Mensajes normales ─────────────────────────────────────────────────────
async def on_message(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return

    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    if not text:
        return

    project = chat_state(state, chat_id)["active_project"]
    if not project:
        await reply(cfg, chat_id, "⚠️ No hay proyecto activo.\n\n" + projects_list_text(projects))
        return
    if project not in projects:
        await reply(cfg, chat_id, f"El proyecto '{project}' ya no está en projects.json.\n\n"
                                  + projects_list_text(projects))
        return

    # Un vuelo por chat: dos --resume concurrentes entrelazan el transcript
    if chat_id in INFLIGHT:
        await reply(cfg, chat_id, f"⏳ Trabajando en lo anterior "
                                  f"({int(now_ts() - INFLIGHT[chat_id])}s). Espera a que termine.")
        return

    ps = project_state(state, chat_id, project)
    session_id = ps["current"]

    # TTL (R3): un --resume eterno arrastra contexto que se paga en cada turno
    aged = session_id and (now_ts() - ps["last_activity"]) > SESSION_TTL_H * 3600
    if aged:
        log.info("TTL: sesión de '%s' caducada (%s)", project, human_age(ps["last_activity"]))
        session_id = None

    INFLIGHT[chat_id] = now_ts()
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        if aged:
            await reply(cfg, chat_id, f"🕓 Sesión nueva por inactividad (>{SESSION_TTL_H}h). "
                                      f"/chats para retomar la anterior.")
        try:
            data = await run_claude(text, projects[project], session_id,
                                    chat_state(state, chat_id)["model"])
        except RuntimeError as exc:
            log.error("invocación fallida: %s", exc)
            await reply(cfg, chat_id, f"❌ {exc}")
            return

        new_session = data.get("session_id")
        answer = (data.get("result") or "").strip() or "(respuesta vacía)"
        denials = data.get("permission_denials") or []
        if data.get("is_error"):
            answer = f"⚠️ Claude reportó error:\n{answer}"
        if denials:
            # Esperado en T1: la prueba de que el modo lectura muerde
            log.info("permission_denials: %d (esperado en solo-lectura)", len(denials))
            answer += (f"\n\n🔒 {len(denials)} acción(es) bloqueada(s) por el modo solo lectura "
                       f"(la escritura llega en T2).")

        # Persistir sesión e historial
        if new_session:
            if new_session != ps["current"]:
                ps["history"].append({
                    "session_id": new_session,
                    "started": datetime.now(timezone.utc).astimezone().isoformat(),
                    "label": (text[:40] + "…") if len(text) > 40 else text,
                })
                ps["history"] = ps["history"][-20:]      # no crecer sin fin
            ps["current"] = new_session
        ps["last_activity"] = now_ts()
        save_state(state)

        log.info("respuesta ok (turnos=%s, costo=%.4f USD)",
                 data.get("num_turns"), data.get("total_cost_usd") or 0)
        await reply(cfg, chat_id, answer)
    finally:
        INFLIGHT.pop(chat_id, None)


async def on_error(update, context):
    log.error("error no controlado: %s", context.error)


# ── Arranque ──────────────────────────────────────────────────────────────
def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    handler = logging.FileHandler(LOG_DIR / f"daemon-{datetime.now():%Y%m}.log",
                                  encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler, console])
    logging.getLogger("httpx").setLevel(logging.WARNING)   # no loggear cada request


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    setup_logging()

    cfg = load_config()
    projects = load_projects()
    state = load_state()

    # concurrent_updates: sin esto PTB procesa los updates EN SERIE, así que un
    # mensaje enviado mientras Claude trabaja se encola y solo se atiende cuando
    # el anterior terminó — para entonces INFLIGHT ya está vacío y en vez del
    # aviso "⏳" se lanzaría una segunda consulta. El lock por chat vive en
    # INFLIGHT (la comprobación y el alta no tienen await entre medias, así que
    # sigue siendo atómica en asyncio).
    app: Application = (ApplicationBuilder()
                        .token(cfg["token"])
                        .concurrent_updates(True)
                        .build())
    app.bot_data.update({"cfg": cfg, "projects": projects, "state": state})

    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("p", cmd_p))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("chats", cmd_chats))
    app.add_handler(CommandHandler("chat", cmd_chat))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_error_handler(on_error)

    log.info("daemon arrancado | proyectos: %s | allowlist: 1 usuario | modo: solo lectura",
             ", ".join(sorted(projects)))
    print("Daemon en marcha (long polling). Ctrl+C para parar.")
    app.run_polling(timeout=40, drop_pending_updates=True,
                    allowed_updates=["message"])


if __name__ == "__main__":
    main()
