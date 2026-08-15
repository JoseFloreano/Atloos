#!/usr/bin/env python3
"""
merge-gate-guard.py — Hook PreToolUse (matcher Bash) de Claude Code.

El W3 del RFD 04: la compuerta determinista que no depende de que una skill gane
un concurso de descripciones.

POR QUÉ EXISTE. En la prueba deliberada del 2026-08-07 el `workstream-merge-gate`
salió 2/4, y la causa medida no fue que la skill fallara: **no llegó a correr**.
En 3 de 4 escenarios ganó `superpowers:finishing-a-development-branch`, que no
tiene confirmación humana ni squash, y se colaron **2 merges a `main` sin OK**.
Una convención escrita vuelve a fallar; un arnés, no.

QUÉ BLOQUEA. `git merge` (y `git pull`, que es fetch+merge) cuyo destino
efectivo sea una rama protegida (`main`/`master`) sin **evidencia determinista
de verde**: un `.claude/gate-verde.json` `{branch, sha, ts, cmd}` cuyo `sha`
coincida con el HEAD actual de la rama que se integra. Esa evidencia la escribe
`scripts/gate-test.py`, que solo la produce con exit 0 de la suite — la palabra
del agente nunca es evidencia.

Y desde el sprint 2, también `git push` a una rama protegida. EL AGUJERO LO
ENCONTRÓ EL CAMPO, no una auditoría (reporte del 2026-08-11):

    "Empujé un commit sin gatear a la rama principal. El gate corría en segundo
     plano sobre un SHA; mientras corría, edité y commiteé un documento sobre
     esa misma rama, y el `--ff-only` se llevó los dos commits. La evidencia de
     verde no cubría ese árbol."

Es la misma clase de error que el hook existe para impedir, cometida por quien
lo estaba operando — y el hook no la vio porque su contrato decía `merge` y el
verbo era `push`. La compuerta guardaba la puerta y la pared estaba abierta.

QUÉ SE COMPARA AL EMPUJAR, y por qué no basta el sha a secas. Lo que tiene que
estar verde es **el árbol que aterriza en la protegida**, así que se acepta el
push si el commit empujado es el gateado (caso `--ff-only` limpio) **o** si su
*tree* coincide con el del sha gateado (caso `--squash`, donde el commit es
nuevo pero el contenido es el mismo). Un commit extra colado durante la corrida
cambia las dos cosas, que es exactamente lo que se escapó.

FALSOS POSITIVOS DEL PUSH, que aquí son caros. No intervienen: push a una rama
de trabajo (el filtro es la rama de DESTINO), `--dry-run`/`-n`, push de tags, y
el push del bot de Telegram —que además va por subprocess del daemon y no por la
herramienta Bash, así que este hook ni lo ve—. Un push que no adelanta nada
(local == `origin/<rama>`) tampoco se toca: no viaja ningún árbol.

LÍMITES DECLARADOS — la lista completa, porque una lista incompleta hace que la
cobertura se lea más ancha de lo que es (auditoría 22, H6):

  · `git push --delete` a una protegida NO se bloquea. Borrar una rama no es
    integrar código y este hook no es un guardián de permisos.
  · **Todo lo que no sea texto plano de shell se escapa**: `bash -c '…'`,
    `if …; then git push …; fi`, bucles `for`, `xargs`, un script que por dentro
    haga el push, o cualquier alias. Este hook es un parser de texto y ese es su
    techo real; los subshells `( … )` y los grupos `{ …; }` sí se pelan porque
    son un carácter de envoltorio, no una construcción.
  · No juzga la CALIDAD del verde, ni el worktree limpio, ni pide la
    confirmación humana: un hook no puede preguntar (ver QUÉ NO HACE).

DESTINO EFECTIVO, no rama actual. Los dos merges que se colaron venían como
`git checkout main && git merge feat/x`: mirar solo el HEAD del momento habría
dejado pasar exactamente el caso que motivó el hook.

QUÉ NO HACE. Fuera de las ramas protegidas no interviene. No juzga la calidad
del verde (eso es el paso 2 de la skill, con los 3 criterios del revisor), no
mira si el worktree está limpio (paso 1) y no exige la confirmación humana
(paso 6): un hook no puede preguntar. Cubre lo verificable por máquina; el
resto lo sigue poniendo la skill.

Fail-open ante entrada ilegible (un bug del hook no tumba la sesión).
Fail-CLOSED ante un merge a protegida que no se puede verificar: ahí la duda
se resuelve parando, que es el sentido de la compuerta.
"""
import json
import os
import re
import subprocess
import sys

