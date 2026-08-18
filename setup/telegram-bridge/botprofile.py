#!/usr/bin/env python3
"""
botprofile.py — De donde sale el perfil recortado del bot, y por que puede
NEGARSE a usarlo.

Vive fuera de tg_daemon.py a proposito, igual que testcmd.py: asi su arnes no
necesita importar python-telegram-bot. Solo stdlib.

EL PROBLEMA QUE CIERRA (auditoria 31, H4 y seccion 9 item 6). El perfil del bot
existe para ahorrar tokens: ~15 skills en vez de ~29, unos 4-5K tokens fijos por
invocacion (ADR-20260801-bot-memoria-y-perfil). Se aplica exportando
`CLAUDE_CONFIG_DIR`. Y ahi estaba el agujero:

  - sin perfil  -> el agente usa `~/.claude`, que `sync-hooks` SI cablea -> 6 hooks
  - con perfil  -> usa otro directorio, que `sync-hooks` NO tocaba     -> 0 hooks

Es decir: **encender el ahorro de tokens apagaba la capa 3, en silencio**, y la
configuracion recomendada era la desprotegida. Medido el 2026-08-17 en la
Legion: el perfil tenia 15 skills, ninguna carpeta `hooks/` y ningun
`settings.json` — 0 de 6, confirmado, no deducido.

LAS DOS PIEZAS DEL ARREGLO:

  1. El nombre. El perfil pasa a `~/.claude-tg`, que es lo que el glob
     `~/.claude-*` de `wire-hooks.py` (y del `.ps1`) ya recorre. Sin codigo
     nuevo de cableado: el instalador que ya existe lo encuentra solo.
  2. La negativa. Si el perfil no tiene los hooks cableados, NO se usa: se cae a
     la config normal y se dice en voz alta. Perder el ahorro es barato; perder
     la vigilancia en la maquina que corre 24/7 sin humano delante, no. Falla
     CERRADO, que es la regla de esta casa.

El nombre viejo (`%LOCALAPPDATA%\\claude-tg-profile`, o `~/claude-tg-profile` en
Linux) se sigue reconociendo — pero pasa por la MISMA aduana, asi que mientras
nadie lo cablee no se usara. Se avisa para que se migre, no se rompe de golpe.
"""
import json
import os
from pathlib import Path

NOMBRE = ".claude-tg"           # bajo $HOME, para que `~/.claude-*` lo cace
NOMBRE_VIEJO = "claude-tg-profile"


def candidatos(home=None, localappdata=None):
    """Los directorios de perfil que se reconocen, en orden de preferencia.

    `home` y `localappdata` se inyectan en el arnes; en produccion salen del
    entorno. El nuevo va primero: si un dia coexisten los dos, gana el que el
    instalador de hooks sabe encontrar.
    """
    home = Path(home) if home else Path.home()
    rutas = [home / NOMBRE]
    local = localappdata if localappdata is not None else os.environ.get("LOCALAPPDATA")
    rutas.append((Path(local) if local else home) / NOMBRE_VIEJO)
    return rutas


def tiene_hooks(base) -> bool:
    """¿Ese config dir tiene hooks CABLEADOS?

    No basta con que exista la carpeta `hooks/`: los ficheros copiados sin
    entrada en `settings.json` no los ejecuta nadie — ese fue justo el fallo del
    sprint 7, un cableado que decia estar hecho y no lo estaba. Se exige la
    seccion `hooks` del settings.json y que no venga vacia.
    """
    try:
        with open(Path(base) / "settings.json", "r", encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError):
        return False
    if not isinstance(datos, dict):
        return False
    hooks = datos.get("hooks")
    return isinstance(hooks, dict) and bool(hooks)


def resolver(home=None, localappdata=None):
    """(ruta, motivo). `ruta` vacia = usa la config normal, y `motivo` dice por que.

    `motivo` nunca es None: o explica por que se usa el perfil, o explica por
    que NO se usa. Un "" mudo es como esto se volvio invisible durante T3.
    """
    for base in candidatos(home, localappdata):
        if not (base / "skills").is_dir():
            continue
        viejo = base.name == NOMBRE_VIEJO
        aviso = (f" [perfil en el nombre viejo '{base}': renombralo a "
                 f"~/{NOMBRE} para que wire-hooks lo cablee solo]") if viejo else ""

        # Un CLAUDE_CONFIG_DIR nuevo no hereda la autenticacion.
        if not (base / ".credentials.json").is_file():
            return "", (f"perfil bot en {base} sin .credentials.json: se usa la "
                        f"config normal (perder el ahorro es preferible a que no "
                        f"arranquen las invocaciones){aviso}")

        if not tiene_hooks(base):
            return "", (f"perfil bot en {base} SIN HOOKS CABLEADOS: se usa la "
                        f"config normal. El ahorro de tokens no puede apagar la "
                        f"capa 3 en la maquina que corre sin humano delante. "
                        f"Cablealo con `setup/scripts/py setup/scripts/"
                        f"wire-hooks.py` y vuelve a arrancar{aviso}")

        n = len(list((base / "skills").iterdir()))
        return str(base), f"perfil bot en {base}: {n} skills, hooks cableados{aviso}"

    return "", "sin perfil bot (no hay directorio con skills): config normal"
