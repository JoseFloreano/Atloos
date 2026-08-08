#!/usr/bin/env python3
"""
gate-test.py — Produce la evidencia de verde que exige el hook merge-gate-guard.

Corre el comando de test del proyecto y, **solo si sale con exit 0**, escribe
`.claude/gate-verde.json` con `{branch, sha, ts, cmd}`. El `sha` es el HEAD de la
rama en el momento de correr: si luego llega un commit más, la evidencia deja de
casar sola y el merge vuelve a estar bloqueado. Eso ES el "verde posterior al
último commit" del paso 2 de `workstream-merge-gate`, hecho verificable.

Por qué existe: la palabra del agente no es evidencia. En la prueba deliberada
del gate, una sesión afirmó "los tests pasaron hoy mismo" sobre un árbol que ya
había avanzado. Aquí el verde lo firma un exit code, no una frase.

Uso:
    py gate-test.py <rama>                    # usa el comando declarado
    py gate-test.py <rama> --cmd "pytest -q"  # o uno explícito

El comando se resuelve, en este orden:
  1. `--cmd`
  2. `GATE_TEST_CMD` del entorno
  3. el bloque "## Comando de test" del CLAUDE.md del repo (primera línea de su
     bloque de código)
Sin ninguno de los tres, no inventa nada: sale con error y lo dice. Sin comando
de test declarado no hay verde posible, y sin verde no se mergea.

Ruta estable: `sync-skills` lo instala en `~/.claude/scripts/` (F13 — una skill
corre desde el cwd de cualquier proyecto, así que no puede citar rutas del repo).
"""
import json
import os
import re
import subprocess
import sys
import time

EVIDENCIA = os.path.join(".claude", "gate-verde.json")


def git(args, cwd="."):
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=10)
        return p.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def comando_declarado(raiz):
    """Primera línea del bloque de código bajo '## Comando de test' en CLAUDE.md."""
    ruta = os.path.join(raiz, "CLAUDE.md")
    try:
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            texto = f.read()
    except OSError:
        return ""
    m = re.search(r"^#+\s*Comando de test\s*$(.*?)```(?:\w+)?\s*\n(.+?)\n",
                  texto, re.S | re.M | re.I)
    return m.group(2).strip() if m else ""


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print("uso: gate-test.py <rama> [--cmd \"<comando>\"]", file=sys.stderr)
        return 2
    rama = args[0]
    cmd = ""
    if "--cmd" in args:
        i = args.index("--cmd")
        if i + 1 < len(args):
            cmd = args[i + 1]

    raiz = git(["rev-parse", "--show-toplevel"]) or os.getcwd()
    cmd = cmd or os.environ.get("GATE_TEST_CMD", "") or comando_declarado(raiz)
    if not cmd:
        print("Sin comando de test declarado: no hay verde posible y no se\n"
              "mergea. Declara uno en el CLAUDE.md del repo bajo '## Comando de\n"
              "test', o pásalo con --cmd. Si el proyecto no tiene suite, redefine\n"
              "el verde (build? lint?) o este patrón no aplica aquí.",
              file=sys.stderr)
        return 2

    sha = git(["rev-parse", rama], raiz)
    if not sha:
        print(f"La rama '{rama}' no resuelve a ningún commit.", file=sys.stderr)
        return 2

    actual = git(["rev-parse", "--abbrev-ref", "HEAD"], raiz)
    if actual != rama:
        print(f"[gate-test] AVISO: estás en '{actual}' y la evidencia se pide "
              f"para '{rama}'.\n            La suite corre sobre el árbol de "
              f"trabajo actual, así que\n            haz checkout de '{rama}' "
              f"antes, o la evidencia mentirá.", file=sys.stderr)
        return 2

    print(f"[gate-test] {cmd}   (rama {rama} @ {sha[:8]})")
    rc = subprocess.run(cmd, shell=True, cwd=raiz).returncode
    if rc != 0:
        print(f"\n[gate-test] SUITE EN ROJO (exit {rc}). No se escribe evidencia:\n"
              f"            el merge sigue bloqueado, que es lo correcto.",
              file=sys.stderr)
        return 1

    destino = os.path.join(raiz, EVIDENCIA)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump({"branch": rama, "sha": sha,
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "cmd": cmd}, f)
    print(f"\n[gate-test] VERDE registrado en {EVIDENCIA} ({rama} @ {sha[:8]}).\n"
          f"            Si llega otro commit, esta evidencia caduca sola.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
