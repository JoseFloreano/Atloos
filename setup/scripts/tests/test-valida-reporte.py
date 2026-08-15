#!/usr/bin/env python3
"""
test-valida-reporte.py — Arnés de `feedback/_herramientas/valida-reporte.py`.

⚠ EL VALIDADOR NO TENÍA ARNÉS. El encargo daba por hecho que sí («el validador
tiene arnés propio; esto entra ahí») y no existía: `grep -rl valida-reporte
--include=*.py` devolvía solo el propio fichero. Llevaba desde el 2026-08-11
siendo la única compuerta del canal de feedback **sin nada que la vigilara**, y
en el sprint 5 se le encontró un hueco real —la sección 9 no veía un marcador
HTML-escapado— que nadie habría cazado sin mirarlo a mano.

POR QUÉ VIVE EN `setup/scripts/tests/` Y NO EN `feedback/`. Porque
`run-tests.py` descubre por el glob `setup/**/tests/test-*.py`, y **un arnés
fuera de ese glob no corre**: no entra en el 16/16, no lo mira el gate de merge
y por tanto no muerde. Un arnés que no corre es documentación con `assert`.

QUÉ MIDE, y las dos mitades importan lo mismo:

  1. **4b vacía o de plantilla BLOQUEA.** Mismo criterio que la sección 9,
     porque es el mismo modo de fallo: la mitad que se queda sin escribir si no
     se le exige.
  2. **4b sin marca `[R]`/`[AR]`/`[H]` BLOQUEA.** Una confesión sin marca es una
     opinión.
  3. **Un v1 completo PASA y el mismo declarando v2 BLOQUEA**, nombrando lo que
     le falta. Es la prueba de que la versión hace algo: sin el caso verde, un
     validador que bloqueara siempre también pasaría el rojo.
  4. **Fecha de hoy con `formato: 1` BLOQUEA.** La versión existe para archivar
     la historia, no para escribir nuevo con el contrato viejo.
  5. **`_EJEMPLO.md` en verde.** El canario de siempre: un validador que grita
     en falso se desactiva a las dos semanas, y entonces no valida nada.

Y uno más que no estaba en el encargo y salió al construirlo (caso 6): **la
plantilla SIN RELLENAR no puede pasar el check de la 4b**. En la primera versión
pasaba, porque su prosa de guía contaba como contenido — el check habría nacido
decorativo, que es el defecto que este repo lleva tres sprints cazando. Por eso
esa guía va entre `>` en `_PLANTILLA.md`, y por eso esto es un caso y no un
comentario.

Uso:  py setup/scripts/tests/test-valida-reporte.py
Salidas: 0 los seis casos como se espera · 1 alguno falló.
"""
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[3]
VALIDADOR = REPO / "feedback" / "_herramientas" / "valida-reporte.py"
EJEMPLO = REPO / "feedback" / "_EJEMPLO.md"
PLANTILLA = REPO / "feedback" / "_PLANTILLA.md"

_spec = importlib.util.spec_from_file_location("valida_reporte", VALIDADOR)
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

# Un reporte v1 COMPLETO: exactamente lo que un reporte del 08-10 traía. Sin
# `setup_sha`, sin `coste_medido`, sin `skills_existentes_que_no_dispararon`,
# sin `formato`, y con la sección 4 de una pieza. Su sección 9 SÍ está
# confirmada, porque eso no depende de la versión y tiene que seguir exigiéndose.
V1 = """---
tipo: feedback
fecha: 2026-08-10
reporter: laboratorio
maquina: laboratorio
so: Windows 11
superficie: claude-code
claude_code: 2.1.226
tarea: Un caso de laboratorio para el arnés del validador
veredicto: sirvio-con-fricciones
skills_disparadas: [session-close]
hooks_disparados: [check-vault-updated]
graphify: no-usado
bloqueantes: 0
---

# Feedback — caso de laboratorio

## 1. Qué se intentó

[H] Probar el validador.

## 2. Evidencia de máquina

[R] Salida literal pegada aquí.

## 3. Qué funcionó

- [R] La compuerta bloqueó cuando tenía que bloquear.

## 4. Qué NO funcionó
{seccion4}

## 5. Triggers

ninguno

## 6. Graphify

- [R] No instalado en este repo de laboratorio.

## 7. Fricciones menores

- [AR] Ninguna digna de mención.

## 8. Lo que esperaba y no existe

- [H] Nada.

## 9. Confirmación del humano

- [H] Leído y corregido por: floreano · 2026-08-10
- [H] Cambios que pedí sobre el borrador del agente: corrigió el foco de la
  sección 4, que hablaba del agente y no del setup, y quitó dos adjetivos.
"""

CUATRO_V1 = """
- [H] El gate tardó más de lo que esperaba y no dijo por qué.
"""

CUATRO_V2 = """
### 4a · El setup

- [H] El gate tardó más de lo que esperaba y no dijo por qué.

### 4b · Yo, el agente

- [AR] Corrí el comando equivocado dos veces antes de leer el mensaje de error
  entero, que decía exactamente qué faltaba desde la primera vez.
"""

CLAVES_V2_EN_FRONT = ("formato: 2\nsetup_sha: fd71659\n"
                      "skills_existentes_que_no_dispararon: []\ncoste_medido: si\n")


def escribe(carpeta, nombre, texto):
    p = Path(carpeta) / nombre
    p.write_text(texto, encoding="utf-8", newline="\n")
    return p


def valida(p):
    """(fallos, version). Se ejerce la función REAL, no una reimplementación."""
    fallos, _avisos, version = V.valida(p)
    return fallos, version


