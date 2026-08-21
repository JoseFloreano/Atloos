#!/usr/bin/env python3
"""
medir-disparo.py — ¿la skill CARGA con la frase real del usuario? Se mide, no se opina.

POR QUÉ EXISTE (sprint 17, 2026-08-19). La `description:` de `skill-forge` sigue
diciendo *«or al detectar un gap que merece skill propia»*: dos juicios
encadenados —hay hueco · y vale una skill— y **nada los cuenta**. Está en el
barrido de `references/disparadores.md` desde el 2026-08-17 y no se ha tocado,
porque la propia skill prohíbe tocar una `description` sin medir el disparo:

    «Hasta que exista esa medición, la `description` no se toca — cambiarla a
    ciegas es apostar cuándo carga una de las 39.»

El sprint 14 dejó el recambio y las frases escritos y **no ejecutó la medida**:
una sesión ciega no se monta desde dentro de la sesión que la necesita. Este
script la monta desde fuera.

QUÉ MIDE, Y POR QUÉ ASÍ. Lanza `claude -p` con cada frase, **una sesión nueva por
frase**, con el `cwd` en un temporal **fuera del repo** — las dos condiciones que
pide el protocolo—, y busca en el flujo de eventos si se invocó la herramienta
`Skill` con `skill-forge`. Ni el resumen del modelo ni «me parece que cargó»:
la llamada, o su ausencia.

LAS TRES COSAS QUE HACEN QUE LA MEDIDA SIRVA, y que un tecleo a mano no da:

  · **El canario (frase 0).** Pide la skill POR SU NOMBRE. Si con eso no carga,
    lo que está roto es el arnés —la copia instalada, el config dir, el flag—,
    **no el disparador**. Sin canario, un arnés mal enchufado se lee como «no
    dispara» y condena una `description` sana. Su fallo aborta con exit 2 y
    **anula la medición**: no hay tabla que interpretar.
  · **La fase la dicta el DISCO, no la memoria.** Antes de gastar un peso lee la
    `description` **instalada** (`~/.claude/skills/`), no la del repo, porque es
    la instalada la que decide si la skill carga. De ahí sale la etiqueta
    ANTES/DESPUÉS y su sha256 al artefacto. Medir la cara que no es fue el fallo
    del check 6 (sprint 14) y del `gate-verde.json` duplicado: aquí no puede
    pasar, porque la etiqueta no se teclea.
  · **N repeticiones.** Una pasada no distingue «no dispara» de «esta vez no
    disparó». El disparo es estocástico; el veredicto es `k/n`, no un sí/no.

LO QUE ESTA MEDIDA **NO** ES. `-p` es un turno único, no una conversación: es un
**proxy** de la sesión interactiva, bueno para comparar ANTES contra DESPUÉS con
todo lo demás fijo, y flojo como retrato de una sesión real. Las frases 1 y 2
conviene confirmarlas una vez a mano. Dicho de otra forma: sirve para el DELTA,
no para el valor absoluto.

DE LAS 6 FRASES, SOLO UNA MIDE EL CAMBIO. La 1 y la 3 ya son disparadores
literales de la `description` de hoy (`"la skill no dispara"`, `"crea una
skill"`): cargan antes y después pase lo que pase. La 4, la 5 y la 6 son
controles negativos. **La discriminante es la 2** — y si la 2 no pasa de NO a SÍ,
el cambio no hizo nada, por bien escrito que esté. Las otras cinco solo dicen
que no rompiste nada, que también hay que saberlo.

CUESTA DINERO Y PIDE RED, así que **no se llama `test-*.py` ni vive en un
`tests/`**: `run-tests.py` descubre por glob (`setup/**/tests/test-*.py`) y este
arnés entraría al gate del merge, que corre en cada integración. Un arnés que
cobra por commit se acaba desactivando — regla de la casa.

Uso:
  setup/scripts/py setup/scripts/medir-disparo.py --seco     # qué haría, gratis
  setup/scripts/py setup/scripts/medir-disparo.py            # mide (n=3)
  setup/scripts/py setup/scripts/medir-disparo.py --n 5
  setup/scripts/py setup/scripts/medir-disparo.py --aplicar  # cambia la description

Salidas: 0 todas las frases coinciden con lo esperado · 1 alguna discrepa (hay
que mirarla) · 2 el canario falló y la medición NO vale · 127 falta `claude`.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

SKILL = "skill-forge"
REPO = Path(__file__).resolve().parents[2]
FUENTE = REPO / "setup" / "skills" / "shared" / SKILL / "SKILL.md"
INSTALADA = Path.home() / ".claude" / "skills" / SKILL / "SKILL.md"
MEDICIONES = REPO / "setup" / "scripts" / "_mediciones"

# Los dos textos que etiquetan la fase. Se buscan en la description INSTALADA.
MARCA_ANTES = "al detectar un gap que merece"
MARCA_DESPUES = "TERCERA vez"

# La description nueva, entera y en una línea. Se escribe completa —y no por
# parche sobre el texto viejo— para que `--aplicar` reenvuelva a 78 columnas y
# el diff sea legible en vez de un reflow accidental.
DESCRIPTION_NUEVA = (
    "Crea, mejora y prueba skills de NUESTRO sistema (setup/skills con carpetas "
    "shared/claude-code/cowork) aplicando las mejores prácticas oficiales de "
    "authoring y nuestras convenciones de sync/auditoría. Use when the user says "
    '"crea una skill", "nueva skill para X", "mejora esta skill", "la skill no '
    'dispara", "optimiza la descripción", or cuando una instrucción se repite a '
    "mano por TERCERA vez en el repo. Para plugins completos de Cowork usa "
    "`cowork:cowork-plugin` (skill bundled de Cowork, no está en Claude Code); "
    "esto es para skills propias."
)

# Los topes que impone la especificación de Agent Skills, revalidados aquí
# porque `--aplicar` escribe: el arnés del catálogo corre después, y para
# entonces el fichero ya está tocado.
TOPE_DESCRIPTION = 1024
AVISO_DESCRIPTION = 950

FRASES = [
    {
        "n": 0,
        "texto": "usa la skill skill-forge ahora",
        "espera": True,
        "papel": "CANARIO",
        "motivo": "la pide por su nombre; si esta falla, lo roto es el arnés",
    },
    {
        "n": 1,
        "texto": "la skill no dispara, arréglala",
        "espera": True,
        "papel": "control +",
        "motivo": "la petición real que falló, literal. Ya es disparador de hoy",
    },
    {
        "n": 2,
        "texto": "llevo tres sprints copiando esta misma instrucción a mano",
        "espera": True,
        "papel": "DISCRIMINANTE",
        "motivo": "la única que mide el cambio: hoy no la cubre nada",
    },
    {
        "n": 3,
        "texto": "crea una skill para esto",
        "espera": True,
        "papel": "control +",
        "motivo": "disparador literal de hoy; vigila que el cambio no lo pise",
    },
    {
        "n": 4,
        "texto": "documenta esta decisión de arquitectura",
        "espera": False,
        "papel": "control -",
        "motivo": "es de adr-writer",
    },
    {
        "n": 5,
        "texto": "guarda esto para que no se olvide",
        "espera": False,
        "papel": "control -",
        "motivo": "es de memory-keeper",
    },
    {
        "n": 6,
        "texto": "cada vez que haga un commit quiero que corra el linter automáticamente",
        "espera": False,
        "papel": "control -",
        "motivo": (
            "la vecina que el protocolo del sprint 14 no tenía: repetir algo a "
            "mano también pide HOOK (update-config), no skill. Si esta carga, "
            "el trigger nuevo se ensanchó de más y toca desambiguar"
        ),
    },
]

# Las herramientas de escritura se apagan: la sesión de medida no viene a
# trabajar, y una frase como «crea una skill para esto» invita a hacerlo.
# `Skill` NO se toca — es justo lo que se está midiendo.
SIN_ESCRITURA = "Edit,Write,NotebookEdit,Bash"


def resuelve_description(ruta):
    """La `description` del frontmatter, plegada a una línea. None si no hay."""
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", texto, re.S)
    if not m:
        return None
    fm = m.group(1)
    m2 = re.search(r"^description:\s*(.*)$", fm, re.M)
    if not m2:
        return None
    cabeza = m2.group(1).strip()
    if cabeza not in (">", "|", ">-", "|-"):
        return cabeza.strip('"').strip("'")
    # Escalar plegado: se une lo indentado que sigue, que es lo que ve el modelo.
    lineas = []
    tras = fm[m2.end():].splitlines()
    for linea in tras:
        if linea.strip() and not linea.startswith(" "):
            break
        if linea.strip():
            lineas.append(linea.strip())
    return " ".join(lineas)


def fase_de(descripcion):
    if descripcion is None:
        return "AUSENTE"
    if MARCA_DESPUES in descripcion:
        return "DESPUES"
    if MARCA_ANTES in descripcion:
        return "ANTES"
    return "DESCONOCIDA"


def sello(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


def comando(frase):
    return [
        "claude",
        "-p",
        frase,
        "--output-format",
        "stream-json",
        "--verbose",
        "--max-turns",
        "2",
        "--disallowed-tools",
        SIN_ESCRITURA,
    ]


def cargo(bruto):
    """¿Se invocó la skill? Devuelve (bool, cómo se supo, coste)."""
    coste = 0.0
    via = None
    for linea in bruto.splitlines():
        linea = linea.strip()
        if not linea.startswith("{"):
            continue
        try:
            ev = json.loads(linea)
        except ValueError:
            continue
        if isinstance(ev.get("total_cost_usd"), (int, float)):
            coste += float(ev["total_cost_usd"])
        mensaje = ev.get("message") or {}
        contenido = mensaje.get("content")
        if not isinstance(contenido, list):
            continue
        for bloque in contenido:
            if not isinstance(bloque, dict) or bloque.get("type") != "tool_use":
                continue
            if "skill" not in str(bloque.get("name", "")).lower():
                continue
            if SKILL in json.dumps(bloque.get("input", {}), ensure_ascii=False):
                via = "tool_use"
    if via:
        return True, via, coste
    # Red de seguridad: si el formato de eventos cambia, el texto crudo sigue
    # delatando la carga. Se marca DISTINTO a propósito — un hallazgo que solo
    # ve la red significa que el parser de arriba se quedó atrás.
    if "<command-name>%s" % SKILL in bruto or '"skill":"%s"' % SKILL in bruto:
        return True, "texto-crudo (revisa el parser)", coste
    return False, None, coste


def corre(frase, timeout, tmp):
    try:
        p = subprocess.run(
            comando(frase),
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": "timeout de %ss" % timeout, "cargo": False, "coste": 0.0}
    if p.returncode != 0 and not p.stdout.strip():
        return {
            "error": "claude salió %d: %s" % (p.returncode, p.stderr.strip()[:300]),
            "cargo": False,
            "coste": 0.0,
        }
    ok, via, coste = cargo(p.stdout)
    return {"cargo": ok, "via": via, "coste": coste, "bruto": p.stdout}


def aplica():
    """Escribe la description nueva. Exige que exista una medición ANTES válida."""
    previas = []
    if MEDICIONES.is_dir():
        for f in sorted(MEDICIONES.glob("disparo-%s-*.json" % SKILL)):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if d.get("fase") == "ANTES" and d.get("canario") == "OK":
                previas.append(f)
    if not previas:
        print("  [BLOQUEADO] No hay medición ANTES válida en %s" % MEDICIONES)
        print("  La regla es de la propia skill: «hasta que exista esa medición,")
        print("  la description no se toca». Corre el script sin --aplicar primero.")
        return 1

def escribe_atomico(destino: Path, contenido: str) -> None:
    """Escribe `destino` entero o no lo toca. Nunca a medias.

    POR QUE (2026-08-20, auditoria) → [[bug-medir-disparo-sin-arnes]]. Esto
    reescribe una `SKILL.md` VERSIONADA. Un `write_text` directo trunca el
    fichero antes de escribirlo: si el proceso muere ahi —Ctrl-C, disco lleno,
    OOM— la skill queda partida en el arbol de trabajo, y lo que se pierde es
    el fichero que decide si esa skill dispara. Con temporal + `os.replace` el
    cambio es una operacion sola del sistema de ficheros: o esta la version
    vieja o esta la nueva.

    El temporal va en el MISMO directorio a proposito: `os.replace` solo es
    atomico dentro del mismo sistema de ficheros, y `/tmp` puede no serlo.
    """
    destino = Path(destino)
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=str(destino.parent),
                                   prefix=f".{destino.name}.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(contenido)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, destino)
        tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)                 # el fallo no deja basura al lado


def reescribe_description(texto: str, description: str) -> tuple:
    """(texto_nuevo, n) con el bloque `description: >` sustituido. n debe ser 1.

    Funcion aparte de `aplicar` para que se pueda EJERCER sin lanzar mediciones
    de pago: era el otro motivo por el que esto no tenia arnes.
    """
    cuerpo = textwrap.fill(
        description, width=78, initial_indent="  ", subsequent_indent="  ")
    # El reemplazo va por lambda y no por cadena: `re.sub` interpreta `\1` y
    # `\g<...>` en el texto de sustitucion, y aqui lo que entra es prosa del
    # usuario. Un backslash en la description no puede convertirse en un grupo.
    return re.subn(
        r"^description:\s*>\s*\n(?:[ \t]+.*\n)+",
        lambda _: "description: >\n" + cuerpo + "\n",
        texto, count=1, flags=re.M,
    )


    if len(DESCRIPTION_NUEVA) > TOPE_DESCRIPTION:
        print("  [ERROR] La description nueva mide %d caracteres, tope %d."
              % (len(DESCRIPTION_NUEVA), TOPE_DESCRIPTION))
        return 1
    if "<" in DESCRIPTION_NUEVA or ">" in DESCRIPTION_NUEVA:
        print("  [ERROR] La description nueva trae angulares: rompen la subida.")
        return 1

    texto = FUENTE.read_text(encoding="utf-8")
    nuevo, n = reescribe_description(texto, DESCRIPTION_NUEVA)
    if n != 1:
        print("  [ERROR] No reconocí el bloque `description: >` de %s" % FUENTE)
        return 1
    escribe_atomico(FUENTE, nuevo)
    print("  [OK] %s reescrita (%d caracteres, aviso a %d)."
          % (FUENTE.name, len(DESCRIPTION_NUEVA), AVISO_DESCRIPTION))
    print("  Evidencia usada: %s" % previas[-1].name)
    print()
    print("  Ahora, y en este orden:")
    print("    1. setup/sync-skills.sh        # sin esto medirías la vieja")
    print("    2. setup/scripts/py setup/scripts/medir-disparo.py")
    print("    3. setup/scripts/py setup/scripts/tests/test-skill-catalog.py")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Mide si %s carga con cada frase." % SKILL)
    ap.add_argument("--n", type=int, default=3, help="repeticiones por frase (3)")
    ap.add_argument("--timeout", type=int, default=180, help="segundos por sesión (180)")
    ap.add_argument("--seco", action="store_true", help="enseña el plan y no gasta")
    ap.add_argument("--aplicar", action="store_true", help="escribe la description nueva")
    args = ap.parse_args()

    if args.aplicar:
        return aplica()

    desc = resuelve_description(INSTALADA)
    fase = fase_de(desc)
    print("▶ Medición del disparo de `%s`" % SKILL)
    print("  Instalada: %s" % INSTALADA)
    if fase in ("AUSENTE", "DESCONOCIDA"):
        print("  Fase: %s — no pude leer la description instalada, o no reconozco" % fase)
        print("        su texto. Corre setup/sync-skills.sh y reintenta.")
    else:
        print("  Fase: %s  ·  sha256[:12]=%s  ·  %d caracteres"
              % (fase, sello(desc), len(desc)))
    print("  Sesiones: %d frases × %d repeticiones = %d"
          % (len(FRASES), args.n, len(FRASES) * args.n))

    # `--seco` se sirve ANTES de exigir la fase: no gasta nada y su trabajo es
    # dejarte ver el plan, incluso en una máquina donde la skill no está puesta.
    if args.seco:
        print()
        for f in FRASES:
            print("  [%d·%s] %s" % (f["n"], f["papel"], f["texto"]))
            print("      espera: %s — %s" % ("CARGA" if f["espera"] else "NO", f["motivo"]))
        print()
        print("  Comando por sesión (cwd = temporal fuera del repo):")
        print("    " + " ".join(comando("LA FRASE")))
        return 0

    if fase in ("AUSENTE", "DESCONOCIDA"):
        print("  [ERROR] Sin fase reconocida no hay medición que etiquetar.")
        return 2

    if not shutil.which("claude"):
        print("  [ERROR] No encuentro `claude` en el PATH.")
        return 127

    tmp = tempfile.mkdtemp(prefix="medir-disparo-")
    MEDICIONES.mkdir(parents=True, exist_ok=True)
    print("  cwd de las sesiones: %s" % tmp)
    print()

    resultados = []
    coste_total = 0.0
    canario = None
    for f in FRASES:
        cargas, errores, vias = 0, [], set()
        ultimo_bruto = ""
        for _ in range(args.n):
            r = corre(f["texto"], args.timeout, tmp)
            coste_total += r.get("coste", 0.0)
            ultimo_bruto = r.get("bruto") or ultimo_bruto
            if r.get("error"):
                errores.append(r["error"])
            if r["cargo"]:
                cargas += 1
                if r.get("via"):
                    vias.add(r["via"])
        veredicto = "?"
        if f["papel"] == "CANARIO":
            canario = "OK" if cargas == args.n else "ROTO"
            veredicto = canario
        else:
            obtuvo = cargas > 0
            if cargas in (0, args.n):
                veredicto = "COINCIDE" if obtuvo == f["espera"] else "DISCREPA"
            else:
                veredicto = "INESTABLE"
        resultados.append({
            "n": f["n"], "frase": f["texto"], "papel": f["papel"],
            "espera": f["espera"], "cargas": cargas, "de": args.n,
            "veredicto": veredicto, "vias": sorted(vias), "errores": errores,
        })
        # Un veredicto raro se mira en el flujo, no en este resumen: se guarda
        # la última sesión cruda de esa frase. Es la diferencia entre poder
        # revisar el hallazgo y tener que fiarte de quien lo cuenta.
        if veredicto in ("DISCREPA", "INESTABLE") and ultimo_bruto:
            crudo = MEDICIONES / ("crudo-%s-%s-frase%d.jsonl" % (SKILL, fase.lower(), f["n"]))
            escribe_atomico(crudo, ultimo_bruto)

        print("  [%d·%-13s] %d/%d  %-9s  %s"
              % (f["n"], f["papel"], cargas, args.n, veredicto, f["texto"][:44]))
        for e in errores[:2]:
            print("        ⚠ %s" % e)
        if f["papel"] == "CANARIO" and canario == "ROTO":
            print()
            print("  [ABORTADO] El canario no cargó la skill pidiéndola por su nombre.")
            print("  Lo roto es el ARNÉS, no el disparador: revisa que la skill esté")
            print("  instalada en %s y que los flags del CLI sigan vigentes" % INSTALADA.parent)
            print("  (`claude --help`). No hay tabla que interpretar.")
            return 2

    MEDICIONES.mkdir(parents=True, exist_ok=True)
    destino = MEDICIONES / ("disparo-%s-%s-%s.json" % (SKILL, fase.lower(), sello(desc)))
    escribe_atomico(destino, json.dumps({
        "skill": SKILL, "fase": fase, "canario": canario,
        "description_instalada": desc, "sha256_12": sello(desc),
        "n": args.n, "coste_usd": round(coste_total, 4),
        "resultados": resultados,
    }, ensure_ascii=False, indent=2))

    print()
    print("  | # | Frase | Espera | %s |" % fase)
    print("  |---|---|---|---|")
    for r in resultados:
        if r["papel"] == "CANARIO":
            continue
        print("  | %d | %s | %s | **%d/%d** |"
              % (r["n"], r["frase"], "carga" if r["espera"] else "NO",
                 r["cargas"], r["de"]))
    print()
    print("  Coste: $%.4f  ·  artefacto: %s" % (coste_total, destino))

    discrepan = [r for r in resultados if r["veredicto"] in ("DISCREPA", "INESTABLE")]
    dos = [r for r in resultados if r["n"] == 2][0]
    if fase == "ANTES":
        print("  La 2 es la discriminante: %d/%d hoy. Si el cambio sirve, sube."
              % (dos["cargas"], dos["de"]))
    else:
        print("  La 2 es la discriminante: %d/%d. Si no subió, el cambio no sirvió"
              % (dos["cargas"], dos["de"]))
        print("  y toca revertir — por bien escrito que esté.")
    if discrepan:
        print("  ⚠ %d frase(s) fuera de lo esperado: hay que mirarlas, una por una."
              % len(discrepan))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
