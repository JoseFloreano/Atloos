#!/usr/bin/env python3
"""
test-suelo-python.py — Todo `.py` del repo tiene que COMPILAR con el suelo.

Por qué existe (sprint 10, S1). `test-eol-blobs.py`, escrito el sprint 9, usaba
un backslash dentro de la parte de expresión de una f-string — legal desde
**Python 3.12** (PEP 701). En la máquina de quien lo escribió compilaba; desde
el puente, con **3.10.12**, el fichero **ni se importaba** y `run-tests.py`
daba **18/19** sin que nada dijera por qué.

  **El arnés que existe para acabar con «mismo commit, dos veredictos» produjo
  uno.** El sprint 9 cerró esa enfermedad por el lado del fin de línea y la
  reabrió por el lado de la versión del intérprete.

Y el repo no declaraba suelo: el `README` decía «Python 3». Que la SER8 se
salvara (Ubuntu 24.04 trae 3.12) era accidente, no diseño.

## Por qué SE COMPILA y no se busca el texto

La vía obvia —`grep` del backslash en f-strings— caza **esta** y ninguna otra:
el `type` de 3.12, los genéricos de PEP 695 o las comillas anidadas de PEP 701
pasarían de largo. Es la lección del sprint 7 con otro disfraz: **se verifica el
contrato (compila), no el disfraz (el texto).**

⚠ Y `ast.parse(..., feature_version=(3, 10))` NO SIRVE para esto, medido:
sobre el fichero roto devolvía verde en los 39 ficheros. `feature_version` es
best-effort y **no cambia el tokenizador**, así que toda la familia PEP 701 se
le escapa — que es justo la que mordió. Si este arnés se hubiera escrito con esa
vía habría pasado sin comprobar, que es el defecto que persigue.

**Se compila con un intérprete REAL del suelo cuando lo hay** (`py -3.10`,
`python3.10`). Cuando no lo hay, se dice `[SKIP]` con el motivo y se cae a
`ast.parse`, que caza menos — **nunca se da por verde en silencio**, porque un
check que no puede comprobar y calla es peor que no tenerlo.

## La exención por máquina, y por qué lleva fecha

Una máquina sin intérprete del suelo salía **2**, y `run-tests.py` lo pinta
rojo. Correcto como aviso y **veneno como régimen**: en la SER8 (Ubuntu 24.04,
sin 3.10) ese rojo era permanente, y *una suite que nunca está verde deja de
leerse* — el día que se ponga roja de verdad, nadie lo nota (auditoría 31, H5).

La salida NO es un `skip` genérico, que en dos sprints se vuelve costumbre. Es
una exención **declarada, por máquina y con fecha**, versionada en
`suelo-exenciones.json` y visible en el diff. Una máquina exenta sale verde
**diciendo en grande qué no pudo comprobar**; una máquina sin entrada sigue
saliendo 2; y una exención **caducada pone el arnés ROJO**, que es lo que
impide que la excepción se quede a vivir.

Uso:  setup/scripts/py setup/scripts/tests/test-suelo-python.py          [repo]
Salidas: 0 todo compila con el suelo (o exención vigente) · 1 alguno no compila,
         la autoprueba falló, o hay una exención CADUCADA · 2 no se pudo
         comprobar y esta máquina no está exenta.
"""
import ast
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

# EL SUELO, y la decisión está argumentada en el README.
#
# 3.10 y no 3.12 porque el suelo lo fija el entorno MÁS VIEJO que corre esto
# hoy, y ese es el entorno desde el que se escriben las auditorías: Python
# **3.10.12** (medido, `docs/tmp/PROMPT-SPRINT-10.md`), que es donde el fallo de
# PEP 701 del sprint 9 se descubrió. Subir a 3.12 no arreglaría nada: dejaría
# "no soportado" justo el sitio donde el fallo se ve. Y no cuesta: el repo es
# stdlib pura y los 46 ficheros ya compilan en 3.10.
#
# ⚠ Ninguna de las DOS máquinas del inventario tiene 3.10 de serie: la Legion es
# 3.12.10 (y tiene un 3.10 instalado aparte, vía `py -3.10`) y la SER8 es
# 3.12.3 (`docs/auditoria/28`, medido el 2026-08-16/17). Por eso la SER8 va por
# exención declarada, no por intérprete real — y por eso esa exención CADUCA:
# el día que el entorno de auditoría deje de ser 3.10, el suelo sube a 3.12 y
# esto se simplifica entero. Antes de tocar este número, relee ese párrafo: la
# versión anterior justificaba el suelo con "el puente, Ubuntu 22.04", una
# máquina que el inventario NO conoce, y así estuvo hasta el 2026-08-17.
SUELO = (3, 10)

