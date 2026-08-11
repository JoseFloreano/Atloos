#!/usr/bin/env python3
"""
mark-code-dirty.py — Hook PostToolUse (Write|Edit|MultiEdit) de Claude Code.

Capa 1 del sistema anti-drift del vault: cuando la sesión edita un archivo de
CÓDIGO (cualquier cosa que no sea .md), deja un flag en .claude/vault-dirty.json
y **cuenta** la edición (`edits`). El hook Stop (check-vault-updated.py) usa el
flag para exigir que los pendientes/estado del vault se actualicen antes de
terminar, y usa el contador para volver a exigirlo cada N ediciones sin
registrar — que es lo que lo mantiene vivo en una sesión de 40 turnos.

Fail-open: cualquier error → exit 0 (un bug del hook no debe romper la sesión).
"""
import json
import os
import sys
import time


def _norm(path: str) -> str:
    """Ruta comparable: absoluta, resuelta y sin diferencias de mayúsculas.

    `realpath` neutraliza symlinks y los nombres 8.3 de Windows (RUNNER~1);
    `normcase` evita que `c:\\...` y `C:\\...` — ambas formas llegan según de
    dónde venga la ruta — se lean como sitios distintos.
    """
    try:
        path = os.path.realpath(path)
    except Exception:
        path = os.path.abspath(path)
    return os.path.normcase(os.path.normpath(path))


def is_inside(file_path: str, project_dir: str) -> bool:
    """True si file_path cae dentro de project_dir."""
    p, root = _norm(file_path), _norm(project_dir)
    try:
        return os.path.commonpath([p, root]) == root
    except ValueError:
        # Unidades distintas en Windows (C: vs Z:): con seguridad, fuera.
        return False


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input") or {}
    fp = (tool_input.get("file_path") or "").replace("\\", "/")
    if not fp:
        sys.exit(0)
    # Solo código cuenta: editar .md (vault, docs, planes) no ensucia el flag.
    low = fp.lower()
    if low.endswith(".md") or "/.obsidian/" in low or "/.claude/" in low:
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    # ...y solo el código de ESTE proyecto. Sin esto, cualquier archivo no-.md
    # escrito fuera del repo (un commit-msg.txt del scratchpad, otro repo de las
    # working dirs adicionales) sellaba el flag y el hook Stop pedía actualizar
    # un vault que ya estaba al día. Un aviso que salta cuando no toca es ruido,
    # y el ruido entrena a ignorarlo.
    if not is_inside(fp, project_dir):
        sys.exit(0)

    flag_dir = os.path.join(project_dir, ".claude")
    flag_path = os.path.join(flag_dir, "vault-dirty.json")
    session = data.get("session_id", "")

    try:
        os.makedirs(flag_dir, exist_ok=True)
        state = {}
        if os.path.exists(flag_path):
            with open(flag_path, "r", encoding="utf-8") as f:
                state = json.load(f) or {}
        if state.get("session_id") != session:
            state = {}  # sesión nueva: resetea el contador y los bloqueos
        # `edits` cuenta las ediciones de código SIN REGISTRAR de esta sesión: es
        # la magnitud con la que el hook Stop mide una sesión larga (D2 del RFD
        # 18, opción b). Muere con el flag en cuanto el vault se actualiza, así
        # que no es un contador de la sesión: es el tamaño de la deuda.
        state.update({
            "session_id": session,
            "last_code_edit": time.time(),
            "edits": int(state.get("edits", 0) or 0) + 1,
        })
        with open(flag_path, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
