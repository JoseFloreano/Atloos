#!/usr/bin/env python3
"""
vaultio.py — Lectura y escritura del vault **por el daemon**, nunca por el agente.

RFD 05 C1(b) y C4. El daemon es código nuestro, no un LLM: puede tocar el vault
sin abrir la puerta que T2 cerró. Dos direcciones:

- **C1b (leer)**: extracto de `_PROJECT.md` + `codebase-map.md` que se antepone
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
MAP_BUDGET = 2000          # chars del extracto de codebase-map.md (RFD 05 §6.3)


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
            partes.append("### Mapa del codebase\n\n"
                          + _trim(cm.read_text(encoding="utf-8", errors="replace"),
                                  MAP_BUDGET))
        except OSError:
            pass

    if not partes:
        return ""
    return ("[Contexto inyectado por el puente — extracto del vault del proyecto. "
            "Es una FOTO del momento en que abriste la conversación: si necesitas "
            "el detalle completo, pídelo. No escribas en el vault; de eso se "
            "encarga el daemon al cerrar con /done.]\n\n"
            + "\n\n".join(partes) + "\n\n---\n\n")


def write_session_note(project: str, branch: str, commits: list, estado: str,
                       etapas: list, label: str = "") -> str:
    """C4 — nota de sesión al hacer /done. Devuelve la ruta escrita, o "".

    La escribe el DAEMON, no el agente: cumple el objetivo de dejar memoria sin
    darle al LLM permiso de escritura sobre el vault. Solo en `/done` — un
    `/write off` es una pausa, no un final (RFD 05 §6.2).
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
