#!/usr/bin/env python3
"""
notify_telegram.py — Vía 1 (fase T0) del puente Telegram: SOLO ENVIAR.

POST saliente a la Bot API. Sin servidor, sin daemon, sin bot escuchando,
sin URL pública (ver docs/telegram/00-DISENO-TELEGRAM-BRIDGE.md §1).

Uso (desde la raíz del repo; `py` a secas no existe en Linux):
    setup/scripts/py setup/telegram-bridge/notify_telegram.py "mensaje"
    setup/scripts/py setup/telegram-bridge/notify_telegram.py "resumen" --file informe.md
    echo "mensaje" | setup/scripts/py setup/telegram-bridge/notify_telegram.py
    setup/scripts/py setup/telegram-bridge/notify_telegram.py "titulo" < informe.txt
                                            # (arg = texto, stdin ignorado)

Credenciales (NUNCA hardcodeadas, NUNCA en OneDrive/skills — anti-patrón S5):
    TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID como variables de entorno,
    con fallback a un `.env` (KEY=VALUE) junto a este script.
    El entorno GANA sobre el .env. El token jamás se imprime ni se loggea.

Formato: HTML (subconjunto de Telegram) con escapado total previo, y **fallback
automático a texto plano** si la API devuelve 400. El markdown de Claude
(`**negrita**`, `## títulos`, ``` bloques ```) se convierte a lo que Telegram
entiende; los encabezados pasan a negrita y las viñetas a `•` porque Telegram
no tiene ni encabezados ni listas. El principio se mantiene: el formato es un
lujo, que el mensaje LLEGUE no es negociable.

Salida: 0 = enviado | 1 = error de uso/configuración | 2 = fallo de red/API.
"""
import argparse
import html as html_mod
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# Límites oficiales de la Bot API (core.telegram.org/bots/api)
TEXT_LIMIT = 4096          # sendMessage
SUMMARY_CHARS = 800        # resumen que acompaña al adjunto
DOC_LIMIT = 50 * 1024 * 1024   # sendDocument: 50 MB
TIMEOUT = 15               # segundos
BACKOFF = 2                # espera del reintento único si no hay Retry-After
INTER_MSG_PAUSE = 0.4      # ~1 msg/seg por chat (guía oficial)

def _env_candidates() -> list:
    """Rutas del .env, en orden de preferencia.

    La PRIMERA es disco local fuera de OneDrive: este repo vive dentro de
    OneDrive y un secreto ahí se replicaría a la nube y a cada laptop — es
    exactamente el hallazgo A4 de la auditoría (por el que el .env de Graphiti
    vive en %LOCALAPPDATA%). La segunda se acepta por comodidad, pero el
    README avisa del riesgo.
    """
    paths = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        paths.append(Path(local) / "claude-telegram" / ".env")
    paths.append(Path.home() / ".config" / "claude-telegram" / ".env")  # Unix
    paths.append(Path(__file__).resolve().parent / ".env")             # repo
    return paths


ENV_FILE = _env_candidates()[0]   # la recomendada, para los mensajes de ayuda


# ── Credenciales ──────────────────────────────────────────────────────────
def load_env_file(path: Path) -> dict:
    """Lee un .env simple KEY=VALUE. Ignora comentarios y líneas vacías."""
    values = {}
    if not path.is_file():
        return values
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip().strip('"').strip("'")
    except OSError as exc:
        die(f"No se pudo leer {path.name}: {exc}", 1)
    return values


def get_credentials() -> tuple:
    """Entorno primero, luego el primer .env que exista. Falla ruidosamente."""
    file_env = {}
    for candidate in _env_candidates():
        if candidate.is_file():
            file_env = load_env_file(candidate)
            break

    token = os.environ.get("TELEGRAM_BOT_TOKEN") or file_env.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or file_env.get("TELEGRAM_CHAT_ID")

    missing = [n for n, v in (("TELEGRAM_BOT_TOKEN", token),
                              ("TELEGRAM_CHAT_ID", chat_id)) if not v]
    if missing:
        die(
            f"Faltan credenciales: {', '.join(missing)}.\n"
            f"  Define las variables de entorno o crea el archivo (recomendado,\n"
            f"  fuera de OneDrive):\n"
            f"    {ENV_FILE}\n"
            f"  con el formato:\n"
            f"    TELEGRAM_BOT_TOKEN=123456:ABC-DEF...\n"
            f"    TELEGRAM_CHAT_ID=987654321\n"
            f"  Guía completa: setup/telegram-bridge/README.md",
            1,
        )
    return token, chat_id


