#!/usr/bin/env python3
"""
tg_daemon.py — Puente Telegram ↔ Claude Code. Fases T1 (chat) y T2 (escritura).

Long polling saliente: sin URL pública, sin túnel, detrás de NAT. Cada mensaje
invoca `claude -p --output-format json` desde el cwd correspondiente, así que la
sesión hereda el CLAUDE.md y las Memory Rules de ESE proyecto.

T2 — modo escritura (`ADR-20260801-puente-telegram`):
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

Arranque (Ctrl+C para parar):
  Windows:  py tg_daemon.py
  Linux:    "${XDG_DATA_HOME:-$HOME/.local/share}"/claude-telegram/venv/bin/python tg_daemon.py
            (el intérprete del venv que deja install-deps.sh, no python3 del
             sistema: python-telegram-bot no está fuera del venv por PEP 668)
"""
import asyncio
import json
import logging
import ntpath
import os
import posixpath
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from telegram import (BotCommand, InlineKeyboardButton,
                          InlineKeyboardMarkup, Update)
    from telegram.ext import (Application, ApplicationBuilder, CallbackQueryHandler,
                              CommandHandler, ContextTypes, MessageHandler, filters)
except ImportError:
    # ⚠ El mensaje anterior daba UNA receta y era Windows-only (`py -m pip`,
    # comando que en Linux no existe) — y en Ubuntu 24.04 el pip pelado falla
    # además por PEP 668. Auditoría 31, H3b.
    sys.exit("Falta python-telegram-bot. Instala las dependencias del puente:\n"
             "  Linux:    bash setup/telegram-bridge/install-deps.sh   (venv, PEP 668)\n"
             "  Windows:  py -m pip install -r setup/telegram-bridge/requirements.txt")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gitops                                              # noqa: E402
from progress import ProgressTracker                       # noqa: E402
import vaultio                                             # noqa: E402
import testcmd                                              # noqa: E402
import altas                                                # noqa: E402
import botprofile                                          # noqa: E402
from notify_telegram import deliver_text, load_env_file, _env_candidates, redact  # noqa: E402

BASE = Path(__file__).resolve().parent
PROJECTS_FILE = BASE / "projects.json"
STATE_FILE = BASE / "state.json"
LOG_DIR = BASE / "logs"

SESSION_TTL_H = 24          # R3 `ecosistema/16`: la continuidad durable la da el vault
READ_TIMEOUT = 1200         # 20 min · procedencia justo abajo
WRITE_TIMEOUT = 5400        # 90 min: un desarrollo real no cabe en 10 (RFD C9)

# ⏱ DE DÓNDE SALE `READ_TIMEOUT` (sprint 16, 2026-08-18).
#
# El 600 anterior venía comentado «10 min basta para una consulta». Eso no era
# una medida: era una SUPOSICIÓN escrita una vez que nadie volvió a mirar — la
# misma forma que el ×2,05 y el suelo de ~330 s. El campo la desmintió.
#
# MEDIDO, emparejando `invocando claude` con su cierre en los logs de las dos
# máquinas (26 lecturas que TERMINARON):
#   Legion, daemon-202608.log, 08-01..08-11 · n=24 · mediana 28 s · p90 138 s · max 394 s
#   SER8,   journalctl, 08-18               · n=2  · 179 s y 216 s
#   SER8,   08-18T11:36:42 → 11:46:42       · UNA MUERTE EN EL TECHO:
#     «invocando claude (escritura=False, prompt=3091 chars)» y diez minutos
#     después «invocación fallida: La tarea superó 10 minutos y se canceló».
#
# Esa muerte es **dato censurado**: no dice cuánto necesitaba, solo que 600 no
# bastó. Por eso el techo NO se sube «a un número más alto porque sí», se pone
# donde deja de ser lo que decide: 3× la lectura más larga jamás medida
# (394 s ⇒ 1182) redondeado a 1200. El acotador real vuelve a ser
# `--max-turns 15`, que acota por diseño y no por reloj — y esto YA NO es una
# suposición: la auditoría 39 (§3.2) señaló con razón que la frase iba sin
# medir, así que se midió el 2026-08-19 con una invocación deliberada:
#   claude -p ... --max-turns 1  ->  subtype=error_max_turns · num_turns=2
# El flag corta (ahí está el `error_max_turns`). Lo que NO coincide son las
# unidades: `num_turns` sale ~2× el tope, y por eso el log de la Legion tiene
# dos lecturas cerradas con `turnos=30` y `turnos=32` contra un tope de 15 sin
# un solo `error_max_turns` en 46 invocaciones. No era que el flag no acotara:
# era que se comparaban dos reglas distintas. Corregido en `progress.py`.
#
# QUÉ LO REVISA: rehacer la misma medida, no discutirla. En la SER8
#   journalctl --user -u claude-telegram -o short-iso
#     | grep -E "invocando claude|respuesta ok|invocación fallida"
# y emparejar cada invocación con su cierre. Si la máxima de lectura se acerca a
# ~400 s otra vez, este número volvió a quedarse corto: re-derívalo, no lo subas.
#
# Y el techo ya no mata a ciegas: al 80 % avisa (`TIMEOUT_ALERT_RATIO`) y el
# mensaje de cancelación dice en qué estaba (`ProgressTracker.death_text`).

# Cadencia del checkpoint: FRACCIÓN del techo, no un número suelto. El 1800
# anterior («30 min», RFD C2) estaba dimensionado para los 90 min de escritura
# y bajo el techo de lectura NO SE DISPARABA NUNCA: 30 min de cadencia dentro
# de 10 de vida. Un número absoluto al lado de un techo variable caduca solo;
# una fracción no. Con 0,25 salen ~5 min en lectura —que es lo que esta casa ya
# considera demasiado silencio (`SILENCE_ALERT`)— y 22,5 min en escritura, al
# lado de los 30 que ya se usaban: un solo criterio sirve a los dos modos.
CHECKPOINT_RATIO = 0.25     # ⇒ lectura 300 s · escritura 1350 s
CHECKPOINT_MIN = 60         # suelo: un techo pequeño no puede volverlo spam
MERGE_TOKEN_TTL = 300       # 5 min de vida del botón de merge (RFD C4)
MAX_TURNS = "15"            # consultas de lectura
MAX_TURNS_WRITE = "60"      # desarrollo real: con 15 una investigación se corta
                            # a mitad (observado: 6m40s → error_max_turns)

