#!/usr/bin/env python3
"""
test-bootstrap-sin-docker.py — El alta de una máquina NO depende de Docker.

EL FALLO QUE CIERRA (2026-08-19). `setup-new-machine.sh` contaba Docker y Docker
Compose como **errores críticos** y moría con `exit 1` en su bloque 1:

    command -v docker ... || { err "Docker no encontrado."; ERRORS=$((ERRORS+1)); }
    [ $ERRORS -gt 0 ] && { err "Hay $ERRORS errores críticos."; exit 1; }

Pero **Docker solo lo pide Graphiti, que está POSPUESTO por ADR**
(`ADR-20260808-graphiti-ratificado-pospuesto`). O sea: el script que da de alta
una máquina nueva se negaba a instalar las skills, los **hooks** y los
esqueletos de `.env` por una dependencia que el propio repo había decidido no
usar — y lo hacía en el primer minuto, cuando la máquina todavía no tiene nada
con lo que depurarlo. En la SER8 eso significaba quedarse sin capa 3.

LOS CASOS QUE MANDAN son el 1 y el 2, y son las dos direcciones:
  · 1 — sin Docker el preflight sale **0** y dice que Graphiti se salta.
  · 2 — con `CON_GRAPHITI=1` y sin Docker sale **1**. Si esto no bloqueara, el
        arreglo habría convertido «muere siempre» en «no puedes exigirlo nunca»,
        que es el mismo defecto por el otro lado.

CÓMO SE EJERCE «UNA MÁQUINA SIN DOCKER» SIN DEPENDER DE ESTA MÁQUINA: el script
lee `DOCKER_CMD`, y aquí se le pasa el nombre de un binario que no existe. No es
un adorno de pruebas — es el mismo patrón que el `sep` inyectado de `deny_glob`
y el `which` inyectable de `altas.revisar`, y existe porque el fallo vive
justamente en la máquina que NO tiene la herramienta.

LÍMITE DECLARADO, y es grande: esto mide **el preflight y la decisión**, no una
corrida completa. Correr el bootstrap entero escribiría en `~/.claude`, el
crontab y `~/.config` de quien lance la suite, así que no se hace. Para que el
límite no se coma la garantía, el caso 4 comprueba por ESTRUCTURA que ningún
bloque de Graphiti quedó fuera de su guardia — que es lo que se rompería si
alguien añade un `docker` suelto dentro de un año.

Uso:  setup/scripts/py setup/scripts/tests/test-bootstrap-sin-docker.py   [repo]
Salidas: 0 todo verde · 1 algún caso falló
"""
import os
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

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "setup" / "scripts"))
import shellrun  # noqa: E402  (como se invoca un .sh en LAS DOS plataformas)

SH = RAIZ / "setup" / "setup-new-machine.sh"
PS1 = RAIZ / "setup" / "setup-new-machine.ps1"

results = []


def check(nombre, ok, detalle=""):
    results.append((nombre, bool(ok)))
    print(f"[{'OK  ' if ok else 'FALLA'}] {nombre}" + (f"\n         {detalle}" if not ok and detalle else ""))


