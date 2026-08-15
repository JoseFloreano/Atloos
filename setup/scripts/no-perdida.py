#!/usr/bin/env python3
"""
no-perdida.py — ¿lo que salió de un sitio llegó a otro? Mide EXTRACCIÓN, no tamaño.

POR QUÉ EXISTE (sprint 4, 2026-08-14). Un frente mecánico recibió un criterio de
aceptación numérico —siete skills por debajo de 460 palabras, `description`
intacta, arnés en exit 0— y **acertó todos los números**. Su trabajo se descartó
entero: no extrajo, **comprimió y borró**. 102 líneas del cuerpo sin destino en
ninguna `references/`.

  **La lección no es «el modelo barato no sirve»: es que un criterio de
  aceptación numérico SE CUMPLE DESTRUYENDO.** Un número se cumple borrando;
  dos, no. Este script es la segunda medida.

Contrato en `setup/skills/shared/workstream-dispatch/references/no-perdida.md`.

QUÉ MÉTODO, Y POR QUÉ NO LOS OTROS DOS. Se probaron tres sobre el mismo caso
real —las 7 skills del sprint 4— y los números decidieron:

  · **línea a línea con puntuación** → **21 falsos positivos**. Reajustar dónde
    corta la línea al reflowear un párrafo no pierde nada, y el comparador lo
    cantaba como pérdida. Hubo que arreglarlo antes de poder creerle.
  · **6-gramas de palabras** → **160 «sin destino»**, casi todo ruido de junta:
    un 6-grama que cruza el punto donde se reordenó texto falla aunque las dos
    mitades sobrevivan intactas. Sensible a la costura, no al contenido.
  · **multiconjunto de palabras de contenido** → **3 palabras desaparecidas de
    1550**. Es el que decide, y es el que está implementado aquí.

La razón es estructural, no de calibración: **mover texto no cambia el
multiconjunto**. Los otros dos miden posición, y la posición es justo lo que una
extracción legítima cambia a propósito.

CERO NO ES EL CRITERIO DE ACEPTACIÓN, y confundirlo volvería a producir el fallo
que este script persigue. Reformular cambia palabras: quien exija cero acabará
prohibiendo reescribir, o —peor— maquillando la reescritura para que el número
salga. **El criterio es que cada desaparecida se JUSTIFIQUE, una por una**, y por
eso cada hallazgo se imprime con la frase de la que salió: para poder mirarla.

  En el sprint 4 las tres desaparecidas —`contradicciones`, `probaron`,
  `reescriben`— resultaron ser ideas que **sobrevivieron con mejor redacción y
  más evidencia**. Ese es el resultado bueno, y solo se ve mirándolas.

Por eso el exit 1 significa **«hay que mirar N palabras»**, no «está mal». Quien
lo llame decide si las justifica; lo que no puede es no verlas.

Uso:
  py setup/scripts/no-perdida.py <dir-de-skill> [--base <rev>]
      ANTES = el SKILL.md en <rev> (default HEAD); DESPUÉS = el SKILL.md de
      disco MÁS todas sus `references/*.md`.

  py setup/scripts/no-perdida.py --antes <fichero> --despues <fichero>...
      Sin git. Es el modo que ejerce el arnés, y el que sirve para comparar
      cualquier par de árboles (un worktree contra otro, por ejemplo).

Salidas: 0 ninguna palabra desaparece · 1 hay N que justificar · 2 error de uso.
"""
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Lista CORTA y cerrada a propósito. Cada palabra que se añade aquí es una
# pérdida que el script deja de poder ver, así que la duda se resuelve DEJÁNDOLA
# FUERA: un falso positivo cuesta una mirada, un falso negativo cuesta el
# hallazgo entero. Las de 1-2 caracteres (de, la, el, en, se, un, lo, al, es,
# su, no, si, y, a) no están porque ya las descarta el filtro de longitud.
VACIAS = {
    "los", "las", "que", "con", "por", "para", "del", "una", "uno", "unas",
    "unos", "como", "mas", "pero", "sus", "sin", "este", "esta", "esto",
    "estos", "estas", "ese", "esa", "eso", "esos", "esas", "son", "ser",
    "era", "han", "hay", "fue", "the", "and", "for",
}

MIN_LARGO = 2           # se descarta lo de longitud <= 2


def normaliza(texto):
    """El texto como multiconjunto de palabras de contenido.

    Cuatro pasos y cada uno quita una forma de falso positivo:
      1. minúsculas — «Extracción» y «extracción» son la misma palabra;
      2. sin acentos (NFKD + descarte de combinantes) — un `.md` reescrito en
         otra máquina puede traer la tilde compuesta o descompuesta, y eso no es
         una pérdida de contenido;
      3. lo que no es alfanumérico separa — así la puntuación, los backticks y
         los guiones de markdown dejan de contar como cambio;
      4. fuera lo de <=2 caracteres y las vacías, que aparecen y desaparecen con
         cualquier reescritura y ahogarían la señal.

    Devuelve una LISTA (no un set): el multiconjunto conserva las repeticiones,
    y perder 3 de 4 apariciones de una palabra es un dato distinto de perderlas
    todas — aunque solo lo segundo sea hallazgo.
    """
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return [p for p in re.findall(r"[a-z0-9]+", texto)
            if len(p) > MIN_LARGO and p not in VACIAS]


