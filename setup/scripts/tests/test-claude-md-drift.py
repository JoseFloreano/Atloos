#!/usr/bin/env python3
"""
test-claude-md-drift.py — Caza copias declaradas "sincronizadas" que divergen.

Por qué existe (2026-08-09): la auditoría externa del W3 (H3) encontró que el
`CLAUDE.md` de `Atloos` **no llevaba la línea determinista del merge-gate**. La
llevaba su fuente (`memory-snippet.md`) y la copia hermana; no la llevaba el
proyecto en cuyo `main` caen los merges. La capa 1 de las tres —la única que la
prueba del 08-08 midió como imbatible, porque no compite en ningún concurso de
descripciones— estaba ausente justo donde hacía falta.

**La enfermedad**: un contenido con DOS puntos de consumo, donde editar uno no
obliga a editar el otro. La copia desplegada se queda atrás y nada lo delata,
porque no hay diff que mirar: son ficheros distintos con formas distintas.

Está medida tres veces, no es hipotética:
  · `memory-instructions.md` volvió a la v1 en un pull — **3 divergencias**
    documentadas en su propia cabecera (la última, 2026-07-26).
  · el `CLAUDE.md` de este repo, atrasado varias versiones (H3, 2026-08-09).
  · la copia instalada de `merge-gate-guard.py` en `~/.claude/hooks/`, que
    siguió ejecutando el parser roto tras arreglarlo en el repo (2026-08-09).

**Por qué un arnés y no una nota**: las tres veces la regla estaba escrita —la
cabecera de los dos ficheros dice "editar ambas a la vez"— y las tres veces se
incumplió. Es la tesis del RFD 11: la convención escrita no muerde.

QUÉ CAMBIÓ EN EL SPRINT 2 (2026-08-11), y por qué el arnés estaba verificando el
contrato equivocado. Su regla es "todo lo que dice el snippet debe estar en el
CLAUDE.md desplegado". El disparador de Graphify —la instrucción que sustituye a
la que escribe `graphify claude install`— **nunca estuvo en el snippet**: vivía
en el paso 7 de `project-onboard` (una orden para que un agente lo sustituyera a
mano) y en `hooks/README.md` (documentación). Así que el arnés comparaba
fielmente y no encontraba nada, mientras `graphify: no-usado` salía en los dos
reportes de campo de dos. **El disparador arreglado no viajaba en el vehículo
que lo despliega.** Tres arreglos, y este fichero implementa dos:

  1. el disparador entra en `memory-snippet.md` (y en su gemelo), así que viaja
     solo en cada onboarding y este arnés empieza a exigirlo — eso no es código;
  2. los objetivos dejan de ser solo el CLAUDE.md de este repo: se leen de
     `setup/telegram-bridge/projects.json`, el registro de proyectos vivos que
     ya existe. **No se escribe una segunda lista**: una lista a mano es otro
     catálogo, y otro catálogo se desincroniza — que es la enfermedad que este
     arnés persigue;
  3. la línea vieja de Graphify se caza **por su nombre** (`LINEA_OBSOLETA`), no
     solo por las líneas nuevas que le faltan, para que el hallazgo diga qué
     borrar y no solo qué añadir.

Y el arnés se autoprueba (`autoprueba()`): en cada corrida fabrica en memoria un
CLAUDE.md con la línea vieja y comprueba que lo caza. Un check que solo se corre
en verde no está verificado.

Uso:  setup/scripts/py setup/scripts/tests/test-claude-md-drift.py [otro/CLAUDE.md ...]
      Sin argumentos comprueba el `CLAUDE.md` de este repo MÁS los declarados en
      `projects.json`. Un proyecto declarado que no está en esta máquina sale
      como `[SKIP]` con su ruta —multi-laptop—, nunca en silencio.
      Con `CLAUDE_TG_BOT=1` y SIN argumentos, los objetivos por defecto se
      saltan —a la vista, como `[SKIP]`, nunca como `[OK]` en silencio—: es el
      worktree del bot, y ver por qué eso es seguro exige leer
      `check_desplegado()` más abajo. Un objetivo explícito se sigue
      comprobando siempre, con o sin la variable puesta.
Salidas: 0 sin deriva · 1 hay deriva
"""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

