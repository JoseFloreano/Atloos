#!/usr/bin/env python3
"""
run-tests.py — Corre TODOS los arneses del repo y devuelve un solo exit code.

Existe porque el merge gate exige un comando de test declarado y este repo no
tenía ninguno: el 2026-08-09 el gate solo pasó encadenando los 9 arneses a mano
con `--cmd`, así que todo merge futuro chocaba con el mismo muro.

Descubre por glob en vez de por lista escrita a mano. Una lista sería otro
contenido con dos puntos de consumo: añades el arnés décimo y nada te obliga a
registrarlo. No es una medida de seguridad, es mantenimiento.

Uso:  py setup/scripts/run-tests.py
Salidas: 0 todos verdes · 1 alguno falló · 2 no encontró ningún arnés
"""
import glob
import os
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
    for ruta in arneses:
        nombre = os.path.basename(ruta)
        t0 = time.time()
        p = subprocess.run([sys.executable, ruta], cwd=base,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        seg = int(time.time() - t0)
        if p.returncode == 0:
            print(f"[OK]    {nombre}  {seg}s")
        else:
            print(f"[FALLO] {nombre}  {seg}s  (exit {p.returncode})")
            fallos.append((nombre, p.stdout.decode("utf-8", "replace")))

    print(f"\n[run-tests] {len(arneses) - len(fallos)}/{len(arneses)} en verde.")
    for nombre, salida in fallos:
        print(f"\n----- salida de {nombre} -----\n{salida}", file=sys.stderr)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
