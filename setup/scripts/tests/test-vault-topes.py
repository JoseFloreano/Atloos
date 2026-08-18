#!/usr/bin/env python3
"""
test-vault-topes.py — Mide el techo de `_PROJECT.md` en vez de escribirlo.

Por qué existe (2026-08-18): los umbrales del tablero —**blando 120, duro
150**— los fija el paso 7 de `session-close` y los repite `vault-drift-audit`,
y **nadie los mide**. Se cumplen a mano, en el ritual de cierre, por un agente
que tiene que acordarse de correr `wc -l`. El historial del propio `_PROJECT.md`
de Atloos dice cómo termina eso: *"08-09 149 lineas · 2.o aviso,
INCUMPLIMIENTO"*, *"08-11 151 lineas · rebaso el DURO"*, y el del copiloto llegó
a **327**, se podó a 203 y **volvió a subir en una tarde**.

Es la tesis del RFD 11 otra vez —la convención escrita no muerde— y es el mismo
patrón que ya se cerró seis veces en este repo: el tope de 500 palabras dentro
de una cadena de texto (auditoría 22, H7), el 450 dentro de un comentario
(sprint 9, S4b), el presupuesto del snippet dentro de su cabecera (sprint 14,
S2b). **Escrito, no vigilado.** La cura no es recordarlo mejor: es que la suite
lo diga en cada corrida.

MEDIDO AL NACER (2026-08-18, este árbol):

    tt1-revisor-chatbot     66     holgado
    atloos                 120     justo en el blando
    alphadogs              149     a UNA línea del duro, y nadie lo sabía

Nace en verde y ya dice algo verdadero: `alphadogs` está a una línea de romper
el techo duro. Eso es un alambre puesto antes de que alguien lo pise, no un
refactor pendiente — la misma forma en que nació el tope duro de 500.

EL VAULT NO ES EL REPO, Y ESO GOBIERNA TODO EL DISEÑO. Este arnés mide ficheros
que viven fuera del checkout, en una ruta distinta por máquina (OneDrive en la
multi-laptop, `$HOME/DevSetup` en la single — la regla la fija
`setup-new-machine.sh:19-31`). De ahí las dos decisiones que más importan:

  1. **Vault ausente = [SKIP], nunca hallazgo.** Es B1 de la auditoría 22
     aplicado antes de que muerda: `gate-test.py` corre la suite en la raíz del
     worktree, así que un arnés que se pone rojo por un fichero que no está
     **impediría producir el verde que el propio gate exige**. Y la SER8 corre
     sin nadie mirando: un rojo permanente ahí se vuelve ruido en una jornada.
  2. **El [SKIP] dice la ruta que buscó.** Un salto silencioso es un verde
     falso en miniatura, y en multi-laptop sería el modo de fallo normal.

LOS TRES SITIOS QUE ESCRIBEN EL NÚMERO, y por eso el check 2. `120/150` vive
hoy en `session-close/SKILL.md` (paso 7, el normativo), en
`vault-drift-audit/references/checks.md` (dos veces) y en el comentario de
cabecera de cada `_PROJECT.md` que lo declara. Cuatro puntos de consumo donde
editar uno no obliga a editar los otros: es exactamente la enfermedad de
`test-claude-md-drift.py`, y aquí se cierra por el mismo método que el check 6
del catálogo usa con el snippet — **lo declarado tiene que coincidir con lo que
mide el arnés**, o el hallazgo dice cuál miente.

CÓMO SE CUENTAN LAS LÍNEAS, declarado porque el contrato humano dice `wc -l` y
las dos cuentas pueden diferir. Se usa `splitlines()`, que para cualquier
fichero terminado en `\n` —todos, git los normaliza— da EXACTAMENTE lo mismo que
`wc -l`. En el caso patológico de un fichero sin salto final, `splitlines()`
cuenta **una más** que `wc -l`. Se elige a propósito la que cuenta de más: un
arnés que se equivoca tiene que hacerlo en la dirección incómoda, no en la
cómoda. La dirección cómoda —contar de menos— es la que dejó pasar el escalar
plano multilínea del sprint 3b.

LÍMITE DECLARADO: esto mide LÍNEAS, que es lo que el contrato pide, y las
líneas no son contenido. Un `_PROJECT.md` de 119 líneas de relleno pasa. El
tablero de checkboxes (crear >12, disolver ≤8), las secciones `## Hecho`
prohibidas y la frescura contra la actividad del repo los mira
`vault-drift-audit`, que corre en Cowork con el vault conectado y tiene contexto
para juzgar. Este arnés hace lo que una máquina puede hacer sin juicio, y lo
hace en cada corrida de la suite.

Uso:  setup/scripts/py setup/scripts/tests/test-vault-topes.py [ruta/al/vault]
      Sin argumento se resuelve por las rutas candidatas del setup, y
      `ATLOOS_VAULT` manda sobre todas.
Salidas: 0 nadie pasa el techo duro (o no hay vault que medir) · 1 hay hallazgos
"""
import io
import contextlib
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
SKILLS = SETUP / "skills"

