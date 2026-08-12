#!/usr/bin/env python3
"""
valida-reporte.py — comprueba que un reporte de feedback cumple el contrato.

Uso:
    py feedback/_herramientas/valida-reporte.py feedback/reportes/<archivo>.md
    py feedback/_herramientas/valida-reporte.py            # valida todos

Salida: exit 0 si todo pasa, 1 si hay algún FALLO. Los AVISOS no bloquean.

POR QUÉ ESTA SEPARACIÓN. Lo que puede costar caro de verdad —una clave, un
token, un JWT— **bloquea**. Lo que es solo higiene —una ruta con tu nombre de
usuario— **avisa**. Un validador bloqueante que grita en falso se desactiva a
las dos semanas, y entonces no protege de nada.

No está cableado a ningún hook ni a CI: se corre a mano antes de guardar.
"""
import re
import sys
from pathlib import Path

# La consola de Windows es cp1252 y los símbolos del informe (✗, ·) no caben:
# sin esto, el validador REVIENTA justo cuando tiene algo que decir —pasaba
# limpio cuando todo iba bien y moría con un traceback en cuanto encontraba un
# fallo—. Es el mismo arreglo que ya llevan los arneses de `setup/`.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

CLAVES = ["tipo", "fecha", "reporter", "maquina", "so", "superficie",
          "claude_code", "setup_sha", "tarea", "veredicto", "skills_disparadas",
          "skills_existentes_que_no_dispararon", "hooks_disparados", "graphify",
          "bloqueantes", "coste_medido"]

# `setup_sha` es el commit del repo desde el que se corrió `sync-skills` en esa
# máquina. Sin él, la pregunta que decide la conclusión más importante de los
# dos reportes de campo —¿estaba `requirements-designer` instalada? ¿el fix del
# comando de test ya estaba?— NO SE PUEDE CONTESTAR. `claude_code: 2.1.227`
# fija la versión del harness y no dice nada de las skills, que es justo lo que
# el reporte está evaluando.
#
# `skills_existentes_que_no_dispararon` se llamaba `skills_que_faltaron`, y ese
# nombre mentía en la dirección peor: `[]` significaba «existía y no disparó, no
# hubo ninguna» pero se leía como «no faltó ninguna skill». En los dos reportes
# venía `[]` mientras la sección 8 decía lo contrario. Son dos preguntas
# distintas y ahora tienen dos claves distintas: esta (existe, no cargó) y
# `skills_inexistentes` (no existe, hacía falta), opcional.
#
# `coste_medido` es sí/no. No obliga a correr `/cost`, obliga a DECIR si se
# corrió: en los dos reportes de dos no se midió y el hueco pasó desapercibido
# porque no había campo donde faltara.
COSTE = {"si", "sí", "no"}

VEREDICTOS = {"sirvio", "sirvio-con-fricciones", "no-sirvio"}

# `graphify` mide si el mapa se usó — es el instrumento de campo del C1 del
# RFD 11: la instrucción cambió de forma para que se cumpliera, y hasta que
# alguien lo reporte no sabemos si funcionó.
GRAPHIFY = {"usado", "no-usado", "no-instalado"}

SECCIONES = ["1. Qué se intentó", "2. Evidencia de máquina", "3. Qué funcionó",
             "4. Qué NO funcionó", "5. Triggers", "6. Graphify",
             "7. Fricciones menores", "8. Lo que esperaba y no existe",
             "9. Confirmación del humano"]

