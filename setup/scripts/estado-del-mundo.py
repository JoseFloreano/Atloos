#!/usr/bin/env python3
"""
estado-del-mundo.py — Genera el bloque 2 del despacho, en vez de escribirlo.

POR QUÉ EXISTE. `workstream-dispatch` lleva sprints diciendo que el bloque 2 va
**GENERADO, no escrito a mano**, y aun así el último escrito a mano llevó **tres
datos falsos y contaminó un frente entero**. La regla estaba; faltaba la
herramienta. Un bloque que se escribe de memoria miente por construcción: los
números de línea los movió la tarea anterior, y el mundo cambia mientras el
agente trabaja.

LA LEY DE ESTE FICHERO, y es la única que importa:

    **NO INVENTA NADA.** Lo que no pudo medir sale como `HUECO` con el comando
    que lo llenaría — nunca omitido, nunca estimado, nunca en blanco.

No es escrupulosidad: un generador que se salta en silencio la sección que no
supo medir produce un bloque que **parece completo** y es exactamente la
enfermedad que viene a curar, con mejores modales. El pecado del bloque escrito
a mano no fue tener huecos; fue tener tres afirmaciones falsas donde debía haber
huecos declarados.

QUÉ MIDE, y de dónde sale cada cosa —todo derivado del repo, ninguna lista
escrita a mano, porque una lista a mano es otro catálogo que se desincroniza:

  1. **Base real y desfase.** El dato que motivó media doctrina: un worktree de
     agente **nace en `main`, no en tu HEAD** (`gitops.py:204-205`), así que la
     base puede ir muchos commits por detrás de lo que acabas de escribir — y
     todo lo que el agente ve es coherente. Aquí sale el número.
  2. **Ramas vivas y los ficheros que toca cada una**, con las **colisiones**
     calculadas: un fichero que tocan dos ramas es el hallazgo, no la lista.
  3. **Worktrees**, y cuáles tienen cambios sin commitear — la colisión viva que
     no se ve desde `git branch`.
  4. **Artefactos fuera de git que SÍ están en este árbol.** Se leen de
     `git status --ignored`, o sea del `.gitignore` real y del disco real. Esto
     es literalmente *«la DIFERENCIA entre la máquina y lo que la suite
     supone»*: lo que hay aquí y un worktree nuevo NO tendrá.
  5. **Flags de entorno que mueven la suite, CON SU VALOR.** Se sacan grepeando
     `os.environ`/`getenv` en el repo: los interruptores que de verdad existen
     son los que el código lee. En campo, **42 de 51 skips eran una sola
     variable**, y `DEBUG=1` y `DEBUG=0` no son el mismo inventario.
  6. **La firma de la suite** —pasan / fallan / saltan— solo con `--con-suite`,
     porque correrla cuesta minutos. Sin el flag es un HUECO declarado.
  7. **Los DOS baselines** (este árbol y un worktree recién creado) solo con
     `--dos-baselines`. Es la sección más cara y la que más enseña: *no son el
     mismo número, y esa diferencia ES el inventario que falta*.

POR QUÉ 6 Y 7 VAN DETRÁS DE UN FLAG Y NO POR DEFECTO. La suite de campo tarda
**551 s**; `--dos-baselines` la corre dos veces y además monta un worktree. Un
generador que por defecto tarda veinte minutos no se usa, y el que no se usa
deja el bloque escrito a mano — que es el problema. Apagado por defecto **y
declarado como hueco**: el coste lo decide quien despacha, la honestidad no.

LÍMITE DECLARADO: la **firma de los fallos conocidos** (qué test concreto se
pone rojo y qué artefacto le falta) NO se genera. Requiere saber que un rojo es
de entorno y no de código, que es un juicio con contexto. Lo que esta
herramienta da es la materia prima —los artefactos ignorados de §4 y el conteo
de §6—; escribir *«si ves EXACTAMENTE estos 2 rojos, te falta data/padron.csv»*
sigue siendo del humano, y el bloque lo pide en un hueco con su plantilla.

Uso:  setup/scripts/py setup/scripts/estado-del-mundo.py [--con-suite] [--dos-baselines]
Salida: el bloque 2 en markdown, listo para pegar en el despacho.
Códigos: 0 siempre que pudo generar algo. Los huecos NO son error — son el
         producto. Solo sale 1 si ni siquiera hay repo que mirar.
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parents[2]
TIMEOUT = 30
# El runner declarado de la casa. Sale del mismo sitio que lo lee el gate, para
# no escribir aquí un segundo comando de test que se desincronice del primero.
CMD_SUITE = os.environ.get("GATE_TEST_CMD") or "py setup/scripts/run-tests.py"

# Los interruptores se descubren, no se enumeran: son los que el código lee.
LEE_ENTORNO = re.compile(
    r"""(?:os\.environ\.get\(|os\.getenv\(|os\.environ\[)\s*["']([A-Z][A-Z0-9_]{2,})["']""")

# NO hay regex de firma a propósito. La primera versión traía una que intentaba
# sacar pasan/fallan/saltan de la salida del runner, y eso es adivinar: cada
# runner lo imprime a su manera y un número mal parseado es peor que ninguno —
# sería este fichero cometiendo el pecado que viene a cerrar. Se pega la cola de
# la salida cruda y el conteo lo lee quien despacha.


def git(args, cwd=None, timeout=TIMEOUT):
    """(salida, None) o (None, motivo). NUNCA lanza: un generador que se cae a
    mitad deja medio bloque, y medio bloque se pega igual — con la mitad que
    falta convertida en silencio."""
    try:
        p = subprocess.run(["git"] + args, cwd=str(cwd or RAIZ),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout)
    except FileNotFoundError:
        return None, "no hay `git` en esta máquina"
    except subprocess.TimeoutExpired:
        return None, f"`git {' '.join(args[:2])}` no respondió en {timeout} s"
    except Exception as exc:
        return None, f"{type(exc).__name__} al correr git"
    if p.returncode != 0:
        err = p.stderr.decode("utf-8", "replace").strip().splitlines()
        return None, (err[0][:120] if err else f"git salió {p.returncode}")
    return p.stdout.decode("utf-8", "replace").rstrip("\n"), None


def hueco(que, comando, porque=""):
    """Un agujero DECLARADO. Es un producto legítimo de esta herramienta."""
    linea = [f"> ⚠ **HUECO — {que}.**"]
    if porque:
        linea.append(f"> {porque}")
    linea.append(f"> Se llena con: `{comando}`")
    return "\n".join(linea)


def seccion_base():
    out = ["### Base real y desfase", ""]
    head, err = git(["rev-parse", "--short", "HEAD"])
    rama, _ = git(["rev-parse", "--abbrev-ref", "HEAD"])
    if err:
        out.append(hueco("no se pudo leer el HEAD", "git rev-parse HEAD", err))
        return "\n".join(out)

    principal = None
    for cand in ("main", "master"):
        if git(["rev-parse", "--verify", cand])[0]:
            principal = cand
            break
    out.append(f"- **HEAD de esta sesión**: `{head}` (rama `{rama}`)")
    if not principal:
        out.append(hueco("no hay `main` ni `master`: no se puede calcular la base",
                         "git branch -a"))
        return "\n".join(out)

    base, err = git(["merge-base", "HEAD", principal])
    if err or not base:
        out.append(hueco("no se pudo calcular la base",
                         f"git merge-base HEAD {principal}", err or ""))
        return "\n".join(out)
    out.append(f"- **Base con `{principal}`** (`git merge-base`): `{base[:8]}`")

    # EL número que da el susto: un worktree de agente nace en `main`, así que
    # esto es cuánto no vería de lo que acabas de escribir.
    detras, _ = git(["rev-list", "--count", f"{principal}..HEAD"])
    tip, _ = git(["rev-parse", "--short", principal])
    out.append(f"- **`{principal}` está en** `{tip}`")
    if detras and detras.isdigit() and int(detras) > 0:
        out.append(
            f"- ⚠ **Un worktree nuevo nace en `{principal}`, no aquí: no vería "
            f"tus {detras} commit(s) de esta rama.** No es un descuido — es lo "
            f"que hace `git worktree add` (`gitops.py:204-205`). Dale el hash "
            f"`{head}` al frente o trabajará contra un repo viejo **sin que nada "
            f"se lo diga**: la suite pasa, el código compila, todo es coherente.")
    else:
        out.append(f"- Sin commits propios por delante de `{principal}`: un "
                   f"worktree nuevo ve lo mismo que tú.")
    return "\n".join(out)


def seccion_ramas():
    out = ["### Ramas vivas y qué ficheros toca cada una", ""]
    crudo, err = git(["for-each-ref", "--format=%(refname:short)", "refs/heads/"])
    if err:
        out.append(hueco("no se pudieron listar las ramas", "git branch -v", err))
        return "\n".join(out)
    ramas = [r for r in (crudo or "").splitlines() if r.strip()]
    principal = "main" if "main" in ramas else ("master" if "master" in ramas else None)

    tocados = {}
    for rama in ramas:
        if rama == principal:
            continue
        base, _ = git(["merge-base", rama, principal]) if principal else (None, None)
        rango = f"{base}..{rama}" if base else rama
        ficheros, e = git(["diff", "--name-only", rango])
        if e:
            out.append(f"- `{rama}`: no se pudo diffear ({e})")
            continue
        lista = [f for f in (ficheros or "").splitlines() if f.strip()]
        tocados[rama] = lista
        muestra = ", ".join(f"`{f}`" for f in lista[:6])
        extra = f" (+{len(lista) - 6} más)" if len(lista) > 6 else ""
        out.append(f"- **`{rama}`** — {len(lista)} fichero(s): "
                   f"{muestra or '_ninguno_'}{extra}")
    if not tocados:
        out.append("- _Ninguna rama viva además de la principal._")

    # La COLISIÓN es el hallazgo; la lista de arriba es solo el material.
    choques = {}
    for rama, lista in tocados.items():
        for f in lista:
            choques.setdefault(f, []).append(rama)
    duplicados = {f: r for f, r in choques.items() if len(r) > 1}
    out.append("")
    if duplicados:
        out.append(f"⚠ **{len(duplicados)} fichero(s) los tocan DOS o más ramas.** "
                   f"Esto es ownership roto, y es la clase de cosa que dos "
                   f"frentes descubren a la vez y arreglan en direcciones "
                   f"opuestas:")
        for f, rs in sorted(duplicados.items())[:12]:
            out.append(f"  - `{f}` ← {', '.join(f'`{r}`' for r in rs)}")
    else:
        out.append("✓ Ningún fichero lo tocan dos ramas: el ownership está limpio.")
    return "\n".join(out)


def seccion_worktrees():
    out = ["### Worktrees y colisiones vivas", ""]
    crudo, err = git(["worktree", "list", "--porcelain"])
    if err:
        out.append(hueco("no se pudieron listar los worktrees",
                         "git worktree list", err))
        return "\n".join(out)
    rutas = [l.split(" ", 1)[1] for l in (crudo or "").splitlines()
             if l.startswith("worktree ")]
    for ruta in rutas:
        estado, e = git(["status", "--porcelain"], cwd=ruta)
        if e:
            out.append(f"- `{ruta}` — no se pudo leer su estado ({e})")
            continue
        sucios = [l for l in (estado or "").splitlines() if l.strip()]
        if sucios:
            out.append(f"- ⚠ `{ruta}` — **{len(sucios)} cambio(s) sin commitear**. "
                       f"Un frente que toque esos ficheros pisa trabajo que no "
                       f"está en ninguna rama.")
        else:
            out.append(f"- `{ruta}` — limpio")
    return "\n".join(out)


def seccion_artefactos():
    out = ["### Artefactos fuera de git — lo que este árbol tiene y uno nuevo NO", ""]
    crudo, err = git(["status", "--porcelain", "--ignored=matching", "-uall"])
    if err:
        out.append(hueco("no se pudo leer lo ignorado",
                         "git status --porcelain --ignored", err))
        return "\n".join(out)
    ignorados = [l[3:] for l in (crudo or "").splitlines() if l.startswith("!! ")]
    if not ignorados:
        out.append("- _Nada ignorado presente: un worktree nuevo nace igual que "
                   "este árbol._")
        return "\n".join(out)

    # Se agrupa por raíz: `node_modules/` con 40 000 ficheros no es cuarenta mil
    # hallazgos, es uno. Un bloque de 40 000 líneas no lo lee nadie, y lo que no
    # se lee no informa.
    grupos = {}
    for ruta in ignorados:
        raiz = ruta.split("/", 1)[0] + ("/" if "/" in ruta else "")
        grupos[raiz] = grupos.get(raiz, 0) + 1
    out.append("Esto es **la diferencia entre esta máquina y lo que la suite "
               "supone**. Un worktree recién creado no tiene nada de esto:")
    out.append("")
    for raiz, n in sorted(grupos.items(), key=lambda x: -x[1])[:20]:
        cuenta = f" ({n} ficheros)" if n > 1 else ""
        out.append(f"- `{raiz}`{cuenta}")
    out.append("")
    out.append("> Para cada uno que la suite NECESITE, el brief tiene que decir "
               "**ruta y cómo obtenerlo** — no solo su nombre. Un frente que "
               "no lo tiene no ve un fallo: ve un rojo que parece preexistente.")
    return "\n".join(out)


def seccion_flags():
    out = ["### Flags de entorno que mueven la suite — CON SU VALOR", ""]
    nombres = set()
    for py in RAIZ.rglob("*.py"):
        if "_build" in py.parts or "__pycache__" in py.parts:
            continue
        try:
            nombres |= set(LEE_ENTORNO.findall(py.read_text(encoding="utf-8",
                                                            errors="replace")))
        except OSError:
            continue
    # Ruido del intérprete, no interruptores del repo.
    nombres -= {"PATH", "HOME", "TMPDIR", "LOCALAPPDATA", "APPDATA", "USERPROFILE"}
    if not nombres:
        out.append("- _Ningún `os.environ` en el repo: no hay interruptores._")
        return "\n".join(out)
    out.append("Descubiertos grepeando `os.environ`/`getenv` en el repo — los "
               "interruptores que existen son los que el código lee, no los que "
               "alguien recuerde:")
    out.append("")
    for n in sorted(nombres):
        v = os.environ.get(n)
        out.append(f"- `{n}` = " + (f"`{v}`" if v is not None else "_sin poner_"))
    out.append("")
    out.append("> **El baseline no es un número: es un número más el estado de "
               "estos interruptores.** En campo, 42 de 51 skips eran UNA sola "
               "variable. `DEBUG=1` y `DEBUG=0` no son el mismo inventario.")
    return "\n".join(out)


def corre_suite(cwd, etiqueta):
    """(texto, segundos) de una corrida, o (None, motivo). No interpreta: el
    conteo lo lee quien despacha, porque cada runner lo imprime a su manera y
    adivinarlo sería inventar — que es lo único que este fichero no hace."""
    t0 = time.time()
    try:
        p = subprocess.run(CMD_SUITE, shell=True, cwd=str(cwd),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=3600)
    except Exception as exc:
        return None, f"{type(exc).__name__}: no se pudo correr `{CMD_SUITE}`"
    dur = time.time() - t0
    salida = p.stdout.decode("utf-8", "replace")
    cola = "\n".join(salida.rstrip().splitlines()[-12:])
    return (f"**{etiqueta}** — `{CMD_SUITE}` salió **{p.returncode}** en "
            f"**{dur:.0f} s**\n\n```\n{cola}\n```"), dur


def seccion_suite(con_suite, dos):
    out = ["### Firma de la suite", ""]
    if not con_suite:
        out.append(hueco(
            "la firma de una corrida sana (pasan / fallan / SALTAN) no se midió",
            f"{Path(__file__).name} --con-suite",
            "Apagado por defecto porque cuesta minutos (551 s en campo). El "
            "conteo de skips es la señal más barata que existe y casi nadie la "
            "pasa: sin ella, un frente no puede distinguir «me falta un "
            "artefacto» de «esto ya estaba roto»."))
    else:
        texto, motivo = corre_suite(RAIZ, "Este árbol")
        out.append(texto or hueco("la corrida falló", CMD_SUITE, str(motivo)))

    out.append("")
    if not dos:
        out.append(hueco(
            "el SEGUNDO baseline (un worktree recién creado) no se midió",
            f"{Path(__file__).name} --con-suite --dos-baselines",
            "Y es el que más enseña: **no son el mismo número, y esa diferencia "
            "ES el inventario que falta**. Cuatro frentes perdieron una corrida "
            "entera diagnosticando inventario ausente como daño — uno reportó "
            "256 rojos, otro 294."))
    elif con_suite:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="estado-mundo-") as tmp:
            dest = Path(tmp) / "wt"
            _s, e = git(["worktree", "add", "--detach", str(dest), "HEAD"])
            if e:
                out.append(hueco("no se pudo montar el worktree de control",
                                 "git worktree add", e))
            else:
                texto, _m = corre_suite(dest, "Worktree recién creado")
                out.append(texto or hueco("la corrida del worktree falló",
                                          CMD_SUITE, ""))
                git(["worktree", "remove", "--force", str(dest)])
    return "\n".join(out)


def seccion_firma_conocida():
    return "\n".join([
        "### Firma de los fallos de entorno CONOCIDOS",
        "",
        hueco("esto NO se genera: es un juicio, no una medición",
              "escríbelo tú, con la plantilla de abajo",
              "Saber que un rojo es de entorno y no de código pide contexto que "
              "una herramienta no tiene. El material está arriba (los artefactos "
              "de §4 y el conteo de §6); la frase es tuya."),
        "",
        "```",
        "Si ves EXACTAMENTE estos N rojos:",
        "    <ruta::test>",
        "…y M skips, NO son preexistentes: te falta <artefacto> en el worktree.",
        "Tráelo con `<comando>` y vuelve a correr ANTES de reportar nada.",
        "```",
        "",
        "> Seis subagentes reportaron los mismos 2 rojos como «preexistentes». No "
        "lo eran. A partir del quinto brief se les dio la firma exacta y **los "
        "siguientes la resolvieron en vez de reportarla**. La diferencia no fue "
        "el modelo ni la tarea: fue una línea en el brief.",
    ])


def main():
    global RAIZ           # va PRIMERO: declararlo tras usar el nombre es SyntaxError

    argv = sys.argv[1:]
    con_suite = "--con-suite" in argv
    dos = "--dos-baselines" in argv
    # El repo objetivo es un ARGUMENTO, no el repo de esta herramienta. Se
    # despacha en otros repos —`recomendador-cobranza` es el caso vivo— y un
    # generador que solo sabe mirarse a sí mismo obliga a escribir a mano el
    # bloque justo donde más frentes hay. Por defecto, el suyo.
    sueltos = [a for a in argv if not a.startswith("-")]
    if sueltos:
        RAIZ = Path(sueltos[0]).expanduser().resolve()
        if not RAIZ.is_dir():
            print(f"No existe el directorio: {RAIZ}", file=sys.stderr)
            return 1

    if not (RAIZ / ".git").exists() and git(["rev-parse", "--git-dir"])[1]:
        print("No hay repo git que mirar: este bloque no se puede generar.",
              file=sys.stderr)
        return 1

    sello, _ = git(["rev-parse", "--short", "HEAD"])
    print("## 2 · Estado del mundo — GENERADO\n")
    print(f"> Generado por `setup/scripts/{Path(__file__).name}` sobre "
          f"`{sello or '(sin sha)'}`. **No lo edites a mano**: si algo aquí está "
          f"mal, está mal en el repo. Y lo que salga como `HUECO` es un agujero "
          f"declarado, no un descuido — vuelve a generarlo con el flag que dice.\n")

    for seccion in (seccion_base(), seccion_ramas(), seccion_worktrees(),
                    seccion_artefactos(), seccion_flags(),
                    seccion_suite(con_suite, dos), seccion_firma_conocida()):
        print(seccion)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