def corre_preflight(extra_env=None, args=("--preflight",), home=None):
    """(rc, salida) del bootstrap en modo preflight, con HOME desechable.

    El HOME temporal es cinturón: el preflight sale ANTES de escribir nada, así
    que si alguna vez alguien mete un `mkdir` antes del corte, el destrozo cae
    en un temporal y este arnés lo delata en vez de tocar el home real.
    """
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["LOCAL"] = "1"                       # sin OneDrive: no es lo que se mide
    env.pop("CON_GRAPHITI", None)
    env.pop("SIN_GRAPHITI", None)
    env.update(extra_env or {})
    # `shellrun.cmd_bash` y no `["bash", str(SH)]`: en Windows los backslashes
    # de la ruta llegan a bash como escapes y el fichero desaparece (exit 127
    # con el .sh delante). El helper resuelve el bash Y la forma de la ruta.
    p = subprocess.run(shellrun.cmd_bash(SH, *args), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, env=env, timeout=120,
                       stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def main():
    usable, motivo = shellrun.bash_utilizable()
    if not usable:
        print("[SKIP] el bootstrap .sh no se puede ejercer aquí: %s" % motivo)
        return 0
    if not SH.is_file():
        check("0. existe setup-new-machine.sh", False, f"no está en {SH}")
        return 1

    sin_docker = {"DOCKER_CMD": "docker-que-no-existe-en-esta-maquina"}

    # --- Caso 1: SIN Docker, el alta sigue y lo dice ---
    with tempfile.TemporaryDirectory(prefix="bootstrap-") as tmp:
        rc, out = corre_preflight(sin_docker, home=tmp)
        plano = out.lower()
        check("1. sin Docker: preflight sale 0 (el alta NO muere)", rc == 0,
              f"rc={rc}\n{out[-600:]}")
        check("1b. y dice que se salta Graphiti, con su motivo",
              "graphiti" in plano and ("salta" in plano or "sin graphiti" in plano),
              out[-600:])
        check("1c. y promete lo que SÍ hará: skills y hooks",
              "hooks" in plano and "skills" in plano, out[-600:])
        # Que el preflight no escriba: el HOME temporal debe quedar como estaba.
        creados = [p.name for p in Path(tmp).iterdir()]
        check("1d. el preflight NO escribe nada en el disco", not creados,
              f"creó: {creados!r}")

    # --- Caso 2: si lo EXIGES y no hay Docker, sí bloquea ---
    with tempfile.TemporaryDirectory(prefix="bootstrap-") as tmp:
        env = dict(sin_docker)
        env["CON_GRAPHITI"] = "1"
        rc, out = corre_preflight(env, home=tmp)
        check("2. CON_GRAPHITI=1 sin Docker: sale != 0 (no se finge)", rc != 0,
              f"rc={rc}\n{out[-600:]}")

    # --- Caso 3: SIN_GRAPHITI se respeta aunque Docker exista ---
    # Se ejerce con un `docker` FABRICADO que responde a `compose version`: sin
    # esto, en una máquina sin Docker el caso pasaría por el motivo equivocado
    # (que es como se cuela un check que no comprueba nada).
    with tempfile.TemporaryDirectory(prefix="bootstrap-") as tmp:
        falso = Path(tmp) / "bin" / "docker"
        falso.parent.mkdir(parents=True)
        falso.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        falso.chmod(0o755)
        casa = Path(tmp) / "home"
        casa.mkdir()
        rc, out = corre_preflight({"DOCKER_CMD": str(falso)}, home=casa)
        check("3. con Docker disponible, el preflight dice que SÍ lo montará",
              rc == 0 and "montar" in out.lower(), f"rc={rc}\n{out[-600:]}")
        rc, out = corre_preflight({"DOCKER_CMD": str(falso), "SIN_GRAPHITI": "1"},
                                  home=casa)
        check("3b. SIN_GRAPHITI=1 manda sobre un Docker presente",
              rc == 0 and "sin graphiti" in out.lower(), f"rc={rc}\n{out[-600:]}")

    # --- Caso 4: por ESTRUCTURA, nada de Graphiti quedó fuera de su guardia ---
    # Es el que cubre lo que el preflight no puede: que los bloques 2-9 estén
    # dentro de `if [ "${GRAPHITI}" = true ]`. Se mide contando guardias contra
    # usos de docker, no leyendo prosa.
    fuente = SH.read_text(encoding="utf-8")
    guardias = len(re.findall(r'if \[ "\$\{GRAPHITI\}" = true \]', fuente))
    check("4. el .sh guarda sus bloques de Graphiti", guardias >= 5,
          f"solo {guardias} guardia(s): algún bloque de Graphiti corre sin protección")
    # Solo donde docker se EJECUTA. Las líneas que lo imprimen —`info "...docker
    # compose..."`, la receta del resumen— no son invocaciones, y marcarlas era
    # un falso positivo de este mismo arnés (cazado al estrenarlo). Un check que
    # grita en falso se apaga a las dos semanas, así que se afina en vez de
    # aflojarse: se exige que `docker` esté en posición de comando.
    IMPRIME = re.compile(r"^\s*(info|echo|warn|err|ok|printf|#)\b")
    EJECUTA = re.compile(r"(?:^|&&|\|\||;|\|\s|\$\()\s*docker\s+(compose|exec|pull|--version)\b")
    sueltos = [l.strip() for l in fuente.splitlines()
               if EJECUTA.search(l) and not IMPRIME.match(l)
               and "${DOCKER_CMD}" not in l]
    check("4b. ningún `docker` ejecutable escapa a DOCKER_CMD", not sueltos,
          f"sueltos={sueltos!r}")
    # Y lo que NO puede estar guardado, porque es el corazón del arreglo.
    corte = fuente.find("6-9. Todo lo que sigue es de Graphiti")
    antes = fuente[:corte] if corte != -1 else fuente
    check("4c. sync-skills y sync-hooks corren FUERA del guardia de Graphiti",
          "sync-skills.sh" in antes and "sync-hooks.sh" in antes,
          "si caen dentro, una máquina sin Docker vuelve a quedarse sin capa 3")

    # --- Caso 5: paridad con el gemelo PowerShell ---
    if not PS1.is_file():
        check("5. existe el gemelo .ps1", False, f"no está en {PS1}")
    else:
        ps = PS1.read_text(encoding="utf-8", errors="replace")
        faltan = [t for t in ("SinGraphiti", "ConGraphiti", "Preflight", "DOCKER_CMD")
                  if t not in ps]
        check("5. el .ps1 declara los mismos modos que el .sh", not faltan,
              f"le faltan: {faltan!r} — los dos scripts dan de alta la misma casa")

        # El BOM. Es invariante de la casa (`setup/README.md`): powershell.exe
        # lee un .ps1 sin BOM como ANSI y los `─`/`—` inyectan comillas fantasma
        # que rompen el parseo — y este fichero está lleno de esos caracteres.
        # Se comprueba AQUÍ porque cualquier edición del .ps1 puede comérselo, y
        # el daño solo aparece en la otra máquina, que es donde nadie mira.
        crudo = PS1.read_bytes()
        check("5a. el .ps1 conserva su BOM UTF-8", crudo.startswith(b"\xef\xbb\xbf"),
              f"empieza por {crudo[:6]!r} — sin BOM, powershell.exe lo lee como ANSI")

        # Y la mitad que este arnés NO puede afirmar. Se DICE, con la marca que
        # `run-tests.py` lee: el .sh se ejerce de verdad (casos 1-3) y del .ps1
        # solo se mira el texto. Callarlo dejaría creer que los dos están
        # medidos igual, que es el defecto que el sprint 15 vino a cerrar.
        pwsh = shutil.which("pwsh") or shutil.which("powershell")
        if not pwsh:
            print("[SKIP] 5b. la sintaxis del gemelo .ps1 NO se comprobó: no hay "
                  "pwsh ni powershell en esta máquina. Del .ps1 solo se ha mirado "
                  "que declare los modos — que corra es otra cosa.")
            print("Modo: PARCIAL — el lado Windows se comprueba donde haya PowerShell")
        else:
            # ParseFile y no `-File`: **parsear no es ejecutar**. Correr el
            # bootstrap para ver si parsea daría de alta la máquina de quien
            # lance la suite, que es justo lo que un arnés no puede hacer.
            comando = (
                "$errs = $null; "
                "[void][System.Management.Automation.Language.Parser]::ParseFile("
                "'" + str(PS1).replace("'", "''") + "', [ref]$null, [ref]$errs); "
                "if ($errs -and $errs.Count -gt 0) { $errs | ForEach-Object "
                "{ Write-Output $_.Message }; exit 1 }")
            p = subprocess.run([pwsh, "-NoProfile", "-Command", comando],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               timeout=120)
            check("5b. el gemelo .ps1 parsea", p.returncode == 0,
                  p.stdout.decode("utf-8", "replace")[:400])

    print()
    fallos = [n for n, ok in results if not ok]
    print(f"[test-bootstrap-sin-docker] {len(results) - len(fallos)}/{len(results)} en verde.")
    if fallos:
        print("\n  Recordatorio del porqué: Docker es dependencia de Graphiti, no del\n"
              "  alta. Un bootstrap que muere sin Docker deja la máquina sin hooks.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
