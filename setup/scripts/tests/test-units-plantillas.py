#!/usr/bin/env python3
"""
test-units-plantillas.py — Las CUATRO plantillas de systemd, no solo una.

EL HUECO QUE CIERRA (2026-08-20, auditoría). `test-unit-systemd.py` mira una
sola plantilla —`claude-telegram.service.example`— y sus checks son de servicio
(ExecStart al venv, WorkingDirectory, Restart). Las otras tres entraron al repo
sin que nadie mirara nada:

    claude-telegram-vault.timer.example      · el respaldo del vault de la SER8
    claude-telegram-doctor.timer.example     · el latido diario
    claude-telegram-aviso@.service.example   · el aviso de fallo

Aquí van los invariantes que valen para CUALQUIERA de las cuatro, y el que sale
del campo: **si `ExecStart` invoca un script directamente, ese script tiene que
estar ejecutable EN GIT**. `vault-sync.sh` está como `100644`, y el 2026-08-20
en la SER8 invocarlo directo dio `Permission denied` (exit 126) — la unit lo
rodea llamándolo con `/bin/bash`, pero **cualquier receta de la documentación
que lo nombre a secas falla igual**, y eso ya pasó.

LO QUE SE AFIRMA sobre cada plantilla:
  A · todo `ExecStart` apunta a un fichero que existe en el repo
  B · si lo invoca sin intérprete, ese fichero es ejecutable en git  ← el medido
  C · ninguna fija `CLAUDE_CONFIG_DIR` (dejaría al bot sin los 6 hooks; misma
      regla que ya defiende `test-unit-systemd.py` sobre la unit del daemon)
  D · ninguna lleva la ruta absoluta de una máquina concreta: `<REPO>`/`%h` o nada
  E · todo bloque `[Timer]` —aunque venga comentado, que es como se distribuyen—
      trae planificación e `[Install] WantedBy=timers.target`, o el timer se
      instala y no dispara nunca

Uso:  setup/scripts/py setup/scripts/tests/test-units-plantillas.py
Salidas: 0 todo verde · 1 alguna plantilla en rojo
"""
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PUENTE = RAIZ / "telegram-bridge"

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

EJECUTABLE = 0o111


def descomenta(texto):
    """El texto con los bloques de unit comentados devueltos a INI.

    Las plantillas traen la segunda unit comentada con `# ` para que quepan dos
    en un fichero; si no se descomenta, sus claves son invisibles y el check
    pasaría en falso justo sobre lo que hay que mirar.
    """
    fuera = []
    for linea in texto.splitlines():
        limpia = re.sub(r"^#\s?", "", linea)
        if re.match(r"^\[(Unit|Service|Timer|Install)\]\s*$", limpia) or \
           re.match(r"^[A-Z][A-Za-z]+=", limpia):
            fuera.append(limpia)
        else:
            fuera.append(linea)
    return "\n".join(fuera)


def claves(texto, nombre):
    return [l.split("=", 1)[1].strip()
            for l in texto.splitlines()
            if l.strip().startswith(f"{nombre}=")]


def modo_en_git(ruta):
    """El modo con que git guarda el fichero, o None si no lo trackea."""
    p = subprocess.run(["git", "-C", str(RAIZ.parent), "ls-files", "-s", "--",
                        str(ruta.relative_to(RAIZ.parent))],
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30)
    salida = p.stdout.decode("utf-8", "replace").strip()
    return int(salida.split()[0], 8) if salida else None


def resuelve(arg):
    """El fichero del repo que nombra un argumento de ExecStart, o None."""
    if "<REPO>" not in arg and "<RUTA_AL_REPO>" not in arg:
        return None
    rel = re.sub(r"^.*<(?:REPO|RUTA_AL_REPO)>/", "", arg).split()[0]
    return RAIZ.parent / rel