# El bloqueo se explica por stderr, y en Windows esa consola es cp1252: sin
# esto, un mensaje con acentos —todos los de aquí— sale mutilado o revienta al
# escribirse. Un hook que bloquea y no consigue decir POR QUÉ es medio hook.
try:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROTEGIDAS = {"main", "master"}
EVIDENCIA = os.path.join(".claude", "gate-verde.json")   # el sitio de respaldo
NOMBRE_EVIDENCIA = "gate-verde.json"   # dentro del directorio git COMUN

# Subcomandos de `git merge` que NO son una integración.
NO_MERGE = {"--abort", "--continue", "--quit"}


def git(args, cwd):
    """Salida de un git, o "" si falla. Nunca lanza."""
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=10)
        return p.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def ruta_evidencia(cwd):
    """Dónde se busca el verde. GEMELA de la de `setup/scripts/gate-test.py`.

    Las dos tienen que resolver la MISMA ruta sobre el mismo repo. Son procesos
    distintos —este hook vive en `~/.claude/hooks/`, el otro en
    `~/.claude/scripts/`— y no comparten módulo, así que la copia no se puede
    evitar; lo que sí se puede es vigilarla, y lo hace `test-gate-test.py`
    afirmando que ambas coinciden. Si tocas una, toca la otra.

    POR QUÉ EL DIRECTORIO GIT COMÚN Y NO `.claude/` DEL ÁRBOL (auditoría del
    08-14, H2): `gate-test.py` escribía en la raíz de SU árbol —en un worktree,
    el worktree— y este guard leía en el `cwd` de quien integra —el checkout
    principal—. La evidencia producida donde la skill manda **no la veía quien
    integra**, así que el procedimiento documentado no se podía ejecutar. El
    `--git-common-dir` es el mismo `.git` desde cualquier worktree.

    ⚠ No abre nada: lo que se le exige a la evidencia —`branch`, `sha`, y que el
    árbol del tip coincida con el del sha registrado— no cambia ni una línea.
    """
    comun = git(["rev-parse", "--git-common-dir"], cwd)
    if not comun:
        return os.path.join(cwd, EVIDENCIA)
    if not os.path.isabs(comun):
        comun = os.path.join(cwd, comun)
    return os.path.join(os.path.abspath(comun), NOMBRE_EVIDENCIA)


# Un ref de git no lleva estos caracteres. Si el "nombre de rama" los trae, no
# es un comando: es prosa que casualmente empieza por `git merge`.
NO_ES_REF = set("`'\"()[]{}<>,¿?¡!*:\\ ")

# Opciones GLOBALES de git (van antes del subcomando) que consumen el token
# siguiente. Sin esto, `git -C . merge x` rompía el ancla `^git\s+merge` y
# esquivaba la compuerta entera (H1 de la auditoría del 2026-08-09).
GLOBAL_CON_VALOR = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                    "--exec-path"}

# Opciones de `git pull` que consumen el token siguiente, para no confundir su
# valor con el nombre del remoto.
PULL_CON_VALOR = {"-s", "--strategy", "-X", "--strategy-option", "--depth"}

# Ídem para `git push`.
PUSH_CON_VALOR = {"--repo", "-o", "--push-option", "--receive-pack", "--exec"}

# Un push que no publica ningún árbol nuevo en la protegida. `--dry-run` no
# ejecuta nada y `--delete` borra en vez de integrar (ver LÍMITE DECLARADO).
PUSH_NO_INTEGRA = {"--dry-run", "-n", "--delete", "-d"}

# Formas de nombrar «la rama actual» en un refspec. No son ramas: hay que
# resolverlas antes de preguntar si el destino está protegido.
ALIAS_DE_HEAD = {"head", "@"}


def sin_opciones_globales(seg):
    """`git -C . -c k=v merge x` → `git merge x`, o None si no queda subcomando."""
    toks = seg.split()
    if not toks or toks[0] != "git":
        return None
    i = 1
    while i < len(toks) and toks[i].startswith("-"):
        i += 2 if toks[i] in GLOBAL_CON_VALOR else 1
    return "git " + " ".join(toks[i:]) if i < len(toks) else None


def _spans_citados(linea):
    """Tramos entre comillas, como (inicio, fin). Lo de dentro es texto."""
    spans, i, n = [], 0, len(linea)
    while i < n:
        c = linea[i]
        if c in "'\"":
            j = linea.find(c, i + 1)
            if j == -1:
                spans.append((i, n - 1))
                break
            spans.append((i, j))
            i = j + 1
        else:
            i += 1
    return spans