SETUP = Path(__file__).resolve().parents[2]              # setup/
REPO = SETUP.parent
SNIPPET = SETUP / "skills" / "claude-code" / "project-onboard" / "references" / "memory-snippet.md"
GEMELO = SETUP / "memory-instructions.md"
PROYECTOS = SETUP / "telegram-bridge" / "projects.json"

# La línea que escribe `graphify claude install` en el CLAUDE.md del repo. Dice
# QUÉ hacer y no dice CUÁNDO, así que no se dispara nunca: en campo,
# `graphify: no-usado` en las dos jornadas de dos con la herramienta al día. El
# snippet trae la instrucción que la sustituye; esta hay que BORRARLA, y por eso
# se caza por su nombre y no solo por las líneas nuevas que falten.
LINEA_OBSOLETA = re.compile(r"for codebase questions.{0,60}graphify query", re.I)

# El SELLO de version del snippet (sprint 9, S2). Es texto VISIBLE, no un
# comentario HTML, precisamente para que viaje al `CLAUDE.md` desplegado y
# cualquier maquina pueda contestar con un `grep` que version lleva. Antes la
# unica forma de saberlo era diffear dos ficheros que ni siquiera tienen la
# misma forma.
SELLO = re.compile(r"snippet v(\d+)\s*[·.]\s*(\d{4}-\d{2}-\d{2})")

# Presupuesto del snippet, en tokens MEDIDOS. El fichero declaraba "~300" y
# nadie lo habia medido nunca: el real es 890 (tiktoken/o200k, 2026-08-16),
# x2,97. Se sube el numero al real en vez de recortar el bloque —cada regla de
# ahi es la defensa contra alucinacion cruzada entre proyectos— y se le pone
# margen, igual que la `description` de una skill tiene 950 contra su 1024.
# Ahora lo mide alguien, que es lo que le faltaba.
PRESUPUESTO_TOKENS = 950

hallazgos = []


def sello_de(texto):
    """(version, fecha) del snippet en `texto`, o (None, None)."""
    m = SELLO.search(texto)
    return (m.group(1), m.group(2)) if m else (None, None)


def tokens_del_snippet():
    """(n_tokens, metodo). Sin tokenizador, (None, motivo) — nunca un invento.

    Se usa tiktoken porque esta instalado y es un tokenizador DE VERDAD. No es
    el de Anthropic —ese solo se consulta por red— asi que el numero es una
    aproximacion buena, y se dice: un `chars/3,5` no lo es, y este repo lleva
    seis numeros escritos que nadie midio.
    """
    try:
        import tiktoken
    except ImportError:
        return None, "tiktoken no instalado"
    try:
        enc = tiktoken.get_encoding("o200k_base")
    except Exception as e:                     # sin red y sin cache del BPE
        return None, f"no se pudo cargar o200k_base ({type(e).__name__})"
    return len(enc.encode(cuerpo(SNIPPET.read_text(encoding="utf-8")))), "tiktoken/o200k"


def cuerpo(texto):
    """Quita los comentarios HTML de cabecera: son instrucciones, no contenido."""
    return re.sub(r"(?s)<!--.*?-->", "", texto).strip()


def norma(linea):
    """Normaliza para comparar: espacios colapsados, sin anotaciones de plantilla."""
    linea = re.sub(r"←.*$", "", linea)                   # "← reemplazar al copiar"
    return re.sub(r"\s+", " ", linea).strip()


def lineas_utiles(texto):
    return [n for n in (norma(l) for l in cuerpo(texto).splitlines()) if n]


def check_gemelos():
    """Las dos copias que se declaran sincronizadas deben tener el MISMO cuerpo."""
    if not (SNIPPET.is_file() and GEMELO.is_file()):
        hallazgos.append(f"falta uno de los gemelos: {SNIPPET.name} / {GEMELO.name}")
        return
    a = lineas_utiles(SNIPPET.read_text(encoding="utf-8"))
    b = lineas_utiles(GEMELO.read_text(encoding="utf-8"))
    solo_a = [l for l in a if l not in b]
    solo_b = [l for l in b if l not in a]
    if solo_a or solo_b:
        hallazgos.append(
            f"{SNIPPET.name} y {GEMELO.name} se declaran copias sincronizadas "
            f"pero divergen: {len(solo_a)} línea(s) solo en el primero, "
            f"{len(solo_b)} solo en el segundo")
        for l in (solo_a + solo_b)[:5]:
            hallazgos.append(f"    · {l[:96]}")


