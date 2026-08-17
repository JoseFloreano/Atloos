#!/usr/bin/env python3
"""
test-mark-code-dirty.py — Arnés de contrato de setup/hooks/mark-code-dirty.py.

Lanza el hook como subproceso real (igual que Claude Code: payload PostToolUse
por stdin) sobre un proyecto temporal, y comprueba QUÉ ediciones sellan el flag
`.claude/vault-dirty.json` y cuáles no.

Regla que verifica: solo cuenta como "editó código de ESTE proyecto" un archivo
no-.md que esté DENTRO de CLAUDE_PROJECT_DIR. Lo de fuera (scratchpad, otro
repo, otra unidad) no debe sellar nada — ese era el falso positivo que hacía
saltar el hook Stop con el vault ya al día.

Uso:  setup/scripts/py setup/hooks/tests/test-mark-code-dirty.py
Salida: una línea por caso + resumen; exit 1 si algo falla.

Sin dependencias externas: solo stdlib. No toca el vault ni el repo real.
"""
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    os.pardir, "mark-code-dirty.py")
HOOK = os.path.normpath(HOOK)

SESSION = "sess-test-0001"
results = []


def run_hook(project_dir, file_path, session=SESSION, tool="Edit"):
    """Ejecuta el hook con el payload de PostToolUse. Devuelve (rc, stderr)."""
    payload = {
        "session_id": session,
        "hook_event_name": "PostToolUse",
        "tool_name": tool,
        "tool_input": {"file_path": file_path},
    }
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = project_dir
    p = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload).encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=project_dir, env=env,
    )
    return p.returncode, p.stderr.decode("utf-8", "replace")


def flag_state(project_dir):
    """Contenido del flag, o None si no existe."""
    fp = os.path.join(project_dir, ".claude", "vault-dirty.json")
    if not os.path.exists(fp):
        return None
    with open(fp, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_flag(project_dir):
    fp = os.path.join(project_dir, ".claude", "vault-dirty.json")
    if os.path.exists(fp):
        os.remove(fp)


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))
    mark = "OK  " if condition else "FALLA"
    print(f"[{mark}] {name}" + (f" -- {detail}" if detail and not condition else ""))


