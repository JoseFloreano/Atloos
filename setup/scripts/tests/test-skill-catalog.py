#!/usr/bin/env python3
"""
test-skill-catalog.py — Caza referencias colgantes entre skills y mide la
saturación del catálogo. Hermano de `test-skill-paths.py`: aquel mira RUTAS,
este mira NOMBRES.

Por qué existe (2026-08-09): `skill-forge` mandaba usar `cowork-plugin`,
`sql-conventions` mandaba a `warehouse-query-optimize`, y DOS skills afirmaban
que "la garantía dura es el hook `validate-migration-review`" — un hook que
nunca se construyó. Una skill que afirma una garantía de máquina inexistente es
peor que una que manda a una skill ausente.

POR QUÉ ESTA ESPECIFICACIÓN Y NO LA DEL RFD 17 R2. La original —"toda skill
nombrada debe existir en setup/skills/"— se implementó y se corrió el 08-09:
**26 hallazgos, casi todos falsos** (skills de Superpowers, bundled de
Anthropic, scripts `.ps1`, hooks `.py`, un MCP y el literal `alg:none` de un
JWT). Y **no cazaba el caso que la motivó**, porque la referencia a
`cowork-plugin` iba sin backticks. Fallaba en las dos direcciones a la vez.

EL ARREGLO ES EL NAMESPACE (D6 del doc 19, opción (a)). Con prefijo obligatorio
el check deja de ser heurística y pasa a ser comprobación exacta:

  superpowers:x · bundled:x · cowork:x · mcp:x   → de otra superficie, se acepta
  x  (sin prefijo)                               → skill PROPIA: debe existir

La convención no se inventa aquí: ya se usaba en `workstream-merge-gate`.

LAS DOS EXCEPCIONES, y las dos son exactas —no listas blancas a mano, que se
desincronizan (ese es el problema del §1 del RFD 17 otra vez):

  1. **Artefactos del propio repo.** `sync-skills` es un `.ps1`, `gate-test` un
     `.py`. El inventario se lee del disco (`setup/**/*.py|ps1|sh`), así que se
     mantiene solo.
  2. **Hedge declarado y greppable** en la MISMA línea ("si está instalada"),
     igual que el `[repo]` de `test-skill-paths.py`. Ponerlo en la línea de
     arriba no basta: el check es por línea.

Y sube el listón que pidió la auditoría (A.4): no basta con que la skill
exista, tiene que existir **en la superficie donde se manda usar**. Una skill
de `shared/` se despliega en Claude Code Y en Cowork, así que solo puede
nombrar sin prefijo a otra de `shared/`. Eso es el **check 3, y es AVISO**:
hoy dispara 20 veces sobre skills maduras y convertirlo en bloqueante sería
pedir un refactor del catálogo entero, no media jornada de higiene.

LÍMITE DECLARADO, porque callarlo sería el fallo que este arnés persigue: solo
ve menciones **entre backticks**. Una referencia en prosa corrida a una skill
que no existe —como la de `skill-forge` a `cowork-plugin`, que motivó todo
esto— pasa de largo. Buscar texto plano fue justo lo que produjo los 26 falsos
positivos. La convención que cierra el hueco es humana y vive en `skill-forge`:
**toda skill nombrada dentro de otra va entre backticks y con su namespace.**
Este arnés vigila que lo marcado resuelva; que se marque, lo vigila la skill.

EL TOPE DURO MUERDE DESDE EL 2026-08-12 (auditoría 22, H7). Hasta entonces las
palabras "tope duro 500" solo existían **dentro de la cadena de texto de una
tabla markdown generada**: el único `return 1` del arnés dependía de las
referencias colgantes, así que ningún check bloqueaba por longitud —ni a 450, ni
a 475, ni a 500— mientras siete skills vivían entre 491 y 499. Era la ley 1
aplicada al propio catálogo: la convención escrita no muerde. Ahora sí.

Los dos umbrales son distintos y hacen cosas distintas:
  · 475 (`SATURACION`) → **AVISO**. Mira hacia dónde va el catálogo y dice qué
    skills ya no tienen dónde mover el detalle. No tumba el arnés.
  · 500 (`TOPE_DURO`)  → **BLOQUEA**. 500 es el último valor admisible; 501 pone
    la suite en rojo. Hoy el máximo son 499, así que nace en verde: es un alambre
    puesto antes de que alguien lo pise, no un refactor pendiente.

Uso:  py setup/scripts/tests/test-skill-catalog.py          [repo]
      py setup/scripts/tests/test-skill-catalog.py --tabla  [repo]
Salidas: 0 sin referencias colgantes y sin skills sobre el tope · 1 hay hallazgos.
"""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parents[2]        # setup/
SKILLS = RAIZ / "skills"
SATURACION = 475        # umbral de AVISO; una skill nueva nace en ≤450
TOPE_DURO = 500         # el que BLOQUEA (auditoría 22, H7). 501 pone la suite en rojo