def revisa_desplegado(texto, etiqueta):
    """Hallazgos de UN CLAUDE.md ya leído. Devuelve lista; no toca el global.

    Separado de `check_desplegado` para que `autoprueba()` pueda ejercerlo con un
    texto fabricado sin escribir nada en disco ni contaminar el resultado real.
    """
    encontrados = []
    m = re.search(r"##\s*Active Project:\s*`([^`]+)`", texto)
    if not m:
        return [f"{etiqueta}: sin `## Active Project:` — no se puede "
                f"resolver <project-name> para comparar"]
    proyecto = m.group(1)

    esperado = lineas_utiles(
        SNIPPET.read_text(encoding="utf-8").replace("<project-name>", proyecto))
    presentes = set(lineas_utiles(texto))
    faltan = [l for l in esperado if l not in presentes]
    if faltan:
        encontrados.append(f"{etiqueta} ({proyecto}) va ATRÁS de {SNIPPET.name}: "
                           f"le faltan {len(faltan)} de {len(esperado)} líneas")
        for l in faltan:
            encontrados.append(f"    · {l[:96]}")

    # La línea vieja de Graphify, cazada por su nombre: el hallazgo tiene que
    # decir qué BORRAR, no solo qué añadir. Faltarle las líneas del snippet y
    # arrastrar esta son dos defectos distintos y se arreglan distinto.
    for n, linea in enumerate(texto.splitlines(), 1):
        if LINEA_OBSOLETA.search(linea):
            encontrados.append(
                f"{etiqueta}:{n} arrastra la línea que escribe "
                f"`graphify claude install` — dice QUÉ y no dice CUÁNDO, así que "
                f"no se dispara. Bórrala; el disparador que la sustituye ya viene "
                f"en {SNIPPET.name}")
            encontrados.append(f"    · {linea.strip()[:96]}")
    return encontrados


def check_desplegado(ruta, explicito=False):
    """Todo lo que dice el snippet debe estar en el CLAUDE.md desplegado.

    QUE EL FICHERO NO EXISTA NO ES DERIVA. `CLAUDE.md` está gitignorado —es
    artefacto de instancia, no fuente— así que en un worktree o en un clon
    recién hecho sencillamente no está. La deriva es que la copia desplegada
    EXISTA y vaya atrasada.

    Tratarlo como hallazgo tenía una consecuencia que solo se ve desde fuera del
    checkout principal (auditoría 22, B1): `gate-test.py` corre la suite en la
    raíz del worktree, así que este arnés en rojo **impedía producir el verde
    que el gate exige**. La compuerta se cerraba sobre sí misma, y el 14/14 no
    lo delataba porque se midió donde los ficheros sí están.

    Con `explicito=True` —una ruta que alguien pasó por `sys.argv`— sí es
    hallazgo: si la pides a propósito y no está, eso es un error tuyo, no del
    entorno.
    """
    if not ruta.is_file():
        if explicito:
            hallazgos.append(f"no existe: {ruta}")
        else:
            print(f"  [SKIP] {ruta}: no está en este árbol — `CLAUDE.md` es "
                  f"artefacto de instancia y está gitignorado, así que un "
                  f"worktree o un clon nuevo no lo tienen. Ausencia no es "
                  f"deriva")
        return
    texto = ruta.read_text(encoding="utf-8")
    ver, fecha = sello_de(texto)
    marca = f"snippet v{ver} · {fecha}" if ver else "SIN SELLO (anterior a la v4)"
    print(f"  [VER]  {ruta.name} ({ruta.parent.name}): {marca}")
    hallazgos.extend(revisa_desplegado(texto, ruta.name))


