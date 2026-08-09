#!/usr/bin/env python3
"""
test-claude-md-drift.py — Caza copias declaradas "sincronizadas" que divergen.

Por qué existe (2026-08-09): la auditoría externa del W3 (H3) encontró que el
`CLAUDE.md` de `Atloos` **no llevaba la línea determinista del merge-gate**. La
llevaba su fuente (`memory-snippet.md`) y la copia hermana; no la llevaba el
proyecto en cuyo `main` caen los merges. La capa 1 de las tres —la única que la
prueba del 08-08 midió como imbatible, porque no compite en ningún concurso de
descripciones— estaba ausente justo donde hacía falta.

**La enfermedad**: un contenido con DOS puntos de consumo, donde editar uno no
obliga a editar el otro. La copia desplegada se queda atrás y nada lo delata,
porque no hay diff que mirar: son ficheros distintos con formas distintas.

Está medida tres veces, no es hipotética:
  · `memory-instructions.md` volvió a la v1 en un pull — **3 divergencias**
    documentadas en su propia cabecera (la última, 2026-07-26).
  · el `CLAUDE.md` de este repo, atrasado varias versiones (H3, 2026-08-09).
  · la copia instalada de `merge-gate-guard.py` en `~/.claude/hooks/`, que
    siguió ejecutando el parser roto tras arreglarlo en el repo (2026-08-09).

**Por qué un arnés y no una nota**: las tres veces la regla estaba escrita —la
cabecera de los dos ficheros dice "editar ambas a la vez"— y las tres veces se
incumplió. Es la tesis del RFD 11: la convención escrita no muerde.

Uso:  py setup/scripts/tests/test-claude-md-drift.py [otro/CLAUDE.md ...]
      Sin argumentos comprueba el `CLAUDE.md` de este repo. Los `CLAUDE.md` de
      otros proyectos viven fuera; pásalos por ruta para auditarlos también.
Salidas: 0 sin deriva · 1 hay deriva
"""
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SETUP = Path(__file__).resolve().parents[2]              # setup/
REPO = SETUP.parent
SNIPPET = SETUP / "skills" / "claude-code" / "project-onboard" / "references" / "memory-snippet.md"
GEMELO = SETUP / "memory-instructions.md"

hallazgos = []


def cuerpo(texto):
    """Quita los comentarios HTML de cabecera: son instrucciones, no contenido."""
    return re.sub(r"(?s)<!--.*?-->", "", texto).strip()


def norma(linea):
    """Normaliza para comparar: espacios colapsados, sin anotaciones de plantilla."""
    linea = re.sub(r"←.*$", "", linea)                   # "← reemplazar al copiar"
    return re.sub(r"\s+", " ", linea).strip()


def lineas_utiles(texto):
    return [n for n in (norma(l) for l in cuerpo(texto).splitlines()) if n]


def check_gemelos():
    """Las dos copias que se declaran sincronizadas deben tener el MISMO cuerpo."""
    if not (SNIPPET.is_file() and GEMELO.is_file()):
        hallazgos.append(f"falta uno de los gemelos: {SNIPPET.name} / {GEMELO.name}")
        return
    a = lineas_utiles(SNIPPET.read_text(encoding="utf-8"))
    b = lineas_utiles(GEMELO.read_text(encoding="utf-8"))
    solo_a = [l for l in a if l not in b]
    solo_b = [l for l in b if l not in a]
    if solo_a or solo_b:
        hallazgos.append(
            f"{SNIPPET.name} y {GEMELO.name} se declaran copias sincronizadas "
            f"pero divergen: {len(solo_a)} línea(s) solo en el primero, "
            f"{len(solo_b)} solo en el segundo")
        for l in (solo_a + solo_b)[:5]:
            hallazgos.append(f"    · {l[:96]}")


def check_desplegado(ruta):
    """Todo lo que dice el snippet debe estar en el CLAUDE.md desplegado."""
    if not ruta.is_file():
        hallazgos.append(f"no existe: {ruta}")
        return
    texto = ruta.read_text(encoding="utf-8")
    m = re.search(r"##\s*Active Project:\s*`([^`]+)`", texto)
    if not m:
        hallazgos.append(f"{ruta}: sin `## Active Project:` — no se puede "
                         f"resolver <project-name> para comparar")
        return
    proyecto = m.group(1)

    esperado = lineas_utiles(
        SNIPPET.read_text(encoding="utf-8").replace("<project-name>", proyecto))
    presentes = set(lineas_utiles(texto))
    faltan = [l for l in esperado if l not in presentes]
    if faltan:
        hallazgos.append(f"{ruta.name} ({proyecto}) va ATRÁS de {SNIPPET.name}: "
                         f"le faltan {len(faltan)} de {len(esperado)} líneas")
        for l in faltan:
            hallazgos.append(f"    · {l[:96]}")


def main():
    print("Deriva entre fuente y copias desplegadas\n")
    check_gemelos()
    objetivos = [Path(a).resolve() for a in sys.argv[1:]] or [REPO / "CLAUDE.md"]
    for ruta in objetivos:
        check_desplegado(ruta)

    if not hallazgos:
        print(f"  [OK] los gemelos coinciden y {len(objetivos)} CLAUDE.md al día")
        return 0
    for h in hallazgos:
        print(f"  {'' if h.startswith('    ') else '[DERIVA] '}{h}")
    print(f"\n{len(hallazgos)} línea(s) de hallazgo — la copia desplegada manda "
          f"en la sesión real, así que esto NO es cosmético")
    return 1


if __name__ == "__main__":
    sys.exit(main())
