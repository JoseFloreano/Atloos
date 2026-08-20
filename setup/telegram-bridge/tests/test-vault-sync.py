#!/usr/bin/env python3
"""
test-vault-sync.py — Arnés de la sincronía del vault (C5 de vaultio.py).

POR QUÉ EXISTE. El vault es un repo git que en las laptops mueve el plugin Git
de Obsidian. **La SER8 no tiene Obsidian**, así que en la única máquina que corre
el daemon 24/7 nadie hacía `pull` ni `push`: el briefing servía lo que hubiera en
disco (sin decir su edad) y la nota de `/done` se quedaba SOLO en ese disco —
que no es "desincronizado", es pérdida de datos.

Los casos que mandan:
  · 4 y 5 — la nota de `/done` LLEGA al remoto, y cuando no llega **se dice**.
    Un `commit_push` que devolviera True sin publicar reproduciría el fallo
    original con una capa de pintura encima.
  · 2 — un `pull` que no puede avanzar NO deja el vault a medias.
  · 7 y 8 — la EDAD viaja en el briefing. Sin eso, un vault de hace una semana
    y uno de hoy se leen igual desde el móvil, que es justo lo que pasó.

Estos casos tocan git de verdad (repos de laboratorio en un temporal), no un
doble: el fallo que se persigue vive en el comportamiento de `git pull`, y un
doble que lo imite es una suposición mía sobre git, no una medida.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-vault-sync.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir)))
import vaultio  # noqa: E402

results = []

# Identidad y config mínimas por ENTORNO: una caja headless puede no tener
# `user.email` global, y entonces fallaría el commit del arnés y no lo que el
# arnés mide. `vaultio._git` copia os.environ, así que esto le llega.
os.environ.update({
    "GIT_AUTHOR_NAME": "arnes", "GIT_AUTHOR_EMAIL": "arnes@local",
    "GIT_COMMITTER_NAME": "arnes", "GIT_COMMITTER_EMAIL": "arnes@local",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
})


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'OK  ' if ok else 'FALLA'}] {name}" + (f" -- {detail}" if detail and not ok else ""))


def git(args, cwd):
    p = subprocess.run(["git", *args], cwd=str(cwd), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=30)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def escribe(ruta, texto):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    Path(ruta).write_text(texto, encoding="utf-8", newline="\n")


def laboratorio(tmp):
    """(origen_bare, clon_a, clon_b). Dos clones del mismo remoto, como en campo."""
    origen = Path(tmp) / "origen.git"
    git(["init", "--bare", "-b", "main", str(origen)], tmp)
    siembra = Path(tmp) / "siembra"
    git(["clone", str(origen), str(siembra)], tmp)
    escribe(siembra / "10-Projects" / "demo" / "_PROJECT.md",
            f"---\nupdated: {date.today():%Y-%m-%d}\n---\n\n## Estado actual\nx\n")
    git(["add", "-A"], siembra)
    git(["commit", "-m", "siembra"], siembra)
    git(["push", "-u", "origin", "main"], siembra)
    a, b = Path(tmp) / "a", Path(tmp) / "b"
    git(["clone", str(origen), str(a)], tmp)
    git(["clone", str(origen), str(b)], tmp)
    return origen, a, b


def banco(tmp, vault):
    """Un `bridge/` de mentira para EJECUTAR vault-sync.sh de verdad.

    El script resuelve la raíz del vault preguntándole a `vaultio`, y avisa
    llamando a `notify_telegram.py`, los dos por su propio `dirname`. Copiándolo
    a un directorio con esos dos vecinos falsos se ejerce el TEXTO REAL del
    script sin remoto de verdad, sin bot y sin tocar el vault de esta máquina.

    Devuelve (script, buzon): el buzón es el fichero donde aterriza cada aviso.
    """
    bridge = Path(tmp) / "bridge"
    bridge.mkdir(parents=True, exist_ok=True)
    real = Path(__file__).resolve().parent.parent / "vault-sync.sh"
    destino = bridge / "vault-sync.sh"
    shutil.copy2(real, destino)
    destino.chmod(0o755)
    buzon = Path(tmp) / "avisos.txt"
    escribe(bridge / "vaultio.py",
            "from pathlib import Path\n"
            f"def vault_root():\n    return Path(r'{vault}')\n")
    escribe(bridge / "notify_telegram.py",
            "import sys\n"
            f"open(r'{buzon}', 'a', encoding='utf-8').write(' '.join(sys.argv[1:]) + chr(10))\n")
    return destino, buzon


def corre(script, tmp):
    """(exit, salida). El script, tal cual lo lanzaría el timer."""
    p = subprocess.run(["bash", str(script)], cwd=str(tmp), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=120, env=dict(os.environ))
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()


def avisos(buzon):
    return Path(buzon).read_text(encoding="utf-8") if Path(buzon).is_file() else ""


def main():
    if not shutil.which("git"):
        print("[SKIP] no hay git en esta máquina: la sincronía del vault no se mide")
        return 0

    # --- Caso 1: el pull trae lo que puso la otra máquina ---
    with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
        _, a, b = laboratorio(tmp)
        escribe(b / "nota.md", "de la laptop\n")
        git(["add", "-A"], b); git(["commit", "-m", "desde la laptop"], b); git(["push"], b)
        ok, motivo = vaultio.sync_pull(a)
        check("1. sync_pull trae lo que publicó la otra máquina",
              ok and (a / "nota.md").is_file(), f"({ok}, {motivo!r})")

    # --- Caso 2: divergencia -> falla Y NO deja el vault a medias ---
    with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
        _, a, b = laboratorio(tmp)
        escribe(b / "choque.md", "de la laptop\n")
        git(["add", "-A"], b); git(["commit", "-m", "laptop"], b); git(["push"], b)
        escribe(a / "choque.md", "de la SER8\n")
        git(["add", "-A"], a); git(["commit", "-m", "ser8"], a)
        ok, motivo = vaultio.sync_pull(a)
        _, estado = git(["status", "--porcelain=v1", "--branch"], a)
        check("2. divergencia: sync_pull dice que no, y el vault queda limpio",
              (not ok) and bool(motivo) and not (a / ".git" / "rebase-merge").exists()
              and not (a / ".git" / "MERGE_HEAD").exists(),
              f"({ok}, {motivo!r}) estado={estado!r}")

    # --- Caso 3: sin remoto / sin repo -> se dice, no se revienta ---
    with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
        suelto = Path(tmp) / "no-es-repo"
        suelto.mkdir()
        ok, motivo = vaultio.sync_pull(suelto)
        check("3. carpeta que no es repo: (False, motivo legible)",
              (not ok) and "git" in motivo.lower(), f"({ok}, {motivo!r})")

    # --- Caso 4: la nota de /done LLEGA al remoto (el fallo original) ---
    with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
        origen, a, b = laboratorio(tmp)
        nota = a / "10-Projects" / "demo" / "sessions" / "2026-08-19-tg-x.md"
        escribe(nota, "# nota\n")
        ok, motivo = vaultio.commit_push([str(nota)], "tg: nota", root=a)
        _, en_remoto = git(["ls-tree", "-r", "--name-only", "main"], origen)
        check("4. commit_push publica la nota: existe en el REMOTO, no solo aquí",
              ok and "sessions/2026-08-19-tg-x.md" in en_remoto,
              f"({ok}, {motivo!r}) remoto={en_remoto!r}")

    # --- Caso 5: si el push no puede salir, se DICE (no se devuelve un OK falso) ---
    with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
        origen, a, b = laboratorio(tmp)
        # El remoto avanza por otro camino y `a` no lo tiene: su push rebota.
        escribe(b / "otro.md", "x\n")
        git(["add", "-A"], b); git(["commit", "-m", "otro"], b); git(["push"], b)
        escribe(a / "10-Projects" / "demo" / "sessions" / "n.md", "# n\n")
        # Un commit local previo hace que el pull --ff-only interno tampoco salve
        escribe(a / "local.md", "y\n")
        git(["add", "local.md"], a); git(["commit", "-m", "local"], a)
        ok, motivo = vaultio.commit_push(
            [str(a / "10-Projects" / "demo" / "sessions" / "n.md")], "tg: nota", root=a)
        check("5. push rebotado: (False, 'commiteada pero SIN PUBLICAR')",
              (not ok) and "SIN PUBLICAR" in motivo, f"({ok}, {motivo!r})")

    # --- Caso 6: una ruta fuera del vault no se commitea ---
    with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
        _, a, _b = laboratorio(tmp)
        fuera = Path(tmp) / "fuera.md"
        escribe(fuera, "x\n")
        ok, motivo = vaultio.commit_push([str(fuera)], "tg: nota", root=a)
        check("6. ruta fuera del vault -> se rechaza",
              (not ok) and "fuera del vault" in motivo, f"({ok}, {motivo!r})")

    # --- Caso 7: la EDAD viaja, y a los 2 días avisa ---
    with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
        d = Path(tmp) / "10-Projects" / "demo"
        viejo = date.today() - timedelta(days=3)
        escribe(d / "_PROJECT.md", f"---\nupdated: {viejo:%Y-%m-%d}\n---\n\n## Estado actual\nx\n")
        original = vaultio.project_dir
        vaultio.project_dir = lambda p: d
        try:
            linea = vaultio.linea_frescura("demo", (True, "al día"))
        finally:
            vaultio.project_dir = original
        check("7. la edad del vault viaja en la línea de frescura, con aviso",
              "hace 3 días" in linea and "viejo" in linea and "sincronizado" in linea,
              f"linea={linea!r}")

    # --- Caso 8: un pull fallido se DICE en el briefing, no se esconde ---
    with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
        d = Path(tmp) / "10-Projects" / "demo"
        escribe(d / "_PROJECT.md",
                f"---\nupdated: {date.today():%Y-%m-%d}\n---\n\n## Estado actual\nx\n")
        original = vaultio.project_dir
        vaultio.project_dir = lambda p: d
        try:
            brief = vaultio.project_briefing("demo", (False, "sin red"))
            hoy = vaultio.linea_frescura("demo", (True, "al día"))
        finally:
            vaultio.project_dir = original
        check("8. briefing con pull fallido: lo lleva escrito",
              "SIN SINCRONIZAR" in brief and "sin red" in brief, f"brief={brief[:160]!r}")
        check("8b. y con el vault de hoy NO mete el aviso de viejo",
              "hoy" in hoy and "viejo" not in hoy, f"linea={hoy!r}")

    # --- Caso 9: sin vault no hay excepción, hay motivo ---
    ok, motivo = vaultio.sync_pull(Path(tempfile.gettempdir()) / "no-existe-jamas-vault")
    check("9. vault ausente: (False, motivo) y ni una excepción",
          (not ok) and bool(motivo), f"({ok}, {motivo!r})")

    # --- Caso 10: el script del timer, al menos, PARSEA ---
    # Un `.sh` que corre desde una unit de systemd no tiene a nadie delante
    # cuando falla, y un error de sintaxis se ve por primera vez en el journal a
    # las 3 de la mañana. `bash -n` no prueba que haga lo correcto (eso se
    # ejerce en campo, y el .timer.example dice cómo), pero sí que no está roto.
    script = Path(__file__).resolve().parent.parent / "vault-sync.sh"
    if not shutil.which("bash"):
        print("[SKIP] 10. la sintaxis de vault-sync.sh: no hay bash en esta máquina")
    else:
        p = subprocess.run(["bash", "-n", str(script)], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=20)
        check("10. vault-sync.sh parsea (bash -n)", p.returncode == 0,
              p.stdout.decode("utf-8", "replace")[:300])

    # --- Caso 11: y NO resuelve conflictos por su cuenta ---
    # La regla no es un detalle de implementación: con dos escritores (Obsidian
    # en la laptop, daemon aquí) una resolución automática a ciegas es como se
    # pierde la nota que importaba. Se fija en el texto porque es lo que impide
    # que alguien "arregle" el script metiendo un -X ours dentro de un año.
    fuente = script.read_text(encoding="utf-8", errors="replace")
    check("11. vault-sync.sh aborta el rebase ante conflicto y no fuerza nada",
          "rebase --abort" in fuente and "-X ours" not in fuente
          and "--strategy-option" not in fuente and "push --force" not in fuente,
          "el script resuelve conflictos solo: eso es exactamente lo que no debe hacer")

    # ══ Los casos que EJECUTAN el script ══════════════════════════════════
    # Hasta 2026-08-19 el script solo tenía `bash -n` y un grep de su fuente:
    # 116 líneas que estrenaban sin cobertura en la máquina que corre sola. Lo
    # que sigue lo ejerce contra un remoto de mentira.
    if not shutil.which("bash"):
        print("[SKIP] 12-16. el script no se puede ejercer: no hay bash")
    else:
        # --- Caso 12: todo al día -> calla y sale 0 ---
        with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
            _, a, _b = laboratorio(tmp)
            script, buzon = banco(tmp, a)
            rc, out = corre(script, tmp)
            check("12. al día: sale 0 y no dice nada", rc == 0 and not avisos(buzon),
                  f"rc={rc} avisos={avisos(buzon)!r} out={out[:200]!r}")

        # --- Caso 13: la nota local acaba EN EL REMOTO ---
        # Es la pérdida de datos que motivó el script: la nota de `/done` se
        # quedaba en el disco de la SER8. Se comprueba en el remoto, no aquí.
        with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
            origen, a, _b = laboratorio(tmp)
            escribe(a / "10-Projects" / "demo" / "sessions" / "hoy.md", "la nota\n")
            script, buzon = banco(tmp, a)
            rc, out = corre(script, tmp)
            _, listado = git(["ls-tree", "-r", "--name-only", "main"], origen)
            check("13. la nota sin commitear acaba publicada en el remoto",
                  rc == 0 and "sessions/hoy.md" in listado and not avisos(buzon),
                  f"rc={rc} listado={listado!r} avisos={avisos(buzon)!r}")

        # --- Caso 14: conflicto -> avisa, aborta y NO deja el vault a medias ---
        with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
            _, a, b = laboratorio(tmp)
            escribe(b / "choca.md", "lo de la laptop\n")
            git(["add", "-A"], b); git(["commit", "-m", "laptop"], b); git(["push"], b)
            escribe(a / "choca.md", "lo del servidor\n")     # misma línea, otro texto
            script, buzon = banco(tmp, a)
            rc, out = corre(script, tmp)
            _, gitdir = git(["rev-parse", "--absolute-git-dir"], a)
            a_medias = Path(gitdir, "rebase-merge").is_dir() or Path(gitdir, "rebase-apply").is_dir()
            check("14. conflicto: avisa, aborta el rebase y conserva lo local",
                  rc == 1 and "CONFLICTO" in avisos(buzon) and not a_medias
                  and (a / "choca.md").read_text(encoding="utf-8") == "lo del servidor\n",
                  f"rc={rc} a_medias={a_medias} avisos={avisos(buzon)!r}")

        # --- Caso 15: remoto caído CON trabajo en juego -> avisa, y NO de conflicto ---
        # La regresión que cerró este caso: el script hacía `rebase --abort`
        # (no-op) y mandaba "🔴 CONFLICTO" ante un fallo de RED. Con el timer a
        # 20 min eso son tres falsas alarmas por hora.
        with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
            _, a, _b = laboratorio(tmp)
            escribe(a / "pendiente.md", "sin publicar\n")
            git(["remote", "set-url", "origin", str(Path(tmp) / "no-existe.git")], a)
            script, buzon = banco(tmp, a)
            rc, out = corre(script, tmp)
            # Se comprueba que NO saltó la alarma roja (su frase exacta), no que
            # la palabra "conflicto" no aparezca: el mensaje correcto dice "no es
            # un conflicto", y una aserción sobre la subcadena lo daría por malo.
            check("15. remoto caído con nota sin publicar: avisa SIN dar la alarma de conflicto",
                  rc == 1 and "SIN PUBLICAR" in avisos(buzon)
                  and "CONFLICTO al sincronizar" not in avisos(buzon),
                  f"rc={rc} avisos={avisos(buzon)!r}")

        # --- Caso 16: remoto caído SIN nada en juego -> se calla ---
        # La otra mitad del 15: si avisara igual, el fix habría cambiado una
        # falsa alarma por otra, y la regla de la casa es callar cuando no hay
        # nada que decidir.
        with tempfile.TemporaryDirectory(prefix="vaultsync-") as tmp:
            _, a, _b = laboratorio(tmp)
            git(["remote", "set-url", "origin", str(Path(tmp) / "no-existe.git")], a)
            script, buzon = banco(tmp, a)
            rc, out = corre(script, tmp)
            check("16. remoto caído sin nada sin publicar: sale != 0 y CALLA",
                  rc != 0 and not avisos(buzon),
                  f"rc={rc} avisos={avisos(buzon)!r}")

    print()
    fallos = [n for n, ok, _ in results if not ok]
    print(f"[test-vault-sync] {len(results) - len(fallos)}/{len(results)} en verde.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
