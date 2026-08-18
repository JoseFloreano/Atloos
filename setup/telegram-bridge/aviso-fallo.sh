#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════
#  aviso-fallo.sh — Manda por Telegram el aviso de que una unidad entro en fallo.
#
#  Lo invoca `claude-telegram-aviso@.service` desde su `OnFailure=`.
#
#  POR QUE UN SCRIPT Y NO UN `ExecStart=/bin/sh -c '...'`. La primera version
#  metia el comando entero en la unit y **no habria parseado**: el mensaje lleva
#  un salto de linea, y en un fichero .service un salto sin `\` de continuacion
#  empieza una directiva nueva. Ademas systemd trata `%` como especificador, asi
#  que cada `%s` de printf habria tenido que ser `%%s`, y `$` va como `$$`. Todo
#  eso son tres formas distintas de escapar en el mismo renglon, sin manera de
#  probarlo hasta que falla en produccion — que es justo cuando este aviso tiene
#  que funcionar. Aqui se prueba con `bash -n` y se corre a mano.
#
#  Uso:  aviso-fallo.sh <unidad>          # p.ej. claude-telegram.service
#        aviso-fallo.sh --prueba          # manda un aviso de mentira y sale
#
#  QUE MANDA, Y QUE NO. Manda el nombre de la unidad, la maquina y las ultimas
#  lineas del journal, que es lo que dice QUE fallo. **No manda entorno**: el
#  aviso viaja a un chat, y uno que filtre credenciales convierte una caida en un
#  incidente. Por eso se lee el journal —que el daemon ya escribe sin tokens— y
#  nunca `systemctl show`, que imprimiria `Environment=`.
# ══════════════════════════════════════════════════════════════════════════
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${AQUI}/../.." && pwd)"

# El argumento PRIMERO: si falta, el fallo es de quien llama y el mensaje tiene
# que decir eso, no hablar del venv. Un diagnostico que nombra la causa
# equivocada manda a mirar donde no es — nos costo un check en el doctor.
UNIDAD="${1:-}"
if [ -z "$UNIDAD" ]; then
  echo "uso: aviso-fallo.sh <unidad> | --prueba" >&2
  exit 2
fi

# El interprete del venv, resuelto y no adivinado: si no arranca, se dice.
VENV="${CLAUDE_TG_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-telegram/venv}"
PY="${VENV}/bin/python"
if [ ! -x "$PY" ]; then
  echo "aviso-fallo: no hay interprete en ${PY}" >&2
  echo "  El aviso NO se pudo mandar. Corre install-deps.sh." >&2
  exit 1
fi

if [ "$UNIDAD" = "--prueba" ]; then
  MENSAJE="$(printf '🧪 Prueba de aviso desde %s\nSi lees esto, el canal funciona. NO ha fallado nada.' "$(hostname)")"
else
  # `|| true`: si journalctl falla, se avisa IGUAL. Un aviso sin detalle vale
  # infinitamente mas que ningun aviso — y aqui `set -e` lo habria matado.
  DETALLE="$(journalctl --user -u "$UNIDAD" -n 20 --no-pager --output cat 2>&1 | tail -c 2000 || true)"
  [ -n "$DETALLE" ] || DETALLE="(sin lineas en el journal)"
  MENSAJE="$(printf '🔴 %s entro en FALLO en %s\n\n%s' "$UNIDAD" "$(hostname)" "$DETALLE")"
fi

exec "$PY" "${REPO}/setup/telegram-bridge/notify_telegram.py" "$MENSAJE"
