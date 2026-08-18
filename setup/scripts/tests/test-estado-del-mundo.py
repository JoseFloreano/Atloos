#!/usr/bin/env python3
"""
test-estado-del-mundo.py — El generador del bloque 2, contra un repo fabricado.

POR QUÉ SE EJERCE SOBRE UN REPO DE LABORATORIO Y NO SOBRE ESTE. Los hallazgos
que importan —una rama por delante de `main`, dos ramas tocando el mismo
fichero, un artefacto ignorado presente— hay que **fabricarlos** para saber que
se cazan. Correrlo sobre el repo real diría «funcionó hoy» y no distinguiría
«los detecta» de «hoy no había ninguno». Es la misma ley que gobierna las
autopruebas por mutación del resto de la suite.

LO QUE MÁS SE VIGILA AQUÍ NO ES QUE MIDA BIEN: es que **no invente**. La razón
de existir del generador es que el bloque escrito a mano llevó tres datos
falsos, así que un generador que rellena lo que no midió sería peor que el
problema — tendría la autoridad de venir de una herramienta. §D comprueba que
lo no medido sale como `HUECO` **con el comando que lo llena**, y no en blanco
ni omitido.

Uso:  setup/scripts/py setup/scripts/tests/test-estado-del-mundo.py   [repo]
Salidas: 0 todos los casos OK · 1 alguno falló
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

GEN = Path(__file__).resolve().parents[1] / "estado-del-mundo.py"
results = []


def caso(nombre, condicion, detalle=""):
    results.append(bool(condicion))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle[:300]}")


def sh(args, cwd):
    subprocess.run(args, cwd=cwd, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=True)


def repo_lab():
    """Un repo con LOS defectos dentro: rama por delante, dos ramas pisándose
    el mismo fichero, y un artefacto ignorado presente."""
    d = tempfile.mkdtemp(prefix="estado-mundo-lab-")
    sh(["git", "init", "-q", "-b", "main"], d)
    sh(["git", "config", "user.email", "t@t"], d)
    sh(["git", "config", "user.name", "t"], d)
    (Path(d) / "compartido.py").write_text("x = 1\n")
    (Path(d) / ".gitignore").write_text("secretos/\n*.local\n")
    sh(["git", "add", "-A"], d)
    sh(["git", "commit", "-q", "-m", "base"], d)

    # Dos ramas que tocan EL MISMO fichero: la colisión que el bloque 2 existe
    # para destapar antes de despachar, no después.
    for rama, linea in (("frente-a", "a = 1\n"), ("frente-b", "b = 2\n")):
        sh(["git", "checkout", "-q", "-b", rama, "main"], d)
        with open(os.path.join(d, "compartido.py"), "a") as f:
            f.write(linea)
        sh(["git", "add", "-A"], d)
        sh(["git", "commit", "-q", "-m", f"cambio de {rama}"], d)

    # Y la sesión actual, por delante de `main`: el desfase que un worktree
    # nuevo no vería.
    sh(["git", "checkout", "-q", "-b", "sesion", "main"], d)
    (Path(d) / "nuevo.py").write_text("y = 2\n")
    sh(["git", "add", "-A"], d)
    sh(["git", "commit", "-q", "-m", "trabajo de la sesion"], d)

    # Artefacto fuera de git, presente aquí y ausente en cualquier worktree.
    os.makedirs(os.path.join(d, "secretos"), exist_ok=True)
    (Path(d) / "secretos" / "padron.csv").write_text("id,valor\n1,2\n")
    return d


def genera(repo, *flags):
    p = subprocess.run([sys.executable, str(GEN), repo, *flags],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace"), \
        p.stderr.decode("utf-8", "replace")


def main():
    print("Generador del estado del mundo (bloque 2)\n")
    d = repo_lab()
    rc, out, err = genera(d)

    print("A · corre y produce el bloque")
    caso("sale 0 sobre un repo sano", rc == 0, err)
    caso("emite el encabezado del bloque 2", "## 2 · Estado del mundo" in out)
    caso("se declara generado y pide no editarlo a mano",
         "No lo edites a mano" in out)

    print("\nB · el desfase de la base — el dato que motivó la doctrina")
    caso("dice cuántos commits NO vería un worktree nuevo",
         "no vería tus 1 commit(s)" in out,
         "un worktree nace en `main`; si esto no sale, el frente trabaja "
         "contra un repo viejo sin que nada se lo diga")
    caso("nombra el merge-base", "`git merge-base`" in out)

    print("\nC · las colisiones, que son el hallazgo (la lista es solo material)")
    caso("caza el fichero que tocan DOS ramas",
         "los tocan DOS o más ramas" in out and "compartido.py" in out)
    caso("lista las ramas vivas", "frente-a" in out and "frente-b" in out)
    caso("el artefacto ignorado PRESENTE aparece", "secretos/" in out,
         "es la diferencia entre esta máquina y lo que la suite supone")

    print("\nD · lo que no midió sale como HUECO, no en blanco ni omitido")
    caso("sin --con-suite, la firma de la suite es un hueco declarado",
         "HUECO" in out and "--con-suite" in out)
    caso("sin --dos-baselines, el segundo baseline es un hueco declarado",
         "--dos-baselines" in out)
    caso("todo hueco trae el comando que lo llena",
         all("Se llena con:" in b or "escríbelo tú" in b
             for b in out.split("HUECO —")[1:]),
         "un hueco sin salida es una queja, no un producto")
    caso("la firma de fallos conocidos se declara NO generable",
         "es un juicio, no una medición" in out)

    print("\nE · no se cae donde no hay nada que medir")
    vacio = tempfile.mkdtemp(prefix="estado-mundo-vacio-")
    sh(["git", "init", "-q", "-b", "main"], vacio)
    rc2, out2, err2 = genera(vacio)
    caso("un repo sin commits no lo tumba", rc2 == 0, err2)
    caso("...y lo dice como hueco en vez de callarse", "HUECO" in out2)
    shutil.rmtree(vacio, ignore_errors=True)

    rc3, _o, _e = genera(str(Path(d) / "no-existe"))
    caso("una ruta inexistente sale 1 y no genera un bloque falso", rc3 == 1)

    shutil.rmtree(d, ignore_errors=True)
    fallos = results.count(False)
    print(f"\n{len(results) - fallos}/{len(results)} casos OK")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
