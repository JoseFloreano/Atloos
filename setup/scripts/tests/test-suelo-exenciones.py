#!/usr/bin/env python3
"""
test-suelo-exenciones.py — La exención del suelo caduca, y caducar duele.

Por que existe (auditoria 31, H5 · seccion 9 item 8). `test-suelo-python.py`
exige un interprete REAL del suelo (3.10) y la SER8 es Ubuntu 24.04, que trae
3.12: alli ese arnes no podia dar verde NUNCA, y `run-tests.py` lo pintaba rojo
para siempre. *Una suite que nunca esta verde deja de leerse*, y el dia que se
ponga roja de verdad nadie lo notara.

La salida elegida no fue un `skip` —que en dos sprints se vuelve costumbre—
sino una exencion DECLARADA, por maquina y con fecha. Este arnes existe porque
ese mecanismo solo vale si su caducidad MUERDE, y una caducidad que nadie
ejerce es una fecha decorativa.

EL CASO QUE MANDA es el 3: exencion pasada de fecha -> ROJO. Si ese caso se
pusiera verde, habriamos construido exactamente el skip permanente que el
mecanismo evita, solo que con mejor prosa.

Uso:  setup/scripts/py setup/scripts/tests/test-suelo-exenciones.py       [repo]
Salidas: 0 todo verde · 1 algun caso fallo
"""
import importlib.util
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent

# El modulo bajo prueba se llama con guiones, asi que no se puede `import`.
_spec = importlib.util.spec_from_file_location(
    "suelo_bajo_prueba", AQUI / "test-suelo-python.py")
suelo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(suelo)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

results = []


def check(nombre, condicion, detalle=""):
    results.append((nombre, bool(condicion)))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle}")


def fichero_con(tmp, datos):
    ruta = Path(tmp) / "exenciones.json"
    ruta.write_text(datos if isinstance(datos, str) else json.dumps(datos),
                    encoding="utf-8")
    return ruta