def revisa(plantilla):
    """[(ok, titulo, motivo)] de una plantilla."""
    crudo = plantilla.read_text(encoding="utf-8")
    texto = descomenta(crudo)
    nom = plantilla.name
    r = []

    for ex in claves(texto, "ExecStart"):
        partes = ex.split()
        objetivo = resuelve(ex)
        if objetivo is None:
            continue
        # "Directo" = el fichero del repo ES el comando, no un argumento de otro.
        # Preguntarlo así evita mantener una lista de intérpretes, que además ya
        # falló: el python del venv (`%h/.../venv/bin/python`) no estaba en ella
        # y marcaba `tg_daemon.py` como invocado directo siendo su ARGUMENTO.
        directo = resuelve(partes[0]) == objetivo
        r.append((objetivo.is_file(), f"A · {nom}: ExecStart apunta a un fichero real",
                  f"ExecStart nombra {objetivo}, que no existe en el repo"))
        if directo and objetivo.is_file():
            modo = modo_en_git(objetivo)
            r.append((bool(modo and modo & EJECUTABLE),
                      f"B · {nom}: el script que invoca directo es ejecutable en git",
                      f"{objetivo.name} está en git como {oct(modo or 0)}: "
                      f"invocarlo directo da `Permission denied` (126).\n"
                      f"         Arréglalo con `git update-index --chmod=+x "
                      f"{objetivo.relative_to(RAIZ.parent)}`\n"
                      f"         o llámalo con /bin/bash desde la unit."))

    r.append(("CLAUDE_CONFIG_DIR" not in texto,
              f"C · {nom}: sin CLAUDE_CONFIG_DIR",
              "fija CLAUDE_CONFIG_DIR y eso deja al bot sin los 6 hooks (auditoría 31, H4)"))

    absolutas = re.findall(r"=(?:[^\n]*\s)?(/home/[^\s%<]+|/root/[^\s%<]+)", texto)
    r.append((not absolutas, f"D · {nom}: sin rutas de una máquina concreta",
              f"lleva {absolutas[:2]} — la plantilla viaja, esa ruta no"))

    if "[Timer]" in texto:
        plan = any(claves(texto, k) for k in
                   ("OnCalendar", "OnUnitActiveSec", "OnBootSec", "OnActiveSec"))
        r.append((plan, f"E · {nom}: el [Timer] dice cuándo dispara",
                  "tiene [Timer] sin OnCalendar/OnUnitActiveSec/OnBootSec: no dispara nunca"))
        r.append(("timers.target" in " ".join(claves(texto, "WantedBy")),
                  f"E2 · {nom}: y se engancha a timers.target",
                  "sin `WantedBy=timers.target` el `enable` no lo deja armado tras reiniciar"))
    return r


def autoprueba():
    """El check B tiene que CAZAR el caso malo, no solo aprobar el bueno."""
    real = PUENTE / "vault-sync.sh"
    if not real.is_file():
        return False, "no encuentro vault-sync.sh para la autoprueba"
    modo = modo_en_git(real)
    if modo is None:
        return False, "vault-sync.sh no está trackeado: la autoprueba no mide nada"
    # Se ejerce el predicado, no el fichero: se le dan los dos modos a mano.
    caza = not (0o100644 & EJECUTABLE)
    aprueba = bool(0o100755 & EJECUTABLE)
    if not (caza and aprueba):
        return False, "el predicado del bit de ejecución no distingue 644 de 755"
    return True, ""


def main():
    print("\nLas cuatro plantillas de systemd declaran lo que creen declarar\n")
    bien, motivo = autoprueba()
    if not bien:
        print(f"  [AUTOPRUEBA] FALLIDA — {motivo}\n"
              "  El check no está verificado, así que su verde no vale.")
        return 1
    print("  [AUTOPRUEBA] OK — el predicado del bit de ejecución caza 644 y aprueba 755\n")

    plantillas = sorted(p for p in PUENTE.glob("*.example")
                        if p.name.endswith((".service.example", ".timer.example")))
    if len(plantillas) < 4:
        print(f"  Solo veo {len(plantillas)} plantillas en {PUENTE}. "
              "Esperaba las 4 del puente.")
        return 1

    fallos = total = 0
    for p in plantillas:
        for ok, titulo, mot in revisa(p):
            total += 1
            print(f"  [{'OK  ' if ok else 'ROJO'}] {titulo}")
            if not ok:
                print(f"         {mot}")
                fallos += 1

    print(f"\n{total - fallos}/{total} casos OK sobre {len(plantillas)} plantillas")
    if fallos:
        print("\nEstas son las PLANTILLAS: el rojo viaja a toda máquina que las copie.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
