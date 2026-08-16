#!/usr/bin/env python3
"""
test-eol-blobs.py — Ningún `.sh` ni `.py` trackeado puede llevar `\\r` EN EL BLOB.

Por qué existe (sprint 9, S1; hallazgo H1 de la auditoría 27). Sobre el MISMO
commit `e2ec4d5`, la suite daba **18/18 en Windows y 17/18 desde Linux**:

    $ bash setup/hooks/git-post-commit-graph-report.sh
    setup/hooks/git-post-commit-graph-report.sh: line 34: $'\\r': command not found
    exit=2

`bash` no admite el retorno de carro al final de línea, y el error **no menciona
el fin de línea**: dice «command not found» de un carácter invisible. Los `.py`
de `setup/hooks/` comparten el riesgo, porque Linux los ejecuta por shebang.

SE MIDE EL BLOB, NO EL ÁRBOL DE TRABAJO, y esa es toda la diferencia entre un
check y un falso positivo permanente. En Windows con `core.autocrlf=true` el
árbol de trabajo tiene CRLF **a propósito** y eso es correcto; lo que no puede
tener CR es lo que git guarda, porque es lo que viaja a la otra máquina. Un
check sobre el disco daría rojo en Windows el primer día y estaría borrado el
segundo.

  **Es la misma lección del sprint 7 y del check 5 del catálogo: se mide el
  contrato que viaja, no el texto que se ve en la pantalla.**

Y por eso hay DOS checks y no uno. El primero mira el estado; el segundo mira
la REGLA, preguntándole a git en vez de leyendo el `.gitattributes` como texto:

  · **Check 1** · ningún blob de `*.sh` / `*.py` contiene `\\r`.
  · **Check 2** · `git check-attr eol` responde `lf` para esas extensiones.
    Sin él, alguien podría limpiar los blobs a mano y dejar el repo sin la
    regla que impide que vuelvan a ensuciarse — verde, y desprotegido.

Uso:  py setup/scripts/tests/test-eol-blobs.py          [repo]
Salidas: 0 limpio y protegido · 1 hay blobs sucios o la regla no rige.
"""
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Las que MUEREN con `\r`, no las que «quedan feas». `.ps1` no entra: PowerShell
# tolera LF y el `.gitattributes` le pone CRLF a propósito, así que meterlo aquí
# haría fallar el arnés por una regla que decidimos nosotros.
EXTENSIONES = ("*.sh", "*.py")


def git(args, cwd):
    p = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.DEVNULL)
    return p.returncode, p.stdout


def raiz():
    """Raíz del repo desde el cwd. Desde el cwd A PROPÓSITO, como `run-tests`:
    así la autoprueba puede apuntar el detector a un repo de laboratorio."""
    cod, salida = git(["rev-parse", "--show-toplevel"], ".")
    if cod == 0 and salida.strip():
        return salida.decode("utf-8", "replace").strip()
    return str(Path.cwd())


def blob_sucio(base, ruta):
    """Cuántos `\\r` lleva el BLOB de `ruta`. La decisión que ejerce la autoprueba.

    Función y no un `in` suelto por lo mismo que `excede_tope` en el catálogo:
    un check verificado contra una reimplementación no está verificado.
    """
    cod, datos = git(["cat-file", "blob", f":{ruta}"], base)
    if cod != 0:                       # no está en el index (worktree raro)
        cod, datos = git(["cat-file", "blob", f"HEAD:{ruta}"], base)
    if cod != 0:
        return -1                      # no se pudo leer: lo reporta quien llama
    return datos.count(b"\r")


def sucios(base):
    """[(ruta, n_cr)] de los blobs trackeados que llevan CR."""
    cod, salida = git(["ls-files"] + list(EXTENSIONES), base)
    if cod != 0:
        return None
    hallazgos = []
    for ruta in salida.decode("utf-8", "replace").split("\n"):
        ruta = ruta.strip()
        if not ruta:
            continue
        n = blob_sucio(base, ruta)
        if n != 0:
            hallazgos.append((ruta, n))
    return hallazgos


def regla_vigente(base, muestra):
    """(bool, valor) — ¿git dice que `muestra` es `eol=lf`?

    Se le PREGUNTA A GIT (`check-attr`) en vez de leer el `.gitattributes` como
    texto. Leer el texto mediría lo que está escrito; esto mide lo que rige, que
    es distinto en cuanto haya un `.gitattributes` en un subdirectorio o un
    patrón que no case como alguien creía.
    """
    cod, salida = git(["check-attr", "eol", "--", muestra], base)
    if cod != 0:
        return False, "check-attr falló"
    # formato: "ruta: eol: lf"
    valor = salida.decode("utf-8", "replace").strip().rsplit(":", 1)[-1].strip()
    return valor == "lf", valor


