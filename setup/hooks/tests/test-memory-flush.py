#!/usr/bin/env python3
"""
test-memory-flush.py — Arnés de contrato de setup/hooks/memory-flush.py (PreCompact).

Reconstruye el arnés de 10 casos con el que se validó el hook el 2026-08-01 (que
vivía en el scratchpad y se perdió). Se re-corre ante cualquier cambio en el
sistema anti-drift: memory-flush comparte el flag `.claude/vault-dirty.json` con
mark-code-dirty y check-vault-updated, así que un cambio en el flag lo afecta.

Aislamiento: proyecto temporal + vault falso (se apunta `OneDrive` a un temp).
El nombre del proyecto es el de la carpeta temporal — aleatorio —, así que aunque
la búsqueda del vault cayera al OneDrive real no encontraría nada suyo.

Uso:  setup/scripts/py setup/hooks/tests/test-memory-flush.py
Salida: una línea por caso + resumen; exit 1 si algo falla.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HOOK = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "memory-flush.py"))

SESSION = "sess-flush-0001"
results = []


def run_hook(project_dir, vault_root, session=SESSION, stdin=None):
    payload = json.dumps({
        "session_id": session,
        "hook_event_name": "PreCompact",
        "trigger": "manual",
        "custom_instructions": "",
    }).encode("utf-8")
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = project_dir
    env["OneDrive"] = vault_root
    env.pop("ONEDRIVE", None)
    p = subprocess.run([sys.executable, HOOK],
                       input=payload if stdin is None else stdin,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       cwd=project_dir, env=env)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def write_flag(project_dir, **kw):
    d = os.path.join(project_dir, ".claude")
    os.makedirs(d, exist_ok=True)
    state = {"session_id": SESSION, "last_code_edit": time.time(), "enforced": False}
    state.update(kw)
    with open(os.path.join(d, "vault-dirty.json"), "w", encoding="utf-8") as f:
        json.dump(state, f)
    return state


def read_flag(project_dir):
    fp = os.path.join(project_dir, ".claude", "vault-dirty.json")
    if not os.path.exists(fp):
        return None
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_flag(project_dir):
    fp = os.path.join(project_dir, ".claude", "vault-dirty.json")
    if os.path.exists(fp):
        os.remove(fp)


def touch(path, mtime=None, content="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    print(f"[{'OK  ' if condition else 'FALLA'}] {name}"
          + (f" -- {detail}" if detail and not condition else ""))


def main():
    with tempfile.TemporaryDirectory(prefix="mf-proj-") as proj, \
            tempfile.TemporaryDirectory(prefix="mf-vault-") as vault:
        proj, vault = os.path.realpath(proj), os.path.realpath(vault)
        name = os.path.basename(proj)
        pdir = os.path.join(vault, "DevSetup", "ObsidianVault", "10-Projects", name)
        project_md = os.path.join(pdir, "_PROJECT.md")

        # 1. Sin flag: la sesión no tocó código -> silencio total.
        touch(project_md, mtime=time.time() - 3600)
        clear_flag(proj)
        rc, err = run_hook(proj, vault)
        check("1. sin flag -> exit 0 y sin mensaje", rc == 0 and err.strip() == "")

        # 2. Flag + vault viejo -> bloquea la compactación con el recordatorio.
        write_flag(proj)
        rc, err = run_hook(proj, vault)
        check("2. flag + vault viejo -> exit 2 con recordatorio",
              rc == 2 and "Compactaci" in err and name in err, f"rc={rc}")

        # 3. Deja marcado que ya avisó.
        check("3. marca precompact_flushed en el flag",
              (read_flag(proj) or {}).get("precompact_flushed") is True)

        # 4. Segunda compactación de la misma sesión -> deja pasar.
        rc, err = run_hook(proj, vault)
        check("4. segunda compactacion -> exit 0 mudo", rc == 0 and err.strip() == "")

        # 5. Flag de otra sesión: no es asunto suyo (lo limpia el hook Stop).
        write_flag(proj, session_id="otra-sesion")
        rc, err = run_hook(proj, vault)
        check("5. flag de otra sesion -> exit 0", rc == 0 and err.strip() == "")

        # 6. _PROJECT.md actualizado DESPUÉS del código -> vault fresco.
        write_flag(proj)
        touch(project_md, mtime=time.time() + 5)
        rc, err = run_hook(proj, vault)
        check("6. _PROJECT.md fresco -> exit 0", rc == 0 and err.strip() == "")

        # 7. Vía multi-agente: basta una nota de sessions/ fresca.
        write_flag(proj)
        touch(project_md, mtime=time.time() - 3600)
        touch(os.path.join(pdir, "sessions", "20260801-tarea.md"), mtime=time.time() + 5)
        rc, err = run_hook(proj, vault)
        check("7. nota de sessions/ fresca -> exit 0", rc == 0 and err.strip() == "")

        # 8. Proyecto sin carpeta en el vault -> nada que exigir.
        with tempfile.TemporaryDirectory(prefix="mf-vacio-") as vault_vacio:
            write_flag(proj)
            rc, err = run_hook(proj, os.path.realpath(vault_vacio))
            check("8. proyecto no enganchado -> exit 0", rc == 0 and err.strip() == "")

        # 9. stdin ilegible -> fail-open (un bug del hook no impide compactar).
        write_flag(proj)
        rc, err = run_hook(proj, vault, stdin=b"no es json")
        check("9. stdin ilegible -> exit 0 (fail-open)", rc == 0)

        # 10. Flag corrupto -> fail-open.
        with open(os.path.join(proj, ".claude", "vault-dirty.json"), "w",
                  encoding="utf-8") as f:
            f.write("{roto")
        rc, err = run_hook(proj, vault)
        check("10. flag corrupto -> exit 0 (fail-open)", rc == 0)

        # Extra: acentos correctos en stderr (el mojibake de cp1252 ya mordió antes).
        # Ojo: hay que envejecer TAMBIÉN la nota de sessions/ del caso 7, o el
        # hook la seguiría viendo fresca y callaría (con razón).
        touch(project_md, mtime=time.time() - 3600)
        touch(os.path.join(pdir, "sessions", "20260801-tarea.md"),
              mtime=time.time() - 3600)
        write_flag(proj)
        rc, err = run_hook(proj, vault)
        check("11. stderr en UTF-8 sin mojibake",
              "pausada" in err and "Ã" not in err, err[:80])

    fallos = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
