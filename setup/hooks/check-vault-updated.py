#!/usr/bin/env python3
"""
check-vault-updated.py — Hook Stop de Claude Code.

Capa 1 del sistema anti-drift: al terminar cada respuesta, si la sesión editó
código (flag de mark-code-dirty.py) y el _PROJECT.md del proyecto NO se
actualizó después, bloquea el cierre (exit 2) pidiendo actualizar SOLO
pendientes/estado — 2-5 líneas. Diseño anti-molestia:

  - Solo actúa si hubo edición de código en ESTA sesión.
  - Bloquea como mucho MAX_BLOQUEOS veces seguidas; después sale ABIERTO.
  - Tras ese corte se re-arma cada VAULT_DRIFT_EVERY ediciones sin registrar.
  - Proyecto sin onboarding / sin vault → silencio total.
  - El ritual completo (daily note, harvest) NO es asunto de este hook:
    eso es la skill session-close ("cerramos").

POR QUÉ NO ES "UNA VEZ POR SESIÓN" (D2 del RFD 18, opción b). Ese era el
contrato original y funcionaba mientras una sesión fuese media hora. Con `/goal`
y `/loop` una sesión pasa a ser 40 turnos y seis horas: el hook disparaba en el
turno 3, se marcaba hecho y se callaba las cinco horas siguientes — se apagaba
justo en el escenario que más lo necesita, trabajo autónomo sin nadie mirando.
Ahora el disparador es la CAUSA (ediciones de código sin registrar, contadas por
mark-code-dirty), no el síntoma (turnos), y por eso vuelve.

POR QUÉ YA NO SE RESPETA `stop_hook_active`. Se respetaba como anti-bucle, pero
en la práctica era una mordaza: cualquier otro hook de Stop que bloquease
primero —`goal-evidence-guard`, típicamente— dejaba este mudo el resto del
bucle. Estaba MEDIDO (caso E.3 del arnés del guard) y era la mitad de la avería
de D2. El criterio correcto ya lo tenía el hook hermano: la pregunta "¿el vault
sigue desfasado?" tiene respuesta distinta en cada vuelta —el turno anterior
pudo haberlo actualizado—, así que se evalúa siempre y quien acota el bucle es
la cláusula de corte, no el flag.

Fail-open ante errores propios.
"""
import json
import os
import re
import sys

MAX_BLOQUEOS = 3          # mismo contrato que goal-evidence-guard: tres y abre
DEFAULT_CADA = 10         # ediciones sin registrar entre re-armados

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


def cada_cuantas_ediciones() -> int:
    """N del re-armado, desde `VAULT_DRIFT_EVERY`.

    Basura o ausente → DEFAULT_CADA. `0` es la escotilla explícita al
    comportamiento viejo (exige una tanda y no vuelve). Negativo se lee como
    basura: un número inválido no puede desactivar el anti-drift en silencio.
    """
    raw = (os.environ.get("VAULT_DRIFT_EVERY") or "").strip()
    if not raw:
        return DEFAULT_CADA
    try:
        n = int(raw)
    except ValueError:
        return DEFAULT_CADA
    return n if n >= 0 else DEFAULT_CADA


def guarda(flag_path: str, state: dict) -> None:
    try:
        with open(flag_path, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass


def main() -> None:
    # Sesión del daemon de Telegram (ADR puente-telegram §7): no hay un humano
    # al otro lado para "cerrar el vault", y bloquear colgaría la respuesta del
    # bot. El cierre queda para las sesiones normales en la laptop.
    if os.environ.get("CLAUDE_TG_BOT"):
        sys.exit(0)

    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    # `stop_hook_active` se ignora a propósito — ver la cabecera. La acotación
    # del bucle la hace MAX_BLOQUEOS, que es una cuenta propia y no depende de
    # qué otro hook haya bloqueado antes.

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

    # ── Cuándo toca hablar ────────────────────────────────────────────────
    # `edits` es el tamaño de la deuda; `silenced_at` marca en qué punto de esa
    # deuda se agotó la última tanda de bloqueos. Entre las dos sale la regla:
    # se vuelve a exigir cuando la deuda ha crecido en N ediciones más.
    edits = int(state.get("edits", 1) or 1)
    cada = cada_cuantas_ediciones()
    silenced_at = state.get("silenced_at")
    if silenced_at is not None:
        if cada == 0 or edits < int(silenced_at) + cada:
            sys.exit(0)
        state["silenced_at"] = None      # re-armado: empieza tanda nueva
        state["blocks"] = 0

    bloqueos = int(state.get("blocks", 0) or 0)
    if bloqueos >= MAX_BLOQUEOS:
        state["silenced_at"] = edits
        state["blocks"] = 0
        guarda(flag_path, state)
        print(
            f"check-vault-updated: {MAX_BLOQUEOS} avisos y el vault de "
            f"{name} sigue desfasado. Sale ABIERTO — a esta altura insistir "
            f"es un bucle, no una salvaguarda. Vuelvo a avisar si se acumulan "
            f"{cada} ediciones de código más sin registrar."
            if cada else
            f"check-vault-updated: {MAX_BLOQUEOS} avisos y el vault de {name} "
            f"sigue desfasado. Sale ABIERTO y no vuelve "
            f"(VAULT_DRIFT_EVERY=0).",
            file=sys.stderr,
        )
        sys.exit(0)

    # Exigir
    state["blocks"] = bloqueos + 1
    guarda(flag_path, state)

    print(
        f"Esta sesión modificó código pero el vault quedó desfasado. Antes de "
        f"terminar, UNA de dos: (a) actualiza SOLO Pendientes/Estado de "
        f"10-Projects/{name}/_PROJECT.md (2-5 líneas), o (b) si hay OTROS "
        f"agentes trabajando este proyecto, escribe tu avance en "
        f"10-Projects/{name}/sessions/<fecha>-<tu-tarea>.md y NO toques "
        f"_PROJECT.md (session-close consolida). Nada más. "
        f"(aviso {state['blocks']} de {MAX_BLOQUEOS}; después sale abierto)",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