# Los DOS umbrales del paso 7 de `session-close`. Distintos y con oficios
# distintos, igual que SATURACION/TOPE_DURO en `test-skill-catalog.py`:
#   · 120 (blando) → AVISO. Es el número que el ritual cita y el que se cumple
#     a mano; dice "toca rotar algo a sessions/". No tumba la suite.
#   · 150 (duro)   → BLOQUEA. 150 es el último valor admisible; 151 pone rojo.
# El blando NO bloquea a propósito: podar el fichero es una decisión con juicio
# —qué se va a sessions/ y qué se queda— y un check que la forzara convertiría
# un aviso en una guillotina. Misma razón que la caducidad del catálogo.
TECHO_BLANDO = 120
TECHO_DURO = 150

# Dónde puede vivir el vault. El orden y las rutas los dicta
# `setup-new-machine.sh:19-31`, no este fichero: multi-laptop lo pone bajo
# OneDrive, single-laptop bajo $HOME. Escribir aquí una lista propia sería el
# segundo catálogo de siempre.
CANDIDATOS = ("OneDrive/DevSetup/ObsidianVault", "DevSetup/ObsidianVault")
ENV_VAULT = "ATLOOS_VAULT"

# Los OTROS sitios donde el número está escrito, y que por tanto pueden
# divergir. `session-close` es el normativo (paso 7) y declara los dos juntos en
# una forma greppable; `vault-drift-audit` los repite en prosa.
NORMATIVO = SKILLS / "shared" / "session-close" / "SKILL.md"
SEGUNDO_CONSUMO = SKILLS / "cowork" / "vault-drift-audit" / "references" / "checks.md"
DECLARACION = re.compile(r"blando\s+(\d+)\s*,\s*duro\s+(\d+)", re.I)

# El comentario de cabecera que algunos `_PROJECT.md` llevan:
#   "Tope: 120 líneas (duro 150)."
# Es el cuarto punto de consumo y el más peligroso, porque es el que lee el
# agente que está editando el fichero en ese momento.
TOPE_EN_NOTA = re.compile(r"Tope:\s*(\d+)\s*l[ií]neas\s*\(\s*duro\s+(\d+)\s*\)", re.I)


def lineas(texto):
    """Líneas del fichero. Es la unidad de LOS DOS umbrales.

    En una sola función a propósito: medir el aviso de una forma y el bloqueo de
    otra es el defecto que esta casa persigue, cometido dentro del propio arnés.
    Equivale a `wc -l` para todo fichero terminado en salto — ver la cabecera.
    """
    return len(texto.replace("\r", "").splitlines())


def excede_duro(n):
    """¿Pasa del techo duro? 150 es el último admisible; 151 bloquea.

    Función y no un `>` suelto para que la autoprueba ejerza LA MISMA decisión
    que corre en producción. Un check verificado contra una reimplementación no
    está verificado: está duplicado.
    """
    return n > TECHO_DURO


