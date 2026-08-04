#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  sync-skills.sh — Instala las skills del REPO en Claude Code
#                   y empaqueta el plugin dev-skills para Cowork
#
#  Fuente ÚNICA:      setup/skills/{shared,claude-code,cowork} de este repo.
#                     El script vive en setup/, así que la resuelve sola: cero
#                     configuración, y funciona igual con OneDrive o sin él.
#  Destinos Code:     ~/.claude/skills/ + cada ~/.claude-*/skills/ (multi-cuenta)
#  Destino Cowork:    setup/_build/dev-skills.zip → Customize→Plugins
#
#  El espejo OneDrive/DevSetup/claude-skills se RETIRÓ (ADR-20260803-skills-
#  fuente-unica): eran dos fuentes de verdad, y el espejo se quedaba atrás sin
#  que nadie lo notara. Ahora los cambios se revisan por diff en git.
#
#  SIEMPRE copia, nunca symlinks (paridad con Windows — hallazgo H8).
#  Solo gestiona las skills que él mismo instaló (manifest _onedrive-sync.json).
#
#  Requiere bash 4+ (macOS trae 3.2: `brew install bash` y ejecutar con ese bash).
#
#  Uso:
#    ./sync-skills.sh
#    NO_COWORK_BUILD=1 ./sync-skills.sh
# ══════════════════════════════════════════════════════════════

set -euo pipefail
SETUP_DIR="$(cd "$(dirname "$0")" && pwd)"
GREEN='[0;32m'; YELLOW='[1;33m'; BLUE='[0;34m'; RED='[0;31m'; NC='[0m'
ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
info() { echo -e "  ${BLUE}[INFO]${NC} $1"; }

# ── La fuente es el repo: este script vive en setup/ ──────────────────────
# Sin argumento ni variable de entorno a propósito. Un interruptor para elegir
# fuente es lo que mantenía vivas las dos, y había que acordarse de usarlo.
SKILLS_ROOT="${SETUP_DIR}/skills"
if [ ! -d "${SKILLS_ROOT}" ]; then
  echo -e "  ${RED}[ERROR]${NC} No encuentro ${SKILLS_ROOT}."
  echo -e "  ${RED}       ${NC} Corre este script desde el repo ClaudeSetup (setup/sync-skills.sh)."
  exit 1
fi
info "Fuente: ${SKILLS_ROOT}"

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

  # Borrar skills gestionadas que ya no existen en la fuente.
  # utf-8-sig al leer: el manifest lo puede haber escrito sync-skills.ps1, y
  # PS 5.1 le mete BOM — sin esto json.load revienta y la limpieza no corre.
  if [ -f "${manifest}" ] && command -v python3 >/dev/null 2>&1; then
    for old in $(python3 -c "import json;print(' '.join(json.load(open('${manifest}', encoding='utf-8-sig'))['skills']))" 2>/dev/null); do
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
SCRIPTS_SOURCE="${SETUP_DIR}/scripts"
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

  BUILD="${SETUP_DIR}/_build"   # artefacto: gitignorado
  PLUGIN="${BUILD}/dev-skills"
  rm -rf "${PLUGIN}"
  mkdir -p "${PLUGIN}/.claude-plugin" "${PLUGIN}/skills"

  for name in "${!SKILLS[@]}"; do
    cp -R "${SKILLS[$name]}" "${PLUGIN}/skills/${name}"
  done

  cat > "${PLUGIN}/.claude-plugin/plugin.json" << EOF
{
  "name": "dev-skills",
  "description": "Skills personales de desarrollo (fuente: setup/skills del repo ClaudeSetup)",
  "version": "$(date '+%Y.%m.%d')"
}
EOF

  if command -v zip >/dev/null 2>&1; then
    rm -f "${BUILD}/dev-skills.zip"
    # B3 (instalacion single-laptop): el plugin root va en la RAÍZ del zip, sin carpeta
    # envolvente — Cowork rechaza el zip con wrapper "dev-skills/".
    (cd "${PLUGIN}" && zip -qr "${BUILD}/dev-skills.zip" .)
    ok "${#SKILLS[@]} skills → ${BUILD}/dev-skills.zip"
  else
    ok "${#SKILLS[@]} skills → ${PLUGIN}/ (instala 'zip' para generar el .zip)"
  fi
  info "Instalar/actualizar en Cowork: desktop app → Customize → Plugins → subir dev-skills.zip"
fi

echo -e "\n${GREEN}Listo. Las sesiones nuevas de Claude Code ya ven las skills.${NC}"
