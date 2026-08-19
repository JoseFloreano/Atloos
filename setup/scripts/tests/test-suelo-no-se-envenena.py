#!/usr/bin/env python3
"""
test-suelo-no-se-envenena.py — El arnes del suelo no puede tumbarse a si mismo.

POR QUE EXISTE (auditoria 39 §8.1, arreglado el 2026-08-19). `test-suelo-python.py`
fabricaba sus dos ficheros de laboratorio —`_lab_sucio.py`, con el constructo de
3.12 que TIENE que dar rojo, y `_lab_limpio.py`— **dentro del mismo arbol que
despues barre**:

    tmp = Path(base) / "setup" / "scripts" / "tests"

y los borraba en un `finally` cuyo `unlink` iba envuelto en `except OSError:
pass`. Dos caminos dejaban el veneno puesto:

  1. el proceso muere antes del `finally` (Ctrl-C, SIGKILL, corte de sesion);
  2. o el borrado falla y el `except` se lo come en silencio.

A partir de ahi el arnes sale **rojo para siempre**, y con el peor veredicto
posible: «1 de 61 ficheros NO compilan con 3.10 — `_lab_sucio.py`». Un fichero
que fabrico el. Un auditor externo lo provoco en vivo en una maquina donde el
borrado estaba denegado, y cada corrida dejaba el veneno para la siguiente.

EL INVARIANTE, que es lo que fija este arnes:

    ningun residuo de laboratorio —ni de una corrida futura ni de una vieja—
    puede hacer que `test-suelo-python.py` diga que el repo no compila.

Se arreglo por los dos lados y aqui se comprueban los dos, porque hacen falta
los dos: el TIRANTE (el laboratorio se fabrica en un `TemporaryDirectory` fuera
del repo) protege a las corridas futuras; el CINTURON (`ficheros()` ignora
`_lab_*.py`) protege a los clones donde un Ctrl-C de ayer YA dejo uno.

El caso 4 es el anti-artefacto: comprueba que el fichero plantado existe de
verdad, es `.py` y cuelga de la raiz barrida. Sin el, «no aparece en la lista»
podria significar «me equivoque de ruta» en vez de «lo excluye».

QUE CAZA CADA CASO, comprobado devolviendo los defectos uno a uno:

  · quitar el CINTURON  -> rojo en 1 y 2 (el barrido vuelve a tragarse el veneno)
  · quitar el TIRANTE   -> rojo en 4, porque el laboratorio se fabrica encima
                           del fichero plantado y lo borra al salir
  · `rmtree` de ruta ajena -> rojo en 6

⚠ Y lo que NO caza, dicho porque un arnes que se cree mas de lo que mide es peor
que ninguno: el caso 5 (no quedan residuos) solo se pone rojo en una maquina
donde el BORRADO FALLE. Aqui el `unlink` funciona, asi que con el tirante quitado
el caso 5 sigue verde y quien canta es el 4. En la maquina del auditor —donde el
borrado estaba denegado— seria el 5 el que hablara. Se dejan los dos.

Uso:  setup/scripts/py setup/scripts/tests/test-suelo-no-se-envenena.py
Salidas: 0 todo verde · 1 algun caso fallo
Solo stdlib.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent.parent          # setup/scripts/tests -> repo
SUELO = AQUI / "test-suelo-python.py"

# El constructo real que el arnes del suelo persigue: backslash dentro de la
# expresion de una f-string (PEP 701, solo legal desde 3.12).
VENENO = 'd = b"x"\ns = f"{d.count(b\'\\r\')}"\n'

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


def cargar_suelo():
    """Importa `test-suelo-python.py` (el nombre lleva guiones) como modulo."""
    spec = importlib.util.spec_from_file_location("suelo_bajo_prueba", SUELO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def residuos_en_el_repo():
    return [p for p in RAIZ.rglob("_lab_*.py") if ".git" not in p.parts]


def main():
    print("Arnes del arnes del suelo: que no se autoenvenene\n")

    mod = cargar_suelo()
    plantado = AQUI / "_lab_sucio.py"
    plantado.write_text(VENENO, encoding="utf-8")
    try:
        # 1 — EL CINTURON. Un residuo plantado no entra en el barrido.
        listados = mod.ficheros(RAIZ)
        check("1. un `_lab_*.py` plantado NO entra en el barrido del suelo",
              plantado not in listados,
              f"{plantado.name} sigue en la lista de {len(listados)} ficheros: "
              f"un Ctrl-C de ayer deja el repo rojo para siempre")

        # 2 — y el arnes REAL, de punta a punta, sigue verde con el veneno
        # puesto. Es la reproduccion literal del rojo del auditor.
        r = subprocess.run([sys.executable, str(SUELO)], cwd=str(RAIZ),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        check("2. y `test-suelo-python.py` sigue en verde con el veneno puesto",
              r.returncode == 0,
              f"exit={r.returncode}: "
              + " / ".join(l.strip() for l in (r.stdout or "").splitlines()
                           if "_lab_" in l)[:200])

        # 3 — el barrido sigue mirando el repo de verdad: si `ficheros()`
        # devolviera poco o nada, el caso 1 seria verde por vacio.
        check("3. el barrido sigue recogiendo el repo (no es vacio-y-verde)",
              len(listados) >= 30,
              f"solo {len(listados)} ficheros: el barrido dejo de mirar y el "
              f"caso 1 no mide nada")

        # 4 — ANTI-ARTEFACTO: el plantado existe, es .py y cuelga de la raiz
        # barrida. Sin esto, «no aparece» podria ser un error de ruta mio.
        check("4. anti-artefacto: el plantado existe y cuelga de la raiz barrida",
              plantado.is_file() and plantado.suffix == ".py"
              and RAIZ in plantado.parents,
              f"{plantado} no cumple las condiciones para que el caso 1 "
              f"signifique algo")
    finally:
        try:
            plantado.unlink()
        except OSError as exc:
            print(f"  [AVISO] no pude borrar el plantado {plantado}: {exc}")

    # 5 — EL TIRANTE. Correr el arnes del suelo no deja NADA en el repo.
    antes = set(residuos_en_el_repo())
    subprocess.run([sys.executable, str(SUELO)], cwd=str(RAIZ),
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace")
    nuevos = set(residuos_en_el_repo()) - antes
    check("5. correr el arnes del suelo no deja ningun `_lab_*` en el repo",
          not nuevos,
          f"dejo {[str(p.relative_to(RAIZ)) for p in nuevos]}: el laboratorio "
          f"volvio a fabricarse dentro del arbol que se barre")

    # 6 — y el laboratorio no se destruye con una ruta que venga de fuera.
    # Probando la mutacion que devolvia `tmp` al repo, un `rmtree(tmp)` se
    # llevo `setup/scripts/tests/` ENTERO (recuperado de git). `TemporaryDirectory`
    # solo puede borrar lo que el mismo creo; `rmtree` borra lo que le den.
    # Se mira el CODIGO, no la prosa: la primera version de este caso casaba
    # con su propio comentario explicativo y salia roja sobre codigo correcto.
    fuente = SUELO.read_text(encoding="utf-8")
    codigo = "\n".join(l for l in fuente.splitlines()
                       if not l.lstrip().startswith("#"))
    check("6. el laboratorio no se borra con `rmtree` de una ruta ajena",
          "TemporaryDirectory" in codigo and "rmtree(tmp" not in codigo,
          "un `rmtree` sobre la ruta que reciba `autoprueba` convierte un "
          "cambio de una linea en el borrado del arbol de tests")

    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos en verde")
    if fallos:
        print("FALLAN:")
        for n in fallos:
            print(f"  · {n}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
