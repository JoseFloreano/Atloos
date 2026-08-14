#!/usr/bin/env python3
"""
test-gate-test.py — Arnés de contrato de la RESOLUCIÓN de setup/scripts/gate-test.py.

Qué comando acaba corriendo el gate, según qué fuentes estén presentes. No mide
la escritura de la evidencia en sí (eso ya lo cubre test-merge-gate-guard.py por
el otro lado): mide de dónde sale el comando.

El truco para saber qué comando corrió: `gate-verde.json` registra el `cmd`.

Uso:  py setup/scripts/tests/test-gate-test.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import json
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "gate-test.py"))

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'OK  ' if ok else 'FALLA'}] {name}" + (f" -- {detail}" if detail and not ok else ""))


def git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def repo(tmp):
    """Repo git con un commit y la rama `main`: el gate resuelve un sha."""
    git(["init", "-q", "-b", "main", tmp], os.path.dirname(tmp) or ".")
    git(["config", "user.email", "t@t.t"], tmp)
    git(["config", "user.name", "t"], tmp)
    with open(os.path.join(tmp, "semilla.txt"), "w", encoding="utf-8") as f:
        f.write("x\n")
    git(["add", "-A"], tmp)
    git(["commit", "-q", "-m", "semilla"], tmp)
    return tmp


def escribe(raiz, rel, contenido):
    ruta = os.path.join(raiz, rel)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(contenido)


def settings(raiz, cmd, local=False):
    nombre = "settings.local.json" if local else "settings.json"
    escribe(raiz, os.path.join(".claude", nombre),
            json.dumps({"env": {"GATE_TEST_CMD": cmd}}))


def claude_md(raiz, cmd):
    escribe(raiz, "CLAUDE.md", f"# Proyecto\n\n## Comando de test\n\n```\n{cmd}\n```\n")


def run(raiz, *args, env_extra=None):
    entorno = dict(os.environ)
    entorno.pop("GATE_TEST_CMD", None)
    if env_extra:
        entorno.update(env_extra)
    p = subprocess.run([sys.executable, SCRIPT, "main", *args], cwd=raiz,
                       env=entorno, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def cmd_registrado(raiz):
    ruta = os.path.join(raiz, ".claude", "gate-verde.json")
    if not os.path.exists(ruta):
        return None
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f).get("cmd")


def verde(marca):
    """Comando que sale 0 y se distingue de los demás por su último argumento.

    La marca viaja como argv sobrante de `-c`, que Python ignora. Nada de `#`
    para marcarlos: cmd.exe no tiene comentarios y el `#` acabaría de argumento
    igual, pero por accidente en vez de a propósito.

    EL INTÉRPRETE VA POR `sys.executable`, NO POR `py` (auditoría 22, H10). El
    lanzador `py` solo existe en Windows, así que este arnés daba **3/9 en
    Linux** y las seis caídas eran todas `/bin/sh: 1: py: not found` — el fixture
    fallaba, no el contrato que mide. Era cosmético mientras el único sitio donde
    corre sea Windows, y deja de serlo el día que el mini PC 24/7 sea Linux
    (D5/D8). `sys.executable` es absoluto y siempre existe: es el mismo Python
    que está corriendo este arnés.

    Va ENTRECOMILLADO porque `gate-test.py` ejecuta con `shell=True` y en Windows
    la ruta lleva espacios (`C:\\Program Files\\...`). Con cuatro comillas en la
    línea, cmd.exe no entra en su regla de "quita la primera y la última" —esa
    solo aplica con exactamente dos—, así que la cita sobrevive en los dos
    sistemas.
    """
    return f'"{sys.executable}" -c "import sys; sys.exit(0)" {marca}'


def main():
    # --- Caso 1: settings.json declara -> se usa ---
    with tempfile.TemporaryDirectory(prefix="gatetest-") as tmp:
        r = repo(os.path.join(tmp, "repo"))
        settings(r, verde("settings"))
        rc, out, err = run(r)
        check("1. settings.json declara -> el gate lo usa",
              rc == 0 and (cmd_registrado(r) or "").endswith("settings"),
              f"rc={rc} cmd={cmd_registrado(r)!r} err={err[:150]!r}")

    # --- Caso 2: el entorno gana sobre settings.json ---
    with tempfile.TemporaryDirectory(prefix="gatetest-") as tmp:
        r = repo(os.path.join(tmp, "repo"))
        settings(r, verde("settings"))
        rc, out, err = run(r, env_extra={"GATE_TEST_CMD": verde("entorno")})
        check("2. GATE_TEST_CMD del entorno gana sobre settings.json",
              (cmd_registrado(r) or "").endswith("entorno"),
              f"rc={rc} cmd={cmd_registrado(r)!r}")

    # --- Caso 3: --cmd gana sobre todo ---
    with tempfile.TemporaryDirectory(prefix="gatetest-") as tmp:
        r = repo(os.path.join(tmp, "repo"))
        settings(r, verde("settings"))
        rc, out, err = run(r, "--cmd", verde("flag"),
                           env_extra={"GATE_TEST_CMD": verde("entorno")})
        check("3. --cmd gana sobre entorno y settings.json",
              (cmd_registrado(r) or "").endswith("flag"),
              f"rc={rc} cmd={cmd_registrado(r)!r}")

    # --- Caso 4: sin settings.json, cae al CLAUDE.md (otros repos lo versionan) ---
    with tempfile.TemporaryDirectory(prefix="gatetest-") as tmp:
        r = repo(os.path.join(tmp, "repo"))
        claude_md(r, verde("claudemd"))
        rc, out, err = run(r)
        check("4. sin settings.json -> cae al CLAUDE.md",
              (cmd_registrado(r) or "").endswith("claudemd"),
              f"rc={rc} cmd={cmd_registrado(r)!r}")

    # --- Caso 5: settings.json ROTO -> aviso, cae al CLAUDE.md, sin traceback ---
    with tempfile.TemporaryDirectory(prefix="gatetest-") as tmp:
        r = repo(os.path.join(tmp, "repo"))
        escribe(r, os.path.join(".claude", "settings.json"), "{ esto no es json")
        claude_md(r, verde("claudemd"))
        rc, out, err = run(r)
        check("5. settings.json roto -> cae al CLAUDE.md",
              (cmd_registrado(r) or "").endswith("claudemd"),
              f"rc={rc} cmd={cmd_registrado(r)!r}")
        check("5b. avisa del JSON roto y NO suelta traceback",
              "AVISO" in err and "Traceback" not in err, f"err={err[:200]!r}")

    # --- Caso 5c: settings.json válido pero SIN objeto en la raíz (array) ---
    # Un JSON sintácticamente correcto cuyo nivel superior no es un objeto no
    # tiene `.get`: sin la guarda `isinstance(datos, dict)` esto revienta con
    # AttributeError y rc=1 (la peor salida: "suite en rojo" en el vocabulario
    # del script, cuando en realidad es "no hay declaración"). Debe comportarse
    # como cualquier settings.json inservible: avisar y caer al CLAUDE.md.
    with tempfile.TemporaryDirectory(prefix="gatetest-") as tmp:
        r = repo(os.path.join(tmp, "repo"))
        escribe(r, os.path.join(".claude", "settings.json"), "[1, 2, 3]")
        claude_md(r, verde("claudemd"))
        rc, out, err = run(r)
        check("5c. settings.json es un array (JSON válido, no objeto) -> "
              "cae al CLAUDE.md sin traceback",
              (cmd_registrado(r) or "").endswith("claudemd")
              and "Traceback" not in err,
              f"rc={rc} cmd={cmd_registrado(r)!r} err={err[:200]!r}")

    # --- Caso 6 (CANARIO): settings.local.json NO declara ---
    # Es por-maquina y gitignorado. Si se leyera, una copia local podria
    # imponer un verde mas debil sin aparecer en ningun diff: justo el agujero
    # por el que projects.json pierde.
    with tempfile.TemporaryDirectory(prefix="gatetest-") as tmp:
        r = repo(os.path.join(tmp, "repo"))
        settings(r, verde("local"), local=True)
        rc, out, err = run(r)
        check("6. CANARIO: settings.local.json NO se lee",
              rc == 2 and cmd_registrado(r) is None,
              f"rc={rc} cmd={cmd_registrado(r)!r} err={err[:150]!r}")

    # --- Caso 7: sin ninguna fuente -> sale 2 y lo explica ---
    with tempfile.TemporaryDirectory(prefix="gatetest-") as tmp:
        r = repo(os.path.join(tmp, "repo"))
        rc, out, err = run(r)
        check("7. sin declaración de ningún tipo -> exit 2 y lo dice",
              rc == 2 and "Sin comando de test declarado" in err,
              f"rc={rc} err={err[:200]!r}")

    # --- Caso 8: invocado desde la RAMA EQUIVOCADA (sprint 3, S2) ---
    # El fallo de campo: se corrió cuatro veces desde otra rama y las cuatro se
    # creyeron corridas. Tres cosas tienen que cumplirse a la vez, y las tres se
    # comprueban aquí porque en campo fallaron las tres a la vez:
    #   (a) exit != 0, y ademas != 1 — "no corrio" no es "rojo";
    #   (b) la salida es UTF-8 DECODIFICABLE. Se lee en BYTES y se decodifica en
    #       estricto: con `errors="replace"` este caso pasaria siempre, que es
    #       justo la venda que hizo invisible el bug;
    #   (c) NO queda `gate-verde.json`: un "no corrio" que deja evidencia seria
    #       peor que el bug original.
    with tempfile.TemporaryDirectory(prefix="gatetest-") as tmp:
        r = repo(os.path.join(tmp, "repo"))
        settings(r, verde("settings"))
        git(["checkout", "-q", "-b", "otra"], r)
        entorno = dict(os.environ)
        entorno.pop("GATE_TEST_CMD", None)
        p = subprocess.run([sys.executable, SCRIPT, "main"], cwd=r, env=entorno,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        crudo = p.stdout + p.stderr
        try:
            texto = crudo.decode("utf-8")       # ESTRICTO, sin "replace"
            decodifica = True
        except UnicodeDecodeError:
            texto, decodifica = "", False
        check("8a. rama equivocada -> exit propio (3), que no es 0 ni 1",
              p.returncode == 3,
              f"rc={p.returncode} err={crudo[:160]!r}")
        check("8b. rama equivocada -> salida UTF-8 decodificable en estricto",
              decodifica and "NO CORRIO" in texto,
              f"decodifica={decodifica} texto={texto[:160]!r}")
        check("8c. rama equivocada -> NO deja gate-verde.json",
              cmd_registrado(r) is None,
              f"cmd={cmd_registrado(r)!r}")
        check("8d. la primera linea es ASCII puro (sobrevive a cp1252)",
              decodifica and texto.strip().splitlines()[0].isascii(),
              f"primera={texto.strip().splitlines()[0][:120]!r}" if decodifica else "no decodifica")

    fallos = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
