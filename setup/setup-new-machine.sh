#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  setup-new-machine.sh — Bootstrap Graphiti en laptop nueva (macOS/Linux)
#
#  ESTRATEGIA A REAL (fix auditoría A1): datos vivos en disco LOCAL
#  (~/.local/share/graphiti), la raíz de sync SOLO recibe backups terminados.
#  El .env con API keys también vive LOCAL (fix A4 — nunca en OneDrive).
#
#  Prerequisitos: Docker Desktop corriendo, claude CLI. OneDrive es opcional.
#
#  Uso:
#    bash setup-new-machine.sh                   # OneDrive en ~/OneDrive
#    bash setup-new-machine.sh /ruta/a/OneDrive  # path explícito
#    LOCAL=1 bash setup-new-machine.sh           # single-laptop, sin OneDrive
#    FORCE_ONEDRIVE=1 bash setup-new-machine.sh  # escape hatch Estrategia B
# ══════════════════════════════════════════════════════════════

set -euo pipefail
ONEDRIVE="${1:-$HOME/OneDrive}"

# ── Modo de sincronización ────────────────────────────────────────────────
# multi-laptop (default): DevSetup vive en OneDrive → skills/backups viajan solos.
# single-laptop (LOCAL=1 o sin OneDrive): DevSetup vive en ~/DevSetup.
#   Todo lo demás es idéntico; la durabilidad extra la da el remote git del vault.
if [ -n "${LOCAL:-}" ] || [ ! -d "${ONEDRIVE}" ]; then
  [ -d "${ONEDRIVE}" ] || echo "[INFO] OneDrive no encontrado en ${ONEDRIVE} — modo LOCAL (single-laptop)."
  ONEDRIVE="$HOME"
  LOCAL=1
fi
SYNC_MODE=$([ -n "${LOCAL:-}" ] && echo "single-laptop (local, sin OneDrive)" || echo "multi-laptop (OneDrive)")
DEVSETUP="${ONEDRIVE}/DevSetup"
GRAPHITI_LOCAL="${GRAPHITI_LOCAL:-$HOME/.local/share/graphiti}"   # datos + config + .env + scripts (LOCAL)
BACKUP_DIR="${DEVSETUP}/graphiti-data/backups"                     # lo ÚNICO de Graphiti en la raíz de sync
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WARNINGS=()

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'; BOLD='\033[1m'
header() { echo -e "\n${BLUE}${BOLD}▶ $1${NC}"; }
ok()     { echo -e "  ${GREEN}[OK]${NC} $1"; }
warn()   { echo -e "  ${YELLOW}[WARN]${NC} $1"; WARNINGS+=("$1"); }
err()    { echo -e "  ${RED}[ERR]${NC} $1"; }
info()   { echo -e "  ${BLUE}[INFO]${NC} $1"; }

echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD} Graphiti + FalkorDB — Setup (Estrategia A)${NC}"
echo -e "${BOLD} Modo          : ${SYNC_MODE}${NC}"
echo -e "${BOLD} Datos locales : ${GRAPHITI_LOCAL}${NC}"
echo -e "${BOLD} Backups       : ${BACKUP_DIR}${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"

# ── 1. Verificar dependencias ──────────────────────────────────────────────
header "Verificando dependencias"
ERRORS=0
command -v docker >/dev/null 2>&1 && ok "Docker instalado" || { err "Docker no encontrado."; ERRORS=$((ERRORS+1)); }
docker compose version >/dev/null 2>&1 && ok "Docker Compose disponible" || { err "Docker Compose no disponible."; ERRORS=$((ERRORS+1)); }
[ -d "${DEVSETUP}" ] || { warn "No se encontró ${DEVSETUP}. Creando..."; mkdir -p "${DEVSETUP}"; }
[ $ERRORS -gt 0 ] && { err "Hay $ERRORS errores críticos."; exit 1; }

# Guardia anti-OneDrive (fix A1)
case "${GRAPHITI_LOCAL}" in
  *OneDrive*)
    if [ -z "${FORCE_ONEDRIVE:-}" ]; then
      err "GRAPHITI_LOCAL apunta dentro de OneDrive — prohibido (H2, corrupción silenciosa)."
      err "Usa FORCE_ONEDRIVE=1 solo si sabes lo que haces (Estrategia B)."
      exit 1
    fi ;;
