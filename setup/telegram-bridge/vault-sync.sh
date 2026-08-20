#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════
#  vault-sync.sh — El plugin Git de Obsidian, para la maquina que no tiene
#  Obsidian.
#
#  POR QUE EXISTE (2026-08-19). El vault es un repo git. En las laptops lo
#  sincronizan Obsidian + su plugin Git (autocommit + autopush). **La SER8 no
#  tiene Obsidian**, asi que en la unica maquina que corre el daemon 24/7 NADIE
#  hacia `pull` ni `push`:
#
#    · al leer  -> el briefing servia lo que hubiera en disco desde el ultimo
#                  pull a mano, sin decir su edad;
#    · al escribir -> la nota de `/done` se quedaba SOLO en el disco de la SER8.
#                  Eso no es "desincronizado", es perdida de datos.
#
#  El daemon ya cubre sus dos caminos (`vaultio.sync_pull` / `commit_push`), pero
#  solo cuando hay conversacion. Esto cubre el resto del dia.
#
#  LA REGLA QUE LO GOBIERNA, la misma del `latido-doctor.sh`: **calla cuando todo
#  esta bien.** Solo habla al movil cuando hay algo que una persona tiene que
#  decidir, que son tres casos y no uno: el conflicto, el push rebotado y el
#  pull que falla TENIENDO trabajo local sin publicar. Un pull que falla sin
#  nada en juego se calla y lo reintenta el pase de dentro de 20 min: con el
#  timer a esa cadencia, avisar de cada corte de red son tres mensajes por hora
#  que enseñan a no leer el unico que importa.
#
#  ANTE CONFLICTO NO RESUELVE NADA: aborta el rebase, deja el vault como estaba y
#  avisa. Con dos escritores (Obsidian en la laptop, daemon en la SER8) el
#  conflicto es cuestion de tiempo, y una resolucion automatica a ciegas es
#  exactamente como se pierde la nota que importaba. Misma familia que la regla
#  de no crear nunca `X 2.md`.
#
#  Uso:  vault-sync.sh              # calla salvo conflicto o push rebotado
#        vault-sync.sh --verboso    # imprime cada paso (para probarlo a mano)
#  Salidas: 0 al dia (o nada que hacer) · 1 hace falta una persona
# ══════════════════════════════════════════════════════════════════════════
set -uo pipefail          # SIN -e: los exit != 0 de git son el mecanismo

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "${AQUI}/../.." && pwd)"
VENV="${CLAUDE_TG_VENV:-${XDG_DATA_HOME:-$HOME/.local/share}/claude-telegram/venv}"
PY="${VENV}/bin/python"
[ -x "$PY" ] || PY="$(command -v python3 || true)"

VERBOSO=0
[ "${1:-}" = "--verboso" ] && VERBOSO=1
di() { [ "$VERBOSO" -eq 1 ] && echo "vault-sync: $*"; return 0; }

avisa() {   # $1 = titulo. Sin interprete no hay aviso: se dice y se sale != 0.
  if [ -n "${PY:-}" ] && [ -x "$PY" ]; then
    "$PY" "${AQUI}/notify_telegram.py" "$1" || echo "vault-sync: el aviso NO salio" >&2
  else
    echo "vault-sync: HAY algo que decidir y NO se pudo avisar (sin interprete)" >&2
  fi
}

# La raiz del vault la resuelve `vaultio`, no este script. Dos resolvedores para
# la misma ruta divergen en cuanto uno de los dos cambia, y el que se quedaria
# atras es siempre el que nadie lee — la lista de candidatos vive en
# `vaultio.vault_root()` y aqui solo se consulta.
if [ -z "${PY:-}" ] || [ ! -x "$PY" ]; then
  echo "vault-sync: sin interprete de Python; no puedo resolver la raiz del vault" >&2
  exit 1
fi
VAULT="$("$PY" -c "import sys; sys.path.insert(0, '${AQUI}'); import vaultio; print(vaultio.vault_root())" 2>/dev/null)"

if [ -z "$VAULT" ] || [ "$VAULT" = "." ] || [ ! -d "$VAULT" ]; then
  di "no hay vault en esta maquina; nada que sincronizar"
  exit 0
fi
if [ ! -e "${VAULT}/.git" ]; then
  di "el vault no es un repo git; nada que sincronizar"
  exit 0
fi
if [ -z "$(git -C "$VAULT" remote 2>/dev/null)" ]; then
  di "el vault no tiene remoto; nada que publicar"
  exit 0
fi

