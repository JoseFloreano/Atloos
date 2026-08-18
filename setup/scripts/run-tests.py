#!/usr/bin/env python3
"""
run-tests.py — Corre TODOS los arneses del repo y devuelve un solo exit code.

Existe porque el merge gate exige un comando de test declarado y este repo no
tenía ninguno: el 2026-08-09 el gate solo pasó encadenando los 9 arneses a mano
con `--cmd`, así que todo merge futuro chocaba con el mismo muro.

Descubre por glob en vez de por lista escrita a mano. Una lista sería otro
contenido con dos puntos de consumo: añades el arnés décimo y nada te obliga a
registrarlo. No es una medida de seguridad, es mantenimiento.

## El veredicto distingue MEDIDO de NO MEDIDO (sprint 15)

«29/29 en verde» no significaba «29 comprobaron algo». **6 de los 29** tienen
una salida por `[SKIP]`, `[EXENTO]` o `PARCIAL`, y salían del mismo color que
los que midieron. Ahora el resumen los nombra. **No bloquea**: saltarse lo que
la máquina no puede ejercer es correcto; lo que no lo era es que no se viera.

Los seis, con lo que deja de comprobarse cuando saltan:

| Arnés | Salta cuando | Qué deja de medirse | ¿Sano? |
|---|---|---|---|
| `test-claude-md-drift` | un proyecto de `projects.json` no está en esta máquina · o falta `tiktoken` | la deriva del `CLAUDE.md` de ESE proyecto · el presupuesto de tokens del snippet | sí, multi-laptop |
| `test-skill-catalog` | falta `tiktoken` | los TOKENS del snippet (los caracteres sí se miden) | sí, dependencia opcional |
| `test-suelo-python` | no hay un 3.10 real | cae a `ast.parse`, que **no ve la familia PEP 701** — la que mordió | **síntoma** salvo con exención declarada |
| `test-suelo-python` | la máquina tiene exención vigente | ídem, pero DECLARADO y con fecha de caducidad | sí, hasta su `hasta` |
| `test-sync-hooks-paridad` | no hay PowerShell | el lado `.ps1` del instalador, entero | sí en Linux |
| `test-wire-hooks-virgen` | no hay PowerShell | la paridad del exit code con el gemelo `.ps1` | sí en Linux |
| `test-deps-puente` | `python-telegram-bot` no instalado | que el ancla de versión sea **la que corre aquí** | sí fuera del puente |

⚠ Y la lección que lo motivó: `test-claude-md-drift` llevaba meses saliendo por
`[SKIP]` antes de su bucle —`projects.json` está gitignorado— así que **nunca se
había corrido sobre un registro real**. El día del alta de la SER8 se corrió y
reventó. Un arnés que se salta no dice «esto está bien», dice «no se sabe».

El número de saltos **depende de la máquina**, y por eso se deriva de la corrida
en vez de escribirse aquí: en la Legion salta 1, en una headless sin PowerShell
ni `tiktoken` saltan 4-5. Una tabla con el número dentro nacería caduca.

Uso:  setup/scripts/py setup/scripts/run-tests.py
Salidas: 0 todos verdes · 1 alguno falló · 2 no encontró ningún arnés
         (los saltos NO cambian el código de salida, solo el resumen)
"""
import glob
import os
import re
import subprocess
import sys
import time

PATRON = os.path.join("setup", "**", "tests", "test-*.py")


def raiz():
    """Raíz del repo desde el cwd actual. Sin git utilizable, el cwd.

    Desde el cwd A PROPÓSITO: así el arnés puede apuntar el runner a un repo de
    laboratorio. Si la raíz saliera de __file__, el runner se descubriría a sí
    mismo y se correría en bucle.
    """
    try:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=10)
        salida = p.stdout.decode("utf-8", "replace").strip()
        if p.returncode == 0 and salida:
            return salida
    except Exception:
        pass
    return os.getcwd()