# Superficies en las que se despliega una skill, y qué puede ver cada una.
# `shared` va a las dos, así que es la más restringida: solo ve `shared`.
VISIBLE_DESDE = {
    "shared":      {"shared"},
    "claude-code": {"shared", "claude-code"},
    "cowork":      {"shared", "cowork"},
}

# Superficies que NO podemos ver desde aquí: el prefijo se acepta sin verificar,
# porque no tenemos su árbol montado.
EXTERNOS = ("superpowers", "bundled", "mcp")

# Carpetas nuestras. `shared` y `claude-code` son enteramente nuestras, así que
# un prefijo que apunte a una skill que no está ahí es un prefijo que MIENTE, y
# eso es un hallazgo — no un silencio.
#
# `cowork` es el caso ambiguo y se acepta a propósito: nombra tanto nuestra
# carpeta `cowork/` como las skills que Cowork trae de fábrica
# (`cowork:cowork-plugin`), y desde el repo las dos son indistinguibles.
PROPIOS_VERIFICABLES = ("shared", "claude-code")
NAMESPACES = EXTERNOS + PROPIOS_VERIFICABLES + ("cowork",)

# `nombre-en-kebab` entre backticks, opcionalmente con namespace.
# Exige un guion: sin él no es un nombre de skill (y así `alg:none` —el literal
# de un JWT que la primera versión reportaba— deja de ser candidato).
REF = re.compile(r"`(?:(" + "|".join(NAMESPACES) + r"):)?([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")

# Hedge: la mención se declara opcional en su propia línea. Greppable:
#   grep -rn "si está instalad" setup/skills/
#
# También en inglés: `memory-snippet.md` se copia VERBATIM al `CLAUDE.md` de
# cualquier proyecto, así que su hedge está escrito en el idioma de ese fichero
# —"if the X MCP is unavailable, skip"—. Prefijarlo con `mcp:` lo habría metido
# en los CLAUDE.md de proyectos ajenos, donde esta convención no rige; y el
# arnés H3 lo cazó al instante, porque esa línea tiene TRES puntos de consumo.
HEDGE = re.compile(r"si (?:está|estan|están|no está)\s+(?:instalad|disponible|presente)"
                   r"|si existe|si lo tienes|opcional"
                   r"|if .{0,40}\bis (?:unavailable|not installed|missing)", re.I)


def es_comando(nombre, linea):
    """¿El token es un ejecutable, no un nombre de skill?

    `pip-audit` es una CLI, y la línea que lo menciona suelto también lo escribe
    CON argumentos: `` `pip-audit -r requirements.txt` ``. Un nombre de skill
    nunca lleva argumentos. La señal está en la propia línea, así que no hace
    falta lista blanca — que es lo que se desincroniza.
    """
    return re.search(r"`" + re.escape(nombre) + r"\s+[^`]+`", linea) is not None


def artefactos_del_repo():
    """Nombres de ficheros ejecutables/config del repo: no son skills.

    Se lee del disco a propósito. Una lista escrita a mano es un segundo
    catálogo, y un segundo catálogo se desincroniza — que es exactamente la
    enfermedad que este arnés existe para cazar.
    """
    nombres = set()
    for ext in ("*.py", "*.ps1", "*.sh", "*.json", "*.yaml", "*.yml"):
        for f in RAIZ.rglob(ext):
            if "_build" in f.parts or "__pycache__" in f.parts:
                continue
            nombres.add(f.stem)
    return nombres


