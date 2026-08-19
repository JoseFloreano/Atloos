#!/usr/bin/env python3
"""
test-razones-no-mudas.py — Una razon que solo va al log es una razon perdida.

POR QUE EXISTE (sprint 16, A3). `gitops.ensure_pr` degrada bien cuando falta
`gh` —no revienta— y devuelve `{"pr": False, "reason": "gh no esta instalado"}`.
Pero en `/merge` ese diccionario acababa aqui:

    log.warning("sin PR (%s): se intentara merge local", pr.get("reason"))

y en ningun sitio mas. El humano pedia integrar, el bot tomaba la ruta local sin
decir nada, y **no habia forma de saber por que** — el motivo existia, estaba
escrito, y moria en una maquina a la que solo se llega por SSH.

LA CLASE, que es lo que fija este arnes y no el caso del `gh`:

    donde el codigo LEE un `reason`, ese `reason` tiene que salir al chat.
    El log lo lee quien tiene SSH; el chat, quien pidio la accion.

Se barre por AST sobre el codigo real, no por lista escrita a mano: un `reason`
nuevo en un comando nuevo entra solo. Una lista seria otro contenido con dos
puntos de consumo — el mismo error que `run-tests.py` evita usando glob.

⚠ LA GRANULARIDAD ES EL ARNES. La primera version de este fichero preguntaba
«¿esta funcion manda algun reason al chat?» y **daba verde contra el codigo con
el bug**: el manejador lee cuatro razones distintas y ya respondia con otra,
que una sola respuesta tapaba el sitio mudo. Se comprobo corriendolo contra
`HEAD` antes de creerselo — y por eso ahora se mira SITIO A SITIO: cada lectura
de `reason` tiene que tener una respuesta en su propio bloque. Un arnes que no
distingue el codigo roto del arreglado no mide: decora.

LA MUTACION (caso 5) es esa comprobacion, ya permanente: se quita del codigo
real la respuesta que se anadio en este sprint y se exige que el barrido saque
un mudo NUEVO. Se pide «uno nuevo» y no un nombre de funcion para que el caso
sobreviva a que el manejador se renombre o se parta en dos.

Y el caso 3 fija la otra mitad: **una razon sin cura no es una razon util**.
`gh` ausente tiene arreglo conocido y de una linea; decirlo en el mismo mensaje
es la diferencia entre informar y dejar tirado. Va en el PRODUCTOR (`gitops`)
porque `ensure_pr` tiene dos llamadores y la cura es la misma para los dos.

NO comprueba que el texto sea bonito ni que el humano lo lea: comprueba que
exista camino del diccionario al chat.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-razones-no-mudas.py
Salidas: 0 todo verde · 1 algun caso fallo
Solo stdlib.
"""
import ast
import asyncio
import io
import os
import sys
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.normpath(os.path.join(AQUI, os.pardir))
sys.path.insert(0, BRIDGE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

results = []


def check(nombre, condicion, detalle=""):
    results.append((nombre, bool(condicion)))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle}")


def bloques(arbol):
    """(bloque, sentencia) para cada sentencia, con su lista de hermanas.

    El bloque es la unidad correcta: una razon leida dentro de un `else:` se
    responde en ESE `else:`, no en cualquier punto de la funcion. Fue el fallo
    de la primera version de este arnes.
    """
    for nodo in ast.walk(arbol):
        for campo in ("body", "orelse", "finalbody"):
            cuerpo = getattr(nodo, campo, None)
            if isinstance(cuerpo, list):
                for st in cuerpo:
                    yield cuerpo, st


def lee_reason(nodo):
    """True si el nodo consulta la clave `reason`. Las dos formas de la casa:
    `d["reason"]` y `d.get("reason")`."""
    for sub in ast.walk(nodo):
        if (isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.Constant)
                and sub.slice.value == "reason"):
            return True
        if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "get" and sub.args
                and isinstance(sub.args[0], ast.Constant)
                and sub.args[0].value == "reason"):
            return True
    return False


def responde_reason(nodo, fuente):
    """True si el nodo contiene un `reply`/`reply_doc` con el motivo dentro.

    Se mira el TEXTO del argumento porque el motivo casi siempre viaja
    interpolado en una f-string.
    """
    for sub in ast.walk(nodo):
        if not isinstance(sub, ast.Call):
            continue
        nombre = getattr(sub.func, "id", None) or getattr(sub.func, "attr", None)
        if nombre not in ("reply", "reply_doc"):
            continue
        for arg in sub.args:
            if "reason" in (ast.get_source_segment(fuente, arg) or ""):
                return True
    return False


