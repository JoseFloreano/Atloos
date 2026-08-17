#!/usr/bin/env python3
"""
test-perfil-bot.py — Arnes del perfil de permisos del bot de Telegram.

POR QUE EXISTE. Una auditoria escrita DESDE el puente (docs/auditoria/21) no
pudo correr un solo arnes y tuvo que declararlo: "lei el codigo, no vi el
verde". La causa no era que faltara shell — era que el allowlist del perfil de
escritura solo nombra suites genericas (`pytest`, `npm test`, `ruff`,
`flutter test`) y los arneses de esta casa se corren como
`py setup/scripts/run-tests.py`, que no encaja en ninguna entrada. O sea: el
bot tenia PROHIBIDO correr los tests de su propio repo, y por eso su auditoria
se quedo del lado del reporte.

EL INVARIANTE, que es lo que este arnes fija y no el caso concreto:

    el comando de test que el REPO declara tiene que estar permitido por el
    perfil de escritura del bot.

Se comprueba resolviendo la declaracion con el MISMO codigo que usa /test
(`testcmd.resolver`) en vez de con una copia literal: si manana el repo declara
otro runner y nadie toca el allowlist, este arnes se pone rojo. Una constante
copiada a mano no daria esa senal.

NO comprueba que el allowlist sea seguro — eso es juicio humano. Comprueba que
no sea incoherente consigo mismo.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-perfil-bot.py               [repo]
Salida: una linea por caso + resumen; exit 1 si algo falla.
Solo stdlib: no importa python-telegram-bot (el daemon si lo necesita, este no).
"""
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.normpath(os.path.join(AQUI, os.pardir))
RAIZ = os.path.normpath(os.path.join(BRIDGE, os.pardir, os.pardir))
sys.path.insert(0, BRIDGE)

import testcmd  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

results = []


def check(nombre, condicion, detalle=""):
    results.append((nombre, bool(condicion)))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle}")


def lista(nombre):
    """Extrae una constante de tg_daemon.py sin importarlo.

    Importar el daemon exigiria python-telegram-bot instalado, y un arnes que
    solo corre donde estan las dependencias del daemon no corre en CI ni en la
    otra laptop.
    """
    fuente = open(os.path.join(BRIDGE, "tg_daemon.py"), encoding="utf-8").read()
    # Dos formas conviven en el fichero: la de una linea (`X = "..."`) y la
    # parentizada de varias. Aceptar solo una hacia que el arnes midiera el
    # vacio para la otra — READ_TOOLS es de las primeras.
    m = re.search(rf"^{nombre} = \((.*?)^\)\n", fuente, re.S | re.M) \
        or re.search(rf"^{nombre} = (.*?)\n", fuente, re.M)
    if not m:
        return None
    return "".join(re.findall(r'"([^"]*)"', m.group(1)))


def permitido(cmd, allowlist):
    """True si `cmd` casa con alguna entrada Bash(...) del allowlist.

    Las entradas son prefijos con `:*` al final, que es como Claude Code
    interpreta el patron. Se compara sobre el comando normalizado.
    """
    for patron in re.findall(r"Bash\(([^)]*)\)", allowlist):
        prefijo = patron[:-2] if patron.endswith(":*") else patron
        if cmd == prefijo or cmd.startswith(prefijo + " ") or cmd == patron:
            return True
    return False


def main():
    print("Arnes del perfil de permisos del bot\n")

    write = lista("WRITE_TOOLS")
    read = lista("READ_TOOLS")
    deny = lista("DENY_TOOLS")
    check("1. las tres listas del perfil se encuentran en tg_daemon.py",
          write and read and deny,
          "si se renombraron, este arnes esta midiendo el vacio")
    if not (write and read and deny):
        return 1

    # El invariante: lo que el repo declara, el bot lo puede correr.
    declarado = testcmd.resolver(RAIZ, None)
    check(f"2. el repo declara un comando de test ({declarado or 'NINGUNO'})",
          bool(declarado),
          "sin declaracion no hay nada que permitir; lo fija test-testcmd.py")
    check("3. el perfil de ESCRITURA permite correr el comando declarado",
          declarado and permitido(declarado, write),
          f"'{declarado}' no casa con ninguna entrada Bash(...) de WRITE_TOOLS: "
          f"el bot no puede correr los tests de su propio repo, que es como la "
          f"auditoria 21 acabo sin poder ver un verde")

    # Y la mitad de abajo: el modo lectura NO lo permite. Sin esto, "permitir"
    # podria haberse implementado abriendo el perfil entero.
    check("4. el perfil de LECTURA no lo permite (el modo lectura sigue cerrado)",
          declarado and not permitido(declarado, read),
          "modo lectura ejecutando la suite = el aislamiento de T1 roto")

    # Canario del allowlist: un comando que nadie declaro no puede colarse.
    check("5. un comando arbitrario NO esta permitido en escritura",
          not permitido("py borrame_todo.py", write),
          "si esto pasa, el allowlist dejo de discriminar y no protege nada")
    check("6. los destructivos siguen denegados explicitamente",
          all(x in deny for x in ("git push", "rm:", "curl")),
          "DENY_TOOLS perdio alguna de sus entradas")

    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