READ_TOOLS = "Read,Grep,Glob"
# Lista blanca de escritura (RFD C3). Es blanca: lo que no está, no corre.
WRITE_TOOLS = (
    "Read,Grep,Glob,Edit,Write,"
    "Bash(npm test:*),Bash(npm run test:*),Bash(npm run lint:*),Bash(npm run build:*),"
    "Bash(pytest:*),Bash(py -m pytest:*),Bash(python -m pytest:*),"
    # `python3` y no solo `python`: en Debian/Ubuntu el ejecutable se llama así
    # y `python` a secas puede no existir. Sin esta entrada el bot en la SER8
    # tenía permitido el nombre que allí NO se usa (auditoría 31 §9, ítem 7).
    "Bash(python3 -m pytest:*),Bash(ruff:*),"
    "Bash(eslint:*),Bash(flutter test:*),Bash(flutter analyze:*),"
    # El runner declarado en `.claude/settings.json` de ESTE repo. Sin esta
    # entrada el bot no podia correr los arneses de su propia casa: las de
    # arriba nombran suites genéricas (pytest, npm test) y aquí la suite se
    # invoca como `py setup/scripts/run-tests.py`. Una auditoría escrita desde
    # el puente (docs/auditoria/21) se quedó sin poder ver un solo verde por
    # esto, y tuvo que declararse a sí misma "reporte, no artefacto".
    # Es estrecha a propósito: el path exacto del runner, no `py:*`, que sería
    # ejecutar cualquier cosa. Lo vigila tests/test-perfil-bot.py, que resuelve
    # la declaración con el mismo código que /test.
    "Bash(py setup/scripts/run-tests.py:*),"
    # Y su forma PORTABLE, que es la que el agente teclea desde el sprint 11:
    # las skills ya no dicen `py`, dicen `setup/scripts/py` —el resolutor—
    # porque `py` no existe en Linux. Sin esta entrada el bot en la SER8 pedía
    # un permiso que nadie iba a conceder: al otro lado del móvil no hay humano
    # que apruebe un prompt, así que la invocación simplemente se cuelga.
    "Bash(setup/scripts/py setup/scripts/run-tests.py:*),"
    "Bash(git status:*),Bash(git diff:*),Bash(git log:*),Bash(git add:*)"
)
# Segunda barrera explícita: publicar/integrar nunca pasa por el agente.
DENY_TOOLS = ("WebFetch,Bash(git commit:*),Bash(git push:*),Bash(git merge:*),"
              "Bash(git reset:*),Bash(git checkout:*),Bash(rm:*),Bash(curl:*),Bash(wget:*)")


def deny_glob(base, sep=os.sep) -> str:
    """Patrón de denegación absoluto que cubre `base` y todo su árbol.

    ⚠ El separador iba escrito a mano (`f"Read({d}\\\\**)"`). En Windows casaba
    —así se verificó el 2026-08-01— y en Linux **no casaba con nada**: la
    denegación no denegaba, en silencio y solo en la máquina de destino
    (auditoría 31, H1). Aquí lo pone la plataforma, no el autor.

    Se normaliza además con el sabor de esa plataforma porque `repo_path` llega
    crudo de `projects.json`, donde `C:/Users/...` es una forma legal que
    `Path(...).is_dir()` acepta: sin normalizar, el patrón mezclaba separadores
    y la barrera de escritura quedaba abierta también en Windows.

    `sep` se inyecta solo para que el arnés pueda ejercer la plataforma ajena
    —que es donde vive este bug—; en producción nadie lo pasa.
    """
    sabor = ntpath if sep == "\\" else posixpath
    return f"{sabor.normpath(str(base))}{sep}**"


def secret_denies() -> str:
    """Deny de lectura sobre las rutas sensibles conocidas de ESTA máquina.

    Las LECTURAS no tienen frontera de directorio en ningún modo — el agente
    puede leer cualquier ruta del disco (auditoría 08-01; el diseño §2.4 lo
    prometía y no estaba implementado).

    ⚠ Verificado el 2026-08-01: los patrones **glob NO funcionan**
    (`Read(**/.env)` y `Read(*.env)` dejaron pasar la lectura). Solo bloquean
    las **rutas absolutas** (`Read(<ruta absoluta><sep>**)`, con el separador de
    la plataforma — lo pone `deny_glob`), así que se calculan aquí en
    vez de escribirse como comodín. Es mitigación de las rutas conocidas, no una
    frontera general: eso sigue siendo un residual documentado.
    """
    home = Path.home()
    objetivos = [p.parent for p in _env_candidates()]          # dirs de los .env
    objetivos += [home / ".ssh", home / ".aws", home / ".gnupg",
                  home / ".config" / "gh"]
    reglas = []
    for d in objetivos:
        try:
            reglas.append(f"Read({deny_glob(d)})")
        except Exception:
            continue
    return ",".join(dict.fromkeys(reglas))                     # sin duplicados

WRITE_PREAMBLE = (
    "[Puente Telegram — modo escritura. Trabajas en un worktree aislado sobre la "
    "rama {branch}; el árbol del usuario no se toca. Ve anotando el avance en "
    "`.tg/progress.md`: UNA línea por etapa completada (append, no reescribas el "
    "archivo) — es lo único que el usuario ve desde el móvil mientras trabajas. "
    "NO hagas commit, push ni merge: de eso se encarga el daemon con confirmación "
    "del usuario.]\n\n"
)

# El canal de salida es el CHAT, no el disco. Sin esto el agente interpreta
# "mándame un resumen en un md" como "crea el archivo" (patrón de sesión de
# escritorio) y el usuario nunca lo ve: el daemon entrega respuestas, no vigila
# el disco. Observado el 2026-08-01 (bug §11 del RFD 06/T4).
DELIVERY_RULE = (
    "[Cómo se entrega lo que produces: el usuario te lee por Telegram, así que "
    "**el canal de salida es tu respuesta**, no el sistema de archivos. Nunca "
    "uses `Write` para \"entregarle\" algo: no vería ese archivo. Crea archivos "
    "solo cuando formen parte del trabajo en el repo (código, documentación que "
    "se va a commitear).\n"
    "Si te pide **explícitamente un archivo** (\"mándame un md\", \"en un "
    "archivo\", \"un documento con...\"), pon como PRIMERA línea de tu respuesta:\n"
    "ARCHIVO: nombre-descriptivo.md\n"
    "y debajo el contenido. El puente lo entregará como adjunto descargable. Si "
    "no pide archivo, responde normal: lo largo se adjunta solo.]\n\n"
)

# Marcador con el que el agente pide entrega como adjunto (ver DELIVERY_RULE).
FILE_MARKER = re.compile(r"^\s*ARCHIVO:\s*([\w.\- ]{1,60})\s*\n", re.IGNORECASE)

SECRET_DENIES = ""      # se calcula en main() (rutas de ESTA máquina)
BOT_PROFILE_DIR = ""    # perfil de skills del bot (C2); vacío = config normal


