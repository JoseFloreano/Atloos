#!/usr/bin/env python3
"""
test-skill-paths.py — Caza rutas inalcanzables en las skills.

Por qué existe (2026-08-07): la skill `notify-telegram` mandaba ejecutar
`notify_telegram.py` "del repo Atloos, en setup/telegram-bridge/". Desde el
cwd de `alphadogs`, en la MISMA máquina y con el puente configurado, el agente no
tuvo forma de encontrarlo: no hay relación de rutas entre `Python/Lock_in/
AlphaDogs` y `Python/Otros/Atloos`.

**La enfermedad**: una skill corre desde el cwd de CUALQUIER proyecto, así que
todo lo que mande ejecutar o leer necesita una ruta **estable por máquina**.

**Por qué hace falta un arnés y no un grep**: el barrido del 2026-08-03 buscó
rutas HARDCODEADAS (`Mis_Documentos`) — el síntoma. `notify-telegram` tenía la
misma enfermedad con otro síntoma: una ruta VAGA, no una equivocada. Sobrevivió
al grep. Esto busca la enfermedad.

Uso:  setup/scripts/py setup/scripts/tests/test-skill-paths.py
Salidas: 0 sin hallazgos · 1 hay rutas sospechosas
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ventana import RADIO, autoprueba as autoprueba_ventana, marcada  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parents[2]        # setup/
SKILLS = RAIZ / "skills"

# Rutas que SÍ son estables: se resuelven desde $HOME, igual en toda máquina.
ESTABLES = re.compile(
    r"~/\.claude/|\$HOME/\.claude/|%USERPROFILE%\\\.claude\\|\$env:USERPROFILE\\\.claude\\",
    re.I)

# Exención DECLARADA, junto al comando. Existe porque los tests del repo se
# corren desde el repo y eso es legítimo — pero tiene que decirlo donde el check
# la ve. Es greppable a propósito: `grep -rn "\[repo\]" setup/skills/` lista las
# vivas.
#
# Desde el sprint 7 se busca en una VENTANA de líneas y no en una sola: el
# check medía por línea y la gente escribe cruzando líneas, así que un `[repo]`
# en el renglón de justo debajo del comando no lo veía nadie (pasó el
# 2026-08-07 y otra vez en el sprint 6). El número de la ventana, y por qué es
# ese y no uno más ancho, en `_ventana.py`.
EXENTA = re.compile(r"\[repo\]")

# Un comando que el agente ejecutaría.
COMANDO = re.compile(r"(?:^|[\s`(])(?:py|python3?|bash|sh|pwsh|powershell|\./)\s+\S", re.I)

# Ruta absoluta que codifica UNA máquina (usuario, unidad).
MAQUINA = re.compile(r"[A-Za-z]:\\Users\\|/c/Users/|/home/[a-z]|Mis_Documentos", re.I)

# "el repo Atloos", "dentro del repo del setup"… sin decir cómo llegar.
VAGA = re.compile(r"repo\s+Atloos|repo\s+del\s+setup|dentro\s+del\s+repo", re.I)

# Ruta relativa al repo que se USA como si el cwd fuera el repo.
REPO_REL = re.compile(r"(?<![\w/.-])setup/(?:scripts|telegram-bridge|hooks)/\S+\.(?:py|sh|ps1)")

hallazgos = []


def revisa_texto(rel: str, texto: str):
    """Hallazgos de UN texto ya leído. Lista propia; no toca el global.

    Separado de `revisa()` desde el sprint 7 para que la autoprueba pueda
    fabricar el caso de la ventana sin escribir nada en disco. Un arnés que solo
    sabe mirar ficheros reales no puede probar sus propios bordes.
    """
    fuera = []
    lineas = texto.splitlines()
    for i, linea in enumerate(lineas):
        n = i + 1
        # Una línea que ya da la ruta estable está bien, aunque mencione otras.
        # `ESTABLES` se mira SOLO en su línea, y a propósito: no es una marca
        # que alguien pone al lado, es la ruta misma. Ensancharla diría "hay una
        # ruta buena cerca" y daría por buena la mala de al lado — justo el
        # falso negativo del que avisa `_ventana.py`.
        if ESTABLES.search(linea):
            continue
        # `[repo]` sí es una marca declarada junto al comando: ventana.
        if marcada(lineas, i, EXENTA):
            continue

        # 1) Ruta absoluta de una máquina: siempre es bug.
        if MAQUINA.search(linea):
            fuera.append((rel, n, "RUTA DE UNA MÁQUINA", linea.strip()))
            continue

        # 2) Se manda ejecutar algo por ruta relativa al repo.
        if REPO_REL.search(linea) and COMANDO.search(linea):
            fuera.append((rel, n, "EJECUTA POR RUTA DEL REPO", linea.strip()))
            continue

        # 3) "está en el repo Atloos" junto a un script: ruta vaga.
        if VAGA.search(linea) and re.search(r"\.(?:py|sh|ps1)\b", linea):
            fuera.append((rel, n, "RUTA VAGA", linea.strip()))
    return fuera


def revisa(archivo: Path):
    rel = archivo.relative_to(RAIZ.parent).as_posix()
    hallazgos.extend(revisa_texto(rel, archivo.read_text(encoding="utf-8")))


def autoprueba():
    """(bool, motivo). La ventana, por los dos bordes y sobre el check REAL.

    No se ejerce `marcada` a solas —eso ya lo hace `_ventana.autoprueba`— sino
    `revisa_texto`, que es lo que corre en producción: un `[repo]` a distancia
    RADIO exime, y a RADIO+1 NO exime. El segundo es el que importa, porque es
    el que impide que «ensanchar por si acaso» pase inadvertido.
    """
    # Fixture de laboratorio, NO un comando que nadie corra: tiene que disparar
    # el detector para que la ventana se pueda medir por los dos bordes. El
    # sprint 11 lo reescribió con el resolutor y dejó de dispararlo, así que la
    # autoprueba se puso roja midiendo una ventana vacía — se queda como estaba.
    comando = "Corre `py setup/scripts/gate-test.py <rama>` antes de integrar."
    relleno = "Texto de relleno que no dice nada."

    def texto(distancia):
        lineas = [relleno] * 6
        lineas[1] = comando
        if distancia == 0:
            lineas[1] = comando + "   [repo]"
        else:
            lineas[1 + distancia] = "Nota: se corre desde el repo. [repo]"
        return "\n".join(lineas)

    if revisa_texto("lab.md", texto(0)):
        return False, "la marca en la MISMA línea del bloque ya no exime"
    if revisa_texto("lab.md", texto(RADIO)):
        return False, (f"la marca a distancia {RADIO} no exime: el check sigue "
                       f"midiendo por línea (sprint 6 otra vez)")
    if not revisa_texto("lab.md", texto(RADIO + 1)):
        return False, (f"la marca a distancia {RADIO + 1} TAMBIÉN exime: la "
                       f"ventana es demasiado ancha y se comerá la marca de "
                       f"otro comando")
    if not revisa_texto("lab.md", "\n".join([relleno, comando, relleno])):
        return False, "sin marca ninguna, el comando por ruta del repo NO salta"

    ok, motivo = autoprueba_ventana(EXENTA, "[repo]")
    return (True, "") if ok else (False, motivo)


def main():
    if not SKILLS.is_dir():
        print(f"No encuentro {SKILLS}"); return 1
    archivos = sorted(SKILLS.rglob("*.md"))
    for f in archivos:
        if "_build" in f.parts:
            continue
        revisa(f)

    print(f"Revisados {len(archivos)} .md de skills\n")
    ok_ventana, motivo = autoprueba()
    print(f"  [AUTOPRUEBA] {'OK' if ok_ventana else 'FALLIDA'} — `[repo]` exime "
          f"a distancia {RADIO} y NO a distancia {RADIO + 1}"
          + (f"\n               {motivo}" if not ok_ventana else ""))
    print()
    if not hallazgos:
        print("Sin hallazgos: todo lo ejecutable se resuelve por ruta estable.")
        return 0 if ok_ventana else 1

    print(f"{len(hallazgos)} línea(s) sospechosa(s):\n")
    for rel, n, tipo, texto in hallazgos:
        print(f"  {tipo}")
        print(f"    {rel}:{n}")
        print(f"    {texto[:110]}")
    print("""
La regla: una skill corre desde el cwd de CUALQUIER proyecto. Todo lo que mande
ejecutar debe resolverse por una ruta estable por máquina —hoy
`~/.claude/scripts/`, que `sync-skills` puebla— y NO por la ruta del repo ni por
"búscalo en Atloos".

Si algún hallazgo es un falso positivo (documentación que no manda ejecutar
nada), reescribe la línea para que no parezca un comando. Y si de verdad es un
comando que se corre DESDE EL REPO —un test, por ejemplo—, decláralo en la
MISMA línea con `[repo]`: queda greppable y deja de saltar. Un arnés que grita
en falso se ignora a las dos semanas.""")
    return 1


if __name__ == "__main__":
    sys.exit(main())