# Sin prompt de credencial: una caja headless no tiene a quien preguntarle, y sin
# esto el fallo no es "no sincronizo" sino el timer colgado hasta el timeout.
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -oBatchMode=yes}"

# 1 · Lo local primero. El daemon ya commitea su nota en `/done`; esto recoge lo
#     que se haya tocado por fuera (un `_PROJECT.md` editado a mano por ssh).
if [ -n "$(git -C "$VAULT" status --porcelain)" ]; then
  di "hay cambios locales; commiteando"
  git -C "$VAULT" add -A
  git -C "$VAULT" commit -q -m "vault-sync: $(hostname) $(date +%Y-%m-%d\ %H:%M)" \
    || { avisa "🔴 vault en $(hostname): el commit automatico fallo"; exit 1; }
fi

# ¿Hay trabajo local sin publicar? -> 0 si, 1 no, 2 no se puede saber (sin
# upstream). Existe porque la respuesta decide DOS cosas distintas: si hay que
# empujar (paso 3) y si un fallo de red merece despertar a alguien (paso 2). El
# `2>/dev/null` de antes convertia "esta rama no tiene upstream" en "nada que
# publicar", que es la forma callada de no publicar nunca.
sin_publicar() {
  git -C "$VAULT" rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1 || return 2
  [ -n "$(git -C "$VAULT" log --oneline '@{u}..HEAD' 2>/dev/null)" ]
}

# 2 · Traer. `--rebase` para no llenar el historial de merges vacios;
#     `--autostash` por si el paso 1 dejo algo sin trackear en medio.
if ! SALIDA="$(git -C "$VAULT" pull --rebase --autostash 2>&1)"; then
  echo "$SALIDA" >&2
  # UN PULL QUE FALLA NO ES UN CONFLICTO. Se pregunta por el rebase EN CURSO en
  # vez de suponerlo: sin remoto alcanzable, sin credencial o sin upstream, git
  # falla ANTES de empezar el rebase, y el `rebase --abort` de antes era un
  # no-op cuyo mensaje decia "CONFLICTO ... rebase abortado". Con el timer cada
  # 20 min, un corte de red mandaba esa falsa alarma tres veces por hora — y una
  # alarma que casi siempre miente deja de leerse justo el dia que dice verdad.
  GITDIR="$(git -C "$VAULT" rev-parse --absolute-git-dir 2>/dev/null || true)"
  if [ -n "$GITDIR" ] && { [ -d "${GITDIR}/rebase-merge" ] || [ -d "${GITDIR}/rebase-apply" ]; }; then
    # Deshacer ANTES de avisar: un vault en rebase a medias rompe la lectura del
    # briefing, y el mensaje al movil llegaria describiendo un estado que ya
    # estaria haciendo dano.
    git -C "$VAULT" rebase --abort 2>/dev/null
    avisa "🔴 vault en $(hostname): CONFLICTO al sincronizar. Rebase abortado, el vault quedo como estaba. Hace falta resolverlo a mano: git -C ${VAULT} pull --rebase"
    exit 1
  fi
  # No es conflicto. Se habla SOLO si hay algo local en juego, que es la regla
  # de la casa: el pase de dentro de 20 min lo reintenta y nadie tiene nada que
  # decidir mientras no haya una nota sin publicar. Si no se puede saber, se
  # habla: no saber cuenta como algo en juego.
  sin_publicar; PENDIENTE=$?
  if [ "$PENDIENTE" -eq 1 ]; then
    di "pull fallido (no es conflicto) y no hay nada local sin publicar; callo"
    exit 1
  fi
  avisa "🟠 vault en $(hostname): el pull NO salio y no es un conflicto (red, credencial o rama sin upstream). Hay trabajo local SIN PUBLICAR esperando. No he tocado nada; el proximo pase reintenta."
  exit 1
fi
di "pull: ok"

# 3 · Publicar, solo si hay algo que publicar.
sin_publicar; PENDIENTE=$?
if [ "$PENDIENTE" -eq 2 ]; then
  avisa "🟠 vault en $(hostname): la rama del vault no tiene upstream, asi que NADA se esta publicando. Arreglalo: git -C ${VAULT} push -u origin HEAD"
  exit 1
fi
if [ "$PENDIENTE" -eq 0 ]; then
  if ! SALIDA="$(git -C "$VAULT" push 2>&1)"; then
    echo "$SALIDA" >&2
    avisa "🔴 vault en $(hostname): el push rebota. Lo local esta commiteado pero NO publicado."
    exit 1
  fi
  di "push: ok"
else
  di "nada que publicar"
fi

di "al dia"
exit 0
