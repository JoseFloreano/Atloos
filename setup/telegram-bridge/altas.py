#!/usr/bin/env python3
"""
altas.py — Dar de alta un proyecto en el puente: UN validador, con veredicto.

Vive fuera de tg_daemon.py a proposito, igual que testcmd.py y botprofile.py:
asi su arnes no necesita python-telegram-bot. Solo stdlib.

## POR QUE EXISTE (2026-08-19)

El alta estaba repartida en cinco sitios y **ninguno de los cinco fallos se
oia**:

| # | Que | Donde | Si faltaba |
|---|---|---|---|
| 1 | el repo, clonado en esta maquina | disco | — |
| 2 | la ruta absoluta | `projects.json` (por-maquina, gitignorado) | `load_projects()` lo tiraba con un `log.warning`: al journal, **no al movil** |
| 3 | el nombre = la carpeta del vault | `10-Projects/<nombre>` | `project_briefing()` devuelve `""` **en silencio**: trabajas sin memoria y no te enteras |
| 4 | el comando de test | `.claude/settings.json` -> `projects.json` | `/merge` bloqueado por diseno, y te enteras el dia que quieres integrar |
| 5 | el `CLAUDE.md` del proyecto | el repo | el agente arranca sin las reglas de aislamiento |

Cinco sitios, cero verificacion, y los fallos aparecian dias despues y lejos de
su causa. Aqui se comprueban los cinco **en el momento del alta**, y el que no
pasa se dice con su motivo y su receta.

## La regla que gobierna el veredicto

**Bloqueante es solo lo que impide trabajar** (2 y 3 de la tabla de abajo). Lo
demas AVISA y deja pasar: un proyecto sin carpeta en el vault se puede usar hoy
—solo que sin memoria—, y negarle el alta por eso obligaria a hacer el trabajo
en dos maquinas antes de poder mandar un mensaje. Lo que no se acepta es que
falte **y no se diga**.

## Lo portable no es una lista de rutas, es preguntarle a la maquina

Las dos incompatibilidades Windows<->Ubuntu que quedaban vivas (las de
separadores y la del lanzador `py` ya las resuelven `deny_glob` y
`testcmd.argv`):

1. **Una ruta de la otra maquina.** `projects.json` es por-maquina justo por
   esto, pero copiarlo entero de la Legion es la forma natural de darlo de alta y
   nadie lo desmentia: `C:\\Users\\...` en Linux es un `is_dir()` falso y el
   proyecto desaparecia del listado sin una linea en el chat.
2. **Un ejecutable que aqui no existe.** `GATE_TEST_CMD` esta VERSIONADO y viaja
   entre maquinas: `npm test` / `flutter test` / `pytest` valen en la laptop y en
   la SER8 son `FileNotFoundError`. Y no basta con mirar TU PATH: el daemon corre
   bajo `systemd --user`, cuyo PATH es minimo y no lee tu `.bashrc`. Por eso
   `revisar()` acepta un `which` inyectable y el daemon le pasa el suyo — el que
   de verdad va a resolver el comando cuando corras `/test`.

Uso (fuera del bot):  setup/scripts/py setup/telegram-bridge/altas.py <ruta> [comando de test...]
Salidas: 0 alta hecha · 1 bloqueada (algo esencial falta)
"""
import json
import os
import re
import shutil
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testcmd                                              # noqa: E402

BASE = Path(__file__).resolve().parent
PROJECTS_FILE = BASE / "projects.json"


def _kebab(texto: str) -> str:
    """`Mi Proyecto_v2` -> `mi-proyecto-v2`. Sin acentos: es clave de carpeta."""
    plano = unicodedata.normalize("NFKD", texto or "")
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    plano = re.sub(r"[^A-Za-z0-9]+", "-", plano).strip("-").lower()
    return re.sub(r"-{2,}", "-", plano)


def derivar_nombre(ruta) -> str:
    """El nombre del proyecto a partir de su carpeta.

    Es la MISMA clave en tres sitios —`/p <nombre>`, `10-Projects/<nombre>` y el
    `group_id` de Graphiti—, asi que derivarla en vez de inventarla es lo que
    hace que casen sin acordarse de nada.
    """
    p = Path(str(ruta).replace("\\", "/").rstrip("/"))
    return _kebab(p.name)


