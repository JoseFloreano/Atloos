#!/usr/bin/env python3
"""
test-altas.py — Arnés de contrato de setup/telegram-bridge/altas.py.

Qué se comprueba al dar de alta un proyecto, y sobre todo QUÉ SE DICE cuando
falla. El alta estaba repartida en cinco sitios y los cinco fallos eran mudos:
la ruta de la otra máquina se descartaba con un `log.warning` al journal, y la
carpeta ausente en el vault se traducía en un briefing vacío sin una sola línea.

Los casos que mandan son el 1 y el 5, que son las dos incompatibilidades
Windows↔Ubuntu que quedaban vivas:
  · 1 — una ruta de la otra laptop (`projects.json` es por-máquina)
  · 5 — un ejecutable que en ESTA máquina no existe (systemd --user no lee tu
        .bashrc, así que "en mi laptop corre" no dice nada del daemon)

Y el 9, que es la regla de no duplicar: el comando que declara el REPO
(`GATE_TEST_CMD`) no se copia a `projects.json`, porque una copia por-máquina se
queda atrás en cuanto el repo cambie — que es exactamente de dónde salió el
`compileall` que dejaba pasar merges sin correr un arnés.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-altas.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir)))
import altas  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'OK  ' if ok else 'FALLA'}] {name}" + (f" -- {detail}" if detail and not ok else ""))


def repo(tmp, nombre="mi-app", git=True, settings=None, claude_md=False):
    """Repo de laboratorio."""
    d = os.path.join(tmp, nombre)
    os.makedirs(d, exist_ok=True)
    if git:
        os.makedirs(os.path.join(d, ".git"), exist_ok=True)
    if settings is not None:
        os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
        with open(os.path.join(d, ".claude", "settings.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            json.dump({"env": {"GATE_TEST_CMD": settings}}, f)
    if claude_md:
        with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("# proyecto\n")
    return d


def registro(tmp, datos):
    ruta = os.path.join(tmp, "projects.json")
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        json.dump(datos, f)
    return ruta


def de(v, clave):
    """El Check con esa clave, o None."""
    return next((c for c in v["checks"] if c.clave == clave), None)


def sin_vault(_nombre=None):
    return ""          # ninguna máquina de laboratorio tiene vault


def main():
    # --- Caso 1: una ruta de Windows en Linux se dice, no se descarta callando ---
    if os.name == "nt":
        print("[SKIP] 1. ruta de Windows en Linux — esta máquina ES Windows")
    else:
        v = altas.revisar(r"C:\Users\jose\proyectos\app", which=lambda x: None,
                          vault_project_dir="")
        c = de(v, "ruta")
        det = (c.detalle if c else "").lower().replace("á", "a")
        check("1. ruta de Windows en Linux: bloquea Y explica por qué",
              (not v["ok"]) and c and not c.ok and c.bloqueante
              and "windows" in det and "por maquina" in det,
              f"detalle={c.detalle if c else None!r}")

    # --- Caso 2: ruta inexistente, bloqueante ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        v = altas.revisar(os.path.join(tmp, "no-existe"), which=lambda x: None,
                          vault_project_dir="")
        check("2. ruta inexistente -> bloqueante", not v["ok"])

    # --- Caso 3: carpeta sin .git, bloqueante (sin git no hay puente) ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp, git=False)
        v = altas.revisar(d, which=lambda x: None, vault_project_dir="")
        c = de(v, "git")
        check("3. carpeta sin git -> bloqueante", (not v["ok"]) and c and not c.ok and c.bloqueante)

    # --- Caso 4: sin carpeta en el vault AVISA pero deja pasar ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp)
        v = altas.revisar(d, test="pytest -q", which=lambda x: "/usr/bin/pytest",
                          vault_project_dir=os.path.join(tmp, "vault-que-no-existe"))
        c = de(v, "vault")
        check("4. vault ausente: avisa, NO bloquea",
              v["ok"] and c and not c.ok and not c.bloqueante
              and "VACIO" in c.detalle.upper().replace("Í", "I"),
              f"ok={v['ok']} detalle={c.detalle if c else None!r}")

    # --- Caso 5: el ejecutable que aquí no existe (la incompatibilidad viva) ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp)
        v = altas.revisar(d, test="npm test", which=lambda x: None, vault_project_dir="")
        c = de(v, "test")
        check("5. ejecutable ausente del PATH del daemon: lo dice, con PATH y /merge",
              c and not c.ok and not c.bloqueante and "PATH" in c.detalle
              and "merge" in c.detalle.lower(),
              f"detalle={c.detalle if c else None!r}")

    # --- Caso 6: `py` NO se juzga por el PATH: lo resuelve el daemon ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp)
        v = altas.revisar(d, test="py -m pytest -q", which=lambda x: None,
                          vault_project_dir="")
        c = de(v, "test")
        check("6. lanzador `py` pasa aunque no esté en el PATH", c and c.ok,
              f"detalle={c.detalle if c else None!r}")

    # --- Caso 7: sin comando declarado, avisa con la consecuencia y sugiere ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp)
        with open(os.path.join(d, "package.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        v = altas.revisar(d, which=lambda x: None, vault_project_dir="")
        c = de(v, "test")
        check("7. sin test declarado: /merge bloqueado + sugerencia del repo",
              v["ok"] and c and not c.ok and "npm test" in c.detalle
              and "merge" in c.detalle.lower(),
              f"detalle={c.detalle if c else None!r}")

    # --- Caso 8: operadores de shell -> se dice, no se acepta en silencio ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp)
        v = altas.revisar(d, test="npm ci && npm test", which=lambda x: "/usr/bin/npm",
                          vault_project_dir="")
        c = de(v, "test")
        check("8. comando con '&&' -> avisado (aquí se corre argv, sin shell)",
              c and not c.ok and "&&" in c.detalle, f"detalle={c.detalle if c else None!r}")

    # --- Caso 9: el comando del REPO no se copia a projects.json ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp, settings="py setup/scripts/run-tests.py")
        pj = registro(tmp, {"_comentario": "no me borres"})
        v = altas.revisar(d, projects_file=pj, which=lambda x: None, vault_project_dir="")
        ok, _ = altas.registrar(v, projects_file=pj)
        with open(pj, encoding="utf-8") as f:
            datos = json.load(f)
        entrada = datos.get("mi-app", {})
        check("9. el GATE_TEST_CMD del repo NO se duplica en projects.json",
              ok and "test" not in entrada, f"entrada={entrada!r}")
        check("9b. registrar conserva las claves de comentario `_`",
              datos.get("_comentario") == "no me borres", f"datos={list(datos)!r}")
        check("9c. registrar deja la ruta absoluta resuelta",
              os.path.realpath(entrada.get("path", "")) == os.path.realpath(d),
              f"path={entrada.get('path')!r}")

    # --- Caso 10: el comando declarado AQUÍ sí se persiste ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp)
        pj = registro(tmp, {})
        v = altas.revisar(d, test="npm test", projects_file=pj,
                          which=lambda x: "/usr/bin/npm", vault_project_dir="")
        altas.registrar(v, projects_file=pj)
        with open(pj, encoding="utf-8") as f:
            datos = json.load(f)
        check("10. el test declarado en el alta sí se persiste",
              datos.get("mi-app", {}).get("test") == "npm test", f"datos={datos!r}")

    # --- Caso 11: un alta bloqueada NO escribe nada ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        pj = registro(tmp, {"otro": "/ruta/vieja"})
        v = altas.revisar(os.path.join(tmp, "no-existe"), projects_file=pj,
                          which=lambda x: None, vault_project_dir="")
        ok, _ = altas.registrar(v, projects_file=pj)
        with open(pj, encoding="utf-8") as f:
            datos = json.load(f)
        check("11. alta bloqueada -> no se escribe nada",
              (not ok) and datos == {"otro": "/ruta/vieja"}, f"datos={datos!r}")

    # --- Caso 12: el nombre choca con otro proyecto ya registrado ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp)
        pj = registro(tmp, {"mi-app": {"path": os.path.join(tmp, "otra-copia")}})
        v = altas.revisar(d, projects_file=pj, which=lambda x: None, vault_project_dir="")
        c = de(v, "nombre")
        check("12. nombre ya usado por OTRA ruta -> bloquea",
              (not v["ok"]) and c and c.bloqueante and not c.ok,
              f"detalle={c.detalle if c else None!r}")

    # --- Caso 13: re-alta del MISMO proyecto (misma ruta) no bloquea ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp)
        pj = registro(tmp, {"mi-app": {"path": d, "test": "npm test"}})
        v = altas.revisar(d, projects_file=pj, which=lambda x: "/usr/bin/npm",
                          vault_project_dir="")
        altas.registrar(v, projects_file=pj)
        with open(pj, encoding="utf-8") as f:
            datos = json.load(f)
        check("13. re-alta de la misma ruta: pasa y CONSERVA su test",
              v["ok"] and datos["mi-app"].get("test") == "npm test", f"datos={datos!r}")

    # --- Caso 14: el nombre se deriva en kebab, que es la clave de las tres puntas ---
    casos = [("Mi App_v2", "mi-app-v2"), ("Atloos", "atloos"),
             ("proyecto-ñu", "proyecto-nu"), ("/home/x/Mi Repo/", "mi-repo")]
    malos = [(e, altas.derivar_nombre(e)) for e, s in casos
             if altas.derivar_nombre(e) != s]
    check("14. derivar_nombre -> kebab sin acentos", not malos, f"malos={malos!r}")

    # --- Caso 15: el veredicto se puede leer desde el móvil ---
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp, claude_md=True)
        v = altas.revisar(d, test="pytest -q", which=lambda x: "/usr/bin/pytest",
                          vault_project_dir="")
        txt = altas.texto_veredicto(v)
        check("15. texto_veredicto: una línea por casilla y un cierre",
              txt.count("\n") >= len(v["checks"]) and ("⚠️" in txt or "✅" in txt),
              f"txt={txt!r}")

    # --- Caso 16: el registro ilegible NO se reescribe ---
    # El fallo que cerró este caso (2026-08-19): `leer_registro` devolvía `{}`
    # tanto para "no hay fichero" como para "no lo pude parsear", y `registrar`
    # reescribe el fichero ENTERO. Un `projects.json` con una coma de más se
    # traducía en un alta que borraba los otros proyectos y las claves `_`, y
    # contestaba `[OK]` al móvil. Se ejerce el borrado, no la cadena del motivo.
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp)
        pj = registro(tmp, {"_comentario": "no me borres",
                            "ya-estaba": {"path": tmp, "test": "npm test"}})
        crudo = open(pj, encoding="utf-8").read()
        with open(pj, "w", encoding="utf-8") as fh:
            fh.write(crudo.replace('"ya-estaba"', ',,"ya-estaba"'))   # JSON roto
        antes = open(pj, encoding="utf-8").read()
        v = altas.revisar(d, projects_file=pj, which=lambda x: None, vault_project_dir="")
        ok, motivo = altas.registrar(v, projects_file=pj)
        despues = open(pj, encoding="utf-8").read()
        check("16. projects.json ilegible: NO se escribe y se dice por qué",
              (not ok) and antes == despues and "JSON" in motivo.upper(),
              f"ok={ok} motivo={motivo!r} cambio={antes != despues}")

    # --- Caso 17: y el fichero AUSENTE sí se crea (vacío no es ilegible) ---
    # La otra mitad del 16: si "no lo pude leer" bloqueara también el primer
    # alta de una máquina virgen, el fix habría cambiado un borrado por un
    # bloqueo permanente, y nadie podría dar de alta nada nunca.
    with tempfile.TemporaryDirectory(prefix="altas-") as tmp:
        d = repo(tmp)
        pj = os.path.join(tmp, "projects.json")            # NO existe
        v = altas.revisar(d, projects_file=pj, which=lambda x: None, vault_project_dir="")
        ok, motivo = altas.registrar(v, projects_file=pj)
        datos = json.load(open(pj, encoding="utf-8")) if os.path.isfile(pj) else {}
        check("17. registro ausente: el alta lo crea igual", ok and len(datos) == 1,
              f"ok={ok} motivo={motivo!r} datos={datos!r}")

    print()
    fallos = [n for n, ok, _ in results if not ok]
    print(f"[test-altas] {len(results) - len(fallos)}/{len(results)} en verde.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
