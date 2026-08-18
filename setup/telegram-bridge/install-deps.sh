#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  install-deps.sh — Dependencias del puente en Linux, en un venv.
#
#  POR QUE UN VENV Y NO `pip install`. En Ubuntu 24.04 (la SER8) un `pip
#  install` pelado falla con `externally-managed-environment` (PEP 668), y la
#  salida facil —`--break-system-packages`— ensucia el Python del sistema en
#  una maquina que corre sin vigilancia. El repo no traia `requirements.txt` y
#  la unica pista era un mensaje de error que decia `py -m pip install`, un
#  comando que en Linux NO EXISTE. Auditoria 31, H3b.
#
#  POR QUE FUERA DEL REPO. Este repo vive bajo OneDrive. Un `.venv` dentro se
#  sincronizaria entre maquinas con binarios de otra plataforma — es la misma
#  razon por la que los worktrees se sacaron de aqui (ADR 2026-08-05). La raiz
#  por defecto es la misma que ya usa `gitops.worktrees_root()` como fallback
#  Unix: `$XDG_DATA_HOME` o `~/.local/share`.
#
#  NO hay gemelo .ps1 a proposito: en Windows no hay PEP 668 y basta la linea
#  del README. Este repo ya tiene un caso de una cabecera prometiendo dos
#  envoltorios donde solo habia uno; no se anade otro.
#
#  Uso:
#    bash setup/telegram-bridge/install-deps.sh          # crea/actualiza
#    CLAUDE_TG_VENV=/otra/ruta bash .../install-deps.sh  # raiz alternativa
#
#  Sale != 0 si no deja el puente importable. Idempotente.
# ══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQS="${SCRIPT_DIR}/requirements.txt"
VENV="${CLAUDE_TG_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-telegram/venv}"
SUELO_MAYOR=3
SUELO_MENOR=10

[ -f "$REQS" ] || { echo "install-deps.sh: falta $REQS" >&2; exit 1; }

# El interprete se comprueba EJECUTANDOLO, no mirando el PATH: es la regla de
# setup/scripts/py, y viene de que en Windows `python3` existe como alias del
# Store y miente. Aqui ademas se exige el suelo del repo.
PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1 &&
     "$cand" -c "import sys; sys.exit(0 if sys.version_info[:2] >= ($SUELO_MAYOR, $SUELO_MENOR) else 1)" 2>/dev/null; then
    PY="$cand"; break
  fi
done
if [ -z "$PY" ]; then
  echo "install-deps.sh: no hay un Python >= ${SUELO_MAYOR}.${SUELO_MENOR} que arranque" >&2
  # Este es el camino de LINUX. En la Legion pasa justo esto: `python3` y
  # `python` existen como alias del Store y mienten, asi que el script se niega
  # en vez de fabricar un venv roto. El aviso va aqui, que es donde se lee.
  echo "  Si estas en Windows, el camino es otro:" >&2
  echo "    py -m pip install -r setup/telegram-bridge/requirements.txt" >&2
  exit 1
fi
echo "  [INFO] interprete base: $("$PY" -c 'import sys; print(sys.executable, sys.version.split()[0])')"

# La guarda mira que el venv SIRVA, no que exista. Medido en la SER8 el
# 2026-08-17: cuando falta `python3-venv`, `python3 -m venv` deja el directorio
# a medias —los symlinks de bin/python puestos, ensurepip caido, sin pip ni
# pyvenv.cfg util— y sale != 0. Con `[ -x bin/python ]` a secas eso pasa por
# "venv ya existe", y TODA corrida posterior muere abajo en `-m pip` con
# `No module named pip`, que no nombra la causa ni la cura. El script dejaba de
# ser idempotente justo despues del fallo que el propio script diagnostica.
if [ -x "${VENV}/bin/python" ] && ! "${VENV}/bin/python" -m pip --version >/dev/null 2>&1; then
  # Se borra solo si de verdad parece un venv, no lo que apunte $CLAUDE_TG_VENV.
  if [ -f "${VENV}/pyvenv.cfg" ] || [ -x "${VENV}/bin/python" ]; then
    echo "  [INFO] el venv de ${VENV} existe pero no tiene pip (creacion a medias): lo rehago"
    rm -rf "${VENV}"
  fi
fi

if [ ! -x "${VENV}/bin/python" ]; then
  echo "  [INFO] creando venv en ${VENV}"
  # `python3 -m venv` puede faltar en Debian/Ubuntu: viene en python3-venv.
  if ! "$PY" -m venv "$VENV" 2>/tmp/venv-err.$$; then
    echo "  [ERROR] no se pudo crear el venv:" >&2
    cat /tmp/venv-err.$$ >&2 || true
    rm -f /tmp/venv-err.$$
    echo "  En Debian/Ubuntu suele faltar el paquete:  sudo apt install python3-venv" >&2
    exit 1
  fi
  rm -f /tmp/venv-err.$$
else
  echo "  [INFO] venv ya existe: ${VENV}"
fi

"${VENV}/bin/python" -m pip install --quiet --upgrade pip
"${VENV}/bin/python" -m pip install --quiet -r "$REQS"

# Y la prueba de que quedo instalado es IMPORTARLO. Un pip que sale 0 no es
# evidencia de que el daemon arranque: es la ley uno de la casa, aplicada aqui.
VERSION="$("${VENV}/bin/python" - <<'PY'
try:
    import telegram
    print(telegram.__version__)
except Exception as e:
    print(f"FALLO: {type(e).__name__}: {e}")
PY
)"
case "$VERSION" in
  FALLO*) echo "  [ERROR] el puente sigue sin poder importar telegram — ${VERSION}" >&2
          exit 1 ;;
esac

echo "  [OK] python-telegram-bot ${VERSION} instalado en el venv"
echo ""
echo "Listo. Para arrancar el daemon a mano:"
echo "  ${VENV}/bin/python ${SCRIPT_DIR}/tg_daemon.py"
echo ""
echo "Esa es la ruta del interprete que necesita la unit de systemd (ExecStart)."
