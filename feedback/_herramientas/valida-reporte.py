#!/usr/bin/env python3
"""
valida-reporte.py — comprueba que un reporte de feedback cumple el contrato.

Uso:
    setup/scripts/py feedback/_herramientas/valida-reporte.py feedback/reportes/<archivo>.md
    setup/scripts/py feedback/_herramientas/valida-reporte.py            # valida todos

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

# ── LA VERSIÓN DEL CONTRATO ──────────────────────────────────────────────────
#
# POR QUÉ EXISTE. El contrato de este canal se endureció tres veces —`setup_sha`,
# `coste_medido`, `skills_existentes_que_no_dispararon`, y ahora las dos mitades
# de la sección 4— y cada vez se aplicó **hacia atrás**. Resultado medido en el
# sprint 5: los cuatro reportes de campo que existen fallan el validador, y los
# del 08-10 y 08-11 **no pueden pasar nunca**, porque les faltan claves que se
# inventaron después de que se escribieran.
#
#   **Un canal que endurece su contrato retroactivamente no puede archivar su
#   propia historia.** Y un canal cuyo archivo está vacío no es un canal.
#
# CÓMO. El reporte declara qué contrato cumple. Si no lo declara, es de antes de
# que esto existiera y por tanto **es v1 por omisión** — así los cuatro reportes
# viejos quedan bien clasificados sin tocarles una línea, que es la propiedad que
# hace honesto el arreglo: no se reescribe la historia, se fecha.
FORMATO_ACTUAL = 3
FORMATO_POR_OMISION = 1

# El día en que la v2 entró. Un reporte con fecha POSTERIOR que declare v1 no
# está archivando historia: está esquivando el contrato, y se bloquea aunque el
# fichero diga 1.
#
# ⚠ ESTRICTAMENTE POSTERIOR, no "posterior o igual". El propio día es ambiguo —
# el reporte del 08-14 se escribió esa mañana, horas antes de que la v2
# existiera— y tratarlo como v2 sería aplicar el contrato hacia atrás por unas
# horas: exactamente el defecto que esta versión existe para quitar, cometido en
# el mismo fichero que lo arregla. La duda de un día se resuelve a favor del
# reporte; el que venga mañana ya no tiene excusa.
FECHA_V2 = "2026-08-14"

# La v3 entró el 2026-08-16 y añade DOS campos: `nucleos` y `ram_gb`.
#
# POR QUÉ, y es la causa raíz de un número que cruzó cuatro sprints. La sección
# 2 se titula «Evidencia de máquina» y pedía la versión del harness, el sha de
# git, el estado del árbol y el sha del setup — **ni una sola propiedad de la
# MÁQUINA**. Ni núcleos ni RAM.
#
# Consecuencia medida: el ×2,05 que gobierna el techo de frentes de
# `workstream-dispatch` se midió el 2026-08-10 en la máquina `ProgramadoMaxi2`,
# y **nadie puede decir de cuántos núcleos**. Encima de ese hueco se construyó
# un presupuesto «para 8 núcleos» que no era de esa máquina ni de esta (que
# tiene 24), y sobrevivió a cuatro sprints y ocho ficheros porque no había
# campo donde faltara. Un número de tiempo sin el tamaño de la máquina que lo
# produjo no es una medición: es una anécdota que viaja.
FECHA_V3 = "2026-08-16"

# El día en que entró cada versión, para que `version_de` no tenga que saberse
# los nombres. Escrito como tabla y no como cadena de `if` porque la v4 llegará.
ENTRADA = {2: FECHA_V2, 3: FECHA_V3}

# Claves comunes a todas las versiones.
CLAVES_V1 = ["tipo", "fecha", "reporter", "maquina", "so", "superficie",
             "claude_code", "tarea", "veredicto", "skills_disparadas",
             "hooks_disparados", "graphify", "bloqueantes"]

# Lo que añadió la v2. `skills_que_faltaron` era el nombre viejo de
# `skills_existentes_que_no_dispararon` y mentía en la dirección peor, así que
# en v1 no se exige ninguno de los dos: exigir el nombre nuevo a un reporte que
# usó el viejo es pedirle que adivinara el futuro.
CLAVES_V2 = ["setup_sha", "skills_existentes_que_no_dispararon", "coste_medido",
             "formato"]

# Lo que añadió la v3: el TAMAÑO de la máquina. `maquina:` ya decía CUÁL era
# —`ProgramadoMaxi2`, y eso siempre constó—; lo que no constaba, y es lo que
# hace atribuible una cifra de tiempo, es cuánta máquina había debajo.
CLAVES_V3 = ["nucleos", "ram_gb"]


def claves_de(version):
    return (CLAVES_V1
            + (CLAVES_V2 if version >= 2 else [])
            + (CLAVES_V3 if version >= 3 else []))


CLAVES = CLAVES_V1 + CLAVES_V2 + CLAVES_V3   # el contrato de hoy

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

# SIGUEN SIENDO NUEVE. La 4 se partió en `4a`/`4b` sin renumerar nada a
# propósito: «la sección 9» se cita en el vault, en tres encargos y en los
# mensajes de este mismo fichero. Renumerar rompe un vocabulario compartido, y
# eso cuesta más que el orden — el mismo argumento por el que el check de 1024
# se quedó de cuarto aunque bloquee.
SECCIONES = ["1. Qué se intentó", "2. Evidencia de máquina", "3. Qué funcionó",
             "4. Qué NO funcionó", "5. Triggers", "6. Graphify",
             "7. Fricciones menores", "8. Lo que esperaba y no existe",
             "9. Confirmación del humano"]

# Subsecciones que añade la v2. Van como `###`, dentro de la 4.
SUBSECCIONES_V2 = ["4a · El setup", "4b · Yo, el agente"]

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
#
# ⚠ `&lt;…&gt;` va al lado de `<…>` porque el hueco ESCAPADO se coló en campo
# (sprint 5, 2026-08-14). El reporte del 08-13 llegó con
# `**&lt;falta el alias&gt;**` en la línea de "Leído y corregido por", y el
# validador lo dio por confirmado: el patrón `<[^>\n]{1,40}>` no ve un marcador
# HTML-escapado, y ese reporte se escribió en un editor que escapa. Lo bloqueaba
# otra cosa —`setup_sha: no-disponible`—, así que el hueco del check ni se notó:
# el arnés acertó el veredicto por una razón que no era la suya. Es la misma
# forma que H7 (el tope que vivía dentro de una cadena) con otro disfraz.
SIN_CONFIRMAR = re.compile(
    r"(?i:pendiente|por confirmar|sin rellenar|rellenar)"
    r"|\bTODO\b|<[^>\n]{1,40}>|&lt;[^&\n]{1,40}&gt;")

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


MINIMO_4B = 80      # caracteres útiles. Más que la 9 (60): «me equivoqué» no vale


def revisa_4b(cuerpo):
    """La 4b tiene que estar escrita, y con marca. Solo en v2.

    Mismo criterio que la sección 9 y por el mismo motivo: es la mitad que se
    queda sin escribir si no se le exige. Y se le exige marca porque **una
    confesión sin marca es una opinión** — la regla `[R]/[AR]/[H]` ya rige en
    todo el documento, pero aquí es donde más barato sale saltársela.

    ⚠ Se corta en la sección 5, no en el final del fichero: sin eso, cualquier
    marca del resto del reporte contaría como si estuviera en la 4b.
    """
    m = re.search(r"^###\s*4b[^\n]*$(.*?)(?=^##\s|\Z)", cuerpo, re.S | re.M)
    if not m:
        return []          # su ausencia ya la canta el bucle de SUBSECCIONES_V2
    util = [l for l in m.group(1).splitlines()
            if l.strip() and not l.lstrip().startswith(">")]
    texto = "\n".join(util).strip()

    fallos = []
    if len(re.sub(r"[^\wáéíóúñÁÉÍÓÚÑ]", "", texto)) < MINIMO_4B:
        fallos.append(
            f"la sección 4b tiene menos de {MINIMO_4B} caracteres útiles: no "
            f"está escrita. Si de verdad no encontraste ningún fallo propio, "
            f"dilo Y di qué buscaste — «ninguno» sin método es lo mismo que no "
            f"haber mirado")
    marcas = sorted({x.group(0) for x in SIN_CONFIRMAR.finditer(texto)})
    if marcas:
        fallos.append(
            "la sección 4b sigue con texto de plantilla — lleva " +
            ", ".join(f"`{x}`" for x in marcas[:4]))
    if not re.search(r"\[(R|AR|H)\]", texto):
        fallos.append("la sección 4b no lleva ni una marca [R]/[AR]/[H]: una "
                      "confesión sin marca es una opinión")
    return fallos


def version_de(fm, ruta):
    """(version_efectiva, declarada, motivo_del_ajuste).

    Sin `formato:` el reporte es de antes de que la versión existiera → v1.
    Pero declarar v1 con fecha posterior a la v2 no es historia: es esquivar el
    contrato, y entonces se exige v2 igualmente.
    """
    crudo = (fm.get("formato") or "").strip()
    if not crudo:
        declarada = FORMATO_POR_OMISION
    else:
        try:
            declarada = int(crudo)
        except ValueError:
            return FORMATO_ACTUAL, crudo, (
                f"`formato: {crudo}` no es un número; se exige el contrato "
                f"v{FORMATO_ACTUAL}")
    fecha = (fm.get("fecha") or "").strip()
    # Se busca la versión MÁS ALTA cuya fecha de entrada ya haya pasado: un
    # reporte escrito hoy no puede acogerse al contrato de anteayer. Sigue
    # siendo ESTRICTAMENTE POSTERIOR — la duda de un día se resuelve a favor del
    # reporte, por el mismo motivo que se escribió para la v2.
    if declarada < FORMATO_ACTUAL and fecha:
        exigible = max((v for v, d in ENTRADA.items() if fecha > d), default=0)
        if exigible > declarada:
            return exigible, declarada, (
                f"el reporte declara `formato: {declarada}` pero su `fecha: "
                f"{fecha}` es POSTERIOR al {ENTRADA[exigible]}, el día en que "
                f"entró la v{exigible}. La versión existe para que los reportes "
                f"VIEJOS se puedan archivar, no para escribir nuevos con el "
                f"contrato viejo: se exige v{exigible}")
    return declarada, declarada, ""


def valida(ruta):
    fallos, avisos = [], []
    # El BOM se quita antes de nada. `Set-Content -Encoding UTF8` de PowerShell
    # 5.1 lo escribe SIEMPRE, así que un reporte guardado desde PowerShell —lo
    # normal en esta máquina— llegaba con `﻿` delante del `---` y el
    # validador respondía "no tiene frontmatter YAML" seguido de 16 claves que
    # faltaban. Un diagnóstico falso y aterrador para un fichero correcto.
    # Encontrado al probar este mismo cambio: mi propio instrumento lo produjo.
    crudo = ruta.read_bytes().decode("utf-8", "replace").lstrip("﻿")
    texto = crudo.replace("\r\n", "\n")

    # Los ficheros que empiezan por `_` son plantilla/ejemplo: no llevan fecha.
    if not ruta.name.startswith("_") and not NOMBRE.match(ruta.name):
        fallos.append(f"el nombre no sigue AAAA-MM-DD-<maquina>-<tarea>.md: {ruta.name}")

    fm = frontmatter(texto)
    if fm is None:
        fallos.append("no tiene frontmatter YAML delimitado por `---`")
        fm = {}

    version, declarada, ajuste = version_de(fm, ruta)
    if ajuste:
        fallos.append(ajuste)
    for k in claves_de(version):
        if k not in fm:
            fallos.append(f"falta la clave `{k}` en el frontmatter"
                          + (f" (contrato v{version})" if version >= 2 else ""))
    if fm.get("veredicto") and fm["veredicto"] not in VEREDICTOS:
        fallos.append(f"`veredicto: {fm['veredicto']}` no es uno de {sorted(VEREDICTOS)}")
    if fm.get("graphify") and fm["graphify"] not in GRAPHIFY:
        fallos.append(f"`graphify: {fm['graphify']}` no es uno de {sorted(GRAPHIFY)}")
    if fm.get("tarea", "").startswith("Una línea con"):
        fallos.append("`tarea` sigue siendo el texto de la plantilla")
    # v3 · el tamaño de la máquina. Se exige NÚMERO, no texto: `no-disponible`
    # es exactamente la respuesta que dejó el ×2,05 sin atribuir, y aquí el dato
    # cuesta un comando de una línea que está escrito en la sección 2. Un campo
    # que acepta cualquier valor no está eligiendo nada (la lección del bloque 5
    # de `plantilla-despacho.md`, con otro disfraz).
    if version >= 3:
        for clave, unidad in (("nucleos", "núcleos"), ("ram_gb", "GB de RAM")):
            crudo = str(fm.get(clave, "")).strip()
            if not crudo:
                continue                   # ya lo reportó el bucle de claves
            try:
                valor = float(crudo.replace(",", "."))
            except ValueError:
                fallos.append(
                    f"`{clave}: {crudo}` no es un número. Es el tamaño de la "
                    f"máquina en {unidad}, y sin él una cifra de tiempo no se "
                    f"puede atribuir — así es como el ×2,05 cruzó cuatro "
                    f"sprints.\n           Sácalo literal, sección 2:\n"
                    f"             py -c \"import os; print(os.cpu_count())\"")
                continue
            if valor <= 0:
                fallos.append(f"`{clave}: {crudo}` tiene que ser mayor que 0")
    if version >= 2 and fm.get("coste_medido") and fm["coste_medido"].lower() not in COSTE:
        fallos.append(f"`coste_medido: {fm['coste_medido']}` no es `si` ni `no`")
    if version >= 2 and fm.get("coste_medido", "").lower() == "no" and \
            "no se corrió `/cost`" not in texto and "no se corrio `/cost`" not in texto:
        fallos.append("`coste_medido: no` obliga a decirlo en la sección 4a: "
                      "escribe ahí por qué no se corrió `/cost` (literal: "
                      "\"no se corrió `/cost`\")")
    # `setup_sha` volvió `no-disponible` en el reporte del 08-13, y con razón: se
    # pedía un `git rev-parse` de `~/.claude/`, que no es un repo git. El campo
    # era infalsificable POR DISEÑO. Ahora lo escribe `sync-skills` al desplegar,
    # así que el validador puede decir DÓNDE está en vez de aceptar el hueco en
    # silencio — que es lo que hacía: solo comprobaba el formato.
    # El `+` final es la marca de "desplegado desde un árbol sucio" (PROMPT.md).
    #
    # ⚠ SOLO EN v2, y por la misma razón que las claves: bajo v1 este campo no
    # existía en el contrato, y `no-disponible` era la respuesta HONESTA de la
    # época —se pedía un `git rev-parse` de `~/.claude/`, que no es un repo—.
    # Exigirle formato a una clave que su contrato no pedía es aplicar el
    # contrato de hoy hacia atrás, que es justo lo que la versión quita. La
    # regla general, sin casos especiales: **una clave de v2 se valida bajo v2.**
    sha = fm.get("setup_sha", "") if version >= 2 else ""
    if sha and not re.fullmatch(r"[0-9a-f]{7,40}\+?", sha):
        detalle = (f"`setup_sha: {sha}` no parece un sha de git — es el commit "
                   f"del repo desde el que se corrió `sync-skills`.")
        if sha.lower() in {"no-disponible", "no disponible", "n/a", "-", "?"}:
            detalle = (f"`setup_sha: {sha}` ya no vale: desde el sprint 3 el sha "
                       f"lo escribe `sync-skills` al desplegar.")
        fallos.append(
            detalle + "\n           Sácalo de ahí, literal:\n"
            "             Windows: Get-Content "
            "\"$env:USERPROFILE\\.claude\\skills\\.sync-manifest.json\"\n"
            "             Linux:   cat ~/.claude/skills/.sync-manifest.json\n"
            "           Si ese JSON trae \"dirty\": true, escribe el sha con un "
            "`+` detrás.\n"
            "           Si el fichero no existe, esa máquina no ha corrido "
            "`sync-skills` con\n           esta versión: córrelo antes de "
            "reportar.")

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

    # LO QUE SÍ DEPENDE DE LA VERSIÓN: las dos mitades de la sección 4. Un
    # reporte v1 se escribió cuando la 4 era una sola, así que exigírselas sería
    # el defecto que la versión existe para arreglar, cometido en el mismo
    # commit que la introduce.
    if version >= 2:
        for s in SUBSECCIONES_V2:
            if f"### {s}" not in cuerpo:
                fallos.append(f"falta la subsección `### {s}` (contrato v2)")
        fallos.extend(revisa_4b(cuerpo))

    # LO QUE NO DEPENDE DE LA VERSIÓN, y por eso va fuera del `if`: los
    # secretos, la sección 9 confirmada por un humano (arriba) y las marcas.
    # Eso no es contrato de formato — es la razón de existir del canal, y
    # dejarlo pasar por ser "de otra época" vaciaría la versión de sentido.
    if not re.search(r"\[(R|AR|H)\]", cuerpo):
        fallos.append("no hay ni una marca [R]/[AR]/[H] en el cuerpo")

    for patron, que in SECRETOS:
        if re.search(patron, texto):
            fallos.append(f"POSIBLE SECRETO — {que}. Quítalo antes de guardar")
    for patron, que in AVISOS:
        if re.search(patron, texto):
            avisos.append(f"{que} — sustitúyelo por `<redactado>` o por una ruta relativa al repo")

    return fallos, avisos, version


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
        fallos, avisos, version = valida(ruta)
        # LA VERSIÓN SE ENSEÑA SIEMPRE, y en el verde más que en el rojo: un
        # `[OK]` a secas sobre un reporte v1 se lee como "cumple el contrato de
        # hoy", y no lo cumple — cumple el suyo. Ese malentendido es barato de
        # evitar aquí y caro de deshacer dentro de dos meses.
        estado = (f"OK v{version}" if not fallos else "FALLO ").ljust(6)
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
