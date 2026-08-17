#!/usr/bin/env python3
"""
test-graph-report-hook.py — Arnés de `setup/hooks/git-post-commit-graph-report.sh`.

QUÉ DEFECTO CAZA (2026-08-14, reporte de campo del 08-14, H1). El hook corría:

    graphify . >/dev/null 2>&1 || true
    graphify cluster-only . --no-viz >/dev/null 2>&1 || true

Las dos salidas al vacío **y** el código de salida descartado. Cuando la
reconstrucción abortaba —en campo, `no LLM API key found (82 doc/paper/image
files need semantic extraction)`— la segunda línea **re-agrupaba el graph.json
viejo y le estampaba el HEAD actual**. El conteo llevó todo el día clavado en
13 188 nodos y una función creada esa mañana no aparecía en el grafo.

  **El hook no podía fallar, no podía avisar, y firmaba como fresco lo que
  estaba congelado.**

LA MUTACIÓN ES UN `graphify` DE MENTIRA EN EL `PATH`, y es la única forma
honesta de probarlo: el defecto no está en cómo el hook trata su propia lógica,
está en cómo trata el **código de salida de otro proceso**. Un doble que falla a
propósito ejerce exactamente esa juntura. El doble además **apunta cada
subcomando que recibe**, así que el arnés puede afirmar algo más fuerte que "no
se re-selló": puede afirmar que **`cluster-only` no llegó a ejecutarse**.

Los cuatro casos:

  1. **Reconstrucción que FALLA** → no se ejecuta `cluster-only`, no se re-sella
     el snapshot, se dice por stderr, y el hook **sale 0**. Las cuatro cosas.
  2. **Reconstrucción que va bien** → se ejecuta `cluster-only` y el snapshot SÍ
     se actualiza. Sin este caso el 1 no prueba nada: un hook que nunca hiciera
     nada también lo pasaría.
  3. **Commit sin código** → no se llama a graphify siquiera (contrato viejo del
     hook, que este cambio no debe romper).
  4. **El comando de reconstrucción es el que no necesita LLM.** `--code-only`
     NO existe en 0.9.5 —se ignora en silencio y el comando falla igual—, así
     que un hook que lo usara sería un no-op con aspecto de arreglo. Se exige
     `update` con `--no-cluster`, que la ayuda de graphify describe como
     *"re-extract code files and update the graph (no LLM needed)"*.

⚠ RUIDOSO NO ES BLOQUEANTE. Es un hook de `post-commit`: el commit ya está
hecho. Que salga 0 es parte del contrato, no una concesión — por eso el caso 1
lo comprueba explícitamente en vez de darlo por supuesto.

Uso:  setup/scripts/py setup/hooks/tests/test-graph-report-hook.py
Salidas: 0 los cuatro casos como se espera · 1 alguno falló.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

HOOK = (Path(__file__).resolve().parents[1] / "git-post-commit-graph-report.sh")

# El doble. Apunta el subcomando y decide el exit según GRAPHIFY_FAKE_RC, para
# que un mismo binario sirva a los dos casos sin reescribirlo.
DOBLE = """#!/bin/sh
echo "$@" >> "$GRAPHIFY_LOG"
case "$1" in
  update) exit ${GRAPHIFY_FAKE_RC:-0} ;;
  cluster-only)
      mkdir -p graphify-out
      printf '# Corpus Summary\\n\\nnodos: %s\\n' "$GRAPHIFY_SELLO" \
        > graphify-out/GRAPH_REPORT.md
      exit 0 ;;
