#!/usr/bin/env python3
"""
test-goal-evidence-guard.py — Arnés de contrato de setup/hooks/goal-evidence-guard.py.

Monta repos git de verdad en temporal (el hook consulta `git rev-parse`) y lanza
el hook como subproceso con el payload `Stop` real.

EL CASO QUE MANDA ES EL CANARIO (§C). Una meta con condición deliberadamente
falsa —"los tests pasan", con la suite en rojo y sin evidencia en disco— que el
evaluador de `/goal` cerraría, porque solo lee la conversación. El guard debe
rechazarla. Sin ese caso, el resto del arnés no prueba lo que importa: cualquier
hook que salga 0 siempre pasaría los demás.

Y §E mide la CONVIVENCIA con `check-vault-updated.py`, que ya vive en `Stop`.
No es cortesía: dos hooks en el mismo evento pueden enmascararse, y aquí uno lo
hacía — el vecino enmudecía cuando este guard bloqueaba primero. Se arbitró como
D2·b y E.3 pasó de medir la avería a fijar su ausencia.

Uso:  py setup/hooks/tests/test-goal-evidence-guard.py                [repo]
Salida: una línea por caso + resumen; exit 1 si algo falla.
Solo stdlib. No toca el vault, el repo real ni ninguna rama de verdad.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")     # la consola de Windows es cp1252
    except Exception:
        pass

AQUI = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.normpath(os.path.join(AQUI, os.pardir, "goal-evidence-guard.py"))
VAULT_HOOK = os.path.normpath(os.path.join(AQUI, os.pardir, "check-vault-updated.py"))

results = []


def sh(args, cwd):
    subprocess.run(args, cwd=cwd, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=True)


def repo_lab():
    """Repo con un commit. El HEAD importa: la frescura se mide contra él."""
    d = tempfile.mkdtemp(prefix="goal-guard-")
    sh(["git", "init", "-q", "-b", "main"], d)
    sh(["git", "config", "user.email", "t@t"], d)
    sh(["git", "config", "user.name", "t"], d)
    with open(os.path.join(d, "a.py"), "w") as f:
        f.write("x = 1\n")
    sh(["git", "add", "-A"], d)
    sh(["git", "commit", "-q", "-m", "base"], d)
    os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
    return d


def head(d):
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=d,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return p.stdout.decode().strip()


def forja(d, condicion, artefacto, cmd="py -m pytest -q", bloqueos=0, ts=None):
    """Escribe .claude/goal.json — lo que produce la skill `goal-forge`."""
    meta = {"condicion": condicion, "artefacto": artefacto, "cmd": cmd,
            "turnos": 20, "bloqueos": bloqueos,
            "forjada_ts": ts if ts is not None else time.time()}
    with open(os.path.join(d, ".claude", "goal.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)
    return meta


def evidencia(d, ruta, sha=None):
    p = os.path.join(d, ruta)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        if sha is None:
            f.write("suite verde\n")
        else:
            json.dump({"branch": "main", "sha": sha, "ts": "2026-08-09T10:00:00",
                       "cmd": "py -m pytest -q"}, f)


def vault_falso(d, nombre="proyecto-lab"):
    """Vault mínimo que `check-vault-updated.py` sí reconoce, y el CLAUDE.md
    que le da el nombre del proyecto.

    Sin esto el hook del vault sale 0 SIEMPRE («proyecto no enganchado») y el
    caso de convivencia mediría dos silencios en vez de dos decisiones. Lo
    descubrí porque la aserción falló: el arnés midió su propio vacío.
    """
    raiz = os.path.join(d, "_fake_onedrive")
    proj = os.path.join(raiz, "DevSetup", "ObsidianVault", "10-Projects", nombre)
    os.makedirs(proj, exist_ok=True)
    with open(os.path.join(proj, "_PROJECT.md"), "w", encoding="utf-8") as f:
        f.write("# lab\n\n## Pendientes\n")
    with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write(f"# lab\n\n## Active Project: `{nombre}`\n")
    return raiz


def sucia(d, cuando=None):
    """Flag de mark-code-dirty.py: esta sesión editó código y no registró nada."""
    with open(os.path.join(d, ".claude", "vault-dirty.json"), "w") as f:
        json.dump({"session_id": "s1",
                   "last_code_edit": cuando or (time.time() + 3600)}, f)


def corre(d, hook=HOOK, stop_hook_active=False, env_extra=None):
    payload = {"session_id": "s1", "hook_event_name": "Stop",
               "stop_hook_active": stop_hook_active, "cwd": d}
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = d
    env.pop("CLAUDE_TG_BOT", None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, hook],
                       input=json.dumps(payload).encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       cwd=d, env=env)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def caso(nombre, rc, esperado, err=""):
    ok = rc == esperado
    results.append(ok)
    print(f"  [{'OK  ' if ok else 'FALLA'}] {nombre}  (exit {rc}, esperado {esperado})")
    if not ok and err:
        print("          stderr: " + err.strip().splitlines()[0][:100])
    return ok


def afirma(nombre, condicion):
    results.append(bool(condicion))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")


def main():
    print("Arnés de goal-evidence-guard.py\n")

    # ── A · Fail-open: el guard no estorba donde no prometió nada ─────────
    print("A · fail-open (un guard que molesta se desactiva en dos semanas)")

    d = repo_lab()
    rc, err = corre(d)
    caso("sin .claude/goal.json no interviene", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    d = repo_lab()
    forja(d, "el diseño queda revisado", artefacto=None)
    rc, err = corre(d)
    caso("meta que NO nombra artefacto: fail-open", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    d = repo_lab()
    with open(os.path.join(d, ".claude", "goal.json"), "w") as f:
        f.write("{esto no es json")
    rc, err = corre(d)
    caso("goal.json ilegible: fail-open (un bug del hook no tumba la sesión)", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    d = repo_lab()
    forja(d, "los tests pasan", ".claude/verde.json")
    rc, err = corre(d, env_extra={"CLAUDE_TG_BOT": "1"})
    caso("sesión del daemon de Telegram: no bloquea (no hay humano)", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # ── B · Muerde donde la meta prometió algo comprobable ────────────────
    print("\nB · el contrato sha↔HEAD, heredado del merge-gate")

    d = repo_lab()
    forja(d, "`py -m pytest -q` deja `.claude/verde.json` con el sha del HEAD",
          ".claude/verde.json")
    rc, err = corre(d)
    caso("artefacto nombrado que NO existe: bloquea", rc, 2, err)
    enseña = "verde.json" in err and "pytest" in err
    afirma("el mensaje ENSEÑA (nombra el artefacto y el comando que lo produce)", enseña)
    shutil.rmtree(d, ignore_errors=True)

    d = repo_lab()
    forja(d, "verde con sha del HEAD", ".claude/verde.json")
    evidencia(d, ".claude/verde.json", sha=head(d))
    rc, err = corre(d)
    caso("artefacto con sha == HEAD: pasa", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    d = repo_lab()
    viejo = head(d)
    forja(d, "verde con sha del HEAD", ".claude/verde.json")
    evidencia(d, ".claude/verde.json", sha=viejo)
    with open(os.path.join(d, "b.py"), "w") as f:
        f.write("y = 2\n")
    sh(["git", "add", "-A"], d)
    sh(["git", "commit", "-q", "-m", "un commit mas"], d)
    rc, err = corre(d)
    caso("artefacto con sha VIEJO (el repo avanzó): bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # Frescura débil, declarada como tal: sin sha solo se puede exigir que el
    # artefacto sea POSTERIOR a la meta.
    d = repo_lab()
    evidencia(d, "salida.txt")                      # ya estaba ahí de antes
    time.sleep(0.05)
    forja(d, "`ruff check .` deja salida.txt", "salida.txt")
    rc, err = corre(d)
    caso("artefacto sin sha ANTERIOR a la meta: bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    d = repo_lab()
    forja(d, "`ruff check .` deja salida.txt", "salida.txt")
    time.sleep(0.05)
    evidencia(d, "salida.txt")                      # producido durante la meta
    rc, err = corre(d)
    caso("artefacto sin sha POSTERIOR a la meta: pasa", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # ── C · EL CANARIO ───────────────────────────────────────────────────
    # La condición que el evaluador de `/goal` cerraría leyendo el transcript.
    print("\nC · EL CANARIO — la meta falsa que `/goal` desnudo cerraría")

    d = repo_lab()
    # Suite en ROJO: existe y falla. Ningún artefacto de verde en disco.
    with open(os.path.join(d, "test_falla.py"), "w") as f:
        f.write("def test_x():\n    assert False, 'la suite esta en rojo a proposito'\n")
    forja(d,
          condicion="los tests pasan",
          artefacto=".claude/verde.json",
          cmd="py \"$HOME/.claude/scripts/gate-test.py\" main")
    rc, err = corre(d)
    ok = caso("meta FALSA ('los tests pasan', suite roja) → RECHAZADA", rc, 2, err)
    if ok:
        print("\n" + "\n".join("        │ " + l for l in err.strip().splitlines()) + "\n")
    afirma("el guard no se deja cerrar por una afirmación del turno",
           rc == 2 and "no existe" in err.lower())
    shutil.rmtree(d, ignore_errors=True)

    # Y la vuelta: el canario no puede convertir en imposible una meta legítima.
    d = repo_lab()
    forja(d, "los tests pasan", ".claude/verde.json")
    evidencia(d, ".claude/verde.json", sha=head(d))
    rc, err = corre(d)
    caso("la MISMA meta, con la evidencia ya en disco: cierra", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # ── D · Cláusula de corte del propio guard ───────────────────────────
    print("\nD · el guard tiene fondo (un bloqueo infinito es otro fallo)")

    d = repo_lab()
    forja(d, "los tests pasan", ".claude/verde.json", bloqueos=3)
    rc, err = corre(d)
    caso("tras 3 bloqueos sale ABIERTO (la condición está mal forjada)", rc, 0, err)
    afirma("y lo dice en vez de callarse", "mal forjada" in err)
    shutil.rmtree(d, ignore_errors=True)

    d = repo_lab()
    forja(d, "los tests pasan", ".claude/verde.json")
    corre(d)
    corre(d)
    with open(os.path.join(d, ".claude", "goal.json"), encoding="utf-8") as f:
        n = json.load(f).get("bloqueos")
    afirma(f"el contador de bloqueos persiste entre turnos (va por {n})", n == 2)
    shutil.rmtree(d, ignore_errors=True)

    # ── E · CONVIVENCIA con check-vault-updated.py ───────────────────────
    print("\nE · convivencia con check-vault-updated.py (el otro hook de Stop)")

    # E.1 · Sin flag de código sucio, el hook del vault calla y el guard manda.
    d = repo_lab()
    raiz = vault_falso(d)
    forja(d, "los tests pasan", ".claude/verde.json")
    rc_g, _ = corre(d, env_extra={"OneDrive": raiz})
    rc_v, _ = corre(d, hook=VAULT_HOOK, env_extra={"OneDrive": raiz})
    afirma("guard bloquea (2) y el del vault, sin código sucio, no interviene (0)",
           rc_g == 2 and rc_v == 0)
    shutil.rmtree(d, ignore_errors=True)

    # E.2 · Cada uno decide por su cuenta: el guard no lee el flag del vault,
    #       ni el vault lee la meta. Ninguno se traga la señal del otro.
    d = repo_lab()
    raiz = vault_falso(d)
    forja(d, "los tests pasan", ".claude/verde.json")
    evidencia(d, ".claude/verde.json", sha=head(d))
    sucia(d)
    rc_g, _ = corre(d, env_extra={"OneDrive": raiz})
    rc_v, _ = corre(d, hook=VAULT_HOOK, env_extra={"OneDrive": raiz})
    afirma("meta satisfecha + vault sucio: el guard pasa (0) y el del vault "
           f"exige ({rc_v}) — cada uno mide lo suyo", rc_g == 0 and rc_v == 2)
    shutil.rmtree(d, ignore_errors=True)

    # E.3 · LA DEUDA, YA PAGADA. Este caso medía una avería: el guard bloqueaba
    #       primero, el turno siguiente llegaba con `stop_hook_active` puesto y
    #       check-vault-updated —que entonces sí lo respetaba— se callaba el
    #       resto del bucle. Se arbitró como D2·b y el hook dejó de amordazarse:
    #       ahora decide igual con el flag y sin él, acotado por su propia
    #       cláusula de corte. El contrato completo del vecino vive en
    #       `tests/test-check-vault-updated.py` §B y §C; aquí solo se comprueba
    #       que la convivencia ya no lo enmudece.
    d = repo_lab()
    raiz = vault_falso(d)
    sucia(d)
    rc_sin, _ = corre(d, hook=VAULT_HOOK, stop_hook_active=False,
                      env_extra={"OneDrive": raiz})
    sucia(d)
    rc_con, _ = corre(d, hook=VAULT_HOOK, stop_hook_active=True,
                      env_extra={"OneDrive": raiz})
    afirma(f"check-vault-updated ya NO enmudece con stop_hook_active: exige sin "
           f"él ({rc_sin}) y con él ({rc_con})", rc_sin == 2 and rc_con == 2)
    shutil.rmtree(d, ignore_errors=True)

    # E.4 · Y el guard NO hereda ese fallo: sigue evaluando con el flag puesto.
    d = repo_lab()
    forja(d, "los tests pasan", ".claude/verde.json")
    rc, err = corre(d, stop_hook_active=True)
    caso("el guard SÍ evalúa con stop_hook_active (no se auto-enmascara)", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    print(f"\n{sum(results)}/{len(results)} casos OK")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
