#!/usr/bin/env python3
"""
test-medir-disparo.py — El ejecutable que reescribe una SKILL.md, ejercido.

EL HUECO QUE CIERRA (2026-08-20, auditoría) → [[bug-medir-disparo-sin-arnes]].
`setup/scripts/medir-disparo.py` entró en `main` con `bb17cb5`: 475 líneas que
con `--aplicar` **reescriben el bloque `description:` de una SKILL.md
versionada**. La suite siguió en los mismos arneses que había antes del commit
(`ls setup/scripts/tests/ | grep disparo` → nada), así que el fichero que decide
si una skill dispara podía reescribirse sin que nada lo comprobara.

Y no se ejercía por un motivo real: medir de verdad lanza invocaciones **de
pago**. Por eso lo que se ejerce aquí es la parte que escribe, extraída a dos
funciones puras — `reescribe_description` y `escribe_atomico`— que no gastan un
céntimo. Lo que este arnés NO cubre queda dicho, no fingido: la medición en sí
(coste real) y el pulso al CLI de Claude.

LOS DOS DEFECTOS QUE SE PERSIGUEN, y sus contrapesos:

  · 1-3 — **la escritura no era atómica**. `write_text` trunca antes de
    escribir: un Ctrl-C ahí deja la skill partida en el árbol. Se comprueba que
    un fallo a mitad **deja el original intacto y no abandona basura**, que es
    la única forma de afirmar "atómica" en vez de suponerla.
  · 4-6 — **el backslash en la prosa**. `re.sub` interpreta `\\1` y `\\g<...>` en
    el texto de sustitución. El código ya usa `lambda` para evitarlo, pero eso
    no estaba medido: aquí se mide, porque es el fallo que se arregla solo hasta
    que alguien "simplifica" la lambda a una cadena.
  · 7 — el contrapeso: una cabecera que NO trae el bloque devuelve n=0 y no
    toca nada, en vez de inventarse dónde escribir.

Uso:  setup/scripts/py setup/scripts/tests/test-medir-disparo.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

_FUENTE = Path(__file__).resolve().parents[1] / "medir-disparo.py"
_spec = importlib.util.spec_from_file_location("medir_disparo", _FUENTE)
md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md)

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

results = []


def check(nombre, ok, detalle=""):
    results.append((nombre, bool(ok)))
    print(f"[{'OK  ' if ok else 'FALLA'}] {nombre}"
          + (f" -- {detalle}" if not ok and detalle else ""))


SKILL_MD = """---
name: ejemplo
description: >
  La vieja, que ocupa
  dos lineas plegadas.
---

# Ejemplo

Cuerpo que NO se debe tocar, con una linea que dice `description: >` dentro de
un bloque de codigo para que se note si el regex se pasa de listo.
"""


def main():
    # --- 1-3: atomicidad, medida por su fallo ---
    with tempfile.TemporaryDirectory(prefix="medirdisparo-") as tmp:
        destino = Path(tmp) / "SKILL.md"
        destino.write_text(SKILL_MD, encoding="utf-8")

        md.escribe_atomico(destino, "contenido nuevo\n")
        check("1. escribe el contenido entero",
              destino.read_text(encoding="utf-8") == "contenido nuevo\n",
              repr(destino.read_text(encoding="utf-8")[:60]))
        check("2. y no deja temporales al lado",
              [p.name for p in Path(tmp).iterdir()] == ["SKILL.md"],
              f"{sorted(p.name for p in Path(tmp).iterdir())!r}")

        # LA QUE MANDA: si el reemplazo falla, el original tiene que quedar
        # EXACTAMENTE como estaba. Con `write_text` este caso dejaba el fichero
        # truncado, y por eso se mide rompiendo `os.replace` a propósito.
        antes = destino.read_text(encoding="utf-8")
        real = os.replace
        os.replace = lambda *a, **k: (_ for _ in ()).throw(OSError("disco lleno"))
        try:
            md.escribe_atomico(destino, "ESTO NO DEBE LLEGAR")
            fallo = False
        except OSError:
            fallo = True
        finally:
            os.replace = real
        check("3. LA QUE MANDA: un fallo a mitad deja el original intacto y sin basura",
              fallo and destino.read_text(encoding="utf-8") == antes
              and [p.name for p in Path(tmp).iterdir()] == ["SKILL.md"],
              f"fallo={fallo} sobrantes={sorted(p.name for p in Path(tmp).iterdir())!r}")

    # --- 4-6: el reemplazo, y el backslash de la prosa ---
    nuevo, n = md.reescribe_description(SKILL_MD, "Una description nueva y corta.")
    check("4. sustituye el bloque exactamente una vez", n == 1, f"n={n}")
    check("5. la vieja se fue y la nueva está",
          "dos lineas plegadas" not in nuevo and "Una description nueva" in nuevo)

    # `\\1` y `\\g<0>` en la prosa: si alguien cambia la lambda por una cadena,
    # `re.sub` los expandiría como grupos y esto se pone rojo.
    trampa = r"Usa \1 y \g<0> y una barra \\ al final."
    con_trampa, n2 = md.reescribe_description(SKILL_MD, trampa)
    check("6. el backslash de la prosa sobrevive literal (no se expande como grupo)",
          n2 == 1 and r"\1" in con_trampa and r"\g<0>" in con_trampa,
          f"n={n2} · {con_trampa[:160]!r}")

    # --- 7: el contrapeso ---
    sin_bloque = "---\nname: x\ndescription: una linea suelta, sin plegado\n---\n\n# X\n"
    _t, n3 = md.reescribe_description(sin_bloque, "da igual")
    check("7. EL CONTRAPESO: sin bloque `description: >` no toca nada (n=0)",
          n3 == 0, f"n={n3}")

    fallos = [n for n, ok in results if not ok]
    print(f"\n[test-medir-disparo] {len(results) - len(fallos)}/{len(results)} en verde.")
    print("  SIN MEDIR: la medición real (invocaciones de pago) y el pulso al "
          "CLI de Claude.\n  Este arnés cubre la parte que ESCRIBE, que es la "
          "que puede romper el repo.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
