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

QUÉ BLOQUEA. Solo `git merge` cuyo destino efectivo sea una rama protegida
(`main`/`master`) sin **evidencia determinista de verde**: un
`.claude/gate-verde.json` `{branch, sha, ts, cmd}` cuyo `sha` coincida con el
HEAD actual de la rama que se integra. Esa evidencia la escribe
`scripts/gate-test.py`, que solo la produce con exit 0 de la suite — la palabra
del agente nunca es evidencia.

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

PROTEGIDAS = {"main", "master"}
EVIDENCIA = os.path.join(".claude", "gate-verde.json")

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


# Un ref de git no lleva estos caracteres. Si el "nombre de rama" los trae, no
# es un comando: es prosa que casualmente empieza por `git merge`.
NO_ES_REF = set("`'\"()[]{}<>,¿?¡!*:\\ ")


def sin_heredocs(cmd):
    """Quita el CUERPO de los heredocs, que es texto, no comandos.

    Lo aprendió bloqueando su propio commit: el mensaje explicaba el caso
    `git checkout main && git merge x` y el hook lo leyó como un merge de
    verdad. El contenido de un heredoc nunca se ejecuta.
    """
    fuera, saltando, cierre = [], False, None
    for linea in cmd.splitlines():
        if saltando:
            if linea.strip() == cierre:
                saltando = False
            continue
        m = re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", linea)
        if m:
            saltando, cierre = True, m.group(1)
        fuera.append(linea)
    return "\n".join(fuera)


def segmentos(cmd):
    """Parte una línea de shell en comandos, respetando el orden."""
    cmd = sin_heredocs(cmd)
    return [s.strip() for s in re.split(r"&&|\|\||;|\n", cmd) if s.strip()]


def rama_de_checkout(seg):
    """Rama a la que salta un `git checkout/switch`, o None."""
    m = re.match(r"^git\s+(?:checkout|switch)\s+(.*)$", seg)
    if not m:
        return None
    for tok in m.group(1).split():
        if tok.startswith("-"):
            continue          # -b, -q, --detach… la rama es el primer no-flag
        return tok.strip("'\"")
    return None


def fuente_de_merge(seg):
    """(es_merge, rama_origen|None). rama None = merge sin argumento."""
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


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)                                   # fail-open: entrada ilegible

    if (data.get("tool_name") or "") != "Bash":
        sys.exit(0)
    cmd = ((data.get("tool_input") or {}).get("command") or "").strip()
    if "merge" not in cmd:                            # atajo barato
        sys.exit(0)

    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    # ── Destino efectivo: se simula el recorrido de la línea ──────────────
    actual = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd) or ""
    destino = actual
    for seg in segmentos(cmd):
        salto = rama_de_checkout(seg)
        if salto:
            destino = salto
            continue
        es_merge, fuente = fuente_de_merge(seg)
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

        ruta = os.path.join(cwd, EVIDENCIA)
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

        # Evidencia fresca y sha coincidente: el hook no estorba.
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
