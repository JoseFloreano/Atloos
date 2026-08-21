#!/usr/bin/env python3
"""
limpia-ramas.py — Qué ramas ya están en `main`, y cuáles se pueden borrar.

POR QUÉ EXISTE (2026-08-20). Las ramas se acumulan por dos vías distintas y las
dos estaban abiertas:

  · el **puente**: `remove_worktree` borraba la local y NUNCA tocaba el remoto,
    así que cada conversación dejaba su `origin/tg/*` para siempre — cinco
    contadas en campo. Eso se cierra en el daemon (`delete_remote_branch`).
  · el **gate**: su paso 7 manda limpiar, pero es una instrucción, no un
    mecanismo; y su propio texto cuenta a dónde lleva: **92 ramas remotas**, y
    bajarlas a 17 se comió una sesión sin producir nada.

Esto es para lo segundo, y para la basura ya acumulada.

## EL TEST DE «YA ESTÁ INTEGRADA», que es toda la dificultad

Tras un **squash**, los commits de la rama no son ancestros de `main`:
`git branch -d` la ve como no integrada y `git branch --merged` no la lista. Ese
es el motivo por el que nadie limpia — el comando obvio dice que no.

⚠ Y el test que parece obvio está AL REVÉS. `git diff main...rama` (tres puntos)
es *lo que la rama aporta desde que se bifurcó*: tras un squash eso NUNCA está
vacío, así que declararía «no integrada» justo el caso que importa. (Escrito
aquí porque es el error que este fichero estuvo a punto de tener.)

Los tres que sí valen, en orden de fuerza:

  1. **Ancestro** — `merge-base --is-ancestor rama base`. Merge normal: todos sus
     commits están en base. Es la prueba más fuerte que hay.
  2. **Mismo árbol** — `diff --quiet base rama`. Contenido idéntico: la rama no
     aporta nada aunque su historia sea otra.
  3. **Contenido de lo que tocó** — de los ficheros que la rama cambió respecto
     a su punto de bifurcación, ¿alguno difiere hoy entre `base` y la rama? Si
     ninguno difiere, lo suyo ya está dentro. **Este es el que caza el squash.**

Cualquier otra cosa sale como **SIN CONFIRMAR** y NO se borra. No hay cuarta
heurística: aquí una equivocación borra trabajo, y «no lo sé» es una respuesta
legítima que además se puede mirar a mano.

## Lo que no se toca nunca

La rama base · la que esté en HEAD · y **cualquiera con un worktree vivo**: si
hay un árbol montado sobre ella, alguien la está usando, y esa es exactamente la
regla («si sigue en uso, se queda»).

Uso:  setup/scripts/py setup/scripts/limpia-ramas.py              # solo lista
      setup/scripts/py setup/scripts/limpia-ramas.py --borrar     # borra las CONFIRMADAS
      setup/scripts/py setup/scripts/limpia-ramas.py --remotas    # mira también origin/*
      ... --base main --repo /ruta/al/repo
Salidas: 0 · 1 si algo falló al borrar
"""
import argparse
import os
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

INTEGRADA = "INTEGRADA"
SIN_CONFIRMAR = "SIN CONFIRMAR"


def git(args, repo, timeout=60):
    """(rc, salida). Nunca lanza: un limpiador que revienta no limpia nada."""
    try:
        p = subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, f"{type(exc).__name__}: {exc}"
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def rama_base(repo, declarada=""):
    """La rama principal. `origin/HEAD` manda; si no, `main`, si no `master`."""
    if declarada:
        return declarada
    rc, out = git(["symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"], repo)
    if rc == 0 and out:
        return out.rsplit("/", 1)[-1]
    for cand in ("main", "master"):
        if git(["rev-parse", "--verify", cand], repo)[0] == 0:
            return cand
    return "main"


def ramas_locales(repo):
    rc, out = git(["for-each-ref", "--format=%(refname:short)", "refs/heads/"], repo)
    return out.splitlines() if rc == 0 and out else []


def ramas_remotas(repo):
    rc, out = git(["for-each-ref", "--format=%(refname:short)", "refs/remotes/origin/"], repo)
    if rc != 0 or not out:
        return []
    return [r.split("/", 1)[1] for r in out.splitlines()
            if "/" in r and not r.endswith("/HEAD")]


def ramas_en_uso(repo):
    """Ramas con un worktree montado. Son las que alguien está usando AHORA.

    Se leen de `git worktree list --porcelain` y no de `git branch`, porque la
    marca `*` solo delata el worktree actual: las de los otros árboles —las del
    bot, justamente— no aparecerían.
    """
    rc, out = git(["worktree", "list", "--porcelain"], repo)
    if rc != 0:
        return set()
    return {l.split("refs/heads/", 1)[1].strip()
            for l in out.splitlines() if "refs/heads/" in l}


def veredicto(repo, base, rama):
    """(estado, motivo). Los tres tests de la cabecera, en orden de fuerza."""
    if git(["rev-parse", "--verify", rama], repo)[0] != 0:
        return SIN_CONFIRMAR, "no se pudo resolver la rama"

    if git(["merge-base", "--is-ancestor", rama, base], repo)[0] == 0:
        return INTEGRADA, "es ancestro de la base (merge normal)"

    if git(["diff", "--quiet", base, rama], repo)[0] == 0:
        return INTEGRADA, "mismo árbol que la base"

    rc, tocados = git(["diff", "--name-only", f"{base}...{rama}"], repo)
    if rc != 0:
        return SIN_CONFIRMAR, "no se pudieron listar sus ficheros"
    ficheros = [f for f in tocados.splitlines() if f.strip()]
    if not ficheros:
        return INTEGRADA, "no toca ningún fichero respecto a la base"
    rc, _ = git(["diff", "--quiet", base, rama, "--", *ficheros], repo)
    if rc == 0:
        return INTEGRADA, f"su contenido ya está en la base ({len(ficheros)} fichero(s), squash)"

    rc, difieren = git(["diff", "--name-only", base, rama, "--", *ficheros], repo)
    n = len([f for f in difieren.splitlines() if f.strip()]) if rc == 0 else "?"
    return SIN_CONFIRMAR, f"{n} fichero(s) difieren de la base: míralo a mano"


