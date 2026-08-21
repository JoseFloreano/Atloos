#!/usr/bin/env python3
"""
test-borra-remota.py — Arnés de `gitops.delete_remote_branch`.

EL FALLO QUE CIERRA (2026-08-20). `remove_worktree` borraba la rama LOCAL y
**nunca tocaba el remoto**. Cada conversación del bot publicaba su rama con
`/push` y ahí se quedaba: en campo se contaron **cinco** `origin/tg/*` de
conversaciones ya integradas y cerradas. El paso 7 del merge-gate ya cuenta a
dónde lleva: se llegó a 92 ramas remotas.

LOS DOS CASOS QUE MANDAN, y son las dos direcciones del mismo riesgo:

  · 1 — la rama publicada de una conversación cerrada **desaparece del remoto**.
  · 3 — si el remoto tiene commits que NO son los que se integraron (alguien
    empujó ahí desde otra máquina), **NO se borra**. Al llegar aquí la local ya
    no existe, así que el remoto puede ser la ÚNICA copia: fallar cerrado cuesta
    una rama de más, fallar abierto cuesta el trabajo de otro.

Se ejerce contra un remoto de verdad (un bare local), no contra un doble: lo que
se persigue es el comportamiento de `git push --delete` y de `ls-remote`, y un
doble que los imite sería una suposición mía sobre git.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-borra-remota.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import asyncio
import os
import shutil
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
    print(f"[{'OK  ' if ok else 'FALLA'}] {nombre}" + (f" -- {detalle}" if not ok and detalle else ""))


def g(args, cwd):
    p = subprocess.run(["git", *args], cwd=str(cwd), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=60)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def escribe(p, texto):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(texto, encoding="utf-8", newline="\n")


def laboratorio(tmp):
    """(bare, clon) con `main` y una rama `tg/x` publicada, como tras un /push."""
    bare = Path(tmp) / "origen.git"
    g(["init", "--bare", "-b", "main", str(bare)], tmp)
    clon = Path(tmp) / "clon"
    g(["clone", str(bare), str(clon)], tmp)
    escribe(clon / "base.txt", "base\n")
    g(["add", "-A"], clon); g(["commit", "-m", "base"], clon)
    g(["push", "-u", "origin", "main"], clon)
    g(["checkout", "-b", "tg/x"], clon)
    escribe(clon / "trabajo.txt", "t\n")
    g(["add", "-A"], clon); g(["commit", "-m", "trabajo"], clon)
    g(["push", "-u", "origin", "tg/x"], clon)
    return bare, clon


def remotas(bare):
    _rc, out = g(["for-each-ref", "--format=%(refname:short)", "refs/heads/"], bare)
    return set(out.split())


def main():
    if not shutil.which("git"):
        print("[SKIP] no hay git en esta máquina: el borrado remoto no se mide")
        return 0

    # --- Caso 1: la rama publicada e integrada desaparece del remoto ---
    with tempfile.TemporaryDirectory(prefix="borraremota-") as tmp:
        bare, clon = laboratorio(tmp)
        _rc, sha = g(["rev-parse", "HEAD"], clon)
        r = asyncio.run(gitops.delete_remote_branch(str(clon), "tg/x", sha))
        check("1. la rama publicada se borra del remoto",
              r["borrada"] and "tg/x" not in remotas(bare),
              f"{r!r} · remotas={remotas(bare)!r}")

    # --- Caso 2: si ya no estaba, se dice y NO es un fallo ---
    with tempfile.TemporaryDirectory(prefix="borraremota-") as tmp:
        bare, clon = laboratorio(tmp)
        g(["push", "origin", "--delete", "tg/x"], clon)
        r = asyncio.run(gitops.delete_remote_branch(str(clon), "tg/x", ""))
        check("2. rama ya ausente del remoto: no es fallo, y lo dice",
              r["borrada"] is False and "publicada" in r["motivo"], f"{r!r}")

    # --- Caso 3: EL QUE PROTEGE. Otro empujó ahí -> NO se borra ---
    with tempfile.TemporaryDirectory(prefix="borraremota-") as tmp:
        bare, clon = laboratorio(tmp)
        _rc, sha_integrado = g(["rev-parse", "HEAD"], clon)
        otro = Path(tmp) / "otra-maquina"
        g(["clone", str(bare), str(otro)], tmp)
        g(["checkout", "tg/x"], otro)
        escribe(otro / "de-otra-maquina.txt", "trabajo de alguien más\n")
        g(["add", "-A"], otro); g(["commit", "-m", "otro"], otro)
        g(["push"], otro)
        r = asyncio.run(gitops.delete_remote_branch(str(clon), "tg/x", sha_integrado))
        check("3. el remoto avanzó por fuera: NO se borra",
              (not r["borrada"]) and "tg/x" in remotas(bare), f"{r!r}")
        check("3b. y el motivo nombra los dos shas para poder mirarlo",
              sha_integrado[:7] in r["motivo"], f"motivo={r['motivo']!r}")

    # --- Caso 4: sin sha que comparar, NO se borra ---
    # ⚠ CAMBIO DE CONTRATO (2026-08-20, auditoría). Este caso afirmaba lo
    # contrario —"sin sha, borra igual"— y contradecía la cabecera de la propia
    # función, que manda fallar CERRADO porque al llegar ahí el remoto puede ser
    # la única copia. Sin sha no se compara nada: es exactamente la duda que la
    # regla cubre, no una excepción a ella. Fallar cerrado cuesta una rama de
    # más y `limpia-ramas.py --remotas` la recoge; fallar abierto cuesta trabajo
    # de otra máquina, que no se recoge de ningún sitio.
    with tempfile.TemporaryDirectory(prefix="borraremota-") as tmp:
        bare, clon = laboratorio(tmp)
        r = asyncio.run(gitops.delete_remote_branch(str(clon), "tg/x", ""))
        check("4. sin sha local NO borra, y el remoto sigue ahí",
              (not r["borrada"]) and "tg/x" in remotas(bare), f"{r!r}")
        check("4b. y el motivo dice qué hacer con la rama que queda",
              "limpia-ramas" in r["motivo"], f"motivo={r['motivo']!r}")

    # --- Caso 5: repo sin remoto -> motivo, no excepción ---
    with tempfile.TemporaryDirectory(prefix="borraremota-") as tmp:
        suelto = Path(tmp) / "suelto"
        suelto.mkdir()
        g(["init", "-b", "main", "."], suelto)
        escribe(suelto / "a.txt", "a\n")
        g(["add", "-A"], suelto); g(["commit", "-m", "a"], suelto)
        r = asyncio.run(gitops.delete_remote_branch(str(suelto), "tg/x", ""))
        check("5. repo sin remoto: (False, motivo) y ni una excepción",
              (not r["borrada"]) and "remoto" in r["motivo"], f"{r!r}")

    # --- Caso 6: sin rama, no se inventa nada ---
    r = asyncio.run(gitops.delete_remote_branch(os.getcwd(), "", ""))
    check("6. sin rama que borrar: no toca nada", not r["borrada"], f"{r!r}")

    print()
    fallos = [n for n, ok in results if not ok]
    print(f"[test-borra-remota] {len(results) - len(fallos)}/{len(results)} en verde.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
