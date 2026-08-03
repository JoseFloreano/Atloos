#!/usr/bin/env python3
"""
memory-flush.py — Hook PreCompact de Claude Code (matchers manual y auto).

Capa 3 del sistema anti-drift (R5 del `ecosistema/16`, "ahorro de tokens"): compactar es
el momento donde se pierde lo que nunca se escribió. Si la sesión editó CÓDIGO
(flag de mark-code-dirty.py) y el vault sigue desfasado, este hook devuelve el
recordatorio de volcar pendientes/decisiones ANTES de que el contexto se resuma.

Por qué BLOQUEA en vez de "inyectar contexto": PreCompact no admite
`hookSpecificOutput.additionalContext` (docs oficiales de hooks); su único canal
hacia Claude es exit 2 → stderr, y en este evento exit 2 significa "blocks
compaction". Bloquear es además lo correcto aquí: el volcado ocurre con el
contexto todavía íntegro. Se bloquea UNA sola vez por sesión (marca
`precompact_flushed` en el flag): una auto-compactación bloqueada en bucle
ahogaría la sesión cuando el contexto ya está lleno.

Silencio total (exit 0) si: no hay flag — sesión que no tocó código —, el flag
es de otra sesión, el proyecto no está enganchado al vault, el vault ya está
fresco, o ya se avisó en esta sesión.

Fail-open ante errores propios: un bug de este hook no debe impedir compactar.

Nota: `find_vault_project` y la resolución del nombre de proyecto están
duplicadas a propósito desde check-vault-updated.py — los hooks se instalan como
scripts sueltos (sync-hooks.ps1 copia archivo por archivo) y se prefiere que
cada uno corra sin depender de otro.
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


def resolve_project_name(project_dir: str) -> str:
    """Sección 'Active Project' del CLAUDE.md, o el nombre de la carpeta."""
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
    return name


def vault_is_fresh(project_md: str, last_edit: float) -> bool:
    """True si _PROJECT.md — o CUALQUIER nota de sessions/ (vía multi-agente,
    doc 12) — se actualizó después de la última edición de código."""
    if os.path.getmtime(project_md) >= last_edit:
        return True
    sessions_dir = os.path.join(os.path.dirname(project_md), "sessions")
    if os.path.isdir(sessions_dir):
        for fn in os.listdir(sessions_dir):
            fp = os.path.join(sessions_dir, fn)
            if fn.endswith(".md") and os.path.isfile(fp) \
                    and os.path.getmtime(fp) >= last_edit:
                return True
    return False


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    flag_path = os.path.join(project_dir, ".claude", "vault-dirty.json")
    if not os.path.exists(flag_path):
        sys.exit(0)  # la sesión no editó código — cero ruido

    try:
        with open(flag_path, "r", encoding="utf-8") as f:
            state = json.load(f) or {}
    except Exception:
        sys.exit(0)

    # Flag huérfano de otra sesión: no es asunto nuestro (lo limpia el hook Stop).
    if state.get("session_id") != data.get("session_id", ""):
        sys.exit(0)

    if state.get("precompact_flushed"):
        sys.exit(0)  # ya se avisó en esta sesión — no ahogar las compactaciones

    name = resolve_project_name(project_dir)
    project_md = find_vault_project(name)
    if not project_md:
        sys.exit(0)  # proyecto no enganchado al vault — nada que exigir

    try:
        if vault_is_fresh(project_md, float(state.get("last_code_edit", 0))):
            sys.exit(0)
    except OSError:
        sys.exit(0)

    # Avisar (una sola vez): marcar ANTES de bloquear, para que un fallo de
    # escritura no genere un bucle de compactaciones bloqueadas.
    state["precompact_flushed"] = True
    try:
        with open(flag_path, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        sys.exit(0)  # no pudimos marcar: mejor dejar compactar que repetir

    print(
        f"Compactación pausada una vez: esta sesión modificó código y el vault "
        f"sigue desfasado. Antes de compactar (el contexto que se pierde no "
        f"vuelve), vuelca pendientes/decisiones nuevas: (a) trabajando solo → "
        f"Pendientes/Estado de 10-Projects/{name}/_PROJECT.md (2-5 líneas), o "
        f"(b) con OTROS agentes en este proyecto → TU nota "
        f"10-Projects/{name}/sessions/<fecha>-<tu-tarea>.md y NO toques "
        f"_PROJECT.md (reglas 6-7 del multi-agente; session-close consolida). "
        f"Hecho eso, vuelve a compactar (si la compactación era automática se "
        f"reanuda sola): no se interrumpirá otra vez en esta sesión.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
