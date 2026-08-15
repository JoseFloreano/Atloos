#!/bin/sh
# ══════════════════════════════════════════════════════════════
#  git-post-commit-graph-report.sh — Hook post-commit de GIT (por repo)
#
#  Regenera el mapa del codebase con Graphify tras cada commit que toque
#  CÓDIGO. El grafo se actualiza en el COMMIT, no en el cierre de sesión —
#  session-close ya no regenera nada, solo verifica que este hook exista.
#
#  ⚠ DOS DESTINOS, DOS TAMAÑOS (RFD 11 C5, D2=b). El volcado completo —212 KB
#  medidos en campo— NO entra en el vault: iría por OneDrive varias veces al
#  día, que es justo el patrón que H2/A1 prohibieron (datos vivos fuera de la
#  carpeta sincronizada; artefactos terminados dentro).
#    · Volcado completo → %LOCALAPPDATA%/graphify-snapshots/<proyecto>/
#      (local a la máquina que lo generó; consultable ahí, no en las otras)
#    · Recorte ~2 KB    → vault, como codebase-map-snapshot.md
#  El recorte conserva cabecera + secciones de resumen, que es EXACTAMENTE lo
#  que `vaultio.snapshot_resumen` ya lee: corta al primer encabezado de detalle,
#  así que el briefing del bot no cambia ni una línea por este cambio.
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
#
# ⚠ HASTA EL 2026-08-14 ESTE BLOQUE FIRMABA COMO FRESCO UN GRAFO CONGELADO.
#    Eran dos líneas con `>/dev/null 2>&1 || true`: las salidas al vacío **y** el
#    código de salida descartado. En campo `graphify .` abortó con
#    `no LLM API key found (82 doc/paper/image files need semantic extraction)`
#    —exit 1, verificado— y el `cluster-only` de la línea siguiente **re-agrupó
#    el graph.json viejo y le estampó el HEAD actual**. El conteo llevaba todo el
#    día clavado en 13 188 nodos y una función creada esa mañana no aparecía.
#
#      El hook no podía fallar, no podía avisar, y firmaba como fresco lo que
#      estaba congelado. Es la ley 1 del repo invertida: aquí el código de
#      salida SÍ era el estado, y lo tirábamos a la basura a propósito.
#
#    Lo que lo hace grave y no cosmético: fue la PRIMERA jornada de cuatro con
#    `graphify: usado`. Se consultó como manda el disparador nuevo y respondió
#    bien por casualidad —los ficheros eran viejos y estaban indexados—. Una
#    consulta sobre código de esa mañana habría devuelto silencio con el sello
#    de frescura diciendo el HEAD correcto.
#
# ⚠ Y EL ARREGLO NO ERA `--code-only`, aunque lo dijeran el reporte de campo y
#    el encargo. **`--code-only` no existe en 0.9.5**: se ignora en silencio y
#    el comando falla exactamente igual (medido — `graphify . --code-only`
#    devuelve el mismo error de clave y el mismo exit 1). Poner esa bandera
#    habría sido un no-op con aspecto de arreglo, que es peor que no arreglar.
#    El camino sin LLM que SÍ existe en 0.9.5 es `graphify update <path>`, que
#    su propia ayuda describe como *"re-extract code files and update the graph
#    (no LLM needed)"* — y con `--no-cluster` deja el clustering para el paso
#    siguiente, que es quien sabe hacerlo sin generar el .html.
#
#    El fallo de campo tampoco era que faltara la clave: era que el hook pedía
#    extracción semántica de 82 documentos cuando solo necesita código. Por eso
#    aquí NO va ninguna clave de API: va el comando que no la necesita.
#
# ⚠ Sigue siendo un hook de `post-commit`: RUIDOSO NO ES BLOQUEANTE. El commit
#    ya está hecho y no se toca. Lo único que cambia es que el humano se entera.
if command -v graphify >/dev/null 2>&1; then
  if graphify update . --no-cluster >/dev/null 2>&1; then
    graphify cluster-only . --no-viz >/dev/null 2>&1 \
      || echo "[graphify] AVISO: el clustering falló tras una reconstrucción correcta; GRAPH_REPORT.md puede ir atrasado." >&2
  else
    # NO se ejecuta el cluster-only: es justo el paso que re-sella el grafo
    # viejo con el HEAD de hoy. Y se sale ANTES de copiar nada, porque copiar
    # es estampar el sello. Un grafo viejo puede seguir ahí; lo que no puede es
    # decir que es de hoy.
    echo "[graphify] AVISO: la reconstruccion del grafo FALLO — no se re-agrupa ni se re-sella." >&2
    echo "[graphify] AVISO: el grafo que haya en graphify-out/ es VIEJO. Diagnostica con: graphify update ." >&2
    exit 0
  fi