def parece_ruta_de_windows(ruta: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:[\\/]", str(ruta) or "")) or "\\" in str(ruta)


# ── Deteccion del comando de test ─────────────────────────────────────────
# Se SUGIERE, no se impone: un comando adivinado que entra solo a projects.json
# es un verde que nadie eligio, y de ahi salio el `compileall` que dejaba pasar
# merges sin correr un arnes. La sugerencia se imprime; declararla es un acto.
PISTAS = [
    ("pubspec.yaml", "flutter test"),
    ("package.json", "npm test"),
    ("pyproject.toml", "python3 -m pytest -q"),
    ("pytest.ini", "python3 -m pytest -q"),
    ("tox.ini", "python3 -m pytest -q"),
    ("Cargo.toml", "cargo test"),
    ("go.mod", "go test ./..."),
]


def sugerir_test(ruta) -> str:
    d = Path(ruta)
    for fichero, cmd in PISTAS:
        if (d / fichero).is_file():
            return cmd
    if (d / "tests").is_dir() or (d / "test").is_dir():
        return "python3 -m pytest -q"
    return ""


# ── El veredicto ──────────────────────────────────────────────────────────
class Check:
    """Una casilla del alta: pasa o no, con motivo y (si no pasa) receta."""

    def __init__(self, clave, ok, detalle="", bloqueante=False):
        self.clave, self.ok = clave, bool(ok)
        self.detalle, self.bloqueante = detalle, bloqueante

    def linea(self) -> str:
        marca = "✅" if self.ok else ("❌" if self.bloqueante else "⚠️")
        return f"{marca} {self.clave}" + (f" — {self.detalle}" if self.detalle else "")


def leer_registro(projects_file=None) -> dict:
    """El `projects.json` crudo (con sus claves `_`), o {} si no hay/esta roto."""
    f = Path(projects_file or PROJECTS_FILE)
    try:
        datos = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def revisar(ruta, nombre="", test="", projects_file=None,
            which=None, vault_project_dir=None) -> dict:
    """Las cinco casillas del alta. Devuelve {nombre, ruta, test, checks, ok}.

    `which` y `vault_project_dir` se inyectan para que el arnes pueda ejercer una
    maquina que no es esta —y para que el DAEMON pase su propio `which`, que es
    el unico que sabe lo que hay en el PATH de `systemd --user`.
    """
    which = which or shutil.which
    checks = []
    cruda = str(ruta or "").strip().strip('"').strip("'")

    # 1 · La ruta. Bloqueante: sin carpeta no hay nada que activar.
    p = Path(os.path.expanduser(cruda)) if cruda else Path()
    existe = bool(cruda) and p.is_dir()
    if existe:
        p = p.resolve()
        checks.append(Check("ruta", True, str(p)))
    elif cruda and parece_ruta_de_windows(cruda) and os.name != "nt":
        checks.append(Check(
            "ruta", False,
            f"`{cruda}` es una ruta de Windows y esto es Linux. `projects.json` "
            f"es POR MAQUINA: no lo copies de la otra laptop, da el alta aqui "
            f"con la ruta de aqui", bloqueante=True))
    else:
        checks.append(Check("ruta", False,
                            f"no existe o no es una carpeta: `{cruda}`", bloqueante=True))

    nombre = _kebab(nombre) if nombre else (derivar_nombre(p) if cruda else "")

    # 2 · Que sea un repo git. Bloqueante: sin git no hay /write, ni rama, ni
    #     worktree, ni /merge — o sea, no hay puente.
    if existe:
        es_git = (p / ".git").exists()
        checks.append(Check("git", es_git,
                            "" if es_git else "la carpeta no es un repo git: sin "
                            "git no hay rama, ni worktree, ni /merge",
                            bloqueante=True))

    # 3 · El nombre, y que no pise a otro proyecto ya registrado.
    registro = leer_registro(projects_file)
    previo = registro.get(nombre)
    ruta_previa = previo.get("path") if isinstance(previo, dict) else previo
    if previo is not None and existe and ruta_previa and \
            Path(str(ruta_previa)).resolve(strict=False) != p:
        checks.append(Check("nombre", False,
                            f"`{nombre}` ya esta dado de alta apuntando a "
                            f"`{ruta_previa}`. Elige otro nombre o corrige esa entrada",
                            bloqueante=True))
    else:
        checks.append(Check("nombre", bool(nombre),
                            nombre + (" (ya registrado: se actualiza)" if previo is not None else "")
                            if nombre else "no se pudo derivar un nombre de la ruta",
                            bloqueante=not nombre))

    # 4 · El vault. AVISA, no bloquea: se puede trabajar sin memoria, lo que no
    #     se puede es no enterarse de que estas trabajando sin memoria.
    if vault_project_dir is None:
        try:
            import vaultio
            vault_project_dir = vaultio.project_dir(nombre) if nombre else Path()
        except Exception:                          # noqa: BLE001
            vault_project_dir = Path()
    vd = Path(vault_project_dir) if vault_project_dir else Path()
    if vd.parts and vd.is_dir():
        checks.append(Check("vault", True, f"10-Projects/{nombre}"))
    else:
        checks.append(Check(
            "vault", False,
            f"no hay `10-Projects/{nombre}` en el vault: el briefing saldra "
            f"VACIO y en silencio. Engancharlo: skill `project-onboard`"))

    # 5 · El comando de test. Avisa, pero con la consecuencia por delante: sin
    #     verde posible, `/merge` queda bloqueado por diseno.
    declarado, motivo_invalido = "", ""
    if existe:
        try:
            declarado = testcmd.resolver(str(p), {"path": str(p), "test": test})
        except testcmd.ComandoInvalido as exc:
            motivo_invalido = str(exc).splitlines()[0]
    if motivo_invalido:
        checks.append(Check("test", False, motivo_invalido + " — /merge quedara bloqueado"))
    elif not declarado:
        sug = sugerir_test(p) if existe else ""
        checks.append(Check(
            "test", False,
            "ningun comando declarado: /merge quedara bloqueado (no hay verde "
            "posible)" + (f". Sugerencia para este repo: `{sug}`" if sug else "")))
    else:
        primero = declarado.split()[0]
        if primero in testcmd.LANZADORES:
            checks.append(Check("test", True, f"`{declarado}` (el lanzador lo "
                                              f"resuelve el daemon a su interprete)"))
        elif which(primero):
            checks.append(Check("test", True, f"`{declarado}`"))
        else:
            checks.append(Check(
                "test", False,
                f"`{primero}` NO esta en el PATH de este daemon (systemd --user "
                f"no lee tu .bashrc). `{declarado}` corre en la otra maquina y "
                f"aqui seria FileNotFoundError: /merge quedaria bloqueado"))

    # 6 · El CLAUDE.md del proyecto. Aviso puro.
    if existe:
        tiene = (p / "CLAUDE.md").is_file()
        checks.append(Check("CLAUDE.md", tiene,
                            "" if tiene else "el repo no tiene CLAUDE.md: el agente "
                            "arrancara sin las reglas de aislamiento (skill "
                            "`project-onboard`)"))

    return {"nombre": nombre, "ruta": str(p) if existe else cruda,
            "test": declarado if not motivo_invalido else "",
            "test_declarado_aqui": (test or "").strip(),
            "checks": checks,
            "ok": not any(c.bloqueante and not c.ok for c in checks)}


def registrar(veredicto: dict, projects_file=None) -> tuple:
    """Escribe la entrada en `projects.json`. Devuelve (ok, motivo).

    Escritura atomica y **conservando las claves `_`**: esos comentarios son la
    unica documentacion que viaja con el fichero, y una reescritura que los
    tirase dejaria al siguiente sin saber que el formato acepta `{path, test}`.
    """
    if not veredicto.get("ok"):
        return False, "el alta esta bloqueada: no se escribe nada"
    f = Path(projects_file or PROJECTS_FILE)
    datos = leer_registro(f)
    entrada = {"path": veredicto["ruta"]}
    # Solo se persiste el comando declarado AQUI. El que sale del repo
    # (`GATE_TEST_CMD`) no se copia: ya gana solo, y duplicarlo en projects.json
    # crea una copia por-maquina que se queda atras en cuanto el repo cambie.
    if veredicto.get("test_declarado_aqui"):
        entrada["test"] = veredicto["test_declarado_aqui"]
    elif isinstance(datos.get(veredicto["nombre"]), dict):
        previo = datos[veredicto["nombre"]].get("test")
        if previo:
            entrada["test"] = previo
    datos[veredicto["nombre"]] = entrada
    try:
        tmp = f.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        tmp.replace(f)
    except OSError as exc:
        return False, f"no se pudo escribir {f.name}: {exc}"
    return True, f"`{veredicto['nombre']}` -> {veredicto['ruta']}"


def texto_veredicto(veredicto: dict) -> str:
    """El checklist, tal cual se manda al chat."""
    lineas = [c.linea() for c in veredicto["checks"]]
    if veredicto["ok"]:
        pendientes = [c for c in veredicto["checks"] if not c.ok]
        cola = ("\n\nDado de alta. Lo de arriba con ⚠️ no impide trabajar, pero "
                "**tampoco se arregla solo**." if pendientes
                else "\n\nDado de alta, y sin nada pendiente.")
    else:
        cola = "\n\n**No lo he dado de alta**: falta algo sin lo que no se puede trabajar."
    return "\n".join(lineas) + cola


def main(argv):
    if not argv:
        print("\n".join(__doc__.strip().splitlines()[-2:]), file=sys.stderr)
        return 1
    v = revisar(argv[0], test=" ".join(argv[1:]))
    print(texto_veredicto(v))
    if v["ok"]:
        ok, motivo = registrar(v)
        print(("[OK] " if ok else "[FALLA] ") + motivo)
        return 0 if ok else 1
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
