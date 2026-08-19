#!/usr/bin/env python3
"""
test-commit-marcado.py — Un commit del puente tiene que poder distinguirse.

POR QUE EXISTE (auditoria 39 §8.2, arreglado el 2026-08-19). El 2026-08-18 el
puente empujo TRES commits a `main` desde Telegram. Sus metadatos:

    autor:     Jose Floreano <...>      committer: Jose Floreano <...>
    cuerpo:    (vacio)                  trailers:  ninguno
    asunto:    "Solo enlista pendientes rapido"  <- el prompt de chat, truncado

**Nada en git decia que los habia hecho un bot.** Ninguna sesion podia saber que
`main` se habia movido por Telegram y no por una persona; el sprint 16 arranco
declarando una base que ya no existia y estuvo a punto de trabajar sobre ella.
Uno de esos commits traia 20 ficheros y ~2100 lineas, directo a `main`.

EL INVARIANTE:

    todo commit que crea el puente lleva el trailer `Via: telegram-bridge`,
    legible por `git log --format=%(trailers)` sin configurar nada.

Se comprueba EJERCIENDO `gitops.commit_all` contra un repo git de verdad en un
temporal, y leyendo el trailer con git — no mirando si la palabra aparece en el
fuente. La diferencia importa: un trailer pegado en la linea equivocada del
mensaje NO es un trailer para git, y una comprobacion por texto lo daria por
bueno. El caso 3 es justo ese: se lee con `%(trailers)`, que es lo que un hook
o una sesion usarian.

NO comprueba la autoria: sigue siendo de quien pidio el trabajo, y eso es
deliberado (el ADR del puente: el humano es el autor, el bot es el medio).

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-commit-marcado.py
Salidas: 0 todo verde · 1 algun caso fallo · [SKIP] si no hay git utilizable
Solo stdlib.
"""
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BRIDGE = AQUI.parent
sys.path.insert(0, str(BRIDGE))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import gitops  # noqa: E402

results = []


def check(nombre, condicion, detalle=""):
    results.append((nombre, bool(condicion)))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle}")


def git(repo, *args):
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip()


def repo_de_prueba(raiz):
    """Un repo git minimo, con identidad propia para no depender de la global."""
    for args in (("init", "-q", "-b", "main"),
                 ("config", "user.email", "arnes@ejemplo"),
                 ("config", "user.name", "Arnes")):
        rc, out = git(raiz, *args)
        if rc != 0:
            return False, f"`git {args[0]}` fallo: {out}"
    (Path(raiz) / "hola.txt").write_text("uno\n", encoding="utf-8")
    return True, ""


def main():
    print("Arnes del commit marcado (el puente se distingue del humano)\n")

    if not gitops.shutil.which("git"):
        print("  [SKIP] no hay `git` en esta maquina: el invariante se comprueba "
              "donde el puente pueda commitear de verdad")
        print("\nModo: PARCIAL")
        return 0

    with tempfile.TemporaryDirectory(prefix="commit-marcado-") as raiz:
        ok, motivo = repo_de_prueba(raiz)
        if not ok:
            print(f"  [SKIP] no pude montar el repo de prueba: {motivo}")
            print("\nModo: PARCIAL")
            return 0

        MENSAJE = "Solo enlista pendientes rapido"
        r = asyncio.run(gitops.commit_all(raiz, MENSAJE))

        check("1. el commit se hizo", r.get("committed"),
              f"gitops devolvio {r}")
        if not r.get("committed"):
            return resumen()

        # 2 — el asunto NO se toca: el trailer va abajo, no encima del titulo.
        rc, asunto = git(raiz, "log", "-1", "--pretty=%s")
        check("2. el asunto sigue siendo el del humano, intacto",
              asunto == MENSAJE,
              f"asunto={asunto!r}: el trailer se comio o ensucio el titulo")

        # 3 — EL CASO. Se lee con `%(trailers)`, que es lo que usaria un hook.
        # Una comprobacion por texto daria verde a un trailer mal colocado.
        rc, trailers = git(raiz, "log", "-1", "--pretty=%(trailers:key=Via)")
        check("3. `git` lo reconoce como TRAILER, no como texto suelto",
              "telegram-bridge" in trailers,
              f"%(trailers:key=Via) devolvio {trailers!r}: el mensaje lleva la "
              f"linea pero git no la lee como trailer (le falta el parrafo "
              f"aparte), asi que ningun hook puede filtrarla")

        # 4 — y no se duplica si el mensaje ya lo traia.
        (Path(raiz) / "hola.txt").write_text("dos\n", encoding="utf-8")
        r2 = asyncio.run(gitops.commit_all(
            raiz, f"otro cambio\n\n{gitops.COMMIT_TRAILER}"))
        rc, cuerpo = git(raiz, "log", "-1", "--pretty=%B")
        check("4. no se duplica si el mensaje ya lo traia",
              r2.get("committed") and cuerpo.count("Via: telegram-bridge") == 1,
              f"aparece {cuerpo.count('Via: telegram-bridge')} veces")

        # 5 — ANTI-ARTEFACTO: un commit hecho a mano en ese mismo repo NO lo
        # lleva. Sin esto, el caso 3 podria estar pasando porque `git` devuelve
        # algo para cualquier commit.
        (Path(raiz) / "hola.txt").write_text("tres\n", encoding="utf-8")
        git(raiz, "add", "-A")
        git(raiz, "commit", "-q", "-m", "commit humano, sin pasar por el puente")
        rc, trailers_h = git(raiz, "log", "-1", "--pretty=%(trailers:key=Via)")
        check("5. anti-artefacto: un commit humano NO lleva el trailer",
              "telegram-bridge" not in trailers_h,
              f"un commit hecho a mano tambien sale marcado ({trailers_h!r}): "
              f"el trailer no distingue nada")

    return resumen()


def resumen():
    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos en verde")
    if fallos:
        print("FALLAN:")
        for n in fallos:
            print(f"  · {n}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
