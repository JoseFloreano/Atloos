#!/usr/bin/env python3
"""
test-run-tests.py — Arnés de contrato de setup/scripts/run-tests.py.

Monta repos git de laboratorio con arneses FALSOS y comprueba qué descubre el
runner, qué exit code devuelve y qué salida vuelca.

NUNCA apunta el runner a la raíz real del repo. Si lo hiciera, el runner se
descubriría a sí mismo corriéndose a sí mismo, en bucle: este archivo casa con
su propio glob (`setup/**/tests/test-*.py`).

Uso:  py setup/scripts/tests/test-run-tests.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "run-tests.py"))

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'OK  ' if ok else 'FALLA'}] {name}" + (f" -- {detail}" if detail and not ok else ""))


def repo(tmp):
    """Repo git de laboratorio. El runner resuelve su raíz con git."""
    subprocess.run(["git", "init", "-q", tmp], check=True)
    return tmp


def arnes(raiz, rel, codigo, mensaje):
    """Escribe un arnés falso que imprime `mensaje` y sale con `codigo`."""
    ruta = os.path.join(raiz, rel)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write("import sys\n"
                f"print({mensaje!r})\n"
                f"sys.exit({codigo})\n")
    return ruta


def run(raiz):
    p = subprocess.run([sys.executable, SCRIPT], cwd=raiz,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


def main():
    # --- Caso 1: dos arneses verdes en carpetas distintas -> exit 0 ---
    with tempfile.TemporaryDirectory(prefix="runtests-") as tmp:
        r = repo(tmp)
        arnes(r, "setup/hooks/tests/test-uno.py", 0, "verde uno")
        arnes(r, "setup/scripts/tests/test-dos.py", 0, "verde dos")
        rc, out, err = run(r)
        check("1. dos verdes en carpetas distintas -> exit 0",
              rc == 0, f"rc={rc} err={err[:120]!r}")
        check("1b. los descubre los dos",
              "test-uno.py" in out and "test-dos.py" in out, f"out={out[:200]!r}")

    # --- Caso 2: uno rojo -> exit 1 y se vuelca SU salida ---
    with tempfile.TemporaryDirectory(prefix="runtests-") as tmp:
        r = repo(tmp)
        arnes(r, "setup/hooks/tests/test-verde.py", 0, "SALIDA-DEL-VERDE")
        arnes(r, "setup/hooks/tests/test-rojo.py", 1, "SALIDA-DEL-ROJO")
        rc, out, err = run(r)
        todo = out + err
        check("2. un arnés rojo -> exit 1", rc == 1, f"rc={rc}")
        check("2b. vuelca la salida del que falla",
              "SALIDA-DEL-ROJO" in todo, f"todo={todo[:300]!r}")
        check("2c. NO vuelca la salida de los que pasan",
              "SALIDA-DEL-VERDE" not in todo, f"todo={todo[:300]!r}")

    # --- Caso 3: sin arneses -> exit 2, NO 0 (un verde vacío no es verde) ---
    with tempfile.TemporaryDirectory(prefix="runtests-") as tmp:
        r = repo(tmp)
        os.makedirs(os.path.join(r, "setup", "scripts"), exist_ok=True)
        rc, out, err = run(r)
        check("3. sin ningún arnés -> exit 2", rc == 2, f"rc={rc} out={out[:120]!r}")

    # --- Caso 4: archivos que NO son arneses no se corren ---
    with tempfile.TemporaryDirectory(prefix="runtests-") as tmp:
        r = repo(tmp)
        arnes(r, "setup/hooks/tests/test-si.py", 0, "SOY-ARNES")
        arnes(r, "setup/hooks/tests/helper.py", 1, "NO-SOY-ARNES")
        arnes(r, "setup/hooks/test-fuera.py", 1, "FUERA-DE-TESTS")
        rc, out, err = run(r)
        todo = out + err
        check("4. solo corre setup/**/tests/test-*.py -> exit 0",
              rc == 0, f"rc={rc} todo={todo[:300]!r}")
        check("4b. ignora helper.py y lo que está fuera de tests/",
              "helper.py" not in todo and "test-fuera.py" not in todo,
              f"todo={todo[:300]!r}")

    # --- Caso 5: el conteo del resumen es real ---
    with tempfile.TemporaryDirectory(prefix="runtests-") as tmp:
        r = repo(tmp)
        arnes(r, "setup/scripts/tests/test-a.py", 0, "a")
        arnes(r, "setup/scripts/tests/test-b.py", 0, "b")
        arnes(r, "setup/scripts/tests/test-c.py", 1, "c")
        rc, out, err = run(r)
        check("5. el resumen dice 2/3", "2/3" in out, f"out={out[:300]!r}")

    fallos = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