def touch(path, content="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def main():
    with tempfile.TemporaryDirectory(prefix="mcd-proj-") as proj, \
            tempfile.TemporaryDirectory(prefix="mcd-out-") as outside:
        proj = os.path.realpath(proj)
        outside = os.path.realpath(outside)

        # --- Casos que SÍ deben sellar el flag (el anti-drift sigue vivo) ---
        clear_flag(proj)
        rc, _ = run_hook(proj, touch(os.path.join(proj, "app.py")))
        check("1. codigo en la raiz del proyecto -> sella flag",
              rc == 0 and flag_state(proj) is not None)

        clear_flag(proj)
        rc, _ = run_hook(proj, touch(os.path.join(proj, "setup", "hooks", "x.ps1")))
        check("2. codigo en subdirectorio del proyecto -> sella flag",
              rc == 0 and flag_state(proj) is not None)

        clear_flag(proj)
        rc, _ = run_hook(proj, os.path.join(proj, "setup", "hooks", "x.ps1").replace("\\", "/"))
        check("3. misma ruta con separadores '/' -> sella flag",
              flag_state(proj) is not None)

        clear_flag(proj)
        rc, _ = run_hook(proj, "app.py")  # cwd = proyecto
        check("4. ruta relativa dentro del proyecto -> sella flag",
              flag_state(proj) is not None)

        # Windows entrega a veces la unidad en minuscula ('c:\\') y otras en
        # mayuscula; si el fix comparase texto crudo, esto desactivaria el
        # anti-drift en silencio -- el modo de fallo peligroso.
        if os.name == "nt" and len(proj) > 1 and proj[1] == ":":
            clear_flag(proj)
            swapped = (proj[0].lower() if proj[0].isupper() else proj[0].upper()) + proj[1:]
            rc, _ = run_hook(proj, os.path.join(swapped, "app.py"))
            check("5. unidad con distinta capitalizacion -> sella flag",
                  flag_state(proj) is not None,
                  "comparar rutas sin normcase rompe el anti-drift")
        else:
            check("5. unidad con distinta capitalizacion (solo Windows)", True)

        # --- Casos que NO deben sellar (el bug) ---
        clear_flag(proj)
        rc, _ = run_hook(proj, touch(os.path.join(proj, "notas.md")))
        check("6. archivo .md del proyecto -> NO sella",
              flag_state(proj) is None)

        clear_flag(proj)
        tmpfile = touch(os.path.join(outside, "commit-msg.txt"))
        rc, _ = run_hook(proj, tmpfile)
        check("7. .txt temporal FUERA del proyecto (scratchpad) -> NO sella",
              flag_state(proj) is None,
              "este es el falso positivo del bug")

        clear_flag(proj)
        rc, _ = run_hook(proj, touch(os.path.join(outside, "otro_repo", "main.py")))
        check("8. codigo de OTRO repo -> NO sella",
              flag_state(proj) is None)

        clear_flag(proj)
        other_drive = "Z:\\tmp\\x.py" if os.name == "nt" else "/mnt/otro/x.py"
        rc, _ = run_hook(proj, other_drive)
        check("9. ruta en otra unidad/raiz -> NO sella (sin excepcion)",
              rc == 0 and flag_state(proj) is None)

        # --- El escenario exacto del bug reportado ---
        # 1) se edita codigo de verdad, 2) se actualiza el vault, 3) un archivo
        # temporal fuera del proyecto NO debe adelantar `last_code_edit` (si lo
        # hace, el hook Stop concluye drift con el vault ya al dia).
        clear_flag(proj)
        run_hook(proj, os.path.join(proj, "app.py"))
        antes = flag_state(proj)["last_code_edit"]
        run_hook(proj, os.path.join(outside, "commit-msg.txt"))
        despues = flag_state(proj)["last_code_edit"]
        check("10. temporal externo no adelanta last_code_edit",
              antes == despues,
              f"antes={antes} despues={despues}")

        # --- Fail-open: un hook roto no puede romper la sesion ---
        p = subprocess.run([sys.executable, HOOK], input=b"esto no es json",
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        check("11. stdin ilegible -> exit 0 (fail-open)", p.returncode == 0)

        p = subprocess.run([sys.executable, HOOK], input=json.dumps(
            {"session_id": SESSION, "tool_input": {}}).encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        check("12. payload sin file_path -> exit 0", p.returncode == 0)

        # --- Contador de ediciones sin registrar (D2 del RFD 18, opcion b) ---
        # El hook Stop dejo de exigir "una vez por sesion" y pasa a re-armarse
        # cada N ediciones sin registrar. Ese N se cuenta AQUI: sin contador, el
        # anti-drift no tiene con que medir la sesion larga.
        clear_flag(proj)
        run_hook(proj, os.path.join(proj, "app.py"))
        run_hook(proj, os.path.join(proj, "otro.py"))
        st = flag_state(proj)
        check("13. dos ediciones de codigo -> edits == 2",
              st is not None and st.get("edits") == 2,
              f"edits={None if st is None else st.get('edits')}")

        clear_flag(proj)
        run_hook(proj, os.path.join(proj, "app.py"))
        run_hook(proj, os.path.join(outside, "commit-msg.txt"))
        st = flag_state(proj)
        check("14. edicion fuera del proyecto NO incrementa edits",
              st is not None and st.get("edits") == 1,
              f"edits={None if st is None else st.get('edits')}")

        clear_flag(proj)
        run_hook(proj, os.path.join(proj, "app.py"))
        run_hook(proj, os.path.join(proj, "app.py"), session="sess-test-0002")
        st = flag_state(proj)
        check("15. sesion nueva resetea el contador a 1",
              st is not None and st.get("edits") == 1,
              f"edits={None if st is None else st.get('edits')}")

    fallos = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
