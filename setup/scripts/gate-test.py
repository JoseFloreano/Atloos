#!/usr/bin/env python3
"""
gate-test.py — Produce la evidencia de verde que exige el hook merge-gate-guard.

Corre el comando de test del proyecto y, **solo si sale con exit 0**, escribe
`.claude/gate-verde.json` con `{branch, sha, ts, cmd}`. El `sha` es el HEAD de la
rama en el momento de correr: si luego llega un commit más, la evidencia deja de
casar sola y el merge vuelve a estar bloqueado. Eso ES el "verde posterior al
último commit" del paso 2 de `workstream-merge-gate`, hecho verificable.

Por qué existe: la palabra del agente no es evidencia. En la prueba deliberada
del gate, una sesión afirmó "los tests pasaron hoy mismo" sobre un árbol que ya
había avanzado. Aquí el verde lo firma un exit code, no una frase.

Uso:
    py gate-test.py <rama>                    # usa el comando declarado
    py gate-test.py <rama> --cmd "pytest -q"  # o uno explícito

El comando se resuelve, en este orden:
  1. `--cmd`
  2. `GATE_TEST_CMD` del entorno (lo inyecta Claude Code desde settings.json)
  3. `env.GATE_TEST_CMD` del `.claude/settings.json` VERSIONADO del repo, leido
     del disco: asi funciona lo lance quien lo lance, tambien desde una
     terminal pelada. Nunca se lee `settings.local.json`, que es por-maquina.
  4. el bloque "## Comando de test" del CLAUDE.md del repo (primera linea de su
     bloque de codigo), para repos donde el CLAUDE.md si se versiona
Sin ninguno de los cuatro, no inventa nada: sale con error y lo dice. Sin
comando de test declarado no hay verde posible, y sin verde no se mergea.

Ruta estable: `sync-skills` lo instala en `~/.claude/scripts/` (F13 — una skill
corre desde el cwd de cualquier proyecto, así que no puede citar rutas del repo).

POR QUÉ NO CORRIÓ ES AHORA RUIDOSO (sprint 3, S2). En campo se invocó CUATRO
veces desde la rama equivocada y las cuatro se creyeron corridas:

  · este era el único de los seis scripts del repo SIN reconfigurar la
    codificación de salida, y tiene 17 caracteres acentuados en sus mensajes.
    En una consola cp1252 el `así` de la línea del aviso salía como `est?s`,
    que no es UTF-8 válido ⇒ `grep` declaró el fichero **binario** ⇒ se leyó
    "Binary file matches" como "sí, salió". Tres instrumentos rotos seguidos
    para leer un resultado que no existía;
  · y el aviso salía con `exit 2`, el mismo código que "no hay comando
    declarado": indistinguible en una tubería.

**Ese bug ya se había arreglado en `merge-gate-guard.py` (sprint 2) y no se
barrió la clase.** Cinco de seis lo tenían; el que no, era el que el humano
invoca a mano diez veces por sesión. Cuarta vez en este repo que se arregla la
instancia y no la clase.

Dos salidas posibles y se elige la segunda **a propósito**: (a) hacer el
checkout él mismo es cómodo pero mueve el árbol de trabajo bajo los pies de
quien lo llamó, y eso ya rompió una presentación en directo ("suspende los
merge ahorita estoy presentando"); (b) salir con un código propio (**3**) y una
primera línea **sin acentos** y con prefijo estable — `[gate-test] NO CORRIO:` —
que sobrevive a cualquier consola y se puede `grep`ear. Un gate no debe mover el
mundo por su cuenta: debe ser imposible de confundir con uno que corrió.

Códigos de salida:
  0 verde registrado · 1 suite en rojo · 2 no se puede resolver (uso, comando
  ausente, rama inexistente) · **3 NO CORRIÓ: estás en otra rama**
"""
import json
import os
import re
import subprocess
import sys
import time

# La consola de Windows es cp1252 y este script escribe acentos. Sin esto, el
# mensaje sale con bytes inválidos, `grep` lo declara binario y "Binary file
# matches" se lee como una corrida. Es la línea que faltaba (S2), y la llevan
# los otros cinco scripts del repo.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