def funcion_de(arbol, sentencia):
    """Nombre de la funcion que contiene esa sentencia (para poder senalarla)."""
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(s is sentencia for s in ast.walk(nodo)):
                return nodo.name
    return "<modulo>"


def barrer(fuente):
    """Sitios donde se lee un `reason` y NADIE lo responde en su bloque.

    Devuelve (mudos, total_de_sitios). El total sirve para que un barrido vacio
    no pueda pasar por verde.
    """
    arbol = ast.parse(fuente)
    mudos, sitios = [], 0
    for bloque, st in bloques(arbol):
        if not lee_reason(st):
            continue
        sitios += 1
        if any(responde_reason(h, fuente) for h in bloque):
            continue
        mudos.append(f"{funcion_de(arbol, st)}:{st.lineno}")
    return mudos, sitios


def mutar_quitando_respuesta(fuente, marca):
    """Quita del codigo REAL la sentencia `reply` que lleva `marca` dentro.

    Se muta la fuente que hay hoy en el repo, no una copia escrita aqui: si
    manana alguien reescribe ese bloque, el ancla deja de casar y el caso 5 se
    pone rojo en vez de aprobar en silencio.
    """
    arbol = ast.parse(fuente)
    candidatas = [seg for _b, st in bloques(arbol)
                  if marca in (seg := ast.get_source_segment(fuente, st) or "")
                  and "reply(" in seg]
    if not candidatas:
        return fuente, False
    # La MAS PEQUENA. `ast.walk` va de fuera a dentro, asi que la primera
    # coincidencia es el bloque entero: sustituirlo por `pass` se lleva tambien
    # las lecturas de `reason` y el barrido sale limpio por VACIADO, no por
    # arreglo. Mismo error de granularidad que tenia el caso 1.
    return fuente.replace(min(candidatas, key=len), "pass"), True


def stub_telegram():
    """Deja importable `tg_daemon` sin python-telegram-bot instalado."""
    tg = types.ModuleType("telegram")
    for n in ("BotCommand", "InlineKeyboardButton", "InlineKeyboardMarkup", "Update"):
        setattr(tg, n, type(n, (), {}))
    ext = types.ModuleType("telegram.ext")
    for n in ("Application", "ApplicationBuilder", "CallbackQueryHandler",
              "CommandHandler", "ContextTypes", "MessageHandler", "filters"):
        setattr(ext, n, type(n, (), {}))
    tg.ext = ext
    sys.modules.setdefault("telegram", tg)
    sys.modules.setdefault("telegram.ext", ext)


# Token con la forma real de uno de Telegram. Es de mentira, y por eso se puede
# escribir aqui: lo que se comprueba es que NO SALGA, no cual es.
TOKEN_FALSO = "123456789:AAFakeFakeFakeFakeFakeFakeFakeFakeFake"


def ejercer_on_error():
    """Corre `on_error` DE VERDAD con una excepcion que lleva el token dentro.

    Se ejecuta en vez de inspeccionarse a proposito. La auditoria 39 (§4.2)
    encontro que la propiedad critica de este arreglo —no filtrar el token— no
    la observaba nada: se podia borrar el aviso entero, o cambiar el tipo de la
    excepcion por su texto, y los dos arneses seguian en verde. Un comentario
    no es un control.

    Devuelve (mensajes_al_chat, lineas_de_log).
    """
    stub_telegram()
    import tg_daemon  # noqa: E402

    chat, logs = [], []

    async def reply_espia(_cfg, _chat_id, texto):
        chat.append(texto)

    class LogEspia:
        def error(self, fmt, *args):
            logs.append(fmt % args if args else fmt)
        def __getattr__(self, _n):
            return lambda *a, **k: None

    previos = (tg_daemon.reply, tg_daemon.log)
    tg_daemon.reply = reply_espia
    tg_daemon.log = LogEspia()
    try:
        error = RuntimeError(
            f"HTTP 400 en https://api.telegram.org/bot{TOKEN_FALSO}/sendMessage: "
            f"Bad Request: chat not found")
        contexto = types.SimpleNamespace(
            error=error, bot_data={"cfg": {"token": TOKEN_FALSO}})
        update = types.SimpleNamespace(
            effective_chat=types.SimpleNamespace(id=944659340))
        asyncio.run(tg_daemon.on_error(update, contexto))
    finally:
        tg_daemon.reply, tg_daemon.log = previos
    return chat, logs


