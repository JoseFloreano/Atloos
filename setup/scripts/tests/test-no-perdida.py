#!/usr/bin/env python3
"""
test-no-perdida.py — Muta `no-perdida.py` y exige que muerda, y que NO muerda.

Las dos mitades importan lo mismo, y la segunda es la que faltó en los dos
métodos descartados. Un comparador que canta pérdida siempre —el línea a línea
dio **21 falsos positivos**, el de 6-gramas **160**— no distingue una extracción
correcta de un borrado, así que no sirve para decidir nada: se desactiva a la
segunda vez que grita en falso, y entonces no protege del caso que motivó todo.
Por eso aquí hay tantos casos VERDES obligatorios como rojos.

Los cinco casos, y qué defecto caza cada uno:

  1. **Normalizador** — acentos, longitud y vacías. Si esto se desalinea, todos
     los demás casos miden otra cosa sin decirlo.
  2. **Borrado sin destino** (ROJO) — el fallo del sprint 4, literal: un párrafo
     desaparece del cuerpo y no aparece en ninguna `references/`. Es la mutación
     que el criterio de aceptación del sprint 5 exige, y `main()` debe devolver
     **exit 1**.
  3. **Extracción correcta** (VERDE) — el MISMO párrafo, movido verbatim al
     destino. Cero hallazgos **por construcción**: mover no cambia el
     multiconjunto. Sin este caso, el 2 no prueba nada — un comparador que
     siempre dice rojo también lo pasaría.
  4. **Reformulación conservadora** (VERDE) — mismas palabras, otro orden, otros
     cortes de línea, otra puntuación. Es exactamente lo que hundió a los otros
     dos métodos, y aquí tiene que salir en cero.
  5. **Una sola palabra borrada** (ROJO, y NOMBRADA) — el borrado pequeño dentro
     de un párrafo que por lo demás sobrevive. No basta con que salte: tiene que
     decir QUÉ palabra, porque el criterio de aceptación es justificarlas una a
     una y para eso hay que poder mirarlas.
  6. **Una `references/` destripada** (ROJO) — el cuerpo intacto y el destino
     vaciado. **Es el agujero real que tuvo la primera versión**, encontrado a
     las horas de nacer: como el ANTES era solo el SKILL.md, lo que ya vivía en
     un reference no tenía antes del que desaparecer, y 85 líneas → 3 salían en
     exit 0. La destrucción puede pasar en cualquiera de los dos lados.
  7. **Un párrafo escondido en la `description`** (ROJO) — el destino tiene que
     ser un sitio donde alguien lo vaya a leer. El frontmatter es el disparador,
     no un almacén; contarlo lo convertía en escondite legítimo.

Se ejercen las funciones REALES importadas del script, no una reimplementación:
un check verificado contra su propia copia no está verificado, está duplicado.

Uso:  setup/scripts/py setup/scripts/tests/test-no-perdida.py
Salidas: 0 los cinco casos como se espera · 1 alguno falló.
"""
import contextlib
import importlib.util
import io
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPTS = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("no_perdida", SCRIPTS / "no-perdida.py")
NP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NP)

# El párrafo que se mueve o se borra según el caso. Lleva acentos, una palabra
# repetida y una que solo aparece aquí, para que los tres filtros se ejerzan.
PARRAFO = (
    "El coordinador verifica el artefacto y no el reporte: hashes, worktree\n"
    "limpio y el destino de cada rama ejecutado al cerrar su frente. La\n"
    "verificación adversarial encontró contradicciones que ninguna revisión\n"
    "por tarea podía ver.\n")

CUERPO = (
    "---\nname: laboratorio\ndescription: da igual, el frontmatter no se mide\n---\n\n"
    "# Laboratorio\n\n"
    "Este cuerpo existe para que el comparador tenga algo estable alrededor\n"
    "de la mutación. Habla de despachos, de frentes y de presupuestos.\n\n"
    + PARRAFO +
    "\nY una cola que tampoco cambia nunca, con su tabla y su comando\n"
    "`setup/scripts/py setup/scripts/run-tests.py`, para que la puntuación intervenga.\n")


def escribe(carpeta, nombre, texto):
    p = Path(carpeta) / nombre
    p.write_text(texto, encoding="utf-8", newline="\n")
    return str(p)


def corre(antes, despues):
    """(exit, salida) de `main()` — el contrato que ve quien lo invoca."""
    return corre_multi([antes], despues)