def bot_profile_dir() -> str:
    """Directorio de config con SOLO las skills del perfil bot, o "".

    La decisión vive en `botprofile.py` —stdlib pura— para que su arnés no
    necesite python-telegram-bot, igual que `testcmd.py`. Aquí solo se registra
    el motivo, que ahora SIEMPRE existe: el perfil se niega si no tiene los
    hooks cableados (auditoría 31, H4), y una negativa muda es como esto pasó
    16 días encendido apagando la capa 3.
    """
    ruta, motivo = botprofile.resolver()
    (log.info if ruta else log.warning)("%s", motivo)
    return ruta

# Menú nativo de Telegram: al escribir "/" salen todos con autocompletado.
# Es la forma de no tener que recordarlos — mejor que un /help que hay que
# invocar sabiendo que existe. El orden es el del flujo real de trabajo.
BOT_COMMANDS = [
    ("p", "Activar proyecto · sin argumento lista los disponibles"),
    ("alta", "Dar de alta un proyecto: /alta <ruta> [comando de test]"),
    ("status", "Dónde estás: proyecto, conversación, modo, rama"),
    ("progress", "Qué está haciendo ahora · 'live' panel, 'off' apagar"),
    ("new", "Empezar una conversación nueva"),
    ("chats", "Listar las conversaciones del proyecto"),
    ("chat", "Retomar una conversación: /chat <n>"),
    ("model", "Ver o cambiar el modelo (opus, sonnet, haiku, fable)"),
    ("write", "Modo escritura on|off — crea rama y worktree propios"),
    ("diff", "Ver los cambios de la rama"),
    ("commit", "Guardar en la rama · sin mensaje lo propone el agente"),
    ("test", "Correr los tests del proyecto (obligatorio antes de /merge)"),
    ("pull", "Traer main a la rama, por si se quedó atrás"),
    ("push", "Publicar la rama y crear/actualizar su PR"),
    ("merge", "Integrar en main — pide confirmación y exige tests verdes"),
    ("done", "Terminar: limpia rama y worktree, archiva la conversación"),
    ("help", "Esta lista, con más detalle"),
]

MODELS = {
    "opus":   "el más capaz; caro (~0.1-1.9 USD por consulta observado)",
    "sonnet": "equilibrio capacidad/costo",
    "haiku":  "el más barato y rápido; ideal para consultas simples",
    "fable":  "rápido, orientado a escritura",
}
DEFAULT_MODEL = ""

INFLIGHT: dict = {}         # chat_id -> ts de inicio (un vuelo por chat)
PENDING_MERGE: dict = {}    # token -> {chat_id, project, idx, expires}
TRACKERS: dict = {}         # chat_id -> ProgressTracker (vivo o el último)
MONITOR_TICK = 5            # cada cuánto revisa el monitor (alertas + panel)

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


def leer_projects() -> tuple:
    """(proyectos, descartados, error). No mata el proceso: solo informa.

    Existe separado de `load_projects()` porque el arranque y la RECARGA EN
    CALIENTE necesitan lo mismo con finales distintos: en el arranque un
    `projects.json` roto debe tumbar el daemon, pero con el daemon ya en marcha
    tumbarlo por una coma de mas es perder el chat entero por un fichero que se
    puede volver a leer dentro de un minuto.
    """
    if not PROJECTS_FILE.is_file():
        return {}, [], f"Falta {PROJECTS_FILE.name}. Copia projects.example.json y edítalo."
    try:
        raw = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [], f"{PROJECTS_FILE.name} no es JSON válido: {exc}"

    valid, descartados = {}, []
    for name, entry in raw.items():
        if name.startswith("_"):
            continue
        cfg = {"path": entry, "test": ""} if isinstance(entry, str) else {
            "path": entry.get("path", ""), "test": entry.get("test", "")}
        if cfg["path"] and Path(cfg["path"]).is_dir():
            valid[name] = cfg
        else:
            descartados.append((name, cfg["path"]))
    return valid, descartados, ""


def load_projects() -> dict:
    """nombre → {path, test}. Acepta el formato de T1 (`"nombre": "ruta"`).

    ⚠ Los descartados se avisan **por su nombre y su ruta**. Antes era un
    `log.warning` genérico, y en la SER8 eso va al journal: un alta con la ruta
    de la Legion (`C:\\Users\\…`) desaparecía del listado sin una sola línea en
    el chat, que es donde estás mirando cuando das de alta un proyecto.
    """
    valid, descartados, error = leer_projects()
    if error:
        sys.exit(error)
    for name, ruta in descartados:
        log.warning("Proyecto '%s' ignorado: la ruta no existe en ESTA máquina (%s). "
                    "projects.json es por-máquina: da el alta aquí con /alta", name, ruta)
    if not valid:
        sys.exit("Ningún proyecto de projects.json apunta a una carpeta existente.")
    return valid


PROJECTS_MTIME = 0.0


def refrescar_projects(bot_data) -> list:
    """Relee `projects.json` si cambió en disco. Devuelve los nombres nuevos.

    POR QUÉ (2026-08-19). `load_projects()` corría SOLO en `main()`, así que dar
    de alta un proyecto exigía reiniciar el servicio — desde el móvil, que es el
    único sitio desde donde se usa esto, imposible. El dict se muta EN SITIO
    porque los handlers ya tienen su referencia desde `bot_data`.
    """
    global PROJECTS_MTIME
    try:
        mtime = PROJECTS_FILE.stat().st_mtime
    except OSError:
        return []
    if mtime == PROJECTS_MTIME:
        return []
    valid, descartados, error = leer_projects()
    if error:
        log.warning("projects.json no se pudo releer: %s", error)
        return []
    PROJECTS_MTIME = mtime
    proyectos = bot_data["projects"]
    nuevos = [n for n in valid if n not in proyectos]
    proyectos.clear()
    proyectos.update(valid)
    for name, ruta in descartados:
        log.warning("Proyecto '%s' ignorado al recargar: la ruta no existe (%s)", name, ruta)
    log.info("projects.json recargado: %d proyecto(s)%s", len(valid),
             f", nuevos: {', '.join(nuevos)}" if nuevos else "")
    return nuevos


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
    """Respuesta con la política de entrega de T0 (>4096 → resumen + adjunto).

    Si el agente marcó `ARCHIVO: nombre.md` en la primera línea, se entrega como
    adjunto descargable aunque sea corto: pedir "un md" y recibir un mensaje de
    chat no es lo que el usuario pidió (observado el 2026-08-01).
    """
    m = FILE_MARKER.match(text or "")
    if m:
        nombre = m.group(1).strip().replace(" ", "-")
        if not nombre.lower().endswith((".md", ".txt", ".json", ".csv")):
            nombre += ".md"
        cuerpo = text[m.end():].lstrip()
        await reply_doc(cfg, chat_id, nombre, cuerpo)
        log.info("entregado como adjunto: %s (%d chars)", nombre, len(cuerpo))
        return
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