def sin_heredocs(cmd):
    """Quita el CUERPO de los heredocs, que es texto, no comandos.

    Lo aprendió bloqueando su propio commit: el mensaje explicaba el caso
    `git checkout main && git merge x` y el hook lo leyó como un merge de
    verdad. El contenido de un heredoc nunca se ejecuta.

    Y aprendió la vuelta con la auditoría: un `<<IDENT` DENTRO de comillas no
    abre ningún heredoc. Al tratarlo como si lo abriera, se comía todas las
    líneas siguientes esperando un cierre que nunca llegaba —y con ellas, el
    merge de verdad—. Este repo escribe sobre heredocs en sus mensajes de
    commit, así que el caso no era hipotético.
    """
    fuera, saltando, cierre = [], False, None
    for linea in cmd.splitlines():
        if saltando:
            if linea.strip() == cierre:
                saltando = False
            continue
        spans = _spans_citados(linea)
        for m in re.finditer(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", linea):
            if any(a <= m.start() <= b for a, b in spans):
                continue                  # `<<` entrecomillado: es prosa
            saltando, cierre = True, m.group(2)
            break
        fuera.append(linea)
    return "\n".join(fuera)


def pela_envoltorio(seg):
    """`(git push …)` y `{ git push …; }` → `git push …`.

    Un subshell y un grupo son UN carácter de envoltorio alrededor del mismo
    comando, así que pelarlos es honesto y barato. La auditoría 22 (H6) los
    encontró esquivando el gate —también en `git merge`, así que venía del W3—
    y lo grave no era el hueco sino que el bloque de límites declarados no lo
    mencionara: la cobertura se leía más ancha de lo que era.

    Se pelan SUELTOS, no por pares: `segmentos()` corta antes por `;`, así que
    `{ git push …; }` llega aquí como `{ git push …` — sin su cierre. Y ningún
    comando de git empieza por `(` o `{`, de modo que quitarlos no puede tapar
    nada legítimo.
    """
    return seg.strip().lstrip("({").rstrip(")}").strip()


def segmentos(cmd):
    """Parte una línea de shell en comandos, respetando el orden."""
    cmd = sin_heredocs(cmd)
    return [pela_envoltorio(s) for s in re.split(r"&&|\|\||;|\n", cmd)
            if pela_envoltorio(s)]


def rama_de_checkout(seg):
    """Rama a la que salta un `git checkout/switch`, o None. "-" = la anterior."""
    seg = sin_opciones_globales(seg) or seg
    m = re.match(r"^git\s+(?:checkout|switch)\s+(.*)$", seg)
    if not m:
        return None
    resto = m.group(1)
    # `git checkout <rama> -- <ruta>` RESTAURA ficheros desde esa rama: no salta
    # a ella. Tratarlo como salto bloqueaba trabajo legítimo desde otra rama.
    if re.search(r"(^|\s)--(\s|$)", resto):
        return None
    for tok in resto.split():
        if tok == "-":
            return "-"        # `switch -` vuelve: lo resuelve el recorrido
        if tok.startswith("-"):
            continue          # -b, -q, --detach… la rama es el primer no-flag
        return tok.strip("'\"")
    return None


def fuente_de_pull(seg, destino):
    """(es_integracion, rama_origen|None) para `git pull`, que es fetch+merge.

    Escapaba entero: ni siquiera contiene la palabra "merge". Pero solo cuenta
    como integración si nombra una rama DISTINTA del destino — un `git pull` a
    secas, o `git pull origin main` estando en main, es sincronizar con el
    remoto. Bloquear eso sería un falso positivo diario, peor que el escape.

    Límite declarado: un `git pull` sin refspec cuyo upstream fuera una rama de
    trabajo pasaría. Exige una configuración que aquí no se da.
    """
    seg = sin_opciones_globales(seg) or seg
    m = re.match(r"^git\s+pull(?:\s+(.*))?$", seg)
    if not m:
        return False, None
    args, saltar = [], False
    for tok in (m.group(1) or "").split():
        if saltar:
            saltar = False
            continue
        if tok in PULL_CON_VALOR:
            saltar = True
            continue
        if not tok.startswith("-"):
            args.append(tok)
    if len(args) < 2:
        return False, None                        # sin refspec: sincronización
    rama = args[1].strip("'\"").split(":")[0]     # <src>:<dst> → nos importa src
    if not rama or any(c in NO_ES_REF for c in rama) or rama == destino:
        return False, None
    return True, rama


def fuente_de_merge(seg):
    """(es_merge, rama_origen|None). rama None = merge sin argumento."""
    seg = sin_opciones_globales(seg) or seg
    m = re.match(r"^git\s+merge(?:\s+(.*))?$", seg)
    if not m:
        return False, None
    resto = (m.group(1) or "").split()
    if any(t in NO_MERGE for t in resto):
        return False, None
    saltar = False
    for tok in resto:
        if saltar:
            saltar = False
            continue
        if tok in ("-m", "-F", "--file", "-S", "--gpg-sign"):
            saltar = True
            continue
        if tok.startswith("-"):
            continue
        limpio = tok.strip("'\"")
        # Prosa disfrazada: un ref no lleva backticks, comas ni paréntesis.
        if any(c in NO_ES_REF for c in limpio):
            return False, None
        return True, limpio
    return True, None


def destinos_de_push(seg, rama_actual):
    """[(rama_destino, ref_local)] que un `git push` publicaría. [] = no aplica.

    El filtro de "protegida" NO vive aquí sino en el llamador, así que una rama
    de trabajo y un tag `v1.2.3` caen solos: su destino no está en PROTEGIDAS.
    Aquí solo se descartan las formas que no publican un árbol (`--dry-run`,
    `--delete`) y se resuelve qué ref local viaja a qué rama remota.

    `--tags` no se descarta entero: suprime el push implícito de la rama actual
    —`git push --tags` estando en `main` NO empuja `main`, y tratarlo como si lo
    hiciera era el falso positivo más caro de los cuatro— pero deja en pie los
    refspecs explícitos, que sí publican.

    `--all` / `--mirror` publican todas las ramas, protegidas incluidas: se
    devuelve el comodín ("*", "*") y lo expande el llamador, que es quien puede
    preguntarle a git cuáles existen.
    """
    seg = sin_opciones_globales(seg) or seg
    m = re.match(r"^git\s+push(?:\s+(.*))?$", seg)
    if not m:
        return []
    args, saltar, solo_tags, todas = [], False, False, False
    for tok in (m.group(1) or "").split():
        if saltar:
            saltar = False
            continue
        if tok in PUSH_NO_INTEGRA:
            return []
        if tok in PUSH_CON_VALOR:
            saltar = True
            continue
        if tok == "--tags":
            solo_tags = True
            continue
        if tok in ("--all", "--mirror"):
            todas = True
            continue
        if tok.startswith("-"):
            continue
        args.append(tok.strip("'\""))

    if todas:
        return [("*", "*")]

    refspecs = args[1:]                       # args[0] es el remoto
    if not refspecs:
        # `git push` / `git push origin`: publica la rama actual sobre su
        # homónima. Es la forma exacta del incidente del 2026-08-11.
        if solo_tags or not rama_actual:
            return []
        return [(rama_actual, rama_actual)]

    salidas = []
    for rs in refspecs:
        rs = rs.lstrip("+")                   # `+main` es push forzado
        if rs.startswith("refs/tags/"):
            continue
        src, sep, dst = rs.partition(":")
        if not sep:
            dst = src                         # `git push origin main`
        src = src or dst                      # `git push origin :main` es borrado
        if not sep or src:
            dst = dst.replace("refs/heads/", "")
            src = src.replace("refs/heads/", "")
            # `git push origin HEAD` publica la rama ACTUAL, así que su destino
            # es esa rama y no el literal "HEAD". Sin esto el destino nunca
            # estaba en PROTEGIDAS y el push pasaba de largo: auditoría 22 (B2)
            # lo empujó de verdad a `origin/main`. El arnés probaba `HEAD:main`
            # —con dos puntos— y no `HEAD` a secas, que es como se teclea.
            if dst.lower() in ALIAS_DE_HEAD:
                dst = rama_actual
            if dst and not any(c in NO_ES_REF for c in dst):
                salidas.append((dst, src))
    return salidas


def bloquea_push(motivo, rama):
    """Exit 2 para el push. Mensaje propio: el fix no es el mismo que el merge."""
    sys.stderr.write(
        "PUSH BLOQUEADO — falta la evidencia de verde (hook merge-gate-guard).\n\n"
        f"{motivo}\n\n"
        "El contrato: lo que aterriza en una rama protegida tiene que estar\n"
        "verde, y el verde se mide sobre EL ÁRBOL QUE VIAJA, no sobre el que\n"
        "corriste hace un rato. Esto existe porque ya pasó: el gate corría en\n"
        "segundo plano sobre un SHA, entró un commit más en la misma rama, y el\n"
        "`--ff-only` se llevó los dos. La evidencia no cubría ese árbol.\n\n"
        "Produce la evidencia sobre lo que vas a empujar y repite el push:\n\n"
        f"    py \"$HOME/.claude/scripts/gate-test.py\" {rama}\n\n"
        "Si acabas de integrar una rama, el árbol de la protegida es NUEVO:\n"
        "el verde del frente no vale por sí solo, hay que correr la suite sobre\n"
        "el resultado de la integración.\n"
    )
    sys.exit(2)


def bloquea(motivo, comando_fix):
    """Exit 2 con un mensaje que ENSEÑA: qué faltó y cómo producirlo."""
    sys.stderr.write(
        "MERGE BLOQUEADO — falta la evidencia de verde (hook merge-gate-guard).\n\n"
        f"{motivo}\n\n"
        "El contrato: a una rama protegida solo se integra con un verde POSTERIOR\n"
        "al último commit de la rama, y producido por un comando, no por una\n"
        "afirmación. Produce la evidencia y repite el merge:\n\n"
        f"    {comando_fix}\n\n"
        "Ese helper corre la suite del proyecto y SOLO con exit 0 escribe\n"
        f"{EVIDENCIA}. Si la suite está roja, el merge no debe ocurrir: mal merge\n"
        "es peor que ningún merge.\n\n"
        "Y esto es solo la parte que una máquina puede verificar — el criterio\n"
        "completo (artefacto, tests que no escribió el implementador, squash y\n"
        "confirmación humana) está en la skill `workstream-merge-gate`.\n"
    )
    sys.exit(2)


# Verbos que MUEVEN la rama en la que estás. Si uno de estos cae sobre una
# protegida antes de un `git push` en la MISMA línea, el árbol que se empujaría
# todavía no existe cuando el hook corre (es PreToolUse), así que no hay nada
# que comparar. Ese caso se bloquea por no verificable, no por sospechoso.
MUTAN_LA_RAMA = re.compile(
    r"^git\s+(commit|merge|pull|cherry-pick|rebase|revert|reset|am)\b")


def revisa_push(rama_dst, ref_src, cwd, mutadas):
    """Bloquea si lo que se empuja a `rama_dst` no está cubierto por el verde.

    Se llama SOLO con `rama_dst` protegida. Dentro de la protegida es
    fail-closed: si no se puede verificar, se para — igual que en el merge.
    """
    if rama_dst in mutadas:
        bloquea_push(
            f"En esta misma línea se mueve `{rama_dst}` ANTES de empujarla, así "
            f"que el\nárbol que viajaría todavía no existe: no hay nada contra "
            f"qué comparar.\nSepara el push en su propio comando, con el verde "
            f"corrido sobre el\nresultado.", rama_dst)

    tip = git(["rev-parse", ref_src or rama_dst], cwd)
    if not tip:
        bloquea_push(
            f"`{ref_src or rama_dst}` no resuelve a ningún commit en este repo, "
            f"así que no\nse puede comprobar qué árbol viajaría a `{rama_dst}`.",
            rama_dst)

    # Push que no adelanta nada: no viaja ningún árbol nuevo, no hay nada que
    # gatear. Sin esto, un `git push` de cortesía tras un `pull` se bloquearía a
    # diario, y un gate que grita en falso se acaba desactivando.
    remoto = git(["rev-parse", f"origin/{rama_dst}"], cwd)
    if remoto and remoto == tip:
        return

    ruta = ruta_evidencia(cwd)
    if not os.path.exists(ruta):
        bloquea_push(f"No existe `{EVIDENCIA}`: no hay ningún verde registrado, "
                     f"y a `{rama_dst}`\nviajaría `{tip[:8]}`.", rama_dst)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            ev = json.load(f) or {}
    except Exception:
        bloquea_push(f"`{EVIDENCIA}` existe pero no es JSON legible.", rama_dst)

    sha_ev = str(ev.get("sha", ""))
    if sha_ev == tip:
        return                                 # el commit gateado, tal cual

    # El commit puede ser nuevo y el contenido el mismo: es lo que pasa con un
    # `merge --squash`, que el propio gate manda usar. Lo que tiene que estar
    # verde es el árbol, así que se compara el árbol.
    if sha_ev:
        t_tip = git(["rev-parse", f"{tip}^{{tree}}"], cwd)
        t_ev = git(["rev-parse", f"{sha_ev}^{{tree}}"], cwd)
        if t_tip and t_ev and t_tip == t_ev:
            return

    rama_ev = str(ev.get("branch", "")).replace("refs/heads/", "")
    bloquea_push(
        f"A `{rama_dst}` viajaría `{tip[:8]}`, y el verde registrado es de\n"
        f"`{sha_ev[:8] or '(vacío)'}` (rama `{rama_ev or '?'}`, "
        f"{ev.get('ts', 'sin fecha')}). Ni el commit ni su\n"
        f"árbol coinciden: ese contenido no lo ha probado nadie.",
        rama_dst)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)                                   # fail-open: entrada ilegible

    if (data.get("tool_name") or "") != "Bash":
        sys.exit(0)
    cmd = ((data.get("tool_input") or {}).get("command") or "").strip()
    # Atajo barato. `pull` entra porque es fetch+merge y no lleva la palabra;
    # `push` entra porque el verbo cambia pero el árbol que aterriza es el mismo.
    if not any(v in cmd for v in ("merge", "pull", "push")):
        sys.exit(0)

    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    # ── Destino efectivo: se simula el recorrido de la línea ──────────────
    actual = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd) or ""
    destino = anterior = actual
    mutadas = set()          # protegidas que esta línea mueve antes de empujar
    for seg in segmentos(cmd):
        salto = rama_de_checkout(seg)
        if salto == "-":                  # vuelve a la de antes, como git
            destino, anterior = anterior, destino
            continue
        if salto:
            destino, anterior = salto, destino
            continue
        # ── `git push` a protegida: mismo contrato, otro verbo ────────────
        empujes = destinos_de_push(seg, destino)
        if empujes == [("*", "*")]:            # --all / --mirror
            empujes = [(p, p) for p in sorted(PROTEGIDAS)
                       if git(["rev-parse", "--verify", p], cwd)]
        for rama_dst, ref_src in empujes:
            if rama_dst not in PROTEGIDAS:
                continue                       # rama de trabajo o tag: fail-open
            revisa_push(rama_dst, ref_src, cwd, mutadas)
        if empujes:
            continue

        if destino in PROTEGIDAS and MUTAN_LA_RAMA.match(
                sin_opciones_globales(seg) or seg):
            mutadas.add(destino)

        es_merge, fuente = fuente_de_merge(seg)
        if not es_merge:
            es_merge, fuente = fuente_de_pull(seg, destino)
        if not es_merge:
            continue
        if destino not in PROTEGIDAS:
            continue                                  # fuera de main no interviene

        helper = "py \"$HOME/.claude/scripts/gate-test.py\" <rama>"
        if not fuente:
            bloquea(
                f"El merge no nombra la rama a integrar, así que no se puede\n"
                f"comprobar contra qué verde validarlo (destino: `{destino}`).",
                helper.replace("<rama>", "<rama>") + "   # y `git merge <rama>`")
        helper = helper.replace("<rama>", fuente)

        ruta = ruta_evidencia(cwd)
        if not os.path.exists(ruta):
            bloquea(f"No existe `{EVIDENCIA}`: no hay ningún verde registrado "
                    f"para `{fuente}` → `{destino}`.", helper)
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                ev = json.load(f) or {}
        except Exception:
            bloquea(f"`{EVIDENCIA}` existe pero no es JSON legible.", helper)

        rama_ev = str(ev.get("branch", "")).replace("refs/heads/", "")
        if rama_ev != fuente:
            bloquea(f"La evidencia es de la rama `{rama_ev or '(vacía)'}`, "
                    f"pero se está integrando `{fuente}`.", helper)

        head = git(["rev-parse", fuente], cwd)
        sha_ev = str(ev.get("sha", ""))
        if not head:
            bloquea(f"`{fuente}` no resuelve a ningún commit en este repo.", helper)
        if sha_ev != head:
            bloquea(
                f"El verde registrado es de `{sha_ev[:8] or '(vacío)'}` y el HEAD\n"
                f"de `{fuente}` es `{head[:8]}`: la rama avanzó DESPUÉS de correr\n"
                f"la suite. Un verde anterior al último commit no es un verde\n"
                f"(registrado: {ev.get('ts', '?')}).", helper)

        # Evidencia fresca y sha coincidente: este merge pasa. Se SIGUE
        # recorriendo la línea en vez de salir, porque `git merge x && git push`
        # es un solo comando con dos puertas y antes solo se miraba la primera.
        continue

    sys.exit(0)


if __name__ == "__main__":
    main()