esac

# ── 2. Crear directorios ───────────────────────────────────────────────────
header "Creando directorios"
mkdir -p "${GRAPHITI_LOCAL}"/{data,config,scripts}
mkdir -p "${BACKUP_DIR}"
ok "Local:   ${GRAPHITI_LOCAL}/{data,config,scripts}"
ok "Backups: ${BACKUP_DIR} (solo snapshots)"

# ── 3. Instalar compose, config y scripts (fix A2) ────────────────────────
header "Instalando archivos"
DOTFILES="${DEVSETUP}/claude-dotfiles/graphiti"
install_file() {  # $1 nombre, $2 destino
  local src
  for src in "${SCRIPT_DIR}" "${DOTFILES}"; do
    if [ -f "${src}/$1" ]; then
      cp "${src}/$1" "$2"
      ok "$1 instalado"
      return 0
    fi
  done
  warn "$1 no encontrado (busqué en ${SCRIPT_DIR} y ${DOTFILES}). Cópialo manualmente."
  return 1
}
install_file "docker-compose.yml" "${GRAPHITI_LOCAL}/" || true
install_file "config.yaml"        "${GRAPHITI_LOCAL}/config/" || true
HAS_BACKUP=true;  install_file "backup-graph.sh"  "${GRAPHITI_LOCAL}/scripts/" || HAS_BACKUP=false
HAS_RESTORE=true; install_file "restore-graph.sh" "${GRAPHITI_LOCAL}/scripts/" || HAS_RESTORE=false
chmod +x "${GRAPHITI_LOCAL}/scripts/"*.sh 2>/dev/null || true

# ── 4. Crear .env LOCAL (fix A4: API keys nunca en OneDrive) ──────────────
header "Creando .env (local, fuera de OneDrive)"
ENV_FILE="${GRAPHITI_LOCAL}/.env"
if [ -f "${ENV_FILE}" ]; then
  info ".env ya existe. No sobreescrito."
else
  info "Pin de versiones (auditoría A5). Consulta el tag estable actual con:"
  info "  docker pull falkordb/falkordb:latest ; docker image ls falkordb/falkordb"
  read -rp "  FALKORDB_VERSION (tag concreto, ej. v4.2.1 — vacío = decidir después): " FK_VER
  read -rp "  GRAPHITI_MCP_VERSION (tag concreto — vacío = decidir después): " MCP_VER
  cat > "${ENV_FILE}" << ENVEOF
# Auto-generado por setup-new-machine.sh en $(hostname) — $(date)
# UBICACIÓN LOCAL A PROPÓSITO: contiene API keys (auditoría A4).

# Estrategia A: datos vivos LOCALES, backups a la raíz de sync
FALKORDB_DATA_PATH=${GRAPHITI_LOCAL}/data
CONFIG_PATH=${GRAPHITI_LOCAL}/config
BACKUP_DIR=${BACKUP_DIR}

# Pins de versión (OBLIGATORIOS — el compose no arranca sin ellos)
FALKORDB_VERSION=${FK_VER}
GRAPHITI_MCP_VERSION=${MCP_VER}

# Extracción de entidades — 3 rutas (detalle en .env.example del repo):
#  openai = pago, óptima | gemini = GRATIS (recomendada sin costo) | groq = gratis, TPM bajo
# La key del provider elegido es obligatoria. Nunca anthropic/haiku (H7).
LLM_PROVIDER=openai
OPENAI_API_KEY=
GOOGLE_API_KEY=
GROQ_API_KEY=
ANTHROPIC_API_KEY=
MODEL_NAME=gpt-4.1-mini
SMALL_MODEL_NAME=gpt-4.1-nano
# Ruta gemini: LLM_PROVIDER=gemini + GOOGLE_API_KEY + MODEL_NAME=gemini-2.0-flash
#   (y en config.yaml cambia el embedder a gemini o sentence_transformers)
# Ruta groq:   LLM_PROVIDER=groq + GROQ_API_KEY + MODEL_NAME=llama-3.3-70b-versatile
#   + SEMAPHORE_LIMIT=2 (free tier ~6k tokens/min)

