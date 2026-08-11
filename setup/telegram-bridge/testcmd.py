#!/usr/bin/env python3
"""
testcmd.py — De donde sale el comando de test que corre /test, y por tanto de
que depende el verde que /merge exige.

Vive fuera de tg_daemon.py a proposito: asi su arnes no necesita importar
python-telegram-bot. Solo stdlib.

El REPO manda sobre projects.json. projects.json es por-maquina y no viaja, asi
que si ganara el, la copia vieja de otra laptop seguiria imponiendo su verde
(en atloos era `compileall`, que no corre ni un arnes).
"""
import json
import os

METACARACTERES = ("&&", "||", "|", ";")


class ComandoInvalido(ValueError):
    """El comando declarado no se puede correr como argv sin shell."""


def _de_settings(worktree):
    """`env.GATE_TEST_CMD` del .claude/settings.json del worktree.

    Solo settings.json, nunca settings.local.json (gitignorado, por-maquina).
    Un JSON roto no puede tumbar /test: se ignora y se cae al fallback.
    """
    ruta = os.path.join(worktree or "", ".claude", "settings.json")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError):
        return ""
    if not isinstance(datos, dict):
        return ""
    env = datos.get("env")
    if not isinstance(env, dict):
        return ""
    return str(env.get("GATE_TEST_CMD", "")).strip()


def resolver(worktree, cfg_proyecto):
    """El comando de test, o "" si no hay ninguno declarado.

    worktree:      ruta del worktree de la conversacion.
    cfg_proyecto:  dict del proyecto en projects.json ({"path":..., "test":...}).

    Lanza ComandoInvalido si el comando trae operadores de shell: aqui se corre
    argv sin shell (gitops.run(cmd.split(), ...)) mientras que gate-test.py
    corre con shell=True, asi que un `&&` funcionaria en la laptop y se
    romperia en el movil con un error incomprensible.
    """
    cmd = _de_settings(worktree) or str((cfg_proyecto or {}).get("test") or "").strip()
    if not cmd:
        return ""
    for meta in METACARACTERES:
        if meta in cmd:
            raise ComandoInvalido(
                f"El comando de test declarado trae '{meta}':\n  {cmd}\n"
                f"Debe ser un ejecutable con sus argumentos, sin operadores de "
                f"shell: aqui se corre argv, sin shell. Envuelvelo en un script.")
    return cmd