def revisar(repo, base, incluir_remotas=False):
    """[(ámbito, rama, estado, motivo)] de todo lo revisable, ya filtrado."""
    en_uso = ramas_en_uso(repo)
    filas = []
    for rama in ramas_locales(repo):
        if rama == base:
            continue
        if rama in en_uso:
            filas.append(("local", rama, "EN USO", "tiene un worktree montado: se queda"))
            continue
        estado, motivo = veredicto(repo, base, rama)
        filas.append(("local", rama, estado, motivo))
    if incluir_remotas:
        for rama in ramas_remotas(repo):
            if rama == base:
                continue
            # ⚠ El mismo filtro que arriba, y hacia falta decirlo dos veces.
            # Estando solo en el bucle local, una rama con worktree montado
            # salia "EN USO — se queda" y su remota se borraba EN LA MISMA
            # CORRIDA: el fichero se contradecia a si mismo y rompia el
            # invariante de su cabecera ("si alguien la esta usando, se queda").
            # Que la local sobreviva no lo arregla — la copia publicada es la
            # que ve la otra maquina. Medido el 2026-08-20 en laboratorio.
            if rama in en_uso:
                filas.append(("remota", rama, "EN USO",
                              "su rama local tiene un worktree montado: se queda"))
                continue
            estado, motivo = veredicto(repo, base, f"origin/{rama}")
            filas.append(("remota", rama, estado, motivo))
    return filas


def borrar(repo, ambito, rama):
    """(ok, motivo). Local con `-D` porque tras un squash `-d` se niega."""
    if ambito == "local":
        rc, out = git(["branch", "-D", rama], repo)
    else:
        rc, out = git(["push", "origin", "--delete", rama], repo, timeout=180)
        if rc != 0:
            # Que ya no estuviera no es un fallo. Pero se comprueba PREGUNTANDO
            # por la rama, no leyendo el mensaje: `git` habla el idioma del
            # sistema y un `"does not exist"` suelto casa tambien con errores
            # que no son este (y diria "borrada" de algo que sigue ahi).
            rc2, sigue = git(["ls-remote", "--heads", "origin", rama], repo, timeout=180)
            if rc2 == 0 and not sigue.strip():
                return True, "ya no estaba"
    return (rc == 0), (out.splitlines() or [""])[-1][:150]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Ramas ya integradas en la base.")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--base", default="")
    ap.add_argument("--remotas", action="store_true", help="mirar también origin/*")
    ap.add_argument("--borrar", action="store_true",
                    help="borrar las CONFIRMADAS (sin esto solo lista)")
    a = ap.parse_args(argv)

    base = rama_base(a.repo, a.base)
    if git(["rev-parse", "--verify", base], a.repo)[0] != 0:
        print(f"[ERROR] no existe la rama base '{base}' en {a.repo}", file=sys.stderr)
        return 1
    filas = revisar(a.repo, base, a.remotas)
    if not filas:
        print(f"No hay ramas además de '{base}'. Nada que limpiar.")
        return 0

    print(f"Base: {base}   ({a.repo})")
    # Esto NO hace fetch a propósito: un limpiador que toca la red antes de que
    # se lo pidas decide por ti con datos que no viste. Pero juzgar contra una
    # base atrasada declara «sin confirmar» ramas que sí están dentro, así que
    # el desfase se DICE en vez de corregirse a escondidas.
    rc, detras = git(["rev-list", "--count", f"{base}..origin/{base}"], a.repo)
    if rc == 0 and detras.strip().isdigit() and int(detras) > 0:
        print(f"  ⚠ tu '{base}' va {detras} commit(s) por detrás de 'origin/{base}'.\n"
              f"    Sin un `git pull` antes, esto dirá SIN CONFIRMAR de ramas que\n"
              f"    ya están integradas allí. No las borra: solo no las ve.")
    print()
    print(f"  {'ámbito':<8}{'rama':<46}estado")
    for ambito, rama, estado, motivo in filas:
        print(f"  {ambito:<8}{rama[:44]:<46}{estado} — {motivo}")

    integradas = [f for f in filas if f[2] == INTEGRADA]
    dudosas = [f for f in filas if f[2] == SIN_CONFIRMAR]
    print(f"\n  {len(integradas)} integrada(s) · {len(dudosas)} sin confirmar · "
          f"{len(filas) - len(integradas) - len(dudosas)} en uso")

    if not a.borrar:
        if integradas:
            print(f"\n  Nada borrado (falta `--borrar`). Con él se irían "
                  f"{len(integradas)}, y SOLO esas.")
        return 0

    fallos = []
    print()
    for ambito, rama, _e, _m in integradas:
        ok, motivo = borrar(a.repo, ambito, rama)
        print(f"  [{'OK  ' if ok else 'FALLA'}] {ambito} {rama}"
              + (f" — {motivo}" if not ok else ""))
        if not ok:
            fallos.append(rama)
    if dudosas:
        print(f"\n  {len(dudosas)} sin tocar: no se pudo confirmar que estén "
              f"dentro, y aquí equivocarse borra trabajo.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