FALKORDB_PASSWORD=
SEMAPHORE_LIMIT=3
ENVEOF
  ok ".env creado en ${ENV_FILE}"
  warn "Edita el .env: la key del provider elegido (LLM_PROVIDER) es obligatoria."
  read -rp "  ¿Editar .env ahora? [y/N] " EDIT
  [[ "${EDIT:-N}" =~ ^[Yy]$ ]] && "${EDITOR:-nano}" "${ENV_FILE}"
fi

# Validación fail-fast de lo obligatorio (key según el provider elegido)
ENV_READY=true
PROVIDER=$(grep -E '^LLM_PROVIDER=' "${ENV_FILE}" | tail -1 | cut -d= -f2)
case "${PROVIDER:-openai}" in
  gemini)    KEYVAR="GOOGLE_API_KEY" ;;
  groq)      KEYVAR="GROQ_API_KEY" ;;
  anthropic) KEYVAR="ANTHROPIC_API_KEY"
             warn "LLM_PROVIDER=anthropic: structured output experimental (H7) — usa openai o gemini." ;;
  *)         KEYVAR="OPENAI_API_KEY" ;;
esac
for REQ in "${KEYVAR}" FALKORDB_VERSION GRAPHITI_MCP_VERSION; do
  if grep -qE "^${REQ}=\s*$" "${ENV_FILE}"; then
    warn "${REQ} está vacío en .env (LLM_PROVIDER=${PROVIDER:-openai}) — el stack NO se levantará hasta llenarlo."
    ENV_READY=false
  fi
done
if grep -qE "^FALKORDB_DATA_PATH=.*OneDrive" "${ENV_FILE}" && [ -z "${FORCE_ONEDRIVE:-}" ]; then
  err "FALKORDB_DATA_PATH apunta a OneDrive — prohibido (H2)."
  exit 1
fi

# ── 4b. Esqueletos de .env por servicio (registro en setup/README.md) ─────
# UN .env POR SERVICIO a propósito: `docker --env-file` inyecta el archivo
# ENTERO en el contenedor, así que un .env único le daría al MCP las
# credenciales del bot y viceversa. En Debian esto mapea 1:1 a EnvironmentFile=
# de systemd, una unit por servicio (ADR-20260801-os-servidor-24-7).
#
# REGLA CRÍTICA: si el archivo ya existe NO se toca — ni se sobreescribe ni se
# "completa". Este bootstrap se re-corre en máquinas que YA tienen secretos
# reales dentro; rozarlos sería destruirlos.
header "Esqueletos de .env por servicio"

TELEGRAM_ENV="${HOME}/.config/claude-telegram/.env"

# graphiti: normalmente ya lo creó el paso 4; este bloque es la red de seguridad.
mkdir -p "$(dirname "${ENV_FILE}")"
if [ -f "${ENV_FILE}" ]; then
  info "graphiti: .env ya existe — NO se toca (${ENV_FILE})"
else
  cat > "${ENV_FILE}" << 'ENVSKEL'
# Esqueleto creado por setup-new-machine.sh. Rellena y guarda.
# Registro de secretos (rutas, quién lo consume, cómo rotar): setup/README.md
# NUNCA muevas este archivo a OneDrive ni lo versiones (anti-patrón S5 / fix A4).
LLM_PROVIDER=openai
DEEPSEEK_API_KEY=
DEEPSEEK_API_URL=https://api.deepseek.com/v1
OPENAI_API_KEY=
MODEL_NAME=deepseek-chat
SMALL_MODEL_NAME=deepseek-chat
LLM_STRUCTURED_OUTPUT_MODE=json_object
FALKORDB_PASSWORD=
SEMAPHORE_LIMIT=3
ENVSKEL
  chmod 600 "${ENV_FILE}"
  ok "graphiti: esqueleto creado en ${ENV_FILE}"
  warn "graphiti: rellena sus llaves — ver 'Registro de secretos' en setup/README.md"
fi

mkdir -p "$(dirname "${TELEGRAM_ENV}")"
if [ -f "${TELEGRAM_ENV}" ]; then
  info "claude-telegram: .env ya existe — NO se toca (${TELEGRAM_ENV})"
else
  cat > "${TELEGRAM_ENV}" << 'ENVSKEL'
