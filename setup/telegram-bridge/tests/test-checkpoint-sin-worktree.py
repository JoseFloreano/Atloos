#!/usr/bin/env python3
"""
test-checkpoint-sin-worktree.py — El checkpoint tiene que disparar SIN worktree.

POR QUE EXISTE (sprint 16, 2026-08-18). El humano lo reporto asi: «el timeout de
10 min, ya no esta el msg en live del proceso, es una caja negra al respecto».
Los tres sintomas eran UN solo defecto, y estaba en una palabra del bucle del
monitor:

    if worktree and not live and now_ts() - ultimo_checkpoint >= CHECKPOINT_EVERY:

En modo lectura NO HAY worktree. Asi que el checkpoint —cuyo propio comentario
lo llamaba «superviviente para tareas MUY largas sin panel»— quedaba excluido
justo del unico modo que no tiene otra red:

  · el panel esta APAGADO por defecto (`/progress live` es opt-in);
  · `SILENCE_ALERT` solo salta cuando el stream se CALLA, y una tarea que
    trabaja de verdad emite eventos, asi que no saltaba nada;
  · y el checkpoint no se disparaba.

Resultado medido en la SER8 el 2026-08-18: una lectura mando CERO mensajes
durante diez minutos hasta que el techo la mato
(`11:36:42 invocando claude` → `11:46:42 La tarea supero 10 minutos`).

EL INVARIANTE QUE ESTE ARNES FIJA, que no es el caso concreto:

    una invocacion que dura mas que su cadencia de checkpoint manda al menos
    un mensaje, TENGA O NO worktree.

Y el segundo, que es el que impide que el numero vuelva a caducar:

    bajo el techo de CADA modo tiene que caber mas de un checkpoint.

Ese es el fallo real del `CHECKPOINT_EVERY = 1800` con `READ_TIMEOUT = 600`:
30 min de cadencia dentro de 10 de vida. Un numero absoluto al lado de un techo
variable caduca solo; por eso ahora la cadencia es una FRACCION del techo y lo
que se comprueba es la relacion, no la cifra.

LA MUTACION (casos 5 y 6) es la mitad que importa. Se toma el codigo REAL de
`monitor_loop`, se le devuelve la guarda vieja por sustitucion de texto y se
ejerce el mismo escenario: sin worktree tiene que mandar CERO. Sin ese caso,
el caso 3 podria estar pasando porque el arnes manda mensajes por su cuenta, y
la guarda volveria en tres sprints sin que nadie se enterara. El caso 6 es el
anti-artefacto: el MISMO mutante CON worktree si manda, luego el cero del 5 es
la guarda y no la fontaneria del arnes rota.

No comprueba que el texto del checkpoint guste, ni el intervalo exacto en
segundos: comprueba que salga, que caiga a la ultima accion cuando no hay etapa,
y que la cadencia quepa bajo el techo.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-checkpoint-sin-worktree.py
Salidas: 0 todo verde · 1 algun caso fallo
Solo stdlib: se stubea `telegram` para importar el codigo REAL en vez de copiarlo.
"""
import asyncio
import inspect
import io
import os
import re
import sys
import tempfile
import textwrap
import types

AQUI = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.normpath(os.path.join(AQUI, os.pardir))
sys.path.insert(0, BRIDGE)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def stub_telegram():
    """Deja importable `tg_daemon` sin python-telegram-bot instalado.

    Mismo motivo que en `test-deny-separador.py`: un arnes que solo corre donde
    estan las dependencias del daemon no corre en la otra laptop ni en CI.
    """
    nombres = ("BotCommand", "InlineKeyboardButton", "InlineKeyboardMarkup", "Update")
    tg = types.ModuleType("telegram")
    for n in nombres:
        setattr(tg, n, type(n, (), {}))
    ext = types.ModuleType("telegram.ext")
    for n in ("Application", "ApplicationBuilder", "CallbackQueryHandler",
              "CommandHandler", "ContextTypes", "MessageHandler", "filters"):
        setattr(ext, n, type(n, (), {}))
    tg.ext = ext
    sys.modules.setdefault("telegram", tg)
    sys.modules.setdefault("telegram.ext", ext)


stub_telegram()
import tg_daemon                       # noqa: E402
from progress import ProgressTracker    # noqa: E402

