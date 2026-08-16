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

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOOK = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "merge-gate-guard.py"))

# El hook, importado como módulo, para preguntarle DÓNDE busca la evidencia en
# vez de suponerlo. Lo sigue ejerciendo como subproceso —que es como corre de
# verdad—; esto es solo para el fixture.
import importlib.util as _il
_spec = _il.spec_from_file_location("merge_gate_guard", HOOK)
GUARD_MOD = _il.module_from_spec(_spec)
_spec.loader.exec_module(GUARD_MOD)

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
    """Deja el verde DONDE EL GUARD LO BUSCA, preguntándoselo al propio guard.

    La ruta se resuelve importando `ruta_evidencia` del hook real en vez de
    escribirla aquí a mano. Escribirla a mano es lo que había, y por eso este
    arnés se puso rojo al mover la evidencia al directorio git común (H2 del
    08-14): el fixture afirmaba una ruta por su cuenta, así que medía su propia
    copia de la regla y no la regla.

    ⚠ Y fíjate en la DIRECCIÓN del fallo: los casos que se rompieron fueron los
    que esperaban PASAR; los que esperaban bloquear siguieron bloqueando. Un
    desajuste de rutas en esta compuerta falla cerrado, que es lo que tiene que
    hacer — pero no por eso deja de ser un desajuste.
    """
    destino = GUARD_MOD.ruta_evidencia(d)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w") as f:
        json.dump({"branch": branch, "sha": sha,
                   "ts": "2026-08-08T10:00:00", "cmd": cmd}, f)


def repo_lab_remoto():
    """Repo lab + un `origin` de verdad (bare) con `main` ya publicada.

    Hace falta un remoto porque el guard del push consulta `origin/<rama>` para
    no bloquear un push que no adelanta nada.
    """
    d = repo_lab()
    bare = tempfile.mkdtemp(prefix="gate-guard-origin-")
    sh(["git", "init", "-q", "--bare", "-b", "main"], bare)
    sh(["git", "remote", "add", "origin", bare], d)
    sh(["git", "push", "-q", "origin", "main"], d)
    sh(["git", "fetch", "-q", "origin"], d)
    return d, bare


def commit_en(d, fichero, texto, msg):
    with open(os.path.join(d, fichero), "w") as f:
        f.write(texto)
    sh(["git", "add", "-A"], d)
    sh(["git", "commit", "-q", "-m", msg], d)