def checkpoint_interval(timeout: int) -> int:
    """Cada cuánto manda checkpoint una invocación con ESE techo.

    Función y no constante porque el techo depende del modo: lo que sirve a 90
    min no sirve a 20, y escribir dos números sueltos garantiza que uno de los
    dos se quede atrás (que es exactamente lo que pasó con `CHECKPOINT_EVERY`).
    """
    return max(CHECKPOINT_MIN, int(timeout * CHECKPOINT_RATIO))


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
                "**Puente Telegram ↔ Claude Code**\n"
                "_Escribe `/` para ver todos los comandos con autocompletado._\n\n"

                "**Para empezar**\n"
                "`/p <proyecto>` — activar proyecto (sin argumento: lista)\n"
                "…y ya escribes normal: te respondo leyendo ese repo.\n"
                "`/status` — dónde estás · `/model` — cambiar modelo\n"
                "`/alta <ruta> [test]` — dar de alta un proyecto nuevo\n\n"

                "**Mientras trabajo**\n"
                "`/progress` — foto de qué estoy haciendo ahora\n"
                "`/progress live` — panel que se actualiza solo · `off` lo apaga\n"
                "_Los avisos de turnos al 80% y de 5 min sin actividad llegan "
                "siempre, tengas el panel o no._\n\n"

                "**Conversaciones** (cada una con su rama)\n"
                "`/new` · `/chats` · `/chat <n>`\n\n"

                "**Escritura** — `/write on` abre rama y worktree propios\n"
                "`/diff` → `/commit [msg]` → `/test` → `/merge` → `/done`\n"
                "`/pull` — traer main si la rama se quedó atrás\n"
                "`/push` — publicar la rama y su PR\n\n"

                "**Las reglas que no cambian**\n"
                "• Por defecto **solo leo**.\n"
                "• En escritura trabajo en una rama `tg/*` aislada: **tu árbol "
                "de trabajo nunca se toca**.\n"
                "• Yo no commiteo, publico ni integro — eso lo haces tú con los "
                "comandos de arriba.\n"
                "• `/merge` es el único con botón, y exige tests en verde.")


async def cmd_p(update, context):
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):          # RFD C10: no cambiar de foco en vuelo
        await reply(cfg, chat_id, msg)
        return

    # Un `projects.json` editado a mano (por ssh, o desde la otra laptop vía
    # sync) entra aquí sin reiniciar el servicio: `/p` es justo el sitio donde
    # notarías que falta el proyecto que acabas de escribir.
    refrescar_projects(context.bot_data)

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


async def cmd_alta(update, context):
    """`/alta <ruta> [comando de test]` — dar de alta un proyecto, desde el móvil.

    Las cinco comprobaciones y su veredicto viven en `altas.py` (stdlib, con
    arnés propio); aquí solo se entrega el checklist y se recarga en caliente.

    El `which` que se le pasa es **el de este proceso**: el daemon corre bajo
    `systemd --user`, cuyo PATH no es el de tu shell de login. Comprobar el
    comando de test contra cualquier otro PATH sería comprobar otra máquina.
    """
    cfg, projects, state = (context.bot_data[k] for k in ("cfg", "projects", "state"))
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    if (msg := busy(chat_id)):
        await reply(cfg, chat_id, msg)
        return

    args = context.args or []
    if not args:
        await reply(cfg, chat_id,
                    "*Dar de alta un proyecto*\n"
                    "`/alta <ruta absoluta> [comando de test]`\n\n"
                    "Ejemplos:\n"
                    "`/alta ~/projects/mi-app`\n"
                    "`/alta /home/floreano/projects/mi-app npm test`\n\n"
                    "La ruta es **de esta máquina** (el registro es por-máquina: "
                    "una ruta de la otra laptop no vale). El comando de test es "
                    "opcional _aquí_, pero sin ninguno declarado `/merge` queda "
                    "bloqueado: no hay verde posible.")
        return

    ruta, test = args[0], " ".join(args[1:])
    v = await asyncio.to_thread(altas.revisar, ruta, "", test, None, shutil.which)
    texto = altas.texto_veredicto(v)

    if not v["ok"]:
        await reply(cfg, chat_id, texto)
        return
    ok, motivo = await asyncio.to_thread(altas.registrar, v)
    if not ok:
        await reply(cfg, chat_id, texto + f"\n\n❌ {motivo}")
        return
    refrescar_projects(context.bot_data)
    activo = v["nombre"] in projects
    log.info("alta: %s -> %s (activable=%s)", v["nombre"], v["ruta"], activo)
    await reply(cfg, chat_id, texto + f"\n\n📇 {motivo}\n"
                + (f"Ya puedes activarlo: `/p {v['nombre']}`" if activo else
                   "⚠️ Escrito, pero el daemon no lo ve todavía: mira el journal."))


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


async def cmd_progress(update, context):
    """/progress · /progress live · /progress off (ADR-20260801-puente-telegram).

    NO está sujeto al lock de un vuelo por chat: su utilidad es precisamente
    mientras algo corre.
    """
    cfg, state = context.bot_data["cfg"], context.bot_data["state"]
    if not guard(update, cfg):
        return
    chat_id = update.effective_chat.id
    cs = chat_state(state, chat_id)
    arg = (context.args or [""])[0].strip().lower()
    tracker = TRACKERS.get(chat_id)

    if arg in ("live", "on"):
        cs["progress_live"] = True
        save_state(state)
        if tracker and not tracker.finished:
            # Encender a media tarea muestra lo YA ocurrido: el búfer estaba ahí
            msg = await context.bot.send_message(chat_id, tracker.panel_text())
            tracker.panel_msg_id = msg.message_id
            await reply(cfg, chat_id, "📊 Panel en vivo encendido (arriba, se actualiza solo).")
        else:
            await reply(cfg, chat_id, "📊 Panel en vivo encendido. Aparecerá en la próxima tarea.")
        return

    if arg in ("off", "no"):
        cs["progress_live"] = False
        save_state(state)
        await reply(cfg, chat_id, "📊 Panel apagado. `/progress` sigue disponible "
                                  "y las alertas siguen activas.")
        return

    if arg:
        await reply(cfg, chat_id, "Uso: /progress · /progress live · /progress off")
        return

    if not tracker:
        await reply(cfg, chat_id, "Nada en curso y sin tareas previas en esta sesión.")
        return
    ended = 0 if not tracker.finished else now_ts() - tracker.last_event
    await reply(cfg, chat_id, tracker.snapshot_text(ended))


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
    try:
        tests = testcmd.resolver(conv["worktree"], projects[project]) \
            or "(sin comando de test declarado)"
    except testcmd.ComandoInvalido as exc:
        tests = f"⚠ declarado pero invalido: {exc}"
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
    try:
        cmd = testcmd.resolver(conv["worktree"], projects[project])
    except testcmd.ComandoInvalido as exc:
        await reply(cfg, chat_id, f"❌ {exc}")
        return
    if not cmd:
        await reply(cfg, chat_id,
                    f"El proyecto '{project}' no declara comando de test.\n"
                    f"Se busca en .claude/settings.json del repo "
                    f"(env.GATE_TEST_CMD) y, si no, en projects.json.\n"
                    f"Sin verde no se puede /merge.")
        return

    INFLIGHT[chat_id] = now_ts()
    try:
        # El argv REAL, con el lanzador resuelto: el repo declara
        # `py setup/scripts/run-tests.py` y en Linux `py` no existe (auditoría
        # 31 §9). Se muestra lo que de verdad se va a ejecutar, no lo declarado:
        # si el usuario ve `py …` desde el móvil y el daemon corre otra cosa,
        # el día que falle estará depurando un comando que nadie lanzó.
        argv = testcmd.argv(cmd)
        await reply(cfg, chat_id, f"🧪 Ejecutando: `{' '.join(argv)}`")
        # CLAUDE_TG_BOT=1: la señal que test-claude-md-drift.py usa para saltar
        # (en voz alta) el chequeo del CLAUDE.md desplegado en este worktree —
        # esa copia es la versión BOT de gitops.bot_claude_md(), no una que se
        # quedó atrás. Antes de este cambio la variable solo llegaba a la
        # invocación de Claude (más abajo, run_claude), nunca a este subproceso.
        env = {**os.environ, "CLAUDE_TG_BOT": "1"}
        rc, out, err = await gitops.run(argv, conv["worktree"], timeout=1800, env=env)
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
        if r.get("forzado"):
            await reply(cfg, chat_id, "ℹ️ La rama venía rebasada (`/pull`), así que se "
                                      "reescribió en el remoto con `--force-with-lease`. "
                                      "Si había un PR abierto, se actualiza solo.")
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