def cuerpo(texto):
    """El .md sin frontmatter y sin CR.

    El frontmatter se quita porque no es contenido que se extraiga: la
    `description` es el disparador y vive donde vive. Medirla aquí haría que
    reescribir un trigger apareciera como pérdida de cuerpo, que es otra cosa
    y se mide con `test-skill-catalog.py`.
    """
    texto = texto.replace("\r", "")
    if texto.startswith("---"):
        fin = texto.find("\n---", 3)
        if fin != -1:
            texto = texto[fin + 4:]
    return texto


def frases(texto):
    """El texto partido en unidades legibles, para poder citar el contexto.

    Se corta por final de frase Y por salto de línea: en markdown media línea
    de una tabla o un bullet no termina en punto, y una «frase» de 40 líneas no
    sirve para mirar nada.
    """
    trozos = []
    for linea in cuerpo(texto).splitlines():
        for t in re.split(r"(?<=[.!?:;])\s+", linea.strip()):
            if t.strip():
                trozos.append(t.strip())
    return trozos


def desaparecidas(antes, despues):
    """[(palabra, veces_antes, frase)] de lo que estaba y ya no está en ninguna parte.

    «En ninguna parte» es la clave y es lo que hace legítimo el método: `despues`
    es la suma del cuerpo nuevo MÁS todos sus destinos. Mover un párrafo del
    cuerpo a `references/` no mueve el multiconjunto ni una unidad, así que la
    extracción correcta sale en cero por construcción — no por calibración.
    """
    ca, cd = Counter(normaliza(antes)), Counter(normaliza(despues))
    perdidas = sorted(p for p in ca if cd[p] == 0)
    if not perdidas:
        return []
    indice = {}
    for f in frases(antes):
        for p in set(normaliza(f)):
            indice.setdefault(p, f)
    return [(p, ca[p], indice.get(p, "(sin frase: la palabra no está en el cuerpo)"))
            for p in perdidas]


def texto_en_rev(repo, rel, rev):
    """El fichero tal como estaba en `rev`. None si no existía."""
    p = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=repo,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace")


def raiz_git(desde):
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=desde,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
    return p.stdout.decode("utf-8", "replace").strip() if p.returncode == 0 else None


def lee(rutas):
    return "\n".join(Path(r).read_text(encoding="utf-8") for r in rutas)


def informa(hallazgos, etiqueta, n_antes):
    print(f"No-pérdida — {etiqueta}")
    print(f"  {n_antes} palabras de contenido en el ANTES "
          f"(sin vacías, sin las de <={MIN_LARGO} caracteres)\n")
    if not hallazgos:
        print("  [OK] ninguna palabra de contenido desaparece. Lo que salió del\n"
              "       cuerpo está en algún destino: es extracción, no borrado.")
        return 0
    print(f"  {len(hallazgos)} palabra(s) que ya no están EN NINGUNA PARTE.\n")
    for palabra, veces, frase in hallazgos:
        print(f"    · `{palabra}`  (x{veces} en el antes)")
        print(f"      {frase[:150]}")
    print(f"""
  Esto NO dice «está mal»: dice «hay {len(hallazgos)} que mirar». Reformular
  cambia palabras, y exigir cero prohibiría reescribir. El criterio es
  justificar CADA UNA, una por una, mirando su frase. Si la idea sobrevive con
  otras palabras, la desaparecida está justificada y se dice en el reporte; si
  al mirarla no está la idea, eso es el borrado que este script existe para
  cazar.""")
    return 1


def main(argv):
    if "--antes" in argv:
        i = argv.index("--antes")
        if "--despues" not in argv:
            print("--antes exige --despues", file=sys.stderr)
            return 2
        j = argv.index("--despues")
        antes_r, despues_r = argv[i + 1:j], argv[j + 1:]
        if not antes_r or not despues_r:
            print("--antes y --despues necesitan al menos un fichero cada uno",
                  file=sys.stderr)
            return 2
        antes, despues = lee(antes_r), lee(despues_r)
        etiqueta = f"{len(antes_r)} fichero(s) antes → {len(despues_r)} después"
    else:
        objetivos = [a for a in argv if not a.startswith("--")]
        if "--base" in argv:
            objetivos = [o for o in objetivos if o != argv[argv.index("--base") + 1]]
        if len(objetivos) != 1:
            print(__doc__.split("Uso:")[1], file=sys.stderr)
            return 2
        base = argv[argv.index("--base") + 1] if "--base" in argv else "HEAD"
        carpeta = Path(objetivos[0]).resolve()
        skill = carpeta / "SKILL.md" if carpeta.is_dir() else carpeta
        if not skill.is_file():
            print(f"no existe: {skill}", file=sys.stderr)
            return 2
        repo = raiz_git(skill.parent)
        if not repo:
            print(f"{skill.parent} no está en un repo git: usa --antes/--despues",
                  file=sys.stderr)
            return 2
        rel = skill.resolve().relative_to(Path(repo).resolve()).as_posix()
        antes = texto_en_rev(repo, rel, base)
        if antes is None:
            print(f"`git show {base}:{rel}` no devuelve nada: ¿fichero nuevo? "
                  f"Un fichero que no existía en {base} no puede haber perdido "
                  f"nada, así que no hay nada que medir.", file=sys.stderr)
            return 2
        refs = sorted((skill.parent / "references").glob("*.md"))
        despues = lee([skill] + refs)
        etiqueta = (f"{rel} en {base} → disco (cuerpo + {len(refs)} "
                    f"`references/`)")

    return informa(desaparecidas(antes, despues), etiqueta,
                   len(normaliza(antes)))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
