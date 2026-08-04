#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  sync-skills.sh — Sincroniza skills desde OneDrive a Claude Code
#                   y empaqueta el plugin dev-skills para Cowork
#
#  Fuente de verdad:  OneDrive/DevSetup/claude-skills/{shared,claude-code,cowork}
#  Destinos Code:     ~/.claude/skills/ + cada ~/.claude-*/skills/ (multi-cuenta)
#  Destino Cowork:    claude-skills/_build/dev-skills(.zip) → Customize→Plugins
#
#  SIEMPRE copia, nunca symlinks (paridad con Windows — hallazgo H8).
#  Solo gestiona las skills que él mismo instaló (manifest _onedrive-sync.json).
#
#  Requiere bash 4+ (macOS trae 3.2: `brew install bash` y ejecutar con ese bash).
#
#  Uso:
#    ./sync-skills.sh                                  # OneDrive en ~/OneDrive
#    ./sync-skills.sh /ruta/a/OneDrive
#    NO_COWORK_BUILD=1 ./sync-skills.sh
# ══════════════════════════════════════════════════════════════

set -euo pipefail
ONEDRIVE="${1:-$HOME/OneDrive}"
# Sin OneDrive → raíz local (modo single-laptop)
if [ ! -d "${ONEDRIVE}" ]; then
  echo "[INFO] OneDrive no encontrado — usando raíz LOCAL (single-laptop): ${HOME}/DevSetup/claude-skills"
  ONEDRIVE="${HOME}"
fi
SKILLS_ROOT="${ONEDRIVE}/DevSetup/claude-skills"
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
info() { echo -e "  ${BLUE}[INFO]${NC} $1"; }

# ── Primera vez: crear estructura y seed desde el repo ────────────────────
if [ ! -d "${SKILLS_ROOT}" ]; then
  info "Creando estructura en ${SKILLS_ROOT}"
  mkdir -p "${SKILLS_ROOT}"/{shared,claude-code,cowork,_template}
  REPO_SKILLS="$(cd "$(dirname "$0")" && pwd)/skills"
  if [ -d "${REPO_SKILLS}" ]; then
    cp -R "${REPO_SKILLS}/." "${SKILLS_ROOT}/"
    ok "Seed inicial copiado desde el repo (${REPO_SKILLS})"
  fi
fi

# ── Recolectar skills (carpetas con SKILL.md); la última categoría gana ───
collect_skills() {  # $@ = categorías en orden de precedencia ascendente
  declare -gA SKILLS=()
  local cat dir d name
  for cat in "$@"; do
    dir="${SKILLS_ROOT}/${cat}"
    [ -d "${dir}" ] || continue
    for d in "${dir}"/*/; do
      [ -f "${d}SKILL.md" ] || continue
      name="$(basename "${d}")"
      SKILLS["${name}"]="${d%/}"
    done
  done
}

# ── 1. Claude Code: shared + claude-code → cada config dir ────────────────
echo -e "\n${BLUE}▶ Sincronizando skills para Claude Code${NC}"
collect_skills shared claude-code

CONFIG_DIRS=("$HOME/.claude")
for d in "$HOME"/.claude-*/; do [ -d "$d" ] && CONFIG_DIRS+=("${d%/}"); done

for cfg in "${CONFIG_DIRS[@]}"; do
  [ -d "${cfg}" ] || continue
  target="${cfg}/skills"
  mkdir -p "${target}"
  manifest="${target}/_onedrive-sync.json"

  # Borrar skills gestionadas que ya no existen en OneDrive
  if [ -f "${manifest}" ] && command -v python3 >/dev/null 2>&1; then
    for old in $(python3 -c "import json;print(' '.join(json.load(open('${manifest}'))['skills']))" 2>/dev/null); do
      if [ -z "${SKILLS[$old]:-}" ]; then
        rm -rf "${target:?}/${old}"
        info "Removida skill obsoleta '${old}' de ${target}"
      fi
    done
  fi

  for name in "${!SKILLS[@]}"; do
    rm -rf "${target:?}/${name}"
    cp -R "${SKILLS[$name]}" "${target}/${name}"
  done

  {
    echo "{\"syncedAt\": \"$(date '+%Y-%m-%d %H:%M')\", \"source\": \"${SKILLS_ROOT}\","
    echo -n "\"skills\": ["
    first=1
    for name in "${!SKILLS[@]}"; do
      [ $first -eq 0 ] && echo -n ", "; echo -n "\"${name}\""; first=0
    done
    echo "]}"
  } > "${manifest}"
  ok "${#SKILLS[@]} skills → ${target}"
done

# ── 1b. Scripts auxiliares → ~/.claude/scripts/ ───────────────────────────
# Las skills (adr-writer, project-resume, vault-drift-audit) invocan
# adr-index.py por ruta absoluta, porque corren desde el cwd de cualquier
# proyecto. Antes esa ruta era la del repo DENTRO de OneDrive: inerte en modo
# single-laptop, y atada al árbol de carpetas de UNA laptop. Ahora la ruta
# estable es ~/.claude/scripts/ y este paso la materializa en cada máquina,
# igual que sync-hooks hace con ~/.claude/hooks/.
SCRIPTS_SOURCE="$(cd "$(dirname "$0")" && pwd)/scripts"
if [ -d "${SCRIPTS_SOURCE}" ]; then
  echo -e "\n${BLUE}▶ Instalando scripts auxiliares${NC}"
  for cfg in "${CONFIG_DIRS[@]}"; do
    mkdir -p "${cfg}/scripts"
    n=0
    for f in "${SCRIPTS_SOURCE}"/*.py; do
      [ -f "$f" ] || continue
      cp "$f" "${cfg}/scripts/"; n=$((n+1))
    done
    ok "${n} scripts → ${cfg}/scripts"
  done
fi

# ── 2. Cowork: empaquetar plugin dev-skills (shared + cowork) ─────────────
if [ -z "${NO_COWORK_BUILD:-}" ]; then
  echo -e "\n${BLUE}▶ Empaquetando plugin dev-skills para Cowork${NC}"
  collect_skills shared cowork

  BUILD="${SKILLS_ROOT}/_build"
  PLUGIN="${BUILD}/dev-skills"
  rm -rf "${PLUGIN}"
  mkdir -p "${PLUGIN}/.claude-plugin" "${PLUGIN}/skills"

  for name in "${!SKILLS[@]}"; do
    cp -R "${SKILLS[$name]}" "${PLUGIN}/skills/${name}"
  done

  cat > "${PLUGIN}/.claude-plugin/plugin.json" << EOF
{
  "name": "dev-skills",
  "description": "Skills personales de desarrollo (sincronizadas desde OneDrive/DevSetup/claude-skills)",
  "version": "$(date '+%Y.%m.%d')"
}
EOF

  if command -v zip >/dev/null 2>&1; then
    rm -f "${BUILD}/dev-skills.zip"
    # Doc 11 (B3/estructura): el plugin root va en la RAÍZ del zip, sin carpeta
    # envolvente — Cowork rechaza el zip con wrapper "dev-skills/".
    (cd "${PLUGIN}" && zip -qr "${BUILD}/dev-skills.zip" .)
    ok "${#SKILLS[@]} skills → ${BUILD}/dev-skills.zip"
  else
    ok "${#SKILLS[@]} skills → ${PLUGIN}/ (instala 'zip' para generar el .zip)"
  fi
  info "Instalar/actualizar en Cowork: desktop app → Customize → Plugins → subir dev-skills.zip"
fi

echo -e "\n${GREEN}Listo. Las sesiones nuevas de Claude Code ya ven las skills.${NC}"
