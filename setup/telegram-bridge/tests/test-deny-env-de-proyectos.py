#!/usr/bin/env python3
"""
test-deny-env-de-proyectos.py — Arnes del deny de los .env de los REPOS
enganchados en projects.json.

POR QUE EXISTE. `secret_denies()` deniega por ruta absoluta los .env del
PUENTE, ~/.ssh, ~/.aws, ~/.gnupg y ~/.config/gh. No cubre el .env del
PROYECTO. Y su propio docstring declara las dos mitades que lo vuelven grave:
los globs NO funcionan (`Read(**/.env)` dejo pasar la lectura, medido el
2026-08-01) y la LECTURA no tiene frontera de directorio en ningun modo.

Hasta hoy eso era un residual teorico porque ningun proyecto enganchado
guardaba credenciales de produccion. Al dar de alta AlphaDogs deja de serlo:
su `backend/.env` lleva la clave de Anthropic, las credenciales de la BD de
Azure y el secreto de sesion del panel admin, y el bot puede leerlo por ruta
absoluta desde el movil.

EL INVARIANTE que fija este arnes:

    todo directorio conocido de un repo enganchado que pueda contener
    ficheros de entorno queda cubierto por una regla de denegacion cuya
    forma es la UNICA verificada en campo: prefijo literal + `**`.

La forma importa tanto como la ruta. Una regla `Read(<fichero exacto>)` sin
`**` es de una forma que NADIE ha verificado aqui; y `Read(**/.env)` esta
medido que no deniega. Por eso las reglas se emiten como
`<dir><sep>.env**`, cuyo prefijo literal (`<dir><sep>.env`) es prefijo real
de `.env`, `.env.local` y `.env.prod` — incluidos los que se creen DESPUES
de arrancar el daemon, que es lo que una enumeracion de ficheros no cubre.

Los casos de mutacion son los que impiden el arreglo perezoso: denegar el
arbol entero del repo taparia los .env y de paso dejaria al bot sin poder
leer el codigo que viene a tocar. Un deny que lo deniega todo no es
seguridad, es un bot roto.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-deny-env-de-proyectos.py
Salida: una linea por caso + resumen; exit 1 si algo falla.
Solo stdlib; se stubea telegram para importar el codigo REAL (una copia a
mano no daria la senal el dia que alguien deshaga el arreglo).
"""
import os
import re
import shutil
import sys
import tempfile
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.normpath(os.path.join(AQUI, os.pardir))
sys.path.insert(0, BRIDGE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def stub_telegram():
    """Deja importable `tg_daemon` sin python-telegram-bot instalado."""
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

    Misma regla que test-deny-separador.py: prefijo literal mas comodin. Se
    repite a proposito — si un dia la regla de Claude Code cambia, los dos
    arneses tienen que poder discrepar en vez de compartir un error.
    """
    if not patron.endswith("**"):
        return False
    return ruta.startswith(patron[:-2])


def reglas_de(salida):
    """Las rutas dentro de `Read(...)` de una cadena de denegaciones."""
    return re.findall(r"Read\(([^)]*)\)", salida)


def repo_de_mentira():
    """Un repo con .env en la raiz, otro en backend/ y codigo que SI se lee."""
    raiz = tempfile.mkdtemp(prefix="arnes-deny-env-")
    os.makedirs(os.path.join(raiz, "backend", "app"))
    os.makedirs(os.path.join(raiz, "frontend"))
    for ruta in (os.path.join(raiz, ".env"),
                 os.path.join(raiz, "backend", ".env"),
                 os.path.join(raiz, "backend", ".env.local")):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("SECRETO=1\n")
    with open(os.path.join(raiz, "backend", "app", "main.py"), "w",
              encoding="utf-8") as f:
        f.write("# codigo que el bot SI tiene que poder leer\n")
    return raiz


def main():
    print("Arnes del deny de los .env de los proyectos enganchados\n")

    fuente = open(os.path.join(BRIDGE, "tg_daemon.py"), encoding="utf-8").read()

    # 1 — el helper existe y acepta `sep` inyectable. Sin eso no se puede
    # ejercer la plataforma AJENA, que es donde el separador ya mordio una vez
    # (auditoria 31, H1: en Linux la denegacion no denegaba, en silencio).
    helper = getattr(tg_daemon, "project_env_denies", None)
    check("1. tg_daemon expone `project_env_denies(paths, sep)`",
          callable(helper),
          "sin un unico sitio que construya estas reglas, cada llamada repite "
          "el error por su cuenta")
    if not callable(helper):
        return resumen()

    raiz = repo_de_mentira()
    try:
        reglas = helper([raiz])
        patrones = reglas_de(",".join(reglas) if isinstance(reglas, list)
                             else reglas)

        # 2 — la raiz del repo, que es donde vive el .env de la mayoria.
        check("2. cubre el .env de la raiz del repo",
              any(cubre(p, os.path.join(raiz, ".env")) for p in patrones),
              f"patrones {patrones}: el .env de la raiz queda legible")

        # 3 — el caso AlphaDogs: el secreto no esta en la raiz, esta un nivel
        # dentro. Un arreglo que solo mire la raiz no lo tapa.
        check("3. cubre `backend/.env` (el caso que motivo el arreglo)",
              any(cubre(p, os.path.join(raiz, "backend", ".env"))
                  for p in patrones),
              f"patrones {patrones}: la clave de Anthropic y las credenciales "
              f"de Azure siguen legibles desde el movil")

        # 4 — y los hermanos que aun no existen. Es la ventaja de la forma
        # prefijo+`**` sobre enumerar ficheros: un .env.prod creado despues de
        # arrancar el daemon queda cubierto sin reiniciar nada.
        check("4. cubre un .env.prod que todavia no existe en disco",
              any(cubre(p, os.path.join(raiz, "backend", ".env.prod"))
                  for p in patrones),
              "la regla enumera ficheros en vez de cubrir el prefijo")

        # 5 — LA MUTACION que impide el arreglo perezoso. Denegar el arbol del
        # repo taparia los .env y dejaria al bot sin poder leer el codigo.
        codigo = os.path.join(raiz, "backend", "app", "main.py")
        check("5. mutacion: NO deniega el codigo del repo",
              not any(cubre(p, codigo) for p in patrones),
              f"alguna regla alcanza {codigo!r}: el bot no puede leer el "
              f"codigo que viene a tocar — eso no es seguridad, es un bot roto")

        # 6 — ni nada fuera del repo.
        fuera = os.path.join(os.path.dirname(raiz), "otro-sitio", ".env")
        check("6. mutacion: NO deniega rutas fuera del repo",
              not any(cubre(p, fuera) for p in patrones),
              f"alguna regla se desborda fuera de {raiz!r}")

        # 7 — todas usan la forma VERIFICADA. Una regla sin `**` es de una
        # forma que nadie ha medido aqui, y una denegacion que no deniega es
        # peor que ninguna: da por cubierto lo que esta abierto.
        sin_comodin = [p for p in patrones if not p.endswith("**")]
        check("7. todas las reglas usan la forma verificada (prefijo + `**`)",
              patrones and not sin_comodin,
              f"reglas de forma no verificada: {sin_comodin}")

        # 8 y 9 — las dos plataformas, con su separador inyectado.
        base_posix = "/home/floreano/AlphaDogs"
        pat_posix = reglas_de(",".join(helper([base_posix], "/",
                                              subdirs=("backend",))))
        check("8. en Linux cubre `<repo>/backend/.env`",
              any(cubre(p, base_posix + "/backend/.env") for p in pat_posix),
              f"patrones {pat_posix}: en la SER8 la denegacion no denegaria")
        check("9. mutacion: con separador de Windows en Linux NO cubre",
              not any(cubre(p, base_posix + "/backend/.env")
                      for p in reglas_de(",".join(
                          helper([base_posix], "\\", subdirs=("backend",))))),
              "el chequeo no discrimina: daria verde al bug del separador")

        # 10 — la ruta llega CRUDA de projects.json, donde `C:/Users/...` es
        # forma legal (`Path(...).is_dir()` la acepta). Sin normalizar, el
        # patron mezcla separadores y no cubre nada. Mismo fallo que el caso
        # 10 del arnes hermano, en la barrera nueva.
        pat_mixto = reglas_de(",".join(
            helper(["C:/Users/jlflo/AlphaDogs"], "\\", subdirs=("backend",))))
        objetivo = "C:\\Users\\jlflo\\AlphaDogs\\backend\\.env"
        check("10. una ruta con barras normales en Windows queda cubierta",
              any(cubre(p, objetivo) for p in pat_mixto),
              f"patrones {pat_mixto}: projects.json admite esa forma")

        # 11 — integracion: `secret_denies` las incluye SIN perder las suyas.
        completo = reglas_de(tg_daemon.secret_denies([raiz]))
        check("11. `secret_denies(paths)` suma las del repo a las de siempre",
              any(cubre(p, os.path.join(raiz, "backend", ".env"))
                  for p in completo) and len(completo) > len(patrones),
              f"{len(completo)} reglas totales frente a {len(patrones)} del "
              f"repo: o no suma las nuevas, o perdio las viejas")

        # 12 — y que el daemon se las PASE de verdad. Sin esto lo anterior es
        # una funcion correcta que nadie llama: `main()` calculaba el deny
        # ANTES de cargar los proyectos, asi que la lista llegaba vacia.
        orden = re.search(r"projects\s*=\s*load_projects\(\)"
                          r"[\s\S]{0,400}?SECRET_DENIES\s*=\s*secret_denies\(",
                          fuente)
        check("12. `main()` carga los proyectos ANTES de calcular el deny",
              bool(orden),
              "secret_denies() se calcula antes de load_projects(): las rutas "
              "de los repos no existen todavia y el deny sale sin ellas")
    finally:
        shutil.rmtree(raiz, ignore_errors=True)

    return resumen()


def resumen():
    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
