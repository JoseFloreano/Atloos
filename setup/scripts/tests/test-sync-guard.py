#!/usr/bin/env python3
"""
test-sync-guard.py — Arnés de contrato del guard de borrado de sync-skills.

Por qué existe: en campo (2026-08-05) una enumeración parcial de la fuente hizo
que la corrida SIGUIENTE borrase 2 skills de `~/.claude/skills` imprimiendo
`[OK]` y sin un solo error. El guard del RFD 10 C1 cierra eso; esto lo prueba.

**Nunca toca la instalación real.** Cada caso monta una fuente y un destino de
laboratorio en un temporal, corre el script apuntando ahí, y verifica el
FILESYSTEM — no la salida.

Uso:  setup/scripts/py setup/scripts/tests/test-sync-guard.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# La consola de Windows es cp1252 y este arnés imprime flechas y acentos: sin
# esto revienta con UnicodeEncodeError antes del primer caso (mismo motivo por
# el que los hooks reconfiguran stderr).
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

RAIZ = Path(__file__).resolve().parents[2]          # setup/
PS1 = RAIZ / "sync-skills.ps1"
FALLOS = []


def ok(msg):   print(f"  [OK] {msg}")
def fail(msg): print(f"  [FALLO] {msg}"); FALLOS.append(msg)


def monta(base, skills, manifest_skills):
    """Fuente de laboratorio + destino con manifest previo."""
    fuente = base / "setup" / "skills"
    for cat in ("shared", "claude-code", "cowork", "_template"):
        (fuente / cat).mkdir(parents=True, exist_ok=True)
    for nombre in skills:
        d = fuente / "shared" / nombre
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"---\nname: {nombre}\n---\n# {nombre}\n",
                                    encoding="utf-8")
    # el script resuelve la fuente desde su propia ubicación: se copia ahí
    shutil.copy2(PS1, base / "setup" / "sync-skills.ps1")
    (base / "setup" / "scripts").mkdir(parents=True, exist_ok=True)

    cfg = base / "cfgdir" / ".claude"
    destino = cfg / "skills"
    destino.mkdir(parents=True, exist_ok=True)
    for nombre in manifest_skills:                   # ya "instaladas"
        d = destino / nombre
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"# {nombre} (instalada)\n", encoding="utf-8")
    (destino / "_onedrive-sync.json").write_text(
        json.dumps({"syncedAt": "2026-01-01 00:00", "source": str(fuente),
                    "skills": manifest_skills}), encoding="utf-8")
    return fuente, destino


def corre(base, prune=False):
    """Corre el script con USERPROFILE apuntando al laboratorio."""
    env = dict(os.environ)
    env["USERPROFILE"] = str(base / "cfgdir")
    args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(base / "setup" / "sync-skills.ps1"), "-NoCoworkBuild"]
    if prune:
        args.append("-Prune")
    return subprocess.run(args, capture_output=True, text=True, env=env,
                          cwd=str(base), timeout=180)


def instaladas(destino):
    return {p.name for p in destino.iterdir() if p.is_dir() and not p.name.endswith(".tmp")}


# ── Caso 1: subenumeración (manifest 3, fuente 2) → NO borra, las grita ──────
def caso_subenumeracion():
    print("\nCaso 1 · manifest tiene 3, la fuente solo 2 → no debe borrar nada")
    with tempfile.TemporaryDirectory() as t:
        base = Path(t)
        _, destino = monta(base, ["alfa", "beta"], ["alfa", "beta", "gamma"])
        r = corre(base)
        vivas = instaladas(destino)
        if "gamma" in vivas:
            ok("'gamma' NO fue borrada (el guard la protegió)")
        else:
            fail("'gamma' fue BORRADA pese a no usar -Prune")
        if "gamma" in r.stdout and ("HUERFANA" in r.stdout.upper()):
            ok("la gritó como huérfana, por nombre")
        else:
            fail(f"no gritó la huérfana. stdout:\n{r.stdout[-500:]}")
        if "-Prune" in r.stdout:
            ok("dio el comando exacto para podarla")
        else:
            fail("no dio el comando de poda")
        man = json.loads((destino / "_onedrive-sync.json").read_text(encoding="utf-8-sig"))
        if "gamma" in man["skills"]:
            ok("el manifest NO se reescribió: sigue recordando 'gamma'")
        else:
            fail("el manifest se reescribió y perdió memoria de 'gamma'")


# ── Caso 2: retirada real + -Prune → sí borra ───────────────────────────────
def caso_prune():
    print("\nCaso 2 · retirada real + -Prune → debe borrar")
    with tempfile.TemporaryDirectory() as t:
        base = Path(t)
        _, destino = monta(base, ["alfa", "beta"], ["alfa", "beta", "gamma"])
        corre(base, prune=True)
        vivas = instaladas(destino)
        if "gamma" not in vivas:
            ok("'gamma' podada con -Prune")
        else:
            fail("-Prune no borró la huérfana")
        if {"alfa", "beta"} <= vivas:
            ok("las vigentes siguen instaladas")
        else:
            fail(f"se perdieron skills vigentes: {vivas}")


# ── Caso 3: doble corrida sana → idempotente y sin huérfanas ────────────────
def caso_doble_corrida():
    print("\nCaso 3 · dos corridas sanas seguidas → conjuntos idénticos")
    with tempfile.TemporaryDirectory() as t:
        base = Path(t)
        _, destino = monta(base, ["alfa", "beta"], ["alfa", "beta"])
        r1 = corre(base); v1 = instaladas(destino)
        r2 = corre(base); v2 = instaladas(destino)
        if v1 == v2 == {"alfa", "beta"}:
            ok(f"idempotente: {sorted(v1)}")
        else:
            fail(f"no idempotente: {sorted(v1)} vs {sorted(v2)}")
        if "HUERFANA" not in r2.stdout.upper():
            ok("sin huérfanas espurias en la segunda corrida")
        else:
            fail("gritó huérfanas donde no las hay")
        if "manifest:" in r2.stdout:
            ok("el conteo sale contrastado contra el manifest")
        else:
            fail(f"el conteo no se contrasta. stdout:\n{r2.stdout[-300:]}")
        if not list(destino.glob("*.tmp")):
            ok("no quedaron .tmp huérfanos")
        else:
            fail("quedaron .tmp sin renombrar")


if __name__ == "__main__":
    if os.name != "nt":
        print("Este arnés prueba el .ps1: requiere Windows. Omitido.")
        sys.exit(0)
    print("Arnés del guard de borrado (RFD 10 C1) — laboratorio, no toca ~/.claude")
    caso_subenumeracion()
    caso_prune()
    caso_doble_corrida()
    print()
    if FALLOS:
        print(f"FALLARON {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print("  -", f)
        sys.exit(1)
    print("Todo verde.")
