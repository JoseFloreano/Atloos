#!/usr/bin/env python3
"""
test-merge-ya-integrada.py — El `/merge` repetido, y el gemelo del veredicto.

EL FALLO QUE CIERRA (2026-08-19, medido desde el móvil) →
[[bug-merge-rama-ya-squasheada]]. Un `/merge` sobre una rama que YA se había
integrado por squash no era un no-op: el squash mete el CONTENIDO en la base
pero **no la ANCESTRÍA**, así que para git la rama sigue sin mergear y el
segundo intento vuelve a mezclarla ENTERA contra una base que ya la tiene:

    CONFLICT (content): Merge conflict in setup/telegram-bridge/tg_daemon.py
    Tu árbol quedó como estaba (revertido).

El usuario veía un conflicto y culpaba al fichero. La causa era que nadie había
preguntado si la rama ya estaba dentro.

Y LA SEGUNDA MITAD, que es la que evita el fallo de mañana. Los tres tests de
integración existen DOS veces —`gitops.ya_integrada` (async, el daemon) y
`limpia-ramas.veredicto` (subprocess, la línea de comandos)—, porque son
runtimes distintos y el código no se puede compartir. Lo que sí se comparte es
la RESPUESTA, así que aquí se comparan **caso a caso**: si alguien toca uno y no
el otro, esto se pone rojo y le dice a cuál ir. Una duplicación medida es una
duplicación gobernada; una duplicación silenciosa es la que se desincroniza.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-merge-ya-integrada.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import asyncio
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_AQUI = Path(__file__).resolve()
sys.path.insert(0, str(_AQUI.parents[1]))
import gitops  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "limpia_ramas", _AQUI.parents[2] / "scripts" / "limpia-ramas.py")
limpia = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(limpia)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ.update({
    "GIT_AUTHOR_NAME": "arnes", "GIT_AUTHOR_EMAIL": "arnes@local",
    "GIT_COMMITTER_NAME": "arnes", "GIT_COMMITTER_EMAIL": "arnes@local",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
})

results = []


def check(nombre, ok, detalle=""):
    results.append((nombre, bool(ok)))
    print(f"[{'OK  ' if ok else 'FALLA'}] {nombre}"
          + (f" -- {detalle}" if not ok and detalle else ""))


def g(args, cwd):
    p = subprocess.run(["git", "-C", str(cwd), *args], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def escribe(repo, nombre, texto):
    (Path(repo) / nombre).write_text(texto, encoding="utf-8", newline="\n")


def laboratorio(tmp):
    """Repo con `main` y las cuatro situaciones que hay que distinguir."""
    repo = Path(tmp) / "repo"
    repo.mkdir()
    g(["init", "-b", "main"], repo)
    escribe(repo, "base.txt", "base\n")
    g(["add", "-A"], repo); g(["commit", "-m", "base"], repo)

    g(["checkout", "-b", "aplastada", "main"], repo)      # el caso del bug
    escribe(repo, "toca.txt", "uno\n")
    g(["add", "-A"], repo); g(["commit", "-m", "uno"], repo)
    escribe(repo, "toca.txt", "dos\n")
    g(["add", "-A"], repo); g(["commit", "-m", "dos"], repo)
    g(["checkout", "main"], repo)
    g(["merge", "--squash", "aplastada"], repo)
    g(["commit", "-m", "squash de aplastada"], repo)

    g(["checkout", "-b", "normal", "main"], repo)         # merge normal
    escribe(repo, "normal.txt", "n\n")
    g(["add", "-A"], repo); g(["commit", "-m", "normal"], repo)
    g(["checkout", "main"], repo)
    g(["merge", "--no-ff", "-m", "merge normal", "normal"], repo)

    g(["checkout", "-b", "viva", "main"], repo)           # el contrapeso
    escribe(repo, "viva.txt", "trabajo sin integrar\n")
    g(["add", "-A"], repo); g(["commit", "-m", "viva"], repo)

    g(["checkout", "-b", "aplastada-vieja", "main"], repo)  # squash + main avanzó
    escribe(repo, "vieja.txt", "v\n")
    g(["add", "-A"], repo); g(["commit", "-m", "vieja"], repo)
    g(["checkout", "main"], repo)
    g(["merge", "--squash", "aplastada-vieja"], repo)
    g(["commit", "-m", "squash de vieja"], repo)
    escribe(repo, "posterior.txt", "main siguio\n")
    g(["add", "-A"], repo); g(["commit", "-m", "main avanza"], repo)
    return repo


RAMAS = ["aplastada", "normal", "viva", "aplastada-vieja"]


def main():
    # --- Casos 1-3: el /merge repetido se rechaza ANTES de tocar el árbol ---
    with tempfile.TemporaryDirectory(prefix="mergeyaint-") as tmp:
        repo = laboratorio(tmp)
        antes = g(["rev-parse", "HEAD"], repo)[1]

        r = asyncio.run(gitops.merge_squash(str(repo), "aplastada", "main", "otra vez"))
        check("1. LA QUE MANDA: el 2.º /merge de una rama aplastada no mezcla nada",
              (not r["merged"]) and r.get("ya_integrada"), f"{r!r}")
        check("2. y el motivo nombra el squash en vez de culpar a un fichero",
              "squash" in r.get("reason", ""), f"reason={r.get('reason')!r}")
        check("3. y `main` quedó EXACTAMENTE donde estaba (ni un commit, ni un conflicto)",
              g(["rev-parse", "HEAD"], repo)[1] == antes
              and not g(["status", "--porcelain"], repo)[1],
              f"antes={antes[:7]} ahora={g(['rev-parse', 'HEAD'], repo)[1][:7]}")

        # El contrapeso: la rama con trabajo de verdad SÍ se integra. Sin esto,
        # "no mezclar nunca" también pasaría los tres casos de arriba.
        r2 = asyncio.run(gitops.merge_squash(str(repo), "viva", "main", "integra viva"))
        check("4. EL CONTRAPESO: la rama con trabajo sin integrar sí se mezcla",
              r2["merged"], f"{r2!r}")

    # --- Casos 5+: los dos veredictos, comparados rama a rama ---
    with tempfile.TemporaryDirectory(prefix="mergeyaint-") as tmp:
        repo = laboratorio(tmp)
        for rama in RAMAS:
            aqui = asyncio.run(gitops.ya_integrada(str(repo), rama, "main"))[0]
            alli = limpia.veredicto(repo, "main", rama)[0] == limpia.INTEGRADA
            check(f"5.{rama} · gitops y limpia-ramas dicen lo mismo",
                  aqui == alli,
                  f"gitops.ya_integrada={aqui} limpia.veredicto={alli} "
                  f"-> uno de los dos se quedó atrás; están emparejados a propósito")

    fallos = [n for n, ok in results if not ok]
    print(f"\n[test-merge-ya-integrada] {len(results) - len(fallos)}/{len(results)} en verde.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