EVIDENCIA = os.path.join(".claude", "gate-verde.json")   # el sitio de respaldo

# Nombre del fichero de evidencia dentro del directorio git COMÚN. Tiene que ser
# idéntico en `merge-gate-guard.py`, que lo resuelve con esta misma función
# copiada: son dos procesos distintos (un hook en ~/.claude/hooks/ y un script en
# ~/.claude/scripts/) y no comparten módulo. La duplicación no se puede quitar,
# pero SÍ se puede vigilar: `test-gate-test.py` afirma que los dos resuelven la
# MISMA ruta sobre el mismo repo, así que si alguien cambia una y no la otra, el
# arnés lo dice. Un contenido con dos puntos de consumo y un check encima deja
# de ser la enfermedad de siempre.
NOMBRE_EVIDENCIA = "gate-verde.json"


def ruta_evidencia(cwd):
    """Dónde vive el verde. Resuelto contra el directorio git COMÚN.

    POR QUÉ NO `.claude/` DEL ÁRBOL (auditoría del 08-14, H2). La ruta era
    relativa al árbol de trabajo, y los dos extremos usaban árboles distintos:
    `gate-test.py` escribía en `git rev-parse --show-toplevel` —en un worktree,
    el worktree— y `merge-gate-guard.py` leía en el `cwd` de quien integra —el
    checkout principal—. **La evidencia producida donde la skill manda no la veía
    quien integra**, así que el procedimiento documentado no se podía ejecutar.

    `--git-common-dir` apunta al `.git` compartido desde cualquier worktree, así
    que un verde producido en un worktree lo ve quien integra sin copiar nada
    entre árboles — la salida que el campo ya rechazó, y con razón: copiar
    ficheros de evidencia es fabricar el verde a mano.

    SE ELIGE ESTO Y NO «EL GATE SE CORRE DONDE SE INTEGRA» porque esa alternativa
    obliga a hacer checkout de la rama en el checkout principal, es decir a mover
    el árbol de trabajo del humano — que es exactamente lo que rompió una sesión
    en directo (*«suspende los merge ahorita estoy presentando»*). El sprint 3 ya
    lo decidió al revés por ese motivo; cambiarlo ahora para arreglar un bug de
    rutas sería pagar un coste real para evitar uno menor.

    ⚠ ESTO NO ABRE EL GATE. La evidencia sigue llevando `branch` y `sha`, y el
    guard sigue comparando el árbol del tip contra el del sha registrado: un
    verde de OTRA rama sigue sin valer, y uno anterior al último commit caduca
    solo. Lo único que cambia es DÓNDE se busca el fichero, no qué se le exige.

    Sin git utilizable se cae al sitio de siempre: un directorio que no es un
    repo no tiene dónde compartir nada, y ahí `.claude/` del árbol es correcto.
    """
    comun = git(["rev-parse", "--git-common-dir"], cwd)
    if not comun:
        return os.path.join(cwd, EVIDENCIA)
    if not os.path.isabs(comun):
        comun = os.path.join(cwd, comun)
    return os.path.join(os.path.abspath(comun), NOMBRE_EVIDENCIA)

# Exit propio del "no corrió". Distinto de 2 a propósito: 2 significa "no pude
# resolver qué correr" y se confundía con este en cualquier tubería.
NO_CORRIO = 3


def git(args, cwd="."):
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=10)
        return p.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def comando_declarado(raiz):
    """Primera línea del bloque de código bajo '## Comando de test' en CLAUDE.md."""
    ruta = os.path.join(raiz, "CLAUDE.md")
    try:
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            texto = f.read()
    except OSError:
        return ""
    m = re.search(r"^#+\s*Comando de test\s*$(.*?)```(?:\w+)?\s*\n(.+?)\n",
                  texto, re.S | re.M | re.I)
    return m.group(2).strip() if m else ""


