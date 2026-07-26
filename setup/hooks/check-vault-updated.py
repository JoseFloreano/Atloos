#!/usr/bin/env python3
"""
check-vault-updated.py — Hook Stop de Claude Code.

Capa 1 del sistema anti-drift: al terminar cada respuesta, si la sesión editó
código (flag de mark-code-dirty.py) y el _PROJECT.md del proyecto NO se
actualizó después, bloquea el cierre (exit 2) pidiendo actualizar SOLO
pendientes/estado — 2-5 líneas. Diseño anti-molestia:

  - Solo actúa si hubo edición de código en ESTA sesión.
  - Solo exige UNA vez por sesión (marca "enforced" en el flag).
  - Respeta stop_hook_active (anti-loop infinito).
  - Proyecto sin onboarding / sin vault → silencio total.
  - El ritual completo (daily note, harvest) NO es asunto de este hook:
    eso es la skill session-close ("cerramos").

Fail-open ante errores propios.
"""
import json
import os
import re
import sys

# Windows: la consola usa cp1252/cp850 y los acentos llegarían corruptos a
# Claude (mojibake). Forzamos UTF-8 en stderr; fail-open si no se puede.
try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def find_vault_project(project_name: str):
    """Busca 10-Projects/<name>/_PROJECT.md bajo OneDrive o el home (modo local)."""
    roots = []
    onedrive = os.environ.get("OneDrive") or os.environ.get("ONEDRIVE")
    if onedrive:
        roots.append(onedrive)
    home = os.path.expanduser("~")
    roots.extend([os.path.join(home, "OneDrive"), home])
    for root in roots:
        p = os.path.join(root, "DevSetup", "ObsidianVault",
                         "10-Projects", project_name, "_PROJECT.md")
        if os.path.isfile(p):
            return p
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if data.get("stop_hook_active"):
        sys.exit(0)  # ya estamos dentro de una continuación forzada — no re-bloquear

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    flag_path = os.path.join(project_dir, ".claude", "vault-dirty.json")
    if not os.path.exists(flag_path):
        sys.exit(0)

    try:
        with open(flag_path, "r", encoding="utf-8") as f:
            state = json.load(f) or {}
    except Exception:
        sys.exit(0)

    session = data.get("session_id", "")
    if state.get("session_id") != session:
        # flag huérfano de otra sesión: limpiar y salir
        try:
            os.remove(flag_path)
        except OSError:
            pass
        sys.exit(0)

    if state.get("enforced"):
        sys.exit(0)  # ya se pidió una vez en esta sesión — no ser insoportable

    # Nombre del proyecto: sección "Active Project" del CLAUDE.md, o carpeta
    name = None
    claude_md = os.path.join(project_dir, "CLAUDE.md")
    if os.path.isfile(claude_md):
        try:
            with open(claude_md, "r", encoding="utf-8", errors="ignore") as f:
                m = re.search(r"Active Project:\s*`([^`]+)`", f.read())
            if m:
                name = m.group(1).strip()
        except Exception:
            pass
    if not name or name == "<project-name>":
        name = os.path.basename(os.path.normpath(project_dir))

    project_md = find_vault_project(name)
    if not project_md:
        sys.exit(0)  # proyecto no enganchado al vault — nada que exigir

    # Satisface el hook: _PROJECT.md actualizado O una nota de sesión propia
    # (sessions/*.md) actualizada — esto último es la vía multi-agente (doc 12):
    # con 2+ agentes en el mismo proyecto, cada uno escribe SOLO su nota de
    # sesión y session-close consolida; exigir _PROJECT.md a todos convertía
    # a este hook en fuente de contención sobre un solo archivo.
    last_edit = float(state.get("last_code_edit", 0))
    try:
        satisfied = os.path.getmtime(project_md) >= last_edit
        if not satisfied:
            sessions_dir = os.path.join(os.path.dirname(project_md), "sessions")
            if os.path.isdir(sessions_dir):
                for fn in os.listdir(sessions_dir):
                    fp = os.path.join(sessions_dir, fn)
                    if fn.endswith(".md") and os.path.isfile(fp) \
                            and os.path.getmtime(fp) >= last_edit:
                        satisfied = True
                        break
        if satisfied:
            os.remove(flag_path)  # el vault ya se actualizó después del código
            sys.exit(0)
    except OSError:
        sys.exit(0)

    # Exigir (una sola vez)
    state["enforced"] = True
    try:
        with open(flag_path, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass

    print(
        f"Esta sesión modificó código pero el vault quedó desfasado. Antes de "
        f"terminar, UNA de dos: (a) actualiza SOLO Pendientes/Estado de "
        f"10-Projects/{name}/_PROJECT.md (2-5 líneas), o (b) si hay OTROS "
        f"agentes trabajando este proyecto, escribe tu avance en "
        f"10-Projects/{name}/sessions/<fecha>-<tu-tarea>.md y NO toques "
        f"_PROJECT.md (session-close consolida). Nada más.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
