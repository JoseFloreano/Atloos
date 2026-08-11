#!/usr/bin/env python3
"""
test-testcmd.py — Arnés de contrato de setup/telegram-bridge/testcmd.py.

De dónde sale el comando que corre /test, y por tanto de qué depende el verde
que /merge exige. Hasta el 2026-08-09 salía solo de projects.json, donde atloos
declaraba `compileall`: un /merge desde el móvil entraba a main con un verde que
no ejecutaba ni uno de los 9 arneses.

El caso que manda es el 1: el REPO gana sobre projects.json. Si perdiera, la
copia vieja de otra laptop seguiría imponiendo su verde débil, porque
projects.json es por-máquina y no viaja.

Uso:  py setup/telegram-bridge/tests/test-testcmd.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir)))
import testcmd  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'OK  ' if ok else 'FALLA'}] {name}" + (f" -- {detail}" if detail and not ok else ""))


def worktree(tmp, contenido_settings=None, local=None):
    """Worktree de laboratorio. contenido_settings: str crudo o None."""
    d = os.path.join(tmp, "wt")
    os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
    if contenido_settings is not None:
        with open(os.path.join(d, ".claude", "settings.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(contenido_settings)
    if local is not None:
        with open(os.path.join(d, ".claude", "settings.local.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"env": {"GATE_TEST_CMD": local}}))
    return d


def settings_con(cmd):
    return json.dumps({"env": {"GATE_TEST_CMD": cmd}})


def main():
    # --- Caso 1: el repo gana sobre projects.json ---
    with tempfile.TemporaryDirectory(prefix="testcmd-") as tmp:
        wt = worktree(tmp, settings_con("py setup/scripts/run-tests.py"))
        got = testcmd.resolver(wt, {"path": wt, "test": "py -m compileall -q setup"})
        check("1. settings.json del repo gana sobre projects.json",
              got == "py setup/scripts/run-tests.py", f"got={got!r}")

    # --- Caso 2: sin settings.json, cae a projects.json ---
    with tempfile.TemporaryDirectory(prefix="testcmd-") as tmp:
        wt = worktree(tmp)
        got = testcmd.resolver(wt, {"path": wt, "test": "pytest -q"})
        check("2. sin settings.json -> fallback a projects.json",
              got == "pytest -q", f"got={got!r}")

    # --- Caso 3: sin ninguno de los dos -> cadena vacía ---
    with tempfile.TemporaryDirectory(prefix="testcmd-") as tmp:
        wt = worktree(tmp)
        got = testcmd.resolver(wt, {"path": wt})
        check("3. sin declaración de ningún tipo -> ''", got == "", f"got={got!r}")

    # --- Caso 4: settings.json roto no revienta, cae al fallback ---
    with tempfile.TemporaryDirectory(prefix="testcmd-") as tmp:
        wt = worktree(tmp, "{ esto no es json")
        try:
            got = testcmd.resolver(wt, {"path": wt, "test": "pytest -q"})
            ok, detalle = got == "pytest -q", f"got={got!r}"
        except Exception as exc:
            ok, detalle = False, f"reventó: {type(exc).__name__}: {exc}"
        check("4. settings.json roto -> no revienta, usa el fallback", ok, detalle)

    # --- Caso 5: settings.json sin bloque env -> fallback ---
    with tempfile.TemporaryDirectory(prefix="testcmd-") as tmp:
        wt = worktree(tmp, json.dumps({"permissions": {"allow": []}}))
        got = testcmd.resolver(wt, {"path": wt, "test": "pytest -q"})
        check("5. settings.json sin bloque env -> fallback", got == "pytest -q", f"got={got!r}")

    # --- Caso 5b: settings.json válido pero SIN objeto en la raíz (array) ---
    # JSON sintácticamente correcto cuyo nivel superior no es un objeto: sin la
    # guarda `isinstance(datos, dict)` esto revienta con AttributeError, que
    # aquí no capturaría ni cmd_test ni cmd_write y se propagaría al daemon.
    # Debe comportarse como cualquier settings.json inservible: cae al fallback.
    with tempfile.TemporaryDirectory(prefix="testcmd-") as tmp:
        wt = worktree(tmp, "[1, 2, 3]")
        try:
            got = testcmd.resolver(wt, {"path": wt, "test": "pytest -q"})
            ok, detalle = got == "pytest -q", f"got={got!r}"
        except Exception as exc:
            ok, detalle = False, f"reventó: {type(exc).__name__}: {exc}"
        check("5b. settings.json es un array (JSON válido, no objeto) -> "
              "no revienta, usa el fallback", ok, detalle)

    # --- Caso 6: metacaracteres -> ComandoInvalido, no un split mal hecho ---
    for meta, cmd in (("&&", "pytest -q && ruff check"),
                      ("||", "pytest -q || true"),
                      ("|",  "pytest -q | tee out.txt"),
                      (";",  "pytest -q; ruff check")):
        with tempfile.TemporaryDirectory(prefix="testcmd-") as tmp:
            wt = worktree(tmp, settings_con(cmd))
            try:
                got = testcmd.resolver(wt, {"path": wt})
                ok, detalle = False, f"no lanzó nada, devolvió {got!r}"
            except testcmd.ComandoInvalido as exc:
                # No basta con "meta in str(exc)": el mensaje tambien echoa el
                # comando completo, y "|" es substring de "||", asi que ese
                # in-check pasaba aunque el codigo hubiera nombrado "|" en vez
                # de "||". Se ancla al fragmento exacto que nombra el meta.
                frag = f"trae '{meta}'"
                ok, detalle = frag in str(exc), f"el mensaje no tiene {frag!r}: {exc}"
            except Exception as exc:
                ok, detalle = False, f"excepción equivocada: {type(exc).__name__}"
            check(f"6{meta}. comando con '{meta}' -> ComandoInvalido", ok, detalle)

    # --- Caso 7 (CANARIO): settings.local.json NO se lee ---
    with tempfile.TemporaryDirectory(prefix="testcmd-") as tmp:
        wt = worktree(tmp, local="py -c pass")
        got = testcmd.resolver(wt, {"path": wt, "test": "pytest -q"})
        check("7. CANARIO: settings.local.json no declara nada",
              got == "pytest -q", f"got={got!r}")

    # --- Caso 8: worktree None o vacío no revienta ---
    got_ok = True
    try:
        testcmd.resolver(None, {"test": "pytest -q"})
        testcmd.resolver("", {"test": "pytest -q"})
    except Exception as exc:
        got_ok = False
        detalle = f"reventó: {type(exc).__name__}: {exc}"
    check("8. worktree None o '' -> no revienta", got_ok,
          "" if got_ok else detalle)

    fallos = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
