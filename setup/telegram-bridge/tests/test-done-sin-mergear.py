#!/usr/bin/env python3
"""
test-done-sin-mergear.py — Que `/done` no se lleve trabajo que nadie integró.

EL FALLO QUE CIERRA (2026-08-20, auditoría). `remove_worktree` preguntaba
"¿está integrada?" con `git branch -d` y leyendo su exit code. No es esa la
pregunta que `-d` responde: `-d` responde "¿es seguro borrarla?", y su criterio
incluye **el upstream**. Una rama que hizo `/push` está contenida en
`origin/<ella misma>` por definición, así que `-d` salía 0 aunque la base no
tuviera ni uno de sus commits — y `remove_worktree` la marcaba `branch_deleted`.

Solo eso ya perdía la rama local. Lo grave llegó con `8f24a48`, que encadenó
`delete_remote_branch` a esa MISMA señal: la conversación que publicaba y no
mergeaba se quedaba sin worktree, sin rama local y **sin rama remota**. Las tres
copias. Reproducido contra el código real antes de arreglarlo.

LO QUE SE AFIRMA, en las dos direcciones (un arnés que solo mira el caso bueno
no habría cazado nada: antes del arreglo, los casos 3 y 4 ya pasaban):

  · 1 — publicada y NO mergeada: la rama se CONSERVA y el remoto sigue ahí.
  · 2 — y la trampa que lo causaba sigue viva en git, así que el caso 1 mide
    algo: `-d` sale 0 sobre esa misma rama. Si git cambiara y `-d` empezara a
    negarse, este caso lo diría en vez de dejar el 1 pasando por casualidad.
  · 3 — mergeada de verdad (ancestro de la base): se borra. El arreglo no puede
    volverse una excusa para no limpiar nunca.
  · 4 — squash con `merged=True`: se borra (ahí `-d` se niega y toca `-D`).

Se ejerce contra repos de git de verdad, con worktree y remoto bare: lo que se
persigue es el comportamiento de `git branch -d` frente al upstream, y un doble
que lo imitara sería justamente la suposición que causó el fallo.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-done-sin-mergear.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir)))
import gitops  # noqa: E402

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


def g(args, cwd, check_rc=True):
    p = subprocess.run(["git", *args], cwd=str(cwd), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    if check_rc and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: "
                           f"{p.stdout.decode('utf-8', 'replace')}")
    return p.returncode, p.stdout.decode("utf-8", "replace")


def remotas(bare):
    return g(["ls-remote", "--heads", str(bare)], bare)[1]


def laboratorio(tmp, rama, publicar=True):
    """Repo + bare + un worktree sobre `rama` con un commit propio.

    Devuelve (bare, repo, worktree). La base se llama `main` porque es lo que
    `default_branch` busca, que es parte de lo que se está midiendo.
    """
    bare = Path(tmp) / "remoto.git"
    repo = Path(tmp) / "repo"
    wt = Path(tmp) / "wt"
    g(["init", "-q", "--bare", str(bare)], Path(tmp))
    g(["clone", "-q", str(bare), str(repo)], Path(tmp))
    (repo / "a.txt").write_text("base\n", encoding="utf-8")
    g(["add", "."], repo)
    g(["commit", "-qm", "base"], repo)
    g(["branch", "-M", "main"], repo)
    g(["push", "-q", "-u", "origin", "main"], repo)

    g(["worktree", "add", "-q", "-b", rama, str(wt)], repo)
    (wt / "trabajo.txt").write_text("TRABAJO QUE NADIE INTEGRO\n", encoding="utf-8")
    g(["add", "."], wt)
    g(["commit", "-qm", "trabajo"], wt)
    if publicar:                      # esto es el `/push` del puente
        g(["push", "-q", "-u", "origin", rama], wt)
    return bare, repo, wt


def main():
    # --- Casos 1 y 2: publicada, NO mergeada -> se conserva entera ---
    with tempfile.TemporaryDirectory(prefix="donesinmerge-") as tmp:
        rama = "tg/sin-mergear"
        bare, repo, wt = laboratorio(tmp, rama)
        sha = asyncio.run(gitops.head_sha(str(wt), short=False))

        # La trampa, medida ANTES de tocar nada: la base no la contiene y aun
        # así `-d` la borraría. Se pregunta sobre una copia para no gastar la
        # rama de verdad, que el caso 1 necesita intacta. ⚠ La copia necesita
        # el MISMO upstream: `git branch <copia> <rama>` no lo hereda, y sin
        # upstream `-d` juzga contra HEAD y se niega — o sea, mediría otra cosa
        # y el caso pasaría por el motivo equivocado.
        g(["branch", "espejo", rama], repo)
        g(["branch", f"--set-upstream-to=origin/{rama}", "espejo"], repo)
        no_ancestro = g(["merge-base", "--is-ancestor", rama, "main"],
                        repo, check_rc=False)[0] != 0
        d_borraria = g(["branch", "-d", "espejo"], repo, check_rc=False)[0] == 0
        check("2. la trampa sigue viva: no es ancestro y aun así `-d` la borra",
              no_ancestro and d_borraria,
              f"no_ancestro={no_ancestro} d_borraria={d_borraria}")

        # `/done` sin `/merge`: es exactamente lo que calcula cmd_done (integro=False)
        r = asyncio.run(gitops.remove_worktree(str(repo), str(wt), rama, merged=False))
        conservada = not r["branch_deleted"]
        if r.get("branch_deleted"):           # la guarda de cmd_done
            asyncio.run(gitops.delete_remote_branch(str(repo), rama, sha))
        check("1. publicada y sin mergear: la rama se conserva",
              conservada, f"{r!r}")
        check("1b. y el remoto sigue teniendo el trabajo",
              rama in remotas(bare), remotas(bare))
        check("1c. y lo dice en vez de callarlo",
              "sin mergear" in r["branch_status"], f"{r['branch_status']!r}")

    # --- Caso 3: mergeada de verdad -> sí se limpia, local y remoto ---
    with tempfile.TemporaryDirectory(prefix="donesinmerge-") as tmp:
        rama = "tg/mergeada"
        bare, repo, wt = laboratorio(tmp, rama)
        sha = asyncio.run(gitops.head_sha(str(wt), short=False))
        g(["merge", "-q", "--no-ff", "-m", "integra", rama], repo)

        r = asyncio.run(gitops.remove_worktree(str(repo), str(wt), rama, merged=False))
        rm = (asyncio.run(gitops.delete_remote_branch(str(repo), rama, sha))
              if r.get("branch_deleted") else {"borrada": False})
        check("3. mergeada (ancestro de la base): se borra aunque merged=False",
              r["branch_deleted"], f"{r!r}")
        check("3b. y la remota también se va", rm["borrada"] and rama not in remotas(bare),
              f"{rm!r}")

    # --- Caso 4: squash con merged=True -> `-d` se niega, `-D` la quita ---
    with tempfile.TemporaryDirectory(prefix="donesinmerge-") as tmp:
        rama = "tg/squasheada"
        bare, repo, wt = laboratorio(tmp, rama)
        g(["merge", "-q", "--squash", rama], repo)
        g(["commit", "-qm", "squash"], repo)

        no_ancestro = g(["merge-base", "--is-ancestor", rama, "main"],
                        repo, check_rc=False)[0] != 0
        r = asyncio.run(gitops.remove_worktree(str(repo), str(wt), rama, merged=True))
        check("4. squash con merged=True: se borra pese a no ser ancestro",
              no_ancestro and r["branch_deleted"], f"no_ancestro={no_ancestro} {r!r}")

    fallos = [n for n, ok in results if not ok]
    print(f"\n[test-done-sin-mergear] {len(results) - len(fallos)}/{len(results)} en verde.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
