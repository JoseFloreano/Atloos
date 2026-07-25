#!/usr/bin/env python3
"""
validate-graphiti-group-id.py — Hook PreToolUse de Claude Code.

Fix de auditoría R2: el aislamiento de memoria por proyecto era solo una
instrucción en CLAUDE.md (probabilístico). Este hook lo vuelve DETERMINISTA:
bloquea cualquier llamada a Graphiti sin group_id/group_ids válido, antes
de que toque el grafo. "CLAUDE.md dice qué hacer; los hooks lo garantizan."

Instalación: ver hooks/README.md (copiar a ~/.claude/hooks/ + snippet en
settings.json). El hook recibe JSON por stdin; exit 2 = bloquear con mensaje.
"""
import json
import sys

# Windows: la consola usa cp1252/cp850 y los acentos llegarían corruptos a
# Claude (mojibake). Forzamos UTF-8 en stderr; fail-open si no se puede.
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

FORBIDDEN_IDS = {"", "main", "default", "<project-name>"}


def block(msg: str) -> None:
    # exit 2 = bloquea la herramienta; stderr se muestra a Claude para que corrija
    print(msg, file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # entrada ilegible: no bloquear (fail-open para no romper otras tools)

    tool = data.get("tool_name", "") or ""
    if "graphiti" not in tool.lower():
        sys.exit(0)

    tool_input = data.get("tool_input") or {}

    if "add_episode" in tool:
        gid = (tool_input.get("group_id") or "").strip()
        if gid in FORBIDDEN_IDS:
            block(
                "BLOCKED by memory-isolation hook: add_episode requiere un "
                "group_id explícito del proyecto activo (o 'dev-global' para "
                "preferencias personales). Nunca 'main', nunca vacío. "
                "Reintenta con group_id=\"<nombre-del-proyecto-activo>\"."
            )

    elif "search" in tool:  # search_facts, search_nodes, search_memory_*
        gids = tool_input.get("group_ids")
        if not gids or not isinstance(gids, list):
            block(
                "BLOCKED by memory-isolation hook: toda búsqueda en Graphiti "
                "requiere group_ids=[\"<proyecto-activo>\", \"dev-global\"]. "
                "Buscar sin filtro mezcla memoria de otros proyectos "
                "(alucinaciones cross-proyecto). Reintenta con group_ids."
            )
        bad = [g for g in gids if (g or "").strip() in FORBIDDEN_IDS]
        if bad:
            block(
                f"BLOCKED by memory-isolation hook: group_ids contiene valores "
                f"prohibidos {bad}. Usa el nombre real del proyecto activo + "
                f"'dev-global'."
            )

    sys.exit(0)


if __name__ == "__main__":
    main()
