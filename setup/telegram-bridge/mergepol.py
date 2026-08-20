#!/usr/bin/env python3
"""
mergepol.py — La política de la ruta PR del `/merge`. Solo stdlib.

Vive fuera de tg_daemon.py como `testcmd.py`, `botprofile.py` y `altas.py`: así
su arnés no necesita python-telegram-bot, y la decisión se puede ejercer sin
levantar un bot ni tocar un remoto.

## EL AGUJERO QUE CIERRA (leído en `gitops.merge_squash`, 2026-08-19)

Con `gh` presente, el `/merge` hacía esto **en una sola pulsación**:

    ensure_pr(...)                 -> abre el PR
    gh pr merge <rama> --squash    -> y lo integra, la línea siguiente

El PR se abría y se cerraba sin que nadie pudiera mirarlo: **no había ventana de
revisión**. Y las dos guardas del camino local —árbol en `base`, árbol limpio—
no aplican al remoto, porque el merge por PR ocurre allí a propósito.

**Hoy eso está contenido POR ACCIDENTE**: `gh` no está instalado en la SER8, así
que la ruta ni se toma. Pero la contención es la AUSENCIA DE UN BINARIO: un
`apt install` de cualquier cosa que arrastre `gh` cambia la ruta en silencio, en
la máquina 24/7, sin que nadie lo pida. La firma B1 decidió no instalarlo
([[ADR-20260819-gh-fuera-del-puente]]); lo que faltaba era **la guarda que lo
hiciera explícito**, y es esto.

## Los tres modos

| `CLAUDE_TG_PR_MERGE` | Qué hace | Cuándo |
|---|---|---|
| `ventana` *(por defecto)* | Integra por PR **solo si el PR ya existía** antes de la pulsación. Si lo acaba de abrir el puente, lo deja abierto y pide un segundo `/merge` | Siempre, salvo que decidas otra cosa |
| `off` | El puente **nunca** integra por PR: lo abre, lo publica y ahí lo deja | Si quieres que main solo se toque desde la laptop |
| `auto` | El comportamiento viejo: abrir e integrar de una | Solo si lo eliges **por escrito**; el daemon lo dice al arrancar y en cada merge |

La ventana no es un retardo simbólico: entre la primera pulsación y la segunda
el PR **existe, está publicado y se puede mirar desde el móvil**, que es
justamente lo que no había. Y el verde sigue vigente mientras no llegue otro
commit, así que el coste de la segunda pulsación es una pulsación.

⚠ Esto gobierna SOLO la ruta PR. Sin `gh` no hay PR, el merge va por la ruta
local y ahí siguen mandando sus dos guardas (árbol en `base` y árbol limpio),
que son las que este módulo NO puede sustituir.
"""
import os

VAR = "CLAUDE_TG_PR_MERGE"
MODOS = ("ventana", "off", "auto")
POR_DEFECTO = "ventana"


def modo(entorno=None) -> tuple:
    """(modo, motivo). Nunca lanza y nunca devuelve un motivo vacío.

    DOS REGLAS, y la segunda la escribió su propio arnés (2026-08-19):

    1. **Sin declarar → `ventana`.** Es el default, y se anuncia igual: este
       módulo nace de una contención que nadie había declarado, así que un
       default mudo repetiría el fallo con otra cara.
    2. **Valor que no entiendo → `off`, el modo MÁS restrictivo.** No `ventana`.
       La primera versión hacía `.lower()` y caía al default, y el arnés enseñó
       las dos mitades del problema: `Auto` acababa abriendo la ruta permisiva
       desde una variable que nadie había validado, y un `offf` mal tecleado
       daba MENOS restricción de la que su autor quiso. Con esto, escribir mal
       la variable nunca concede más permiso que escribirla bien: falla cerrado
       y con el valor crudo delante para que se pueda corregir.

    La comparación sí ignora mayúsculas y espacios (`  OFF ` es `off`): eso no
    es adivinar, es la misma palabra. Lo que no se adivina es una palabra que no
    está en la lista.
    """
    env = os.environ if entorno is None else entorno
    crudo = str(env.get(VAR, ""))
    normal = crudo.strip().lower()
    if not normal:
        return POR_DEFECTO, (f"{VAR} sin declarar: ruta PR con ventana de revisión "
                             f"(no integro un PR recién abierto)")
    if normal not in MODOS:
        return "off", (f"{VAR}={crudo!r} no es un modo válido "
                       f"({', '.join(MODOS)}): NO integro por la ruta PR hasta que "
                       f"la variable diga algo que se entienda.")
    return normal, f"{VAR}={normal}"


def aplica(pr_url, gh_presente) -> bool:
    """¿Gobierna esta política ESTE merge? Solo si la ruta PR se va a tomar.

    Salió de auditar el cableado (2026-08-19): la guarda miraba solo `pr_url`, y
    `gitops.merge_squash` toma la ruta PR únicamente si hay **URL y `gh`**. Con
    una `pr_url` vieja en el estado y `gh` desinstalado, el merge se iba por la
    ruta LOCAL y aun así lo habría bloqueado un `off` — bloquear de más también
    es un fallo: enseña a desconfiar de la guarda, y una guarda en la que no se
    confía se apaga.

    El camino local no queda a la intemperie: tiene sus propias dos guardas
    (árbol en `base`, árbol limpio), que son las que esta política no sustituye.
    """
    return bool(pr_url) and bool(gh_presente)


def decidir(modo_actual: str, pr_creado_ahora: bool) -> dict:
    """¿Se integra este PR en esta pulsación? -> {integrar, motivo}.

    `pr_creado_ahora` es lo único que distingue "el PR llevaba abierto desde el
    `/push` de antes" de "lo acabo de abrir yo hace medio segundo". Sale de
    `gitops.ensure_pr`, que ya devolvía `created` y no lo miraba nadie.

    El motivo va redactado para el CHAT: el que pulsa el botón es quien tiene
    que entender por qué su merge se paró, y un log en la SER8 no lo lee nadie
    a las once de la noche.
    """
    if modo_actual == "off":
        return {"integrar": False,
                "motivo": (f"la ruta PR está desactivada ({VAR}=off): el PR queda "
                           f"abierto y publicado, y lo integras tú desde la laptop "
                           f"o desde GitHub.")}
    if modo_actual == "auto":
        return {"integrar": True,
                "motivo": (f"{VAR}=auto: integro el PR en la misma pulsación, sin "
                           f"ventana de revisión (elegido explícitamente).")}
    # ventana
    if pr_creado_ahora:
        return {"integrar": False,
                "motivo": ("acabo de abrir el PR en esta misma pulsación, así que "
                           "no lo integro sin que puedas verlo. Míralo y vuelve a "
                           "lanzar /merge: el verde sigue vigente mientras no "
                           "llegue otro commit.")}
    return {"integrar": True,
            "motivo": "el PR ya existía antes de esta pulsación (hubo ventana de revisión)."}
