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
#    PRUNE=1 ./sync-skills.sh        # y SOLO entonces borra las huerfanas
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
  manifest_tmp="${manifest}.tmp"

  # ── Guard por CONJUNTOS, no por conteos (RFD 10 C1) ─────────────────────
  # utf-8-sig al leer: el manifest lo puede haber escrito sync-skills.ps1, y
  # PS 5.1 le mete BOM — sin esto json.load revienta y el guard no corre.
  PREVIAS=""
  if [ -f "${manifest}" ] && command -v python3 >/dev/null 2>&1; then
    PREVIAS=$(python3 -c "import json;print(' '.join(json.load(open('${manifest}', encoding='utf-8-sig'))['skills']))" 2>/dev/null || echo "")
  fi
  faltantes() { local f=""; for o in ${PREVIAS}; do [ -z "${SKILLS[$o]:-}" ] && f="${f} ${o}"; done; echo "${f# }"; }
  FALTAN=$(faltantes)

  # Reintento unico: cubre el flush pendiente tras un reset --hard, que es
  # cuando muchas carpetas de la fuente se reescriben a la vez.
  if [ -n "${FALTAN}" ]; then
    echo -e "  ${YELLOW}[WARN]${NC} Faltan skills del manifest — releyendo la fuente…"
    sleep 0.4
    collect_skills shared claude-code
    FALTAN=$(faltantes)
  fi

  if [ -n "${FALTAN}" ]; then
    if [ -z "${PRUNE:-}" ]; then
      # NO se borra nada: una enumeracion corta es indistinguible de una
      # retirada real. Se GRITA en cada corrida para que la huerfana no se
      # acumule en silencio pagando su description en cada sesion.
      echo -e "  ${RED}[HUERFANAS]${NC} instaladas y NO en la fuente:"
      for f in ${FALTAN}; do echo -e "      ${RED}- ${f}${NC}"; done
      echo -e "  ${YELLOW}Si las retiraste a proposito:  PRUNE=1 ./setup/sync-skills.sh${NC}"
      echo -e "  ${YELLOW}Si NO las retiraste, es enumeracion parcial: NO uses PRUNE.${NC}"
    else
      for f in ${FALTAN}; do rm -rf "${target:?}/${f}"; info "Podada skill retirada '${f}'"; done
    fi
  fi

  # .tmp -> rm -> mv. ENCOGE la ventana destructiva, no la elimina: sigue
  # habiendo un rm antes del mv. Lo que se gana es que la copia ya termino
  # cuando se borra; si el script muere en medio, el contenido esta en
  # "<skill>.tmp" al lado y se recupera renombrando.
  for name in "${!SKILLS[@]}"; do
    rm -rf "${target:?}/${name}.tmp"
    cp -R "${SKILLS[$name]}" "${target}/${name}.tmp"
    rm -rf "${target:?}/${name}"
    mv "${target}/${name}.tmp" "${target}/${name}"
  done

  {
    echo "{\"syncedAt\": \"$(date '+%Y-%m-%d %H:%M')\", \"source\": \"${SKILLS_ROOT}\","
    echo -n "\"skills\": ["
    first=1
    for name in "${!SKILLS[@]}"; do
      [ $first -eq 0 ] && echo -n ", "; echo -n "\"${name}\""; first=0
    done
    echo "]}"
  } > "${manifest_tmp}"
  # Si quedaron huerfanas sin podar, NO se reescribe el manifest: si se
  # reescribiera, la proxima corrida ya no recordaria que existieron.
  if [ -z "${FALTAN}" ] || [ -n "${PRUNE:-}" ]; then
    mv "${manifest_tmp}" "${manifest}"
  else
    rm -f "${manifest_tmp}"
    echo -e "  ${YELLOW}[WARN]${NC} Manifest NO actualizado: sigue recordando las huerfanas."
  fi
  NPREV=$(echo ${PREVIAS} | wc -w)
  ok "${#SKILLS[@]} skills → ${target}  (manifest: ${NPREV})"
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