def inventario_skills():
    """{nombre: superficie} de las skills reales del repo."""
    inv = {}
    for skill_md in SKILLS.rglob("SKILL.md"):
        partes = skill_md.relative_to(SKILLS).parts
        if "_build" in partes or partes[0] == "_template":
            continue
        superficie, nombre = partes[0], partes[1]
        inv.setdefault(nombre, set()).add(superficie)
    return inv


def cuerpo(texto):
    """El .md sin frontmatter y sin CR. Es la unidad que mide el tope."""
    texto = texto.replace("\r", "")
    if texto.startswith("---"):
        fin = texto.find("\n---", 3)
        if fin != -1:
            texto = texto[fin + 4:]
    return texto


def palabras_de(texto):
    """Palabras del cuerpo. Es la unidad de LOS DOS umbrales, y por eso vive
    en una sola función: medir el aviso de una forma y el bloqueo de otra sería
    el defecto que este arnés persigue, cometido dentro del propio arnés."""
    return len(cuerpo(texto).split())


def excede_tope(palabras):
    """¿Pasa del tope duro? 500 es el último valor admisible; 501 bloquea.

    Se escribe como función y no como un `>` suelto para que `autoprueba_tope()`
    pueda ejercer LA MISMA decisión que corre en producción. Un check verificado
    contra una reimplementación no está verificado: está duplicado.
    """
    return palabras > TOPE_DURO


def revisa_referencias(inv, artefactos):
    """(colgantes, fuera_de_superficie). Las primeras BLOQUEAN; las otras avisan.

    Se lee el fichero ENTERO, frontmatter incluido: la `description` es lo que
    el modelo usa para enrutar, y el caso que motivó todo esto —`skill-forge`
    mandando a `cowork-plugin`— vive justo ahí. Medir el cuerpo sin frontmatter
    (check 2) y revisarlo con él son dos cosas distintas.
    """
    colgantes, superficie_mal = [], []
    for md in sorted(SKILLS.rglob("*.md")):
        partes = md.relative_to(SKILLS).parts
        if len(partes) < 2 or "_build" in partes or partes[0] == "_template":
            continue                          # setup/skills/README.md y demás
        superficie, propia = partes[0], partes[1]
        visibles = VISIBLE_DESDE.get(superficie, {"shared"})
        rel = md.relative_to(RAIZ.parent).as_posix()

        texto = md.read_text(encoding="utf-8").replace("\r", "")
        for n, linea in enumerate(texto.splitlines(), 1):
            if HEDGE.search(linea):
                continue                      # excepción declarada en su línea
            for ns, nombre in REF.findall(linea):
                if ns in EXTERNOS or ns == "cowork":
                    continue                  # otra superficie: no la podemos ver
                if ns in PROPIOS_VERIFICABLES:
                    # El prefijo es una AFIRMACIÓN sobre nuestro propio árbol, así
                    # que se comprueba. Aceptarlo a ciegas convertiría el namespace
                    # en un silenciador: exactamente lo que el hedge ya hacía mal.
                    donde = inv.get(nombre) or set()
                    if ns not in donde:
                        vive = "/".join(sorted(donde)) if donde else "ninguna superficie"
                        colgantes.append((rel, n, "PREFIJO QUE MIENTE",
                                          f"dice `{ns}:{nombre}` pero esa skill vive "
                                          f"en {vive}", linea.strip()))
                    continue
                if nombre == propia or nombre in artefactos or es_comando(nombre, linea):
                    continue
                donde = inv.get(nombre)
                if not donde:
                    colgantes.append((rel, n, "REFERENCIA COLGANTE",
                                      f"`{nombre}` no existe en setup/skills/",
                                      linea.strip()))
                elif not (donde & visibles):
                    superficie_mal.append((rel, n, "FUERA DE SUPERFICIE",
                                           f"`{nombre}` solo vive en "
                                           f"{'/'.join(sorted(donde))}, y quien la "
                                           f"nombra se despliega en {superficie}",
                                           linea.strip()))
    return colgantes, superficie_mal


def mide_saturacion():
    filas = []
    for skill_md in sorted(SKILLS.rglob("SKILL.md")):
        partes = skill_md.relative_to(SKILLS).parts
        if "_build" in partes or partes[0] == "_template":
            continue
        palabras = palabras_de(skill_md.read_text(encoding="utf-8"))
        if palabras < SATURACION:
            continue
        refs = skill_md.parent / "references"
        n_refs = len(list(refs.glob("*.md"))) if refs.is_dir() else 0
        filas.append((f"{partes[0]}/{partes[1]}", palabras, n_refs))
    return sorted(filas, key=lambda f: -f[1])