def main():
    print("Validador de reportes — sección 4b y versión del contrato\n")
    fallos_globales = []

    def caso(n, titulo, ok, detalle=""):
        print(f"  [{n}] {titulo:<44}{'OK' if ok else 'FALLIDO'}")
        if not ok:
            fallos_globales.append(str(n))
            for l in str(detalle).splitlines():
                print(f"      · {l}")

    with tempfile.TemporaryDirectory() as tmp:
        # 3 · un v1 completo PASA; el MISMO con formato: 2 bloquea
        p1 = escribe(tmp, "2026-08-10-laboratorio-caso.md",
                     V1.format(seccion4=CUATRO_V1))
        f1, v1 = valida(p1)
        caso(3, "v1 completo pasa, y se reporta como v1", not f1 and v1 == 1,
             f"version={v1} fallos={f1}")

        p2 = escribe(tmp, "2026-08-10-laboratorio-caso2.md",
                     V1.replace("tipo: feedback", CLAVES_V2_EN_FRONT + "tipo: feedback")
                       .replace("formato: 2\n", "formato: 2\n", 1)
                       .format(seccion4=CUATRO_V1))
        f2, v2 = valida(p2)
        # Le sobra el frontmatter de v2 pero le falta la sección 4 partida.
        nombra = any("4a" in x or "4b" in x for x in f2)
        caso(3, "el MISMO, declarando v2, bloquea y nombra 4a/4b",
             bool(f2) and v2 == 2 and nombra, f"version={v2} fallos={f2}")

        # …y con la sección 4 partida, el v2 completo pasa: sin este verde, el
        # rojo de arriba no distingue "falta 4a/4b" de "v2 bloquea siempre".
        p3 = escribe(tmp, "2026-08-10-laboratorio-caso3.md",
                     V1.replace("tipo: feedback", CLAVES_V2_EN_FRONT + "tipo: feedback")
                       .format(seccion4=CUATRO_V2))
        f3, v3 = valida(p3)
        caso(3, "v2 completo (con 4a/4b) pasa", not f3 and v3 == 2,
             f"version={v3} fallos={f3}")

        # 1 · 4b vacía o de plantilla
        p4 = escribe(tmp, "2026-08-10-laboratorio-caso4.md",
                     V1.replace("tipo: feedback", CLAVES_V2_EN_FRONT + "tipo: feedback")
                       .format(seccion4=CUATRO_V2.replace(
                           "- [AR] Corrí el comando equivocado dos veces antes de leer el mensaje de error\n"
                           "  entero, que decía exactamente qué faltaba desde la primera vez.\n",
                           "- [AR] …\n")))
        f4, _ = valida(p4)
        caso(1, "4b sin rellenar bloquea",
             any("4b" in x and "caracteres útiles" in x for x in f4), f4)

        p5 = escribe(tmp, "2026-08-10-laboratorio-caso5.md",
                     V1.replace("tipo: feedback", CLAVES_V2_EN_FRONT + "tipo: feedback")
                       .format(seccion4=CUATRO_V2.replace(
                           "- [AR] Corrí", "- [AR] <pendiente de repasar> Corrí")))
        f5, _ = valida(p5)
        caso(1, "4b con marca de plantilla bloquea",
             any("4b" in x and "plantilla" in x for x in f5), f5)

        # 2 · 4b sin marca
        p6 = escribe(tmp, "2026-08-10-laboratorio-caso6.md",
                     V1.replace("tipo: feedback", CLAVES_V2_EN_FRONT + "tipo: feedback")
                       .format(seccion4=CUATRO_V2.replace("- [AR] Corrí", "- Corrí")))
        f6, _ = valida(p6)
        caso(2, "4b sin marca [R]/[AR]/[H] bloquea",
             any("4b" in x and "marca" in x for x in f6), f6)

        # 4 · la puerta trasera cerrada
        p7 = escribe(tmp, "2026-08-20-laboratorio-caso7.md",
                     V1.replace("fecha: 2026-08-10", "fecha: 2026-08-20")
                       .replace("tipo: feedback", "formato: 1\ntipo: feedback")
                       .format(seccion4=CUATRO_V1))
        f7, v7 = valida(p7)
        caso(4, "fecha posterior + formato: 1 → se exige v2",
             v7 == 2 and any("no para escribir" in x for x in f7),
             f"version={v7} fallos={f7}")

        # …y el reverso: la MISMA fecha con formato: 2 y todo puesto, pasa.
        p8 = escribe(tmp, "2026-08-20-laboratorio-caso8.md",
                     V1.replace("fecha: 2026-08-10", "fecha: 2026-08-20")
                       .replace("tipo: feedback", CLAVES_V2_EN_FRONT + "tipo: feedback")
                       .format(seccion4=CUATRO_V2))
        f8, v8 = valida(p8)
        caso(4, "misma fecha con v2 completo pasa", not f8 and v8 == 2,
             f"version={v8} fallos={f8}")

    # 5 · el canario
    f9, v9 = valida(EJEMPLO)
    caso(5, "_EJEMPLO.md sigue en verde", not f9, f"version={v9} fallos={f9}")

    # 6 · el que no estaba en el encargo: la plantilla no puede pasar la 4b
    texto = PLANTILLA.read_text(encoding="utf-8").replace("\r", "")
    cuerpo = texto[texto.find("\n---\n", 4) + 5:]
    caso(6, "la PLANTILLA sin rellenar NO pasa el check de 4b",
         bool(V.revisa_4b(cuerpo)),
         "la guía de la 4b cuenta como contenido: el check nace decorativo")

    if fallos_globales:
        print(f"\n{len(set(fallos_globales))} caso(s) fallidos "
              f"({', '.join(sorted(set(fallos_globales)))}).")
        return 1
    print("\n  Los seis casos. La 4b se exige de verdad, la versión clasifica sin\n"
          "  abrir puertas, y el canario sigue verde.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
