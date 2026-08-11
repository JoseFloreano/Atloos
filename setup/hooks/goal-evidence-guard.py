#!/usr/bin/env python3
"""
goal-evidence-guard.py — Hook Stop de Claude Code. Capa 1 del contrato de `/goal`.

POR QUÉ EXISTE. `/goal` es un envoltorio sobre un Stop hook de tipo `prompt`, y
**su evaluador no llama a herramientas**: solo juzga lo que ya apareció en la
conversación. Es decir, cierra metas leyendo el reporte, no el artefacto — que
es exactamente lo que este setup existe para impedir (ley 1). La documentación
de Anthropic lo dice sin rodeos y recomienda escribir la condición *"como algo
que la propia salida de Claude pueda demostrar"*. Es razonable en general; aquí
no, porque un bucle autónomo amplifica lo que se le dé, y un evaluador que cree
reportes corriendo solo de noche es una máquina de acumular reportes falsos.

QUÉ HACE. Lee la meta forjada por la skill `goal-forge` en `.claude/goal.json`
y, si nombra un artefacto, comprueba contra el DISCO que existe y que es
fresco. Es el mismo contrato sha↔HEAD del `merge-gate-guard`, movido del evento
`PreToolUse` al evento `Stop`: declarar, diferir, actuar.

FAIL-OPEN, y es deliberado. Sin `.claude/goal.json`, o con una meta que no
nombra artefacto, este hook no interviene. Un guard que bloquea cierres
legítimos se desactiva en dos semanas —lección del validador de `feedback/`— y
un guard desactivado no protege nada. Solo muerde donde la meta prometió algo
comprobable.

CLÁUSULA DE CORTE PROPIA. Bloquea como mucho MAX_BLOQUEOS veces por meta. Si el
artefacto no aparece tras eso, el problema no es que falte evidencia: es que la
condición está mal forjada, y seguir bloqueando sería un bucle sin fondo. Sale
abierto diciéndolo.

QUÉ MIRA DEL ARTEFACTO, y en este orden: que exista, que **no declare rojo** si
trae un campo de veredicto (`exit_code`, `ok`, `fallos`…), y que sea fresco
(sha↔HEAD, o mtime posterior a la meta si no lleva sha). Lo del veredicto es H1
de la auditoría 21: con `gate-verde.json` existir ES el veredicto —solo se
escribe en exit 0—, pero nada obligaba a esa semántica, y un artefacto que se
escribe también en rojo cerraba la meta con la suite rota.

QUÉ NO HACE. No lee la condición de `/goal` (el payload de `Stop` no la trae:
por eso `goal-forge` la declara en un fichero). **No se inventa un veredicto que
el artefacto no declara** — por eso el contrato de `goal-forge` exige artefactos
que solo existan en verde: lo que el fichero no dice, el hook no lo adivina. Y
**no construye la capa 2** —el hook `type: "agent"`, que sí lee
disco y correría la comprobación—: es experimental por declaración de Anthropic
y la producción va en `command`. Queda nombrada, no construida.

CONVIVE CON `check-vault-updated.py`, que ya vive en `Stop`. Los dos corren; ver
`tests/test-goal-evidence-guard.py` §convivencia. El efecto que ese arnés dejó
medido —que el vecino enmudecía cuando este guard bloqueaba primero— se arbitró
como D2·b y está arreglado: hoy los dos ignoran `stop_hook_active` y cada uno se
acota con su propia cláusula de corte.
"""
import json
import os
import subprocess
import sys

META = os.path.join(".claude", "goal.json")
MAX_BLOQUEOS = 3

# Campos con los que un artefacto puede DECLARAR su veredicto. Se respeta el que
# traiga; los que no aparecen no se inventan (ver `veredicto_rojo`).
CODIGOS = ("exit_code", "returncode", "rc")          # != 0 es rojo
BANDERAS = ("ok", "verde", "passed", "success")      # False es rojo
CONTEOS = ("fallos", "failed", "errors", "failures")  # > 0 es rojo

