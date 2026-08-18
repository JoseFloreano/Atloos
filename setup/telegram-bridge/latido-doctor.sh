#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════
#  latido-doctor.sh — Corre el doctor y avisa SOLO si hay divergencia.
#
#  Lo invoca `claude-telegram-doctor.service`, disparado por su timer diario.
#
#  LA REGLA QUE LO GOBIERNA: **calla cuando todo esta bien.** Un aviso diario que
#  siempre dice «todo bien» se deja de leer en una semana — la misma enfermedad
#  que la suite que nunca esta verde, y este repo la lleva persiguiendo doce
#  sprints. Por eso el envio cuelga del exit code del doctor.
#
#  Cubre lo que el `OnFailure` NO ve, que es casi todo lo que mata despacio a una
#  maquina headless: el disco llenandose, el journal sin techo, un CLAUDE.md que
#  se quedo atras, y la exencion del suelo que caduca sin que nadie mire.
#
#  Uso:  latido-doctor.sh              # calla si no hay divergencia
#        latido-doctor.sh --siempre    # manda el informe pase lo que pase
# ══════════════════════════════════════════════════════════════════════════
set -uo pipefail          # SIN -e: el exit != 0 del doctor es el mecanismo

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${AQUI}/../.." && pwd)"
VENV="${CLAUDE_TG_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-telegram/venv}"
PY="${VENV}/bin/python"

# El nombre del fichero ES el nombre del adjunto que llega al movil
# (notify_telegram.py usa `path.name`). Un `tmp.AbC123` en el chat es la
# friccion que hace que dejes de abrir el aviso, asi que se nombra.
DIR="$(mktemp -d)"
SALIDA="${DIR}/doctor-$(hostname)-$(date +%Y%m%d-%H%M).txt"
trap 'rm -rf "$DIR"' EXIT

# El doctor se corre UNA vez y se guarda su salida. Correrlo otra vez para el
# mensaje podria dar un veredicto distinto y mandarias el que no fue — es la
# misma regla que la del exit code sin tuberia.
"${REPO}/setup/scripts/py" "${REPO}/setup/scripts/doctor.py" --breve > "$SALIDA" 2>&1
RC=$?

if [ "$RC" -eq 0 ] && [ "${1:-}" != "--siempre" ]; then
  echo "latido: doctor sin divergencias (exit 0), no se avisa"
  exit 0
fi

if [ ! -x "$PY" ]; then
  echo "latido: HAY divergencias y NO se pudo avisar: no hay interprete en ${PY}" >&2
  cat "$SALIDA" >&2
  exit 1
fi

TITULO="🩺 doctor en $(hostname): $( [ "$RC" -eq 0 ] && echo 'sin divergencias' || echo 'HAY divergencias' )"
"$PY" "${REPO}/setup/telegram-bridge/notify_telegram.py" "$TITULO" --file "$SALIDA"
