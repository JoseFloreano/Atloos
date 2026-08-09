#!/usr/bin/env python3
"""
test-merge-gate-guard.py — Arnés de contrato de setup/hooks/merge-gate-guard.py.

Monta repos git de verdad en temporal (nada de mocks: el hook consulta `git`) y
lanza el hook como subproceso con el payload PreToolUse real, comprobando el
contrato del W3:

  · merge a `main` sin evidencia            → BLOQUEA (exit 2)
  · evidencia con sha viejo (llegó un commit) → BLOQUEA
  · evidencia válida                        → PASA (exit 0)
  · merge a rama NO protegida               → no interviene

Y los dos casos que la prueba deliberada del 2026-08-07 hizo obligatorios:

  · `git checkout main && git merge x` estando en otra rama → BLOQUEA
    (mirar solo el HEAD del momento dejaría pasar justo los 2 merges que se
    colaron; el destino es EFECTIVO, no el actual)
  · evidencia de OTRA rama                  → BLOQUEA

Uso:  py setup/hooks/tests/test-merge-gate-guard.py
Salida: una línea por caso + resumen; exit 1 si algo falla.
Solo stdlib. No toca el vault, el repo real ni ninguna rama de verdad.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HOOK = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "merge-gate-guard.py"))

results = []


def sh(args, cwd):
    subprocess.run(args, cwd=cwd, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, check=True)


def repo_lab():
    """Repo con `main` y una rama `feat/x` con un commit propio."""
    d = tempfile.mkdtemp(prefix="gate-guard-")
    sh(["git", "init", "-q", "-b", "main"], d)
    sh(["git", "config", "user.email", "t@t"], d)
    sh(["git", "config", "user.name", "t"], d)
    with open(os.path.join(d, "a.py"), "w") as f:
        f.write("x = 1\n")
    sh(["git", "add", "-A"], d)
    sh(["git", "commit", "-q", "-m", "base"], d)
    sh(["git", "checkout", "-q", "-b", "feat/x"], d)
    with open(os.path.join(d, "b.py"), "w") as f:
        f.write("y = 2\n")
    sh(["git", "add", "-A"], d)
    sh(["git", "commit", "-q", "-m", "feature"], d)
    return d


def head(d, ref):
    p = subprocess.run(["git", "rev-parse", ref], cwd=d,
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return p.stdout.decode().strip()


def escribe_evidencia(d, branch, sha, cmd="py -m pytest -q"):
    os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
    with open(os.path.join(d, ".claude", "gate-verde.json"), "w") as f:
        json.dump({"branch": branch, "sha": sha,
                   "ts": "2026-08-08T10:00:00", "cmd": cmd}, f)


def corre(d, comando):
    """Lanza el hook con el payload PreToolUse. Devuelve (rc, stderr)."""
    payload = {"session_id": "s1", "hook_event_name": "PreToolUse",
               "tool_name": "Bash", "tool_input": {"command": comando}}
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = d
    p = subprocess.run([sys.executable, HOOK],
                       input=json.dumps(payload).encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       cwd=d, env=env)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def caso(nombre, rc, esperado, err=""):
    ok = rc == esperado
    results.append(ok)
    estado = "OK  " if ok else "FALLA"
    print(f"  [{estado}] {nombre}  (exit {rc}, esperado {esperado})")
    if not ok and err:
        print("          stderr: " + err.strip().splitlines()[0][:100])


def main():
    print("Arnés de merge-gate-guard.py\n")

    # 1 · merge a main sin evidencia → bloquea
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git merge feat/x")
    caso("merge a main SIN evidencia bloquea", rc, 2, err)
    enseña = "gate-test.py" in err and "feat/x" in err
    results.append(enseña)
    print(f"  [{'OK  ' if enseña else 'FALLA'}] el mensaje ENSEÑA "
          f"(nombra el helper y la rama)")
    shutil.rmtree(d, ignore_errors=True)

    # 2 · evidencia con sha viejo → bloquea
    d = repo_lab()
    viejo = head(d, "feat/x")
    with open(os.path.join(d, "c.py"), "w") as f:
        f.write("z = 3\n")
    sh(["git", "add", "-A"], d)
    sh(["git", "commit", "-q", "-m", "un commit mas"], d)
    escribe_evidencia(d, "feat/x", viejo)
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git merge feat/x")
    caso("evidencia con sha VIEJO bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # 3 · evidencia válida → pasa
    d = repo_lab()
    escribe_evidencia(d, "feat/x", head(d, "feat/x"))
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git merge --squash feat/x")
    caso("evidencia VÁLIDA pasa (y con --squash)", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # 4 · rama no protegida → no interviene
    d = repo_lab()
    sh(["git", "checkout", "-q", "-b", "integracion"], d)
    rc, err = corre(d, "git merge feat/x")
    caso("merge a rama NO protegida no interviene", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # 5 · destino EFECTIVO: checkout main && merge, estando en otra rama
    d = repo_lab()          # HEAD queda en feat/x
    rc, err = corre(d, "git checkout main && git merge feat/x")
    caso("`checkout main && merge` bloquea (destino efectivo)", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # 6 · evidencia de OTRA rama → bloquea
    d = repo_lab()
    escribe_evidencia(d, "otra/rama", head(d, "feat/x"))
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git merge feat/x")
    caso("evidencia de OTRA rama bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # 7 · git merge --abort no es una integración
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git merge --abort")
    caso("`merge --abort` no se bloquea", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # 8 · PROSA dentro de un heredoc, no un merge.
    #     Regresión real: este hook bloqueó el commit que lo introducía, porque
    #     el mensaje explicaba el caso `git checkout main && git merge x`.
    #     El cuerpo de un heredoc nunca se ejecuta.
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    mensaje = ("git commit -q -F - <<'EOF'\n"
               "feat: algo\n\n"
               "Los merges venian como `git checkout main && git merge x`.\n"
               "EOF")
    rc, err = corre(d, mensaje)
    caso("prosa en heredoc no se confunde con un merge", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # 9 · prosa entrecomillada en la misma línea (mismo fallo, sin heredoc)
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, 'git commit -m "explica git merge `feat/x`, nada mas"')
    caso("prosa entrecomillada no se confunde con un merge", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # 10 · y el merge de verdad SIGUE bloqueándose (que el fix no abra un boquete)
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git merge feat/x   # despues del fix de la prosa")
    caso("tras el fix, el merge real sigue bloqueado", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # ── Los 9 de la auditoría externa del 2026-08-09 ─────────────────────
    # H1: el parser dejaba pasar 5 merges reales y bloqueaba 3 comandos
    # legítimos. El 9.º es el boquete que el arreglo NO debe abrir.

    # 11-12 · opciones globales de git rompían el ancla `^git\s+merge`
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git -C . merge feat/x")
    caso("opción global `-C` no esquiva el gate", rc, 2, err)
    rc, err = corre(d, "git -c core.editor=true merge feat/x")
    caso("opción global `-c` no esquiva el gate", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # 12b · la otra mitad: las opciones globales también rompían el ancla del
    #       CHECKOUT, así que el destino efectivo se perdía. Lo destapó un
    #       mutante: sin este caso, revertir esa normalización pasaba inadvertido.
    d = repo_lab()          # HEAD en feat/x
    rc, err = corre(d, "git -C . checkout main && git merge feat/x")
    caso("opción global en el `checkout` no pierde el destino efectivo", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # 13 · `<<IDENT` DENTRO de comillas no abre un heredoc: el fix del falso
    #      positivo se comía el resto del comando. Y este repo escribe sobre
    #      heredocs en sus mensajes de commit, así que el caso es real.
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, 'git commit -m "docs: explica el uso de <<EOF en los tests"\n'
                       "git merge feat/x")
    caso("`<<EOF` entrecomillado no se traga el merge que sigue", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # 14 · lo mismo con un `<<` suelto en un echo
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, 'echo "x << n"\ngit merge feat/x')
    caso("`<<` suelto en un echo no se traga el merge", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # 15 · `git pull` ES un merge (fetch + merge) y ni siquiera contenía la
    #      palabra: se caía por el atajo barato antes de llegar al parser.
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git pull origin feat/x")
    caso("`git pull <remoto> <rama>` a main sin evidencia bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # 16-17 · `git checkout <rama> -- <ruta>` NO cambia de rama: restaura
    #         ficheros. Bloquear aquí es un falso positivo sobre trabajo legítimo.
    d = repo_lab()          # HEAD en feat/x, rama no protegida
    rc, err = corre(d, "git checkout main -- a.py && git merge feat/x")
    caso("`checkout main -- <ruta>` no cambia de rama (no bloquea)", rc, 0, err)
    rc, err = corre(d, "git checkout main -- . && git merge feat/x")
    caso("`checkout main -- .` no cambia de rama (no bloquea)", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # 18 · `git switch -` vuelve a la rama anterior: el destino efectivo
    #      deja de ser main.
    d = repo_lab()          # HEAD en feat/x
    rc, err = corre(d, "git switch main && git switch - && git merge feat/x")
    caso("`switch -` deshace el salto a main (no bloquea)", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # 19 · el boquete que el arreglo no debe abrir: enseñarle `git pull` no
    #      puede convertir cada pull cotidiano en un bloqueo.
    d = repo_lab()          # HEAD en feat/x, rama no protegida
    rc, err = corre(d, "git pull origin feat/x")
    caso("`git pull` en rama NO protegida sigue sin intervenir", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # 20 · el otro boquete simétrico: `git pull` que SINCRONIZA main con su
    #      remoto no integra ningún frente. Bloquearlo sería un falso positivo
    #      diario, peor que el escape que arregla el caso 15.
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git pull origin main")
    caso("`git pull origin main` estando en main no bloquea (sincroniza)", rc, 0, err)
    rc, err = corre(d, "git pull")
    caso("`git pull` a secas no bloquea (sincroniza)", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    print(f"\n{sum(results)}/{len(results)} casos OK")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