# ── Utilidades ────────────────────────────────────────────────────────────
def die(msg: str, code: int) -> None:
    print(f"[notify-telegram] ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def redact(text: str, token: str) -> str:
    """El token viaja en la URL: jamás debe aparecer en un log o error."""
    return text.replace(token, "<TOKEN-OCULTO>") if token else text


TABLE_RE = re.compile(
    r"(?m)^[^\n]*\|[^\n]*\n[ \t]*\|?[\s:|-]*-[\s:|-]*\|[\s:|-]*\n(?:[^\n]*\|[^\n]*(?:\n|$))*")

TABLE_MAX_WIDTH = 42       # ancho cómodo en pantalla de móvil


def _render_table(block: str) -> tuple:
    """Tabla markdown → texto legible en Telegram (que no soporta tablas).

    Estrecha  → columnas alineadas en monoespaciado (`<pre>`).
    Ancha     → una entrada por fila con `campo: valor` (en móvil lee mejor
                que una tabla que obliga a hacer scroll horizontal).
    Devuelve (texto, usar_pre).
    """
    rows = []
    for line in block.strip().splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        if re.fullmatch(r"\|?[\s:|-]+\|?", line):      # fila separadora
            continue
        rows.append([c.strip() for c in line.strip("|").split("|")])
    if not rows:
        return block, False

    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    widths = [max(len(r[i]) for r in rows) for i in range(ncols)]
    total = sum(widths) + 2 * (ncols - 1)

    if total <= TABLE_MAX_WIDTH:
        # Ya va en monoespaciado: los backticks solo serían ruido visual
        rows = [[c.replace("`", "") for c in r] for r in rows]
        widths = [max(len(r[i]) for r in rows) for i in range(ncols)]
        total = sum(widths) + 2 * (ncols - 1)
        out = []
        for idx, row in enumerate(rows):
            out.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(row)).rstrip())
            if idx == 0:
                out.append("─" * total)
        return "\n".join(out), True

    header, out = rows[0], []
    for row in rows[1:]:
        out.append(f"▸ {row[0]}")
        for i in range(1, ncols):
            if row[i]:
                label = header[i] if header[i] else f"col{i + 1}"
                out.append(f"   {label}: {row[i]}")
        out.append("")
    return "\n".join(out).rstrip(), False


def md_to_telegram_html(text: str) -> str:
    """Markdown de Claude → el subconjunto HTML que acepta Telegram.

    Telegram NO tiene encabezados ni listas: los encabezados se vuelven negrita
    y las viñetas `-` se vuelven `•`. Orden crítico: los bloques de código se
    apartan ANTES de escapar (su contenido no debe interpretarse), y TODO se
    escapa antes de insertar nuestras propias etiquetas — así el `<b>` que
    venga en el texto del usuario nunca es HTML activo.
    """
    blocks = []

    def _stash(match):
        blocks.append(match.group(1))
        return f"\x00B{len(blocks) - 1}\x00"

    # 1. Apartar bloques ``` ``` (incluye el caso sin cierre por truncado)
    text = re.sub(r"```[\w+-]*\n?(.*?)```", _stash, text, flags=re.S)
    text = re.sub(r"```[\w+-]*\n?(.*)$", _stash, text, flags=re.S)

    # 1b. Apartar tablas ya renderizadas (Telegram no soporta tablas)
    tables = []

    def _stash_table(match):
        tables.append(_render_table(match.group(0)))
        return f"\x00T{len(tables) - 1}\x00"

    text = TABLE_RE.sub(_stash_table, text)

    # 2. Escapar TODO lo que quede
    text = html_mod.escape(text, quote=False)

    # 3. Subconjunto soportado
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)          # código inline
    text = re.sub(r"\*\*([^\n*]+?)\*\*", r"<b>\1</b>", text)          # negrita
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*$", r"<b>\1</b>", text)   # encabezados
    text = re.sub(r"(?m)^(\s*)[-*+]\s+", r"\1• ", text)               # viñetas
    text = re.sub(r"(?m)^\s*(?:---+|===+|\*\*\*+)\s*$", "──────────", text)  # separadores

    # 4. Devolver tablas y bloques (escapando su contenido al insertarlos)
    for i, (rendered, use_pre) in enumerate(tables):
        safe = html_mod.escape(rendered, quote=False)
        if not use_pre:
            # Formato vertical: es texto normal, así que sí admite <code>/<b>
            safe = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", safe)
            safe = re.sub(r"\*\*([^\n*]+?)\*\*", r"<b>\1</b>", safe)
        text = text.replace(f"\x00T{i}\x00", f"<pre>{safe}</pre>" if use_pre else safe)
    for i, block in enumerate(blocks):
        text = text.replace(f"\x00B{i}\x00",
                            f"<pre>{html_mod.escape(block.strip(), quote=False)}</pre>")
    return text


