#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  sync-hooks.sh — Instala/sincroniza los hooks de Claude Code (Linux/macOS).
#
#  Gemelo de sync-hooks.ps1. Hasta el sprint 11 este fichero NO EXISTÍA: los
#  hooks solo se podían instalar desde PowerShell, así que en la SER8 —la
#  máquina que corre sin vigilancia humana— no existían merge-gate-guard,
#  goal-evidence-guard, check-vault-updated, memory-flush ni mark-code-dirty.
#
#  UNA FUENTE, DOS ENVOLTORIOS. La lista de hooks NO está aquí: está en
#  setup/hooks/hooks-map.json, que leen los dos. Este script es una cáscara —
#  resuelve el intérprete y delega en setup/scripts/wire-hooks.py. Que los dos
#  envoltorios registren lo MISMO lo vigila
#  setup/scripts/tests/test-sync-hooks-paridad.py.
#
#  Uso:
#    bash setup/sync-hooks.sh                 # copia + cablea settings.json
#    bash setup/sync-hooks.sh --no-wire       # solo copia los .py
#    bash setup/sync-hooks.sh --prune         # poda los hooks retirados
#    bash setup/sync-hooks.sh --config-dir D  # laboratorio (arneses)
# ══════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RESOLUTOR="${SCRIPT_DIR}/scripts/py"
NUCLEO="${SCRIPT_DIR}/scripts/wire-hooks.py"

[ -f "$NUCLEO" ] || { echo "sync-hooks.sh: falta $NUCLEO" >&2; exit 1; }
[ -f "$RESOLUTOR" ] || { echo "sync-hooks.sh: falta $RESOLUTOR" >&2; exit 1; }

# El intérprete se resuelve EJECUTÁNDOLO, no mirando el PATH: en Windows
# `python3` existe como alias del Store y miente. Ver setup/scripts/py.
exec bash "$RESOLUTOR" "$NUCLEO" --hooks-source "${SCRIPT_DIR}/hooks" "$@"