def objetivos_declarados(registro=None):
    """(rutas, ausentes) de los CLAUDE.md vivos, leídos de `projects.json`.

    El registro de proyectos vivos YA existe y lo mantiene el puente Telegram.
    Escribir aquí una segunda lista sería exactamente la enfermedad que este
    arnés persigue: dos catálogos, y el segundo se queda atrás sin que nadie lo
    note. Si `projects.json` no está o no parsea, se dice —no se asume vacío—.

    Las rutas son absolutas y de una máquina concreta: en otra laptop puede que
    el repo no esté clonado. Eso NO es deriva, así que sale como ausente (se
    imprime `[SKIP]` con su ruta) y no como hallazgo. Lo que no puede pasar es
    que desaparezca en silencio.
    """
    registro = registro or PROYECTOS
    if not registro.is_file():
        # `projects.json` también está gitignorado: en un worktree o un clon
        # nuevo no está, y eso es entorno, no deriva (auditoría 22, B1).
        print(f"  [SKIP] {registro.name}: no está en este árbol (gitignorado) "
              f"— sin registro no hay CLAUDE.md vivos que auditar, y eso no es "
              f"una deriva")
        return [], []
    try:
        datos = json.loads(registro.read_text(encoding="utf-8"))
    except Exception as e:
        # Existir y no parsear SÍ es un defecto: alguien lo rompió.
        hallazgos.append(f"{registro.name} no parsea ({e}): no hay lista de "
                         f"CLAUDE.md vivos que auditar")
        return [], []
    rutas, ausentes = [], []
    for nombre, cfg in sorted(datos.items()):
        # Las dos formas las dicta el CONSUMIDOR, no este arnés: `tg_daemon.py`
        # (277-281) salta las claves `_*` y acepta un string suelto como ruta
        # (el "formato viejo" que documenta `projects.example.json`). Este bucle
        # asumía dict siempre, así que reventaba con un AttributeError sobre
        # cualquier `projects.json` copiado del ejemplo —que ya trae cuatro
        # claves `_*`—. Medido en la SER8 el 2026-08-17 dando de alta la máquina:
        # el arnés jamás se había corrido en un árbol con registro real, porque
        # `projects.json` está gitignorado y arriba se sale por [SKIP].
        if nombre.startswith("_"):
            continue
        base = cfg if isinstance(cfg, str) else (cfg or {}).get("path")
        if not base:
            hallazgos.append(f"{registro.name}: el proyecto `{nombre}` no "
                             f"declara `path`")
            continue
        ruta = Path(base).expanduser() / "CLAUDE.md"
        (rutas if ruta.is_file() else ausentes).append((nombre, ruta))
    return rutas, ausentes


def autoprueba():
    """Mutación: fabrica el defecto y exige que el check lo cace.

    Un check que solo se corre sobre entradas sanas no está verificado — es la
    misma ley que gobierna al gate ("el código de salida no es el estado").
    Aquí el defecto es el caso que el sprint 2 existe para cerrar: un CLAUDE.md
    que arrastra la línea vieja de Graphify. Antes de este cambio, ese fichero
    daba VERDE.
    """
    viejo = ("## Active Project: `laboratorio`\n\n"
             "For codebase questions, first run `graphify query` to explore.\n")
    encontrados = revisa_desplegado(viejo, "(autoprueba)")
    if not any(LINEA_OBSOLETA.search(h) or "graphify claude install" in h
               for h in encontrados):
        hallazgos.append(
            "AUTOPRUEBA FALLIDA: un CLAUDE.md con la línea vieja de Graphify no "
            "produjo hallazgo. El check no está verificando lo que dice.")
        return False
    return True


def autoprueba_formatos():
    """Las dos formas de `projects.json` se leen sin reventar.

    El caso que motiva esto (SER8, 2026-08-17): `objetivos_declarados()` hacía
    `cfg.get("path")` sobre TODO valor, así que un `projects.json` copiado del
    ejemplo —cuatro claves `_*` de comentario, todas strings— tumbaba el arnés
    con un `AttributeError`, no con un hallazgo. Un arnés que se cae no dice
    «hay deriva», dice «no se sabe», y eso lo cuenta el gate como rojo.

    Se ejerce escribiendo un registro de verdad en un temporal, porque el
    defecto vivía justo en el camino que el [SKIP] de arriba no recorre.
    """
    antes = len(hallazgos)
    registro = {
        "_comentario": "una clave de metadatos, como las del example",
        "nuevo": {"path": str(REPO / "__no-existe-nuevo__")},
        "viejo": str(REPO / "__no-existe-viejo__"),      # formato viejo: string
    }
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "projects.json"
        ruta.write_text(json.dumps(registro), encoding="utf-8")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                vivos, ausentes = objetivos_declarados(ruta)
        except Exception as e:
            hallazgos.append(
                f"AUTOPRUEBA FALLIDA: `projects.json` con una clave `_*` y una "
                f"entrada en formato viejo hace estallar el arnés "
                f"({type(e).__name__}: {e}). Las dos formas las acepta "
                f"`tg_daemon.py`, así que el registro es válido y el roto es "
                f"este check.")
            return False
    nombres = sorted(n for n, _ in vivos + ausentes)
    if nombres != ["nuevo", "viejo"] or len(hallazgos) != antes:
        del hallazgos[antes:]
        hallazgos.append(
            f"AUTOPRUEBA FALLIDA: se esperaban los proyectos ['nuevo', 'viejo'] "
            f"y ningún hallazgo; salieron {nombres}. O se cuela una clave `_*` "
            f"como proyecto, o se pierde el formato viejo.")
        return False
    return True


