#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  backup-graph.sh — Snapshot RDB de FalkorDB → OneDrive
#  Cron sugerido: 0 */4 * * * /path/to/backup-graph.sh
#  También: ejecutar SIEMPRE antes de cambiar de laptop.
#
#  Fixes de auditoría (`auditoria/09`):
#   - Manifest JSON válido (A7: antes incrustaba INFO multilínea)
#   - Aviso de fork si el último backup lo escribió otra máquina (R1)
#   - Restore SOLO via restore-graph.sh (A3: con AOF activo, copiar
#     dump.rdb a mano NO restaura — el server carga del AOF)
#   - Sin copia en caliente del AOF (docker cp mid-write = archivo roto)
#
#  Uso:
#    ./backup-graph.sh                          # usa defaults
#    ./backup-graph.sh ~/OneDrive               # OneDrive path explícito
#    ONEDRIVE_PATH=/ruta backup-graph.sh        # via env var
# ══════════════════════════════════════════════════════════════

set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-graphiti-falkordb}"
ONEDRIVE_PATH="${1:-${ONEDRIVE_PATH:-$HOME/OneDrive}}"
# Sin OneDrive → backups en ~/DevSetup (modo single-laptop; mismo layout)
[ -d "${ONEDRIVE_PATH}" ] || ONEDRIVE_PATH="$HOME"
BACKUP_DIR="${BACKUP_DIR:-${ONEDRIVE_PATH}/DevSetup/graphiti-data/backups}"
MAX_BACKUPS="${MAX_BACKUPS:-15}"
HOST="$(hostname)"

# ── 1. Verificar container ────────────────────────────────────────────────
if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
  echo "[WARN] Container '${CONTAINER_NAME}' no está corriendo. Backup omitido."
  exit 0
fi

mkdir -p "${BACKUP_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# ── 2. Aviso de fork multi-laptop (R1) ───────────────────────────────────
LATEST_MANIFEST=$(ls -t "${BACKUP_DIR}"/*.manifest.json 2>/dev/null | head -1 || echo "")
if [ -n "${LATEST_MANIFEST}" ] && command -v python3 >/dev/null 2>&1; then
  LAST_HOST=$(python3 -c "import json;print(json.load(open('${LATEST_MANIFEST}')).get('hostname',''))" 2>/dev/null || echo "")
  if [ -n "${LAST_HOST}" ] && [ "${LAST_HOST}" != "${HOST}" ]; then
    echo "══════════════════════════════════════════════════════════════"
    echo "[⚠ FORK WARNING] El backup más reciente lo escribió '${LAST_HOST}'."
    echo "  Si NO restauraste desde él en esta máquina (restore-graph.sh),"
    echo "  este backup guardará una historia DIVERGENTE del grafo."
    echo "══════════════════════════════════════════════════════════════"
  fi
fi

# ── 3. Trigger BGSAVE y esperar a que termine ─────────────────────────────
echo "[INFO] Triggering BGSAVE en FalkorDB..."
BEFORE_SAVE=$(docker exec "${CONTAINER_NAME}" redis-cli LASTSAVE 2>/dev/null || echo "0")
docker exec "${CONTAINER_NAME}" redis-cli BGSAVE > /dev/null 2>&1 || true

MAX_WAIT=30
SAVED=false
for i in $(seq 1 $MAX_WAIT); do
  sleep 1
  AFTER_SAVE=$(docker exec "${CONTAINER_NAME}" redis-cli LASTSAVE 2>/dev/null || echo "0")
  if [ "$AFTER_SAVE" != "$BEFORE_SAVE" ]; then
    echo "[INFO] BGSAVE completado (${i}s)."
    SAVED=true
    break
  fi
done
[ "$SAVED" = false ] && echo "[WARN] BGSAVE no confirmado en ${MAX_WAIT}s. Copiando de todas formas."

# ── 4. Copiar dump.rdb ────────────────────────────────────────────────────
BACKUP_FILE="${BACKUP_DIR}/graphiti_${TIMESTAMP}.rdb"
COPIED=false
for DATA_PATH in "/var/lib/falkordb/data/dump.rdb" "/data/dump.rdb"; do
  if docker exec "${CONTAINER_NAME}" test -f "${DATA_PATH}" 2>/dev/null; then
    docker cp "${CONTAINER_NAME}:${DATA_PATH}" "${BACKUP_FILE}" 2>/dev/null && {
      echo "[OK] Backup guardado: ${BACKUP_FILE}"
      COPIED=true
      break
    }
  fi
done
if [ "$COPIED" = false ]; then
  echo "[ERR] No se pudo copiar dump.rdb. Backup FALLIDO."
  exit 1
fi

# ── 5. Manifiesto (JSON válido — solo campos escalares) ──────────────────
DBSIZE=$(docker exec "${CONTAINER_NAME}" redis-cli DBSIZE 2>/dev/null | tr -dc '0-9' || echo "-1")
IMAGE=$(docker inspect --format '{{.Config.Image}}' "${CONTAINER_NAME}" 2>/dev/null || echo "unknown")
MANIFEST="${BACKUP_DIR}/graphiti_${TIMESTAMP}.manifest.json"
cat > "${MANIFEST}" << MANIFEST_EOF
{
  "timestamp": "${TIMESTAMP}",
  "hostname": "${HOST}",
  "container": "${CONTAINER_NAME}",
  "image": "${IMAGE}",
  "rdb_file": "graphiti_${TIMESTAMP}.rdb",
  "dbsize": ${DBSIZE:--1},
  "restore": "NO copiar dump.rdb a mano (AOF lo ignora). Usar restore-graph.sh / restore-graph.ps1"
}
MANIFEST_EOF
echo "[INFO] Manifiesto: ${MANIFEST} (dbsize=${DBSIZE})"

# ── 6. Rotación (mantener últimos MAX_BACKUPS) ────────────────────────────
OLD_BACKUPS=$(ls -t "${BACKUP_DIR}"/*.rdb 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) || true)
if [ -n "$OLD_BACKUPS" ]; then
  echo "$OLD_BACKUPS" | xargs rm -f
  ls -t "${BACKUP_DIR}"/*.manifest.json 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f 2>/dev/null || true
  echo "[INFO] Backups viejos limpiados."
fi

BACKUP_SIZE=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1 || echo "?")
echo "[INFO] Tamaño total de backups: ${BACKUP_SIZE} en ${BACKUP_DIR}"
echo "[DONE] Backup completado: $(date)"