def autoprueba(base):
    """Mutación: fabrica un blob CON `\\r` y exige que el detector lo cace.

    (bool, motivo). No toca ningún fichero trackeado: escribe un blob suelto en
    la base de objetos con `hash-object -w` y lo lee con la MISMA función que
    corre en producción. Un check que solo se ha visto en verde no está
    verificado — es el agujero de H7 de la auditoría 22.
    """
    def blob_de(contenido):
        p = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=base,
                           input=contenido, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL)
        if p.returncode != 0:
            return None
        sha = p.stdout.decode().strip()
        cod, datos = git(["cat-file", "blob", sha], base)
        return datos if cod == 0 else None

    sucio = blob_de(b"#!/bin/bash\r\necho hola\r\n")
    if sucio is None:
        return False, "no se pudo fabricar el blob de laboratorio"
    if sucio.count(b"\r") != 2:
        return False, (f"el blob sucio de laboratorio debería tener 2 CR y "
                       f"tiene {sucio.count(b'\r')}: el detector mediría mal")

    limpio = blob_de(b"#!/bin/bash\necho hola\n")
    if limpio is None or limpio.count(b"\r") != 0:
        return False, "un blob limpio da CR: el detector produce falsos positivos"

    # Y el reverso que importa: que `check-attr` sepa responder. Si devolviera
    # siempre lo mismo, el check 2 sería decorativo.
    ok_sh, val_sh = regla_vigente(base, "cualquiera.sh")
    ok_ps1, val_ps1 = regla_vigente(base, "cualquiera.ps1")
    if not ok_sh:
        return False, f"`.sh` no rige como eol=lf: check-attr dice {val_ps1!r}"
    if ok_ps1:
        return False, ("`.ps1` también sale `lf`: check-attr no está "
                       "distinguiendo por extensión, así que el check 2 no mide "
                       "nada")
    return True, ""


def main():
    base = raiz()
    print("Fin de línea en los BLOBS (lo que viaja), no en el árbol de trabajo\n")

    ok_auto, motivo = autoprueba(base)
    print(f"  [AUTOPRUEBA] {'OK' if ok_auto else 'FALLIDA'} — un blob con `\\r` se "
          f"caza, uno limpio no, y `check-attr` distingue `.sh` de `.ps1`"
          + (f"\n               {motivo}" if not ok_auto else ""))

    print("\n── Check 1 · blobs de " + " / ".join(EXTENSIONES) + " " + "─" * 30 + "\n")
    hallazgos = sucios(base)
    if hallazgos is None:
        print("  No pude listar ficheros trackeados: ¿esto es un repo git?")
        return 1
    if hallazgos:
        print(f"  {len(hallazgos)} blob(s) con retorno de carro:\n")
        for ruta, n in hallazgos:
            detalle = "no se pudo leer" if n < 0 else f"{n} CR"
            print(f"    {ruta:<52}{detalle}")
        print("\n  Esto SÍ tumba el arnés. `bash` muere con `$'\\r': command not\n"
              "  found` y el error no menciona el fin de línea. El arreglo:\n"
              "      git add --renormalize <fichero> && git commit")
    else:
        cod, salida = git(["ls-files"] + list(EXTENSIONES), base)
        n = len([x for x in salida.decode("utf-8", "replace").split("\n") if x.strip()])
        print(f"  {n} ficheros, ninguno con CR en el blob.")

    print("\n── Check 2 · la REGLA rige (se le pregunta a git) " + "─" * 24 + "\n")
    fallos_regla = []
    for patron, esperado in (("cualquiera.sh", "lf"), ("cualquiera.py", "lf")):
        ok, valor = regla_vigente(base, patron)
        estado = "OK" if ok else f"dice {valor!r}"
        print(f"  {patron:<22}eol esperado {esperado:<4}  {estado}")
        if not ok:
            fallos_regla.append(patron)
    if fallos_regla:
        print("\n  Los blobs pueden estar limpios hoy y volver a ensuciarse\n"
              "  mañana: sin la regla en `.gitattributes`, la protección es la\n"
              "  variable `core.autocrlf` de cada máquina — que es justo lo que\n"
              "  produjo 18/18 en una y 17/18 en otra sobre el mismo commit.")

    return 1 if (hallazgos or fallos_regla or not ok_auto) else 0


if __name__ == "__main__":
    sys.exit(main())
