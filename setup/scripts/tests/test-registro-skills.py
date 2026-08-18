#!/usr/bin/env python3
"""
test-registro-skills.py — El registro del perfil `bot` contra el disco.

Por qué existe (2026-08-18). `setup/skills/README.md` lleva una tabla que decide
qué skills ve el perfil `bot` del puente Telegram, y su propia regla de
mantenimiento dice: *"toda skill nueva añade su fila en el mismo PR"* y *"si una
fila falta, el perfil bot la excluye por defecto"*.

**Esa regla se incumplió seis veces seguidas.** La auditoría 21 (H5) reportó DOS
filas ausentes el 2026-08-14 —`goal-forge` y `requirements-designer`—; al
reconstruir la tabla contra el disco el 2026-08-18 faltaban SEIS: las dos de la
auditoría más `ml-problem-framing`, `ml-tabular-workflow`, `web-design-guidelines`
y `deck-or-brief`. Las cuatro nuevas entraron **después** de que la auditoría
señalara el hueco.

Y ahí está el argumento entero para este fichero: **arreglar la tabla a mano fue
el parche, no la cura.** Ya se había arreglado antes; volvió a desincronizarse.
Es el mismo patrón que el tope de 500 palabras (auditoría 22, H7), el 450 dentro
de un comentario (sprint 9), el presupuesto del snippet dentro de su cabecera
(sprint 14) y el techo de `_PROJECT.md` (`test-vault-topes.py`, hoy mismo):
**escrito, no vigilado**. La séptima vez se cierra midiendo.

QUÉ HACE QUE ESTA OMISIÓN DUELA, y por qué no es cosmética: la exclusión es
**silenciosa y en la dirección cómoda**. Una skill sin fila no da error, no
avisa, no aparece — el bot sencillamente no la tiene, y desde el móvil eso se
vive como "el modelo no la usó", que es indistinguible de un problema de
`description`. Se puede perder una skill entera durante semanas sin que nada lo
diga. Un catálogo que falla en silencio es peor que uno que falla ruidosamente.

LOS TRES DEFECTOS QUE CAZA, y los tres bloquean:

  1. **Skill en disco sin fila** — el defecto de H5. El bot la pierde por
     omisión, no por decisión.
  2. **Fila sin skill en disco** — el reverso, y nadie lo miraba. Una fila
     fantasma hace creer que una skill borrada sigue disponible.
  3. **Categoría que no cuadra** con la superficie real del fichero. Una fila
     que dice `shared` sobre una skill de `claude-code/` miente sobre dónde se
     despliega, que es justo lo que el check 3 del catálogo vigila en las
     referencias.

EL UNIVERSO SON `shared/` + `claude-code/`, y no se elige aquí: lo declara el
propio README —*"las 2 de `cowork/` quedan fuera A PROPÓSITO —el bot corre sobre
Claude Code— y por eso no tienen fila"*—. Ese **2** también se comprueba: es un
número escrito en prosa, o sea exactamente la clase de afirmación que este repo
lleva seis veces descubriendo tarde. Si mañana nace una tercera skill de
`cowork/`, la frase pasa a ser falsa y alguien tiene que decidir si el universo
cambió; el arnés no lo decide, lo delata.

LÍMITE DECLARADO: esto mide que **exista la fila**, no que el motivo sea el
correcto. Si alguien pone `web-security-review` en ✗ con el motivo "no me gusta",
la tabla pasa. Juzgar el criterio de inclusión pide contexto que una máquina no
tiene; lo que una máquina sí puede garantizar es que **toda skill tenga una
decisión escrita**, y que ninguna se caiga por descuido. La diferencia entre
"excluida por decisión" y "excluida por omisión" es todo lo que este arnés
existe para preservar.

Uso:  setup/scripts/py setup/scripts/tests/test-registro-skills.py     [repo]
Salidas: 0 la tabla y el disco coinciden · 1 hay hallazgos
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
SKILLS = SETUP / "skills"
REGISTRO = SKILLS / "README.md"

# El universo del registro. Lo declara el README, no este fichero.
SUPERFICIES = ("shared", "claude-code")
# Las superficies fuera del universo, con el número que el README afirma en
# prosa. Se comprueba por lo mismo que el resto: es un número escrito.
FUERA = {"cowork": 2}

# Fila de la tabla: | nombre | categoría | ✓/✗ | motivo |
FILA = re.compile(r"^\|\s*`?([a-z][a-z0-9-]*)`?\s*\|\s*([a-z-]+)\s*\|\s*([^|]*?)\s*\|")
ANCLA = re.compile(r"^#{2,4}\s+Registro\s*$", re.I)
CABECERA = re.compile(r"^\|\s*Skill\s*\|", re.I)
SEPARADOR = re.compile(r"^\|[\s:-]+\|")
# Marcas admitidas en la columna `Bot`. Cualquier otra cosa es una fila a medias:
# alguien la escribió sin decidir, y el efecto práctico es el mismo hueco.
MARCAS = ("✓", "✗")


def inventario():
    """{nombre: {superficies}} de las skills reales del repo.

    **Un conjunto y no un valor suelto, y esto no es purismo**: `project-resume`
    vive HOY en `claude-code/` y en `cowork/` a la vez. Con un dict plano el
    último `rglob` que llegara ganaba, así que la superficie de esa skill
    dependía del orden de recorrido del sistema de ficheros — y si ganaba
    `cowork/`, su fila legítima se reportaba como «fuera del universo del
    registro». Un arnés cuyo veredicto depende del orden del disco no es un
    arnés: es un sorteo.
    """
    inv = {}
    for skill_md in SKILLS.rglob("SKILL.md"):
        partes = skill_md.relative_to(SKILLS).parts
        if "_build" in partes or partes[0] == "_template" or len(partes) < 2:
            continue
        inv.setdefault(partes[1], set()).add(partes[0])
    return inv


def filas_del_registro(texto):
    """{nombre: (categoria, marca)} leído de la tabla del README.

    Se parsea la tabla y no una lista aparte a propósito: una segunda lista sería
    un tercer catálogo, y el tercer catálogo se desincroniza igual que el
    segundo — que es la enfermedad que este arnés persigue.
    """
    filas, dentro = {}, False
    for linea in texto.replace("\r", "").splitlines():
        # SOLO la sección `### Registro`. El README tiene otras dos tablas —los
        # productos de sync y el árbol de decisión de carpeta— y hoy ninguna
        # colisiona **por casualidad**: sus filas empiezan en mayúscula y el
        # patrón exige minúscula. Depender de eso es depender de que nadie
        # escriba nunca una fila en minúscula en otra tabla, que es la clase de
        # suposición que se rompe sola. Se acota por encabezado.
        if ANCLA.match(linea):
            dentro = True
            continue
        if dentro and linea.startswith("#"):
            break                              # empezó otra sección
        if not dentro or CABECERA.match(linea) or SEPARADOR.match(linea):
            continue
        m = FILA.match(linea)
        if m:
            filas[m.group(1)] = (m.group(2), m.group(3).strip())
    return filas


def revisa(inv, filas):
    """Los tres defectos. Función aparte para que la autoprueba ejerza ESTA
    decisión y no una reimplementación suya."""
    hall = []
    delbot = {n: s for n, s in inv.items() if s & set(SUPERFICIES)}

    for nombre, donde in sorted(delbot.items()):
        vive = "/ y ".join(sorted(donde))
        if nombre not in filas:
            hall.append(f"`{nombre}` ({vive}/) existe en disco y NO tiene "
                        f"fila: el perfil bot la excluye POR OMISIÓN, en "
                        f"silencio y sin que nadie lo haya decidido")
            continue
        categoria, marca = filas[nombre]
        if categoria not in donde:
            hall.append(f"`{nombre}`: la fila dice `{categoria}` y el fichero "
                        f"vive en `{vive}/` — la categoría miente sobre "
                        f"dónde se despliega")
        if marca not in MARCAS:
            hall.append(f"`{nombre}`: la columna `Bot` dice {marca!r} y solo "
                        f"valen {' o '.join(MARCAS)}. Una fila a medias deja el "
                        f"mismo hueco que ninguna fila")

    for nombre in sorted(set(filas) - set(delbot)):
        if nombre in inv:
            hall.append(f"`{nombre}` tiene fila pero solo vive en "
                        f"`{'/ y '.join(sorted(inv[nombre]))}/`, que está fuera "
                        f"del universo del registro")
        else:
            hall.append(f"`{nombre}` tiene fila y NO existe en disco: una fila "
                        f"fantasma hace creer que una skill borrada sigue "
                        f"disponible")

    # El número que el README afirma en prosa sobre las superficies excluidas:
    # «las 2 de `cowork/`». Se cuentan las skills QUE VIVEN AHÍ, que es lo que
    # la frase dice — no las que viven solo ahí. `project-resume` está en
    # `cowork/` y en `claude-code/`, cuenta para el 2 y aun así tiene fila por
    # su lado de `claude-code/`. Medir "solo ahí" daría 1 y el arnés se pondría
    # rojo contra una frase que es verdad.
    for superficie, declarado in FUERA.items():
        real = sum(1 for s in inv.values() if superficie in s)
        if real != declarado:
            hall.append(f"el README dice que `{superficie}/` tiene {declarado} "
                        f"skills fuera del registro y hay {real}. O el universo "
                        f"cambió o la frase caducó — la decisión es humana, pero "
                        f"la frase no puede seguir siendo falsa")
    return hall


def autoprueba():
    """Mutación: fabrica los tres defectos y exige que cada uno se cace.

    (bool, motivo). Y el cuarto caso, que es el que da valor a los otros tres:
    un registro COMPLETO tiene que salir limpio. Sin él, "siempre rojo" pasaría
    la autoprueba sin comprobar nada — el defecto que esta casa persigue.
    """
    global FUERA          # va PRIMERO: declararlo tras usar el nombre es SyntaxError

    # Conjuntos, como el inventario real. `beta` vive en DOS superficies a la
    # vez —el caso `project-resume`—, así que la tabla sana también lo ejerce:
    # si el arnés volviera a aplastar superficies, este caso lo dice.
    inv = {"alfa": {"shared"}, "beta": {"claude-code", "cowork"},
           "gamma": {"cowork"}}
    completo = {"alfa": ("shared", "✓"), "beta": ("claude-code", "✗")}
    original = FUERA
    # El inventario de laboratorio tiene 1 skill de `cowork/`, no las 2 reales,
    # así que el conteo declarado se ajusta al laboratorio. Si no, el caso
    # "tabla sana" saldría rojo por un motivo que no está probando.
    FUERA = {k: sum(1 for s in inv.values() if k in s) for k in original}
    try:
        if revisa(inv, completo):
            return False, ("un registro COMPLETO da hallazgo: el arnés no "
                           "distingue la tabla sana de la rota y su rojo no "
                           "significaría nada")

        sin_fila = {"alfa": ("shared", "✓")}
        if not any("POR OMISIÓN" in h for h in revisa(inv, sin_fila)):
            return False, ("una skill en disco sin fila NO da hallazgo: es "
                           "exactamente H5 y volvería a pasar")

        fantasma = dict(completo, delta=("shared", "✓"))
        if not any("fantasma" in h for h in revisa(inv, fantasma)):
            return False, "una fila sin skill en disco NO da hallazgo"

        mal = dict(completo, beta=("shared", "✗"))
        if not any("miente sobre" in h for h in revisa(inv, mal)):
            return False, "una categoría equivocada NO da hallazgo"

        media = dict(completo, beta=("claude-code", "—"))
        if not any("fila a medias" in h for h in revisa(inv, media)):
            return False, ("una columna `Bot` sin ✓ ni ✗ NO da hallazgo: deja "
                           "el mismo hueco que la fila ausente")

        FUERA = {"cowork": 99}
        if not any("caducó" in h for h in revisa(inv, completo)):
            return False, ("el conteo declarado de las superficies excluidas no "
                           "se comprueba: es un número escrito más, que es el "
                           "patrón que este arnés cierra")
        # Y el parseo, que es la otra mitad y no la ejerce ninguno de los casos
        # de arriba: la tabla señuelo lleva una fila en MINÚSCULA para que el
        # acotado por encabezado tenga algo que rechazar. Sin ella el caso
        # pasaría aunque el arnés leyera el README entero.
        doc = ("## Otra cosa\n\n"
               "| Producto | Mecanismo |\n|---|---|\n"
               "| cowork | señuelo que NO debe entrar |\n\n"
               "### Registro\n\n"
               "| Skill | Categoría | Bot | Por qué |\n|---|---|:---:|---|\n"
               "| alfa | shared | ✓ | motivo |\n\n"
               "## Sección siguiente\n\n"
               "| beta | shared | ✓ | tampoco debe entrar |\n")
        leidas = filas_del_registro(doc)
        if set(leidas) != {"alfa"}:
            return False, (f"el parseo no se acota a `### Registro`: leyó "
                           f"{sorted(leidas)} donde solo debía leer ['alfa']")
    finally:
        FUERA = original
    return True, ""


def main():
    if not REGISTRO.is_file():
        print(f"No encuentro {REGISTRO}: sin registro no hay perfil bot que "
              f"auditar, y eso no es un salto — es el fichero que decide qué "
              f"skills ve el daemon.")
        return 1

    print("Registro del perfil `bot` contra el disco\n")
    ok, motivo = autoprueba()
    print(f"  [AUTOPRUEBA] {'OK' if ok else 'FALLIDA'} — los cinco defectos "
          f"(sin fila, fila fantasma, categoría mala,\n               marca "
          f"inválida, conteo declarado falso) se cazan, y una tabla sana pasa"
          + (f"\n               {motivo}" if not ok else ""))

    inv = inventario()
    filas = filas_del_registro(REGISTRO.read_text(encoding="utf-8"))
    if not filas:
        # Sin esto, un ancla renombrada produciría «39 skills sin fila», que es
        # un diagnóstico FALSO con pinta de catástrofe: diría que la tabla está
        # vacía cuando lo que pasa es que no se encontró. Un arnés tiene que
        # distinguir «medí y salió mal» de «no pude medir».
        print(f"\n  [FALLA] no se encontró ninguna fila bajo un encabezado "
              f"`### Registro` en\n          {REGISTRO.name}. Esto NO significa "
              f"que la tabla esté vacía: significa\n          que este arnés no "
              f"la encontró — si la sección se renombró, ajusta `ANCLA`.")
        return 1
    hall = revisa(inv, filas)

    delbot = {n: s for n, s in inv.items() if s in SUPERFICIES}
    marcadas = sum(1 for _c, m in filas.values() if m == "✓")
    print(f"\n  [MEDIDO] {len(delbot)} skills en {' + '.join(SUPERFICIES)}, "
          f"{len(filas)} filas en la tabla, {marcadas} con ✓ para el bot")

    if hall:
        print(f"\n  {len(hall)} hallazgo(s):\n")
        for h in hall:
            print(f"    [FALLA] {h}")
        print("\n  La regla del propio README: «toda skill nueva añade su fila\n"
              "  en el mismo PR». Se incumplió seis veces seguidas porque nadie\n"
              "  la medía. El arreglo es la fila, con su motivo escrito — no\n"
              "  bajar este arnés.")
    else:
        print(f"\n  [OK] toda skill de {' + '.join(SUPERFICIES)} tiene su fila y "
              f"su decisión\n       escrita, y ninguna fila apunta a una skill "
              f"que ya no está.")

    return 1 if (hall or not ok) else 0


if __name__ == "__main__":
    sys.exit(main())