def excede_blando(n):
    """¿Pasa del techo blando? Avisa, no bloquea."""
    return n > TECHO_BLANDO


def resuelve_vault(argv):
    """(ruta, motivo). `ruta` es None si no hay vault en esta máquina.

    Una ruta explícita se respeta aunque no exista: si la pides a propósito y no
    está, ese es un error tuyo y no del entorno — misma regla que el
    `explicito=True` de `test-claude-md-drift.py`.
    """
    if argv:
        p = Path(argv[0]).expanduser()
        return p, f"ruta explícita: {p}"
    env = os.environ.get(ENV_VAULT)
    if env:
        p = Path(env).expanduser()
        return p, f"${ENV_VAULT}: {p}"
    for rel in CANDIDATOS:
        p = Path.home() / rel
        if (p / "10-Projects").is_dir():
            return p, f"candidato del setup: {p}"
    buscadas = " · ".join(str(Path.home() / r) for r in CANDIDATOS)
    return None, buscadas


def notas_de(vault):
    """[(proyecto, ruta)] de los `_PROJECT.md` bajo `10-Projects/`, ordenados."""
    base = vault / "10-Projects"
    if not base.is_dir():
        return []
    return sorted((d.name, d / "_PROJECT.md") for d in base.iterdir()
                  if d.is_dir() and (d / "_PROJECT.md").is_file())


def revisa_nota(texto, etiqueta):
    """(n_lineas, hallazgos, avisos) de UNA nota ya leída.

    Separada de la lectura para que las autopruebas ejerzan el camino real sobre
    un texto fabricado, sin tocar el vault de verdad ni escribir en disco.
    """
    n = lineas(texto)
    hall, avisos = [], []
    if excede_duro(n):
        hall.append(f"{etiqueta}: {n} líneas — POR ENCIMA del techo duro de "
                    f"{TECHO_DURO} (+{n - TECHO_DURO}). El arreglo no es subir "
                    f"el número: es rotar lo que pasó a `sessions/`")
    elif excede_blando(n):
        avisos.append(f"{etiqueta}: {n} líneas — pasa el blando de "
                      f"{TECHO_BLANDO} (+{n - TECHO_BLANDO}), quedan "
                      f"{TECHO_DURO - n} hasta el duro")
    # El cuarto punto de consumo: el propio fichero declarando su tope. Si
    # miente, miente justo delante del agente que lo está editando.
    m = TOPE_EN_NOTA.search(texto)
    if m and (int(m.group(1)), int(m.group(2))) != (TECHO_BLANDO, TECHO_DURO):
        hall.append(f"{etiqueta}: su cabecera declara «Tope: {m.group(1)} líneas "
                    f"(duro {m.group(2)})» y los umbrales vigentes son "
                    f"{TECHO_BLANDO}/{TECHO_DURO} — el número que lee quien "
                    f"edita el fichero es el equivocado")
    return n, hall, avisos


