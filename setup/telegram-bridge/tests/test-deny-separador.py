#!/usr/bin/env python3
"""
test-deny-separador.py — Arnes de las denegaciones de rutas absolutas del bot.

POR QUE EXISTE. Las dos barreras de permisos que el daemon calcula a mano
—los deny de secretos (`secret_denies`) y la segunda barrera de escritura
sobre el repo del usuario— escribian el separador de directorio LITERAL:
`f"Read({d}\\\\**)"`. En Windows eso casa y por eso se verifico verde el
2026-08-01; en Linux el separador es `/`, el patron generado no casa con
NADA y la denegacion NO DENIEGA. No falla ruidosamente: falla ABIERTA y en
silencio, y solo el dia que el puente se lleve a la SER8 (auditoria 31, H1).

Es el modo de fallo del CRLF del sprint 9 —inerte en Windows, letal al cruzar
de plataforma— pero en la capa de permisos, que es la que protege las llaves.

EL INVARIANTE, que es lo que este arnes fija y no el caso concreto:

    un patron de denegacion `X<sep>**` solo protege algo si su prefijo
    literal es prefijo REAL de la ruta que pretende cubrir.

Con el separador equivocado el prefijo no es prefijo de nada, y ahi muere la
proteccion. Se comprueba en las dos plataformas (una de las dos siempre es la
ajena, y el bug vive justo ahi) y ADEMAS sobre `secret_denies()` ejecutada de
verdad en ESTA maquina, que es la mitad que se pondria roja en la SER8.

Los casos 4 y 5 son la mutacion: exigen que el patron con el separador
equivocado NO pase. Sin ellos, "cubre" podria estar devolviendo True siempre
y el arnes seria decorativo.

NO comprueba que la lista de rutas sensibles sea completa —eso es juicio, y el
docstring de `secret_denies` ya declara que es mitigacion de rutas conocidas y
no una frontera general. Comprueba que las que hay funcionen donde corren.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-deny-separador.py
Salida: una linea por caso + resumen; exit 1 si algo falla.
Solo stdlib: el daemon necesita python-telegram-bot, este arnes NO — se stubea
el modulo para poder importar el codigo REAL en vez de copiarlo (una copia a
mano no daria la senal el dia que alguien vuelva a escribir el separador).
"""
import os
import re
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.normpath(os.path.join(AQUI, os.pardir))
sys.path.insert(0, BRIDGE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def stub_telegram():
    """Deja importable `tg_daemon` sin python-telegram-bot instalado.

    El daemon hace `from telegram import ...` y `sys.exit()` si falta. Un arnes
    que solo corre donde estan las dependencias del daemon no corre en la otra
    laptop ni en CI — y este tiene que correr JUSTO en la maquina donde el bug
    se activa, que es la que todavia no tiene nada instalado.
    """
    nombres = ("BotCommand", "InlineKeyboardButton", "InlineKeyboardMarkup",
               "Update")
    tg = types.ModuleType("telegram")
    for n in nombres:
        setattr(tg, n, type(n, (), {}))
    ext = types.ModuleType("telegram.ext")
    for n in ("Application", "ApplicationBuilder", "CallbackQueryHandler",
              "CommandHandler", "ContextTypes", "MessageHandler", "filters"):
        setattr(ext, n, type(n, (), {}))
    tg.ext = ext
    sys.modules.setdefault("telegram", tg)
    sys.modules.setdefault("telegram.ext", ext)


stub_telegram()
import tg_daemon  # noqa: E402

results = []


def check(nombre, condicion, detalle=""):
    results.append((nombre, bool(condicion)))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle}")


def cubre(patron, ruta):
    """True si el patron `X<sep>**` cubre `ruta`.

    La regla de Claude Code para rutas absolutas es un prefijo mas `**`; el
    patron solo puede alcanzar la ruta si todo lo que va antes del comodin es
    prefijo literal de ella. Es exactamente lo que el separador a mano rompia.
    """
    if not patron.endswith("**"):
        return False
    return ruta.startswith(patron[:-2])


