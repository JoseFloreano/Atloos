#!/usr/bin/env python3
"""
wire-hooks.py — Instala y cablea los hooks de Claude Code. Núcleo del lado
Linux/macOS de `sync-hooks`, y equivalente de `setup/sync-hooks.ps1`.

POR QUÉ EXISTE (sprint 11). `sync-hooks.ps1` era el ÚNICO instalador de hooks
del repo, y solo hablaba PowerShell. Consecuencia literal, medida en la SER8:
en Linux no existían `merge-gate-guard`, `goal-evidence-guard`,
`check-vault-updated`, `memory-flush` ni `mark-code-dirty`. La máquina que corre
sin vigilancia humana era la única sin capa 3 — no es una carencia de
portabilidad, es que el gate no existía donde más falta hace.

QUÉ COMPARTE Y QUÉ NO CON EL .ps1. Comparten la LISTA: los dos leen
`setup/hooks/hooks-map.json`, que es la fuente única. NO comparten la
implementación del copiado y el cableado — el .ps1 sigue siendo el suyo. Es una
deuda declarada, no un descuido: colapsarla obliga a reescribir el instalador
que hoy protege la ruta de Windows, y eso no se hace a mitad de un sprint de
portabilidad sin red del lado Windows. Lo que sostiene la equivalencia mientras
tanto es `setup/scripts/tests/test-sync-hooks-paridad.py`, que compara lo que
registra CADA envoltorio y falla si difieren.

QUÉ HACE, por config dir (`~/.claude` y cada `~/.claude-*`):
  1. Copia `setup/hooks/*.py` a `<cfg>/hooks/`, con manifest y guard por
     CONJUNTOS: un hook que este script instaló y ya no está en la fuente se
     AVISA y no se borra salvo `--prune` (el borrado es opt-in, RFD 10 C1).
  2. Cablea `<cfg>/settings.json` de forma idempotente, y REESCRIBE el matcher
     si cambió — sin eso el cableado decía "ya cableado" y dejaba el matcher
     viejo para siempre, que es el fallo del sprint 7.

Uso:  setup/scripts/py setup/scripts/wire-hooks.py
      setup/scripts/py setup/scripts/wire-hooks.py --no-wire      # solo copia
      setup/scripts/py setup/scripts/wire-hooks.py --prune        # poda huérfanos
      setup/scripts/py setup/scripts/wire-hooks.py --config-dir <dir>   # laboratorio
Salidas: 0 todo bien · 1 error de instalación
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parent.parent          # setup/
FUENTE_DEFECTO = RAIZ / "hooks"


def ok(m):   print(f"  [OK] {m}")
def warn(m): print(f"  [WARN] {m}")
def info(m): print(f"  [INFO] {m}")
def err(m):  print(f"  [ERROR] {m}", file=sys.stderr)


def lee_mapa(fuente):
    """La lista de hooks, desde la fuente única. Un mapa vacío es ERROR.

    Cablear cero hooks en silencio es la misma clase de fallo que el guard por
    conjuntos persigue al copiar: sales con 0 y sin capa 3.
    """
    ruta = fuente / "hooks-map.json"
    if not ruta.is_file():
        err(f"no existe el mapa de hooks: {ruta}")
        return None
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except Exception as e:
        err(f"hooks-map.json ilegible: {e}")
        return None
    entradas = datos.get("hooks") or []
    if not entradas:
        err("hooks-map.json no declara ningún hook: no se cablea nada")
        return None
    for e in entradas:
        if not e.get("file") or not e.get("event"):
            err(f"entrada del mapa sin 'file' o sin 'event': {e!r}")
            return None
    return entradas


def config_dirs(explicito=None):
    """`~/.claude` y cada `~/.claude-*` (multi-cuenta), igual que el .ps1."""
    if explicito:
        return [Path(explicito)]
    home = Path.home()
    dirs = [home / ".claude"]
    try:
        dirs += sorted(p for p in home.glob(".claude-*") if p.is_dir())
    except Exception:
        pass
    return [d for d in dirs if d.is_dir()]


def copia_hooks(fuente, destino, prune):
    """Copia los .py con manifest y guard por conjuntos. → (n_copiados, ok)."""
    origen = sorted(p for p in fuente.glob("*.py") if p.is_file())
    if not origen:
        warn(f"no hay .py en {fuente}")
        return 0, True
    destino.mkdir(parents=True, exist_ok=True)

    manifest = destino / "_sync-hooks.json"
    previos = []
    if manifest.is_file():
        try:
            previos = json.loads(manifest.read_text(encoding="utf-8")).get("hooks") or []
        except Exception:
            previos = []

    nombres = {p.name for p in origen}
    faltantes = [h for h in previos if h and h not in nombres]

    if faltantes and not prune:
        # No se borra y no se actualiza el manifest: que siga recordando los
        # huérfanos, o la próxima corrida los olvida y el aviso desaparece solo.
        print(f"  [HUERFANOS] {len(faltantes)} hooks instalados y NO en la fuente:")
        for f in faltantes:
            print(f"      - {f}")
        print("  Si los retiraste a proposito:  setup/sync-hooks.sh --prune")
    elif faltantes:
        for viejo in faltantes:
            (destino / viejo).unlink(missing_ok=True)
            info(f"podado hook retirado '{viejo}'")

    # .tmp + replace: os.replace es atómico dentro del mismo sistema de ficheros,
    # así que no queda ventana en la que el hook esté a medio escribir.
    for p in origen:
        tmp = destino / (p.name + ".tmp")
        shutil.copyfile(p, tmp)
        os.replace(tmp, destino / p.name)

    if not faltantes or prune:
        manifest.write_text(json.dumps({
            "syncedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": str(fuente),
            "hooks": sorted(nombres),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        warn("manifest NO actualizado: sigue recordando los huerfanos.")

    ok(f"{len(origen)} hooks copiados  (manifest: {len(previos)})")
    return len(origen), True


def cablea(cfg, destino, entradas, python_cmd):
    """Cablea settings.json. Idempotente, y REESCRIBE el matcher si cambió."""
    settings = cfg / "settings.json"
    if settings.is_file():
        crudo = settings.read_text(encoding="utf-8-sig").strip()
    else:
        crudo = ""
    if not crudo:
        crudo = "{}"
    try:
        s = json.loads(crudo)
    except Exception:
        warn("settings.json ilegible, se omite el cableado")
        return False
    if not isinstance(s, dict):
        warn("settings.json no es un objeto, se omite el cableado")
        return False

    presentes = {p.name for p in destino.glob("*.py")}
    s.setdefault("hooks", {})
    cambiado = False

    for h in entradas:
        fichero, evento = h["file"], h["event"]
        matcher = h.get("matcher")
        if fichero not in presentes:
            continue                                  # hook no presente en la fuente
        cmd = f"{python_cmd} {(destino / fichero).as_posix()}"
        lista = s["hooks"].setdefault(evento, [])

        encontrado = reescrito = False
        for entrada in lista:
            if not isinstance(entrada, dict):
                continue
            for inner in entrada.get("hooks") or []:
                if isinstance(inner, dict) and inner.get("command") == cmd:
                    encontrado = True
                    actual = entrada.get("matcher")
                    if actual != matcher:
                        if matcher is None:
                            entrada.pop("matcher", None)
                        else:
                            entrada["matcher"] = matcher
                        cambiado = reescrito = True
                        ok(f"{fichero} → {evento}  (matcher '{actual}' → '{matcher}')")
        if encontrado:
            if not reescrito:
                info(f"{fichero} ya cableado en {evento}")
            continue

        nueva = {"hooks": [{"type": "command", "command": cmd}]}
        if matcher is not None:
            nueva = {"matcher": matcher, "hooks": nueva["hooks"]}
        lista.append(nueva)                            # APENDE: el orden es el del mapa
        cambiado = True
        ok(f"{fichero} → {evento}")

    if cambiado:
        if settings.is_file():
            shutil.copyfile(settings, settings.parent / (settings.name + ".bak"))
        # UTF-8 SIN BOM: un BOM puede romper el parseo de settings.json.
        settings.write_text(json.dumps(s, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        ok("settings.json actualizado (backup en settings.json.bak)")
    else:
        info("settings.json ya estaba al día")
    return True


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--hooks-source", default=str(FUENTE_DEFECTO))
    ap.add_argument("--python-cmd", default="")
    ap.add_argument("--config-dir", default="")
    ap.add_argument("--no-wire", action="store_true")
    ap.add_argument("--prune", action="store_true")
    a = ap.parse_args()

    fuente = Path(a.hooks_source)
    if not fuente.is_dir():
        err(f"no existe la carpeta de hooks: {fuente}")
        return 1
    entradas = lee_mapa(fuente)
    if entradas is None:
        return 1

    # El intérprete que se ESCRIBE en settings.json. Por defecto, el que está
    # corriendo esto: es el único del que tenemos prueba de que arranca — en
    # Windows `python3` existe como alias del Store y MIENTE, así que "el
    # comando existe" no es evidencia de nada.
    python_cmd = a.python_cmd or sys.executable or "python3"

    dirs = config_dirs(a.config_dir or None)
    if not dirs:
        # ⚠ Máquina virgen: Claude Code no ha arrancado nunca aquí, así que
        # `~/.claude` todavía no existe. Antes se avisaba y se salía **0**, y
        # `setup-new-machine.sh` —que llama con `|| warn`— daba el paso por
        # bueno y dejaba la máquina SIN capa 3 (auditoría 31, H2). En una
        # máquina sin vigilancia humana un aviso que nadie lee y un exit 0 son
        # la misma cosa: se CREA el directorio. Y si no se puede, se sale != 0.
        nuevo = Path.home() / ".claude"
        try:
            nuevo.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            err(f"no hay config dir y no se pudo crear {nuevo}: {e}")
            return 1
        info(f"config dir creado: {nuevo} (Claude Code no había arrancado aquí)")
        dirs = [nuevo]

    info(f"Interprete para los hooks: {python_cmd}")
    copiados = 0
    for cfg in dirs:
        print(f"\n> {cfg}")
        destino = cfg / "hooks"
        n, bien = copia_hooks(fuente, destino, a.prune)
        if not bien:
            return 1
        copiados += n
        if not a.no_wire:
            cablea(cfg, destino, entradas, python_cmd)

    # La misma ley por la tercera puerta: `cablea` salta los hooks que no
    # están en la fuente, así que una fuente sin `.py` cableaba NADA y salía 0
    # diciendo "settings.json ya estaba al día". Cero hooks no es éxito.
    if not copiados:
        err("no se instaló ningún hook: la máquina queda SIN capa 3")
        return 1

    print("\nListo. Los hooks aplican en sesiones NUEVAS de Claude Code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
