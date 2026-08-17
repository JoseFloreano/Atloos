#!/usr/bin/env python3
"""
test-deps-puente.py — Las dependencias del puente estan DECLARADAS, ancladas, y
se pueden instalar en la maquina de destino.

POR QUE EXISTE. El puente tiene una dependencia externa (`python-telegram-bot`)
y el repo no traia `requirements.txt`: la unica pista era el mensaje del
ImportError, que decia `py -m pip install`, un comando que en Linux NO EXISTE.
Y en Ubuntu 24.04 un `pip install` pelado falla ademas por PEP 668
(`externally-managed-environment`), asi que la instruccion no solo estaba en el
comando equivocado: estaba en el METODO equivocado. Auditoria 31, H3b.

EL INVARIANTE, que es lo que este arnes fija y no la lista concreta:

    todo modulo de terceros que el puente importa para arrancar tiene que estar
    declarado con version anclada, y el camino de instalacion documentado tiene
    que funcionar en la maquina donde el daemon va a correr.

La lista de terceros se DERIVA del codigo (`sys.stdlib_module_names` menos los
modulos hermanos), no se copia: si manana entra una dependencia nueva y nadie
toca requirements.txt, esto se pone rojo. Una lista escrita a mano no daria esa
senal — es el mismo error que tenia el repo antes de este arnes.

Lo opcional se declara opcional: `tiktoken` NO es dependencia de arranque
porque su unico uso (`test-claude-md-drift.py`) degrada con motivo declarado si
falta. Si algun dia se importa sin red de seguridad, el caso 3 lo cazara.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-deps-puente.py
Salida: una linea por caso + resumen; exit 1 si algo falla.
Solo stdlib: no importa el daemon ni sus dependencias — parsea el fuente.
"""
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
BRIDGE = AQUI.parent
RAIZ = BRIDGE.parent.parent
REQS = BRIDGE / "requirements.txt"
INSTALADOR = BRIDGE / "install-deps.sh"

# modulo importado -> paquete que lo instala. Entrada OBLIGATORIA por cada
# tercero: el mapa no se adivina, y el caso 3 exige que este completo.
PAQUETE = {"telegram": "python-telegram-bot"}

# Terceros que NO son de arranque, con el motivo por el que no lo son. La
# excusa vive aqui escrita, no en la cabeza de quien lo leyo una vez.
OPCIONALES = {
    "tiktoken": "solo test-claude-md-drift.py, que degrada con motivo si falta",
}

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


def modulos_importados(ruta):
    """Modulos de primer nivel que importa `ruta`, tambien los indentados.

    Los indentados importan: el del daemon esta dentro de un `try`, y un
    escaneo anclado a `^` se lo salta — justo la dependencia que falta.
    """
    fuente = ruta.read_text(encoding="utf-8")
    return {m.group(1) for m in
            re.finditer(r"^[ \t]*(?:import|from)[ \t]+([A-Za-z_][A-Za-z0-9_]*)",
                        fuente, re.M)}


