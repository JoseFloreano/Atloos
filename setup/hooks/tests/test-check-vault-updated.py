#!/usr/bin/env python3
"""
test-check-vault-updated.py — Arnés de contrato de setup/hooks/check-vault-updated.py.

POR QUÉ EXISTE AHORA. Este hook llevaba desde el principio sin arnés propio: sus
únicos casos vivían PRESTADOS en §E del arnés de `goal-evidence-guard`, y uno de
ellos (E.3) no medía un acierto sino una avería — que con `stop_hook_active`
puesto el anti-drift se calla el resto del bucle. Esa avería es D2 del RFD 18 y
aquí se arbitra: opción (b), «cada N ediciones de código sin registrar».

QUÉ FIJA ESTE ARNÉS, en dos mitades que hay que leer juntas:

  §A  Lo de antes NO se rompe: primer Stop con código sin registrar → exige;
      vault al día → calla y limpia; sin vault, sesión del bot o stdin ilegible
      → silencio total (fail-open).

  §B  El re-armado (D2·b): tras la cláusula de corte, el hook vuelve a exigir
      cuando se acumulan N ediciones de código nuevas sin registrar. N sale de
      `VAULT_DRIFT_EVERY` (default 10); basura → default; 0 → nunca re-arma
      (escotilla al comportamiento viejo, para quien lo quiera).

  §C  El fix de E.3: `stop_hook_active` deja de ser un silenciador general. Es
      el mismo criterio que ya usa `goal-evidence-guard` y por el que ese hook
      NO heredó la avería: la pregunta «¿el vault sigue desfasado?» tiene
      respuesta distinta en cada vuelta, y quien acota el bucle es la cláusula
      de corte (3 bloqueos), no el flag.

CANARIO, con los números MEDIDOS sobre estos 28 casos — no escritos a ojo, que
es como este mismo párrafo llegó a mentir en su primera versión hasta que una
revisión externa lo desmintió:

  - hook **mudo** (exit 0 siempre) → **16/28**; caen A.1 A.4 A.10 B.1 B.3 B.5
    B.6 B.8 B.11 C.1 C.2 D.2
  - hook que **bloquea siempre** (exit 2) → **11/28**; caen los 17 restantes

Ningún caso pasa bajo las dos mutaciones a la vez: no hay compuertas vacías.

§B.7-B.12 y §D existen porque cinco mutantes sobrevivieron a alguna versión de
este arnés: basura que desactiva el anti-drift en silencio, negativo aceptado
tal cual, negativo leído como escotilla, off-by-one temprano en el umbral, y un
`mark-code-dirty` que deja de contar. El más instructivo fue **un caso mío que
tampoco discriminaba**: medía el negativo por el lado de arriba («a las 10
re-arma»), que un hook con `cada=-1` cumple igual porque re-arma siempre.
Un caso que no puede fallar es peor que no tenerlo: ocupa el sitio del que sí.

Uso:  py setup/hooks/tests/test-check-vault-updated.py
Salida: una línea por caso + resumen; exit 1 si algo falla.
Sin dependencias externas: solo stdlib. No toca el vault ni el repo real.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.normpath(os.path.join(AQUI, os.pardir, "check-vault-updated.py"))
HERMANO = os.path.normpath(os.path.join(AQUI, os.pardir, "mark-code-dirty.py"))

results = []

# La consola de Windows es cp1252: un símbolo sin reconfigurar mata el arnés
# justo cuando tiene algo que decir (el bug de `valida-reporte.py`).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ── Laboratorio ───────────────────────────────────────────────────────────
def proyecto_lab(nombre="proyecto-lab"):
    """Proyecto temporal con vault falso y CLAUDE.md que lo nombra.

    Sin el vault el hook sale 0 SIEMPRE («proyecto no enganchado») y el arnés
    mediría su propio vacío en vez de decisiones — el fallo que ya se cazó una
    vez en §E del arnés del guard.
    """
    d = os.path.realpath(tempfile.mkdtemp(prefix="cvu-"))
    os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
    raiz = os.path.join(d, "_fake_onedrive")
    proj = os.path.join(raiz, "DevSetup", "ObsidianVault", "10-Projects", nombre)
    os.makedirs(os.path.join(proj, "sessions"), exist_ok=True)
    with open(os.path.join(proj, "_PROJECT.md"), "w", encoding="utf-8") as f:
        f.write("# lab\n\n## Pendientes\n")
    with open(os.path.join(d, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write(f"# lab\n\n## Active Project: `{nombre}`\n")
    return d, raiz, proj


def sucia(d, edits=1, **extra):
    """Flag de mark-code-dirty.py: se editó código y el vault no lo registró.

    `last_code_edit` va al futuro para que el vault quede desfasado sin depender
    de la resolución del mtime del sistema de ficheros.
    """
    estado = {"session_id": "s1", "last_code_edit": time.time() + 3600,
              "edits": edits}
    estado.update(extra)
    with open(os.path.join(d, ".claude", "vault-dirty.json"), "w",
              encoding="utf-8") as f:
        json.dump(estado, f)
    return estado


def flag(d):
    p = os.path.join(d, ".claude", "vault-dirty.json")
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def edita_codigo(d, veces=1):
    """Corre el hook HERMANO (mark-code-dirty) con un payload PostToolUse real.

    Existe porque `sucia()` escribe el flag a mano: con eso solo, este arnés
    nunca ejercita quién PRODUCE el contador, y un `mark-code-dirty` que dejara
    de contar pasaría los 22 casos sin despeinarse. Lo cazó una revisión
    externa por mutación (M9b).
    """
    for i in range(veces):
        payload = {"session_id": "s1", "hook_event_name": "PostToolUse",
                   "tool_name": "Edit",
                   "tool_input": {"file_path": os.path.join(d, f"mod{i}.py")}}
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = d
        subprocess.run([sys.executable, HERMANO],
                       input=json.dumps(payload).encode("utf-8"),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       cwd=d, env=env)


def tras_el_corte(d, raiz, mas, env_extra=None):
    """Gasta la cláusula de corte y acumula `mas` ediciones sin registrar.

    Devuelve (rc, stderr) del Stop siguiente. Es el escenario del re-armado y
    se repite en todo §B: escrito a mano en cada caso, un error de copia se
    leería como un fallo del hook.
    """
    sucia(d)
    for _ in range(4):
        corre(d, raiz, env_extra=env_extra)      # 3 bloqueos + el corte
    estado = flag(d)
    sucia(d, edits=int(estado.get("edits", 1)) + mas, **{
        k: v for k, v in estado.items()
        if k not in ("session_id", "last_code_edit", "edits")})
    return corre(d, raiz, env_extra=env_extra)


def corre(d, raiz, stop_hook_active=False, env_extra=None, payload=None):
    datos = payload if payload is not None else json.dumps(
        {"session_id": "s1", "hook_event_name": "Stop",
         "stop_hook_active": stop_hook_active, "cwd": d}).encode("utf-8")
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = d
    env["OneDrive"] = raiz
    env.pop("CLAUDE_TG_BOT", None)
    env.pop("VAULT_DRIFT_EVERY", None)
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable, HOOK], input=datos,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       cwd=d, env=env)
    return p.returncode, p.stderr.decode("utf-8", "replace")


def caso(nombre, rc, esperado, err=""):
    ok = rc == esperado
    results.append((nombre, ok))
    print(f"  [{'OK  ' if ok else 'FALLA'}] {nombre}  (exit {rc}, esperado {esperado})")
    if not ok and err:
        print("          stderr: " + (err.strip().splitlines() or [""])[0][:110])
    return ok


def afirma(nombre, condicion, detalle=""):
    results.append((nombre, bool(condicion)))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle}")


def limpia(d):
    shutil.rmtree(d, ignore_errors=True)


# ── Casos ─────────────────────────────────────────────────────────────────
def main():
    print("Arnés de check-vault-updated.py\n")

    # ── A · Lo que ya hacía, y no puede romperse ──────────────────────────
    print("A · contrato previo (regresión)")

    d, raiz, _ = proyecto_lab()
    sucia(d)
    rc, err = corre(d, raiz)
    caso("A.1 primer Stop con código sin registrar -> exige", rc, 2, err)
    limpia(d)

    d, raiz, _ = proyecto_lab()
    rc, err = corre(d, raiz)
    caso("A.2 sin flag de código sucio -> calla", rc, 0, err)
    limpia(d)

    d, raiz, proj = proyecto_lab()
    sucia(d)
    # El vault se actualiza DESPUÉS del código: mtime por delante de last_code_edit
    futuro = time.time() + 7200
    os.utime(os.path.join(proj, "_PROJECT.md"), (futuro, futuro))
    rc, err = corre(d, raiz)
    caso("A.3 _PROJECT.md actualizado tras el código -> calla", rc, 0, err)
    afirma("A.4 ...y borra el flag (no queda deuda para el próximo Stop)",
           flag(d) is None)
    limpia(d)

    d, raiz, proj = proyecto_lab()
    sucia(d)
    nota = os.path.join(proj, "sessions", "2026-08-10-lab.md")
    with open(nota, "w", encoding="utf-8") as f:
        f.write("avance\n")
    os.utime(nota, (futuro, futuro))
    rc, err = corre(d, raiz)
    caso("A.5 nota de sesión actualizada (vía multi-agente) -> calla", rc, 0, err)
    limpia(d)

    d, raiz, _ = proyecto_lab()
    sucia(d)
    os.remove(os.path.join(d, "CLAUDE.md"))   # sin nombre -> usa la carpeta, que no está en el vault
    rc, err = corre(d, raiz)
    caso("A.6 proyecto no enganchado al vault -> silencio total", rc, 0, err)
    limpia(d)

    d, raiz, _ = proyecto_lab()
    sucia(d)
    rc, err = corre(d, raiz, env_extra={"CLAUDE_TG_BOT": "1"})
    caso("A.7 sesión del daemon de Telegram -> no bloquea al bot", rc, 0, err)
    limpia(d)

    d, raiz, _ = proyecto_lab()
    sucia(d)
    rc, err = corre(d, raiz, payload=b"esto no es json")
    caso("A.8 stdin ilegible -> fail-open", rc, 0, err)
    limpia(d)

    d, raiz, _ = proyecto_lab()
    sucia(d)
    with open(os.path.join(d, ".claude", "vault-dirty.json"), "w",
              encoding="utf-8") as f:
        json.dump({"session_id": "OTRA", "last_code_edit": time.time() + 3600}, f)
    rc, err = corre(d, raiz)
    caso("A.9 flag huérfano de otra sesión -> calla", rc, 0, err)
    afirma("A.10 ...y lo borra", flag(d) is None)
    limpia(d)

    # ── B · D2·b: re-armado cada N ediciones sin registrar ────────────────
    print("\nB · D2 opción (b): el anti-drift se re-arma, no se muere")

    d, raiz, _ = proyecto_lab()
    sucia(d)
    rc1, _ = corre(d, raiz)
    rc2, err = corre(d, raiz)
    afirma(f"B.1 dos Stop seguidos sin registrar -> sigue exigiendo "
           f"({rc1} y {rc2}), no calla tras el primero",
           rc1 == 2 and rc2 == 2,
           "el comportamiento viejo («una vez por sesión») exigía una y se moría")
    limpia(d)

    d, raiz, _ = proyecto_lab()
    sucia(d)
    rcs = [corre(d, raiz)[0] for _ in range(4)]
    caso("B.2 al 4.º Stop, cláusula de corte -> sale ABIERTO", rcs[3], 0)
    afirma(f"B.3 ...tras exactamente 3 bloqueos (fueron {rcs.count(2)})",
           rcs[:3] == [2, 2, 2])
    rc, err = corre(d, raiz)
    caso("B.4 y sigue callado mientras no haya ediciones nuevas", rc, 0, err)
    limpia(d)

    # El corazón de D2: la sesión larga sigue trabajando, se acumulan ediciones
    # sin registrar y el hook VUELVE. Hoy (una vez por sesión) no volvía nunca.
    d, raiz, _ = proyecto_lab()
    rc, err = tras_el_corte(d, raiz, 10)
    caso("B.5 tras 10 ediciones nuevas sin registrar -> RE-ARMA y exige", rc, 2, err)
    limpia(d)

    d, raiz, _ = proyecto_lab()
    rc, err = tras_el_corte(d, raiz, 2, {"VAULT_DRIFT_EVERY": "2"})
    caso("B.6 N configurable: VAULT_DRIFT_EVERY=2 re-arma a las 2", rc, 2, err)
    limpia(d)

    # B.7 y B.9 miden lo MISMO por los dos lados, y hace falta: con solo la
    # mitad de arriba, un mutante que leyera la basura como 0 —desactivando el
    # anti-drift en silencio— pasaba el arnés entero. Lo cazó la revisión
    # externa. Una cifra inválida tiene que caer al default, no al silencio.
    d, raiz, _ = proyecto_lab()
    rc, err = tras_el_corte(d, raiz, 2, {"VAULT_DRIFT_EVERY": "abc"})
    caso("B.7 valor basura: 2 ediciones NO bastan (el default son 10)", rc, 0, err)
    limpia(d)

    d, raiz, _ = proyecto_lab()
    rc, err = tras_el_corte(d, raiz, 10, {"VAULT_DRIFT_EVERY": "abc"})
    caso("B.8 valor basura: a las 10 SÍ re-arma (default, no desactivado)", rc, 2, err)
    limpia(d)

    d, raiz, _ = proyecto_lab()
    rc, err = tras_el_corte(d, raiz, 100, {"VAULT_DRIFT_EVERY": "0"})
    caso("B.9 escotilla VAULT_DRIFT_EVERY=0 -> nunca re-arma", rc, 0, err)
    limpia(d)

    # Un negativo hay que medirlo por el lado TEMPRANO, y esto me lo enseñó un
    # mutante: «a las 10 re-arma» lo cumple igual un hook que acepte `-1` tal
    # cual (con cada=-1 re-arma SIEMPRE), así que ese caso no discriminaba nada.
    # El borde que separa «basura» de «escotilla» está abajo, no arriba.
    d, raiz, _ = proyecto_lab()
    rc, err = tras_el_corte(d, raiz, 2, {"VAULT_DRIFT_EVERY": "-1"})
    caso("B.10 negativo: 2 ediciones NO bastan (se lee como basura)", rc, 0, err)
    limpia(d)

    d, raiz, _ = proyecto_lab()
    rc, err = tras_el_corte(d, raiz, 10, {"VAULT_DRIFT_EVERY": "-1"})
    caso("B.11 negativo: a las 10 SÍ re-arma (basura, no escotilla)", rc, 2, err)
    limpia(d)

    # El umbral, por el lado TEMPRANO. Sin este caso todos los demás alimentan
    # exactamente N o de sobra, así que un `+ cada - 1` (re-armar una edición
    # antes) sobrevivía intacto: el borde solo estaba fijado por un lado.
    d, raiz, _ = proyecto_lab()
    rc, err = tras_el_corte(d, raiz, 9)
    caso("B.12 con N-1 ediciones (9 de 10) todavía NO re-arma", rc, 0, err)
    limpia(d)

    # ── C · El fix de E.3: stop_hook_active deja de amordazar ─────────────
    print("\nC · E.3 arreglado: stop_hook_active ya no es un silenciador")

    d, raiz, _ = proyecto_lab()
    sucia(d)
    rc, err = corre(d, raiz, stop_hook_active=True)
    caso("C.1 código sin registrar y stop_hook_active=True -> SIGUE exigiendo",
         rc, 2, err)
    limpia(d)

    d, raiz, _ = proyecto_lab()
    sucia(d)
    rc_sin, _ = corre(d, raiz, stop_hook_active=False)
    limpia(d)
    d, raiz, _ = proyecto_lab()
    sucia(d)
    rc_con, _ = corre(d, raiz, stop_hook_active=True)
    afirma(f"C.2 decide igual con el flag y sin él ({rc_sin} == {rc_con})",
           rc_sin == rc_con == 2,
           "era la avería E.3: el guard bloquea primero y el anti-drift enmudece")
    limpia(d)

    d, raiz, _ = proyecto_lab()
    sucia(d)
    rcs = [corre(d, raiz, stop_hook_active=True)[0] for _ in range(4)]
    caso("C.3 y aun así NO es un bucle infinito: al 4.º sale abierto", rcs[3], 0)
    limpia(d)

    d, raiz, proj = proyecto_lab()
    sucia(d)
    futuro2 = time.time() + 7200
    os.utime(os.path.join(proj, "_PROJECT.md"), (futuro2, futuro2))
    rc, err = corre(d, raiz, stop_hook_active=True)
    caso("C.4 con el vault al día calla también con el flag puesto", rc, 0, err)
    limpia(d)

    # ── D · El contador lo produce el hook hermano, no el arnés ───────────
    print("\nD · integración con mark-code-dirty (quien cuenta de verdad)")

    d, raiz, proj = proyecto_lab()
    pasado = time.time() - 7200          # vault viejo: el código llega después
    os.utime(os.path.join(proj, "_PROJECT.md"), (pasado, pasado))
    edita_codigo(d, 3)
    st = flag(d)
    afirma(f"D.1 tres ediciones REALES sellan el flag y cuentan 3 "
           f"(edits={st and st.get('edits')})",
           st is not None and st.get("edits") == 3,
           "si mark-code-dirty deja de contar, el re-armado no tiene con qué medir")
    rc, err = corre(d, raiz)
    caso("D.2 y el Stop exige sobre ESE flag, no sobre uno escrito a mano", rc, 2, err)
    limpia(d)

    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN:")
        for n in fallos:
            print(f"  - {n}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