def autoprueba_tope():
    """Mutación: fabrica el defecto y exige que el tope lo cace.

    (bool, motivo). El defecto es justo el que H7 dejó pasar durante meses: una
    skill por encima del tope duro que no tumba nada. Se ejerce la MISMA pareja
    de funciones que corre en producción —`palabras_de` y `excede_tope`—, con
    frontmatter delante para que el contador tenga que quitarlo: si mide el
    fichero entero, el borde se desplaza y el tope deja de significar lo que dice.

    Se comprueban los DOS lados del borde. Un check que solo prueba que 501
    bloquea no distingue "tope en 500" de "tope en 0": cualquier umbral más bajo
    también lo bloquearía, y la suite entera se pondría roja sin que este caso
    lo notara.
    """
    cabecera = "---\nname: laboratorio\ndescription: no existe en disco\n---\n\n"
    justo = cabecera + " ".join(["palabra"] * TOPE_DURO)
    pasada = cabecera + " ".join(["palabra"] * (TOPE_DURO + 1))

    if palabras_de(justo) != TOPE_DURO:
        return False, (f"el contador no mide el cuerpo sin frontmatter: "
                       f"{palabras_de(justo)} palabras donde hay {TOPE_DURO}")
    if excede_tope(palabras_de(justo)):
        return False, f"{TOPE_DURO} palabras exactas deberían pasar, y bloquean"
    if not excede_tope(palabras_de(pasada)):
        return False, (f"{TOPE_DURO + 1} palabras NO producen bloqueo — el tope "
                       f"duro vuelve a ser decorativo, que es H7 otra vez")
    if SATURACION > TOPE_DURO:
        # El tope se lee de las filas que `mide_saturacion` recoge, y esa función
        # filtra por SATURACION. Con el aviso por encima del bloqueo, una skill
        # sobre el tope no entraría en la lista y saldría en verde: el arnés
        # mentiría en la dirección peligrosa. Es config, no datos, así que se
        # caza aquí y no en tiempo de ejecución.
        return False, (f"SATURACION ({SATURACION}) está por encima de TOPE_DURO "
                       f"({TOPE_DURO}): las skills sobre el tope no llegarían a "
                       f"mirarse")
    return True, ""


def sello():
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             cwd=RAIZ.parent, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=10
                             ).stdout.decode().strip()
    except Exception:
        sha = ""
    return f"medido en {sha or '(sin git)'} · {date.today().isoformat()}"


def total_skills():
    return len([m for m in SKILLS.rglob("SKILL.md")
                if "_build" not in m.parts
                and m.relative_to(SKILLS).parts[0] != "_template"])


def tabla_markdown(filas, total):
    out = [f"<!-- Generada por setup/scripts/tests/test-skill-catalog.py — "
           f"no editar a mano -->",
           f"**Saturación del catálogo** — {sello()}",
           "",
           f"{len(filas)} de {total} skills en {SATURACION}+ palabras "
           f"(tope duro 500; una skill nueva nace en ≤450).",
           "",
           "| Skill | Palabras | `references/` |",
           "|---|---:|:---:|"]
    for nombre, palabras, refs in filas:
        marca = f"**{refs}**" if refs == 0 else str(refs)
        out.append(f"| `{nombre}` | {palabras} | {marca} |")
    return "\n".join(out)


