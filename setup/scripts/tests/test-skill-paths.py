#!/usr/bin/env python3
"""
test-skill-paths.py — Caza rutas inalcanzables en las skills.

Por qué existe (2026-08-07): la skill `notify-telegram` mandaba ejecutar
`notify_telegram.py` "del repo ClaudeSetup, en setup/telegram-bridge/". Desde el
cwd de `alphadogs`, en la MISMA máquina y con el puente configurado, el agente no
tuvo forma de encontrarlo: no hay relación de rutas entre `Python/Lock_in/
AlphaDogs` y `Python/Otros/ClaudeSetup`.

**La enfermedad**: una skill corre desde el cwd de CUALQUIER proyecto, así que
todo lo que mande ejecutar o leer necesita una ruta **estable por máquina**.

**Por qué hace falta un arnés y no un grep**: el barrido del 2026-08-03 buscó
rutas HARDCODEADAS (`Mis_Documentos`) — el síntoma. `notify-telegram` tenía la
misma enfermedad con otro síntoma: una ruta VAGA, no una equivocada. Sobrevivió
al grep. Esto busca la enfermedad.

Uso:  py setup/scripts/tests/test-skill-paths.py
Salidas: 0 sin hallazgos · 1 hay rutas sospechosas
"""
import re
import sys
from pathlib import Path

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

# Exención DECLARADA, en la propia línea. Existe porque los tests del repo se
# corren desde el repo y eso es legítimo — pero tiene que decirlo donde el check
# la ve. Poner el contexto en la línea de ARRIBA no basta: el check es por línea
# y el arreglo semántico no se enteró del sintáctico (pasó el 2026-08-07).
# Es greppable a propósito: `grep -rn "\[repo\]" setup/skills/` lista las vivas.
EXENTA = re.compile(r"\[repo\]")

# Un comando que el agente ejecutaría.
COMANDO = re.compile(r"(?:^|[\s`(])(?:py|python3?|bash|sh|pwsh|powershell|\./)\s+\S", re.I)

# Ruta absoluta que codifica UNA máquina (usuario, unidad).
MAQUINA = re.compile(r"[A-Za-z]:\\Users\\|/c/Users/|/home/[a-z]|Mis_Documentos", re.I)

# "el repo ClaudeSetup", "dentro del repo del setup"… sin decir cómo llegar.
VAGA = re.compile(r"repo\s+ClaudeSetup|repo\s+del\s+setup|dentro\s+del\s+repo", re.I)

# Ruta relativa al repo que se USA como si el cwd fuera el repo.
REPO_REL = re.compile(r"(?<![\w/.-])setup/(?:scripts|telegram-bridge|hooks)/\S+\.(?:py|sh|ps1)")

hallazgos = []


def revisa(archivo: Path):
    rel = archivo.relative_to(RAIZ.parent).as_posix()
    for n, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
        # Una línea que ya da la ruta estable está bien, aunque mencione otras.
        # Y una que declara `[repo]` asume la excepción por escrito.
        if ESTABLES.search(linea) or EXENTA.search(linea):
            continue

        # 1) Ruta absoluta de una máquina: siempre es bug.
        if MAQUINA.search(linea):
            hallazgos.append((rel, n, "RUTA DE UNA MÁQUINA", linea.strip()))
            continue

        # 2) Se manda ejecutar algo por ruta relativa al repo.
        if REPO_REL.search(linea) and COMANDO.search(linea):
            hallazgos.append((rel, n, "EJECUTA POR RUTA DEL REPO", linea.strip()))
            continue

        # 3) "está en el repo ClaudeSetup" junto a un script: ruta vaga.
        if VAGA.search(linea) and re.search(r"\.(?:py|sh|ps1)\b", linea):
            hallazgos.append((rel, n, "RUTA VAGA", linea.strip()))


def main():
    if not SKILLS.is_dir():
        print(f"No encuentro {SKILLS}"); return 1
    archivos = sorted(SKILLS.rglob("*.md"))
    for f in archivos:
        if "_build" in f.parts:
            continue
        revisa(f)

    print(f"Revisados {len(archivos)} .md de skills\n")
    if not hallazgos:
        print("Sin hallazgos: todo lo ejecutable se resuelve por ruta estable.")
        return 0

    print(f"{len(hallazgos)} línea(s) sospechosa(s):\n")
    for rel, n, tipo, texto in hallazgos:
        print(f"  {tipo}")
        print(f"    {rel}:{n}")
        print(f"    {texto[:110]}")
    print("""
La regla: una skill corre desde el cwd de CUALQUIER proyecto. Todo lo que mande
ejecutar debe resolverse por una ruta estable por máquina —hoy
`~/.claude/scripts/`, que `sync-skills` puebla— y NO por la ruta del repo ni por
"búscalo en ClaudeSetup".

Si algún hallazgo es un falso positivo (documentación que no manda ejecutar
nada), reescribe la línea para que no parezca un comando. Y si de verdad es un
comando que se corre DESDE EL REPO —un test, por ejemplo—, decláralo en la
MISMA línea con `[repo]`: queda greppable y deja de saltar. Un arnés que grita
en falso se ignora a las dos semanas.""")
    return 1


if __name__ == "__main__":
    sys.exit(main())