def main():
    print("Arnes de las razones mudas (del diccionario al chat)\n")

    fuente = io.open(os.path.join(BRIDGE, "tg_daemon.py"), encoding="utf-8").read()

    # 1 — EL BARRIDO, sitio a sitio.
    mudos, sitios = barrer(fuente)
    check(f"1. los {sitios} sitios que leen un `reason` lo responden en su bloque",
          not mudos,
          f"mudos: {mudos} — el motivo existe, esta escrito, y muere en el log")

    # 2 — el barrido mira algo. Si `sitios` fuera 0 el caso 1 seria vacio y
    # verde: la trampa clasica del arnes decorativo.
    check("2. el barrido encontro sitios que mirar (no es vacio-y-verde)",
          sitios >= 5,
          f"solo {sitios} sitios: el AST dejo de casar con el codigo y el caso "
          f"1 no esta midiendo nada")

    # 3 — la razon de `gh` ausente lleva la CURA.
    gitops_src = io.open(os.path.join(BRIDGE, "gitops.py"), encoding="utf-8").read()
    arbol_g = ast.parse(gitops_src)
    ensure_pr = next((n for n in ast.walk(arbol_g)
                      if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                      and n.name == "ensure_pr"), None)
    trozo = ast.get_source_segment(gitops_src, ensure_pr) if ensure_pr else ""
    check("3. la razon de `gh` ausente dice como arreglarlo",
          ensure_pr is not None and "gh auth login" in trozo,
          "«gh no esta instalado» informa del sintoma y no del arreglo: el "
          "humano se queda sin PR y sin saber que hacer")

    # 4 — y la cura vive en `ensure_pr`, no copiada en cada llamador: dos
    # consumidores, una sola verdad. Si se duplicara, una copia se quedaria
    # atras sin diff que lo revele (la leccion del espejo de skills).
    veces = fuente.count("gh auth login") + gitops_src.count("gh auth login")
    check("4. la cura esta escrita UNA vez, en quien sabe el porque",
          veces == 1,
          f"aparece {veces} veces: si son 2+, hay dos fuentes de verdad")

    # 5 — LA MUTACION. Sin la respuesta que anadio el sprint 16, el barrido
    # TIENE que cantar `cmd_merge`. Es la comprobacion que la primera version de
    # este arnes no pasaba: daba verde contra el codigo con el bug dentro.
    mutada, aplicada = mutar_quitando_respuesta(fuente, "Sigo por la ruta local")
    check("5a. el ancla de la mutacion sigue casando con el codigo real",
          aplicada,
          "no se encontro la respuesta del `/merge` sin PR: la mutacion no se "
          "aplico y el caso 5b no mide nada")
    if aplicada:
        mudos_mut, sitios_mut = barrer(mutada)
        # Se exige un mudo NUEVO, no un nombre de funcion: asi el caso sobrevive
        # a que el manejador se renombre o se parta en dos.
        check("5b. mutacion: sin esa respuesta, el barrido canta un sitio mudo nuevo",
              set(mudos_mut) - set(mudos),
              f"el barrido siguio igual con el bug devuelto (mudos: {mudos_mut}): "
              f"no distingue el codigo roto del arreglado")
        # 5c — y la mutacion no puede haber pasado quitando las lecturas: si el
        # numero de sitios cae, lo que se probo fue un fichero mas corto.
        # La respuesta que se quita LEE un `reason`, asi que su sitio se va con
        # ella: uno menos es correcto. Mas de uno significa que la mutacion se
        # llevo el bloque entero y el 5b estaria midiendo un fichero mas corto.
        check("5c. la mutacion quito una respuesta, no un bloque entero",
              0 <= sitios - sitios_mut <= 1,
              f"sitios {sitios} -> {sitios_mut}: la mutacion vacio el bloque y "
              f"el caso 5b mediria otra cosa")

    # ── 6-8 · `on_error`: el fallo no controlado tampoco puede ser mudo, y
    # el aviso no puede convertirse en una fuga (auditoria 39, §4.2 y §4.3).
    chat, logs = ejercer_on_error()

    check("6. un fallo no controlado AVISA al chat (no solo al log)",
          len(chat) == 1,
          f"mando {len(chat)} mensajes: el humano se queda sin respuesta y sin "
          f"motivo, que es la caja negra de este sprint por el otro lado")

    check("7. y el aviso NO lleva el texto de la excepcion (ahi va el token)",
          all(TOKEN_FALSO not in m for m in chat),
          f"el token de la Bot API salio al chat: {chat}")
    if chat:
        check("7b. pero si dice QUE se rompio (el tipo, que no filtra)",
              "RuntimeError" in chat[0],
              f"aviso sin contenido util: {chat[0]!r}")

    check("8. el LOG tampoco lo filtra: va por `redact`",
          logs and all(TOKEN_FALSO not in l for l in logs),
          f"el token acabo en el journal: {logs} — y los logs se pegan en los "
          f"informes de campo")

    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos en verde")
    if fallos:
        print("FALLAN:")
        for n in fallos:
            print(f"  · {n}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