def corre_multi(antes, despues):
    """Igual, con VARIOS ficheros en el antes: el conjunto entero contra el entero."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        codigo = NP.main(["--antes"] + antes + ["--despues"] + despues)
    return codigo, buf.getvalue()


def caso_normalizador():
    # `red` tiene 3 caracteres y SE QUEDA: el filtro descarta <=2, no <=3. Está
    # en el caso a propósito, porque exigir que desaparezca sería calibrar el
    # umbral desde el test —y entonces el test dejaría de medirlo.
    v = NP.normaliza("Extracción, EXTRACCION y la extraccíon —de la— red.")
    if v != ["extraccion", "extraccion", "extraccion", "red"]:
        return (f"acentos, mayúsculas o el filtro de <=2 caracteres no hacen lo "
                f"que dicen: {v}")
    if NP.normaliza("que con para del una") != []:
        return f"una vacía de la lista sobrevive al filtro: {NP.normaliza('que con para del una')}"
    if NP.normaliza("# ## `código` — (paréntesis)") != ["codigo", "parentesis"]:
        return (f"la puntuación de markdown no separa limpiamente: "
                f"{NP.normaliza('# ## `código` — (paréntesis)')}")
    return None


def main():
    print("No-pérdida — mutación del comparador\n")
    fallos = []

    motivo = caso_normalizador()
    print(f"  [1] normalizador                      "
          f"{'OK' if not motivo else 'FALLIDO — ' + motivo}")
    if motivo:
        fallos.append("1")

    with tempfile.TemporaryDirectory() as tmp:
        antes = escribe(tmp, "antes.md", CUERPO)
        sin_parrafo = CUERPO.replace(PARRAFO, "")

        # 2 · borrado sin destino → ROJO
        borrado = escribe(tmp, "borrado.md", sin_parrafo)
        codigo, salida = corre(antes, [borrado])
        ok2 = codigo == 1 and "contradicciones" in salida
        print(f"  [2] párrafo borrado sin destino       "
              f"{'OK — exit 1' if ok2 else f'FALLIDO — exit {codigo}'}")
        if not ok2:
            fallos.append("2")
            print(f"      un párrafo del cuerpo desaparece sin destino y el\n"
                  f"      comparador no lo canta: es el fallo del sprint 4 otra vez")

        # 3 · el MISMO párrafo movido a references/ → VERDE
        refs = escribe(tmp, "referencia.md", "# Extraído\n\n" + PARRAFO)
        codigo, salida = corre(antes, [borrado, refs])
        ok3 = codigo == 0
        print(f"  [3] el mismo párrafo, movido a un destino "
              f"{'OK — exit 0' if ok3 else f'FALLIDO — exit {codigo}'}")
        if not ok3:
            fallos.append("3")
            print(f"      una extracción CORRECTA produce hallazgo: el comparador\n"
                  f"      mide posición y no contenido, que es lo que hundió al\n"
                  f"      método de 6-gramas (160 falsos positivos)\n{salida}")

        # 4 · reformulación conservadora → VERDE
        reflow = CUERPO.replace(PARRAFO, (
            "La verificación adversarial encontró contradicciones; ninguna "
            "revisión por tarea podía ver. El coordinador verifica el artefacto, "
            "no el reporte — hashes; worktree limpio; y el destino de cada rama "
            "ejecutado al cerrar su frente.\n"))
        codigo, salida = corre(antes, [escribe(tmp, "reflow.md", reflow)])
        ok4 = codigo == 0
        print(f"  [4] reformulado: mismas palabras, otro orden "
              f"{'OK — exit 0' if ok4 else f'FALLIDO — exit {codigo}'}")
        if not ok4:
            fallos.append("4")
            print(f"      reordenar y repuntuar produce hallazgo: son los 21\n"
                  f"      falsos positivos del comparador línea a línea\n{salida}")

        # 5 · una sola palabra, y tiene que decir CUÁL
        una = CUERPO.replace("contradicciones", "cosas")
        codigo, salida = corre(antes, [escribe(tmp, "una.md", una)])
        ok5 = codigo == 1 and "`contradicciones`" in salida and salida.count("· `") == 1
        print(f"  [5] una sola palabra de contenido borrada "
              f"{'OK — exit 1, y la nombra' if ok5 else f'FALLIDO — exit {codigo}'}")
        if not ok5:
            fallos.append("5")
            print(f"      el hallazgo tiene que NOMBRAR la palabra: el criterio\n"
                  f"      es justificarlas una por una, y para eso hay que verlas\n{salida}")

        # 6 · una `references/` destripada, con el cuerpo INTACTO.
        # El párrafo ya vivía en el destino (extracción de ayer, el caso 3 ya
        # cerrado), y hoy alguien vacía el destino sin tocar el cuerpo. Si el
        # ANTES no incluyera el reference, este caso saldría verde — que es
        # literalmente lo que pasaba.
        ref_vacia = escribe(tmp, "ref-vacia.md", "# Extraído\n")
        codigo, salida = corre_multi([borrado, refs], [borrado, ref_vacia])
        ok6 = codigo == 1 and "contradicciones" in salida
        print(f"  [6] una `references/` destripada, cuerpo intacto "
              f"{'OK — exit 1' if ok6 else f'FALLIDO — exit {codigo}'}")
        if not ok6:
            fallos.append("6")
            print(f"      el cuerpo no cambia y el destino se vacía, y el\n"
                  f"      comparador no lo ve: es el agujero de la v1, donde el\n"
                  f"      ANTES era solo el SKILL.md\n{salida}")

        # 7 · el párrafo escondido en la `description`
        escondido = (
            "---\nname: laboratorio\ndescription: da igual, el frontmatter no se mide "
            + PARRAFO.replace("\n", " ") +
            "\n---\n\n# Laboratorio\n\n"
            "Este cuerpo existe para que el comparador tenga algo estable alrededor\n"
            "de la mutación. Habla de despachos, de frentes y de presupuestos.\n\n"
            "\nY una cola que tampoco cambia nunca, con su tabla y su comando\n"
            "`setup/scripts/py setup/scripts/run-tests.py`, para que la puntuación intervenga.\n")
        codigo, salida = corre(antes, [escribe(tmp, "escondido.md", escondido)])
        ok7 = codigo == 1 and "contradicciones" in salida
        print(f"  [7] el párrafo escondido en la `description` "
              f"{'OK — exit 1' if ok7 else f'FALLIDO — exit {codigo}'}")
        if not ok7:
            fallos.append("7")
            print(f"      el frontmatter cuenta como destino: la `description`\n"
                  f"      es el disparador, no un almacén\n{salida}")

    if fallos:
        print(f"\n{len(fallos)} caso(s) fallidos ({', '.join(fallos)}). El "
              f"comparador no está midiendo lo que dice.")
        return 1
    print("\n  7/7. Muerde el borrado —del cuerpo, de un destino y del que se\n"
          "  esconde en el frontmatter—, no muerde la extracción ni el reflow, y\n"
          "  nombra la palabra que falta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