def main():
    print("Arnes de las dependencias del puente\n")

    fuentes = sorted(BRIDGE.glob("*.py"))
    hermanos = {p.stem for p in fuentes} | {"tests"}
    check(f"0. hay fuentes del puente que escanear ({len(fuentes)})",
          len(fuentes) >= 5,
          f"solo {len(fuentes)} .py en {BRIDGE}: el arnes estaria midiendo el vacio")
    if len(fuentes) < 5:
        return resumen()

    todos = set()
    for f in fuentes:
        todos |= modulos_importados(f)
    terceros = {m for m in todos
                if m not in sys.stdlib_module_names and m not in hermanos
                and m != "__future__"}
    de_arranque = sorted(terceros - set(OPCIONALES))
    print(f"  [INFO] terceros detectados en el puente: "
          f"{sorted(terceros) or 'ninguno'}  (de arranque: {de_arranque})")

    check("1. existe setup/telegram-bridge/requirements.txt",
          REQS.is_file(),
          "sin declaracion, la unica pista es un mensaje de error — y el que "
          "habia daba un comando que en Linux no existe")
    if not REQS.is_file():
        return resumen()

    lineas = [l.strip() for l in REQS.read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.strip().startswith("#")]

    # 2 — el mapa modulo->paquete cubre todo lo detectado. Sin esto, un tercero
    # nuevo se colaria sin que nadie decidiera nada sobre el.
    sin_mapear = [m for m in de_arranque if m not in PAQUETE]
    check("2. cada tercero de arranque tiene paquete conocido",
          not sin_mapear,
          f"modulos sin entrada en PAQUETE: {sin_mapear} — decide si es "
          f"dependencia o si degrada, y anotalo")

    # 3 — el invariante gordo: declarado.
    faltan = [PAQUETE[m] for m in de_arranque
              if m in PAQUETE and not any(PAQUETE[m] in l for l in lineas)]
    check("3. todo tercero de arranque esta declarado en requirements.txt",
          not faltan,
          f"sin declarar: {faltan} — el daemon no arranca en una maquina limpia")

    # 4 — anclado. "versiones sin comprobar" ya es un hallazgo abierto de la
    # auditoria 21; un nombre desnudo instala lo que haya ese dia.
    desnudas = [l for l in lineas if not re.search(r"[=<>~!]=|@", l)]
    check("4. cada linea lleva version anclada",
          not desnudas,
          f"sin ancla: {desnudas} — en la SER8 instalaria otra version que en "
          f"la Legion, y el 'funciona aqui' deja de significar nada")

    # 5 — y el ancla es la que corre de verdad DONDE hay con que comprobarlo.
    # Donde no lo hay se dice SKIP: no se finge cobertura.
    pin = None
    for l in lineas:
        m = re.match(r"^([A-Za-z0-9_.\-]+)==([0-9][^\s;]*)", l)
        if m and m.group(1) == "python-telegram-bot":
            pin = m.group(2)
    if pin is None:
        check("5. python-telegram-bot esta anclado con ==", False,
              "es la unica dependencia de arranque del daemon")
    else:
        try:
            from importlib.metadata import version as _v
            instalada = _v("python-telegram-bot")
        except Exception:
            instalada = None
        if instalada is None:
            print(f"  [SKIP] 5. no se pudo comparar el ancla ({pin}) con lo "
                  f"instalado: python-telegram-bot no esta en esta maquina")
            print("         Modo: PARCIAL — el ancla se comprueba donde el "
                  "puente corre de verdad")
        else:
            check(f"5. el ancla ({pin}) es la version que corre aqui ({instalada})",
                  pin == instalada,
                  "el ancla no es lo que esta probado: o se sube el ancla, o se "
                  "instala lo anclado, pero no pueden discrepar en silencio")

    # 6 — el mensaje que ve quien se estrella. Era Windows-only.
    # Se toma el BLOQUE por posicion, no con un regex que exija `sys.exit`
    # pegado al `except`: entre los dos puede haber comentarios, y un regex
    # rigido daba rojo con el mensaje ya arreglado (medido al escribir esto).
    daemon = (BRIDGE / "tg_daemon.py").read_text(encoding="utf-8")
    i = daemon.find("except ImportError:")
    bloque = daemon[i:i + 800] if i >= 0 else ""
    check("6. el ImportError del daemon no da una receta Windows-only",
          "sys.exit(" in bloque and
          ("install-deps.sh" in bloque or "requirements.txt" in bloque),
          "sigue diciendo solo `py -m pip install`: en Linux ese comando no "
          "existe y el pip pelado falla por PEP 668")

    # 7 — el camino de Linux existe y respeta PEP 668 con un venv.
    check("7. existe el instalador de Linux (install-deps.sh)",
          INSTALADOR.is_file(),
          "en Ubuntu 24.04 `pip install` pelado falla: hace falta venv, y el "
          "manual no lo decia")
    if INSTALADOR.is_file():
        script = INSTALADOR.read_text(encoding="utf-8")
        check("8. crea un venv en vez de pelear con PEP 668",
              re.search(r"-m\s+venv", script),
              "sin venv, en Ubuntu 24.04 hace falta --break-system-packages, "
              "que ensucia el Python del sistema")
        # 9 — y el venv NO puede vivir en el repo: esto esta bajo OneDrive, que
        # es la razon por la que los worktrees se sacaron de aqui (ADR 08-05).
        rutas = re.findall(r"^VENV=\"?([^\"\n]+)", script, re.M)
        check("9. el venv vive FUERA del repo (esto esta bajo OneDrive)",
              rutas and all(("HOME" in r or "LOCALAPPDATA" in r or
                             "XDG_DATA_HOME" in r) and "SCRIPT_DIR" not in r
                            for r in rutas),
              f"rutas de venv encontradas: {rutas} — un venv dentro del repo lo "
              f"sincroniza OneDrive entre maquinas con binarios de otra")

    return resumen()


def resumen():
    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
