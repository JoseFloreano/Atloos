#!/usr/bin/env python3
"""
vaultio.py — Lectura y escritura del vault **por el daemon**, nunca por el agente.

Decisión: ADR-20260801-bot-memoria-y-perfil (vault).
El daemon es código nuestro, no un LLM: puede tocar el vault
sin abrir la puerta que T2 cerró. Dos direcciones:

- **C1b (leer)**: extracto de `_PROJECT.md` + `codebase-map.md` (curado, con su
  `updated:`) + resumen fresco de `codebase-map-snapshot.md` (D1 del RFD 10;
  el curado da señal sin garantía de edad, el snapshot da frescura), que se antepone
  al primer mensaje de cada conversación. Sustituye a las órdenes de "lee el
  vault" que el bot recibía sin poder cumplir de forma fiable.
- **C4 (escribir)**: nota de sesión en `/done`, con rama, commits y etapas.

Ojo con E1 (2026-08-01): el agente **sí puede** leer el vault desde el worktree.
La inyección no está aquí porque sea imposible leerlo, sino porque es
**determinista y acotada**: sin gastar turnos, sin depender de que encuentre la
ruta, y sin que el vault entre en su superficie de escritura.
"""
import os
import re
from datetime import date
from pathlib import Path

PROJECT_BUDGET = 2000      # chars del extracto de _PROJECT.md
MAP_BUDGET = 2000          # chars del extracto del codebase-map CURADO (presupuesto del ADR)
SNAPSHOT_BUDGET = 800      # chars del resumen del snapshot generado (D1 del RFD 10)


def vault_root() -> Path:
    """Raíz del vault: OneDrive (multi-laptop) o el home (single-laptop)."""
    candidatos = []
    od = os.environ.get("OneDrive") or os.environ.get("ONEDRIVE")
    if od:
        candidatos.append(Path(od))
    candidatos += [Path.home() / "OneDrive", Path.home()]
    for base in candidatos:
        p = base / "DevSetup" / "ObsidianVault"
        if p.is_dir():
            return p
    return Path()


def project_dir(project: str) -> Path:
    root = vault_root()
    return (root / "10-Projects" / project) if root.parts else Path()


# Secciones de _PROJECT.md por VALOR para una sesión de bot, no por orden de
# aparición. Coger los primeros 2000 chars daba "Qué es" y se quedaba sin
# presupuesto antes de "Pendientes" — justo lo que hace falta para trabajar.
PRIORIDAD = ["próximo paso", "proximo paso", "pendientes", "estado actual",
             "convenciones", "bugs", "decisiones clave", "qué es", "que es"]


def _strip_frontmatter(text: str) -> str:
    """Fuera el YAML: son metadatos del vault, no contexto para el agente."""
    text = (text or "").lstrip()
    if text.startswith("---"):
        fin = text.find("\n---", 3)
        if fin != -1:
            return text[fin + 4:].lstrip()
    return text


def _secciones(text: str) -> list:
    """[(titulo_normalizado, bloque)] a partir de los encabezados `## `."""
    trozos = re.split(r"(?m)^(?=## )", _strip_frontmatter(text))
    out = []
    for t in trozos:
        if not t.strip():
            continue
        primera = t.splitlines()[0]
        titulo = primera.lstrip("# ").strip().lower()
        out.append((titulo, t.rstrip()))
    return out


def _trim(text: str, budget: int, priorizar: bool = False) -> str:
    """Recorta por secciones enteras, nunca a mitad de línea.

    Un extracto cortado en seco desinforma más de lo que informa: mejor perder
    una sección entera y decirlo. Con `priorizar`, elige por valor (PRIORIDAD)
    en vez de por orden de aparición.
    """
    text = _strip_frontmatter(text).strip()
    if len(text) <= budget:
        return text

    secs = _secciones(text)
    if priorizar:
        def rango(par):
            titulo = par[0]
            for i, clave in enumerate(PRIORIDAD):
                if clave in titulo:
                    return i
            return len(PRIORIDAD)
        secs = sorted(secs, key=rango)

    # Las TOP_N primeras por prioridad se recortan si no caben; el resto se
    # descarta. Saltarse "Pendientes" porque es larga y meter "Qué es" porque
    # es corta invierte el criterio: mejor media sección útil que una entera
    # irrelevante.
    TOP_N = 3
    elegidas, total, omitidas = [], 0, 0
    for i, (_, bloque) in enumerate(secs):
        libre = budget - total
        if len(bloque) + 2 <= libre:
            elegidas.append(bloque)
            total += len(bloque) + 2
        elif priorizar and i < TOP_N and libre > 200:
            corte = bloque[:libre - 20].rsplit("\n", 1)[0]
            elegidas.append(corte + "\n  […]")
            total = budget
        else:
            omitidas += 1

    if not elegidas:                     # ni la sección más corta cabe
        corte = text[:budget].rsplit("\n", 1)[0]
        return corte + "\n[…recortado]"
    cola = f"\n\n[…{omitidas} sección(es) omitida(s) por presupuesto]" if omitidas else ""
    return "\n\n".join(elegidas).rstrip() + cola