def revisa_declaraciones():
    """Los sitios que ESCRIBEN el número deben coincidir con el que se mide.

    Sin esto el arnés sería un quinto punto de consumo en vez de la cura: alguien
    cambiaría el 120 en `session-close` y aquí seguiría midiendo 120 sin que nada
    lo dijera. Es el método del check 6 del catálogo, aplicado a cuatro sitios.
    """
    hall = []
    if not NORMATIVO.is_file():
        hall.append(f"no existe {NORMATIVO.relative_to(SETUP)}: es el paso 7 que "
                    f"fija los umbrales, y sin él este arnés mide un contrato "
                    f"que ya no está escrito en ninguna parte")
    else:
        m = DECLARACION.search(NORMATIVO.read_text(encoding="utf-8"))
        if not m:
            hall.append(f"{NORMATIVO.name} (session-close) no declara los "
                        f"umbrales en la forma «blando N, duro M»: sin "
                        f"declaración no hay nada que contrastar")
        elif (int(m.group(1)), int(m.group(2))) != (TECHO_BLANDO, TECHO_DURO):
            hall.append(f"session-close declara «blando {m.group(1)}, duro "
                        f"{m.group(2)}» y este arnés mide {TECHO_BLANDO}/"
                        f"{TECHO_DURO}. El normativo es el paso 7: o se sube el "
                        f"arnés al número del contrato, o se cambia el contrato "
                        f"— pero no pueden discrepar")
    if SEGUNDO_CONSUMO.is_file():
        # Aquí la regla es DELIBERADAMENTE floja: los números aparecen en prosa
        # («> 120 líneas», «por encima de 120») y exigir una forma exacta daría
        # falsos positivos, que es lo que hace que alguien apague un check.
        texto = SEGUNDO_CONSUMO.read_text(encoding="utf-8")
        faltan = [str(v) for v in (TECHO_BLANDO, TECHO_DURO)
                  if not re.search(rf"\b{v}\b", texto)]
        if faltan:
            hall.append(f"vault-drift-audit/{SEGUNDO_CONSUMO.name} ya no cita "
                        f"{' ni '.join(faltan)}: repite estos umbrales en prosa "
                        f"y se está separando del paso 7")
    return hall


def autoprueba_bordes():
    """Mutación: los DOS lados de los DOS bordes, con la decisión real.

    Un check que solo prueba que 151 bloquea no distingue «duro en 150» de «duro
    en 0»: cualquier umbral más bajo también bloquearía y este caso no lo
    notaría. Y el blando se ejerce aparte porque su oficio es NO bloquear —si
    algún día alguien lo hace bloqueante por descuido, la suite se pondría roja
    en dos proyectos de tres y el arnés duraría una tarde.
    """
    nota = lambda n: "l\n" * n                                   # noqa: E731
    if lineas(nota(TECHO_DURO)) != TECHO_DURO:
        return False, (f"el contador no cuenta líneas: {lineas(nota(TECHO_DURO))} "
                       f"donde hay {TECHO_DURO}")
    _n, hall, _a = revisa_nota(nota(TECHO_DURO), "(autoprueba)")
    if hall:
        return False, f"{TECHO_DURO} líneas exactas deberían pasar, y bloquean"
    _n, hall, _a = revisa_nota(nota(TECHO_DURO + 1), "(autoprueba)")
    if not hall:
        return False, (f"{TECHO_DURO + 1} líneas NO producen hallazgo — el techo "
                       f"duro vuelve a ser decorativo, que es el patrón que este "
                       f"arnés existe para cerrar")
    _n, hall, avisos = revisa_nota(nota(TECHO_BLANDO + 1), "(autoprueba)")
    if hall or not avisos:
        return False, (f"{TECHO_BLANDO + 1} líneas deberían AVISAR y no bloquear; "
                       f"salieron {len(hall)} hallazgo(s) y {len(avisos)} aviso(s)")
    _n, _h, avisos = revisa_nota(nota(TECHO_BLANDO), "(autoprueba)")
    if avisos:
        return False, f"{TECHO_BLANDO} líneas exactas deberían pasar, y avisan"
    if TECHO_BLANDO > TECHO_DURO:
        return False, (f"el blando ({TECHO_BLANDO}) está por encima del duro "
                       f"({TECHO_DURO}): el aviso no llegaría antes que el corte")
    # Y la cabecera que miente, que es el hallazgo del cuarto punto de consumo.
    mentirosa = f"<!--\n  Tope: {TECHO_BLANDO - 20} líneas (duro {TECHO_DURO})\n-->\n"
    _n, hall, _a = revisa_nota(mentirosa, "(autoprueba)")
    if not any("cabecera declara" in h for h in hall):
        return False, ("una nota cuya cabecera declara un tope distinto del "
                       "vigente NO da hallazgo: el número que lee quien edita "
                       "puede mentir sin que nada lo diga")
    return True, ""


