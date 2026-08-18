#!/usr/bin/env python3
"""
test-readme-no-miente.py — El README no puede aplazar lo que ya esta en el repo.

EL CASO QUE MANDA es el 2. Durante doce sprints el README del puente dijo, en su
seccion de arranque:

    «El arranque 24/7 con systemd llega cuando exista la mini PC
     — no lo montes aqui.»

La mini PC existe desde hace semanas, corre Ubuntu y se alcanza por Tailscale.
Esa frase no era prosa vieja: es lo que un agente LEE para decidir que hacer, y
le decia que NO montara justo la pieza que faltaba. Una instruccion falsa en el
sitio donde se opera es peor que una carencia, porque se obedece.

Este arnes fija el invariante barato y comprobable: **si el repo ya trae la
plantilla, el README no puede seguir aplazandola**. No juzga prosa en general
—eso no se puede automatizar sin falsos positivos—, juzga la contradiccion
concreta entre un fichero que existe y un texto que dice que aun no.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-readme-no-miente.py
Salidas: 0 todo verde · 1 algun caso fallo
"""
import os
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BRIDGE = AQUI.parent
README = BRIDGE / "README.md"
PLANTILLA = BRIDGE / "claude-telegram.service.example"

# Las formas de aplazar. Se buscan sobre el texto en minusculas y sin acentos
# para que un tilde de mas no abra un agujero.
APLAZAMIENTOS = (
    r"llega cuando exista la mini ?pc",
    r"no lo montes aqui",
    r"cuando exista la mini ?pc",
    r"systemd .{0,40}mas adelante",
    r"pendiente de la mini ?pc",
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

results = []


def check(nombre, condicion, detalle=""):
    results.append((nombre, bool(condicion)))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle}")


def plano(texto):
    """Minusculas y sin acentos: el check no puede depender de una tilde."""
    tabla = str.maketrans("áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN")
    return texto.translate(tabla).lower()


def aplazamientos_en(texto):
    """[(patron, linea, texto)] de cada aplazamiento encontrado."""
    hallados = []
    for n, linea in enumerate(texto.splitlines(), 1):
        p = plano(linea)
        for patron in APLAZAMIENTOS:
            if re.search(patron, p):
                hallados.append((patron, n, linea.strip()))
    return hallados


def main():
    print("Arnes: el README no aplaza lo que ya esta en el repo\n")

    check("1. el README del puente existe", README.is_file(), f"{README} no esta")
    if not README.is_file():
        return 1
    texto = README.read_text(encoding="utf-8")

    # --- 2. EL CASO QUE MANDA ---
    existe = PLANTILLA.is_file()
    hallados = aplazamientos_en(texto)
    check(f"2. la plantilla existe ({PLANTILLA.name}) y el README NO la aplaza",
          not (existe and hallados),
          "el fichero YA esta en el repo y el README sigue diciendo que no:\n          "
          + "\n          ".join(f"linea {n}: {t}" for _, n, t in hallados))

    # --- 3. La otra mitad: si el README la NOMBRA, tiene que existir ---
    # Sin esto, "arreglar" el caso 2 seria tan facil como borrar la plantilla y
    # dejar el README prometiendo un fichero fantasma.
    nombrada = PLANTILLA.name in texto
    check("3. si el README nombra la plantilla, la plantilla existe",
          not nombrada or existe,
          f"el README nombra {PLANTILLA.name} y el fichero NO esta en {BRIDGE}")

    # --- 4. Y el procedimiento tiene las dos ordenes que mas se olvidan ---
    plano_txt = plano(texto)
    for orden, porque in (
            ("enable-linger", "sin esto el servicio muere al cerrar la sesion SSH"),
            ("journalctl --user", "sin esto no hay forma de ver por que no arranco"),
            ("systemctl --user enable", "la orden que deja el servicio puesto")):
        check(f"4. el procedimiento incluye `{orden}`",
              plano(orden) in plano_txt, porque)

    # --- 5. El ExecStart apunta al venv, no a python3 del sistema ---
    if existe:
        unit = PLANTILLA.read_text(encoding="utf-8")
        exec_lines = [l for l in unit.splitlines() if l.startswith("ExecStart=")]
        check("5. la plantilla tiene un solo ExecStart", len(exec_lines) == 1,
              f"encontrados {len(exec_lines)}")
        ejecuta = exec_lines[0] if exec_lines else ""
        check("5b. y usa el interprete del venv, no python3 del sistema",
              "venv/bin/python" in ejecuta,
              f"ExecStart={ejecuta!r}: con python3 del sistema el arranque muere "
              f"en el import de python-telegram-bot (PEP 668) y systemd lo "
              f"reintenta en bucle sin que el mensaje llegue a nadie")
        for clave in ("MemoryHigh", "MemoryMax", "MemorySwapMax"):
            check(f"5c. la plantilla declara {clave}",
                  re.search(rf"^{clave}=", unit, re.M) is not None,
                  "sin MemorySwapMax=0 el techo no mata: manda a swap, y una "
                  "headless en swap sigue 'arriba' sin que salte ninguna alarma"
                  if clave == "MemorySwapMax" else "")
        # La formula al lado, que es lo que impide que el numero se copie a otra
        # maquina con otra RAM como si fuera universal.
        check("5d. y deja la formula de memoria al lado de los numeros",
              "MemoryMax  ≈" in unit or "MemoryMax ≈" in unit,
              "sin la formula, 4G se copia a una maquina de 8 GB sin pensar")

    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
