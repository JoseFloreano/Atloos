#!/usr/bin/env python3
"""
test-limpia-ramas.py — Arnés de `setup/scripts/limpia-ramas.py`.

EL CASO QUE MANDA ES EL 3: una rama integrada **por squash**. Es el caso real
—el `/merge` del puente y el gate aplastan siempre— y es justo el que los
comandos obvios no ven: tras un squash, `git branch -d` la declara «no
integrada» y `git branch --merged` no la lista. Por eso nadie limpia.

Y el 5 es su contrapeso: una rama con trabajo de verdad **no puede** salir como
integrada. Un limpiador que se equivoca en esa dirección borra trabajo, así que
aquí se fabrican las dos y se exige que las distinga.

⚠ EL ERROR QUE ESTE ARNÉS EXISTE PARA IMPEDIR QUE VUELVA. La primera versión del
test iba a ser `git diff base...rama` vacío. Tres puntos es *lo que la rama
aporta desde la bifurcación*: tras un squash NUNCA está vacío, así que habría
declarado «no integrada» exactamente el caso 3 — y el limpiador no habría
limpiado nada, en silencio y para siempre.

Se ejerce sobre repos git FABRICADOS, no sobre este: los estados que importan
—squash, divergencia, worktree vivo— hay que construirlos para saber que se
distinguen. Correrlo sobre el repo real diría «hoy funcionó».

Uso:  setup/scripts/py setup/scripts/tests/test-limpia-ramas.py   [repo]
Salidas: 0 todo verde · 1 algún caso falló
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir)))
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "limpia_ramas", Path(__file__).resolve().parents[1] / "limpia-ramas.py")
limpia = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(limpia)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Identidad por entorno: una caja headless puede no tener `user.email`, y
# entonces fallaría el commit del arnés y no lo que el arnés mide.
os.environ.update({
    "GIT_AUTHOR_NAME": "arnes", "GIT_AUTHOR_EMAIL": "arnes@local",
    "GIT_COMMITTER_NAME": "arnes", "GIT_COMMITTER_EMAIL": "arnes@local",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
})

results = []


def check(nombre, ok, detalle=""):
    results.append((nombre, bool(ok)))
    print(f"[{'OK  ' if ok else 'FALLA'}] {nombre}" + (f" -- {detalle}" if not ok and detalle else ""))


def g(args, repo):
    p = subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def escribe(repo, nombre, texto):
    (Path(repo) / nombre).write_text(texto, encoding="utf-8", newline="\n")


def laboratorio(tmp):
    """Repo con main y cuatro ramas, una por cada estado que hay que distinguir."""
    repo = Path(tmp) / "repo"
    repo.mkdir()
    g(["init", "-b", "main"], repo)
    escribe(repo, "base.txt", "base\n")
    g(["add", "-A"], repo); g(["commit", "-m", "base"], repo)

    # a) integrada por MERGE NORMAL (sus commits son ancestros de main)
    g(["checkout", "-b", "normal"], repo)
    escribe(repo, "normal.txt", "n\n")
    g(["add", "-A"], repo); g(["commit", "-m", "normal"], repo)
    g(["checkout", "main"], repo)
    g(["merge", "--no-ff", "-m", "merge normal", "normal"], repo)

    # b) integrada por SQUASH — el caso real del puente y del gate
    g(["checkout", "-b", "aplastada", "main"], repo)
    escribe(repo, "aplastada.txt", "a\n")
    g(["add", "-A"], repo); g(["commit", "-m", "uno"], repo)
    escribe(repo, "aplastada.txt", "a2\n")
    g(["add", "-A"], repo); g(["commit", "-m", "dos"], repo)
    g(["checkout", "main"], repo)
    g(["merge", "--squash", "aplastada"], repo)
    g(["commit", "-m", "squash de aplastada"], repo)

    # c) VIVA: tiene trabajo que main no tiene
    g(["checkout", "-b", "viva", "main"], repo)
    escribe(repo, "viva.txt", "trabajo sin integrar\n")
    g(["add", "-A"], repo); g(["commit", "-m", "viva"], repo)
    g(["checkout", "main"], repo)

    # d) squash + main avanzó DESPUÉS (el caso que engaña a los tests ingenuos)
    g(["checkout", "-b", "aplastada-vieja", "main"], repo)
    escribe(repo, "vieja.txt", "v\n")
    g(["add", "-A"], repo); g(["commit", "-m", "vieja"], repo)
    g(["checkout", "main"], repo)
    g(["merge", "--squash", "aplastada-vieja"], repo)
    g(["commit", "-m", "squash de vieja"], repo)
    escribe(repo, "posterior.txt", "main siguió\n")
    g(["add", "-A"], repo); g(["commit", "-m", "main avanza"], repo)
    return repo


def estado_de(filas, rama):
    return next((f[2] for f in filas if f[1] == rama), None)


def main():
    if not shutil.which("git"):
        print("[SKIP] no hay git en esta máquina: el limpiador no se puede ejercer")
        return 0

    with tempfile.TemporaryDirectory(prefix="limpiaramas-") as tmp:
        repo = laboratorio(tmp)
        filas = limpia.revisar(repo, "main")

        check("1. la rama integrada por merge NORMAL sale integrada",
              estado_de(filas, "normal") == limpia.INTEGRADA, f"{filas!r}")
        check("2. y su motivo dice cuál de los tres tests la salvó",
              "ancestro" in next(f[3] for f in filas if f[1] == "normal"), f"{filas!r}")
        check("3. LA QUE MANDA: la integrada por SQUASH sale integrada",
              estado_de(filas, "aplastada") == limpia.INTEGRADA, f"{filas!r}")
        check("4. y también si main avanzó DESPUÉS del squash",
              estado_de(filas, "aplastada-vieja") == limpia.INTEGRADA, f"{filas!r}")
        check("5. EL CONTRAPESO: la rama con trabajo NO sale integrada",
              estado_de(filas, "viva") == limpia.SIN_CONFIRMAR, f"{filas!r}")
        check("6. la base nunca aparece en la lista",
              not any(f[1] == "main" for f in filas), f"{filas!r}")

        # --- Caso 7: sin --borrar no se borra nada ---
        rc = limpia.main(["--repo", str(repo), "--base", "main"])
        _, ramas = g(["for-each-ref", "--format=%(refname:short)", "refs/heads/"], repo)
        check("7. sin --borrar no desaparece ninguna rama",
              rc == 0 and "aplastada" in ramas and "viva" in ramas, f"ramas={ramas!r}")

        # --- Caso 8: con --borrar se van las integradas y SOLO esas ---
        rc = limpia.main(["--repo", str(repo), "--base", "main", "--borrar"])
        _, ramas = g(["for-each-ref", "--format=%(refname:short)", "refs/heads/"], repo)
        quedan = set(ramas.split())
        check("8. con --borrar se van las integradas", rc == 0
              and "aplastada" not in quedan and "normal" not in quedan
              and "aplastada-vieja" not in quedan, f"quedan={quedan!r}")
        check("8b. y la rama con trabajo SIGUE ahí", "viva" in quedan, f"quedan={quedan!r}")
        check("8c. y la base también", "main" in quedan, f"quedan={quedan!r}")

    # --- Caso 9: una rama con worktree vivo no se toca, aunque esté integrada ---
    # Es la regla que pediste: si alguien la está usando, se queda.
    with tempfile.TemporaryDirectory(prefix="limpiaramas-") as tmp:
        repo = laboratorio(tmp)
        wt = Path(tmp) / "arbol-vivo"
        rc, out = g(["worktree", "add", str(wt), "aplastada"], repo)
        if rc != 0:
            print(f"[SKIP] 9. no se pudo montar un worktree de laboratorio: {out[:120]}")
        else:
            filas = limpia.revisar(repo, "main")
            check("9. rama con worktree vivo: EN USO, no se borra",
                  estado_de(filas, "aplastada") == "EN USO", f"{filas!r}")
            limpia.main(["--repo", str(repo), "--base", "main", "--borrar"])
            _, ramas = g(["for-each-ref", "--format=%(refname:short)", "refs/heads/"], repo)
            check("9b. y sigue existiendo tras --borrar", "aplastada" in ramas.split(),
                  f"ramas={ramas!r}")

    # --- Caso 10: el test ingenuo que casi se escribe, ejercido para que conste ---
    # `diff base...rama` vacío habría dicho «no integrada» para el squash. Se
    # comprueba que ese diff NO está vacío, o sea que el test ingenuo fallaba.
    with tempfile.TemporaryDirectory(prefix="limpiaramas-") as tmp:
        repo = laboratorio(tmp)
        rc, salida = g(["diff", "--name-only", "main...aplastada"], repo)
        check("10. queda constancia: `diff base...rama` NO sirve para el squash",
              rc == 0 and bool(salida.strip()),
              "si esto sale vacío, el test ingenuo habría funcionado y esta nota sobra")

    # --- Casos 11-13: el ámbito `--remotas`, que no se ejercía en absoluto ---
    # Por eso pasó el fallo: el filtro de "en uso" vivía solo en el bucle local,
    # y la misma rama salía "EN USO — se queda" (local) mientras su copia
    # publicada se borraba en la MISMA corrida. Medido el 2026-08-20.
    with tempfile.TemporaryDirectory(prefix="limpiaramas-") as tmp:
        repo = laboratorio(tmp)
        bare = Path(tmp) / "remoto.git"
        g(["init", "--bare", str(bare)], Path(tmp))
        g(["remote", "add", "origin", str(bare)], repo)
        g(["push", "--all", "origin"], repo)
        # Un worktree vivo sobre `aplastada`, que POR CONTENIDO ya está dentro:
        # es justo la combinación que hacía falta — integrada Y en uso.
        wt = Path(tmp) / "wt"
        g(["worktree", "add", str(wt), "aplastada"], repo)

        filas = limpia.revisar(str(repo), "main", incluir_remotas=True)
        remotas = [f for f in filas if f[0] == "remota"]
        check("11. `--remotas` mira de verdad el ámbito remoto",
              len(remotas) >= 4, f"remotas={[f[1] for f in remotas]!r}")
        check("12. LA QUE MANDA: remota con worktree vivo NO sale integrada",
              next((f[2] for f in remotas if f[1] == "aplastada"), None) == "EN USO",
              f"{[f for f in remotas if f[1] == 'aplastada']!r}")

        limpia.main(["--repo", str(repo), "--base", "main", "--remotas", "--borrar"])
        _rc, quedan = g(["ls-remote", "--heads", str(bare)], repo)
        check("13. y sigue publicada tras --borrar",
              "refs/heads/aplastada\n" in quedan + "\n" or "/aplastada" in quedan,
              f"quedan={quedan!r}")
        g(["worktree", "remove", "--force", str(wt)], repo)

    print()
    fallos = [n for n, ok in results if not ok]
    print(f"[test-limpia-ramas] {len(results) - len(fallos)}/{len(results)} en verde.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
