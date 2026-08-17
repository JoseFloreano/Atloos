#!/usr/bin/env python3
"""
test-sync-hooks-paridad.py — Los dos envoltorios registran LO MISMO, o rojo.

POR QUÉ EXISTE (sprint 11). `sync-hooks` tiene dos envoltorios —`.ps1` para
Windows, `.sh` para Linux/macOS— y la enfermedad conocida de esta casa es que
una lista viva por duplicado y las dos copias se separen sin que nadie se entere
(el `=6` contra el `=3`). La lista se movió a `setup/hooks/hooks-map.json`, que
es fuente única; este arnés comprueba que EL RESULTADO también coincide, que es
lo que de verdad importa: dos envoltorios pueden leer el mismo dato y cablearlo
distinto.

QUÉ AFIRMA:

  1. Ninguno de los dos envoltorios lleva su PROPIA lista de hooks. Un nombre de
     hook escrito dentro del `.ps1` o del `.sh` es una segunda fuente de verdad,
     aunque hoy coincida.
  2. Corriendo cada envoltorio sobre un HOME de laboratorio, el conjunto
     {(evento, matcher, hook)} que queda cableado en `settings.json` es el MISMO
     para los dos, y es el que declara el mapa.

DOS MODOS, Y NUNCA UN SALTO EN SILENCIO. El `.ps1` necesita PowerShell y el
`.sh` necesita bash. En la SER8 no hay `pwsh` (medido el 2026-08-16), así que
allí el punto 2 no se puede ejercer contra los dos. En ese caso este arnés NO
dice "OK": corre el envoltorio que sí puede, hace la comparación ESTÁTICA del
punto 1, e imprime en grande de qué modo viene su verde. Un check que se salta
lo que no puede comprobar y sale 0 igual es el fallo que este repo persigue.

LA MUTACIÓN. Se le da a un envoltorio un mapa DOCTORADO al que le falta un hook
y se exige que la comparación lo cace (exit 1); se le devuelve el mapa bueno y
se exige que vuelva a coincidir. Sin eso, este arnés podría estar comparando dos
conjuntos vacíos y diciendo que son iguales.

Uso:  setup/scripts/py setup/scripts/tests/test-sync-hooks-paridad.py
Salidas: 0 los envoltorios coinciden · 1 divergen, o uno lleva lista propia
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parents[2]        # setup/
MAPA = RAIZ / "hooks" / "hooks-map.json"
PS1 = RAIZ / "sync-hooks.ps1"
SH = RAIZ / "sync-hooks.sh"


def declarados():
    """{(evento, matcher, fichero)} tal y como lo declara la fuente única."""
    datos = json.loads(MAPA.read_text(encoding="utf-8"))
    return {(h["event"], h.get("matcher"), h["file"]) for h in datos["hooks"]}


# ── 1. Nadie lleva lista propia ───────────────────────────────────────────
def lista_propia(ruta, nombres):
    """Nombres de hook escritos DENTRO del envoltorio. Debe salir vacío.

    Se ignoran los comentarios: los dos envoltorios explican en prosa por qué
    la lista se movió, y nombrar un hook al contarlo no es duplicarlo. Lo que
    no puede haber es un nombre de hook en una línea de CÓDIGO.
    """
    hallados = []
    for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        limpia = linea.strip()
        if limpia.startswith("#") or limpia.startswith("//"):
            continue
        for nombre in nombres:
            if nombre in limpia:
                hallados.append((n, nombre, limpia[:70]))
    return hallados


# ── 2. Lo que cada envoltorio deja cableado ───────────────────────────────
def cableado(settings):
    """{(evento, matcher, basename)} leído de un settings.json ya escrito."""
    if not settings.is_file():
        return set()
    datos = json.loads(settings.read_text(encoding="utf-8-sig"))
    fuera = set()
    for evento, entradas in (datos.get("hooks") or {}).items():
        for entrada in entradas or []:
            for inner in entrada.get("hooks") or []:
                cmd = inner.get("command") or ""
                # El comando lleva intérprete y ruta absoluta, que SON distintos
                # en cada máquina y en cada envoltorio a propósito. Lo comparable
                # es el hook y su matcher.
                base = Path(cmd.split()[-1].strip('"')).name if cmd else ""
                fuera.add((evento, entrada.get("matcher"), base))
    return fuera


def lab():
    """HOME de laboratorio con un `.claude/` vacío dentro."""
    d = Path(tempfile.mkdtemp(prefix="paridad-hooks-"))
    (d / ".claude").mkdir()
    return d


def entorno(home):
    """Env con HOME y USERPROFILE apuntando al laboratorio.

    Los dos envoltorios descubren los config dirs por el home del usuario
    (`$env:USERPROFILE` el .ps1, `Path.home()` el núcleo del .sh), así que
    moviendo el home se ejercen SIN flags especiales: se prueba el camino real.
    """
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    return env


def bash_exe():
    """El bash que sabe leer rutas `C:/...`.

    En Windows `bash` en el PATH puede ser el de WSL (`System32\bash.exe`), que
    vive en OTRO sistema de ficheros: recibe `C:/Users/...`, no lo encuentra y
    responde `/bin/bash: ...: No such file or directory` — exit 127 con el
    fichero delante. Lo caza que el arnés eligiera mal, no que el `.sh` esté mal.
    """
    w = shutil.which("bash")
    if w and "system32" not in w.lower():
        return w
    for c in (r"C:\Program Files\Gitinash.exe",
              r"C:\Program Files (x86)\Gitinash.exe"):
        if os.path.isfile(c):
            return c
    return w or "bash"


def corre_sh(home, hooks_source=None):
    # `as_posix()` y no `str()`: en Windows los backslashes de la ruta llegan a
    # bash como escapes y la ruta desaparece (`C:UsersjlfloOneDrive...`, exit
    # 127). Git Bash acepta `C:/Users/...` sin problema.
    cmd = [bash_exe(), SH.as_posix()]
    if hooks_source:
        # El .sh fija --hooks-source; para doctorarlo se llama al núcleo directo.
        cmd = [bash_exe(), (RAIZ / "scripts" / "py").as_posix(),
               (RAIZ / "scripts" / "wire-hooks.py").as_posix(),
               "--hooks-source", Path(hooks_source).as_posix()]
    p = subprocess.run(cmd, env=entorno(home), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, cwd=str(RAIZ.parent))
    return p.returncode, p.stdout.decode("utf-8", "replace")


def powershell():
    """El ejecutable de PowerShell disponible, o None."""
    for c in ("powershell", "pwsh"):
        if shutil.which(c):
            return c
    return None


def corre_ps1(home, exe):
    p = subprocess.run([exe, "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", str(PS1)],
                       env=entorno(home), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, cwd=str(RAIZ.parent))
    return p.returncode, p.stdout.decode("utf-8", "replace")


def mapa_doctorado():
    """Copia de setup/hooks/ con un hook MENOS en el mapa. Devuelve (dir, quitado)."""
    d = Path(tempfile.mkdtemp(prefix="paridad-doctor-")) / "hooks"
    shutil.copytree(RAIZ / "hooks", d,
                    ignore=shutil.ignore_patterns("tests"))
    datos = json.loads((d / "hooks-map.json").read_text(encoding="utf-8"))
    quitado = datos["hooks"].pop()["file"]
    (d / "hooks-map.json").write_text(json.dumps(datos, ensure_ascii=False,
                                                 indent=2), encoding="utf-8")
    return d, quitado


def main():
    print("\nParidad de los envoltorios de sync-hooks\n")
    fallos = []
    esperado = declarados()
    nombres = {f for _, _, f in esperado}

    # ── Punto 1: ningún envoltorio lleva su propia lista ──────────────────
    print("── Lista propia dentro de los envoltorios ───────────────────\n")
    for ruta in (PS1, SH):
        if not ruta.is_file():
            fallos.append(f"falta el envoltorio {ruta.name}")
            print(f"  [FALTA] {ruta.name}")
            continue
        hallados = lista_propia(ruta, nombres)
        if hallados:
            fallos.append(f"{ruta.name} lleva su propia lista de hooks")
            for n, nombre, txt in hallados:
                print(f"  [ROJO] {ruta.name}:{n} nombra '{nombre}' en código")
                print(f"         {txt}")
        else:
            print(f"  [OK] {ruta.name} no nombra ningún hook: lee el mapa")

    # ── Punto 2: lo que cablea cada uno ───────────────────────────────────
    print("\n── Lo que queda cableado ────────────────────────────────────\n")
    exe = powershell()
    home_sh = lab()
    rc, salida = corre_sh(home_sh)
    if rc != 0:
        fallos.append(f"sync-hooks.sh salió {rc}")
        print(f"  [ROJO] sync-hooks.sh salió {rc}\n{salida}")
    obtenido_sh = cableado(home_sh / ".claude" / "settings.json")
    print(f"  sync-hooks.sh  registró {len(obtenido_sh)} hooks")

    if obtenido_sh != esperado:
        fallos.append("sync-hooks.sh no registra lo que declara el mapa")
        print(f"  [ROJO] sobran {obtenido_sh - esperado} · faltan {esperado - obtenido_sh}")

    if exe:
        home_ps = lab()
        rc, salida = corre_ps1(home_ps, exe)
        obtenido_ps = cableado(home_ps / ".claude" / "settings.json")
        print(f"  sync-hooks.ps1 registró {len(obtenido_ps)} hooks  (via {exe})")
        if rc != 0:
            fallos.append(f"sync-hooks.ps1 salió {rc}")
            print(f"  [ROJO] sync-hooks.ps1 salió {rc}\n{salida[-1500:]}")
        if obtenido_ps != obtenido_sh:
            fallos.append("los dos envoltorios registran conjuntos DISTINTOS")
            print(f"  [ROJO] solo en .ps1: {obtenido_ps - obtenido_sh}")
            print(f"         solo en .sh : {obtenido_sh - obtenido_ps}")
        else:
            print("  [OK] los dos envoltorios registran EXACTAMENTE lo mismo")
        modo = "COMPLETO (los dos envoltorios ejercidos)"
    else:
        modo = ("PARCIAL — no hay PowerShell en esta máquina, así que el .ps1 NO "
                "se ejerció.\n         El punto 1 (lista propia) sí se comprobó "
                "en los dos. Para el verde\n         completo, corre este arnés "
                "en una máquina con PowerShell.")

    # ── La mutación ───────────────────────────────────────────────────────
    print("\n── Mutación ─────────────────────────────────────────────────\n")
    doctor, quitado = mapa_doctorado()
    home_mut = lab()
    corre_sh(home_mut, hooks_source=doctor)
    mutado = cableado(home_mut / ".claude" / "settings.json")
    if mutado == obtenido_sh:
        fallos.append("MUTACIÓN NO CAZADA: falta un hook y la comparación no lo ve")
        print(f"  [ROJO] quité '{quitado}' del mapa y el conjunto no cambió:")
        print("         este arnés no estaba comparando nada.")
    else:
        print(f"  [OK] quitado '{quitado}' del mapa → la comparación lo caza")
        print(f"       ({len(obtenido_sh)} hooks → {len(mutado)})")
    home_vuelta = lab()
    corre_sh(home_vuelta)
    if cableado(home_vuelta / ".claude" / "settings.json") != obtenido_sh:
        fallos.append("devuelto el mapa bueno, el resultado NO vuelve a coincidir")
        print("  [ROJO] con el mapa bueno el resultado no se reproduce")
    else:
        print("  [OK] devuelto el hook, vuelve a coincidir")

    print(f"\n── Modo de esta corrida: {modo}\n")
    if fallos:
        print("ROJO:")
        for f in fallos:
            print(f"  · {f}")
        return 1
    print("Los dos envoltorios de sync-hooks registran el mismo cableado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
