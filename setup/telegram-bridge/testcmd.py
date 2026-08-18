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
import sys

METACARACTERES = ("&&", "||", "|", ";")

# Lanzadores de Python cuyo nombre NO es portable. `py` solo existe en Windows;
# `python3` existe en Windows pero MIENTE (alias de la Microsoft Store: imprime
# "Python was not found" y no ejecuta nada). Medido el 2026-08-16 en las dos
# maquinas — misma lista y mismo motivo que `setup/scripts/gate-test.py`.
LANZADORES = ("py", "python3", "python")


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


def argv(cmd, interprete=None):
    """El comando declarado, como argv, con el lanzador de Python RESUELTO.

    POR QUE EXISTE (auditoria 31, seccion 9, items 4 y 7). `GATE_TEST_CMD` esta
    VERSIONADO a proposito —viaja entre maquinas y se ve en el diff— pero su
    primer token no es portable: este repo declara `py setup/scripts/run-tests.py`
    y en Linux `py` NO EXISTE. Aqui se corre argv SIN shell, asi que eso no era
    un mensaje raro: era `FileNotFoundError`, y sin verde `/merge` quedaba
    bloqueado por diseno justo en la maquina 24/7, que es donde el bot vive.

    Lo portable no es elegir un literal, es usar el interprete que YA esta
    ejecutando el daemon: en Windows `py` resuelve a ese mismo Python (el
    comportamiento no cambia) y en Linux deja de ser un comando imposible. Mismo
    razonamiento que `con_interprete_de_aqui` en `setup/scripts/gate-test.py`.

    Solo se toca el PRIMER token y solo si es un lanzador conocido: `pytest -q`,
    `npm test` o `flutter test` pasan intactos. Sin esa mitad, esto seria un
    secuestrador de comandos en vez de un resolutor.

    Y la resolucion vive AQUI, sobre la lista, y no sobre el string: un
    interprete con espacios en la ruta (`C:\\Program Files\\...`) sobrevive
    porque nunca se vuelve a partir. Eso es exactamente lo que rompia el
    `cmd.split()` que habia en el daemon.
    """
    partes = (cmd or "").split()
    if partes and partes[0] in LANZADORES:
        partes[0] = interprete or sys.executable or partes[0]
    return partes