# Las marcas con las que un arnés declara que NO pudo comprobar algo. Son las
# que ya usaba la casa: no se inventa vocabulario, se lee el que hay.
#
# POR QUÉ EXISTE ESTO (sprint 15, S1). 6 de los 29 arneses tienen una salida por
# `[SKIP]`, `[EXENTO]` o `Modo: PARCIAL` — el 21 % de la suite puede pasar
# midiendo cero— y `run-tests.py` pintaba «29/29 en verde» igual. No es teórico:
# `test-claude-md-drift.py` salía por `[SKIP]` antes de su bucle porque
# `projects.json` está gitignorado, así que **nunca se había corrido sobre un
# registro real**, y el día que se corrió reventó. Un arnés que se salta no dice
# «esto está bien»: dice «no se sabe», y las dos cosas no pueden ser del mismo
# color.
#
# Se lee la SALIDA y no un código de retorno nuevo a propósito: obligar a los 29
# a devolver un código extra es un cambio de contrato en 29 sitios que se
# desincroniza; la marca ya está impresa y es la que lee el humano.
MARCAS = re.compile(r"^\s*(?:\[SKIP\]|\[EXENTO\]|\[MODO\]\s*PARCIAL|Modo:\s*PARCIAL)"
                    r"\s*(.*)$", re.M | re.I)


def marcas_de_no_medido(salida):
    """Las líneas con las que un arnés declaró no haber comprobado algo.

    Devuelve el texto recortado de cada una, sin duplicados y en orden. El
    recorte es para que el resumen quepa: el detalle entero sigue en la salida
    del arnés, que es donde hay que mirarlo.
    """
    vistos, out = set(), []
    for m in MARCAS.finditer(salida):
        txt = " ".join(m.group(0).split())
        if len(txt) > 108:
            txt = txt[:105] + "…"
        if txt not in vistos:
            vistos.add(txt)
            out.append(txt)
    return out


def main():
    base = raiz()
    arneses = sorted(glob.glob(os.path.join(base, PATRON), recursive=True))
    if not arneses:
        print(f"[run-tests] NINGUN ARNES ENCONTRADO bajo {PATRON}\n"
              f"            (raiz: {base})\n"
              f"            Un verde sin arneses no es verde: salgo con 2.",
              file=sys.stderr)
        return 2

    fallos = []
    sin_medir = []
    for ruta in arneses:
        nombre = os.path.basename(ruta)
        t0 = time.time()
        p = subprocess.run([sys.executable, ruta], cwd=base,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        seg = int(time.time() - t0)
        salida = p.stdout.decode("utf-8", "replace")
        saltos = marcas_de_no_medido(salida)
        if saltos:
            sin_medir.append((nombre, saltos))
        if p.returncode == 0:
            print(f"[OK]    {nombre}  {seg}s"
                  + (f"   ({len(saltos)} sin medir)" if saltos else ""))
        else:
            print(f"[FALLO] {nombre}  {seg}s  (exit {p.returncode})")
            fallos.append((nombre, salida))

    verdes = len(arneses) - len(fallos)
    resumen = f"\n[run-tests] {verdes}/{len(arneses)} en verde"
    if sin_medir:
        resumen += (f" · {len(sin_medir)} CON ALGO SIN MEDIR "
                    f"(no es lo mismo que verde)")
    print(resumen + ".")

    if sin_medir:
        print("\n  Verde significa «lo que se comprobó, pasó». Estos arneses\n"
              "  pasaron dejando algo SIN comprobar, y en esta máquina eso es\n"
              "  parte del veredicto, no una nota al pie:\n")
        for nombre, saltos in sin_medir:
            print(f"    {nombre}")
            for s in saltos:
                print(f"        · {s}")
        print("\n  No bloquea: saltarse lo que no se puede ejercer en esta\n"
              "  máquina es correcto. Lo que no lo era es que no se viera.")

    for nombre, salida in fallos:
        print(f"\n----- salida de {nombre} -----\n{salida}", file=sys.stderr)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