def corre(d, comando, extra_env=None, tool="Bash"):
    """Lanza el hook con el payload PreToolUse. Devuelve (rc, stderr).

    `tool` es parámetro desde el sprint 7 y no es cosmética: mientras estuvo
    fijo en "Bash", este arnés **no podía ni expresar** el caso de la
    herramienta PowerShell. La tercera puerta de un agujero de tres es la que
    deja escribir la prueba; sin ella el fix se afirma, no se demuestra.
    """
    payload = {"session_id": "s1", "hook_event_name": "PreToolUse",
               "tool_name": tool, "tool_input": {"command": comando}}
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = d
    env.update(extra_env or {})
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

    # ══ `git push` a protegida (sprint 2) ══════════════════════════════════
    # El agujero lo encontró el campo, no una auditoría: el gate corría sobre un
    # SHA, entró un commit más en la misma rama y el `--ff-only` se llevó los
    # dos. El hook miraba `merge` y el verbo era `push`.
    print("\nF · el verbo `push` (el agujero del 2026-08-11)")

    # 21 · el incidente exacto: main avanzó y el verde es de antes → bloquea
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    gateado = head(d, "main")
    escribe_evidencia(d, "main", gateado)
    commit_en(d, "doc.md", "el commit que se coló\n", "doc mientras corria el gate")
    rc, err = corre(d, "git push")
    caso("push a main con un commit POSTERIOR al verde bloquea", rc, 2, err)
    enseña = "gate-test.py" in err and "árbol" in err
    results.append(enseña)
    print(f"  [{'OK  ' if enseña else 'FALLA'}] el mensaje ENSEÑA "
          f"(nombra el helper y habla del árbol)")
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 22 · push a main SIN ninguna evidencia → bloquea
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "algo\n", "un commit en main")
    rc, err = corre(d, "git push")
    caso("push a main SIN evidencia bloquea", rc, 2, err)
    rc, err = corre(d, "git push origin main")
    caso("  ídem con refspec explícito `git push origin main`", rc, 2, err)
    rc, err = corre(d, "git push --force-with-lease origin +main")
    caso("  ídem con push forzado `+main`", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 23 · evidencia sobre el tip exacto → pasa
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "algo\n", "un commit en main")
    escribe_evidencia(d, "main", head(d, "main"))
    rc, err = corre(d, "git push")
    caso("push a main con el verde sobre ESE commit pasa", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 24 · el commit es nuevo pero el ÁRBOL es el gateado: es lo que produce el
    #      `merge --squash` que el propio gate manda usar. Tiene que pasar.
    d, bare = repo_lab_remoto()
    escribe_evidencia(d, "feat/x", head(d, "feat/x"))
    sh(["git", "checkout", "-q", "main"], d)
    sh(["git", "merge", "-q", "--squash", "feat/x"], d)
    sh(["git", "commit", "-q", "-m", "integra feat/x (squash)"], d)
    rc, err = corre(d, "git push")
    caso("tras `--squash`, commit nuevo pero MISMO árbol: pasa", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 25 · y el reverso: squash + un commit extra encima → el árbol ya no es el
    #      gateado → bloquea. Si esto pasara, el caso 24 sería un agujero.
    d, bare = repo_lab_remoto()
    escribe_evidencia(d, "feat/x", head(d, "feat/x"))
    sh(["git", "checkout", "-q", "main"], d)
    sh(["git", "merge", "-q", "--squash", "feat/x"], d)
    sh(["git", "commit", "-q", "-m", "integra feat/x (squash)"], d)
    commit_en(d, "extra.md", "colado\n", "y un extra encima")
    rc, err = corre(d, "git push")
    caso("squash + commit extra: el árbol cambió → bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 26 · PreToolUse corre ANTES del comando: en `merge && push` el árbol que
    #      viajaría aún no existe, así que no es verificable → bloquea el push.
    d, bare = repo_lab_remoto()
    escribe_evidencia(d, "feat/x", head(d, "feat/x"))
    rc, err = corre(d, "git checkout main && git merge feat/x && git push")
    caso("`merge && push` en la misma línea: push no verificable → bloquea",
         rc, 2, err)
    rc, err = corre(d, "git checkout main && git commit -am x && git push")
    caso("`commit && push` sobre main: ídem", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    print("\nG · los cuatro falsos positivos del push, que aquí son caros")

    # 27 · FP 1 · push a una rama de trabajo
    d, bare = repo_lab_remoto()
    commit_en(d, "b.py", "y = 3\n", "mas trabajo")
    rc, err = corre(d, "git push -u origin feat/x")
    caso("FP1 · push a rama de trabajo NO interviene", rc, 0, err)
    rc, err = corre(d, "git push")
    caso("  ídem sin refspec, estando en feat/x", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 28 · FP 2 · `--dry-run` no ejecuta nada
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "algo\n", "un commit en main")
    rc, err = corre(d, "git push --dry-run origin main")
    caso("FP2 · `--dry-run` a main NO interviene", rc, 0, err)
    rc, err = corre(d, "git push -n origin main")
    caso("  ídem con `-n`", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 29 · FP 3 · tags. `git push --tags` estando EN main no empuja main.
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "algo\n", "un commit en main")
    sh(["git", "tag", "v1.0"], d)
    rc, err = corre(d, "git push --tags")
    caso("FP3 · `git push --tags` estando en main NO interviene", rc, 0, err)
    rc, err = corre(d, "git push origin v1.0")
    caso("  ídem empujando un tag por nombre", rc, 0, err)
    rc, err = corre(d, "git push origin refs/tags/v1.0")
    caso("  ídem con `refs/tags/`", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 30 · FP 4 · el bot de Telegram. Empuja a SUS ramas y no puede quedarse
    #      bloqueado (además va por subprocess del daemon, no por Bash).
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "-b", "tg/20260811-una-tarea"], d)
    commit_en(d, "c.py", "z = 1\n", "trabajo del bot")
    rc, err = corre(d, "git push -u origin tg/20260811-una-tarea",
                    {"CLAUDE_TG_BOT": "1"})
    caso("FP4 · push del bot a su rama NO interviene", rc, 0, err)
    rc, err = corre(d, "git push --force-with-lease -u origin tg/20260811-una-tarea",
                    {"CLAUDE_TG_BOT": "1"})
    caso("  ídem con el push forzado que usa gitops.push_branch", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 31 · y el quinto que no estaba en el encargo pero se paga a diario: un
    #      push que no adelanta nada. No viaja ningún árbol, no hay qué gatear.
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git push origin main")
    caso("push que no adelanta nada (local == origin/main) NO interviene",
         rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 32 · refspec `HEAD:main` desde otra rama: el destino es main igual.
    d, bare = repo_lab_remoto()
    rc, err = corre(d, "git push origin HEAD:main")
    caso("`push origin HEAD:main` desde otra rama bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 33 · `HEAD` A SECAS, que es como se teclea. La auditoría 22 (B2) lo empujó
    #      DE VERDAD a `origin/main`: el destino se resolvía como el literal
    #      "HEAD", que no está en PROTEGIDAS, y el hook no intervenía. El caso 32
    #      probaba `HEAD:main` —con dos puntos— y por eso no lo cazó.
    print("\nH · `HEAD` a secas: el escape que el arnés no probaba (auditoría 22)")
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "sin gatear\n", "NUEVO SIN GATEAR")
    for forma in ("git push origin HEAD", "git push origin @",
                  "git push origin head", "git push origin +HEAD",
                  "git push -u origin HEAD"):
        rc, err = corre(d, forma)
        caso(f"`{forma}` estando en main bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 34 · y su reverso: `HEAD` desde una rama de trabajo NO puede bloquear.
    #      Resolver el alias no debe convertirse en un falso positivo diario.
    d, bare = repo_lab_remoto()
    commit_en(d, "b.py", "y = 9\n", "trabajo")        # HEAD queda en feat/x
    rc, err = corre(d, "git push origin HEAD")
    caso("`push origin HEAD` desde una rama de trabajo NO interviene", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 35 · envoltorios de un carácter. Afectaba también a `git merge`, así que
    #      venía del W3 y no del sprint 2 (auditoría 22, H6).
    print("\nI · subshell y grupo: un carácter de envoltorio no es una excusa")
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "sin gatear\n", "sin gatear")
    for forma in ("(git push origin main)", "{ git push origin main; }",
                  "(git push origin HEAD)"):
        rc, err = corre(d, forma)
        caso(f"`{forma}` bloquea", rc, 2, err)
    rc, err = corre(d, "(git merge feat/x)")
    caso("`(git merge feat/x)` a main bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 36 · el límite declarado sigue siéndolo, y el arnés lo FIJA para que nadie
    #      lea la cobertura más ancha de lo que es. `bash -c` no se caza.
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "sin gatear\n", "sin gatear")
    rc, err = corre(d, "bash -c 'git push origin main'")
    caso("LÍMITE: `bash -c` se escapa, y está declarado en el docstring",
         rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # ══ La herramienta PowerShell (sprint 7) ═══════════════════════════════
    # El pendiente decía "el matcher es Bash". Eran TRES puertas: el matcher de
    # `sync-hooks.ps1`, el filtro `tool_name != "Bash"` del propio hook —que
    # rechazaba el payload aunque el matcher lo dejara entrar— y este arnés, que
    # con el `tool_name` fijo no podía ni escribir el caso.
    print("\nJ · la herramienta PowerShell: mismo contrato, otra puerta")

    # 37 · el caso del encargo: merge a protegida sin evidencia, por PowerShell
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git merge feat/x", tool="PowerShell")
    caso("merge a main SIN evidencia por PowerShell BLOQUEA", rc, 2, err)
    enseña = "gate-test.py" in err and "feat/x" in err
    results.append(enseña)
    print(f"  [{'OK  ' if enseña else 'FALLA'}] el mensaje ENSEÑA igual que por Bash")
    # 38 · y la evidencia válida pasa igual: el fix no es "bloquear más"
    escribe_evidencia(d, "feat/x", head(d, "feat/x"))
    rc, err = corre(d, "git merge --squash feat/x", tool="PowerShell")
    caso("evidencia VÁLIDA por PowerShell pasa", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    # 39 · el push, que es el otro verbo del mismo contrato
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "sin gatear\n", "sin gatear")
    rc, err = corre(d, "git push origin main", tool="PowerShell")
    caso("push a main sin evidencia por PowerShell BLOQUEA", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 40 · una herramienta que NO es de shell sigue sin tocarse. El filtro se
    #      ensancha a dos, no se quita: un payload de `Read` no trae comandos.
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git merge feat/x", tool="Read")
    caso("herramienta que no es de shell (`Read`) no se mira", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True)

    print("\nK · sintaxis propia de PowerShell (el matcher es la mitad fácil)")

    # 41 · el operador de llamada `&`, suelto y pegado
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    for forma in ("& git merge feat/x", "&git merge feat/x",
                  "$(git merge feat/x)", "(& git merge feat/x)"):
        rc, err = corre(d, forma, tool="PowerShell")
        caso(f"`{forma}` a main bloquea", rc, 2, err)
    # 42 · `;` como separador, con el destino efectivo cruzando el separador
    rc, err = corre(d, "git status; git merge feat/x", tool="PowerShell")
    caso("`;` separa comandos (destino efectivo intacto)", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    d = repo_lab()          # HEAD en feat/x
    rc, err = corre(d, "git checkout main; git merge feat/x", tool="PowerShell")
    caso("`git checkout main; git merge feat/x` bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # 43 · el push por `$( … )` y por `&`
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "sin gatear\n", "sin gatear")
    for forma in ("$(git push origin main)", "& git push origin main"):
        rc, err = corre(d, forma, tool="PowerShell")
        caso(f"`{forma}` bloquea", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 44 · continuación por tilde invertida. NO se unen las líneas (límite
    #      declarado), pero el marcador se retira para que el fallo caiga del
    #      lado seguro: sin rama que comprobar, en protegida se bloquea. Antes
    #      del sprint 7 el segmento `git merge ´` se leía como PROSA y el merge
    #      se escapaba entero — fail-OPEN dentro de la protegida.
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, "git merge `\n  feat/x", tool="PowerShell")
    caso("merge partido por la tilde de continuación NO se escapa", rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    # 44b · el `&` corta FUERA de comillas y no dentro. El corte a ciegas del
    #       primer intento metió un falso positivo NUEVO —y por la vía Bash, que
    #       no había que tocar—: lo destapó la auditoría del sprint 7 midiendo el
    #       antes y el después, no leyendo el diff. Los dos bordes, fijados.
    d = repo_lab()
    sh(["git", "checkout", "-q", "main"], d)
    rc, err = corre(d, 'git commit -m "arregla el & git merge feat/x que quedo roto"')
    caso("prosa con `&` entrecomillado NO se lee como comando", rc, 0, err)
    rc, err = corre(d, 'git commit -m "arregla el & git merge feat/x"',
                    tool="PowerShell")
    caso("  ídem por la vía PowerShell", rc, 0, err)
    rc, err = corre(d, "git status & git merge feat/x")
    caso("y el `&` FUERA de comillas sigue cortando (bloquea)", rc, 2, err)
    # El reverso declarado: `;` y `&&` sí cortan dentro de comillas, y eso es
    # PREEXISTENTE. Se fija para que nadie lo lea como cobertura.
    rc, err = corre(d, 'git commit -m "arregla el ; git merge feat/x"')
    caso("LÍMITE: `;` entrecomillado sí corta (preexistente, declarado)",
         rc, 2, err)
    shutil.rmtree(d, ignore_errors=True)

    print("\nL · y por la vía PowerShell los mismos falsos positivos siguen pasando")

    # 45 · FP 1 · rama de trabajo. Fuera de las protegidas NO se cierra: el bot
    #      de Telegram empuja a las suyas y no puede quedarse bloqueado.
    d, bare = repo_lab_remoto()
    commit_en(d, "b.py", "y = 3\n", "mas trabajo")
    rc, err = corre(d, "git push -u origin feat/x", tool="PowerShell")
    caso("FP1 · push a rama de trabajo NO interviene (PowerShell)", rc, 0, err)
    rc, err = corre(d, "& git merge feat/x", tool="PowerShell")
    caso("  ídem un `& git merge` fuera de protegida", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 46 · FP 2 · `--dry-run`
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "algo\n", "un commit en main")
    rc, err = corre(d, "git push --dry-run origin main", tool="PowerShell")
    caso("FP2 · `--dry-run` a main NO interviene (PowerShell)", rc, 0, err)
    rc, err = corre(d, "git push -n origin main", tool="PowerShell")
    caso("  ídem con `-n`", rc, 0, err)
    # 47 · FP 3 · tags
    sh(["git", "tag", "v1.0"], d)
    rc, err = corre(d, "git push --tags", tool="PowerShell")
    caso("FP3 · `git push --tags` estando en main NO interviene (PowerShell)",
         rc, 0, err)
    rc, err = corre(d, "git push origin v1.0", tool="PowerShell")
    caso("  ídem empujando un tag por nombre", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 48 · FP 4 · el push del bot a su rama
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "-b", "tg/20260811-una-tarea"], d)
    commit_en(d, "c.py", "z = 1\n", "trabajo del bot")
    rc, err = corre(d, "git push -u origin tg/20260811-una-tarea",
                    {"CLAUDE_TG_BOT": "1"}, tool="PowerShell")
    caso("FP4 · push del bot a su rama NO interviene (PowerShell)", rc, 0, err)
    rc, err = corre(d, "git push --force-with-lease -u origin tg/20260811-una-tarea",
                    {"CLAUDE_TG_BOT": "1"}, tool="PowerShell")
    caso("  ídem con el push forzado de `gitops.push_branch`", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    # 49 · el límite declarado de PowerShell, FIJADO igual que el de `bash -c`:
    #      lo que el parser no entiende se declara, no se finge.
    d, bare = repo_lab_remoto()
    sh(["git", "checkout", "-q", "main"], d)
    commit_en(d, "doc.md", "sin gatear\n", "sin gatear")
    rc, err = corre(d, "Invoke-Expression 'git push origin main'",
                    tool="PowerShell")
    caso("LÍMITE: `Invoke-Expression` se escapa, y está declarado", rc, 0, err)
    rc, err = corre(d, "& \"C:\\Program Files\\Git\\cmd\\git.exe\" push origin main",
                    tool="PowerShell")
    caso("LÍMITE: `& <ruta a git.exe>` se escapa, y está declarado", rc, 0, err)
    shutil.rmtree(d, ignore_errors=True); shutil.rmtree(bare, ignore_errors=True)

    print(f"\n{sum(results)}/{len(results)} casos OK")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
