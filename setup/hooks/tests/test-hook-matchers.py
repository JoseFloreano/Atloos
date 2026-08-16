#!/usr/bin/env python3
"""
test-hook-matchers.py — El barrido de la CLASE, no de la instancia.

POR QUÉ EXISTE (sprint 7). `merge-gate-guard` se registraba con matcher `Bash`,
así que no veía los comandos git que van por la herramienta `PowerShell` — en
una máquina Windows, media sesión sin compuerta. El arreglo de esa instancia es
de dos líneas; lo que este arnés impide es la CUARTA repetición: primero el
verbo (`merge` sí, `push` no), luego el entorno (el worktree), luego la
herramienta, y la vez siguiente será otra frontera mal dibujada por un hook
nuevo que nadie relacionó con este.

QUÉ AFIRMA, sobre `setup/sync-hooks.ps1` y `setup/hooks/*.py`:

  1. Todo hook `.py` de la fuente está REGISTRADO en `$HookMap`. Uno que no lo
     esté no se cablea: existe en el repo y no corre en ninguna parte.
  2. Todo hook de `PreToolUse` que INSPECCIONE comandos de shell —lo dice su
     propio código: lee `tool_input` y `command`— lleva en el matcher las DOS
     herramientas que mandan una línea de shell, `Bash` y `PowerShell`.
  3. Y ese mismo hook SE COMPORTA IGUAL con las dos. Es la puerta que muerde:
     con el matcher ancho y el filtro estrecho, el hook se registra, se invoca y
     sale 0 sin mirar nada — un arreglo que parece hecho y no lo está.

CÓMO SE COMPRUEBA EL 3, Y POR QUÉ NO COMO LA PRIMERA VEZ. La versión que salió
del sprint 7 lo miraba en el CÓDIGO: exigía una línea que nombrara las dos
herramientas. La auditoría la mutó —`HERRAMIENTAS_SHELL = {"bash"}`, el guard
otra vez ciego, nueve escapes reabiertos— y este arnés dijo verde, porque el
docstring del propio guard ya nombra las dos en una línea. **El check reconocía
el disfraz histórico (`!= "Bash"`) y no el contrato**, que es el patrón de la
casa metido dentro del arnés que lo persigue.

Ahora se mide el COMPORTAMIENTO, que es lo que se afirma: se le manda al hook la
MISMA línea de comandos una vez por herramienta, sobre un repo de laboratorio, y
se exige que los exit codes COINCIDAN. Un filtro estrecho las separa al instante
(2 por Bash, 0 por PowerShell) diga lo que diga el texto. Y se exige que alguna
sonda lo ENGANCHE —que alguna dé distinto de 0—: si ninguna lo ejerce, la
igualdad sería cierta y vacía, así que eso también es rojo, con el mensaje de
que hay que darle una sonda que lo toque.

Lo que NO afirma: nada sobre hooks que no inspeccionan shell. El de Graphiti
mira argumentos de un MCP y los de `Stop`/`PreCompact` ni reciben herramienta;
ensancharles el matcher sería ruido, y este arnés los enumera para dejar dicho
que se miraron.

Uso:  py setup/hooks/tests/test-hook-matchers.py
Salidas: 0 el barrido está limpio · 1 algún hook queda fuera de su contrato
"""
import json
import re
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

RAIZ = Path(__file__).resolve().parents[2]          # setup/
HOOKS = RAIZ / "hooks"
SYNC = RAIZ / "sync-hooks.ps1"

# Las herramientas que entregan una línea de shell en `tool_input.command`. Si
# mañana aparece una tercera, se añade aquí y este arnés señala a quién le falta.
HERRAMIENTAS_SHELL = ("Bash", "PowerShell")

# Una entrada del $HookMap. El `Matcher` puede ser una cadena o `$null`.
ENTRADA = re.compile(
    r'@\{\s*File\s*=\s*"(?P<file>[^"]+)"\s*;\s*'
    r'Event\s*=\s*"(?P<event>[^"]+)"\s*;\s*'
    r'Matcher\s*=\s*(?:"(?P<matcher>[^"]*)"|\$null)')


def registrados(texto):
    """[(fichero, evento, matcher|None)] tal y como los cablea sync-hooks.ps1."""
    return [(m.group("file"), m.group("event"), m.group("matcher"))
            for m in ENTRADA.finditer(texto)]


def codigo(fuente):
    """El código sin comentarios de línea. Un check que una línea de comentario
    puede satisfacer no comprueba nada: aquí se exige la afirmación EN CÓDIGO."""
    return "\n".join(l for l in fuente.splitlines()
                     if not l.lstrip().startswith("#"))


def inspecciona_shell(fuente):
    """¿Este hook lee la línea de comandos de la herramienta? Lo dice su código.

    No es una lista blanca a mano —que se desincroniza— sino la huella de leer
    `tool_input` y sacar de ahí `command`. Un hook que no toca ninguna de las
    dos cosas no tiene nada que ganar con un matcher más ancho.
    """
    src = codigo(fuente)
    return "tool_input" in src and "command" in src