def main():
    print("Arnes de las exenciones del suelo de Python\n")
    hoy = date(2026, 8, 17)

    with tempfile.TemporaryDirectory(prefix="exen-") as tmp:
        # --- 1. Exencion vigente -> vigente ---
        f = fichero_con(tmp, {"la-maquina": {"motivo": "x", "hasta": "2026-11-17"}})
        estado, det = suelo.exencion(f, maquina="la-maquina", hoy=hoy)
        check("1. exencion con fecha futura -> vigente",
              estado == "vigente", f"estado={estado!r} det={det!r}")

        # --- 2. Insensible a mayusculas: platform.node() no es estable ---
        estado, _ = suelo.exencion(f, maquina="LA-MAQUINA", hoy=hoy)
        check("2. la clave de maquina no distingue mayusculas",
              estado == "vigente",
              "'Floreano_Legion' y 'floreano_legion' son la misma maquina")

        # --- 3. EL CASO QUE MANDA: caducada -> caducada (y el arnes rojo) ---
        f = fichero_con(tmp, {"la-maquina": {"motivo": "x", "hasta": "2026-08-16"}})
        estado, det = suelo.exencion(f, maquina="la-maquina", hoy=hoy)
        check("3. exencion pasada de fecha -> CADUCADA",
              estado == "caducada",
              f"estado={estado!r}: una exencion que no caduca es un skip "
              f"permanente con mejor nombre")
        check("3b. y el mensaje dice que hay que DECIDIR, no renovar y ya",
              "instalar" in det and "suelo" in det,
              f"det={det!r}")
        # El mensaje tiene que nombrar la maquina JUZGADA, no la que corre el
        # arnes: si dice 'Floreano_Legion' cuando esta juzgando a la SER8, el
        # que lo lea depura la maquina equivocada.
        check("3c. el mensaje nombra la maquina juzgada, no la que corre",
              "la-maquina" in det, f"det={det!r}")

        # --- 4. El mismo dia todavia vale (el limite es inclusivo) ---
        f = fichero_con(tmp, {"la-maquina": {"motivo": "x", "hasta": "2026-08-17"}})
        estado, _ = suelo.exencion(f, maquina="la-maquina", hoy=hoy)
        check("4. el ultimo dia declarado todavia vale", estado == "vigente")

        # --- 5. Sin fecha NO hay exencion ---
        f = fichero_con(tmp, {"la-maquina": {"motivo": "sin fecha"}})
        estado, _ = suelo.exencion(f, maquina="la-maquina", hoy=hoy)
        check("5. exencion SIN campo 'hasta' -> caducada (no vale)",
              estado == "caducada",
              "la fecha es el mecanismo entero; sin ella esto es un skip")

        f = fichero_con(tmp, {"la-maquina": {"motivo": "x", "hasta": "manana"}})
        estado, _ = suelo.exencion(f, maquina="la-maquina", hoy=hoy)
        check("5b. fecha con formato invalido -> caducada", estado == "caducada")

        # --- 6. Maquina sin entrada -> ninguna exencion (el arnes sale 2) ---
        f = fichero_con(tmp, {"otra": {"motivo": "x", "hasta": "2026-11-17"}})
        estado, _ = suelo.exencion(f, maquina="la-maquina", hoy=hoy)
        check("6. maquina sin entrada -> sin exencion",
              estado is None, "una exencion ajena no puede cubrir a esta maquina")

        # --- 7. Las claves de documentacion (_algo) no son maquinas ---
        f = fichero_con(tmp, {"_contrato": {"motivo": "x", "hasta": "2026-11-17"}})
        estado, _ = suelo.exencion(f, maquina="_contrato", hoy=hoy)
        check("7. las claves '_...' son documentacion, no maquinas",
              estado is None)

        # --- 8. Fichero roto NO concede exencion (falla cerrado) ---
        f = fichero_con(tmp, "{ esto no es json")
        estado, _ = suelo.exencion(f, maquina="la-maquina", hoy=hoy)
        check("8. JSON roto -> sin exencion (falla CERRADO, no verde)",
              estado is None,
              "si un fichero ilegible concediera la exencion, romperlo seria "
              "la via barata para poner la suite en verde")

        estado, _ = suelo.exencion(Path(tmp) / "no-existe.json",
                                   maquina="la-maquina", hoy=hoy)
        check("8b. fichero ausente -> sin exencion", estado is None)

    # --- 9. El fichero REAL del repo es valido y sus fechas se sostienen ---
    real = suelo.EXENCIONES
    check("9. existe el fichero de exenciones del repo", real.is_file(),
          f"{real} no esta: el mecanismo no tiene donde declararse")
    if real.is_file():
        try:
            datos = json.loads(real.read_text(encoding="utf-8"))
            ok_json = isinstance(datos, dict)
        except ValueError as exc:
            datos, ok_json = {}, False
            print(f"          JSON invalido: {exc}")
        check("9b. y es JSON valido", ok_json)

        maquinas = {k: v for k, v in datos.items()
                    if not k.startswith("_") and isinstance(v, dict)}
        caducadas = []
        for nombre in maquinas:
            estado, det = suelo.exencion(real, maquina=nombre, hoy=date.today())
            if estado != "vigente":
                caducadas.append(f"{nombre}: {estado} ({det})")
        # Esto es el despertador: el dia que una exencion del repo caduque,
        # la suite se pone roja AQUI, en la maquina de quien la declaro, y no
        # solo en la maquina exenta —que quiza nadie mire ese dia—.
        check("9c. ninguna exencion declarada en el repo esta caducada",
              not caducadas,
              "CADUCADAS: " + " | ".join(caducadas) + "\n          "
              "Toca decidir (instalar el suelo alli, subirlo, o renovar con "
              "motivo), no borrar este arnes.")
        check("9d. toda exencion del repo declara motivo y fecha",
              all(str(v.get("motivo", "")).strip() and str(v.get("hasta", "")).strip()
                  for v in maquinas.values()),
              "una exencion sin motivo escrito no se puede revisar despues")

    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
