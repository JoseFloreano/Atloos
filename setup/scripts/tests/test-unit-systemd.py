#!/usr/bin/env python3
"""
test-unit-systemd.py — La unit del puente declara lo que cree declarar.

POR QUÉ EXISTE (alta de la SER8, 2026-08-17). La unit de systemd es el único
trozo del setup que nadie lee después de escribirlo: se copia una vez, arranca,
y a partir de ahí lo único que se mira es `is-active`. Eso la convierte en el
sitio perfecto para un fallo callado, y ya nos dio dos de esa familia:

  1. `StartLimitIntervalSec` estaba en `[Service]`, donde systemd la IGNORA
     (van en `[Unit]`). Su gemela `StartLimitBurst` sí colaba, por
     compatibilidad heredada y SIN avisar. Medido en la SER8 con systemd 255:
     la plantilla declaraba «10 arranques en 600 s» y `systemctl show`
     devolvía `Burst=10` con la ventana por defecto de `10 s`. Media política
     aplicada, ningún error a la vista.
  2. Un `CLAUDE_CONFIG_DIR` apuntando a un perfil propio deja al bot SIN los
     6 hooks de la capa 3 (auditoría 31, H4). El bot sigue respondiendo —por
     eso no se nota—: lo que desaparece es la vigilancia.

QUÉ AFIRMA, sobre la PLANTILLA versionada (`claude-telegram.service.example`),
que es lo comprobable en estático desde cualquier máquina:

  - `ExecStart` invoca el intérprete del venv, no un `python3` del sistema.
  - No hay `CLAUDE_CONFIG_DIR` en ninguna forma.
  - `MemorySwapMax=0` acompaña al `MemoryMax` (sin eso el techo no mata: se
    va a swap, y una máquina headless en swap sigue «arriba»).
  - Las claves `StartLimit*` viven en `[Unit]`.
  - `Restart` es `on-failure` y trae un `RestartSec` explícito.

LO QUE NO AFIRMA, y conviene tenerlo escrito. No mira la copia desplegada en
`~/.config/systemd/user/`: esa es por-máquina, no viaja en el repo, y en la
Legion ni existe. Tampoco juzga el VALOR de `MemoryMax` —sale de la RAM de
cada caja, no de una constante— más allá de exigir que no se quede en el
conservador de 24 GB sin que nadie lo haya mirado. Y no sustituye a
`systemd-analyze --user verify`, que es lo que hay que correr sobre la copia
real: esto cubre el viaje, aquello cubre el destino.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLA = RAIZ / "telegram-bridge" / "claude-telegram.service.example"


def parsea(texto):
    """{seccion: [(clave, valor), ...]}, ignorando comentarios y líneas sueltas.

    Un parser de verdad no hace falta y sería peor: lo que se persigue es
    justamente en qué SECCIÓN cae cada clave, que es lo que systemd mira y lo
    que un `grep` se pierde.
    """
    secciones = {}
    actual = None
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or linea.startswith(";"):
            continue
        if linea.startswith("[") and linea.endswith("]"):
            actual = linea[1:-1]
            secciones.setdefault(actual, [])
            continue
        if actual is None or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        secciones[actual].append((clave.strip(), valor.strip()))
    return secciones


def valor(secciones, seccion, clave):
    for k, v in secciones.get(seccion, []):
        if k == clave:
            return v
    return None


def claves(secciones, seccion):
    return [k for k, _ in secciones.get(seccion, [])]


def a_bytes(valor_gb):
    """`16G` -> 17179869184. None si no se entiende."""
    m = re.fullmatch(r"(\d+)([KMGT]?)", (valor_gb or "").strip())
    if not m:
        return None
    return int(m.group(1)) * {"": 1, "K": 1024, "M": 1024 ** 2,
                              "G": 1024 ** 3, "T": 1024 ** 4}[m.group(2)]


# ── Los checks ────────────────────────────────────────────────────────────
def comprueba(secciones):
    """[(ok, titulo, motivo)] — un motivo solo cuando ok es False."""
    r = []

    ex = valor(secciones, "Service", "ExecStart") or ""
    r.append((("/venv/bin/python" in ex or "claude-telegram/venv" in ex),
              "1. ExecStart usa el intérprete del venv",
              f"ExecStart no apunta al venv: {ex or '(ausente)'}\n"
              "         Con el python del sistema el arranque muere en el "
              "import de telegram\n         y systemd lo reintenta en bucle "
              "sin que el mensaje llegue a nadie."))

    # Un `python3` suelto en posición de comando es el fallo concreto que se
    # persigue; dentro de la ruta del venv la subcadena no aparece.
    r.append((not re.search(r"(^|/|\s)python3(\s|$)", ex),
              "1b. …y no un `python3` del sistema",
              f"ExecStart invoca `python3` a secas: {ex}"))

    todas = [k for s in secciones for k in claves(secciones, s)]
    texto_env = " ".join(v for s in secciones for k, v in secciones[s]
                         if k in ("Environment", "EnvironmentFile"))
    r.append((("CLAUDE_CONFIG_DIR" not in todas
               and "CLAUDE_CONFIG_DIR" not in texto_env),
              "2. Sin CLAUDE_CONFIG_DIR",
              "La unit fija CLAUDE_CONFIG_DIR. Un perfil propio deja al bot "
              "SIN los 6\n         hooks de la capa 3 (auditoría 31, H4). El "
              "ahorro de tokens no paga\n         la vigilancia."))

    wd = valor(secciones, "Service", "WorkingDirectory") or ""
    r.append((wd.endswith("telegram-bridge"),
              "3. WorkingDirectory en setup/telegram-bridge",
              f"WorkingDirectory={wd or '(ausente)'} — el daemon escribe "
              "logs/ ahí."))

    rst = valor(secciones, "Service", "Restart")
    r.append((rst == "on-failure",
              "4. Restart=on-failure",
              f"Restart={rst or '(ausente)'} — `always` ciego reinicia también "
              "una salida\n         limpia y esconde el motivo."))
    r.append((valor(secciones, "Service", "RestartSec") is not None,
              "4b. …con RestartSec explícito",
              "Sin RestartSec el reintento es inmediato y quema la ventana "
              "de arranques."))

    # El hallazgo del 2026-08-17.
    mal = [k for k in claves(secciones, "Service") if k.startswith("StartLimit")]
    r.append((not mal,
              "5. Las StartLimit* NO están en [Service]",
              f"{', '.join(mal)} en [Service]: systemd las ignora ahí "
              "(van en [Unit]).\n         `StartLimitIntervalSec` al menos "
              "avisa en `systemd-analyze verify`;\n         "
              "`StartLimitBurst` cuela por compatibilidad y NO avisa, que es "
              "peor."))
    r.append((any(k.startswith("StartLimit") for k in claves(secciones, "Unit")),
              "5b. …y sí en [Unit]",
              "Ninguna StartLimit* en [Unit]: rige el defecto (5 en 10 s) y "
              "systemd\n         deja el servicio MUERTO tras tres reinicios "
              "rápidos."))

    mx = a_bytes(valor(secciones, "Service", "MemoryMax"))
    hi = a_bytes(valor(secciones, "Service", "MemoryHigh"))
    r.append((mx is not None and hi is not None and hi < mx,
              "6. MemoryHigh por debajo de MemoryMax",
              f"MemoryHigh={valor(secciones, 'Service', 'MemoryHigh')} / "
              f"MemoryMax={valor(secciones, 'Service', 'MemoryMax')} — "
              "High es el freno,\n         Max es el techo; invertidos el "
              "freno no frena."))
    r.append((valor(secciones, "Service", "MemorySwapMax") == "0",
              "7. MemorySwapMax=0",
              "Sin esto MemoryMax no mata: el proceso se va a swap. Una "
              "máquina headless\n         con un agente en swap no está "
              "lenta, está inutilizable — y sigue\n         «arriba», así que "
              "ninguna alarma salta."))

    return r


def autoprueba():
    """El parser distingue la sección, que es lo único que aquí importa."""
    s = parsea("[Unit]\nStartLimitBurst=10\n\n[Service]\n# x=1\nExecStart=/a/b\n")
    if claves(s, "Unit") != ["StartLimitBurst"]:
        return False, "no asigna la clave a [Unit]"
    if claves(s, "Service") != ["ExecStart"]:
        return False, "el comentario `# x=1` se colo como clave"
    malo = parsea("[Service]\nStartLimitBurst=10\n")
    if [c for c in comprueba(malo) if c[1].startswith("5.")][0][0]:
        return False, "no caza StartLimit* en [Service] — es el hallazgo que motiva el arnés"
    if a_bytes("16G") != 16 * 1024 ** 3 or a_bytes("nada") is not None:
        return False, "a_bytes() no convierte los sufijos"
    return True, ""


def main():
    print("\nLa unit de systemd del puente declara lo que cree declarar\n")
    bien, motivo = autoprueba()
    if not bien:
        print(f"  [AUTOPRUEBA] FALLIDA — {motivo}")
        print("\n  El check no está verificado, así que su verde no vale.")
        return 1
    print("  [AUTOPRUEBA] OK — el parser separa por sección y caza el caso "
          "de [Service]\n")

    if not PLANTILLA.is_file():
        print(f"No encuentro {PLANTILLA}")
        return 1

    secciones = parsea(PLANTILLA.read_text(encoding="utf-8"))
    fallos = 0
    for ok, titulo, motivo in comprueba(secciones):
        print(f"  [{'OK  ' if ok else 'ROJO'}] {titulo}")
        if not ok:
            print(f"         {motivo}")
            fallos += 1

    total = len(comprueba(secciones))
    print(f"\n{total - fallos}/{total} casos OK")
    if fallos:
        print(f"\n{fallos} en rojo sobre {PLANTILLA.name}. Esta es la "
              "PLANTILLA:\n"
              "el rojo viaja a toda máquina que la copie.")
        return 1
    print("\nY sobre la copia desplegada, que esto no mira, corre:\n"
          "  systemd-analyze --user verify ~/.config/systemd/user/"
          "claude-telegram.service\n"
          "  systemctl --user show claude-telegram -p MemoryMax -p "
          "StartLimitIntervalUSec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
