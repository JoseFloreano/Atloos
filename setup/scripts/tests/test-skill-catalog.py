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
  2. **Hedge declarado y greppable** junto a la referencia ("si está
     instalada"), igual que el `[repo]` de `test-skill-paths.py`. Desde el
     sprint 7 se busca en una VENTANA de líneas: antes el check medía por línea
     y la gente escribe cruzando líneas, así que un hedge partido por el
     plegado del markdown no lo veía nadie —cuatro veces, incluidas dos del
     auditor y una de quien escribió el aviso—. El número de la ventana y su
     porqué, en `_ventana.py`; ancharlo más sería peor que el fallo, porque
     encontraría el hedge de OTRA referencia.

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
  · 450 (`SATURACION`) → **AVISO**. Es el número que el contrato cita («una
    skill nueva nace en ≤450»), y desde el sprint 9 lo mide alguien. Dice qué
    skills ya no tienen dónde mover el detalle. No tumba el arnés.
  · 500 (`TOPE_DURO`)  → **BLOQUEA**. 500 es el último valor admisible; 501 pone
    la suite en rojo. Hoy el máximo son 499, así que nace en verde: es un alambre
    puesto antes de que alguien lo pise, no un refactor pendiente.

EL CHECK 4 MIDE UN LÍMITE DE LA PLATAFORMA, NO NUESTRO (sprint 3, S1). La
especificación de Agent Skills obliga a `description` de 1 a 1024 caracteres y
`name` de 1 a 64. **Claude Code no usa ese límite** —trunca a 1536 en el listado
y encima es configurable (`skillListingMaxDescChars`)—, así que una skill por
encima de 1024 **carga y funciona aquí** y falla solo al subirla. Eso es lo que
pasó: `requirements-designer` llegó a **1074** al ganar la fase 0 y bloqueó la
subida sin que nada de este repo lo dijera.

  **Un límite de la plataforma que el repo no mide es un límite que se descubre
  el día que bloquea.** Es la tercera vez: el tope de 500 palabras vivía dentro
  de una cadena de texto (H7), el arnés de deriva verificaba el contrato
  equivocado (sprint 2, S2), y ahora esto. El patrón no es el número — es que
  medimos lo que se nos ocurrió medir.

Se mide la description **RESUELTA**, no el texto crudo: el frontmatter usa
escalares plegados (`>`), y lo que el cargador valida es la cadena de una sola
línea, sin los saltos ni la sangría. Medir el crudo daría un número mayor que el
real y el arnés mentiría en la dirección cómoda.

EL CHECK 5 ES LA MISMA ASIMETRÍA POR TERCERA VEZ (sprint 8, S2). Un `<persona>`
en la `description` de `requirements-designer` rompía la subida —el angular se
parsea como etiqueta abierta— y **aquí no se notaba**, porque Claude Code escapa
los angulares de la `description` a propósito. Tope de 1024, escalar plano
multilínea, angulares: las tres funcionan en Code y fallan al subir, y las tres
las descubrió el bloqueo. Se mide el valor RESUELTO por la misma razón que el
check 4, y aquí es más urgente: las 39 skills abren con `description: >`, así
que un check sobre el texto crudo daría 39 hallazgos el primer día y estaría
apagado el segundo.

Va el ÚLTIMO aunque BLOQUEE, y a propósito: los números de check ya se citan
fuera de este fichero ("el check 3 bajó de 22 a 19" vive en el vault y en dos
encargos). Renumerar para colocarlo por severidad rompería ese vocabulario
compartido, que es más caro que el orden.

Uso:  py setup/scripts/tests/test-skill-catalog.py          [repo]
      py setup/scripts/tests/test-skill-catalog.py --tabla  [repo]
Salidas: 0 sin referencias colgantes y sin skills sobre el tope · 1 hay hallazgos.
"""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ventana import RADIO, autoprueba as autoprueba_ventana, marcada  # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parents[2]        # setup/
SKILLS = RAIZ / "skills"
# EL AVISO BAJA DE 475 A 450 (sprint 9, S4b). El 475 no lo citaba nadie: el
# número que este repo usa de verdad es **450** —«una skill nueva nace en ≤450»
# lo dice `skill-forge`, y los criterios de aceptación de cinco encargos piden
# «cuerpos ≤450»—, y ese 450 vivía SOLO dentro de un comentario. Una skill a 460
# incumplía el contrato escrito y pasaba en silencio: **sexta vez el mismo
# patrón**, y esta dentro del arnés que persigue a las otras cinco.
#
# Se elige subir el arnés al número del contrato y no bajar el contrato al del
# arnés, porque el 450 es el que la gente tiene que cumplir; el 475 no era un
# umbral distinto, era un número sin dueño. Hoy sale gratis: la mayor de las 39
# está en 475 y las cinco tocadas en el sprint 8 van entre 442 y 449.
SATURACION = 450        # umbral de AVISO, y es EL número del contrato
TOPE_DURO = 500         # el que BLOQUEA (auditoría 22, H7). 501 pone la suite en rojo

# Los DOS números de la especificación de Agent Skills, en CARACTERES —no en
# palabras: son unidades distintas y confundirlas es el fallo que S1 arregla.
# `AVISO_DESC` es la misma idea que SATURACION: avisar antes del precipicio, con
# margen para que una edición del disparador no lo cruce sin querer.
LIMITE_DESC = 1024      # BLOQUEA. 1024 es el último valor admisible; 1025 rojo
AVISO_DESC = 950        # AVISO. Una description nueva nace por debajo
LIMITE_NAME = 64        # BLOQUEA. Mismo origen, y hoy el máximo son 24

# CHECK 5 · angulares en el frontmatter (sprint 8, S2). `requirements-designer`
# llevaba `"haz X para <persona>"` en su description y eso ROMPE LA SUBIDA: el
# angular se parsea como etiqueta abierta. En Claude Code no se nota porque Code
# **escapa los angulares de la description** —"in text that reaches Claude, such
# as the description, it also escapes angle brackets so the text can't imitate
# Claude Code's internal formatting"—, así que la skill funciona aquí y falla
# fuera. Es la TERCERA vez con la misma asimetría (el tope de 1024, el escalar
# plano multilínea, y esto): el repo medía lo de Code y no medía lo del otro lado.
#
# SOLO EL FRONTMATTER, y no por prudencia sino por medición: en el cuerpo hay
# angulares legítimos —huecos a rellenar como `<mecánico|con juicio>` en
# `plantilla-despacho.md`, `<project-name>` en `memory-snippet.md`— y
# bloquearlos sería el falso positivo que hace que alguien apague el check.
#
# LÍMITE DECLARADO: se exige `<` pegado a una letra (o a `/`), que es la forma
# que un parser lee como etiqueta. Un `<` suelto seguido de espacio ("a < b")
# NO se caza. Rompería XML igual, pero cazarlo metería en el saco toda
# comparación escrita en prosa, y un check con falsos positivos se desactiva —
# que es el modo de fallo que este arnés persigue en otras skills.
ANGULARES = re.compile(r"</?[A-Za-z]")

# CADUCIDAD DE LAS FAMILIAS PROPUESTAS (sprint 10, S6a). Por R3 del RFD 17, una
# pieza propuesta y no construida en 60 días se borra o se re-justifica por
# escrito. El reloj arrancó en la poda del 2026-08-09.
#
# POR QUÉ ESTÁ AQUÍ Y NO EN UN DOCUMENTO. La fecha vivía en UNA FRASE de
# `docs/bd-y-nube/05-CATALOGO-Y-PLAN-DE-IMPLEMENTACION.md:51` y en documentos de
# trabajo. Es el mismo patrón que el 450 antes del sprint 9 y que los otros
# cinco: **escrito, no vigilado**. Aquí se ve en cada corrida de la suite, que
# es la superficie que ya se lee sola.
#
# NO BLOQUEA, y es deliberado: el vencimiento no es un defecto del catálogo, es
# una decisión que toca a un humano. Cuando llegue el día, el aviso pasa a decir
# que venció y SIGUE sin borrar nada — borrar o re-justificar es su llamada, y
# un check que borrase solo convertiría una caducidad en una guillotina.
CADUCIDAD = date(2026, 10, 8)
CADUCAN = "familias 4, 5 y 6 del catálogo (RFD 17 R3, reloj desde la poda del 2026-08-09)"

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
# El hedge tiene DOS formas y no se buscan igual (sprint 7).
#
# CLÁUSULA: "si está instalada", "si existe", "if X is unavailable". Es una
# oración, alguien la escribe junto a la referencia y el plegado del markdown la
# parte por la mitad. Esta se busca en una VENTANA de líneas.
#
# PALABRA SUELTA: "opcional". Esta se queda pegada a SU línea, y no por
# purismo: al ensancharla, `api-design/SKILL.md:36` dejó de avisar porque una
# línea antes decía "(campos nuevos opcionales)" — prosa de otra frase, sobre
# otro tema. Medido, no hipotético. Una palabra corriente en una ventana silencia
# por accidente, que es el falso negativo del que avisa `_ventana.py`; una
# cláusula, no. La regla: **se ensancha lo que alguien escribe COMO exención,
# no lo que puede aparecer por casualidad.**
HEDGE_CLAUSULA = re.compile(
    r"si (?:está|estan|están|no está)\s+(?:instalad|disponible|presente)"
    r"|si existe|si lo tienes"
    r"|if .{0,40}\bis (?:unavailable|not installed|missing)", re.I)
HEDGE_SUELTO = re.compile(r"opcional", re.I)
# El de siempre, para quien quiera preguntar "¿esta línea lleva hedge?" sin
# distinguir formas. El check usa los dos de arriba, cada uno a su alcance.
HEDGE = re.compile(HEDGE_CLAUSULA.pattern + r"|" + HEDGE_SUELTO.pattern, re.I)


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


def campo_resuelto(texto, clave):
    """Valor de `clave` en el frontmatter, TAL COMO LO VE EL CARGADOR.

    Resuelve las TRES formas que puede tener un valor multilínea, porque el
    limite se mide sobre la cadena que el cargador construye, no sobre el texto
    crudo con sus saltos y su sangría:

      · **plegado** (`>` / `|`, con sus variantes `-` y `+`);
      · **entrecomillado** en una línea;
      · **plano multilínea** — el que sale de escribir a mano y seguir en la
        línea siguiente sin poner `>`. Es YAML válido.

    EL PLANO SE AÑADIÓ PORQUE SE ESCAPABA (sprint 3b). El resolutor devolvía
    solo la primera línea y paraba, así que **contaba de menos**, que es la
    dirección peligrosa: 600 + 600 caracteres se medían como **600**, el arnés
    daba verde y la subida fallaba igual — el fallo exacto que el check 4 existe
    para impedir. Era latente (0 de 38 skills usan esa forma), y ese es el
    momento de arreglarlo: cuando todavía no ha mordido.

    No se importa un parser YAML a propósito: este arnés es **solo-stdlib**, y
    meter una dependencia aquí rompería la disciplina justo en el fichero que la
    sostiene.

    Devuelve None si la clave no está — que es un defecto distinto y lo reporta
    quien llama, no esta función.
    """
    texto = texto.replace("\r", "")
    if not texto.startswith("---"):
        return None
    fin = texto.find("\n---", 3)
    lineas = (texto[4:fin] if fin != -1 else texto).split("\n")
    for i, linea in enumerate(lineas):
        m = re.match(r"^" + re.escape(clave) + r":\s*(.*)$", linea)
        if not m:
            continue
        valor = m.group(1).strip()
        if valor in (">", "|", ">-", "|-", ">+", "|+"):
            partes = []
            for siguiente in lineas[i + 1:]:
                if not siguiente.strip():
                    partes.append("")
                    continue
                if not siguiente.startswith((" ", "\t")):
                    break                      # empezó la clave siguiente
                partes.append(siguiente.strip())
            valor = " ".join(partes)
        elif len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        elif valor:
            # ESCALAR PLANO: sigue en las líneas más sangradas. Misma mecánica
            # que el plegado de arriba, con dos diferencias que importan:
            #   · una línea en blanco CORTA (en el plegado solo separa párrafo);
            #   · exige `valor` no vacío. `clave:` a secas y luego líneas
            #     sangradas NO es un escalar: es un mapa anidado, y tragárselo
            #     seria pasarse consumiendo — el riesgo de este arreglo.
            for siguiente in lineas[i + 1:]:
                if not siguiente.strip() or not siguiente.startswith((" ", "\t")):
                    break
                valor += " " + siguiente.strip()
        return re.sub(r"\s+", " ", valor).strip()
    return None


def excede_desc(chars):
    """¿Pasa del límite de la especificación? 1024 pasa; 1025 bloquea.

    Función y no un `>` suelto por lo mismo que `excede_tope`: `autoprueba_desc`
    ejerce ESTA decisión, no una reimplementación suya.
    """
    return chars > LIMITE_DESC


def mide_frontmatter():
    """[(skill, chars_desc, chars_name)] de todas las skills, sin filtrar."""
    filas = []
    for skill_md in sorted(SKILLS.rglob("SKILL.md")):
        partes = skill_md.relative_to(SKILLS).parts
        if "_build" in partes or partes[0] == "_template":
            continue
        texto = skill_md.read_text(encoding="utf-8")
        desc = campo_resuelto(texto, "description")
        nombre = campo_resuelto(texto, "name")
        filas.append((f"{partes[0]}/{partes[1]}",
                      -1 if desc is None else len(desc),
                      -1 if nombre is None else len(nombre)))
    return filas


def autoprueba_desc():
    """Mutación: fabrica los dos lados del borde de 1024 y exige la decisión.

    (bool, motivo). Se ejerce el par real —`campo_resuelto` + `excede_desc`—, y
    con la description escrita como escalar plegado en varias líneas, que es la
    forma que tienen todas las nuestras: si el resolvedor no plegara, el conteo
    incluiría saltos y sangría y el borde se movería sin que nadie lo notara.
    """
    def skill_con(n, plana=False):
        # 8 caracteres por trozo + el espacio que los une = 9 por bloque.
        bloques, resto = divmod(n + 1, 9)
        trozos = ["x" * 8] * bloques
        if resto:
            trozos.append("x" * (resto - 1))
        if plana:
            # El primer trozo va en la MISMA línea que la clave y el resto
            # sangrados: escalar PLANO multilínea, sin `>`. Es la forma que sale
            # de escribir a mano, y la que se escapaba del check.
            cola = "".join("\n  " + t for t in trozos[1:])
            return (f"---\nname: laboratorio\ndescription: {trozos[0]}{cola}\n"
                    f"---\n\ncuerpo\n")
        cuerpo_desc = "\n".join("  " + t for t in trozos)
        return f"---\nname: laboratorio\ndescription: >\n{cuerpo_desc}\n---\n\ncuerpo\n"

    # Las DOS formas, en los DOS lados del borde. Probar solo la que el
    # resolutor ya sabía leer es lo que dejó vivo el escape del plano: un
    # resolutor verificado contra su propio caso fácil no está verificado.
    for plana in (False, True):
        forma = "plano multilínea" if plana else "plegado `>`"
        justo = campo_resuelto(skill_con(LIMITE_DESC, plana), "description")
        pasada = campo_resuelto(skill_con(LIMITE_DESC + 1, plana), "description")
        if justo is None or len(justo) != LIMITE_DESC:
            return False, (f"el resolvedor no resuelve el escalar {forma}: mide "
                           f"{len(justo or '')} donde hay {LIMITE_DESC}")
        if excede_desc(len(justo)):
            return False, (f"{LIMITE_DESC} caracteres exactos en {forma} "
                           f"deberían pasar, y bloquean")
        if not excede_desc(len(pasada)):
            return False, (f"{LIMITE_DESC + 1} caracteres en {forma} NO bloquean "
                           f"— el límite de la especificación vuelve a ser "
                           f"decorativo")

    # Y el reverso del arreglo: `clave:` vacía seguida de líneas sangradas es un
    # MAPA ANIDADO, no un escalar. Tragárselo sería pasarse consumiendo, que es
    # el modo de fallo que este arreglo puede introducir.
    anidado = campo_resuelto(
        "---\ndescription:\n  type: user\n  otro: 2\nname: x\n---\n", "description")
    if anidado:
        return False, (f"un mapa anidado bajo `description:` se está leyendo "
                       f"como valor ({anidado[:40]!r}): el resolutor consume de "
                       f"más")
    if AVISO_DESC > LIMITE_DESC:
        return False, (f"AVISO_DESC ({AVISO_DESC}) por encima de LIMITE_DESC "
                       f"({LIMITE_DESC}): el aviso no llegaría antes que el corte")
    return True, ""


def claves_frontmatter(texto):
    """Claves de primer nivel del frontmatter, en orden. [] si no hay.

    Se enumeran en vez de mirar solo `name`/`description` porque el check 5 mide
    el frontmatter ENTERO: el día que alguien añada `when_to_use` o `allowed-
    tools`, el angular tiene que seguir bloqueando sin que nadie se acuerde de
    ampliar una lista. Una lista a mano es otro catálogo que se desincroniza.
    """
    texto = texto.replace("\r", "")
    if not texto.startswith("---"):
        return []
    fin = texto.find("\n---", 3)
    cuerpo_fm = texto[4:fin] if fin != -1 else texto
    claves = []
    for linea in cuerpo_fm.split("\n"):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):", linea)
        if m and m.group(1) not in claves:
            claves.append(m.group(1))
    return claves


def tiene_angulares(valor):
    """El fragmento con angulares, o None. La decisión que ejerce la autoprueba.

    Función y no un `search` suelto por lo mismo que `excede_tope` y
    `excede_desc`: un check verificado contra una reimplementación no está
    verificado, está duplicado.
    """
    m = ANGULARES.search(valor or "")
    if not m:
        return None
    ini = max(0, m.start() - 22)
    return valor[ini:m.start() + 26]


def mide_angulares():
    """[(skill, clave, fragmento)] — angulares en el frontmatter de cada skill.

    SE MIDE EL VALOR RESUELTO, NO EL TEXTO CRUDO, y esa es toda la diferencia
    entre un check y un falso positivo masivo: las 39 skills abren su
    description con `description: >`, y ese `>` es el indicador de plegado de
    YAML —sintaxis, no contenido—. Un check sobre el crudo diría «39 hallazgos»
    el primer día y estaría desactivado el segundo.

    Es la lección del sprint 7 aplicada antes de que muerda: **se mide el
    contrato que llega al cargador, no el texto que se lee en la pantalla.**
    """
    filas = []
    for skill_md in sorted(SKILLS.rglob("SKILL.md")):
        partes = skill_md.relative_to(SKILLS).parts
        if "_build" in partes or partes[0] == "_template":
            continue
        texto = skill_md.read_text(encoding="utf-8")
        for clave in claves_frontmatter(texto):
            fragmento = tiene_angulares(campo_resuelto(texto, clave))
            if fragmento:
                filas.append((f"{partes[0]}/{partes[1]}", clave, fragmento))
    return filas


def autoprueba_angulares():
    """Mutación: mete un angular en una description y exige que se cace.

    (bool, motivo). Los CUATRO lados, porque los tres últimos son los que
    convierten un check en ruido:
      · con `<algo>` → hallazgo;
      · sin él → limpio;
      · el `>` del plegado NO es hallazgo (si lo fuera, dispararía en las 39);
      · un angular en el CUERPO no es hallazgo — ahí hay markdown legítimo, y
        bloquearlo sería el falso positivo que desactiva el check. Hoy el cuerpo
        de las skills usa angulares a propósito (`<mecánico|con juicio>` en la
        plantilla de despacho es un hueco a rellenar, no una etiqueta).
    """
    def skill_con(desc):
        return f"---\nname: laboratorio\ndescription: >\n  {desc}\n---\n\ncuerpo\n"

    sucia = skill_con('usa "haz X para <persona>" como gatillo')
    if not tiene_angulares(campo_resuelto(sucia, "description")):
        return False, ("un `<persona>` en la description NO se caza: el check "
                       "no vería el caso que lo motivó")
    limpia = skill_con('usa "haz X para Fulano" como gatillo')
    if tiene_angulares(campo_resuelto(limpia, "description")):
        return False, "una description sin angulares da hallazgo: falso positivo"
    # El plegado. Este es el que importa: `campo_resuelto` se come el `>` como
    # sintaxis, así que el valor resuelto no lo lleva. Si algún día alguien
    # cambia el resolutor y el `>` empieza a colarse en el valor, esto se pone
    # rojo ANTES de que el check dispare 39 veces y alguien lo apague.
    for skill_md in sorted(SKILLS.rglob("SKILL.md")):
        partes = skill_md.relative_to(SKILLS).parts
        if "_build" in partes or partes[0] == "_template":
            continue
        crudo = skill_md.read_text(encoding="utf-8").replace("\r", "")
        fin = crudo.find("\n---", 3)
        if "description: >" in crudo[:fin if fin != -1 else len(crudo)]:
            if tiene_angulares(campo_resuelto(crudo, "description")):
                continue                      # es un angular de verdad, no el `>`
            break
    else:
        return False, ("ninguna skill usa `description: >`: la autoprueba del "
                       "plegado ya no ejerce nada y hay que revisarla")
    # Y el reverso declarado: el CUERPO no se mide. Se comprueba ejerciendo
    # `mide_angulares` sobre una skill de laboratorio con angulares abajo.
    if tiene_angulares("texto con <etiqueta> en el cuerpo") is None:
        return False, ("el detector no ve `<etiqueta>`: no es que el cuerpo esté "
                       "exento, es que el detector no detecta")
    if AVISO_DESC > LIMITE_DESC:
        return False, "AVISO_DESC por encima de LIMITE_DESC"
    return True, ""


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
        lineas = texto.splitlines()
        for i, linea in enumerate(lineas):
            n = i + 1
            # Excepción declarada JUNTO a la referencia, en una ventana de
            # líneas y no en una sola (sprint 7). El hedge es una frase, y una
            # frase la parte el plegado del markdown: "— si / está instalada"
            # no lo veía nadie, y este arnés lo AVISABA en su propio mensaje
            # mientras seguía mordiendo. El número, en `_ventana.py`.
            if marcada(lineas, i, HEDGE_CLAUSULA) or HEDGE_SUELTO.search(linea):
                continue
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
           f"(aviso {SATURACION}, tope duro {TOPE_DURO})).",
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
    # La ventana del hedge, por los DOS bordes y con la frase real: dentro
    # exime, a una línea más NO —si eximiera, encontraría el hedge de otra
    # referencia y daría por buena una que no lo está—, y una frase partida por
    # el plegado se ve, que es el fallo del sprint 1.
    ok_ventana, motivo_ventana = autoprueba_ventana(
        HEDGE_CLAUSULA, "usa `x` si está instalada",
        partida=("— usa `x` si", "está instalada y sigue"))
    if ok_ventana and marcada(["(campos nuevos opcionales) no versionan",
                               "la política vive en `api-evolution`"], 1,
                              HEDGE_CLAUSULA):
        # El caso REAL que destapó la ventana: una palabra corriente en la línea
        # de al lado no puede eximir. Si algún día `opcional` vuelve a entrar en
        # la cláusula, esto se pone rojo antes de que silencie nada.
        ok_ventana, motivo_ventana = False, (
            "`opcional` en la línea vecina exime: una palabra suelta en la "
            "ventana silencia por accidente (api-design:36, medido)")
    print(f"  [AUTOPRUEBA] {'OK' if ok_ventana else 'FALLIDA'} — el hedge-cláusula "
          f"exime a distancia {RADIO}, no a {RADIO + 1}, se ve partido por el "
          f"salto, y `opcional` no cruza de línea"
          + (f"\n               {motivo_ventana}" if not ok_ventana else ""))
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

    print("\n── Check 4 · límites de la especificación (BLOQUEA) " + "─" * 22 + "\n")
    ok_desc, motivo_desc = autoprueba_desc()
    print(f"  [AUTOPRUEBA] {'OK' if ok_desc else 'FALLIDA'} — {LIMITE_DESC} "
          f"caracteres pasan y {LIMITE_DESC + 1} bloquean"
          + (f"\n               {motivo_desc}" if not ok_desc else ""))
    fm = mide_frontmatter()
    sin_campo = [(s, d, n) for s, d, n in fm if d < 0 or n < 0]
    pasadas = [(s, d, n) for s, d, n in fm
               if excede_desc(d) or n > LIMITE_NAME]
    avisos_desc = [(s, d, n) for s, d, n in fm
                   if AVISO_DESC < d <= LIMITE_DESC]
    if sin_campo:
        print(f"\n  {len(sin_campo)} skill(s) sin `name` o sin `description` en "
              f"el frontmatter:\n")
        for s, d, n in sin_campo:
            falta = " y ".join(x for x, v in (("description", d), ("name", n))
                               if v < 0)
            print(f"    {s:<34}falta {falta}")
    if pasadas:
        print(f"\n  {len(pasadas)} skill(s) POR ENCIMA de la especificación "
              f"(description ≤{LIMITE_DESC}, name ≤{LIMITE_NAME}):\n")
        for s, d, n in pasadas:
            exceso = []
            if excede_desc(d):
                exceso.append(f"description {d} (+{d - LIMITE_DESC})")
            if n > LIMITE_NAME:
                exceso.append(f"name {n} (+{n - LIMITE_NAME})")
            print(f"    {s:<34}{' · '.join(exceso)}")
        print(f"\n  Esto SÍ tumba el arnés, y no es cosmético: la skill CARGA en\n"
              f"  Claude Code (que trunca a 1536) y falla AL SUBIRLA. El arreglo\n"
              f"  no es subir el número —no es nuestro—: es acortar el disparador\n"
              f"  sin tocar las frases gatillo, que son su razón de ser.")
    if avisos_desc:
        print(f"\n  {len(avisos_desc)} en la banda de aviso "
              f"({AVISO_DESC + 1}-{LIMITE_DESC}): margen escaso para la próxima "
              f"edición.\n")
        for s, d, _n in avisos_desc:
            print(f"    {s:<34}{d:>9}   (a {LIMITE_DESC - d} del corte)")
    if not (sin_campo or pasadas or avisos_desc):
        mayor = max(fm, key=lambda f: f[1])
        print(f"\n  Las {len(fm)} descriptions por debajo de {AVISO_DESC}. "
              f"La mayor: {mayor[0]} ({mayor[1]}).")

    print("\n── Check 5 · angulares en el frontmatter (BLOQUEA) " + "─" * 23 + "\n")
    ok_ang, motivo_ang = autoprueba_angulares()
    print(f"  [AUTOPRUEBA] {'OK' if ok_ang else 'FALLIDA'} — un `<algo>` en la "
          f"description se caza, el `>` del plegado no, y el cuerpo no se mide"
          + (f"\n               {motivo_ang}" if not ok_ang else ""))
    angulares = mide_angulares()
    if angulares:
        print(f"\n  {len(angulares)} campo(s) del frontmatter con angulares:\n")
        for s, clave, frag in angulares:
            print(f"    {s:<34}{clave}:  …{frag}…")
        print(f"\n  Esto SÍ tumba el arnés, y no es cosmético: el angular se\n"
              f"  parsea como etiqueta abierta y ROMPE LA SUBIDA. Aquí no se ve\n"
              f"  porque Claude Code escapa los angulares de la `description`.\n"
              f"  El arreglo no es borrar la frase gatillo —es su razón de ser—:\n"
              f"  es quitarle los angulares. `<persona>` → `Fulano`.")
    else:
        print("  Ningún frontmatter lleva angulares: las 39 suben sin romper XML.")

    print("\n── Caducidad de las propuestas (AVISO, no bloquea) " + "─" * 23 + "\n")
    dias = (CADUCIDAD - date.today()).days
    if dias > 0:
        print(f"  Faltan {dias} días para el {CADUCIDAD} — {CADUCAN}.")
        if dias <= 14:
            print(f"  ⚠ Menos de dos semanas: o se construyen, o se re-justifican\n"
                  f"    por escrito, o se borran. La decisión es humana.")
    elif dias == 0:
        print(f"  ⚠ VENCEN HOY ({CADUCIDAD}) — {CADUCAN}.\n"
              f"    Construir, re-justificar por escrito, o borrar.")
    else:
        print(f"  ⚠ VENCIERON hace {-dias} días (el {CADUCIDAD}) — {CADUCAN}.\n"
              f"    Esto NO borra nada: la decisión de borrar o re-justificar es\n"
              f"    humana, y el aviso se queda hasta que alguien la tome.")

    # Ocho motivos de rojo, y CUATRO son las propias autopruebas: si caen, lo que
    # este fichero afirma sobre sus topes —y sobre dónde busca el hedge— deja de
    # estar respaldado, y un check no verificado en verde es exactamente el
    # agujero de H7.
    return 1 if (hallazgos or excedidas or pasadas or sin_campo or angulares
                 or not ok_tope or not ok_desc or not ok_ventana
                 or not ok_ang) else 0


if __name__ == "__main__":
    sys.exit(main())