try:
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def git_head(cwd):
    try:
        p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           timeout=10)
        return p.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def veredicto_rojo(datos):
    """Motivo si el artefacto DECLARA que el comando falló; None si no lo dice.

    Deliberadamente conservador: solo mira campos inequívocos y **no adivina**.
    Un artefacto sin veredicto pasa igual que antes — el guard no puede
    inventarse lo que el fichero no dice, y por eso el contrato de `goal-forge`
    exige artefactos que solo existan (o solo se actualicen) en verde.
    """
    if not isinstance(datos, dict):
        return None
    for k in CODIGOS:
        v = datos.get(k)
        if isinstance(v, int) and not isinstance(v, bool) and v != 0:
            return f"`{k}` vale {v}"
    for k in BANDERAS:
        if datos.get(k) is False:
            return f"`{k}` vale false"
    for k in CONTEOS:
        v = datos.get(k)
        if isinstance(v, int) and not isinstance(v, bool) and v > 0:
            return f"`{k}` vale {v}"
    return None


def bloquea(meta, ruta_meta, motivo):
    """Exit 2 con un mensaje que ENSEÑA: qué prometió la meta y qué falta."""
    meta["bloqueos"] = int(meta.get("bloqueos", 0)) + 1
    try:
        with open(ruta_meta, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    cmd = meta.get("cmd") or "(la meta no registró el comando que la prueba)"
    sys.stderr.write(
        "META NO CERRADA — falta la evidencia en disco (hook goal-evidence-guard).\n\n"
        f"{motivo}\n\n"
        f"La condición forjada fue:\n    {meta.get('condicion', '(sin registrar)')}\n\n"
        "El contrato de `/goal` en esta casa: una meta se cierra contra el\n"
        "ARTEFACTO, no contra el reporte del turno. Su evaluador solo lee la\n"
        "conversación, así que decir «los tests pasan» la cerraría; este hook\n"
        "mira el disco y no.\n\n"
        "Produce la evidencia y vuelve a terminar el turno:\n\n"
        f"    {cmd}\n\n"
        f"Si la condición está mal forjada —nombra un artefacto que ese comando\n"
        f"no escribe—, arréglala con `goal-forge` en vez de pelear con el hook.\n"
        f"(bloqueo {meta['bloqueos']} de {MAX_BLOQUEOS}; después sale abierto)\n"
    )
    sys.exit(2)


def main():
    # Sesión del daemon de Telegram: no hay humano al otro lado y bloquear
    # colgaría la respuesta del bot. Mismo criterio que check-vault-updated.
    if os.environ.get("CLAUDE_TG_BOT"):
        sys.exit(0)

    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)                   # fail-open ante entrada ilegible

    # NO se respeta `stop_hook_active` a propósito. Ese flag existe para no
    # re-bloquear en cadena, pero aquí la pregunta "¿existe ya el artefacto?"
    # tiene respuesta distinta en cada vuelta: el turno anterior pudo haberlo
    # producido. Quien acota el bucle es MAX_BLOQUEOS, no el flag.

    proyecto = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    ruta_meta = os.path.join(proyecto, META)
    if not os.path.exists(ruta_meta):
        sys.exit(0)                   # no hay meta forjada: no es asunto nuestro

    try:
        with open(ruta_meta, "r", encoding="utf-8") as f:
            meta = json.load(f) or {}
    except Exception:
        sys.exit(0)                   # fail-open: un bug del hook no tumba la sesión

    # ── La meta pertenece a la sesión que la forjó ────────────────────────
    # `/goal` es de sesión, pero este fichero no lo era: una meta forjada ayer y
    # no cumplida bloqueaba los tres primeros cierres de CUALQUIER sesión futura
    # del proyecto. `goal-forge` no puede escribir el id —no lo conoce—, así que
    # lo sella el guard en el primer turno que la ve. El gesto (comparar y
    # borrar el huérfano) es el de `check-vault-updated.py` con su flag.
    sesion = (payload or {}).get("session_id", "") if isinstance(payload, dict) else ""
    dueño = meta.get("session_id")
    if sesion:
        if not dueño:
            meta["session_id"] = sesion
            try:
                with open(ruta_meta, "w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        elif dueño != sesion:
            try:
                os.remove(ruta_meta)
            except OSError:
                pass
            sys.stderr.write(
                "goal-evidence-guard: `.claude/goal.json` era de otra sesión y se\n"
                "ha borrado. Una meta de `/goal` muere con su sesión; el fichero no\n"
                "lo hacía, y bloqueaba turnos ajenos por algo que ya no existe.\n")
            sys.exit(0)

    artefacto = meta.get("artefacto")
    if not artefacto:
        sys.exit(0)                   # meta sin artefacto: fail-open declarado

    if int(meta.get("bloqueos", 0)) >= MAX_BLOQUEOS:
        sys.stderr.write(
            f"goal-evidence-guard: la meta lleva {MAX_BLOQUEOS} bloqueos y el\n"
            f"artefacto `{artefacto}` sigue sin aparecer. Sale ABIERTO: a esta\n"
            "altura el problema no es que falte evidencia, es que la condición\n"
            "está mal forjada. Revísala con `goal-forge`.\n")
        sys.exit(0)                   # cláusula de corte del propio guard

    ruta_art = os.path.join(proyecto, artefacto)
    if not os.path.exists(ruta_art):
        bloquea(meta, ruta_meta,
                f"La meta nombra `{artefacto}` y ese fichero NO existe. Ningún\n"
                f"turno lo ha producido todavía.")

    # ── Frescura ──────────────────────────────────────────────────────────
    # Fuerte: el artefacto lleva el sha con el que se produjo (la forma que ya
    # escribe `gate-test.py`). Un verde anterior al último commit no es verde.
    datos = None
    try:
        with open(ruta_art, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except Exception:
        datos = None

    # El veredicto manda sobre la frescura: una evidencia fresquísima que dice
    # ROJO no es evidencia de nada bueno. Con `gate-verde.json` esta rama no se
    # toca (solo se escribe en exit 0), pero nada obligaba a esa semántica y sin
    # esto un artefacto escrito también en rojo cerraba la meta con la suite
    # rota — H1 de la auditoría 21.
    rojo = veredicto_rojo(datos)
    if rojo:
        bloquea(meta, ruta_meta,
                f"`{artefacto}` existe, pero DICE que el comando falló: {rojo}.\n"
                f"Una evidencia que declara rojo cierra la meta solo si nadie la\n"
                f"lee. Este hook la lee.")

    if isinstance(datos, dict) and datos.get("sha"):
        head = git_head(proyecto)
        if head and str(datos["sha"]) != head:
            bloquea(meta, ruta_meta,
                    f"`{artefacto}` registra el sha `{str(datos['sha'])[:8]}` y el\n"
                    f"HEAD es `{head[:8]}`: el repo avanzó DESPUÉS de producir la\n"
                    f"evidencia. Una evidencia anterior al último commit no es\n"
                    f"evidencia de este estado.")
        sys.exit(0)

    # Débil, y se declara como tal: el artefacto no lleva sha, así que solo se
    # puede exigir que se haya escrito DESPUÉS de forjar la meta. Impide dar
    # por buena una evidencia vieja que ya estaba ahí; no prueba de qué commit
    # es. Prefiere siempre un artefacto con sha.
    forjada = float(meta.get("forjada_ts") or 0)
    if forjada:
        try:
            if os.path.getmtime(ruta_art) < forjada:
                bloquea(meta, ruta_meta,
                        f"`{artefacto}` existe pero es ANTERIOR a la meta (escrito\n"
                        f"{int(forjada - os.path.getmtime(ruta_art))} s antes de\n"
                        f"forjarla). Es evidencia de otro trabajo, no de este.")
        except OSError:
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