def comando_en_settings(raiz):
    """`env.GATE_TEST_CMD` del .claude/settings.json VERSIONADO del repo.

    Solo settings.json, NUNCA settings.local.json: ese esta gitignorado y es
    por-maquina, asi que dejarle declarar el comando reabriria por detras el
    agujero por el que projects.json pierde — una copia local imponiendo un
    verde mas debil, sin diff donde se vea.
    """
    ruta = os.path.join(raiz, ".claude", "settings.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except FileNotFoundError:
        return ""
    except (OSError, ValueError) as exc:
        print(f"[gate-test] AVISO: no pude leer {ruta} ({exc}).\n"
              f"            Sigo con el resto de la resolucion.", file=sys.stderr)
        return ""
    if not isinstance(datos, dict):
        return ""
    env = datos.get("env")
    if not isinstance(env, dict):
        return ""
    return str(env.get("GATE_TEST_CMD", "")).strip()


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print("uso: gate-test.py <rama> [--cmd \"<comando>\"]", file=sys.stderr)
        return 2
    rama = args[0]
    cmd = ""
    if "--cmd" in args:
        i = args.index("--cmd")
        if i + 1 < len(args):
            cmd = args[i + 1]

    raiz = git(["rev-parse", "--show-toplevel"]) or os.getcwd()
    cmd = (cmd or os.environ.get("GATE_TEST_CMD", "")
           or comando_en_settings(raiz) or comando_declarado(raiz))
    if not cmd:
        print("Sin comando de test declarado: no hay verde posible y no se\n"
              "mergea. Declara uno en '.claude/settings.json' del repo, bajo\n"
              "'env.GATE_TEST_CMD' (viaja entre máquinas y se ve en el diff), o\n"
              "en el CLAUDE.md del repo bajo '## Comando de test' si aquí lo\n"
              "versionas, o pásalo con --cmd. Si el proyecto no tiene suite,\n"
              "redefine el verde (build? lint?) o este patrón no aplica aquí.",
              file=sys.stderr)
        return 2

    sha = git(["rev-parse", rama], raiz)
    if not sha:
        print(f"La rama '{rama}' no resuelve a ningún commit.", file=sys.stderr)
        return 2

    actual = git(["rev-parse", "--abbrev-ref", "HEAD"], raiz)
    if actual != rama:
        # PRIMERA LÍNEA SIN ACENTOS Y CON PREFIJO ESTABLE, a propósito: es la
        # única que sobrevive a una consola cp1252 y a un `grep`. El resto del
        # mensaje sí lleva acentos — ya no hacen daño con el reconfigure puesto,
        # pero la línea que se busca no depende de él.
        print(f"[gate-test] NO CORRIO: estas en '{actual}' y se pide "
              f"'{rama}'. La suite NO se ha ejecutado.\n"
              f"            La suite corre sobre el árbol de trabajo actual, "
              f"así que haz\n            checkout de '{rama}' antes, o la "
              f"evidencia mentiría. No se toca\n            tu árbol por ti: "
              f"mover la rama bajo los pies de quien llama ya\n"
              f"            rompió una sesión en directo.\n"
              f"            (exit {NO_CORRIO} = no corrio; 1 seria rojo, y no "
              f"es lo mismo)", file=sys.stderr)
        return NO_CORRIO

    print(f"[gate-test] {cmd}   (rama {rama} @ {sha[:8]})")
    rc = subprocess.run(cmd, shell=True, cwd=raiz).returncode
    if rc != 0:
        print(f"\n[gate-test] SUITE EN ROJO (exit {rc}). No se escribe evidencia:\n"
              f"            el merge sigue bloqueado, que es lo correcto.",
              file=sys.stderr)
        return 1

    destino = ruta_evidencia(raiz)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump({"branch": rama, "sha": sha,
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "cmd": cmd}, f)
    print(f"\n[gate-test] VERDE registrado en {destino} ({rama} @ {sha[:8]}).\n"
          f"            Vive en el directorio git común, así que lo ve quien\n"
          f"            integre desde cualquier worktree de este repo. Si llega\n"
          f"            otro commit, esta evidencia caduca sola.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