def autoprueba_entorno():
    """Sin vault en la máquina, el arnés no puede producir hallazgos.

    Es B1 de la auditoría 22 convertido en caso. La suite corre en la raíz de un
    worktree y en la SER8 sin nadie mirando; un rojo por un fichero que vive en
    otra máquina impediría producir el verde que el gate exige. Se ejerce con un
    directorio temporal vacío, que es exactamente lo que tiene una laptop sin el
    vault sincronizado.
    """
    with tempfile.TemporaryDirectory() as tmp:
        vacio = Path(tmp) / "sin-vault"
        if notas_de(vacio):
            return False, "un vault inexistente devuelve notas que medir"
        with contextlib.redirect_stdout(io.StringIO()):
            ruta, _motivo = resuelve_vault([str(vacio)])
        if ruta != vacio:
            return False, ("una ruta explícita no se respeta: el arnés mediría "
                           "otro vault que el que le pidieron")
    return True, ""


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    print("Techo de `_PROJECT.md` en el vault\n")

    ok_bordes, motivo_bordes = autoprueba_bordes()
    print(f"  [AUTOPRUEBA] {'OK' if ok_bordes else 'FALLIDA'} — {TECHO_DURO} "
          f"líneas pasan y {TECHO_DURO + 1} bloquean; {TECHO_BLANDO + 1} avisa "
          f"sin bloquear"
          + (f"\n               {motivo_bordes}" if not ok_bordes else ""))
    ok_entorno, motivo_entorno = autoprueba_entorno()
    print(f"  [AUTOPRUEBA] {'OK' if ok_entorno else 'FALLIDA'} — una máquina sin "
          f"el vault NO produce hallazgos"
          + (f"\n               {motivo_entorno}" if not ok_entorno else ""))

    hallazgos = revisa_declaraciones()

    vault, motivo = resuelve_vault(argv)
    if vault is None:
        print(f"\n  [SKIP] no hay vault en esta máquina. Buscado en: {motivo}\n"
              f"         (y `${ENV_VAULT}` sin poner). El vault vive fuera del\n"
              f"         checkout y su ruta cambia por máquina: ausencia NO es\n"
              f"         incumplimiento, y con esto en rojo el gate no podría\n"
              f"         producir su verde.")
        notas = []
    else:
        print(f"\n  [VAULT] {motivo}")
        notas = notas_de(vault)
        if not notas:
            print(f"  [SKIP] {vault}/10-Projects/ sin ningún `_PROJECT.md` que "
                  f"medir")

    avisos = []
    if notas:
        print(f"\n  {'Proyecto':<26}{'Líneas':>7}   estado")
        for proyecto, ruta in notas:
            n, h, a = revisa_nota(ruta.read_text(encoding="utf-8"), proyecto)
            hallazgos.extend(h)
            avisos.extend(a)
            if excede_duro(n):
                estado = f"ROJO — pasa el duro de {TECHO_DURO}"
            elif excede_blando(n):
                estado = f"aviso — a {TECHO_DURO - n} del duro"
            else:
                estado = f"{TECHO_BLANDO - n} de margen al blando"
            print(f"  {proyecto:<26}{n:>7}   {estado}")

    if avisos:
        print(f"\n  {len(avisos)} por encima del blando de {TECHO_BLANDO} "
              f"(AVISO, no bloquea — podar es una decisión con juicio):\n")
        for a in avisos:
            print(f"    {a}")

    if hallazgos:
        print(f"\n  {len(hallazgos)} hallazgo(s):\n")
        for h in hallazgos:
            print(f"    [FALLA] {h}")
    elif notas:
        print(f"\n  [OK] ninguna nota pasa el techo duro de {TECHO_DURO}, y los "
              f"sitios que\n       escriben los umbrales dicen {TECHO_BLANDO}/"
              f"{TECHO_DURO}, que es lo que aquí se mide.")

    return 1 if (hallazgos or not ok_bordes or not ok_entorno) else 0


if __name__ == "__main__":
    sys.exit(main())