results = []


def check(nombre, condicion, detalle=""):
    results.append((nombre, bool(condicion)))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle}")


# ── Banco de pruebas del bucle ────────────────────────────────────────────
#
# El reloj es falso y lo mueve el propio `sleep`: asi 10 minutos simulados
# cuestan milisegundos y el arnes no depende de esperar de verdad. Se sustituye
# `now_ts` (que es lo que el bucle usa para decidir) y el modulo `asyncio` que
# ve la funcion, no el global del proceso.

class RelojFalso:
    def __init__(self, paso):
        self.t = 1_000_000.0
        self.paso = paso

    def now_ts(self):
        return self.t


class AsyncioShim:
    """`asyncio` para el bucle: todo real menos `sleep`, que mueve el reloj."""

    def __init__(self, reloj):
        self._reloj = reloj

    def __getattr__(self, nombre):
        return getattr(asyncio, nombre)

    async def sleep(self, _segundos):
        self._reloj.t += self._reloj.paso
        await asyncio.sleep(0)


class BotFalso:
    """Lo minimo que el panel usa. Existe para que el caso del panel mida el
    panel, y no que `bot=None` reviente y el silencio parezca correcto."""

    def __init__(self):
        self.paneles = []

    async def send_message(self, _chat_id, texto):
        self.paneles.append(texto)
        return types.SimpleNamespace(message_id=1)

    async def edit_message_text(self, texto, chat_id=None, message_id=None):
        self.paneles.append(texto)


def worktree_con_etapa(etapa):
    """Un worktree DE VERDAD con su `.tg/progress.md`. Se escribe el fichero en
    vez de sembrar `tracker.milestone` porque el bucle lo relee en cada vuelta:
    sembrar el atributo mediria el arnes, no `read_progress`."""
    raiz = tempfile.mkdtemp(prefix="tg-arnes-")
    tg = os.path.join(raiz, ".tg")
    os.makedirs(tg, exist_ok=True)
    with io.open(os.path.join(tg, "progress.md"), "w", encoding="utf-8") as fh:
        fh.write("Fase 1 arrancada\n" + etapa + "\n")
    return raiz


def tracker_de_prueba(acciones=("Leido tg_daemon.py",), milestone=""):
    t = ProgressTracker(branch="", model="test", max_turns=15, timeout=1200)
    for a in acciones:
        t.actions.append(a)
    t.milestone = milestone
    return t


async def correr(func, globales, *, worktree, live, timeout, tracker,
                 vueltas=400, paso=30, bot=None):
    """Ejerce `func` (una `monitor_loop`) y devuelve los mensajes que mando.

    `globales` es el espacio de nombres donde la funcion resuelve `reply`,
    `now_ts` y `asyncio`: para la funcion real es el modulo, para la mutada es
    la copia donde se ejecuto. Se parchea ahi, nunca en el proceso entero.
    """
    enviados = []
    reloj = RelojFalso(paso)

    async def reply_falso(_cfg, _chat_id, texto):
        enviados.append(texto)

    previos = {k: globales.get(k) for k in ("reply", "now_ts", "asyncio")}
    globales["reply"] = reply_falso
    globales["now_ts"] = reloj.now_ts
    globales["asyncio"] = AsyncioShim(reloj)
    try:
        tarea = asyncio.create_task(
            func({}, 1, tracker, worktree, bot, live, timeout))
        for _ in range(vueltas):
            await asyncio.sleep(0)
            if tarea.done():
                break
        tarea.cancel()
        try:
            await tarea
        except asyncio.CancelledError:
            pass
    finally:
        for k, v in previos.items():
            if v is not None:
                globales[k] = v
    return enviados


def monitor_mutado():
    """`monitor_loop` REAL con la guarda vieja devuelta, y su espacio de nombres.

    Se muta el CODIGO FUENTE de la funcion que hay hoy en el repo, no una copia
    escrita aqui: si manana alguien reescribe el bucle, el ancla deja de casar y
    el arnes se pone ROJO en vez de aprobar en silencio (caso 4).
    """
    fuente = textwrap.dedent(inspect.getsource(tg_daemon.monitor_loop))
    ancla = "if not live and now_ts() - ultimo_checkpoint >= cada:"
    vieja = "if worktree and not live and now_ts() - ultimo_checkpoint >= cada:"
    if fuente.count(ancla) != 1:
        return None, None, fuente.count(ancla)
    ns = dict(tg_daemon.__dict__)
    exec(compile(fuente.replace(ancla, vieja), "<monitor_loop mutado>", "exec"), ns)
    return ns["monitor_loop"], ns, 1


