r"""Cómo se invoca un `.sh` desde Python en LAS DOS plataformas.

POR QUÉ EXISTE (2026-08-20). Tres arneses aprendieron lo mismo por separado y
dos lo aprendieron mal:

  · `subprocess.run(["bash", str(ruta)])` en Windows manda `C:\Users\...` a
    bash, que se come las barras invertidas como escapes. Llega
    `C:UsersjlfloOneDrive...`, y la respuesta es `exit 127` CON el fichero
    delante — o sea, un rojo que parece del `.sh` y es del arnés.
  · `shutil.which("bash")` puede devolver el bash de WSL
    (`System32\bash.exe`), que vive en otro sistema de ficheros y tampoco
    encuentra una ruta `C:/...`.

La guarda `if not shutil.which("bash")` NO cubre ninguno de los dos: pregunta
«¿hay bash?» cuando lo que decide es «¿ESE bash sabe leer esta ruta?».

Aquí viven las dos respuestas, una sola vez. Lo importa quien invoque un `.sh`.
"""
import os
import shutil
from pathlib import Path

# Dónde vive Git Bash cuando el PATH no ayuda. Ojo al escribirlas: la versión
# anterior de esta lista llevaba BACKSPACES literales (`Git\x08in\x08ash.exe`)
# porque alguien tecleó `\b` fuera de una cadena cruda, así que el fallback no
# podía encontrar nada y el arnés seguía verde por tener Git Bash en el PATH.
CANDIDATOS_GIT_BASH = (
    os.path.join("C:\\", "Program Files", "Git", "bin", "bash.exe"),
    os.path.join("C:\\", "Program Files", "Git", "usr", "bin", "bash.exe"),
    os.path.join("C:\\", "Program Files (x86)", "Git", "bin", "bash.exe"),
)


def bash_exe() -> str:
    """El bash que sabe leer rutas `C:/...`.

    Prefiere el del PATH salvo que sea el de WSL (`System32`), y solo entonces
    busca Git Bash en disco. Si no hay ninguno devuelve `"bash"`: que falle a la
    vista, no en silencio.
    """
    w = shutil.which("bash")
    if w and "system32" not in w.lower():
        return w
    for c in CANDIDATOS_GIT_BASH:
        if os.path.isfile(c):
            return c
    return w or "bash"


def sh(ruta) -> str:
    r"""La ruta tal como bash la entiende en las dos plataformas.

    `as_posix()` y no `str()`: Git Bash acepta `C:/Users/...` sin problema y
    `C:\Users\...` no sobrevive al parser.
    """
    return Path(ruta).as_posix()


def cmd_bash(script, *args) -> list:
    """El argv completo, ya resuelto. Es lo que deberían usar los arneses."""
    return [bash_exe(), sh(script), *[str(a) for a in args]]


def bash_utilizable() -> tuple:
    """(bool, motivo). La pregunta que de verdad decide si un `.sh` se puede ejercer.

    `shutil.which("bash")` responde otra: si hay UN bash. Los dos arneses que
    esto vino a arreglar tenian esa guarda, pasaba, y fallaban igual — ni
    corrian ni se saltaban. Aqui se ESCRIBE un `.sh` de verdad y se ejecuta: si
    vuelve 0, ese bash sabe leer una ruta de esta plataforma.
    """
    import subprocess
    import tempfile
    exe = bash_exe()
    d = tempfile.mkdtemp(prefix="shellrun-")
    try:
        f = os.path.join(d, "sonda.sh")
        with open(f, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("#!/usr/bin/env bash\nexit 0\n")
        try:
            p = subprocess.run([exe, sh(f)], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=30)
        except OSError as e:
            return False, "no se pudo lanzar %r: %s" % (exe, e)
        if p.returncode != 0:
            return False, "%r no ejecuta un .sh de esta plataforma (exit %d): %s" % (
                exe, p.returncode, p.stdout.decode("utf-8", "replace").strip()[:200])
        return True, exe
    finally:
        import shutil as _sh
        _sh.rmtree(d, ignore_errors=True)