EXCLUIDOS = ("__pycache__", "_build", ".git", "node_modules")

EXENCIONES = Path(__file__).resolve().parent / "suelo-exenciones.json"


def exencion(fichero=None, maquina=None, hoy=None):
    """(estado, detalle) para ESTA máquina. estado ∈ vigente | caducada | None.

    Se consulta SOLO cuando no hay intérprete del suelo: si lo hay, se compila
    de verdad y ninguna exención pinta nada.

    Un fichero ilegible NO concede la exención: devolver "no exento" deja el
    arnés en 2 (no comprobado), mientras que lo contrario convertiría un JSON
    roto en un verde. Se falla cerrado, que es la regla de esta casa.
    """
    nombre = maquina or platform.node() or "(sin nombre)"
    maquina = nombre.strip().lower()
    hoy = hoy or date.today()
    try:
        with open(fichero or EXENCIONES, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError) as exc:
        return None, f"no se pudo leer {EXENCIONES.name}: {exc}"
    if not isinstance(datos, dict):
        return None, f"{EXENCIONES.name} no es un objeto JSON"

    entrada = None
    for clave, valor in datos.items():
        if clave.startswith("_") or not isinstance(valor, dict):
            continue
        if clave.strip().lower() == maquina:
            entrada = valor
            break
    if entrada is None:
        return None, f"'{nombre}' no tiene exención declarada"

    motivo = str(entrada.get("motivo", "")).strip()
    hasta = str(entrada.get("hasta", "")).strip()
    # Sin fecha NO hay exención: ese es el mecanismo entero. Una exención sin
    # caducidad es un skip con mejor nombre.
    try:
        vence = date.fromisoformat(hasta)
    except ValueError:
        return "caducada", (f"la exención de '{nombre}' no declara una "
                            f"fecha 'hasta' válida (AAAA-MM-DD): sin fecha no vale")
    if hoy > vence:
        return "caducada", (f"la exención de '{nombre}' CADUCÓ el {hasta}. "
                            f"Toca decidir: instalar Python {SUELO[0]}.{SUELO[1]} "
                            f"aquí, subir el suelo, o renovarla con fecha nueva y "
                            f"motivo. Lo que no vale es dejarla correr.")
    return "vigente", f"hasta {hasta} · {motivo}"


def ficheros(base):
    return [p for p in sorted(Path(base).rglob("*.py"))
            if not any(x in p.parts for x in EXCLUIDOS)]


def interprete_del_suelo():
    """Ruta a un intérprete REAL del suelo, o None. Se prueban las tres formas.

    Devolver None no es un fallo del repo: es una máquina sin ese intérprete, y
    se reporta como `[SKIP]` con el motivo — no como verde.
    """
    v = f"{SUELO[0]}.{SUELO[1]}"
    for cmd in ([shutil.which("py"), f"-{v}"], [shutil.which(f"python{v}")],
                [shutil.which(f"python{SUELO[0]}.{SUELO[1]}.exe")]):
        if not cmd[0]:
            continue
        try:
            p = subprocess.run(cmd + ["-c", "import sys;print(sys.version_info[:2])"],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               timeout=20)
            if p.returncode == 0 and f"({SUELO[0]}, {SUELO[1]})" in p.stdout.decode():
                return cmd
        except Exception:
            continue
    return None


def compila_con(cmd, ruta):
    """(bool, detalle) — ¿`ruta` compila con el intérprete `cmd`?

    Se compila en memoria (`compile`), no con `py_compile`, para no sembrar
    `.pyc` de otra versión en el árbol de trabajo.
    """
    guion = ("import sys\n"
             "src = open(sys.argv[1], encoding='utf-8').read()\n"
             "try:\n"
             "    compile(src, sys.argv[1], 'exec')\n"
             "except SyntaxError as e:\n"
             "    print(f'{e.lineno}: {e.msg}'); sys.exit(1)\n")
    p = subprocess.run(cmd + ["-c", guion, str(ruta)],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    return p.returncode == 0, p.stdout.decode("utf-8", "replace").strip()


def compila_ast(ruta):
    """Respaldo sin intérprete del suelo. CAZA MENOS y hay que decirlo."""
    try:
        ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta),
                  feature_version=SUELO)
        return True, ""
    except SyntaxError as e:
        return False, f"{e.lineno}: {e.msg}"