async def main_async():
    print("Arnes del checkpoint sin worktree (caja negra del modo lectura)\n")

    # 1 y 2 — la cadencia cabe bajo el techo, en LOS DOS modos. Este es el
    # invariante que sustituye al numero: con 1800 y un techo de 600 no cabia
    # ninguno, y por eso en lectura no avisaba nunca.
    for modo, techo in (("lectura", tg_daemon.READ_TIMEOUT),
                        ("escritura", tg_daemon.WRITE_TIMEOUT)):
        cada = tg_daemon.checkpoint_interval(techo)
        check(f"{'1' if modo == 'lectura' else '2'}. en {modo} caben >=2 checkpoints "
              f"bajo el techo (cada {cada}s de {techo}s)",
              cada * 2 <= techo,
              f"cadencia {cada}s bajo techo {techo}s: el humano se queda sin "
              f"senal de vida hasta que la tarea muera")

    # 3 — EL CASO. Sin worktree, una invocacion mas larga que su cadencia manda.
    tracker = tracker_de_prueba()
    msgs = await correr(tg_daemon.monitor_loop, tg_daemon.__dict__,
                        worktree="", live=False,
                        timeout=tg_daemon.READ_TIMEOUT, tracker=tracker)
    check("3. SIN worktree y sin panel, la invocacion larga manda checkpoint",
          len(msgs) >= 1,
          "cero mensajes: el modo lectura sigue siendo una caja negra")
    if msgs:
        check("3b. y el checkpoint dice el tiempo y la ultima accion",
              "min" in msgs[0] and "tg_daemon.py" in msgs[0],
              f"texto: {msgs[0]!r}")

    # 4 — el ancla de la mutacion existe. Si el bucle se reescribio, este arnes
    # deja de medir lo que cree medir y tiene que decirlo, no aprobar.
    mutada, ns_mutado, veces = monitor_mutado()
    check("4. el ancla de la mutacion sigue casando con el bucle real",
          mutada is not None,
          f"la guarda aparece {veces} veces en `monitor_loop`: los casos 5 y 6 "
          f"no estan midiendo nada")

    if mutada is not None:
        # 5 — LA MUTACION: con la guarda vieja, sin worktree, CERO mensajes.
        msgs_mut = await correr(mutada, ns_mutado, worktree="", live=False,
                                timeout=tg_daemon.READ_TIMEOUT,
                                tracker=tracker_de_prueba())
        check("5. mutacion: con `worktree and` devuelto, sin worktree NO manda nada",
              not msgs_mut,
              f"mando {len(msgs_mut)}: el caso 3 no depende de la guarda, luego "
              f"no estaba midiendo el arreglo")

        # 6 — anti-artefacto: el MISMO mutante CON worktree si manda. Sin esto,
        # el cero del caso 5 podria ser fontaneria rota del arnes.
        msgs_mut_wt = await correr(mutada, ns_mutado,
                                   worktree=worktree_con_etapa("Fase 2 lista"),
                                   live=False, timeout=tg_daemon.READ_TIMEOUT,
                                   tracker=tracker_de_prueba())
        check("6. anti-artefacto: el mutante CON worktree si manda (el 5 es la guarda)",
              len(msgs_mut_wt) >= 1,
              "el mutante no manda en ningun caso: el cero del 5 es del arnes, "
              "no del codigo")

    # 7 — no hay regresion en escritura: con worktree sigue mandando.
    msgs_wt = await correr(tg_daemon.monitor_loop, tg_daemon.__dict__,
                           worktree=worktree_con_etapa("Fase 2 lista"),
                           live=False, timeout=tg_daemon.WRITE_TIMEOUT,
                           tracker=tracker_de_prueba(), paso=200)
    check("7. CON worktree (escritura) sigue mandando checkpoint",
          len(msgs_wt) >= 1,
          "el arreglo se compro rompiendo el modo que ya funcionaba")
    if msgs_wt:
        check("7b. y con worktree gana la etapa que el agente escribio en .tg/progress.md",
              "Fase 2 lista" in msgs_wt[0],
              f"texto: {msgs_wt[0]!r}")

    # 8 — con el panel encendido el checkpoint calla: el panel ya es la senal.
    bot = BotFalso()
    msgs_live = await correr(tg_daemon.monitor_loop, tg_daemon.__dict__,
                             worktree="", live=True,
                             timeout=tg_daemon.READ_TIMEOUT,
                             tracker=tracker_de_prueba(), bot=bot)
    check("8. con panel `live` el checkpoint no duplica el aviso",
          not msgs_live,
          f"mando {len(msgs_live)} mensajes ademas del panel")
    check("8b. y el panel SI habla (el silencio del 8 es reparto, no mudez)",
          len(bot.paneles) >= 1,
          "con `live` no salio ni panel ni checkpoint: eso no es reparto, es "
          "una caja negra con otro nombre")

    # 9 — el texto cae a la ultima accion cuando el agente no reporto etapa,
    # que es SIEMPRE en lectura (no hay `.tg/progress.md` sin worktree).
    t_sin = tracker_de_prueba(acciones=("Buscado READ_TIMEOUT",))
    check("9. sin etapa, el checkpoint cae a la ultima accion del stream",
          "READ_TIMEOUT" in t_sin.checkpoint_text(),
          f"texto: {t_sin.checkpoint_text()!r}")
    t_vacio = tracker_de_prueba(acciones=())
    check("9b. y sin acciones aun, no revienta ni miente",
          "min" in t_vacio.checkpoint_text(),
          f"texto: {t_vacio.checkpoint_text()!r}")

    # ── A2: el techo avisa antes de matar, y la muerte dice que se perdio ──
    # 10 — el aviso llega ANTES del techo, no despues (seria inutil).
    check("10. el aviso de techo dispara antes de que el techo mate",
          0 < __import__("progress").TIMEOUT_ALERT_RATIO < 1,
          "un ratio >=1 avisa cuando ya esta muerta")

    t_viejo = tracker_de_prueba()
    t_viejo.timeout = 1200
    t_viejo.started -= 1200 * 0.9        # 90% del techo consumido
    avisos = t_viejo.pending_alerts()
    check("11. al 90% del techo el tracker emite el aviso de cancelacion",
          any("se cancela" in a for a in avisos),
          f"alertas emitidas: {avisos}")
    check("11b. y no lo repite en el siguiente tick (una de cada tipo)",
          not any("se cancela" in a for a in t_viejo.pending_alerts()),
          "el aviso se repetiria cada 5 s hasta morir")

    # 12 — la muerte dice EN QUE ESTABA. Es la diferencia entre un error y un
    # diagnostico, y es lo unico que sobrevive a la cancelacion.
    t_muerto = tracker_de_prueba(acciones=("Leido gitops.py",))
    t_muerto.turns = 7
    texto = t_muerto.death_text()
    check("12. el texto de cancelacion nombra turno y ultima accion",
          "7" in texto and "gitops.py" in texto,
          f"texto: {texto!r}")

    # 13 — y el daemon lo pega de verdad al mensaje de muerte (no basta con que
    # el metodo exista: el sprint 15 aprendio que un metodo sin sitio no mide).
    fuente_daemon = inspect.getsource(tg_daemon.run_claude)
    check("13. `run_claude` engancha `death_text()` al mensaje de cancelacion",
          "death_text()" in fuente_daemon and "se canceló" in fuente_daemon,
          "el metodo existe pero la cancelacion sigue diciendo solo el numero")

    # ── 15 · Ningun texto imprime una fraccion imposible ──────────────────
    # La auditoria 39 (§3.3) encontro que el humano recibia «Turnos: 30/15»: un
    # numerador que dobla a su denominador. Mi primer arreglo movio el numero de
    # un contador a otro y ANCLE ESTE CASO EN 15 EVENTOS — justo el valor que lo
    # hace pasar. El auditor lo vio (§13.3): con 20 eventos volvia a salir
    # «Turnos: 20/15». Era el patron que este sprint persigue, cometido aqui.
    #
    # Ahora se alimenta max_turns + 5, que es el ancla que NO puede pasar por
    # casualidad, y se fija el invariante sobre los TRES textos que el humano
    # llega a leer, no sobre uno.
    #
    # Medido antes de elegirlo (2026-08-19): `--max-turns 1` -> error_max_turns
    # con num_turns=2; `--max-turns 4` con la tarea terminada -> 3 eventos y
    # num_turns=2; `--resume` no acumula. Ningun contador esta garantizado en la
    # unidad del flag, asi que la fraccion se imprime mientras se sostiene.
    t_u = tracker_de_prueba(acciones=("Leido gitops.py",))
    t_u.max_turns = 15
    for _ in range(t_u.max_turns + 5):
        t_u.feed({"type": "assistant", "message": {"content": []}})
    t_u.feed({"type": "result", "subtype": "success", "num_turns": 40,
              "total_cost_usd": 1.0})

    def imposibles(texto):
        """Fracciones `N/M` con N > M en un texto de cara al humano."""
        return [f"{a}/{b}" for a, b in re.findall(r"(\d+)/(\d+)", texto or "")
                if int(a) > int(b)]

    textos = {"final_text": t_u.final_text(), "death_text": t_u.death_text()}
    t_alerta = tracker_de_prueba()
    t_alerta.max_turns = 15
    for _ in range(20):
        t_alerta.feed({"type": "assistant", "message": {"content": []}})
    textos["aviso de turnos"] = " ".join(t_alerta.pending_alerts())

    malas = {k: imposibles(v) for k, v in textos.items() if imposibles(v)}
    check("15. ningun texto al humano imprime una fraccion imposible",
          not malas,
          f"fracciones con el numerador por encima del tope: {malas}")
    check("15b. y aun asi dice el numero y nombra el limite",
          "20" in textos["final_text"] and "15" in textos["final_text"],
          f"texto: {textos['final_text']!r}")
    check("15d. y `turns` sigue contando EVENTOS tras el `result`, no `num_turns`",
          t_u.turns == t_u.max_turns + 5,
          f"turns={t_u.turns}: volvio la sobrescritura y el campo mezcla otra "
          f"vez las dos unidades (el helper lo tapa en pantalla, pero el dato "
          f"de cuantos eventos hubo se pierde)")
    check("15c. el contador del CLI se conserva, en su propio campo",
          t_u.turns_cli == 40,
          f"turns_cli={t_u.turns_cli!r}: el dato del CLI se perdio, y es el que "
          f"hace falta para volver a comparar las dos unidades")

    # ── El cableado en produccion, que no lo ejerce nada mas ──────────────
    # Los casos 1-13 miden `monitor_loop` y el tracker por separado, pasandoles
    # el techo a mano. Si `on_message` se olvidara de pasarlo, en escritura se
    # usaria el default (lectura) y la cadencia bajaria a 5 min sin que ningun
    # caso se enterara. Se comprueba el CABLE, no el numero.
    fuente_msg = inspect.getsource(tg_daemon.on_message)
    m = re.search(r"(\w+)\s*=\s*WRITE_TIMEOUT\s+if\s+write_mode\s+else\s+READ_TIMEOUT",
                  fuente_msg)
    check("14. `on_message` calcula el techo segun el modo",
          m is not None,
          "no hay un techo por modo: o esta hardcodeado, o se reparte a mano en "
          "cada sitio y uno se quedara atras")
    if m:
        nombre = m.group(1)
        destinos = {
            "ProgressTracker": r"ProgressTracker\((?:[^()]|\([^()]*\))*\)",
            "monitor_loop": r"monitor_loop\((?:[^()]|\([^()]*\))*\)",
            "run_claude": r"run_claude\((?:[^()]|\([^()]*\))*\)",
        }
        faltan = []
        for destino, patron in destinos.items():
            trozo = re.search(patron, fuente_msg, re.S)
            if not trozo or not re.search(rf"\b{nombre}\b", trozo.group(0)):
                faltan.append(destino)
        check(f"14b. y se lo pasa a los tres: tracker, monitor e invocacion",
              not faltan,
              f"no le llega a {faltan}: el aviso del 80 %, la cadencia y el "
              f"corte dejarian de hablar del mismo techo")

    return resumen()


def resumen():
    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos en verde")
    if fallos:
        print("FALLAN:")
        for n in fallos:
            print(f"  · {n}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main_async()))