def main():
    if not SKILLS.is_dir():
        print(f"No encuentro {SKILLS}")
        return 1

    inv = inventario_skills()
    filas = mide_saturacion()
    total = total_skills()

    if "--tabla" in sys.argv:
        print(tabla_markdown(filas, total))
        return 0

    hallazgos, superficie_mal = revisa_referencias(inv, artefactos_del_repo())

    print(f"Catálogo de skills — {sello()}")
    print(f"{total} skills bajo setup/skills/ "
          f"({', '.join(f'{s}: {sum(1 for d in inv.values() if s in d)}' for s in VISIBLE_DESDE)})\n")

    print("── Check 1 · referencias colgantes " + "─" * 38)
    if hallazgos:
        print(f"\n{len(hallazgos)} referencia(s) que no resuelven:\n")
        for rel, n, tipo, detalle, texto in hallazgos:
            print(f"  {tipo}: {detalle}")
            print(f"    {rel}:{n}")
            print(f"    {texto[:110]}")
        print("""
La regla: sin prefijo = skill PROPIA, y tiene que existir en setup/skills/ y
ser visible desde la superficie donde se despliega quien la nombra.

Tres arreglos legítimos, por orden de preferencia:
  1. Marca la superficie. Externas (se aceptan sin verificar, no vemos su
     árbol):  `superpowers:x` · `bundled:x` · `mcp:x` · `cowork:x`
     Nuestras (SE VERIFICAN, y un prefijo falso es hallazgo):
     `shared:x` · `claude-code:x`
  2. Declara el hedge en la MISMA línea: "usa `x` si está instalada"
     ⚠ En la MISMA línea de verdad: un "— si / está instalada" partido por el
     salto no lo ve nadie. Es el fallo que este repo ya cometió tres veces.
  3. Si no existe en ninguna superficie, la instrucción es falsa: reescríbela.
     Y si afirmaba una GARANTÍA que no hay, decir la verdad no es hedgear —
     es quitar la afirmación.""")
    else:
        print("\n  0 hallazgos: toda referencia sin prefijo resuelve a una skill\n"
              "  real y visible desde su superficie.")

    print("\n── Check 2 · saturación (aviso) y tope duro (BLOQUEA) " + "─" * 20 + "\n")
    ok_tope, motivo_tope = autoprueba_tope()
    print(f"  [AUTOPRUEBA] {'OK' if ok_tope else 'FALLIDA'} — {TOPE_DURO} "
          f"palabras pasan y {TOPE_DURO + 1} bloquean"
          + (f"\n               {motivo_tope}" if not ok_tope else ""))
    excedidas = [f for f in filas if excede_tope(f[1])]
    if excedidas:
        print(f"\n  {len(excedidas)} skill(s) POR ENCIMA del tope duro de "
              f"{TOPE_DURO} palabras:\n")
        for nombre, palabras, refs in excedidas:
            print(f"    {nombre:<34}{palabras:>9}   (+{palabras - TOPE_DURO})")
        print(f"\n  Esto SÍ tumba el arnés. El arreglo no es subir el número: es\n"
              f"  mover detalle a `references/`, que es lo que el modelo carga\n"
              f"  solo cuando lo necesita.")
    print()
    if not filas:
        print(f"  Ninguna skill llega a {SATURACION} palabras.")
    else:
        print(f"  {len(filas)} de {total} skills en {SATURACION}+ palabras. "
              f"Las que tienen 0 en `references/`\n  no tienen dónde mover el "
              f"detalle: ampliarlas empieza por crear la carpeta.\n")
        print(f"  {'Skill':<34}{'Palabras':>9}   references/")
        for nombre, palabras, refs in filas:
            aviso = "  ← sin dónde mover" if refs == 0 else ""
            print(f"  {nombre:<34}{palabras:>9}   {refs}{aviso}")
        print(f"\n  Tabla en markdown:  py {Path(__file__).name} --tabla")

    print("\n── Check 3 · superficie (aviso, no bloquea) " + "─" * 30 + "\n")
    if not superficie_mal:
        print("  Toda referencia resuelve en la superficie de quien la nombra.")
    else:
        print(f"  {len(superficie_mal)} mención(es) a skills que NO están en la\n"
              f"  superficie de quien las nombra. No bloquea —la mayoría son\n"
              f"  informativas y varias ya marcan la superficie en prosa—, pero\n"
              f"  una que MANDE usarla es la enfermedad de `notify-telegram`:\n")
        for rel, n, _t, detalle, _x in superficie_mal:
            print(f"    {rel}:{n}  →  {detalle}")

    # Tres motivos de rojo, y el tercero es el propio arnés: si su autoprueba
    # cae, lo que este fichero afirma sobre el tope deja de estar respaldado, y
    # un check no verificado en verde es exactamente el agujero de H7.
    return 1 if (hallazgos or excedidas or not ok_tope) else 0


if __name__ == "__main__":
    sys.exit(main())