esac
exit 0
"""


def monta(tmp, con_codigo=True):
    """Un repo de laboratorio con su commit hecho y un GRAPH_REPORT.md VIEJO."""
    repo = Path(tmp) / "repo"
    (repo / "graphify-out").mkdir(parents=True)
    (repo / "graphify-out" / "GRAPH_REPORT.md").write_text(
        "# Corpus Summary\n\nnodos: VIEJO\n", encoding="utf-8", newline="\n")
    (repo / "CLAUDE.md").write_text("## Active Project: `laboratorio`\n",
                                    encoding="utf-8", newline="\n")
    (repo / "m.py").write_text("x = 1\n", encoding="utf-8", newline="\n")
    (repo / "notas.md").write_text("nota\n", encoding="utf-8", newline="\n")

    def git(*args):
        subprocess.run(["git", *args], cwd=repo, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    git("add", "-A")
    git("commit", "-q", "-m", "raiz")

    # HACEN FALTA DOS COMMITS. `git diff-tree -r HEAD` sobre un commit RAÍZ no
    # imprime nada (sin `--root` no hay con qué comparar), así que el paso 1 del
    # hook no vería ningún fichero de código y el hook saldría en silencio: el
    # arnés estaría midiendo la ausencia de padre, no la lógica que persigue. Un
    # repo real siempre tiene padre.
    nombre = "m.py" if con_codigo else "notas.md"
    (repo / nombre).write_text("x = 2\n", encoding="utf-8", newline="\n")
    git("add", "-A")
    git("commit", "-q", "-m", "commit de laboratorio")

    binario = Path(tmp) / "bin"
    binario.mkdir()
    (binario / "graphify").write_text(DOBLE, encoding="utf-8", newline="\n")
    os.chmod(binario / "graphify", 0o755)
    return repo, binario


def corre(tmp, repo, binario, rc, sello, vault):
    """(exit, stderr, subcomandos, reporte_en_disco)."""
    log = Path(tmp) / "llamadas.txt"
    log.write_text("", encoding="utf-8")
    env = dict(os.environ)
    env["PATH"] = str(binario) + os.pathsep + env["PATH"]
    env["GRAPHIFY_LOG"] = str(log)
    env["GRAPHIFY_FAKE_RC"] = str(rc)
    env["GRAPHIFY_SELLO"] = sello
    # El vault se redirige a un directorio del laboratorio: el hook busca
    # `<ROOT>/DevSetup/ObsidianVault/10-Projects/<proyecto>` bajo $OneDrive y
    # demás, así que apuntando esas variables aquí no se toca el vault real.
    for k in ("OneDrive", "USERPROFILE", "HOME", "LOCALAPPDATA", "XDG_DATA_HOME"):
        env[k] = str(vault)
    p = subprocess.run(["sh", str(HOOK)], cwd=repo, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    return (p.returncode,
            p.stderr.decode("utf-8", "replace") + p.stdout.decode("utf-8", "replace"),
            log.read_text(encoding="utf-8"),
            (repo / "graphify-out" / "GRAPH_REPORT.md").read_text(encoding="utf-8"))


def main():
    print("Hook del reporte de Graphify — mutación del código de salida\n")
    fallos = []

    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp) / "vaultroot" / "DevSetup" / "ObsidianVault" / \
            "10-Projects" / "laboratorio"
        vault.mkdir(parents=True)
        raiz_vault = Path(tmp) / "vaultroot"

        # 1 · la reconstrucción FALLA
        repo, binario = monta(tmp)
        rc, salida, llamadas, reporte = corre(tmp, repo, binario, 1, "NUEVO", raiz_vault)
        problemas = []
        if "cluster-only" in llamadas:
            problemas.append("se ejecutó `cluster-only` tras una reconstrucción "
                             "fallida — ese es el paso que re-sella el grafo viejo")
        if "VIEJO" not in reporte:
            problemas.append("el GRAPH_REPORT.md se reescribió: el sello se estampó igual")
        if "AVISO" not in salida:
            problemas.append("no dijo nada: el fallo sigue siendo invisible")
        if rc != 0:
            problemas.append(f"salió {rc}: un post-commit ruidoso NO es bloqueante")
        if (vault / "codebase-map-snapshot.md").exists():
            problemas.append("re-selló el snapshot del vault pese al fallo")
        print(f"  [1] reconstrucción FALLIDA            "
              f"{'OK — no re-sella, avisa, y sale 0' if not problemas else 'FALLIDO'}")
        for x in problemas:
            print(f"      · {x}")
        if problemas:
            fallos.append("1")

    with tempfile.TemporaryDirectory() as tmp:
        raiz_vault = Path(tmp) / "vaultroot"
        (raiz_vault / "DevSetup" / "ObsidianVault" / "10-Projects" /
         "laboratorio").mkdir(parents=True)
        vault = raiz_vault / "DevSetup" / "ObsidianVault" / "10-Projects" / "laboratorio"

        # 2 · la reconstrucción va BIEN (el reverso: sin esto, el caso 1 no prueba nada)
        repo, binario = monta(tmp)
        rc, salida, llamadas, reporte = corre(tmp, repo, binario, 0, "NUEVO", raiz_vault)
        problemas = []
        if "cluster-only" not in llamadas:
            problemas.append("no se ejecutó `cluster-only`: el hook dejó de hacer su trabajo")
        if "NUEVO" not in reporte:
            problemas.append("el reporte no se regeneró")
        if not (vault / "codebase-map-snapshot.md").exists():
            problemas.append("no se escribió el recorte en el vault")
        if rc != 0:
            problemas.append(f"salió {rc}")
        print(f"  [2] reconstrucción CORRECTA           "
              f"{'OK — re-agrupa y sella' if not problemas else 'FALLIDO'}")
        for x in problemas:
            print(f"      · {x}")
        if problemas:
            fallos.append("2")

        # 4 · el comando de reconstrucción es el que NO necesita LLM
        problemas = []
        if "update" not in llamadas or "--no-cluster" not in llamadas:
            problemas.append(f"no se llamó a `update --no-cluster`; llamadas: "
                             f"{llamadas.strip()!r}")
        if "--code-only" in llamadas:
            problemas.append("usa `--code-only`, que NO existe en 0.9.5: se ignora "
                             "en silencio y el comando falla igual. Un no-op con "
                             "aspecto de arreglo")
        print(f"  [4] el comando no necesita clave      "
              f"{'OK — `update --no-cluster`' if not problemas else 'FALLIDO'}")
        for x in problemas:
            print(f"      · {x}")
        if problemas:
            fallos.append("4")

    with tempfile.TemporaryDirectory() as tmp:
        raiz_vault = Path(tmp) / "vaultroot"
        (raiz_vault / "DevSetup" / "ObsidianVault" / "10-Projects" /
         "laboratorio").mkdir(parents=True)

        # 3 · commit sin código → ni se llama a graphify
        repo, binario = monta(tmp, con_codigo=False)
        rc, salida, llamadas, _r = corre(tmp, repo, binario, 0, "NUEVO", raiz_vault)
        ok3 = rc == 0 and not llamadas.strip()
        print(f"  [3] commit sin código                 "
              f"{'OK — no llama a graphify' if ok3 else 'FALLIDO'}")
        if not ok3:
            fallos.append("3")
            print(f"      exit {rc}; llamadas: {llamadas.strip()!r}")

    if fallos:
        print(f"\n{len(fallos)} caso(s) fallidos ({', '.join(sorted(fallos))}).")
        return 1
    print("\n  4/4. Un fallo de reconstrucción ya no puede firmarse como grafo\n"
          "  fresco, y el hook sigue sin poder tumbar un commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