# Esqueleto creado por setup-new-machine.sh. Rellena y guarda.
# Registro de secretos (rutas, quién lo consume, cómo rotar): setup/README.md
# Token: @BotFather. Rotar = /revoke (invalida el viejo al instante).
# NUNCA muevas este archivo a OneDrive ni lo versiones (anti-patrón S5 / fix A4).
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_ALLOWED_USER_ID=
ENVSKEL
  chmod 600 "${TELEGRAM_ENV}"
  ok "claude-telegram: esqueleto creado en ${TELEGRAM_ENV}"
  warn "claude-telegram: rellena sus llaves — ver 'Registro de secretos' en setup/README.md"
fi

# ── 5. Agregar Graphiti al MCP de Claude Code ────────────────────────────
header "Configurando MCP en Claude Code"
if command -v claude >/dev/null 2>&1; then
  if claude mcp list 2>/dev/null | grep -q "graphiti"; then
    ok "MCP 'graphiti-memory' ya configurado"
  else
    claude mcp add --transport http graphiti-memory "http://localhost:8000/mcp/" -s user 2>/dev/null && \
      ok "MCP graphiti-memory agregado (scope: user)" || \
      warn "Agrega manualmente: claude mcp add --transport http graphiti-memory http://localhost:8000/mcp/ -s user"
  fi
else
  warn "Claude Code CLI no encontrado. Agrega el MCP manualmente."
fi

# ── 5b. Sincronizar skills (raíz de sync → Claude Code + plugin Cowork) ───
header "Sincronizando skills"
if [ -f "${SCRIPT_DIR}/sync-skills.sh" ]; then
  bash "${SCRIPT_DIR}/sync-skills.sh" || warn "sync-skills falló; córrelo manualmente."
else
  warn "sync-skills.sh no encontrado junto a este script."
fi

# ── 5c. Sincronizar HOOKS (sprint 11) ─────────────────────────────────────
# Antes del sprint 11 este paso no existía y sync-hooks solo hablaba PowerShell:
# una máquina Linux salía de aquí con las skills puestas y SIN capa 3 —sin
# merge-gate-guard, sin goal-evidence-guard, sin check-vault-updated—, que es
# justo lo que hace falta en un servidor que corre sin nadie delante.
# Los hooks son OTRO mecanismo que las skills: por eso es su propio script.
header "Sincronizando hooks"
if [ -f "${SCRIPT_DIR}/sync-hooks.sh" ]; then
  bash "${SCRIPT_DIR}/sync-hooks.sh" || warn "sync-hooks falló; córrelo manualmente."
else
  warn "sync-hooks.sh no encontrado junto a este script: la máquina queda SIN hooks."
  WARNINGS+=("CRÍTICO: sin hooks instalados (no hay compuerta de merge)")
fi