def autoprueba(cmd, tmp):
    """Mutación: fabrica un fichero con el constructo de 3.12 y exige rojo.

    (bool, motivo). Ejerce LA MISMA función que corre en producción, y prueba
    los dos lados. El caso sucio es el real —backslash en la expresión de una
    f-string, PEP 701—, no uno inventado.
    """
    sucio = tmp / "_lab_sucio.py"
    limpio = tmp / "_lab_limpio.py"
    sucio.write_text('d = b"x"\ns = f"{d.count(b\'\\r\')}"\n', encoding="utf-8")
    limpio.write_text('d = b"x"\nn = d.count(b"\\r")\ns = f"{n}"\n', encoding="utf-8")
    try:
        ok_sucio, det = (compila_con(cmd, sucio) if cmd else compila_ast(sucio))
        ok_limpio, _ = (compila_con(cmd, limpio) if cmd else compila_ast(limpio))
        if not cmd:
            # Sin intérprete real la mutación NO se puede ejercer: `ast.parse`
            # deja pasar el caso sucio (medido). Se dice, no se finge.
            return None, ("sin intérprete del suelo la mutación no se puede "
                          "ejercer: `ast.parse` no ve la familia PEP 701")
        if ok_sucio:
            return False, ("el constructo de 3.12 (backslash en f-string) NO da "
                           "rojo: el check no comprueba nada")
        if not ok_limpio:
            return False, f"un fichero legal en el suelo da rojo: {det}"
        return True, ""
    finally:
        for f in (sucio, limpio):
            try:
                f.unlink()
            except OSError:
                pass


def raiz():
    try:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout.decode("utf-8", "replace").strip()
    except Exception:
        pass
    return os.getcwd()


def main():
    base = raiz()
    v = f"{SUELO[0]}.{SUELO[1]}"
    print(f"Suelo de Python declarado: {v} — se COMPILA, no se busca texto\n")

    cmd = interprete_del_suelo()
    estado_ex, detalle_ex = (None, "")
    if cmd:
        print(f"  [OK] intérprete real del suelo: {' '.join(x for x in cmd if x)}")
    else:
        print(f"  [SKIP] no hay Python {v} en esta máquina: se cae a "
              f"`ast.parse`, que CAZA MENOS —toda la familia PEP 701 se le "
              f"escapa, medido—. No es verde: es 'no se pudo comprobar del todo'")
        estado_ex, detalle_ex = exencion()
        if estado_ex == "vigente":
            print(f"  [EXENTO] '{platform.node()}' tiene exención DECLARADA "
                  f"({detalle_ex})\n"
                  f"           El arnés sale verde, y lo que NO comprueba es "
                  f"esto: la familia\n"
                  f"           PEP 701 (backslash en f-string, comillas "
                  f"anidadas). Aquí no se caza.")
        elif estado_ex == "caducada":
            print(f"  [CADUCADA] {detalle_ex}")
        else:
            print(f"  [SIN EXENCIÓN] {detalle_ex} → esto sale 2, y "
                  f"`run-tests.py` lo pinta rojo.\n"
                  f"                 Si esta máquina debe correr sin {v}, "
                  f"decláralo en\n"
                  f"                 setup/scripts/tests/{EXENCIONES.name}, "
                  f"con motivo y fecha.")

    tmp = Path(base) / "setup" / "scripts" / "tests"
    ok_auto, motivo = autoprueba(cmd, tmp)
    if ok_auto is None:
        print(f"  [SKIP] autoprueba: {motivo}")
    else:
        print(f"  [AUTOPRUEBA] {'OK' if ok_auto else 'FALLIDA'} — el backslash "
              f"en f-string da rojo en {v} y su versión sin él, verde"
              + (f"\n               {motivo}" if not ok_auto else ""))

    print(f"\n── Compilando el repo con el suelo {v} " + "─" * 30 + "\n")
    fallos = []
    lista = ficheros(base)
    for p in lista:
        ok, det = (compila_con(cmd, p) if cmd else compila_ast(p))
        if not ok:
            fallos.append((p.relative_to(base), det))
    if fallos:
        print(f"  {len(fallos)} de {len(lista)} ficheros NO compilan con {v}:\n")
        for rel, det in fallos:
            print(f"    {rel}:{det}")
        print(f"\n  Esto SÍ tumba el arnés. El fichero no se importa siquiera, "
              f"así que\n  `run-tests.py` lo cuenta como fallo sin decir por "
              f"qué — y la suite\n  da un número distinto en cada máquina.")
    else:
        print(f"  Los {len(lista)} ficheros compilan con Python {v}.")

    if ok_auto is False:
        return 1
    if fallos:
        return 1
    if cmd:
        return 0
    # Sin intérprete del suelo manda la exención. Y una CADUCADA es roja a
    # propósito: si caducar no doliera, la exención sería permanente y
    # habríamos construido el skip genérico que este mecanismo evita.
    if estado_ex == "caducada":
        return 1
    return 0 if estado_ex == "vigente" else 2


if __name__ == "__main__":
    sys.exit(main())