fi

REPORT="graphify-out/GRAPH_REPORT.md"
[ -f "$REPORT" ] || exit 0

# Sin graphify instalado no ha habido reconstrucción, así que lo que se copia
# abajo es el último reporte que quedó — la degradación documentada en la
# cabecera. Se conserva, pero se DICE: un reporte copiado sin regenerar tiene el
# mismo aspecto que uno fresco, y esa indistinguibilidad es el fallo de arriba
# en pequeño.
command -v graphify >/dev/null 2>&1 \
  || echo "[graphify] AVISO: graphify no esta instalado; se copia el ultimo GRAPH_REPORT.md SIN regenerar." >&2

# 3) Proyecto: sección "Active Project" del CLAUDE.md del repo, o nombre de la carpeta
NAME=$(grep -o 'Active Project: `[^`]*`' CLAUDE.md 2>/dev/null | head -1 | sed 's/.*`\(.*\)`.*/\1/')
[ -n "$NAME" ] && [ "$NAME" != "<project-name>" ] || NAME=$(basename "$(pwd)")

# 4) Volcado COMPLETO fuera del vault, en la máquina que lo generó.
#    LOCALAPPDATA viene con backslashes; se normalizan para el shell.
LOCALROOT=$(printf '%s' "${LOCALAPPDATA:-}" | tr '\\' '/')
[ -n "$LOCALROOT" ] || LOCALROOT="${XDG_DATA_HOME:-$HOME/.local/share}"
SNAPDIR="$LOCALROOT/graphify-snapshots/$NAME"
if mkdir -p "$SNAPDIR" 2>/dev/null; then
  cp "$REPORT" "$SNAPDIR/GRAPH_REPORT.md" 2>/dev/null \
    && echo "[graphify] volcado completo: $SNAPDIR/GRAPH_REPORT.md"
fi

# 5) Vault: OneDrive (multi-laptop) o home (single-laptop) — la raíz que exista
for ROOT in "$OneDrive" "$USERPROFILE/OneDrive" "$HOME/OneDrive" "$USERPROFILE" "$HOME"; do
  [ -n "$ROOT" ] || continue
  DEST="$ROOT/DevSetup/ObsidianVault/10-Projects/$NAME"
  if [ -d "$DEST" ]; then
    # Recorte: cabecera + secciones de resumen. Se corta en el primer
    # encabezado que NO sea de resumen — el mismo criterio que vaultio.
    # Tope duro de 4000 bytes por si un reporte trae un resumen desmedido.
    awk '
      /^#+[ \t]/ {
        if (visto && tolower($0) !~ /corpus|summary|resumen|overview|totales|mapa|freshness/) exit
        visto = 1
      }
      { print }
    ' "$REPORT" | head -c 4000 > "$DEST/codebase-map-snapshot.md" \
      && echo "[graphify] codebase-map-snapshot.md (recorte) actualizado en vault: $NAME"
    rm -f "$DEST/graph-report.md" 2>/dev/null  # migración del nombre viejo
    # NO se toca codebase-map.md: es curado, y su único escritor es humano.
    exit 0
  fi
done
exit 0