def strip_markdown(text: str) -> str:
    """Texto plano legible (fallback): quita el marcado en vez de mostrarlo crudo."""
    text = TABLE_RE.sub(lambda m: _render_table(m.group(0))[0], text)
    text = re.sub(r"```[\w+-]*\n?", "", text)
    text = re.sub(r"\*\*([^\n*]+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`\n]+)`", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+(.+?)\s*$", r"\1", text)
    text = re.sub(r"(?m)^(\s*)[-*+]\s+", r"\1• ", text)
    return text


def encode_multipart(fields: dict, filename: str, content: bytes) -> tuple:
    """multipart/form-data a mano (solo stdlib, sin requests)."""
    boundary = "----notifyTelegram" + datetime.now().strftime("%Y%m%d%H%M%S%f")
    crlf = b"\r\n"
    body = bytearray()
    for key, value in fields.items():
        body += b"--" + boundary.encode() + crlf
        body += f'Content-Disposition: form-data; name="{key}"'.encode() + crlf + crlf
        body += str(value).encode("utf-8") + crlf
    body += b"--" + boundary.encode() + crlf
    body += (f'Content-Disposition: form-data; name="document"; '
             f'filename="{filename}"').encode("utf-8") + crlf
    body += b"Content-Type: text/markdown; charset=utf-8" + crlf + crlf
    body += content + crlf
    body += b"--" + boundary.encode() + b"--" + crlf
    return bytes(body), f"multipart/form-data; boundary={boundary}"


# ── Llamada a la API (timeout + reintento único) ──────────────────────────
class TelegramHTTPError(Exception):
    """Error HTTP no transitorio; permite reaccionar en vez de abortar."""

    def __init__(self, code: int, detail: str):
        super().__init__(f"HTTP {code}: {detail}")
        self.code = code
        self.detail = detail


def api_call(token: str, method: str, body: bytes, content_type: str,
             raise_http: bool = False) -> dict:
    """POST con timeout y UN reintento ante 429/5xx, respetando Retry-After."""
    url = f"https://api.telegram.org/bot{token}/{method}"

    for attempt in (1, 2):
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))

        except urllib.error.HTTPError as exc:
            detail, retry_after = "", None
            try:
                payload = json.loads(exc.read().decode("utf-8"))
                detail = payload.get("description", "")
                retry_after = (payload.get("parameters") or {}).get("retry_after")
            except Exception:
                pass
            retry_after = retry_after or exc.headers.get("Retry-After")

            transient = exc.code == 429 or 500 <= exc.code < 600
            if transient and attempt == 1:
                wait = int(retry_after) if str(retry_after or "").isdigit() else BACKOFF
                print(f"[notify-telegram] {exc.code} transitorio; reintento en {wait}s",
                      file=sys.stderr)
                time.sleep(wait)
                continue
            if raise_http:
                raise TelegramHTTPError(exc.code, redact(detail or str(exc.reason), token))
            die(redact(f"HTTP {exc.code} en {method}: {detail or exc.reason}", token), 2)

        except urllib.error.URLError as exc:
            if attempt == 1:
                print(f"[notify-telegram] red inestable ({exc.reason}); "
                      f"reintento en {BACKOFF}s", file=sys.stderr)
                time.sleep(BACKOFF)
                continue
            die(redact(f"Sin conexión con la Bot API: {exc.reason}", token), 2)

        except (TimeoutError, OSError) as exc:
            if attempt == 1:
                time.sleep(BACKOFF)
                continue
            die(redact(f"Fallo de red en {method}: {exc}", token), 2)

    die(f"{method} agotó los reintentos", 2)


def check_ok(result: dict, token: str, method: str) -> None:
    if not result.get("ok"):
        die(redact(f"{method} rechazado por Telegram: "
                   f"{result.get('description', result)}", token), 2)