def autoprueba_entorno():
    """Un árbol SIN los ficheros gitignorados no puede producir hallazgos.

    Es B1 de la auditoría 22, convertido en caso. El arnés se ponía rojo en
    cualquier worktree y en cualquier clon nuevo, y como `gate-test.py` corre la
    suite en la raíz del worktree, eso impedía producir el verde que el propio
    gate exige. Se comprueba sin montar un worktree: se ejerce el camino con
    rutas que no existen, que es exactamente lo que un worktree tiene.
    """
    antes = len(hallazgos)
    inexistente = REPO / "__no-existe__" / "CLAUDE.md"
    with contextlib.redirect_stdout(io.StringIO()):      # los [SKIP] de mentira
        check_desplegado(inexistente)                    # objetivo por defecto
        objetivos_declarados(REPO / "__no-existe__" / "projects.json")
    if len(hallazgos) != antes:
        del hallazgos[antes:]
        hallazgos.append(
            "AUTOPRUEBA FALLIDA: un árbol sin `projects.json` ni `CLAUDE.md` "
            "—o sea, cualquier worktree— produce hallazgos. Ausencia no es "
            "deriva, y con esto en rojo el gate no puede producir su verde.")
        return False
    return True


def main():
    print("Deriva entre fuente y copias desplegadas\n")
    print(f"  [AUTOPRUEBA] {'OK' if autoprueba() else 'FALLIDA'} — la línea "
          f"vieja de Graphify produce hallazgo")
    print(f"  [AUTOPRUEBA] {'OK' if autoprueba_entorno() else 'FALLIDA'} — un "
          f"worktree sin los ficheros gitignorados NO produce hallazgos")
    print(f"  [AUTOPRUEBA] {'OK' if autoprueba_formatos() else 'FALLIDA'} — las "
          f"dos formas de projects.json (clave `_*` y formato viejo) se leen")
    check_gemelos()

    # El sello y el presupuesto de la FUENTE. Van antes que los destinos porque
    # si la fuente no lleva sello, ningún destino puede llevarlo.
    ver_src, fecha_src = sello_de(SNIPPET.read_text(encoding="utf-8"))
    if not ver_src:
        hallazgos.append(
            f"{SNIPPET.name} no lleva sello de versión (`snippet vN · fecha`). "
            f"Sin él, una máquina no puede contestar con un `grep` qué versión "
            f"de las reglas tiene desplegada")
    else:
        print(f"  [FUENTE] {SNIPPET.name}: snippet v{ver_src} · {fecha_src}")

    n_tok, metodo = tokens_del_snippet()
    if n_tok is None:
        print(f"  [SKIP] presupuesto de tokens: {metodo} — no se estima, se "
              f"dice. Un `caracteres/3,5` no es una medición")
    elif n_tok > PRESUPUESTO_TOKENS:
        hallazgos.append(
            f"el snippet mide {n_tok} tokens ({metodo}) y el presupuesto es "
            f"{PRESUPUESTO_TOKENS}: entra en el `CLAUDE.md` de CADA proyecto y "
            f"se paga en CADA sesión. Recorta por el paréntesis de "
            f"`codebase-map`, no por la línea de higiene")
    else:
        print(f"  [OK] snippet: {n_tok}/{PRESUPUESTO_TOKENS} tokens ({metodo}), "
              f"{PRESUPUESTO_TOKENS - n_tok} de margen")

    argv = sys.argv[1:]
    objetivos = []
    if not argv and os.environ.get("CLAUDE_TG_BOT") == "1":
        # Objetivo por defecto (REPO/CLAUDE.md), y estamos en el worktree del
        # bot: ese CLAUDE.md NO es el del repo, es la versión BOT que
        # gitops.create_worktree() escribe llamando a bot_claude_md()
        # (ADR-20260801-bot-memoria-y-perfil) — sustituye entera la sección de
        # Memory Rules porque el bot no puede cumplir las órdenes de vault y
        # Graphiti que ahí viven. Este chequeo caza una copia que se QUEDÓ
        # ATRÁS de su fuente por descuido; esta copia, en cambio, se REGENERA
        # desde el CLAUDE.md del repo cada vez que se monta un worktree nuevo,
        # así que no puede desincronizarse por su cuenta — el modo de fallo
        # que `check_desplegado` existe para cazar no puede darse aquí. Por
        # eso se salta, y SOLO el objetivo por defecto: si alguien pasa una
        # ruta explícita (`sys.argv[1:]`), la está pidiendo a propósito y se
        # comprueba igual, con o sin la variable. Los gemelos (arriba) siguen
        # corriendo siempre: comparan la fuente contra su copia hermana, algo
        # que un worktree no afecta para nada.
        #
        # Los objetivos de `projects.json` se saltan por la MISMA puerta, pero
        # por otra razón: apuntan al checkout principal de cada proyecto, que
        # desde el worktree del bot es un árbol ajeno. Un rojo ahí sería un rojo
        # que el bot no puede arreglar desde donde está, y dejar `/test` rojo
        # por algo fuera de su alcance es la forma más rápida de que el gate se
        # vuelva ruido. Con ruta explícita se comprueban igual.
        print("  [SKIP] CLAUDE.md desplegado (objetivos por defecto): "
              "CLAUDE_TG_BOT=1 — worktree del bot, CLAUDE.md regenerado en "
              "cada worktree nuevo (gitops.create_worktree/bot_claude_md); no "
              "puede quedarse atrás por su cuenta, así que \"distinto\" aquí "
              "es correcto y no es la deriva que este arnés caza")
    elif argv:
        objetivos = [Path(a).resolve() for a in argv]
        for ruta in objetivos:
            check_desplegado(ruta, explicito=True)
    else:
        # Sin argumentos: el CLAUDE.md de este repo MÁS los proyectos vivos
        # declarados. Antes solo se miraba el primero, así que un proyecto ya
        # enganchado podía arrastrar la línea vieja para siempre sin que nada lo
        # dijera — el script lo soportaba ("pásalos por ruta") y nadie lo hacía.
        vivos, ausentes = objetivos_declarados()
        objetivos = [REPO / "CLAUDE.md"]
        for _n, ruta in vivos:
            if ruta.resolve() not in {o.resolve() for o in objetivos}:
                objetivos.append(ruta)
        for nombre, ruta in ausentes:
            print(f"  [SKIP] {nombre}: declarado en {PROYECTOS.name} pero no "
                  f"está en esta máquina ({ruta}) — multi-laptop, no deriva")
        for ruta in objetivos:
            check_desplegado(ruta)

    if not hallazgos:
        # Se cuentan los COMPROBADOS, no los intentados. Decir "1 CLAUDE.md al
        # día" cuando el único objetivo se saltó es un verde falso en miniatura,
        # y es exactamente la clase de afirmación que este arnés persigue.
        vistos = [o for o in objetivos if o.is_file()]
        extra = (f"y {len(vistos)} CLAUDE.md al día" if vistos
                 else "(ningún CLAUDE.md comprobado: ver los [SKIP] arriba)")
        print(f"  [OK] los gemelos coinciden {extra}")
        return 0
    for h in hallazgos:
        print(f"  {'' if h.startswith('    ') else '[DERIVA] '}{h}")
    print(f"\n{len(hallazgos)} línea(s) de hallazgo — la copia desplegada manda "
          f"en la sesión real, así que esto NO es cosmético")
    return 1


if __name__ == "__main__":
    sys.exit(main())