def project_briefing(project: str) -> str:
    """Extracto que el daemon antepone al PRIMER mensaje de una conversación.

    Devuelve "" si no hay vault o no hay proyecto: el bot funciona igual, solo
    sin contexto previo.
    """
    d = project_dir(project)
    if not d.parts or not d.is_dir():
        return ""

    partes = []
    pm = d / "_PROJECT.md"
    if pm.is_file():
        try:
            partes.append("### Estado del proyecto (del vault)\n\n"
                          + _trim(pm.read_text(encoding="utf-8", errors="replace"),
                                  PROJECT_BUDGET, priorizar=True))
        except OSError:
            pass

    cm = d / "codebase-map.md"
    if cm.is_file():
        try:
            texto = cm.read_text(encoding="utf-8", errors="replace")
            # Se antepone su `updated:` para que el agente pese la EDAD de lo que
            # lee: el curado no tiene generador que garantice su frescura (D1).
            m = re.search(r"^updated:\s*(\S+)", texto, re.M)
            edad = f" (curado, updated: {m.group(1)})" if m else " (curado, sin fecha)"
            partes.append(f"### Mapa del codebase{edad}\n\n" + _trim(texto, MAP_BUDGET))
        except OSError:
            pass

    # D1: la frescura la aporta el snapshot del hook, no el curado. Solo se
    # añade si YA hay briefing o si el snapshot existe: la línea de ausencia es
    # un aviso útil dentro de un briefing, no una razón para fabricar uno donde
    # no lo había.
    if partes or (d / "codebase-map-snapshot.md").is_file():
        partes.append("### Snapshot del grafo\n\n" + snapshot_resumen(d))

    if not partes:
        return ""
    return ("[Contexto inyectado por el puente — extracto del vault del proyecto. "
            "Es una FOTO del momento en que abriste la conversación: si necesitas "
            "el detalle completo, pídelo. No escribas en el vault; de eso se "
            "encarga el daemon al cerrar con /done.]\n\n"
            + "\n\n".join(partes) + "\n\n---\n\n")


def snapshot_resumen(d: Path) -> str:
    """Resumen FRESCO del `codebase-map-snapshot.md` que genera el hook (D1).

    El snapshot es un volcado — en campo se midieron 111 KB. Aquí NO viaja la
    topología: viajan la cabecera de generación (fecha/sha) y la sección de
    resumen (conteo de nodos, módulos top), con tope de `SNAPSHOT_BUDGET`.

    Por qué existe: el `codebase-map.md` curado aporta señal destilada pero sin
    garantía de edad —su único escritor es humano—; el snapshot aporta frescura,
    porque el hook lo regenera en cada commit. El briefing lleva los dos, cada
    uno en su papel (D1 del RFD 10).

    Si falta, lo dice: delata de paso que el hook post-commit no está instalado,
    que es el fallo F6.
    """
    snap = d / "codebase-map-snapshot.md"
    if not snap.is_file():
        return "snapshot ausente (hook post-commit no instalado)"
    try:
        texto = snap.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "snapshot ausente (hook post-commit no instalado)"

    lineas, total = [], 0
    for linea in texto.splitlines():
        # Corta al primer encabezado de DETALLE: lo de arriba es la cabecera y
        # el resumen; lo de abajo es la topología, que no debe viajar.
        if lineas and re.match(r"^#{1,3}\s", linea) and not re.search(
                r"resumen|summary|overview|totales?|mapa", linea, re.I):
            break
        if total + len(linea) + 1 > SNAPSHOT_BUDGET:
            break
        lineas.append(linea)
        total += len(linea) + 1
    resumen = "\n".join(lineas).strip()
    return resumen or "snapshot presente pero sin sección de resumen legible"


def write_session_note(project: str, branch: str, commits: list, estado: str,
                       etapas: list, label: str = "") -> str:
    """C4 — nota de sesión al hacer /done. Devuelve la ruta escrita, o "".

    La escribe el DAEMON, no el agente: cumple el objetivo de dejar memoria sin
    darle al LLM permiso de escritura sobre el vault. Solo en `/done` — un
    `/write off` es una pausa, no un final (ADR-20260801-bot-memoria-y-perfil).
    """
    d = project_dir(project)
    if not d.parts or not d.is_dir():
        return ""
    sessions = d / "sessions"
    try:
        sessions.mkdir(exist_ok=True)
    except OSError:
        return ""

    slug = (branch.split("/")[-1] or "tarea")[:48]
    destino = sessions / f"{date.today():%Y-%m-%d}-tg-{slug}.md"
    n = 2
    while destino.exists():
        destino = sessions / f"{date.today():%Y-%m-%d}-tg-{slug}-{n}.md"
        n += 1

    lineas = [
        "---",
        f"title: \"[Telegram] {label or slug}\"",
        "tags: [session, telegram, tg-bot]",
        f"created: {date.today():%Y-%m-%d}",
        f"updated: {date.today():%Y-%m-%d}",
        f"status: {'active' if estado == 'mergeada' else 'archived'}",
        "type: session",
        f"project: {project}",
        "---",
        "",
        f"# [Telegram] {label or slug}",
        "",
        "> Nota escrita por el **daemon** del puente (no por el agente), al "
        "cerrar la conversación con `/done`.",
        "",
        f"- **Rama:** `{branch}`",
        f"- **Estado:** {estado}",
        f"- **Commits:** {len(commits)}",
    ]
    if commits:
        lineas.append("")
        lineas.append("## Commits")
        lineas += [f"- `{c}`" for c in commits[:20]]
    if etapas:
        lineas.append("")
        lineas.append("## Etapas reportadas por el agente")
        lineas += [f"- {e.lstrip('- ')}" for e in etapas[:20]]
    lineas.append("")

    try:
        destino.write_text("\n".join(lineas), encoding="utf-8")
        return str(destino)
    except OSError:
        return ""