# ── 6. Restaurar backup (fix A3: SOLO via restore-graph, AOF-safe) ────────
header "Verificando backups existentes"
STACK_UP=false
LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/*.rdb 2>/dev/null | head -1 || echo "")
if [ -n "${LATEST_BACKUP}" ]; then
  info "Backup encontrado: $(basename "${LATEST_BACKUP}")"
  if [ "${HAS_RESTORE}" = true ] && [ "${ENV_READY}" = true ]; then
    read -rp "  ¿Restaurar con restore-graph.sh (verifica que los datos carguen)? [y/N] " RESTORE
    if [[ "${RESTORE:-N}" =~ ^[Yy]$ ]]; then
      GRAPHITI_LOCAL="${GRAPHITI_LOCAL}" bash "${GRAPHITI_LOCAL}/scripts/restore-graph.sh" "${LATEST_BACKUP}" && STACK_UP=true
    fi
  else
    warn "Restore pospuesto (falta restore-graph.sh o el .env está incompleto)."
    warn "NUNCA copies dump.rdb a mano: con AOF activo no restaura nada (A3)."
  fi
else
  info "No hay backups previos. Se iniciará con grafo vacío."
fi

# ── 7. Levantar containers ────────────────────────────────────────────────
if [ "${STACK_UP}" = false ]; then
  header "Levantando Docker containers"
  if [ "${ENV_READY}" = true ]; then
    docker compose --env-file "${ENV_FILE}" -f "${GRAPHITI_LOCAL}/docker-compose.yml" up -d \
      && { ok "Containers levantados"; STACK_UP=true; } \
      || err "Error al levantar containers."
  else
    warn "Stack NO levantado: completa el .env y corre:"
    info "docker compose --env-file ${ENV_FILE} -f ${GRAPHITI_LOCAL}/docker-compose.yml up -d"
  fi
fi

# ── 8. Health check ───────────────────────────────────────────────────────
if [ "${STACK_UP}" = true ]; then
  header "Verificando health (espera 10s...)"
  sleep 10
  docker exec graphiti-falkordb redis-cli ping 2>/dev/null | grep -q PONG \
    && ok "FalkorDB respondiendo" \
    || warn "FalkorDB no responde aún: docker logs graphiti-falkordb"
  (curl -sf "http://localhost:8000/mcp/" >/dev/null 2>&1 || curl -sf "http://localhost:8000/" >/dev/null 2>&1) \
    && ok "MCP Server respondiendo en http://localhost:8000/mcp/" \
    || warn "MCP Server no responde aún: docker logs graphiti-mcp-server"
fi

# ── 9. Backup automático cada 4h (cron) ───────────────────────────────────
header "Configurando backup automático"
BACKUP_SCRIPT="${GRAPHITI_LOCAL}/scripts/backup-graph.sh"
if [ "${HAS_BACKUP}" = true ] && command -v crontab >/dev/null 2>&1; then
  CRON_LINE="0 */4 * * * ONEDRIVE_PATH=${ONEDRIVE} ${BACKUP_SCRIPT} >> ${GRAPHITI_LOCAL}/backup.log 2>&1"
  if ! crontab -l 2>/dev/null | grep -q "backup-graph"; then
    (crontab -l 2>/dev/null; echo "${CRON_LINE}") | crontab -
    ok "Cron configurado: backup cada 4 horas (log: ${GRAPHITI_LOCAL}/backup.log)"
  else
    ok "Cron para backup ya existe"
  fi
else
  [ "${HAS_BACKUP}" = true ] || { err "SIN BACKUPS AUTOMÁTICOS: backup-graph.sh no instalado."; WARNINGS+=("CRÍTICO: sin backup automático"); }
  command -v crontab >/dev/null 2>&1 || warn "crontab no disponible — configura el backup con launchd/systemd."
fi

# ── Resumen final ─────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
if [ ${#WARNINGS[@]} -eq 0 ]; then
  echo -e "${BOLD}${GREEN} Setup completado sin advertencias${NC}"
else
  echo -e "${BOLD}${YELLOW} Setup completado con ${#WARNINGS[@]} advertencia(s):${NC}"
  for w in "${WARNINGS[@]}"; do echo -e "   ${YELLOW}• ${w}${NC}"; done
fi
echo -e "${BOLD}════════════════════════════════════════════════════${NC}"
echo ""
echo "  FalkorDB Browser UI : http://localhost:3000 (solo esta máquina)"
echo "  MCP endpoint        : http://localhost:8000/mcp/"
echo "  Datos (LOCAL)       : ${GRAPHITI_LOCAL}/data/"
echo "  .env (LOCAL)        : ${ENV_FILE}"
echo "  Backups             : ${BACKUP_DIR}"
echo ""
if [ -n "${LOCAL:-}" ]; then
  echo -e "  ${YELLOW}Modo single-laptop: los backups quedan en el MISMO disco. Protegen contra${NC}"
  echo -e "  ${YELLOW}corrupción del grafo, no contra falla del disco — agenda copia periódica de${NC}"
  echo -e "  ${YELLOW}${BACKUP_DIR} a disco externo/nube, y usa remote git para el vault.${NC}"
  echo ""
fi
echo "  Próximos pasos:"
echo "  1. Completa el .env si quedó incompleto (key del provider, pins de versión)."
echo "  2. SIMULACRO DE RESTORE (auditoría A3): en cuanto haya datos reales,"
echo "     prueba restore-graph.sh — un backup no probado no existe."
echo "  3. Copia .graphiti.json a cada proyecto."
echo "  4. Cowork: sube setup/_build/dev-skills.zip en Customize > Plugins."
echo "  5. Al cambiar de laptop: docker compose stop → backup-graph.sh → sync."
echo ""