async def cmd_pull(update, context):
    """Trae `main` a la rama de la conversación (gap del `ADR-20260801-puente-telegram` (gate de merge))."""
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
        base = await gitops.default_branch(projects[project]["path"])
        await reply(cfg, chat_id, f"⬇️ Trayendo `{base}` a `{conv['branch']}`…")
        r = await gitops.pull_base(conv["worktree"], base)
        if not r["ok"]:
            await reply(cfg, chat_id, f"❌ {r['reason']}")
            return
        if r.get("sin_cambios"):
            await reply(cfg, chat_id, f"✅ Ya estabas al día con `{base}`.")
            return
        # La rama cambió de base: el verde anterior ya no vale
        conv["test_ok_sha"] = None
        save_state(state)
        log.info("pull: %s rebasada sobre %s (%s commits)", conv["branch"], base, r["detras"])
        await reply(cfg, chat_id,
                    f"✅ Rebasada sobre `{base}` ({r['detras']} commit(s) nuevos).\n"
                    f"`{r['antes']}` → `{r['ahora']}`\n\n"
                    f"⚠️ El verde de /test caducó al cambiar la base: "
                    f"vuelve a correr /test antes de /merge.")
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

    # A3 — TOCTOU: entre lanzar /merge y pulsar el botón pudo pasar cualquier
    # cosa (un /commit invalida el verde, o llegaron cambios sin commitear).
    # El estado se re-verifica AQUÍ, no solo al crear el token.
    try:
        head_ahora = await gitops.head_sha(conv["worktree"])
        sucio = (await gitops.diff_summary(conv["worktree"]))["has_changes"]
    except gitops.GitError as exc:
        await query.edit_message_text(f"❌ No pude verificar el estado: {exc}")
        return
    if sucio:
        await query.edit_message_text("🚫 Cancelado: aparecieron cambios sin commitear "
                                      "después de lanzar /merge. Haz /commit y repite.")
        return
    if conv.get("test_ok_sha") != head_ahora:
        await query.edit_message_text(
            f"🚫 Cancelado: la rama cambió desde que pediste el merge "
            f"(verde en {conv.get('test_ok_sha') or '—'}, ahora {head_ahora}).\n"
            f"Corre /test otra vez y vuelve a lanzar /merge.")
        return

    await query.edit_message_text(f"Integrando {conv['branch']}…")

    INFLIGHT[chat_id] = now_ts()
    try:
        base = await gitops.default_branch(repo)
        pr_url = conv.get("pr_url", "")

        # Ruta preferente: vía PR. El merge ocurre en el remoto y NO toca el
        # árbol del usuario — que casi siempre tiene cambios sin commitear, así
        # que la ruta local sería inutilizable en la práctica.
        #
        # ⚠ SIEMPRE se publica antes de mergear, aunque el PR ya exista. Sin
        # esto, un commit hecho DESPUÉS del último /push se queda fuera del PR
        # y el merge integra solo una parte diciendo "✅ Integrado" (observado
        # el 2026-08-01: rama con 2 commits, PR con 1). Además invalidaría el
        # verde de /test, medido sobre el HEAD local.
        if await gitops.has_remote(repo):
            await reply(cfg, chat_id, "Publicando la rama antes de integrarla "
                                      "(así el PR lleva todos los commits)…")
            pushed = await gitops.push_branch(conv["worktree"], conv["branch"])
            if not pushed.get("pushed"):
                await reply(cfg, chat_id, f"❌ No pude publicar la rama: "
                                          f"{pushed.get('reason')}\nNo integro a medias.")
                return
            # El remoto debe quedar EXACTAMENTE en el HEAD que validó /test.
            # P1: si NO se puede saber (ls-remote falla por red o timeout) NO se
            # integra. "No pude verificar → asumo que sí" es fail-open, y es
            # justo el patrón que este bloque vino a matar.
            remoto = await gitops.remote_head(conv["worktree"], conv["branch"])
            if not remoto:
                await reply(cfg, chat_id, "❌ No pude confirmar la punta remota de la "
                                          "rama (¿red?). No integro sin verificarla: "
                                          "reintenta el /merge en un momento.")
                return
            if not head_ahora.startswith(remoto[:len(head_ahora)]) \
                    and not remoto.startswith(head_ahora):
                await reply(cfg, chat_id, f"❌ El remoto quedó en `{remoto[:7]}` y el "
                                          f"local en `{head_ahora}`. No integro con esa "
                                          f"discrepancia — vuelve a intentarlo.")
                return
            if not pr_url:
                pr = await gitops.ensure_pr(conv["worktree"], conv["branch"], base,
                                            conv["label"][:70] or conv["branch"])
                if pr.get("pr"):
                    pr_url = pr["url"]
                    conv["pr_url"] = pr_url
                    save_state(state)
                    log.info("PR listo para merge: %s", pr_url)
                else:
                    # ⚠ Esto era `log.warning` A SECAS: el único `reason` del
                    # puente que se quedaba en el diccionario. El humano veía
                    # que el merge tomaba la ruta local y no sabía por qué —y
                    # el motivo más frecuente (`gh` ausente) tiene cura. El log
                    # lo lee quien tiene SSH; el chat, quien pidió el merge.
                    log.warning("sin PR (%s): se intentará merge local", pr.get("reason"))
                    await reply(cfg, chat_id,
                                f"ℹ️ Sin PR: {pr.get('reason', 'sin motivo')}\n"
                                f"Sigo por la ruta local (squash directo sobre "
                                f"`{base}`).")

        r = await gitops.merge_squash(repo, conv["branch"], base,
                                      conv["label"][:70] or f"merge {conv['branch']}",
                                      pr_url)
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
        # C4 — la nota la escribe EL DAEMON, y ANTES de borrar el worktree:
        # después ya no se podrían leer ni los commits ni .tg/progress.md.
        # Solo en /done: un /write off es una pausa, no un final (ADR-20260801-bot-memoria-y-perfil).
        try:
            base = await gitops.default_branch(projects[project]["path"])
            commits = await gitops.commits_ahead(conv["worktree"], conv["branch"], base)
        except gitops.GitError:
            commits = []
        etapas = []
        try:
            pf = Path(conv["worktree"]) / gitops.PROGRESS_DIR / "progress.md"
            if pf.is_file():
                etapas = [l.strip() for l in pf.read_text(encoding="utf-8",
                                                          errors="replace").splitlines()
                          if l.strip()]
        except OSError:
            pass
        ruta_nota = vaultio.write_session_note(
            project, conv["branch"] or "", commits,
            "mergeada" if conv.get("merged") else "abandonada",
            etapas, conv.get("label", ""))
        if ruta_nota:
            notas.append(f"nota de sesión en el vault: {Path(ruta_nota).name}")
            log.info("nota de sesión escrita: %s", ruta_nota)
            # C5 — y se PUBLICA. Escribirla y no commitearla no dejaba la nota
            # "desincronizada": la dejaba existiendo solo en el disco de la
            # SER8, o sea perdida en cuanto otra máquina pulle con divergencia.
            # El resultado va al CHAT (aquí, en `notas`), no al log: si el push
            # rebota, el sitio donde eso se tiene que ver es el /done.
            ok_vault, motivo = await asyncio.to_thread(
                vaultio.commit_push, [ruta_nota],
                f"tg: nota de sesión {Path(ruta_nota).stem}")
            notas.append(("vault: " + motivo) if ok_vault
                         else f"⚠️ vault NO sincronizado — {motivo}")
            log.info("vault commit+push: %s (%s)", "ok" if ok_vault else "no", motivo)

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
        if r.get("branch_status"):          # ya viene redactado y sin duplicar
            notas.append(f"rama {r['branch_status']}")
        notas += r["notes"]

    conv["archived"] = True
    conv["write"] = False
    ps["current"] = None
    save_state(state)
    await reply(cfg, chat_id, "🧹 Conversación archivada.\n" + "\n".join(f"· {n}" for n in notas)
                              + "\n\nYa no aparece en /chats. Empieza otra con un mensaje o /new.")


