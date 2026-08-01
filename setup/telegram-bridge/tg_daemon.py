#!/usr/bin/env python3
"""
tg_daemon.py — Puente Telegram ↔ Claude Code. Fases T1 (chat) y T2 (escritura).

Long polling saliente: sin URL pública, sin túnel, detrás de NAT. Cada mensaje
invoca `claude -p --output-format json` desde el cwd correspondiente, así que la
sesión hereda el CLAUDE.md y las Memory Rules de ESE proyecto.

T2 — modo escritura (RFD 02 v2):
  · **1 conversación = 1 rama = 1 worktree.** El bot NUNCA escribe en el árbol
    de trabajo del usuario; trabaja en `%LOCALAPPDATA%\\claude-tg-worktrees\\…`
    sobre una rama `tg/<fecha>-<slug>` creada al primer `/write on`.
  · **Los git ops los ejecuta el daemon, jamás el agente**: no existe camino
    por el que una inyección de prompt commitee, publique o mergee.
  · **Botón solo para `/merge`** (lo único que toca `main`), y solo si `/test`
    pasó después del último commit.
  · **Checkpoints cada 30 min** leyendo `.tg/progress.md` del worktree; timeout
    de 90 min en escritura (10 en lectura).

Seguridad (diseño §2.4): allowlist de user_id con descarte silencioso ANTES de
procesar nada · lista blanca de herramientas (`--permission-mode dontAsk`) ·
JAMÁS `--dangerously-skip-permissions` · un vuelo por chat · sin tokens ni
contenidos en los logs.

Arranque:  py tg_daemon.py       (Ctrl+C para parar)
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
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import (Application, ApplicationBuilder, CallbackQueryHandler,
                              CommandHandler, ContextTypes, MessageHandler, filters)
except ImportError:
    sys.exit("Falta python-telegram-bot. Instala:  py -m pip install \"python-telegram-bot>=21\"")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gitops                                              # noqa: E402
from notify_telegram import deliver_text, load_env_file, _env_candidates  # noqa: E402

BASE = Path(__file__).resolve().parent
PROJECTS_FILE = BASE / "projects.json"
STATE_FILE = BASE / "state.json"
LOG_DIR = BASE / "logs"

SESSION_TTL_H = 24          # R3 doc 16: la continuidad durable la da el vault
READ_TIMEOUT = 600          # 10 min basta para una consulta
WRITE_TIMEOUT = 5400        # 90 min: un desarrollo real no cabe en 10 (RFD C9)
CHECKPOINT_EVERY = 1800     # 30 min (RFD C2)
MERGE_TOKEN_TTL = 300       # 5 min de vida del botón de merge (RFD C4)
MAX_TURNS = "15"

READ_TOOLS = "Read,Grep,Glob"
# Lista blanca de escritura (RFD C3). Es blanca: lo que no está, no corre.
WRITE_TOOLS = (
    "Read,Grep,Glob,Edit,Write,"
    "Bash(npm test:*),Bash(npm run test:*),Bash(npm run lint:*),Bash(npm run build:*),"
    "Bash(pytest:*),Bash(py -m pytest:*),Bash(python -m pytest:*),Bash(ruff:*),"
    "Bash(eslint:*),Bash(flutter test:*),Bash(flutter analyze:*),"
    "Bash(git status:*),Bash(git diff:*),Bash(git log:*),Bash(git add:*)"
)
# Segunda barrera explícita: publicar/integrar nunca pasa por el agente.
DENY_TOOLS = ("WebFetch,Bash(git commit:*),Bash(git push:*),Bash(git merge:*),"
              "Bash(git reset:*),Bash(git checkout:*),Bash(rm:*),Bash(curl:*),Bash(wget:*)")

WRITE_PREAMBLE = (
    "[Puente Telegram — modo escritura. Trabajas en un worktree aislado sobre la "
    "rama {branch}; el árbol del usuario no se toca. Ve anotando el avance en "
    "`.tg/progress.md`: UNA línea por etapa completada (append, no reescribas el "
    "archivo) — es lo único que el usuario ve desde el móvil mientras trabajas. "
    "NO hagas commit, push ni merge: de eso se encarga el daemon con confirmación "
    "del usuario.]\n\n"
)

MODELS = {
    "opus":   "el más capaz; caro (~0.1-1.9 USD por consulta observado)",
    "sonnet": "equilibrio capacidad/costo",
    "haiku":  "el más barato y rápido; ideal para consultas simples",
    "fable":  "rápido, orientado a escritura",
}
DEFAULT_MODEL = ""

INFLIGHT: dict = {}         # chat_id -> ts de inicio (un vuelo por chat)
PENDING_MERGE: dict = {}    # token -> {chat_id, project, idx, expires}

log = logging.getLogger("tg_daemon")


# ── Configuración ─────────────────────────────────────────────────────────
def load_config() -> dict:
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
        sys.exit("Falta TELEGRAM_ALLOWED_USER_ID en el .env — sin allowlist NO se arranca.")
    try:
        cfg["allowed_user_id"] = int(str(cfg["allowed_user_id"]).strip())
    except ValueError:
        sys.exit("TELEGRAM_ALLOWED_USER_ID debe ser numérico.")
    return cfg


def load_projects() -> dict:
    """nombre → {path, test}. Acepta el formato de T1 (`"nombre": "ruta"`)."""
    if not PROJECTS_FILE.is_file():
        sys.exit(f"Falta {PROJECTS_FILE.name}. Copia projects.example.json y edítalo.")
    try:
        raw = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"{PROJECTS_FILE.name} no es JSON válido: {exc}")

    valid = {}
    for name, entry in raw.items():
        if name.startswith("_"):
            continue
        cfg = {"path": entry, "test": ""} if isinstance(entry, str) else {
            "path": entry.get("path", ""), "test": entry.get("test", "")}
        if cfg["path"] and Path(cfg["path"]).is_dir():
            valid[name] = cfg
        else:
            log.warning("Proyecto '%s' ignorado: la ruta no existe (%s)", name, cfg["path"])
    if not valid:
        sys.exit("Ningún proyecto de projects.json apunta a una carpeta existente.")
    return valid


# ── Estado persistente ────────────────────────────────────────────────────
def _blank_conv() -> dict:
    return {"session_id": None, "started": datetime.now(timezone.utc).astimezone().isoformat(),
            "label": "", "branch": None, "worktree": None, "write": False,
            "test_ok_sha": None, "pr_url": "", "archived": False, "last_activity": 0}


def migrate_state(state: dict) -> dict:
    """Estado de T1 (history + current=session_id) → conversaciones de T2."""
    for cs in state.get("chats", {}).values():
        cs.setdefault("model", DEFAULT_MODEL)
        for ps in cs.get("projects", {}).values():
            if "conversations" in ps:
                continue
            convs, current_idx = [], None
            for i, h in enumerate(ps.get("history", [])):
                conv = _blank_conv()
                conv.update({"session_id": h.get("session_id"),
                             "started": h.get("started", conv["started"]),
                             "label": h.get("label", ""),
                             "last_activity": ps.get("last_activity", 0)})
                convs.append(conv)
                if h.get("session_id") and h["session_id"] == ps.get("current"):
                    current_idx = i
            ps["conversations"] = convs
            ps["current"] = current_idx
            ps.pop("history", None)
    return state


def load_state() -> dict:
    if STATE_FILE.is_file():
        try:
            return migrate_state(json.loads(STATE_FILE.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            log.warning("state.json corrupto; se arranca de cero")
    return {"chats": {}}


def save_state(state: dict) -> None:
    """Escritura atómica: un corte a mitad no deja el estado ilegible."""
    try:
        tmp = STATE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(STATE_FILE)
    except OSError as exc:
        log.error("No se pudo guardar el estado: %s", exc)


def chat_state(state: dict, chat_id: int) -> dict:
    cs = state["chats"].setdefault(str(chat_id), {"active_project": None, "projects": {}})
    cs.setdefault("model", DEFAULT_MODEL)
    return cs


def project_state(state: dict, chat_id: int, project: str) -> dict:
    cs = chat_state(state, chat_id)
    return cs["projects"].setdefault(project, {"current": None, "conversations": []})


def live_convs(ps: dict) -> list:
    """(índice, conversación) de las no archivadas, en orden."""
    return [(i, c) for i, c in enumerate(ps["conversations"]) if not c.get("archived")]


def current_conv(ps: dict):
    idx = ps.get("current")
    if idx is None or idx >= len(ps["conversations"]):
        return None, None
    return idx, ps["conversations"][idx]


def ensure_conv(ps: dict) -> tuple:
    """Devuelve la conversación activa, creándola si aún no hay ninguna."""
    idx, conv = current_conv(ps)
    if conv is None:
        ps["conversations"].append(_blank_conv())
        idx = len(ps["conversations"]) - 1
        ps["current"] = idx
        conv = ps["conversations"][idx]
    return idx, conv


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
    """Respuesta con la política de entrega de T0 (>4096 → resumen + adjunto)."""
    try:
        desc = await asyncio.to_thread(deliver_text, cfg["token"], str(chat_id),
                                       text, "claude-tg")
        log.info("respuesta enviada (%s)", desc)
    except SystemExit as exc:
        log.error("fallo al responder al chat %s: %s", chat_id, exc)


async def reply_doc(cfg: dict, chat_id: int, filename: str, content: str) -> None:
    from notify_telegram import send_document
    try:
        await asyncio.to_thread(send_document, cfg["token"], str(chat_id),
                                filename, content.encode("utf-8"))
    except SystemExit as exc:
        log.error("fallo al enviar adjunto: %s", exc)


def guard(update: Update, cfg: dict) -> bool:
    """ALLOWLIST — lo primero. Silencio ante desconocidos: responder confirmaría
    que el bot existe."""
    user = update.effective_user
    uid = user.id if user else None
    if uid != cfg["allowed_user_id"]:
        log.warning("DESCARTADO update de user_id=%s (no está en la allowlist)", uid)
        return False
    return True


def busy(chat_id: int) -> str:
    """Mensaje de ocupado, o cadena vacía si no hay vuelo."""
    started = INFLIGHT.get(chat_id)
    if not started:
        return ""
    return (f"⏳ Trabajando en lo anterior ({int(now_ts() - started)}s). "
            f"Espera a que termine.")


def projects_list_text(projects: dict) -> str:
    return ("Proyectos disponibles:\n"
            + "\n".join(f"  • {n}" for n in sorted(projects))
            + "\n\nActiva uno con /p <nombre>")


def need_project(cfg, state, chat_id, projects):
    """(project, ps) o (None, None) tras avisar al usuario."""
    project = chat_state(state, chat_id)["active_project"]
    if not project or project not in projects:
        return None, None
    return project, project_state(state, chat_id, project)


def read_progress(worktree: str) -> str:
    """Última etapa reportada por el agente en .tg/progress.md."""
    try:
        p = Path(worktree) / gitops.PROGRESS_DIR / "progress.md"
        if not p.is_file():
            return ""
        lines = [l.strip() for l in p.read_text(encoding="utf-8", errors="replace").splitlines()
                 if l.strip()]
        return lines[-1] if lines else ""
    except OSError:
        return ""


# ── Comandos: navegación (T1) ─────────────────────────────────────────────
async def cmd_start(update, context):
    cfg = context.bot_data["cfg"]
    if not guard(update, cfg):
        return
    await reply(cfg, update.effective_chat.id,
                "Puente Telegram ↔ Claude Code.\n\n"
                "**Navegación**\n"
                "/p <proyecto> · /new · /chats · /chat <n> · /model [m] · /status\n\n"
                "**Escritura (T2)**\n"
                "/write on|off — modo auto en una rama y worktree propios\n"
                "/diff · /commit [msg] · /test · /push · /merge · /done\n\n"
                "Por defecto solo leo. En modo escritura trabajo en una rama "
                "`tg/*` aislada: tu árbol de trabajo nunca se toca.")


async def cmd_p(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):          # RFD C10: no cambiar de foco en vuelo
        await reply(cfg, chat_id, msg)
        return

    args = context.args or []
    if not args:
        await reply(cfg, chat_id, projects_list_text(projects))
        return
    name = args[0].strip()
    if name not in projects:
        await reply(cfg, chat_id, f"No existe el proyecto '{name}'.\n\n{projects_list_text(projects)}")
        return

    chat_state(state, chat_id)["active_project"] = name
    ps = project_state(state, chat_id, name)
    save_state(state)
    _, conv = current_conv(ps)
    if not conv:
        extra = "sin conversación previa"
    elif conv.get("branch"):
        extra = f"conversación en curso · rama {conv['branch']}"
    else:
        extra = "conversación en curso"
    log.info("chat %s activó proyecto '%s'", chat_id, name)
    await reply(cfg, chat_id, f"✅ Proyecto activo: {name}\n({extra}; /new para empezar limpio)")


async def cmd_new(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):
        await reply(cfg, chat_id, msg)
        return
    project, ps = need_project(cfg, state, chat_id, projects)
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo. Usa /p <proyecto>.")
        return

    ps["conversations"].append(_blank_conv())
    ps["current"] = len(ps["conversations"]) - 1
    save_state(state)
    await reply(cfg, chat_id, f"🆕 Conversación nueva en {project}.\n"
                              f"(La anterior sigue en /chats. En modo escritura tendrá "
                              f"su propia rama al hacer /write on.)")


async def cmd_chats(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    project, ps = need_project(cfg, state, chat_id, projects)
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo. Usa /p <proyecto>.")
        return
    convs = live_convs(ps)
    if not convs:
        await reply(cfg, chat_id, f"Sin conversaciones en {project}.")
        return

    cur_idx = ps.get("current")
    lines = []
    for n, (idx, c) in enumerate(convs, 1):
        mark = " ← activa" if idx == cur_idx else ""
        rama = f" · {c['branch']}" if c.get("branch") else ""
        modo = " ✍" if c.get("write") else ""
        lines.append(f"{n}. {c['started'][:16]} — {c['label'] or '(sin mensajes)'}{rama}{modo}")
    await reply(cfg, chat_id, f"Conversaciones de {project}:\n" + "\n".join(lines)
                              + "\n\nRetomar: /chat <n>   (✍ = con rama de escritura)")


async def cmd_chat(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):          # RFD C10
        await reply(cfg, chat_id, msg)
        return
    project, ps = need_project(cfg, state, chat_id, projects)
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo. Usa /p <proyecto>.")
        return

    convs = live_convs(ps)
    args = context.args or []
    if not args or not args[0].isdigit() or not (1 <= int(args[0]) <= len(convs)):
        await reply(cfg, chat_id, f"Uso: /chat <n>, con n entre 1 y {len(convs)}. Ver /chats.")
        return
    idx, conv = convs[int(args[0]) - 1]
    ps["current"] = idx
    conv["last_activity"] = now_ts()
    save_state(state)
    rama = f"\nRama: {conv['branch']}" if conv.get("branch") else ""
    await reply(cfg, chat_id, f"↩️ Retomada: {conv['label'] or '(sin mensajes)'}{rama}")


async def cmd_model(update, context):
    cfg, state = context.bot_data["cfg"], context.bot_data["state"]
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    cs = chat_state(state, chat_id)
    args = context.args or []
    if not args:
        actual = cs["model"] or "(el de Claude Code por defecto)"
        opciones = "\n".join(f"  • {k} — {v}" for k, v in MODELS.items())
        await reply(cfg, chat_id, f"Modelo actual: {actual}\n\nDisponibles:\n{opciones}\n\n"
                                  f"Cambiar: /model <nombre> · /model default")
        return
    elegido = args[0].strip().lower()
    if elegido in ("default", "reset", "auto"):
        cs["model"] = DEFAULT_MODEL
        save_state(state)
        await reply(cfg, chat_id, "✅ Modelo: el que tenga configurado Claude Code.")
        return
    if elegido not in MODELS:
        await reply(cfg, chat_id, f"'{elegido}' no está en la lista.\n\nOpciones: {', '.join(MODELS)}")
        return
    cs["model"] = elegido
    save_state(state)
    log.info("chat %s cambió el modelo a '%s'", chat_id, elegido)
    await reply(cfg, chat_id, f"✅ Modelo: {elegido} — {MODELS[elegido]}")


async def cmd_status(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    cs = chat_state(state, chat_id)
    project = cs["active_project"]
    lines = [f"Proyecto activo: {project or '— ninguno —'}"]
    if project and project in projects:
        ps = project_state(state, chat_id, project)
        _, conv = current_conv(ps)
        lines.append(f"Ruta: {projects[project]['path']}")
        if conv:
            lines.append(f"Conversación: {conv['label'] or '(nueva, sin mensajes)'}")
            lines.append(f"Modo: {'✍ ESCRITURA' if conv.get('write') else '👁 solo lectura'}")
            if conv.get("branch"):
                lines.append(f"Rama: {conv['branch']}")
                lines.append(f"Worktree: {conv['worktree']}")
                lines.append(f"Tests verdes: {'sí' if conv.get('test_ok_sha') else 'no'}")
            lines.append(f"Última actividad: {human_age(conv.get('last_activity', 0))}")
        else:
            lines.append("Conversación: ninguna (se creará al escribir)")
        lines.append(f"Guardadas: {len(live_convs(ps))}")
    started = INFLIGHT.get(chat_id)
    lines.append(f"En vuelo: {'sí, ' + str(int(now_ts() - started)) + 's' if started else 'no'}")
    lines.append(f"Modelo: {cs['model'] or '(por defecto de Claude Code)'}")
    await reply(cfg, chat_id, "\n".join(lines))


# ── Comandos: escritura (T2) ──────────────────────────────────────────────
async def cmd_write(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):
        await reply(cfg, chat_id, msg)
        return
    project, ps = need_project(cfg, state, chat_id, projects)
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo. Usa /p <proyecto>.")
        return

    args = [a.lower() for a in (context.args or [])]
    idx, conv = ensure_conv(ps)

    if not args or args[0] not in ("on", "off"):
        estado = "✍ ESCRITURA" if conv.get("write") else "👁 solo lectura"
        await reply(cfg, chat_id, f"Modo actual: {estado}\nUso: /write on · /write off")
        return

    if args[0] == "off":
        conv["write"] = False
        save_state(state)
        await reply(cfg, chat_id, "👁 Modo lectura. La rama y el worktree siguen ahí "
                                  "(/chats para volver, /done para limpiar).")
        return

    # /write on — crea rama + worktree si la conversación aún no tiene (perezoso)
    if not conv.get("worktree"):
        slug = gitops.slugify(conv.get("label") or "tarea")
        await reply(cfg, chat_id, f"Preparando rama y worktree para «{slug}»…")
        try:
            wt = await gitops.create_worktree(projects[project]["path"], project, slug)
        except gitops.GitError as exc:
            log.error("no se pudo crear el worktree: %s", exc)
            await reply(cfg, chat_id, f"❌ No pude crear el worktree: {exc}")
            return
        conv.update({"branch": wt["branch"], "worktree": wt["path"]})
        log.info("worktree creado: %s (%s)", wt["path"], wt["branch"])
        if not wt["claude_md"]:
            await reply(cfg, chat_id, "⚠️ El repo no tiene CLAUDE.md: el worktree "
                                      "arranca sin Memory Rules del proyecto.")

    conv["write"] = True
    conv["last_activity"] = now_ts()
    save_state(state)
    tests = projects[project].get("test") or "(sin comando de test configurado)"
    await reply(cfg, chat_id,
                f"✍ **Modo escritura**\n"
                f"Rama: `{conv['branch']}`\n"
                f"Worktree aislado (tu árbol de trabajo no se toca).\n\n"
                f"Puedo editar archivos y correr tests/linters. NO puedo commitear, "
                f"publicar ni mergear: eso lo haces tú con /commit, /push y /merge.\n"
                f"Tests del proyecto: `{tests}`")


async def cmd_diff(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    project, ps = need_project(cfg, state, chat_id, projects)
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo.")
        return
    _, conv = current_conv(ps)
    if not conv or not conv.get("worktree"):
        await reply(cfg, chat_id, "Esta conversación no tiene rama de trabajo. /write on")
        return

    try:
        d = await gitops.diff_summary(conv["worktree"])
        commits = await gitops.commits_ahead(conv["worktree"], conv["branch"],
                                             await gitops.default_branch(projects[project]["path"]))
    except gitops.GitError as exc:
        await reply(cfg, chat_id, f"❌ {exc}")
        return

    partes = [f"Rama: {conv['branch']}"]
    partes.append(f"Commits por delante de main: {len(commits)}")
    for c in commits[:10]:
        partes.append(f"  · {c}")
    partes.append("")
    partes.append("Sin commitear:" if d["has_changes"] else "Sin cambios pendientes.")
    if d["has_changes"]:
        partes.append(d["stat"])
    await reply(cfg, chat_id, "\n".join(partes))
    if d["has_changes"] and len(d["full"]) > 3000:
        await reply_doc(cfg, chat_id, f"diff-{conv['branch'].replace('/', '-')}.diff", d["full"])
    elif d["has_changes"]:
        await reply(cfg, chat_id, f"```\n{d['full'][:3000]}\n```")


async def cmd_test(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):
        await reply(cfg, chat_id, msg)
        return
    project, ps = need_project(cfg, state, chat_id, projects)
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo.")
        return
    _, conv = current_conv(ps)
    if not conv or not conv.get("worktree"):
        await reply(cfg, chat_id, "Esta conversación no tiene rama de trabajo. /write on")
        return
    cmd = (projects[project].get("test") or "").strip()
    if not cmd:
        await reply(cfg, chat_id, f"El proyecto '{project}' no tiene comando de test en "
                                  f"projects.json.\nSin verde no se puede /merge.")
        return

    INFLIGHT[chat_id] = now_ts()
    try:
        await reply(cfg, chat_id, f"🧪 Ejecutando: `{cmd}`")
        rc, out, err = await gitops.run(cmd.split(), conv["worktree"], timeout=1800)
        salida = (out + "\n" + err).strip()
        if rc == 0:
            conv["test_ok_sha"] = await gitops.head_sha(conv["worktree"])
            save_state(state)
            log.info("tests OK en %s (sha %s)", conv["branch"], conv["test_ok_sha"])
            await reply(cfg, chat_id, f"✅ Tests en verde.\n\n```\n{salida[-1500:]}\n```\n"
                                      f"/merge disponible.")
        else:
            conv["test_ok_sha"] = None
            save_state(state)
            await reply(cfg, chat_id, f"❌ Tests en rojo (código {rc}).\n\n```\n{salida[-2500:]}\n```")
    except gitops.GitError as exc:
        await reply(cfg, chat_id, f"❌ {exc}")
    finally:
        INFLIGHT.pop(chat_id, None)


async def cmd_commit(update, context):
    """Sin mensaje: se lo pide al agente y te lo muestra. Con mensaje: usa el tuyo."""
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):
        await reply(cfg, chat_id, msg)
        return
    project, ps = need_project(cfg, state, chat_id, projects)
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo.")
        return
    _, conv = current_conv(ps)
    if not conv or not conv.get("worktree"):
        await reply(cfg, chat_id, "Esta conversación no tiene rama de trabajo. /write on")
        return

    mensaje = " ".join(context.args or []).strip()
    if not mensaje:
        INFLIGHT[chat_id] = now_ts()
        try:
            await reply(cfg, chat_id, "Pidiendo al agente que proponga el mensaje…")
            data = await run_claude(
                "Mira `git diff --cached` y `git status` de este worktree y propón UN "
                "mensaje de commit en una línea (estilo convencional, en español). "
                "Responde SOLO con el mensaje, sin comillas ni explicación.",
                conv["worktree"], conv.get("session_id"),
                chat_state(state, chat_id)["model"], write_mode=False, timeout=READ_TIMEOUT)
            mensaje = (data.get("result") or "").strip().splitlines()[0][:200] if data.get("result") else ""
        except RuntimeError as exc:
            await reply(cfg, chat_id, f"❌ No pude generar el mensaje: {exc}")
            return
        finally:
            INFLIGHT.pop(chat_id, None)
        if not mensaje:
            await reply(cfg, chat_id, "No obtuve mensaje. Usa /commit <tu mensaje>.")
            return

    try:
        r = await gitops.commit_all(conv["worktree"], mensaje)
    except gitops.GitError as exc:
        await reply(cfg, chat_id, f"❌ {exc}")
        return
    if not r["committed"]:
        await reply(cfg, chat_id, f"ℹ️ {r['reason']}")
        return
    conv["test_ok_sha"] = None          # commit nuevo ⇒ el verde anterior caduca
    save_state(state)
    log.info("commit %s en %s", r["sha"], conv["branch"])
    await reply(cfg, chat_id, f"✅ Commit `{r['sha']}` en `{conv['branch']}`\n"
                              f"«{r['subject']}»\n\n"
                              f"main no se ha movido. Corre /test antes de /merge.")


async def cmd_push(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):
        await reply(cfg, chat_id, msg)
        return
    project, ps = need_project(cfg, state, chat_id, projects)
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo.")
        return
    _, conv = current_conv(ps)
    if not conv or not conv.get("worktree"):
        await reply(cfg, chat_id, "Esta conversación no tiene rama de trabajo. /write on")
        return

    INFLIGHT[chat_id] = now_ts()
    try:
        await reply(cfg, chat_id, f"⬆️ Publicando `{conv['branch']}`…")
        r = await gitops.push_branch(conv["worktree"], conv["branch"])
        if not r["pushed"]:
            await reply(cfg, chat_id, f"ℹ️ No publicado: {r['reason']}")
            return
        base = await gitops.default_branch(projects[project]["path"])
        pr = await gitops.ensure_pr(conv["worktree"], conv["branch"], base,
                                    conv["label"][:70] or conv["branch"])
        if pr.get("pr"):
            conv["pr_url"] = pr["url"]
            save_state(state)
            log.info("PR %s para %s", pr["url"], conv["branch"])
            await reply(cfg, chat_id, f"✅ Rama publicada.\n{'PR creado' if pr.get('created') else 'PR existente'}: "
                                      f"{pr['url']}\n\nRevisa el diff en la app de GitHub.")
        else:
            await reply(cfg, chat_id, f"✅ Rama publicada. (Sin PR: {pr.get('reason','')})")
    except gitops.GitError as exc:
        await reply(cfg, chat_id, f"❌ {exc}")
    finally:
        INFLIGHT.pop(chat_id, None)


async def cmd_merge(update, context):
    """Lo único que toca main ⇒ botón + verde de tests obligatorio."""
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):
        await reply(cfg, chat_id, msg)
        return
    project, ps = need_project(cfg, state, chat_id, projects)
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo.")
        return
    idx, conv = current_conv(ps)
    if not conv or not conv.get("worktree"):
        await reply(cfg, chat_id, "Esta conversación no tiene rama de trabajo. /write on")
        return

    try:
        head = await gitops.head_sha(conv["worktree"])
        if (await gitops.diff_summary(conv["worktree"]))["has_changes"]:
            await reply(cfg, chat_id, "Hay cambios sin commitear. Haz /commit primero.")
            return
    except gitops.GitError as exc:
        await reply(cfg, chat_id, f"❌ {exc}")
        return

    if not conv.get("test_ok_sha"):
        await reply(cfg, chat_id, "🚫 /merge bloqueado: los tests no han pasado en esta rama.\n"
                                  "Corre /test primero.")
        return
    if conv["test_ok_sha"] != head:
        await reply(cfg, chat_id, f"🚫 /merge bloqueado: hay commits posteriores al último "
                                  f"verde ({conv['test_ok_sha']} → {head}).\nVuelve a correr /test.")
        return

    token = f"{chat_id}-{int(now_ts())}"
    PENDING_MERGE[token] = {"chat_id": chat_id, "project": project, "idx": idx,
                            "expires": now_ts() + MERGE_TOKEN_TTL}
    base = await gitops.default_branch(projects[project]["path"])
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Sí, mergea", callback_data=f"m:{token}"),
        InlineKeyboardButton("✖ Cancelar", callback_data=f"x:{token}")]])
    await context.bot.send_message(
        chat_id,
        f"¿Integrar {conv['branch']} en {base}?\n\n"
        f"Modo: squash · Tests: verdes en {head}\n"
        f"{'Vía PR: ' + conv['pr_url'] if conv.get('pr_url') else 'Merge local'}\n\n"
        f"Este botón caduca en {MERGE_TOKEN_TTL // 60} minutos.",
        reply_markup=kb)


async def on_callback(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    query = update.callback_query
    if not guard(update, cfg):
        return
    await query.answer()
    action, _, token = (query.data or "").partition(":")
    pend = PENDING_MERGE.pop(token, None)

    if action == "x":
        await query.edit_message_text("Cancelado. No se ha tocado nada.")
        return
    if action != "m":
        return
    if not pend or pend["expires"] < now_ts():
        await query.edit_message_text("⌛ Confirmación caducada (>5 min). "
                                      "Vuelve a lanzar /merge si sigues queriendo.")
        return

    chat_id = pend["chat_id"]
    ps = project_state(state, chat_id, pend["project"])
    conv = ps["conversations"][pend["idx"]]
    repo = projects[pend["project"]]["path"]
    await query.edit_message_text(f"Integrando {conv['branch']}…")

    INFLIGHT[chat_id] = now_ts()
    try:
        base = await gitops.default_branch(repo)
        r = await gitops.merge_squash(repo, conv["branch"], base,
                                      conv["label"][:70] or f"merge {conv['branch']}",
                                      conv.get("pr_url", ""))
        if r["merged"]:
            conv["merged"] = True       # /done necesita saberlo: el squash no deja rastro
            save_state(state)
            log.info("merge %s -> %s (%s)", conv["branch"], base, r.get("via"))
            await reply(cfg, chat_id, f"✅ Integrado en `{base}` ({r.get('via')}).\n"
                                      f"{r.get('sha','')}\n\nUsa /done para limpiar la rama y el worktree.")
        else:
            await reply(cfg, chat_id, f"❌ No se integró: {r['reason']}")
    except gitops.GitError as exc:
        await reply(cfg, chat_id, f"❌ {exc}")
    finally:
        INFLIGHT.pop(chat_id, None)


async def cmd_done(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):
        await reply(cfg, chat_id, msg)
        return
    project, ps = need_project(cfg, state, chat_id, projects)
    if not project:
        await reply(cfg, chat_id, "No hay proyecto activo.")
        return
    idx, conv = current_conv(ps)
    if not conv:
        await reply(cfg, chat_id, "No hay conversación activa.")
        return

    notas = []
    if conv.get("worktree"):
        try:
            r = await gitops.remove_worktree(projects[project]["path"], conv["worktree"],
                                             conv["branch"], merged=bool(conv.get("merged")))
            log.info("done: %s -> %s", conv["branch"], r)
        except gitops.GitError as exc:
            await reply(cfg, chat_id, f"❌ {exc}")
            return
        if not r["worktree_removed"]:
            # No archivamos: hay trabajo real sin commitear y perderlo sería peor
            await reply(cfg, chat_id, "🚫 No he limpiado nada:\n"
                                      + "\n".join(f"· {n}" for n in r["notes"]))
            return
        notas.append("worktree eliminado")
        notas.append(f"rama {'borrada' if r['branch_deleted'] else 'conservada'}")
        notas += r["notes"]

    conv["archived"] = True
    conv["write"] = False
    ps["current"] = None
    save_state(state)
    await reply(cfg, chat_id, "🧹 Conversación archivada.\n" + "\n".join(f"· {n}" for n in notas)
                              + "\n\nYa no aparece en /chats. Empieza otra con un mensaje o /new.")


# ── Invocación de Claude Code ─────────────────────────────────────────────
async def run_claude(prompt: str, cwd: str, session_id, model: str = "",
                     write_mode: bool = False, timeout: int = READ_TIMEOUT) -> dict:
    """`claude -p` headless en el cwd dado. Devuelve el JSON parseado.

    La lista blanca (`--allowedTools` + `dontAsk`) es el único mecanismo de
    permisos: validado en T1, donde denegó una escritura real.
    """
    exe = shutil.which("claude") or "claude"
    cmd = [exe, "-p", prompt, "--output-format", "json",
           "--allowedTools", WRITE_TOOLS if write_mode else READ_TOOLS,
           "--disallowedTools", DENY_TOOLS,
           "--permission-mode", "dontAsk",
           "--max-turns", MAX_TURNS]
    if session_id:
        cmd += ["--resume", session_id]
    if model in MODELS:
        cmd += ["--model", model]

    env = {**os.environ, "CLAUDE_TG_BOT": "1"}
    log.info("invocando claude (cwd=%s, resume=%s, modelo=%s, escritura=%s, prompt=%d chars)",
             Path(cwd).name, bool(session_id), model or "default", write_mode, len(prompt))

    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd, env=env,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"La tarea superó {timeout // 60} minutos y se canceló.")

    if proc.returncode != 0:
        err = (stderr or b"").decode("utf-8", "replace").strip()[:400]
        raise RuntimeError(f"claude terminó con código {proc.returncode}: {err or 'sin detalle'}")
    try:
        return json.loads((stdout or b"").decode("utf-8", "replace"))
    except json.JSONDecodeError:
        raise RuntimeError("La respuesta de claude no es JSON válido.")


async def checkpoint_loop(cfg: dict, chat_id: int, worktree: str, started: float) -> None:
    """Avisa cada 30 min con la última etapa de .tg/progress.md (RFD C2)."""
    ultima = ""
    while True:
        await asyncio.sleep(CHECKPOINT_EVERY)
        mins = int((now_ts() - started) / 60)
        etapa = read_progress(worktree)
        if etapa and etapa != ultima:
            texto = f"⏱ {mins} min trabajando.\nÚltima etapa: {etapa}"
            ultima = etapa
        elif etapa:
            texto = f"⏱ {mins} min trabajando.\nSigue en: {etapa}"
        else:
            texto = f"⏱ {mins} min trabajando (el agente aún no ha reportado etapas)."
        log.info("checkpoint %s min (%s)", mins, etapa or "sin etapa")
        await reply(cfg, chat_id, texto)


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
    if (msg := busy(chat_id)):
        await reply(cfg, chat_id, msg)
        return

    ps = project_state(state, chat_id, project)
    _, conv = ensure_conv(ps)
    write_mode = bool(conv.get("write") and conv.get("worktree"))
    cwd = conv["worktree"] if write_mode else projects[project]["path"]
    session_id = conv.get("session_id")

    aged = session_id and (now_ts() - conv.get("last_activity", 0)) > SESSION_TTL_H * 3600
    if aged:
        log.info("TTL: sesión de '%s' caducada", project)
        session_id = None

    INFLIGHT[chat_id] = now_ts()
    ticker = None
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        if aged:
            await reply(cfg, chat_id, f"🕓 Sesión nueva por inactividad (>{SESSION_TTL_H}h).")

        prompt = text
        if write_mode:
            prompt = WRITE_PREAMBLE.format(branch=conv["branch"]) + text
            ticker = asyncio.create_task(
                checkpoint_loop(cfg, chat_id, conv["worktree"], now_ts()))

        try:
            data = await run_claude(prompt, cwd, session_id,
                                    chat_state(state, chat_id)["model"],
                                    write_mode=write_mode,
                                    timeout=WRITE_TIMEOUT if write_mode else READ_TIMEOUT)
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
            log.info("permission_denials: %d", len(denials))
            answer += (f"\n\n🔒 {len(denials)} acción(es) bloqueada(s) por la lista blanca"
                       + (" (commit/push/merge los hago yo con /commit, /push, /merge)."
                          if write_mode else " (modo solo lectura)."))

        if new_session:
            conv["session_id"] = new_session
        if not conv.get("label"):
            conv["label"] = (text[:40] + "…") if len(text) > 40 else text
        conv["last_activity"] = now_ts()
        save_state(state)

        log.info("respuesta ok (turnos=%s, costo=%.4f USD, rama=%s)",
                 data.get("num_turns"), data.get("total_cost_usd") or 0,
                 conv.get("branch") or "-")
        if write_mode:
            answer += "\n\n(/diff para ver los cambios · /commit para guardarlos)"
        await reply(cfg, chat_id, answer)
    finally:
        if ticker:
            ticker.cancel()
        INFLIGHT.pop(chat_id, None)


async def on_error(update, context):
    log.error("error no controlado: %s", context.error)


# ── Arranque ──────────────────────────────────────────────────────────────
def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    handler = logging.FileHandler(LOG_DIR / f"daemon-{datetime.now():%Y%m}.log", encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(fmt)
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logging.basicConfig(level=logging.INFO, handlers=[handler, console])
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def reconcile_startup(projects: dict, state: dict) -> None:
    """Contrasta el estado con los worktrees reales. Reporta, nunca borra."""
    for name, cfg in projects.items():
        conocidos = [c.get("worktree") for cs in state.get("chats", {}).values()
                     for pname, ps in cs.get("projects", {}).items() if pname == name
                     for c in ps.get("conversations", []) if c.get("worktree")]
        try:
            r = await gitops.reconcile(cfg["path"], conocidos)
        except gitops.GitError as exc:
            log.warning("reconciliación de '%s' fallida: %s", name, exc)
            continue
        for p in r["missing_on_disk"]:
            log.warning("[%s] worktree en el estado pero NO en disco: %s", name, p)
        for p in r["untracked_on_disk"]:
            log.warning("[%s] worktree tg/* en disco sin registro: %s", name, p)
        if not r["missing_on_disk"] and not r["untracked_on_disk"]:
            log.info("[%s] worktrees reconciliados sin discrepancias", name)


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    setup_logging()

    cfg = load_config()
    projects = load_projects()
    state = load_state()
    asyncio.run(reconcile_startup(projects, state))
    save_state(state)

    # concurrent_updates: sin esto PTB procesa los updates EN SERIE y el aviso
    # "⏳" nunca llegaría a tiempo (bug encontrado en las pruebas de T1).
    app: Application = (ApplicationBuilder().token(cfg["token"])
                        .concurrent_updates(True).build())
    app.bot_data.update({"cfg": cfg, "projects": projects, "state": state})

    for name, fn in (("start", cmd_start), ("help", cmd_start), ("p", cmd_p),
                     ("new", cmd_new), ("chats", cmd_chats), ("chat", cmd_chat),
                     ("model", cmd_model), ("status", cmd_status),
                     ("write", cmd_write), ("diff", cmd_diff), ("test", cmd_test),
                     ("commit", cmd_commit), ("push", cmd_push), ("merge", cmd_merge),
                     ("done", cmd_done)):
        app.add_handler(CommandHandler(name, fn))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_error_handler(on_error)

    log.info("daemon arrancado | proyectos: %s | allowlist: 1 | lectura por defecto",
             ", ".join(sorted(projects)))
    print("Daemon en marcha (long polling). Ctrl+C para parar.")
    app.run_polling(timeout=40, drop_pending_updates=True, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
