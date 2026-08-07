#!/bin/sh
# ══════════════════════════════════════════════════════════════
#  git-post-commit-graph-report.sh — Hook post-commit de GIT (por repo)
#
#  Regenera el mapa del codebase con Graphify tras cada commit que toque
#  CÓDIGO y lo copia al vault como 10-Projects/<proyecto>/codebase-map-snapshot.md.
#  El grafo se actualiza en el COMMIT, no en el cierre de sesión —
#  session-close ya no regenera nada, solo verifica que este hook exista.
#
#  ⚠ ESCRIBE EL SNAPSHOT, NUNCA EL CURADO (RFD 10 C2). Hasta 2026-08-06 este
#  hook copiaba sobre `codebase-map.md`, que es un archivo CURADO A MANO: en
#  campo se comió 3.152 bytes de lecturas humanas con 111.353 de volcado.
#  Ley del único escritor aplicada a archivos: generado y curado no comparten
#  fichero jamás. El curado lo escribe una persona; este snapshot, solo el hook.
#
#  Instalación (por repo, solo donde corre Graphify):
#    cp setup/hooks/git-post-commit-graph-report.sh <repo>/.git/hooks/post-commit
#    chmod +x <repo>/.git/hooks/post-commit
#  (En Windows lo ejecuta Git Bash; funciona con las env OneDrive/USERPROFILE.)
#
#  Silencioso por diseño: commit sin código, sin graphify, sin reporte,
#  sin vault o sin proyecto enganchado → no hace nada.
# ══════════════════════════════════════════════════════════════

# 1) ¿El commit tocó código? (commits solo de docs/md no regeneran el grafo)
git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null \
  | grep -qE '\.(py|js|ts|tsx|jsx|go|rs|java|kt|c|h|cpp|hpp|cs|rb|php|sql)$' || exit 0

# 2) Regenerar con Graphify si está instalado (AST local, rápido — H5).
#    Si no está, degrada a copiar el último reporte existente.
#    ⚠ `graphify .` NO genera GRAPH_REPORT.md por sí solo (verificado con
#    0.9.5): escribe graph.json y te dice "next: run graphify cluster-only …".
#    Sin el segundo paso este hook salía en silencio SIEMPRE — instalado y
#    todo. Explica parte del "mapa congelado 9 días" del F6: no bastaba con
#    instalarlo. `--no-viz` evita generar el .html en cada commit.
if command -v graphify >/dev/null 2>&1; then
  graphify . >/dev/null 2>&1 || true
  graphify cluster-only . --no-viz >/dev/null 2>&1 || true
fi

REPORT="graphify-out/GRAPH_REPORT.md"
[ -f "$REPORT" ] || exit 0

# 3) Proyecto: sección "Active Project" del CLAUDE.md del repo, o nombre de la carpeta
NAME=$(grep -o 'Active Project: `[^`]*`' CLAUDE.md 2>/dev/null | head -1 | sed 's/.*`\(.*\)`.*/\1/')
[ -n "$NAME" ] && [ "$NAME" != "<project-name>" ] || NAME=$(basename "$(pwd)")

# 4) Vault: OneDrive (multi-laptop) o home (single-laptop) — la raíz que exista
for ROOT in "$OneDrive" "$USERPROFILE/OneDrive" "$HOME/OneDrive" "$USERPROFILE" "$HOME"; do
  [ -n "$ROOT" ] || continue
  DEST="$ROOT/DevSetup/ObsidianVault/10-Projects/$NAME"
  if [ -d "$DEST" ]; then
    cp "$REPORT" "$DEST/codebase-map-snapshot.md" && echo "[graphify] codebase-map-snapshot.md actualizado en vault: $NAME"
    rm -f "$DEST/graph-report.md" 2>/dev/null  # migración del nombre viejo
    # NO se toca codebase-map.md: es curado, y su único escritor es humano.
    exit 0
  fi
done
exit 0