def falta_en_matcher(matcher):
    """Herramientas de shell que el matcher NO nombra."""
    m = (matcher or "").lower()
    return [h for h in HERRAMIENTAS_SHELL if h.lower() not in m]


# Líneas de comandos con las que se ejerce a un hook que inspecciona shell. No
# hace falta que las bloquee todas: hace falta que trate igual a las dos
# herramientas, y que al menos UNA lo enganche (si ninguna lo toca, la igualdad
# es cierta y vacía). Un hook nuevo que ninguna sonda ejerza pone esto en rojo a
# propósito, para que quien lo añada traiga la suya.
SONDAS = [
    ("merge a protegida sin evidencia", "git merge feat/x"),
    ("el mismo con el operador de llamada", "& git merge feat/x"),
    ("push a protegida sin evidencia", "git push origin main"),
    ("comando inocuo", "git status"),
]


def repo_lab():
    """Repo con `main` (activa) y una rama `feat/x` con un commit propio."""
    d = tempfile.mkdtemp(prefix="hook-matchers-")
    def sh(args):
        subprocess.run(args, cwd=d, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, check=True)
    sh(["git", "init", "-q", "-b", "main"])
    sh(["git", "config", "user.email", "t@t"])
    sh(["git", "config", "user.name", "t"])
    (Path(d) / "a.py").write_text("x = 1\n", encoding="utf-8")
    sh(["git", "add", "-A"])
    sh(["git", "commit", "-q", "-m", "base"])
    sh(["git", "checkout", "-q", "-b", "feat/x"])
    (Path(d) / "b.py").write_text("y = 2\n", encoding="utf-8")
    sh(["git", "add", "-A"])
    sh(["git", "commit", "-q", "-m", "feature"])
    sh(["git", "checkout", "-q", "main"])
    return d


def invoca(ruta_hook, comando, herramienta, lab):
    """Exit code del hook con ese payload PreToolUse. Como corre de verdad."""
    payload = {"session_id": "s1", "hook_event_name": "PreToolUse",
               "tool_name": herramienta, "tool_input": {"command": comando}}
    import os
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = lab
    p = subprocess.run([sys.executable, str(ruta_hook)],
                       input=json.dumps(payload).encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       cwd=lab, env=env)
    return p.returncode


def desigualdades(ruta_hook, lab):
    """(diferencias, engancha). La PROPIEDAD, medida en comportamiento.

    `diferencias` = [(sonda, {herramienta: rc})] donde las herramientas NO
    coinciden — el hook privilegia una y es ciego a la otra, diga lo que diga su
    texto. `engancha` = alguna sonda produjo algo distinto de 0, sin lo cual la
    igualdad no probaría nada.
    """
    difs, engancha = [], False
    for nombre, comando in SONDAS:
        rcs = {h: invoca(ruta_hook, comando, h, lab) for h in HERRAMIENTAS_SHELL}
        if any(v != 0 for v in rcs.values()):
            engancha = True
        if len(set(rcs.values())) > 1:
            difs.append((nombre, rcs))
    return difs, engancha


def autoprueba():
    """Mutación: fabrica el defecto del sprint 7 y exige que el barrido lo cace.

    Un check verificado solo contra el repo ya arreglado no está verificado —es
    H7 otra vez—, así que aquí se le da el `$HookMap` viejo y el filtro viejo y
    se comprueba que los señala a los dos, y que la versión buena pasa.
    """
    viejo = '@{ File = "x.py"; Event = "PreToolUse";  Matcher = "Bash" }'
    nuevo = '@{ File = "x.py"; Event = "PreToolUse";  Matcher = "Bash|PowerShell" }'
    if len(registrados(viejo)) != 1:
        return False, "el lector de $HookMap no reconoce una entrada válida"
    if falta_en_matcher(registrados(viejo)[0][2]) != ["PowerShell"]:
        return False, "el matcher `Bash` a secas NO se señala: el barrido es ciego"
    if falta_en_matcher(registrados(nuevo)[0][2]):
        return False, "el matcher `Bash|PowerShell` se señala igual: falso positivo"

    if not inspecciona_shell('cmd = tool_input.get("command")\n'):
        return False, "no se reconoce como inspector de shell un hook que lo es"
    if inspecciona_shell('# tool_input command\nx = 1\n'):
        return False, ("un COMENTARIO basta para pasar por inspector de shell: "
                       "el check se puede satisfacer sin código")

    # La mutación que importa, y en la forma NUEVA. La primera versión de este
    # arnés miraba el código y la auditoría la pasó por encima: puso el filtro
    # estrecho, el guard se quedó ciego y esto dijo verde, porque el docstring
    # ya nombraba las dos herramientas. Un hook falso con cada filtro, y se
    # exige que el estrecho se note en el COMPORTAMIENTO.
    cuerpo = (
        "import json, sys\n"
        "d = json.load(sys.stdin)\n"
        "t = (d.get('tool_name') or '').lower()\n"
        "if t not in %s: sys.exit(0)\n"
        "cmd = (d.get('tool_input') or {}).get('command') or ''\n"
        "sys.exit(2 if 'merge' in cmd else 0)\n")
    caja = tempfile.mkdtemp(prefix="hook-matchers-fake-")
    lab = repo_lab()
    try:
        estrecho = Path(caja) / "estrecho.py"
        ancho = Path(caja) / "ancho.py"
        estrecho.write_text(cuerpo % '{"bash"}', encoding="utf-8")
        ancho.write_text(cuerpo % '{"bash", "powershell"}', encoding="utf-8")

        difs, engancha = desigualdades(estrecho, lab)
        if not engancha:
            return False, ("ni la sonda del hook falso lo engancha: las SONDAS "
                           "no ejercen nada y la igualdad sería vacía")
        if not difs:
            return False, ("un filtro estrecho `{\"bash\"}` NO se nota: es "
                           "exactamente la mutación que la auditoría metió y "
                           "este arnés dejó pasar")
        difs_ancho, engancha_ancho = desigualdades(ancho, lab)
        if difs_ancho or not engancha_ancho:
            return False, ("el filtro ANCHO se señala igual: falso positivo, y "
                           "un arnés que grita en falso se acaba desactivando")
    finally:
        shutil.rmtree(caja, ignore_errors=True)
        shutil.rmtree(lab, ignore_errors=True)
    return True, ""


