#!/usr/bin/env python3
"""
_ventana.py — Buscar una MARCA en una ventana de líneas, no en una línea.

No empieza por `test-`, así que `run-tests.py` no lo corre como arnés: es la
pieza que comparten `test-skill-paths.py` (la marca `[repo]`) y
`test-skill-catalog.py` (el hedge "si está instalada"). Una sola copia porque
el número de la ventana es una DECISIÓN, y una decisión con dos copias se
convierte en dos decisiones distintas en cuanto alguien toca una.

POR QUÉ EXISTE — cuatro veces el mismo tropiezo, y ya no es disciplina:

  · sprint 1 · el implementador: el hedge partido por un salto de línea; el
    check no lo vio.
  · sprint 3 · el AUDITOR: un `grep` dio por desaparecidas dos frases gatillo
    partidas por el plegado.
  · sprint 6 · el implementador: `[repo]` en la línea siguiente al comando.
  · sprint 6 · otra vez, y lo dijo él mismo: «segunda vez en dos sprints».

El check mide por línea y la gente escribe cruzando líneas. El propio mensaje
del arnés avisaba —«un hedge partido por el salto no lo ve nadie»— y aun así
mordía a todo el mundo, incluido quien lo escribió. Cuando el aviso ya está
escrito y sigue mordiendo, el que está mal es el check.

EL NÚMERO ES 1, Y SE JUSTIFICA (`RADIO = 1`, ventana de 3 líneas: la anterior,
la propia y la siguiente):

  · Cubre las cuatro instancias reales, que están TODAS a distancia 1 — una
    frase que el plegado parte en dos, o la marca en la línea de justo debajo
    del comando. Ninguna estaba a 2.
  · Y no más, porque el reverso es peor que el fallo: una ventana ancha
    encuentra la marca de OTRO comando y da por bueno lo que no lo es — un
    falso NEGATIVO en un check de seguridad. En los `.md` de este repo, a
    distancia 2 ya suele haber otro bullet o otro bloque de código, así que
    subir a 2 empieza a mezclar vecinos que no tienen nada que ver.

Regla de dedo: la ventana cubre el PÁRRAFO corto donde cabe la marca, no el
bloque. Si un caso real apareciera a distancia 2, se sube el número aquí y se
ajusta el caso de arnés que fija el borde — nunca «por si acaso».

CÓMO SE BUSCA: las líneas de la ventana se unen con un ESPACIO, no con un salto.
Así la ventana resuelve los dos modos de fallo a la vez: la marca en una línea
vecina, y la marca PARTIDA por el salto (`— si` / `está instalada`), que unida
con un salto seguiría sin casar contra un patrón que espera un espacio.
"""

RADIO = 1


def ventana(lineas, i, radio=RADIO):
    """El texto de la ventana centrada en `lineas[i]`, unido por espacios."""
    return " ".join(lineas[max(0, i - radio):i + radio + 1])


def marcada(lineas, i, patron, radio=RADIO):
    """¿La marca `patron` está en la ventana de `lineas[i]`?"""
    return bool(patron.search(ventana(lineas, i, radio)))


def autoprueba(patron, marca, partida=None):
    """(bool, motivo). Los DOS bordes de la ventana, con la marca real del check.

    Un check que solo prueba «la marca dentro pasa» no distingue RADIO=1 de
    RADIO=50: cualquier ventana más ancha también pasaría, y el falso negativo
    —encontrar la marca de otro comando— entraría sin que nada se pusiera rojo.
    Por eso se exige también que a distancia RADIO+1 SIGA bloqueando.

    `partida` es opcional: dos trozos que SOLO juntos forman la marca, para
    fijar el otro modo de fallo —el del sprint 1— en los checks cuya marca es
    una frase y no un token.
    """
    relleno = "una linea cualquiera sin nada que ver"
    dentro = [relleno] * 4
    dentro[2 + RADIO] = marca                      # a distancia exacta RADIO
    if not marcada(dentro, 2, patron):
        return False, (f"la marca a distancia {RADIO} NO se ve: la ventana no "
                       f"resuelve el caso real (marca justo debajo del comando)")

    fuera = [relleno] * (4 + RADIO + 1)
    fuera[2 + RADIO + 1] = marca                   # a distancia RADIO + 1
    if marcada(fuera, 2, patron):
        return False, (f"la marca a distancia {RADIO + 1} TAMBIÉN se ve: la "
                       f"ventana es demasiado ancha y encontrará la marca de "
                       f"otro comando — falso negativo, peor que no encontrarla")

    if partida:
        trozo_a, trozo_b = partida
        if patron.search(trozo_a) or patron.search(trozo_b):
            return False, ("el caso de marca PARTIDA está mal construido: cada "
                           "trozo ya casa por su cuenta, así que no prueba nada")
        if not marcada([relleno, trozo_a, trozo_b, relleno], 1, patron):
            return False, ("una marca partida por el salto de línea sigue sin "
                           "verse: es el fallo del sprint 1, intacto")
    return True, ""