# ── Invocación de Claude Code ─────────────────────────────────────────────
async def run_claude(prompt: str, cwd: str, session_id, model: str = "",
                     write_mode: bool = False, timeout: int = READ_TIMEOUT,
                     tracker=None, repo_path: str = "") -> dict:
    """`claude -p` headless en el cwd dado. Devuelve el evento `result`.

    Usa `stream-json` (que **exige `--verbose`** con `-p`, verificado) para
    poder alimentar el tracker de progreso según ocurren las cosas. El evento
    final `result` tiene la misma forma que el JSON de antes, así que el resto
    del daemon no cambia.

    La lista blanca (`--allowedTools` + `dontAsk`) es el único mecanismo de
    permisos: validado en T1, donde denegó una escritura real.
    """
    exe = shutil.which("claude") or "claude"
    # ⚠ El modo de permisos NO es cosmético: decide si existe frontera de
    # directorio. Verificado el 2026-08-01 con un canario fuera del worktree:
    #   dontAsk     → escribe DENTRO y FUERA del cwd (sin frontera)
    #   acceptEdits → escribe dentro, DENIEGA fuera
    # En lectura `dontAsk` es correcto (deniega toda escritura, validado en T1);
    # en escritura sería un agujero en el aislamiento que T2 promete.
    mode = "acceptEdits" if write_mode else "dontAsk"
    deny = DENY_TOOLS + ("," + SECRET_DENIES if SECRET_DENIES else "")
    if write_mode and repo_path:
        # Segunda barrera explícita sobre el repo del usuario: el worktree vive
        # en %LOCALAPPDATA%, así que esto no estorba al trabajo legítimo.
        deny += f",Write({deny_glob(repo_path)}),Edit({deny_glob(repo_path)})"

    cmd = [exe, "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--allowedTools", WRITE_TOOLS if write_mode else READ_TOOLS,
           "--disallowedTools", deny,
           "--permission-mode", mode,
           "--max-turns", MAX_TURNS_WRITE if write_mode else MAX_TURNS]
    if session_id:
        cmd += ["--resume", session_id]
    if model in MODELS:
        cmd += ["--model", model]

    env = {**os.environ, "CLAUDE_TG_BOT": "1"}
    # C2 — perfil de skills del bot: solo las 15 del registro de
    # setup/skills/README.md. Medido el 2026-08-01 con el mismo prompt:
    #   perfil completo (31 skills) 40 605 tok / 0.1894 USD
    #   perfil bot      (15 skills) 34 961 tok / 0.1248 USD  ← −14% tok, −34% costo
    #   sin skills de usuario       32 487 tok / 0.1034 USD  (pierde las útiles)
    # El costo cae mucho más que los tokens porque crear caché se paga más caro
    # que leerla. Si el perfil no existe, se usa la config normal (fallback).
    if BOT_PROFILE_DIR:
        env["CLAUDE_CONFIG_DIR"] = BOT_PROFILE_DIR
    log.info("invocando claude (cwd=%s, resume=%s, modelo=%s, escritura=%s, prompt=%d chars)",
             Path(cwd).name, bool(session_id), model or "default", write_mode, len(prompt))

    # limit alto: una línea del stream puede traer el input/output de una
    # herramienta y los 64 KB por defecto se quedan cortos.
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd, env=env, limit=8 * 1024 * 1024,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    result_event, stderr_text = None, ""

    async def pump_stdout():
        nonlocal result_event
        descartadas = 0
        while True:
            try:
                raw = await proc.stdout.readline()
            except (ValueError, asyncio.LimitOverrunError):
                # A2 — una línea mayor que el límite NO se consume sola: hacer
                # `continue` sin drenar giraría para siempre quemando CPU.
                # Se drena a mano hasta el próximo salto de línea.
                descartadas += 1
                try:
                    while True:
                        trozo = await proc.stdout.read(65536)
                        if not trozo or b"\n" in trozo:
                            break
                except Exception:
                    break
                if descartadas > 50:          # algo va muy mal: no insistir
                    log.error("stream con demasiadas líneas ilegibles; se corta la lectura")
                    break
                log.warning("línea del stream mayor que el límite: descartada")
                continue
            if not raw:
                break
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if tracker is not None:
                tracker.feed(event)
            if event.get("type") == "result":
                result_event = event

    async def pump_stderr():
        nonlocal stderr_text
        data = await proc.stderr.read()
        stderr_text = data.decode("utf-8", "replace").strip()

    try:
        await asyncio.wait_for(
            asyncio.gather(pump_stdout(), pump_stderr(), proc.wait()), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        # Con el tracker delante, la cancelación puede decir EN QUÉ ESTABA. Sin
        # eso el humano recibe un error; con eso, un diagnóstico.
        detalle = f"\n{tracker.death_text()}" if tracker is not None else ""
        raise RuntimeError(f"La tarea superó {timeout // 60} minutos y se canceló."
                           f"{detalle}")

    # El CLI sale con código 1 en errores SEMÁNTICOS (agotar --max-turns) con
    # stderr vacío, pero el evento `result` SÍ llega — con el session_id dentro.
    # Aprovecharlo siempre: guiarse solo por el returncode pierde la respuesta
    # y, peor, el hilo de la conversación.
    if result_event is not None:
        if proc.returncode != 0:
            log.info("exit %s con evento result (subtype=%s): se aprovecha",
                     proc.returncode, result_event.get("subtype"))
        return result_event

    if proc.returncode != 0:
        raise RuntimeError(f"claude terminó con código {proc.returncode}: "
                           f"{stderr_text[:400] or 'sin detalle en stderr'}")
    raise RuntimeError("El stream terminó sin evento `result`.")


async def monitor_loop(cfg: dict, chat_id: int, tracker: ProgressTracker,
                       worktree: str, bot, live: bool,
                       timeout: int = READ_TIMEOUT) -> None:
    """Vigila la invocación: **alertas siempre**, panel solo si `live`.

    Las alertas proactivas son la pieza no-opcional (ADR-20260801-puente-telegram).

    Las alertas son la red que no depende de que el usuario esté mirando; el
    panel es comodidad. Por eso este bucle corre aunque el panel esté apagado.
    """
    cada = checkpoint_interval(timeout)
    ultimo_checkpoint = now_ts()
    while True:
        await asyncio.sleep(MONITOR_TICK)

        if worktree:                     # hitos semánticos que el agente elige
            tracker.milestone = read_progress(worktree)

        for alerta in tracker.pending_alerts():      # P6: máx 1 de cada tipo
            log.info("ALERTA: %s", alerta)
            await reply(cfg, chat_id, alerta)

        if live and tracker.should_edit():
            try:
                if tracker.panel_msg_id is None:
                    msg = await bot.send_message(chat_id, tracker.panel_text())
                    tracker.panel_msg_id = msg.message_id
                else:
                    await bot.edit_message_text(tracker.panel_text(), chat_id=chat_id,
                                                message_id=tracker.panel_msg_id)
            except Exception as exc:      # panel roto no puede tumbar la tarea
                log.warning("panel no actualizado: %s", exc)

        # Checkpoint de T2 (C2): superviviente para tareas largas sin panel.
        #
        # ⚠ NO lleva `worktree and`. Lo llevó cuatro sprints y por eso el modo
        # lectura era una caja negra POR CONSTRUCCIÓN: en lectura no hay
        # worktree, así que el checkpoint —el propio «superviviente sin panel»—
        # quedaba excluido justo del único modo que no tiene otra red. El panel
        # está apagado por defecto y `SILENCE_ALERT` solo salta cuando el stream
        # se CALLA, y una tarea que trabaja de verdad emite eventos: la red
        # existía y este caso pasaba por debajo. Medido: una lectura de 10 min
        # en la SER8 mandó CERO mensajes hasta que el techo la mató.
        #
        # El worktree solo hacía falta para `read_progress`; el tiempo y la
        # última acción los tiene el tracker, que se alimenta del stream.
        if not live and now_ts() - ultimo_checkpoint >= cada:
            ultimo_checkpoint = now_ts()
            texto = tracker.checkpoint_text()
            log.info("checkpoint: %s", texto)
            await reply(cfg, chat_id, texto)


async def close_panel(bot, chat_id: int, tracker: ProgressTracker) -> None:
    """Edición FINAL del panel con el resumen (ADR-20260801-puente-telegram)."""
    if tracker.panel_msg_id is None:
        return
    try:
        await bot.edit_message_text(tracker.final_text(), chat_id=chat_id,
                                    message_id=tracker.panel_msg_id)
    except Exception as exc:
        log.warning("panel final no actualizado: %s", exc)


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
    cs = chat_state(state, chat_id)
    live = bool(cs.get("progress_live"))          # apagado por defecto (ADR del puente)
    techo = WRITE_TIMEOUT if write_mode else READ_TIMEOUT
    tracker = ProgressTracker(
        branch=conv.get("branch") or "", model=cs["model"] or "default",
        max_turns=int(MAX_TURNS_WRITE if write_mode else MAX_TURNS),
        write_mode=write_mode, timeout=techo)
    TRACKERS[chat_id] = tracker
    monitor = None
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        if aged:
            await reply(cfg, chat_id, f"🕓 Sesión nueva por inactividad (>{SESSION_TTL_H}h).")

        prompt = text
        if write_mode:
            prompt = WRITE_PREAMBLE.format(branch=conv["branch"]) + text
        # La regla de entrega aplica en AMBOS modos: en lectura también puede
        # caer en "creo el archivo" si el proyecto tiene permiso de escritura
        # por otra vía, y sobre todo evita que prometa archivos que no verás.
        prompt = DELIVERY_RULE + prompt
        # C1b — solo en el PRIMER mensaje de la conversación: después ya vive en
        # el transcript y repetirlo sería pagar el mismo contexto cada turno.
        if not session_id:
            # C5 — `pull` ANTES de leer: en la SER8 no hay Obsidian que
            # sincronice el vault, así que sin esto el briefing servía lo que
            # hubiera en disco desde el último pull a mano, sin decir su edad.
            # En un hilo (subprocess síncrono) y con timeout: la red no puede
            # colgar el bucle de eventos, y si falla se sigue con lo que hay.
            sync = await asyncio.to_thread(vaultio.sync_pull)
            log.info("vault pull: %s (%s)", "ok" if sync[0] else "no", sync[1])
            briefing = vaultio.project_briefing(project, sync)
            if briefing:
                prompt = briefing + prompt
                log.info("briefing inyectado (%d chars)", len(briefing))
        # El monitor corre SIEMPRE: las alertas no dependen del panel (P6)
        monitor = asyncio.create_task(
            monitor_loop(cfg, chat_id, tracker, conv.get("worktree") or "",
                         context.bot, live, techo))

        try:
            data = await run_claude(prompt, cwd, session_id, cs["model"],
                                    write_mode=write_mode,
                                    timeout=techo,
                                    tracker=tracker,
                                    repo_path=projects[project]["path"])
        except RuntimeError as exc:
            log.error("invocación fallida: %s", exc)
            tracker.finished = True
            await reply(cfg, chat_id, f"❌ {exc}")
            return

        new_session = data.get("session_id")
        answer = (data.get("result") or "").strip()
        denials = data.get("permission_denials") or []
        subtype = data.get("subtype") or ""

        if subtype == "error_max_turns":
            # No es un fallo: se quedó sin turnos. El hilo sobrevive (guardamos
            # el session_id abajo), así que basta con pedirle que siga.
            limite = MAX_TURNS_WRITE if write_mode else MAX_TURNS
            # Sin «(N usados)»: ese N era `num_turns`, que no va en la unidad
            # del límite y salía mayor que él (auditoría 39 §3.3, medido).
            answer = (f"⏹ Alcanzado el límite de {limite} turnos y se detuvo "
                      f"ahí.\n\n"
                      f"{answer or 'No alcanzó a redactar una respuesta.'}\n\n"
                      f"La conversación NO se perdió: escribe «continúa» y sigue "
                      f"desde donde iba"
                      + (" (revisa /diff: puede haber dejado trabajo hecho)."
                         if write_mode else "."))
        elif data.get("is_error"):
            answer = f"⚠️ Claude reportó error:\n{answer or '(sin detalle)'}"
        elif not answer:
            answer = "(respuesta vacía)"
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
        tracker.finished = True
        if monitor:
            monitor.cancel()
        await close_panel(context.bot, chat_id, tracker)    # resumen final (P3/P5)
        INFLIGHT.pop(chat_id, None)


async def on_error(update, context):
    # ⚠ El texto de la excepcion va REDACTADO tambien al log. La auditoria 39
    # (§4.3) encontro que el sprint 16 cerro la fuga por el lado del chat y dejo
    # abierto el del journal: los errores de la libreria de Telegram llevan la
    # URL de la API dentro, y ahi va el token. `redact` ya existia en
    # `notify_telegram` con ese docstring exacto —«jamas debe aparecer en un log
    # o error»— usada en seis sitios de su fichero y en CERO de este.
    #
    # No hubo incidente: `logs/` esta gitignorado y el log actual no tiene
    # ninguna coincidencia. Era riesgo latente, y los logs se pegan en los
    # informes de campo (este sprint pego `journalctl` tres veces).
    token = (context.bot_data or {}).get("cfg", {}).get("token", "")
    log.error("error no controlado: %s", redact(str(context.error), token))
    # El barrido de razones mudas (sprint 16, A3) encontro este de paso: un
    # fallo no controlado dejaba al humano SIN NADA —ni respuesta ni motivo—,
    # que es la misma caja negra que este sprint cierra por el otro lado. El log
    # lo lee quien tiene SSH; quien escribio el mensaje merece saber que murio.
    #
    # Va el TIPO de la excepcion y no su texto a proposito: los errores de la
    # libreria de Telegram llevan la URL de la API dentro, y ahi va el token.
    # Un aviso no puede convertirse en una fuga.
    #
    # Y entero dentro de un `try`: reventar en el manejador de errores es la
    # forma de tumbar el daemon justo cuando ya iba mal.
    try:
        cfg = context.bot_data.get("cfg") if context.bot_data else None
        chat_id = getattr(getattr(update, "effective_chat", None), "id", None)
        if cfg and chat_id:
            await reply(cfg, chat_id,
                        f"❌ Algo se rompio por dentro y tu peticion no llego a "
                        f"completarse ({type(context.error).__name__}). "
                        f"El detalle esta en el log del daemon.")
    except Exception as exc:
        log.error("ni el aviso del fallo pudo enviarse: %s", exc)


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
        # Solo las conversaciones VIVAS: una archivada por /done ya no tiene
        # worktree a propósito, y reportarla sería ruido en cada arranque.
        conocidos = [c.get("worktree") for cs in state.get("chats", {}).values()
                     for pname, ps in cs.get("projects", {}).items() if pname == name
                     for c in ps.get("conversations", [])
                     if c.get("worktree") and not c.get("archived")]
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

    global SECRET_DENIES, BOT_PROFILE_DIR, PROJECTS_MTIME
    SECRET_DENIES = secret_denies()
    BOT_PROFILE_DIR = bot_profile_dir()
    # El perfil ya se registró (con su motivo) dentro de bot_profile_dir().
    log.info("deny de secretos: %d rutas",
             len(SECRET_DENIES.split(",")) if SECRET_DENIES else 0)
    cfg = load_config()
    projects = load_projects()
    try:                            # base de la recarga en caliente (/alta, /p)
        PROJECTS_MTIME = PROJECTS_FILE.stat().st_mtime
    except OSError:
        PROJECTS_MTIME = 0.0
    state = load_state()
    asyncio.run(reconcile_startup(projects, state))
    save_state(state)

    # concurrent_updates: sin esto PTB procesa los updates EN SERIE y el aviso
    # "⏳" nunca llegaría a tiempo (bug encontrado en las pruebas de T1).
    async def _post_init(application: Application) -> None:
        """Registra el menú de comandos de Telegram (el que sale al teclear '/')."""
        try:
            await application.bot.set_my_commands(
                [BotCommand(c, d) for c, d in BOT_COMMANDS])
            log.info("menú de comandos registrado (%d)", len(BOT_COMMANDS))
        except Exception as exc:      # sin menú se sigue pudiendo usar todo
            log.warning("no se pudo registrar el menú de comandos: %s", exc)

    app: Application = (ApplicationBuilder().token(cfg["token"])
                        .concurrent_updates(True)
                        .post_init(_post_init).build())
    app.bot_data.update({"cfg": cfg, "projects": projects, "state": state})

    for name, fn in (("start", cmd_start), ("help", cmd_start), ("p", cmd_p),
                     ("alta", cmd_alta),
                     ("new", cmd_new), ("chats", cmd_chats), ("chat", cmd_chat),
                     ("model", cmd_model), ("status", cmd_status), ("progress", cmd_progress),
                     ("write", cmd_write), ("diff", cmd_diff), ("test", cmd_test),
                     ("commit", cmd_commit), ("push", cmd_push), ("pull", cmd_pull), ("merge", cmd_merge),
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