def main():
    if not SYNC.is_file():
        print(f"No encuentro {SYNC}")
        return 1

    entradas = registrados(SYNC.read_text(encoding="utf-8"))
    en_disco = sorted(p.name for p in HOOKS.glob("*.py"))
    fallos = []

    print("Barrido de hooks — matcher y comportamiento por herramienta\n")
    ok_auto, motivo = autoprueba()
    print(f"  [AUTOPRUEBA] {'OK' if ok_auto else 'FALLIDA'} — caza el matcher "
          f"`Bash` a secas Y un filtro estrecho que no se ve en el texto"
          + (f"\n               {motivo}" if not ok_auto else ""))
    if not ok_auto:
        fallos.append("la autoprueba del propio barrido")

    # ── 1 · nadie se queda sin cablear ────────────────────────────────────
    registrados_nombres = {f for f, _e, _m in entradas}
    sin_registrar = [n for n in en_disco if n not in registrados_nombres]
    fantasmas = sorted(registrados_nombres - set(en_disco))

    print(f"\n── {len(entradas)} hooks en $HookMap · {len(en_disco)} .py en "
          f"setup/hooks/ " + "─" * 20 + "\n")
    for fichero, evento, matcher in entradas:
        ruta = HOOKS / fichero
        fuente = ruta.read_text(encoding="utf-8") if ruta.is_file() else ""
        shell = inspecciona_shell(fuente)
        etiqueta = "INSPECCIONA SHELL" if shell else "no mira comandos"
        print(f"  {fichero:<32}{evento:<13}{matcher or '(sin matcher)':<22}{etiqueta}")

        if not shell or evento != "PreToolUse":
            continue
        faltan_m = falta_en_matcher(matcher)
        if faltan_m:
            fallos.append(f"{fichero}: el matcher no nombra {', '.join(faltan_m)}")

        # La propiedad, en comportamiento: la MISMA línea por cada herramienta
        # tiene que dar el MISMO exit. Aquí no vale lo que diga el docstring.
        lab = repo_lab()
        try:
            difs, engancha = desigualdades(ruta, lab)
        finally:
            shutil.rmtree(lab, ignore_errors=True)
        if not engancha:
            fallos.append(f"{fichero}: ninguna sonda lo engancha, así que la "
                          f"igualdad entre herramientas sería cierta y vacía — "
                          f"añade a SONDAS una línea que lo ejerza")
        for nombre, rcs in difs:
            detalle = " · ".join(f"{h}={rcs[h]}" for h in HERRAMIENTAS_SHELL)
            fallos.append(f"{fichero}: trata distinto a cada herramienta con "
                          f"«{nombre}» ({detalle})")
        if engancha and not difs:
            print(f"  {'':<32}{'':<13}{'':<22}"
                  f"↳ {len(SONDAS)} sondas, mismo exit por Bash y PowerShell")

    if sin_registrar:
        fallos.append("hooks en la fuente que NADIE cablea: "
                      + ", ".join(sin_registrar))
    if fantasmas:
        fallos.append("entradas de $HookMap sin fichero en la fuente: "
                      + ", ".join(fantasmas))

    print()
    if not fallos:
        print("  Barrido limpio: todo hook de PreToolUse que lee comandos de\n"
              "  shell nombra las dos herramientas, en el matcher Y en su\n"
              "  filtro; y todo hook de la fuente está registrado.")
        return 0

    print(f"  {len(fallos)} problema(s):\n")
    for f in fallos:
        print(f"    · {f}")
    print("""
La regla: un hook de `PreToolUse` que inspecciona comandos de shell tiene que
cazar las DOS herramientas que los entregan. Y son dos puertas, no una — el
matcher de `sync-hooks.ps1` decide si se INVOCA, el filtro por `tool_name`
decide si MIRA. Ensanchar solo la primera deja el agujero abierto con aspecto
de arreglado.""")
    return 1


if __name__ == "__main__":
    sys.exit(main())
