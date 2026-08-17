#!/usr/bin/env python3
"""
test-comandos-portables.py — Ninguna skill manda un comando de una sola plataforma.

POR QUÉ EXISTE (sprint 11). Lo que hay en `setup/skills/` no es documentación:
son las órdenes que las skills le mandan EJECUTAR a Claude Code. Estaban escritas
con `py`, el lanzador de Windows, así que en la SER8 fallaban todas con
`py: command not found` — incluida la que produce la evidencia del gate.

Y la trampa que hace falta nombrar, porque la salida obvia también está rota:
`python3` NO es la respuesta. Medido el 2026-08-16 en las dos máquinas:

    Windows   `py` real (3.12.10) · `python3` EXISTE en el PATH y MIENTE —es el
              alias de la Microsoft Store, imprime "Python was not found".
    SER8      `python3` real (3.12.3) · `py` no existe.

O sea que no hay un literal que sirva en las dos, y "el comando existe" no
prueba nada. La respuesta del repo es `setup/scripts/py` —dentro de este
árbol— y `"$HOME/.claude/scripts/py"` —desde cualquier otro proyecto—: un
resolutor que EJECUTA el intérprete antes de elegirlo.

QUÉ AFIRMA: ningún `.md` de `setup/skills/` propone un lanzador de una sola
plataforma en posición de comando, salvo que la línea DECLARE su plataforma.
Un par etiquetado (`PowerShell: ...` / `bash: ...`) es legítimo: dice cuándo
vale. Lo que no vale es el literal a secas, que se lee como universal.

LO QUE NO AFIRMA, y conviene tenerlo escrito: no persigue toda orden no
portable —`Get-ChildItem`, `chmod`, `sudo` y compañía quedan fuera—. Persigue
la clase que ya mordió, que es el lanzador de Python. Ensancharlo sin una
cicatriz detrás sería ruido, y un check ruidoso se acaba desactivando.

Uso:  setup/scripts/py setup/scripts/tests/test-comandos-portables.py
Salidas: 0 limpio · 1 alguna skill manda un comando de una sola plataforma
"""
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parents[2]        # setup/
SKILLS = RAIZ / "skills"

# Lanzadores que solo existen —o solo funcionan— en una plataforma.
SOLO_UNA = {
    "py": "solo Windows (y en Linux ni existe)",
    "python3": "en Windows es el alias de la Store, que no ejecuta",
    "python": "en Windows es el alias de la Store, que no ejecuta",
}

# En posición de COMANDO: principio de línea, tras un backtick, tras `$`/`>` de
# prompt, o dentro de un bloque de código. No cuenta `.py` ni `scripts/py`.
COMANDO = re.compile(
    r'(?:(?<=^)|(?<=`)|(?<=\$ )|(?<=> )|(?<=\| ))(' + "|".join(SOLO_UNA) + r')\s+\S',
    re.MULTILINE)

# La línea declara su plataforma, así que el literal es legítimo ahí.
ETIQUETA = re.compile(
    r'PowerShell|Windows|Linux|macOS|Unix|cmd\.exe|Git Bash|bash:', re.IGNORECASE)


def revisa_texto(texto):
    """[(nlinea, lanzador, motivo, linea)] de las órdenes no portables."""
    hallazgos = []
    lineas = texto.splitlines()
    for i, linea in enumerate(lineas, 1):
        for m in COMANDO.finditer(linea):
            lanzador = m.group(1)
            # La etiqueta puede ir en la propia línea o en la de encima (un
            # bloque `PowerShell:` seguido de su comando es la forma normal).
            contexto = linea + "\n" + (lineas[i - 2] if i >= 2 else "")
            if ETIQUETA.search(contexto):
                continue
            hallazgos.append((i, lanzador, SOLO_UNA[lanzador], linea.strip()))
    return hallazgos


def autoprueba():
    """La mutación: se fabrica la orden rota y se exige que el check la cace."""
    roto = "Corre `py setup/scripts/run-tests.py` antes de integrar."
    if not revisa_texto(roto):
        return False, "un `py ...` a secas NO se caza: el check es ciego"

    bueno = "Corre `setup/scripts/py setup/scripts/run-tests.py` antes de integrar."
    if revisa_texto(bueno):
        return False, "el resolutor se señala como si fuera el fallo: falso positivo"

    etiquetado = "En PowerShell: `py \"$env:USERPROFILE\\.claude\\scripts\\x.py\"`"
    if revisa_texto(etiquetado):
        return False, ("una línea que DECLARA su plataforma se señala igual: "
                       "entonces no se puede documentar el par por plataforma")

    # Y el borde por el otro lado: la etiqueta no puede ser un salvoconducto
    # para cualquier cosa que esté cerca. Si vale a CUALQUIER distancia, basta
    # con nombrar 'Windows' una vez arriba del fichero para silenciarlo entero.
    lejos = ("Nota sobre Windows.\n" + "relleno\n" * 4 +
             "Corre `py setup/scripts/run-tests.py`.")
    if not revisa_texto(lejos):
        return False, ("una etiqueta a 5 líneas de distancia exime igual: "
                       "la ventana es demasiado ancha y silencia por contagio")

    if not revisa_texto("python3 setup/scripts/run-tests.py"):
        return False, "`python3` a secas no se caza, y en Windows no ejecuta"
    return True, ""


def main():
    print("\nÓrdenes de una sola plataforma en las skills\n")
    bien, motivo = autoprueba()
    if not bien:
        print(f"  [AUTOPRUEBA] FALLIDA — {motivo}")
        print("\n  El check no está verificado, así que su verde no vale.")
        return 1
    print("  [AUTOPRUEBA] OK — caza `py` y `python3` a secas, respeta el "
          "resolutor\n               y el par etiquetado por plataforma")

    if not SKILLS.is_dir():
        print(f"\nNo encuentro {SKILLS}")
        return 1

    ficheros = sorted(SKILLS.rglob("*.md"))
    hallazgos = []
    for f in ficheros:
        for n, lanzador, motivo, linea in revisa_texto(
                f.read_text(encoding="utf-8")):
            hallazgos.append((f.relative_to(RAIZ.parent), n, lanzador, motivo, linea))

    print(f"\nRevisados {len(ficheros)} .md de skills\n")
    if not hallazgos:
        print("  Sin hallazgos: toda orden nombra un intérprete que existe en\n"
              "  las dos plataformas, o declara en cuál vale.")
        return 0

    for rel, n, lanzador, motivo, linea in hallazgos:
        print(f"  [ROJO] {rel}:{n}  `{lanzador}` — {motivo}")
        print(f"         {linea[:96]}")
    print(f"\n{len(hallazgos)} órdenes que fallan en una de las dos máquinas.")
    print("Arreglo: `setup/scripts/py <script>` dentro de este repo, o\n"
          "         `\"$HOME/.claude/scripts/py\" <script>` desde cualquier otro.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