def _message_body(chat_id: str, text: str, parse_mode: str = "") -> bytes:
    fields = {"chat_id": chat_id, "text": text, "disable_web_page_preview": "true"}
    if parse_mode:
        fields["parse_mode"] = parse_mode
    return urllib.parse.urlencode(fields).encode("utf-8")


def send_message(token: str, chat_id: str, text: str, rich: bool = True) -> None:
    """Envía con formato (HTML) y, si Telegram lo rechaza, reenvía en plano.

    El formato es un lujo; que el mensaje LLEGUE no es negociable. Un 400 por
    entidades mal formadas degrada a texto plano en vez de perder el aviso.
    """
    if rich:
        try:
            body = _message_body(chat_id, md_to_telegram_html(text), "HTML")
            check_ok(api_call(token, "sendMessage", body,
                              "application/x-www-form-urlencoded", raise_http=True),
                     token, "sendMessage")
            return
        except TelegramHTTPError as exc:
            if exc.code != 400:
                die(redact(f"HTTP {exc.code} en sendMessage: {exc.detail}", token), 2)
            print(f"[notify-telegram] HTML rechazado ({exc.detail}); envío en texto plano",
                  file=sys.stderr)

    body = _message_body(chat_id, strip_markdown(text) if rich else text)
    check_ok(api_call(token, "sendMessage", body,
                      "application/x-www-form-urlencoded"), token, "sendMessage")


def send_document(token: str, chat_id: str, filename: str, content: bytes) -> None:
    if len(content) > DOC_LIMIT:
        die(f"El adjunto pesa {len(content) // (1024*1024)} MB; el límite es 50 MB.", 1)
    body, content_type = encode_multipart({"chat_id": chat_id}, filename, content)
    check_ok(api_call(token, "sendDocument", body, content_type),
             token, "sendDocument")


def deliver_text(token: str, chat_id: str, text: str, prefix: str = "claude-notify") -> str:
    """Entrega texto respetando el límite de 4096: mensaje suelto, o
    resumen + adjunto .md con el contenido completo.

    Es LA política de entrega del puente: la usan el CLI (T0) y el daemon
    (T1). Devuelve una descripción de lo enviado (para logs).
    """
    if len(text) <= TEXT_LIMIT:
        send_message(token, chat_id, text)
        return f"mensaje de {len(text)} caracteres"

    filename = f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    summary = (f"{text[:SUMMARY_CHARS]}\n"
               f"[...] mensaje de {len(text)} caracteres — completo en {filename}")
    send_message(token, chat_id, summary)
    time.sleep(INTER_MSG_PAUSE)
    send_document(token, chat_id, filename, text.encode("utf-8"))
    return f"resumen + adjunto {filename} ({len(text)} caracteres)"


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")   # Windows: evita mojibake
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        prog="notify_telegram.py",
        description="Envía una notificación a Telegram (vía 1 del puente).")
    parser.add_argument("message", nargs="?",
                        help="Texto a enviar. Si se omite, se lee de stdin.")
    parser.add_argument("--file", metavar="RUTA",
                        help="Adjunta este archivo tras el mensaje.")
    args = parser.parse_args()

    # Mensaje: argumento posicional o stdin (para pipes)
    text = args.message
    if text is None:
        if sys.stdin is None or sys.stdin.isatty():
            die("No hay mensaje: pásalo como argumento o por stdin (pipe).", 1)
        try:
            text = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        except Exception as exc:
            die(f"No se pudo leer stdin: {exc}", 1)
    text = (text or "").strip()
    if not text:
        die("El mensaje está vacío.", 1)

    token, chat_id = get_credentials()

    # Caso 1: adjunto explícito
    if args.file:
        path = Path(args.file)
        if not path.is_file():
            die(f"No existe el archivo a adjuntar: {path}", 1)
        content = path.read_bytes()
        head = text if len(text) <= TEXT_LIMIT else text[:SUMMARY_CHARS] + "\n[...]"
        send_message(token, chat_id, head)
        time.sleep(INTER_MSG_PAUSE)
        send_document(token, chat_id, path.name, content)
        print(f"Enviado: mensaje + adjunto {path.name}")
        return

    # Casos 2 y 3: cabe en un mensaje, o resumen + adjunto (política compartida)
    print(f"Enviado: {deliver_text(token, chat_id, text)}")


if __name__ == "__main__":
    main()
