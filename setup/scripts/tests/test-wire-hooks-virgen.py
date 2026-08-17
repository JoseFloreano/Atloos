#!/usr/bin/env python3
"""
test-wire-hooks-virgen.py — El instalador de hooks no puede reportar exito
habiendo cableado CERO hooks.

POR QUE EXISTE. `sync-hooks.sh` en una maquina virgen —sin `~/.claude`, que es
el estado de cualquier maquina donde Claude Code no ha arrancado todavia—
avisaba y salia **0**. Y su consumidor, `setup-new-machine.sh:251`, hace
`bash sync-hooks.sh || warn ...`: con exit 0 no entra al `||`, da el paso por
bueno y deja la maquina **sin capa 3**. Es el fallo que el sprint 11 existia
para cerrar, dentro del script que lo cierra (auditoria 31, H2).

La SER8 corre SIN VIGILANCIA HUMANA. Un aviso que nadie lee y un exit 0 son la
misma cosa: por eso el arreglo no puede ser solo hablar mas alto.

EL INVARIANTE, que es lo que este arnes fija y no el caso concreto:

    si al terminar hay CERO hooks cableados, el exit NO puede ser 0.

Ley uno de la casa aplicada al propio instalador: el codigo de salida no es el
estado. Aqui el script *es* quien establece el estado.

Se ejerce el NUCLEO (`wire-hooks.py`) y no los envoltorios, por dos razones: es
donde vive la decision (los dos wrappers delegan, y la paridad la vigila
test-sync-hooks-paridad.py), y asi el arnes corre igual donde no hay bash.

Tres puertas al mismo fail-open, y las tres son casos aqui:
  1. sin config dir            -> antes: WARN + exit 0
  2. fuente sin .py            -> antes: "ya estaba al dia" + exit 0
  3. config dir no creable     -> el arreglo no puede ser crear a ciegas

Uso:  setup/scripts/py setup/scripts/tests/test-wire-hooks-virgen.py
Salida: una linea por caso + resumen; exit 1 si algo falla.
Nunca toca el `~/.claude` real: cada caso corre con HOME de laboratorio.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent.parent
NUCLEO = RAIZ / "setup" / "scripts" / "wire-hooks.py"
FUENTE = RAIZ / "setup" / "hooks"

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


def corre(home, fuente=None):
    """Corre el nucleo con `home` como HOME de laboratorio. -> (exit, salida).

    Se sobrescriben HOME y USERPROFILE: `Path.home()` mira el primero en Unix y
    el segundo en Windows, y este arnes tiene que decir lo mismo en las dos.
    """
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    p = subprocess.run([sys.executable, str(NUCLEO),
                        "--hooks-source", str(fuente or FUENTE)],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       env=env, cwd=str(RAIZ), timeout=120)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def cableados(home):
    """(n_hooks_en_disco, n_eventos_en_settings) del config dir por defecto."""
    cfg = Path(home) / ".claude"
    hooks = len(list((cfg / "hooks").glob("*.py"))) if (cfg / "hooks").is_dir() else 0
    eventos = 0
    settings = cfg / "settings.json"
    if settings.is_file():
        try:
            s = json.loads(settings.read_text(encoding="utf-8"))
            eventos = len(s.get("hooks") or {})
        except Exception:
            eventos = 0
    return hooks, eventos


def main():
    print("Arnes del instalador de hooks en maquina virgen\n")

    # Cuantos hooks DEBE dejar: se cuenta la fuente, no una constante. Si
    # manana entra un hook nuevo y el instalador se lo salta, esto lo ve.
    esperados = len(list(FUENTE.glob("*.py")))
    check(f"0. la fuente tiene hooks que instalar ({esperados})",
          esperados > 0,
          f"sin .py en {FUENTE} este arnes estaria midiendo el vacio")
    if not esperados:
        return resumen()

    # ── Caso 1: el camino de la maquina nueva. HOME sin `~/.claude`.
    tmp1 = Path(tempfile.mkdtemp(prefix="lab-virgen-"))
    try:
        rc, salida = corre(tmp1)
        hooks, eventos = cableados(tmp1)
        check("1. en HOME virgen NO reporta exito con cero hooks",
              not (rc == 0 and hooks == 0),
              f"exit {rc} con {hooks} hooks: setup-new-machine.sh:251 usa "
              f"`|| warn`, asi que un 0 aqui deja la maquina sin capa 3 y el "
              f"instalador diciendo que fue bien")
        check("2. en HOME virgen deja la maquina PROTEGIDA (hooks + cableado)",
              hooks == esperados and eventos > 0,
              f"{hooks}/{esperados} hooks en disco y {eventos} eventos en "
              f"settings.json — avisar no basta: la SER8 corre sin vigilancia")
        check("3. si quedo protegida, el exit lo confirma",
              not (hooks == esperados and eventos > 0) or rc == 0,
              f"instalo todo y devolvio {rc}: un rojo que miente cansa igual "
              f"que un verde que miente")
    finally:
        shutil.rmtree(tmp1, ignore_errors=True)

    # ── Caso 2: MUTACION por la segunda puerta. Config dir presente, pero
    # fuente sin ningun .py: `cablea` salta los que no estan y no cambia nada.
    # Antes salia 0 diciendo "settings.json ya estaba al dia".
    tmp2 = Path(tempfile.mkdtemp(prefix="lab-sin-py-"))
    try:
        (tmp2 / ".claude").mkdir()
        fuente_vacia = tmp2 / "fuente"
        fuente_vacia.mkdir()
        shutil.copyfile(FUENTE / "hooks-map.json",
                        fuente_vacia / "hooks-map.json")
        rc, salida = corre(tmp2, fuente=fuente_vacia)
        hooks, _ = cableados(tmp2)
        check("4. con una fuente sin .py tampoco reporta exito",
              not (rc == 0 and hooks == 0),
              f"exit {rc} con {hooks} hooks: el instalador dijo que fue bien "
              f"habiendo cableado nada")
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    # ── Caso 3: y el arreglo no puede ser crear a ciegas. Si el config dir no
    # se puede crear, hay que salir != 0 — no seguir como si nada.
    tmp3 = Path(tempfile.mkdtemp(prefix="lab-imposible-"))
    try:
        falso_home = tmp3 / "soy-un-fichero"
        falso_home.write_text("no soy un directorio", encoding="utf-8")
        rc, salida = corre(falso_home)
        check("5. si el config dir no se puede crear, sale != 0",
              rc != 0,
              f"exit {rc}: no pudo crear nada y lo dio por bueno")
        check("6. y no dice 'Listo' cuando no lo esta",
              "Listo." not in salida,
              "el mensaje final de exito aparece en una corrida que fallo")
    finally:
        shutil.rmtree(tmp3, ignore_errors=True)

    # ── Caso 4: control positivo. El camino que la SER8 ya demostro el 08-16
    # sigue funcionando: config dir presente y fuente real.
    tmp4 = Path(tempfile.mkdtemp(prefix="lab-normal-"))
    try:
        (tmp4 / ".claude").mkdir()
        rc, salida = corre(tmp4)
        hooks, eventos = cableados(tmp4)
        check("7. con `~/.claude` presente sigue instalando y cableando",
              rc == 0 and hooks == esperados and eventos > 0,
              f"exit {rc}, {hooks}/{esperados} hooks, {eventos} eventos: el "
              f"arreglo rompio el camino que ya funcionaba")
    finally:
        shutil.rmtree(tmp4, ignore_errors=True)

    # ── Caso 5: EL GEMELO. `sync-hooks.ps1` no delega en este nucleo — son 196
    # lineas de reimplementacion (la deuda que declaro el sprint 11: "comparten
    # la lista, no la implementacion"), y tiene el mismo agujero por otra via:
    # `if (-not (Test-Path $cfg)) { continue }`. Un arreglo solo en bash deja
    # mintiendo al instalador de Windows, que es el que se usa a diario.
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        print("  [SKIP] 8. el gemelo PowerShell no se pudo ejercer: no hay "
              "pwsh ni powershell en esta maquina")
        print("         Modo: PARCIAL — la paridad del exit code queda sin "
              "comprobar aqui; se comprueba donde haya PowerShell")
    else:
        tmp5 = Path(tempfile.mkdtemp(prefix="lab-ps1-virgen-"))
        try:
            env = {**os.environ, "USERPROFILE": str(tmp5), "HOME": str(tmp5)}
            p = subprocess.run(
                [pwsh, "-NoProfile", "-NonInteractive", "-File",
                 str(RAIZ / "setup" / "sync-hooks.ps1")],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                env=env, cwd=str(RAIZ), timeout=180)
            hooks, eventos = cableados(tmp5)
            check("8. el gemelo PowerShell tampoco reporta exito con cero hooks",
                  not (p.returncode == 0 and hooks == 0),
                  f"exit {p.returncode} con {hooks} hooks: mismo fail-open que "
                  f"H2, en el envoltorio que corre en la Legion")
            check("9. y en HOME virgen deja la maquina protegida igual que el .sh",
                  hooks == esperados and eventos > 0,
                  f"{hooks}/{esperados} hooks y {eventos} eventos: los dos "
                  f"envoltorios tienen que dejar el MISMO estado")
        finally:
            shutil.rmtree(tmp5, ignore_errors=True)

    return resumen()


def resumen():
    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
