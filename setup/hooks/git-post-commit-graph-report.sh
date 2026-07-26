#!/bin/sh
# ══════════════════════════════════════════════════════════════
#  git-post-commit-graph-report.sh — Hook post-commit de GIT (por repo)
#
#  Copia graphify-out/GRAPH_REPORT.md al vault tras cada commit, para que
#  el grafo del codebase viaje solo a 10-Projects/<proyecto>/graph-report.md
#  y Cowork/project-resume lo vean sin pasos manuales (doc 05 §3).
#
#  Instalación (por repo, solo donde corre Graphify):
#    cp setup/hooks/git-post-commit-graph-report.sh <repo>/.git/hooks/post-commit
#    chmod +x <repo>/.git/hooks/post-commit
#  (En Windows, Git Bash lo ejecuta; funciona con las env OneDrive/USERPROFILE.)
#
#  Silencioso por diseño: sin reporte, sin vault o sin proyecto enganchado → no hace nada.
# ══════════════════════════════════════════════════════════════

REPORT="graphify-out/GRAPH_REPORT.md"
[ -f "$REPORT" ] || exit 0

# Proyecto: sección "Active Project" del CLAUDE.md del repo, o nombre de la carpeta
NAME=$(grep -o 'Active Project: `[^`]*`' CLAUDE.md 2>/dev/null | head -1 | sed 's/.*`\(.*\)`.*/\1/')
[ -n "$NAME" ] && [ "$NAME" != "<project-name>" ] || NAME=$(basename "$(pwd)")

# Vault: OneDrive (multi-laptop) o home (single-laptop) — la raíz que exista
for ROOT in "$OneDrive" "$USERPROFILE/OneDrive" "$HOME/OneDrive" "$USERPROFILE" "$HOME"; do
  [ -n "$ROOT" ] || continue
  DEST="$ROOT/DevSetup/ObsidianVault/10-Projects/$NAME"
  if [ -d "$DEST" ]; then
    cp "$REPORT" "$DEST/graph-report.md" && echo "[graph-report] copiado a vault: $NAME"
    exit 0
  fi
done
exit 0