def main():
    print("Arnes del separador de las denegaciones absolutas\n")

    fuente = open(os.path.join(BRIDGE, "tg_daemon.py"), encoding="utf-8").read()

    # 1 — el literal que causo el fallo no vuelve por la puerta de atras. Se
    # busca la CONSTRUCCION (una interpolacion seguida del separador a mano),
    # no la palabra: asi el caso no se puede aprobar reescribiendo un docstring.
    literales = re.findall(r"\{[A-Za-z_][A-Za-z0-9_.\[\]']*\}\\\\\*\*", fuente)
    check("1. no queda ningun separador `\\**` escrito a mano en tg_daemon.py",
          not literales,
          f"encontrado: {literales} — ese patron solo casa en Windows")

    # 2 — el helper existe y es inyectable. Sin `sep` inyectable no se puede
    # ejercer la plataforma AJENA, que es donde vive el bug: un arnes que solo
    # mira la propia plataforma habria dado verde en Windows los cuatro sprints.
    helper = getattr(tg_daemon, "deny_glob", None)
    check("2. tg_daemon expone `deny_glob(base, sep)` para las dos barreras",
          callable(helper),
          "sin un unico sitio que construya el patron, cada barrera repite el "
          "error por su cuenta (la deuda de 'comparten la lista, no la "
          "implementacion' que declaro el sprint 11)")
    if not callable(helper):
        resumen()
        return 1

    # 3 — Linux, la plataforma de destino: el caso que hoy falla abierto.
    base_posix = "/home/floreano/.ssh"
    ruta_posix = "/home/floreano/.ssh/id_ed25519"
    pat_posix = helper(base_posix, "/")
    check("3. en Linux el patron cubre la llave que pretende proteger",
          cubre(pat_posix, ruta_posix),
          f"patron {pat_posix!r} no alcanza {ruta_posix!r}: la denegacion no "
          f"deniega y el bot puede leer la clave privada")

    # 4 — Windows: se conserva el comportamiento VERIFICADO el 2026-08-01. El
    # arreglo no puede comprarse rompiendo la plataforma donde ya funcionaba.
    base_win = r"C:\Users\jlflo\.ssh"
    ruta_win = r"C:\Users\jlflo\.ssh\id_ed25519"
    pat_win = helper(base_win, "\\")
    check("4. en Windows sigue cubriendo, y el patron es el de siempre",
          cubre(pat_win, ruta_win) and pat_win == base_win + r"\**",
          f"patron {pat_win!r}: cambio el formato que se verifico en campo")

    # 5 y 6 — LA MUTACION, en las dos direcciones. Si el separador equivocado
    # pasara, los casos 3 y 4 no estarian midiendo nada.
    check("5. mutacion: con separador de Windows en Linux NO cubre",
          not cubre(helper(base_posix, "\\"), ruta_posix),
          "el chequeo `cubre` no discrimina: da verde al bug original")
    check("6. mutacion: con separador de Linux en Windows NO cubre",
          not cubre(helper(base_win, "/"), ruta_win),
          "el chequeo `cubre` no discrimina en la otra direccion")

    # 7 — y el codigo real, en ESTA maquina, con el separador nativo. Es la
    # mitad que se pone roja en la SER8 si alguien deshace el arreglo.
    reglas = tg_daemon.secret_denies()
    patrones = re.findall(r"Read\(([^)]*)\)", reglas)
    check("7. `secret_denies()` genera reglas para las rutas de esta maquina",
          len(patrones) >= 4,
          f"solo {len(patrones)} patrones: se esperaban .ssh, .aws, .gnupg y "
          f".config/gh mas los directorios de los .env")
    malos = [p for p in patrones
             if not cubre(p, p[:-2] + "un_secreto_cualquiera")]
    check("8. cada regla real cubre un fichero dentro de su directorio",
          not malos,
          f"patrones que no alcanzan su propio arbol: {malos}")
    nativos = [p for p in patrones if not p.endswith(os.sep + "**")]
    check(f"9. todas usan el separador nativo ({os.sep!r}) de esta plataforma",
          not nativos,
          f"con separador ajeno: {nativos} — inerte aqui, abierto alla")

    # 10 — la ruta del repo llega CRUDA de projects.json (`tg_daemon.py` la
    # pasa tal cual desde `projects[project]["path"]`) y `load_projects` solo
    # valida con `Path(...).is_dir()`, que acepta igual `C:/Users/...`. Con
    # barras normales en Windows el patron tampoco casaba: la barrera de
    # escritura estaba abierta AQUI, no solo en Linux. Sale del mismo arreglo.
    base_mixto = "C:/Users/jlflo/repo"
    ruta_mixta = r"C:\Users\jlflo\repo\src\main.py"
    pat_mixto = helper(base_mixto, "\\")     # fuera de la f-string: un
    # backslash en la expresion es PEP 701 (3.12) y el suelo son 3.10 — lo
    # caza test-suelo-python.py, que es como se encontro este mismo comentario.
    check("10. una ruta con barras normales en Windows tambien queda cubierta",
          cubre(pat_mixto, ruta_mixta),
          f"patron {pat_mixto!r}: projects.json admite esa "
          f"forma y la barrera de escritura no la protege")

    # 11 — la segunda barrera (modo escritura sobre el repo del usuario) va
    # por el mismo sitio. Era el otro `\\**` del fichero.
    barrera = re.search(r"deny \+= f\",Write\(([^)]*)\).*?Edit\(([^)]*)\)",
                        fuente)
    check("11. la barrera de escritura del repo tambien usa `deny_glob`",
          barrera and all("deny_glob(" in g for g in barrera.groups()),
          "Write/Edit sobre el repo siguen construyendo el patron a mano: en "
          "Linux el aislamiento que T2 promete no existe")

    return resumen()


def resumen():
    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