# Bloquean: revelan un secreto reutilizable por un tercero.
SECRETOS = [
    (r"sk-[A-Za-z0-9_\-]{16,}",              "clave tipo `sk-…`"),
    (r"ghp_[A-Za-z0-9]{20,}",                "token de GitHub `ghp_…`"),
    (r"gho_[A-Za-z0-9]{20,}",                "token de GitHub `gho_…`"),
    (r"AKIA[0-9A-Z]{16}",                    "access key de AWS"),
    (r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.", "JWT"),
    (r"[?&](token|key|api_key|access_token|secret)=[^\s&)\]]+", "credencial en una URL"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "clave privada"),
]

# Avisan: higiene, no fuga reutilizable.
AVISOS = [
    (r"[A-Za-z]:\\Users\\[^\\\s`]+",          "ruta absoluta de Windows con tu usuario"),
    (r"/(?:home|Users)/[A-Za-z0-9_.\-]+/",    "ruta absoluta con tu usuario"),
    (r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", "correo electrónico"),
]

NOMBRE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)+\.md$")


def frontmatter(texto):
    """Devuelve dict del frontmatter YAML plano, o None si no hay."""
    if not texto.startswith("---\n"):
        return None
    fin = texto.find("\n---\n", 4)
    if fin == -1:
        return None
    datos = {}
    for linea in texto[4:fin].splitlines():
        if ":" in linea and not linea.startswith((" ", "\t", "#")):
            k, _, v = linea.partition(":")
            datos[k.strip()] = v.strip()
    return datos


# Marcas de "esto todavía no lo ha tocado un humano". Se buscan en la sección 9
# y son BLOQUEANTES: es el único sitio del reporte donde un hueco invalida el
# documento entero, porque sin confirmación el resto es un borrador.
#
# ⚠ `TODO` va en MAYÚSCULAS y sin `re.I` a propósito: con la bandera puesta
# cazaba la palabra española «todo», y el `_EJEMPLO.md` —cuya sección 9 dice
# *«quitó la parte donde decía que todo fue fluido»*— pasaba a rojo. Un
# validador que grita en falso se desactiva, y entonces no valida nada.
# Por lo mismo NO se buscan puntos suspensivos: un humano los escribe.
SIN_CONFIRMAR = re.compile(
    r"(?i:pendiente|por confirmar|sin rellenar|rellenar)"
    r"|\bTODO\b|<[^>\n]{1,40}>")

# Mínimo de caracteres ÚTILES en la sección 9. Dos líneas de plantilla rellenas
# de verdad pasan de largo; un `_(pendiente)_` no llega.
MINIMO_SECCION_9 = 60


def revisa_confirmacion(cuerpo):
    """La sección 9 tiene que estar confirmada por una persona, de verdad."""
    m = re.search(r"^## 9\. Confirmación del humano\s*$(.*)\Z", cuerpo,
                  re.S | re.M)
    if not m:
        return []                       # la ausencia de la sección ya la caza SECCIONES
    util = [l for l in m.group(1).splitlines()
            if l.strip() and not l.lstrip().startswith(">")]
    texto9 = "\n".join(util).strip()

    fallos = []
    if len(re.sub(r"[^\wáéíóúñÁÉÍÓÚÑ]", "", texto9)) < MINIMO_SECCION_9:
        fallos.append(
            f"la sección 9 (Confirmación del humano) tiene menos de "
            f"{MINIMO_SECCION_9} caracteres útiles: nadie la ha confirmado. "
            f"El reporte no se guarda sin el paso 5 del PROMPT.md")
    marcas = sorted({x.group(0) for x in SIN_CONFIRMAR.finditer(texto9)})
    if marcas:
        fallos.append(
            "la sección 9 sigue sin confirmar — lleva " +
            ", ".join(f"`{x}`" for x in marcas[:4]) +
            ". Un reporte sin confirmación humana es el borrador de un agente "
            "sobre su propio trabajo")
    if not re.search(r"\d{4}-\d{2}-\d{2}", texto9):
        fallos.append("la sección 9 no lleva fecha de lectura (AAAA-MM-DD)")
    return fallos


def valida(ruta):
    fallos, avisos = [], []
    crudo = ruta.read_bytes().decode("utf-8", "replace")
    texto = crudo.replace("\r\n", "\n")

    # Los ficheros que empiezan por `_` son plantilla/ejemplo: no llevan fecha.
    if not ruta.name.startswith("_") and not NOMBRE.match(ruta.name):
        fallos.append(f"el nombre no sigue AAAA-MM-DD-<maquina>-<tarea>.md: {ruta.name}")

    fm = frontmatter(texto)
    if fm is None:
        fallos.append("no tiene frontmatter YAML delimitado por `---`")
        fm = {}
    for k in CLAVES:
        if k not in fm:
            fallos.append(f"falta la clave `{k}` en el frontmatter")
    if fm.get("veredicto") and fm["veredicto"] not in VEREDICTOS:
        fallos.append(f"`veredicto: {fm['veredicto']}` no es uno de {sorted(VEREDICTOS)}")
    if fm.get("graphify") and fm["graphify"] not in GRAPHIFY:
        fallos.append(f"`graphify: {fm['graphify']}` no es uno de {sorted(GRAPHIFY)}")
    if fm.get("tarea", "").startswith("Una línea con"):
        fallos.append("`tarea` sigue siendo el texto de la plantilla")
    if fm.get("coste_medido") and fm["coste_medido"].lower() not in COSTE:
        fallos.append(f"`coste_medido: {fm['coste_medido']}` no es `si` ni `no`")
    if fm.get("coste_medido", "").lower() == "no" and \
            "no se corrió `/cost`" not in texto and "no se corrio `/cost`" not in texto:
        fallos.append("`coste_medido: no` obliga a decirlo en la sección 4: "
                      "escribe ahí por qué no se corrió `/cost` (literal: "
                      "\"no se corrió `/cost`\")")
    sha = fm.get("setup_sha", "")
    if sha and not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        fallos.append(f"`setup_sha: {sha}` no parece un sha de git — es el "
                      f"commit del repo desde el que se corrió `sync-skills`")

    cuerpo = texto[texto.find("\n---\n", 4) + 5:] if fm else texto
    for s in SECCIONES:
        if f"## {s}" not in cuerpo:
            fallos.append(f"falta la sección `## {s}`")

    # La sección 4 no puede quedar vacía: es la razón de ser del reporte.
    m = re.search(r"^## 4\. Qué NO funcionó\s*$(.*?)^## ", cuerpo,
                  re.S | re.M)
    if m:
        util = [l for l in m.group(1).splitlines()
                if l.strip() and not l.lstrip().startswith(">")]
        cuerpo4 = "\n".join(util).strip()
        if len(cuerpo4) < 40 or cuerpo4 in {"- [H] …", "- …", "-", "…"}:
            fallos.append("la sección 4 (Qué NO funcionó) está vacía o sin rellenar")
    elif "## 4. Qué NO funcionó" in cuerpo:
        fallos.append("la sección 4 no tiene una sección 5 detrás; revisa la estructura")

    # La sección 9 SIN CONFIRMAR pasaba el validador, y pasó en los dos reportes
    # de dos: llegaban con `_(pendiente)_` / `<pendiente>` y el validador daba
    # luz verde. El paso 5 del `PROMPT.md` —el humano lee y corrige— era una
    # regla escrita SIN arnés, escrita justo al lado del arnés. Un reporte sin
    # confirmar es el borrador de un agente sobre su propio trabajo, que es
    # exactamente lo que este canal existe para no ser.
    fallos.extend(revisa_confirmacion(cuerpo))

    if not re.search(r"\[(R|AR|H)\]", cuerpo):
        fallos.append("no hay ni una marca [R]/[AR]/[H] en el cuerpo")

    for patron, que in SECRETOS:
        if re.search(patron, texto):
            fallos.append(f"POSIBLE SECRETO — {que}. Quítalo antes de guardar")
    for patron, que in AVISOS:
        if re.search(patron, texto):
            avisos.append(f"{que} — sustitúyelo por `<redactado>` o por una ruta relativa al repo")

    return fallos, avisos


def main():
    raiz = Path(__file__).resolve().parent.parent / "reportes"
    if len(sys.argv) > 1:
        objetivos = [Path(a) for a in sys.argv[1:]]
    else:
        objetivos = sorted(raiz.glob("*.md")) if raiz.is_dir() else []

    if not objetivos:
        print("No hay reportes que validar en feedback/reportes/.")
        return 0

    total_fallos = 0
    for ruta in objetivos:
        if not ruta.is_file():
            print(f"[FALLO] {ruta}: no existe")
            total_fallos += 1
            continue
        fallos, avisos = valida(ruta)
        estado = "OK   " if not fallos else "FALLO"
        print(f"[{estado}] {ruta.name}")
        for f in fallos:
            print(f"         ✗ {f}")
        for a in avisos:
            print(f"         ! {a}")
        total_fallos += len(fallos)

    print(f"\n{len(objetivos)} reporte(s) · {total_fallos} fallo(s)")
    return 1 if total_fallos else 0


if __name__ == "__main__":
    sys.exit(main())
