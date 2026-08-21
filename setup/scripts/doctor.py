#!/usr/bin/env python3
"""
doctor.py — Compara lo DESPLEGADO en ESTA maquina con lo que el repo declara.

POR QUE EXISTE (sprint 15, S2). De 29 arneses, **solo 2 miran algo desplegado**
—`test-claude-md-drift.py` y `test-unit-systemd.py`—, y el segundo declara su
propio limite: mira la PLANTILLA, no la copia instalada. Eso bastaba mientras
todo corria en una laptop con un humano delante. Ya no: la SER8 es headless y
24/7, y ahi nadie mira a ojo.

Y el alta demostro que la diferencia importa. `StartLimitBurst` y
`StartLimitIntervalSec` vivian en `[Service]`: systemd **aceptaba** la primera
por compatibilidad y **ignoraba** la segunda, las dos en silencio. La plantilla
decia una politica y el servicio obedecia otra. **Un doctor que solo leyera
ficheros no habria cazado eso**: hay que PREGUNTARLE A SYSTEMD. Por eso aqui se
corre `systemctl show` y `systemd-analyze verify`, no se parsea el .service.

LAS TRES REGLAS, y son el contrato:

  1. **Solo lee. NUNCA arregla.** Un diagnostico que repara esconde el problema
     que iba a contar, y en una maquina sin vigilancia eso es peor que el fallo.
  2. **No inventa.** Lo que no se puede mirar en esta maquina se dice con
     `[N/A]` y su motivo. Un check que no corrio no es un check que salio bien.
  3. **Sale != 0 SOLO si hay divergencia real**, no si algo no aplica. Si
     "no aplica" tumbara, en Windows saldria rojo siempre y se dejaria de correr
     — la enfermedad de la suite que nunca esta verde.

Uso:  setup/scripts/py setup/scripts/doctor.py            [desde el repo]
      setup/scripts/py setup/scripts/doctor.py --breve
Salidas: 0 sin divergencias · 1 hay divergencia real · 2 no se pudo localizar el repo
"""
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SERVICIO = "claude-telegram"
divergencias = []
no_aplica = []


def ok(m):      print(f"  [OK]      {m}")
def diverge(m, det=""):
    divergencias.append(m)
    print(f"  [DIVERGE] {m}")
    if det:
        for l in str(det).splitlines():
            print(f"            {l}")
def na(m, motivo):
    no_aplica.append(m)
    print(f"  [N/A]     {m} — {motivo}")
def titulo(t):  print(f"\n── {t} " + "─" * max(4, 66 - len(t)))


def corre(cmd, timeout=20):
    """(rc, salida). Nunca lanza: un doctor que revienta no diagnostica nada."""
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace").strip()
    except Exception as exc:
        return 127, f"{type(exc).__name__}: {exc}"


def raiz_repo():
    rc, out = corre(["git", "rev-parse", "--show-toplevel"])
    return Path(out) if rc == 0 and out else None


def hay_systemd_user():
    if os.name == "nt" or not shutil.which("systemctl"):
        return False
    rc, _ = corre(["systemctl", "--user", "--version"])
    return rc == 0


# ── 1 · La unit, preguntandole a systemd y no al fichero ──────────────────
def revisa_unit(raiz):
    titulo("1 · La unit desplegada, segun systemd")
    if not hay_systemd_user():
        na("unit de systemd", "no hay systemd de usuario en esta maquina "
                              "(Windows, o systemctl ausente)")
        return

    rc, _ = corre(["systemctl", "--user", "cat", SERVICIO])
    if rc != 0:
        na(f"unit {SERVICIO}", "no esta instalada en esta maquina")
        return

    claves = ["MemoryMax", "MemoryHigh", "MemorySwapMax", "Restart", "RestartSec",
              "StartLimitBurst", "StartLimitIntervalUSec", "ExecStart",
              "Environment", "ActiveState", "UnitFileState"]
    rc, out = corre(["systemctl", "--user", "show", SERVICIO]
                    + [a for c in claves for a in ("-p", c)])
    if rc != 0:
        diverge(f"no se pudo interrogar a systemd sobre {SERVICIO}", out)
        return
    v = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)

    if v.get("ActiveState") == "active":
        ok(f"{SERVICIO} activo")
    else:
        diverge(f"{SERVICIO} no esta activo", f"ActiveState={v.get('ActiveState')}")
    if v.get("UnitFileState") == "enabled":
        ok("enabled (arranca solo)")
    else:
        diverge("la unit NO esta enabled: no arrancara sola tras un reinicio",
                f"UnitFileState={v.get('UnitFileState')}")

    # LA FILA QUE MOTIVO ESTO. En [Service] systemd ignoraba el intervalo y
    # dejaba la ventana por defecto de 10 s (10000000 us).
    iv = v.get("StartLimitIntervalUSec", "")
    if iv in ("10s", "10000000"):
        diverge("StartLimitIntervalUSec = 10 s (el DEFECTO): la unit declara "
                "600 s y systemd no la esta obedeciendo",
                "Sintoma del bug del sprint 13: las StartLimit* en [Service] en "
                "vez de [Unit]. Comprueba con `systemd-analyze --user verify`.")
    elif iv:
        ok(f"StartLimitIntervalUSec = {iv} (no es el defecto de 10 s)")
    else:
        na("StartLimitIntervalUSec", "systemd no lo reporto")

    if v.get("MemorySwapMax") == "0":
        ok("MemorySwapMax = 0 (el techo mata en vez de irse a swap)")
    else:
        diverge("MemorySwapMax != 0: al llegar al techo el proceso se ira a "
                "SWAP en vez de morir", f"MemorySwapMax={v.get('MemorySwapMax')}")

    mx = v.get("MemoryMax", "")
    if mx and mx != "infinity":
        gb = int(mx) / (1024 ** 3) if mx.isdigit() else None
        ram = ram_total_gb()
        if gb and ram:
            # La plantilla trae 4G, que es el valor conservador PARA 24 GB.
            if ram >= 40 and gb <= 5:
                diverge(f"MemoryMax = {gb:.0f}G en una maquina de ~{ram:.0f} GB: "
                        f"es el valor de plantilla, sin ajustar",
                        "El fallo no se ve como error: el agente muere por OOM y "
                        "systemd lo reinicia; desde Telegram parece que 'el bot "
                        "se olvido de lo que estaba haciendo'.")
            else:
                ok(f"MemoryMax = {gb:.0f}G para ~{ram:.0f} GB de RAM")
        elif gb:
            na("MemoryMax contra la RAM", "no se pudo leer la RAM total")
    else:
        diverge("MemoryMax sin techo (infinity)")

    exe = v.get("ExecStart", "")
    m = re.search(r"path=([^\s;]+)", exe)
    interprete = m.group(1) if m else ""
    if not interprete:
        na("interprete del ExecStart", "no se pudo extraer de ExecStart")
    elif "venv" not in interprete:
        diverge(f"el ExecStart NO usa un venv: {interprete}",
                "Con python3 del sistema el arranque muere en el import de "
                "python-telegram-bot (PEP 668).")
    else:
        rc2, out2 = corre([interprete, "-c",
                           "import telegram,sys;print(sys.version.split()[0])"])
        if rc2 == 0:
            ok(f"el interprete del ExecStart arranca e importa telegram ({out2})")
        else:
            diverge(f"el interprete del ExecStart NO sirve: {interprete}", out2)

    if "CLAUDE_CONFIG_DIR" in v.get("Environment", ""):
        diverge("la unit exporta CLAUDE_CONFIG_DIR: el bot correria SIN los 6 "
                "hooks (auditoria 31, H4)")
    else:
        ok("sin CLAUDE_CONFIG_DIR: el bot conserva la capa 3")

    rc3, out3 = corre(["systemd-analyze", "--user", "verify",
                       str(Path.home() / ".config/systemd/user" / f"{SERVICIO}.service")])
    if rc3 == 0 and not out3:
        ok("systemd-analyze verify: sin avisos")
    elif rc3 == 127:
        na("systemd-analyze verify", "no disponible")
    else:
        diverge("systemd-analyze verify tiene algo que decir", out3[:600])


def ram_total_gb():
    try:
        for l in Path("/proc/meminfo").read_text().splitlines():
            if l.startswith("MemTotal:"):
                # MemTotal viene en kB (KiB). Se devuelve en GB DECIMALES, que es
                # como se venden: la SER8 son 56 GB y `free -g` dice 50.
                return int(l.split()[1]) * 1024 / 1e9
    except Exception:
        return None
    return None


# ── 2 · Los hooks cableados contra la fuente unica ────────────────────────
def revisa_hooks(raiz):
    titulo("2 · Hooks cableados contra hooks-map.json")
    mapa = raiz / "setup" / "hooks" / "hooks-map.json"
    if not mapa.is_file():
        diverge("no existe setup/hooks/hooks-map.json")
        return
    try:
        declarados = [h for h in json.loads(mapa.read_text(encoding="utf-8"))["hooks"]]
    except Exception as exc:
        diverge("hooks-map.json no se pudo leer", exc)
        return

    cfg = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))
    settings = cfg / "settings.json"
    if not settings.is_file():
        na("hooks cableados", f"no existe {settings}")
        return
    try:
        vivos = json.loads(settings.read_text(encoding="utf-8")).get("hooks") or {}
    except Exception as exc:
        diverge(f"{settings} no parsea", exc)
        return

    texto = json.dumps(vivos, ensure_ascii=False)
    faltan = [h["file"] for h in declarados if h["file"] not in texto]
    if faltan:
        diverge(f"{len(faltan)} de {len(declarados)} hooks declarados NO estan "
                f"cableados en {settings}", ", ".join(faltan))
    else:
        ok(f"los {len(declarados)} hooks de la fuente unica estan cableados")

    for h in declarados:
        f = cfg / "hooks" / h["file"]
        if not f.is_file():
            diverge(f"cableado pero AUSENTE en disco: {f}")


# ── 3 · El sello del snippet en cada CLAUDE.md vivo ───────────────────────
SELLO = re.compile(r"snippet v(\d+)\s*[·.]\s*(\d{4}-\d{2}-\d{2})")


def revisa_snippet(raiz):
    titulo("3 · El sello del snippet en los CLAUDE.md desplegados")
    fuente = (raiz / "setup" / "skills" / "claude-code" / "project-onboard"
              / "references" / "memory-snippet.md")
    if not fuente.is_file():
        diverge("no existe memory-snippet.md")
        return
    m = SELLO.search(fuente.read_text(encoding="utf-8"))
    if not m:
        diverge("la fuente del snippet no lleva sello de version")
        return
    v_src = int(m.group(1))
    ok(f"fuente: snippet v{v_src}")

    reg = raiz / "setup" / "telegram-bridge" / "projects.json"
    if not reg.is_file():
        na("CLAUDE.md desplegados", "no hay projects.json en esta maquina")
        return
    try:
        proyectos = json.loads(reg.read_text(encoding="utf-8"))
    except Exception as exc:
        diverge("projects.json no parsea", exc)
        return

    for nombre, cfg in proyectos.items():
        if nombre.startswith("_"):
            continue
        ruta = cfg if isinstance(cfg, str) else (cfg or {}).get("path")
        repo = Path(ruta or "")
        cmd = repo / "CLAUDE.md"
        # LOS DOS CASOS SON DISTINTOS Y SE CONFUNDIAN (medido en la SER8 el
        # 2026-08-18). Este check decia «el repo no esta en esta maquina»
        # mientras el doctor CORRIA DENTRO de ese repo: lo que faltaba era el
        # `CLAUDE.md`, que esta gitignorado y no viaja en el clon. Un
        # diagnostico que nombra la causa equivocada es peor que no tenerlo:
        # manda a mirar la maquina cuando el problema es el fichero.
        if not repo.is_dir():
            na(f"CLAUDE.md de {nombre}", "el repo no esta en esta maquina")
            continue
        if not cmd.is_file():
            diverge(f"{nombre}: el repo ESTA aqui pero NO tiene CLAUDE.md",
                    f"{cmd}\n"
                    f"`CLAUDE.md` esta gitignorado, asi que un clon nuevo nace "
                    f"sin el. Una sesion abierta ahi corre SIN las Memory "
                    f"Rules, sin el disparador de graphify, sin la linea del "
                    f"merge gate y sin la de higiene de salida.\n"
                    f"Se genera con la skill `project-onboard` desde ese repo.")
            continue
        mv = SELLO.search(cmd.read_text(encoding="utf-8", errors="replace"))
        if not mv:
            diverge(f"{nombre}: su CLAUDE.md no lleva sello")
        elif int(mv.group(1)) < v_src:
            diverge(f"{nombre}: va en v{mv.group(1)} y la fuente en v{v_src}")
        else:
            ok(f"{nombre}: v{mv.group(1)}")


# ── 4 · Disco y journald, que se llenan sin avisar ────────────────────────
def revisa_disco():
    titulo("4 · Disco y journald")
    if os.name == "nt":
        na("disco/journald", "checks de LVM y journald: solo Linux")
        return
    rc, out = corre(["df", "-h", "/"])
    if rc == 0 and len(out.splitlines()) > 1:
        campos = out.splitlines()[1].split()
        uso = campos[4] if len(campos) > 4 else "?"
        pct = int(uso.rstrip("%")) if uso.rstrip("%").isdigit() else 0
        (diverge if pct >= 85 else ok)(f"/ al {uso} ({campos[1]} totales)")
    else:
        na("uso de /", "df no disponible")

    rc, out = corre(["sh", "-c",
                     "cat /etc/systemd/journald.conf /etc/systemd/journald.conf.d/*.conf "
                     "2>/dev/null | grep -iE '^[^#]*SystemMaxUse'"])
    if out.strip():
        ok(f"journald con techo declarado: {' '.join(out.split())}")
    else:
        diverge("journald SIN SystemMaxUse: el journal crece sin techo",
                "En una maquina 24/7 con Restart=on-failure, un servicio que "
                "reinicia en bucle llena el disco y nadie lo ve.")

    rc, out = corre(["sh", "-c", "command -v lvs >/dev/null && lvs --noheadings -o lv_name,lv_size,data_percent 2>/dev/null"])
    if out.strip():
        ok(f"LVM: {' | '.join(l.strip() for l in out.splitlines())}")
    else:
        na("LVM", "no hay lvs o la maquina no usa LVM")


# ── 5 · La exencion del suelo, y cuanto le queda ──────────────────────────
def revisa_exencion(raiz):
    titulo("5 · La exencion del suelo de Python")
    f = raiz / "setup" / "scripts" / "tests" / "suelo-exenciones.json"
    if not f.is_file():
        na("exenciones", "no existe suelo-exenciones.json")
        return
    try:
        datos = json.loads(f.read_text(encoding="utf-8"))
    except Exception as exc:
        diverge("suelo-exenciones.json no parsea", exc)
        return
    import platform
    yo = (platform.node() or "").strip().lower()
    for clave, val in datos.items():
        if clave.startswith("_") or not isinstance(val, dict):
            continue
        try:
            quedan = (date.fromisoformat(str(val.get("hasta", ""))) - date.today()).days
        except ValueError:
            diverge(f"la exencion de '{clave}' no tiene fecha valida")
            continue
        mia = " ← ESTA maquina" if clave.strip().lower() == yo else ""
        if quedan < 0:
            diverge(f"la exencion de '{clave}' CADUCO hace {-quedan} dias{mia}")
        elif quedan <= 30:
            diverge(f"la exencion de '{clave}' caduca en {quedan} dias{mia}",
                    "Cuando caduque, la suite se pone ROJA a proposito. Toca "
                    "decidir: instalar el suelo, subirlo, o renovar con motivo.")
        else:
            ok(f"exencion de '{clave}': quedan {quedan} dias{mia}")


# ── 6 · El aviso de fallo, si esta cableado ───────────────────────────────
def revisa_aviso():
    titulo("6 · El aviso de fallo (OnFailure)")
    if not hay_systemd_user():
        na("OnFailure", "no hay systemd de usuario")
        return
    rc, out = corre(["systemctl", "--user", "show", SERVICIO, "-p", "OnFailure"])
    valor = out.split("=", 1)[1].strip() if "=" in out else ""
    if not valor:
        diverge("el servicio NO tiene OnFailure: si muere de verdad, nadie se "
                "entera", "Restart=on-failure lo mantiene arriba y por eso "
                "ESCONDE el fallo: desde fuera, un daemon que renace cada 30 s "
                "es indistinguible de uno sano.")
        return
    ok(f"OnFailure = {valor}")
    unidad = valor.split()[0]
    rc2, _ = corre(["systemctl", "--user", "cat", unidad])
    if rc2 != 0:
        diverge(f"OnFailure apunta a {unidad}, que NO esta instalada")


# ── 7 · El vault: la caja sin Obsidian es la que no sincroniza sola ───────
def revisa_vault(raiz):
    """La sincronia del vault en ESTA maquina.

    Existe por el fallo del 2026-08-19: el vault es un repo git que en las
    laptops mueve el plugin Git de Obsidian, y **la SER8 no tiene Obsidian**. El
    resultado era mudo por los dos lados — briefings viejos sin decir su edad, y
    notas de `/done` que solo existian en el disco de la SER8.

    El check que importa es el ultimo (el timer): los otros dos dicen COMO esta
    el vault ahora, y ese dice si hay algo que lo mantenga asi manana.
    """
    titulo("7 · El vault (sincronia)")
    sys.path.insert(0, str(raiz / "setup" / "telegram-bridge"))
    try:
        import vaultio
    except Exception as exc:                 # noqa: BLE001 — el doctor no revienta
        na("vault", f"no se pudo importar vaultio ({exc})")
        return
    root = vaultio.vault_root()
    if not root.parts or not root.is_dir():
        na("vault", "no hay vault en esta maquina")
        return
    ok(f"vault en {root}")
    if not (root / ".git").exists():
        na("sincronia del vault", "el vault no es un repo git en esta maquina")
        return
    if not vaultio.tiene_remoto(root):
        na("sincronia del vault", "el vault no tiene remoto")
        return

    # `ls-remote` y NO `fetch`: la regla 1 dice "solo lee, nunca arregla", y un
    # fetch escribe refs en el repo que esta diagnosticando. Distinto de "no
    # hace dano": aqui el doctor tiene que poder correr sin cambiar el sujeto.
    rc, rama = corre(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"])
    rama = rama.strip() if rc == 0 else ""
    rc, out = corre(["git", "-C", str(root), "ls-remote", "origin",
                     f"refs/heads/{rama}"], timeout=25)
    remoto = out.split()[0] if rc == 0 and out.split() else ""
    _, local = corre(["git", "-C", str(root), "rev-parse", "HEAD"])
    if not remoto:
        na("frescura del vault", "no se pudo consultar el remoto (sin red o sin credencial)")
    elif remoto == local.strip():
        ok(f"vault al dia con origin/{rama} (ni detras ni sin publicar)")
    else:
        rc, _ = corre(["git", "-C", str(root), "cat-file", "-e", remoto + "^{commit}"])
        if rc != 0:
            diverge(f"el vault esta DETRAS de origin/{rama}",
                    "hay commits en el remoto que aqui no estan, y el briefing "
                    "se sirve de ESTE disco: lo que lea sera viejo")
        else:
            _, n = corre(["git", "-C", str(root), "rev-list", "--count",
                          f"{remoto}..HEAD"])
            diverge(f"el vault tiene {n or '?'} commit(s) SIN PUBLICAR",
                    "incluidas las notas de /done: hoy solo existen en esta maquina")

    # Lo anterior es una foto; esto es lo que la mantiene fresca manana.
    if not hay_systemd_user():
        na("timer de sincronia del vault", "no hay systemd de usuario aqui")
        return
    rc, _ = corre(["systemctl", "--user", "cat", f"{SERVICIO}-vault.timer"])
    if rc == 0:
        ok(f"{SERVICIO}-vault.timer instalado (sustituye al plugin de Obsidian)")
    else:
        diverge(f"{SERVICIO}-vault.timer NO esta instalado",
                "sin el, en una maquina sin Obsidian el vault solo se mueve "
                "cuando alguien entra a hacer git pull a mano. "
                "Receta: setup/telegram-bridge/claude-telegram-vault.timer.example")


# ── 8 · El perfil recortado del bot: el ADR lo exige y nadie lo instala ──
def revisa_perfil_bot(raiz):
    """¿Corre el agente del puente con el perfil que el ADR decidio?

    Existe por el fallo del 2026-08-20: el daemon emitia
    `WARNING sin perfil bot (no hay directorio con skills): config normal`
    en LOS 6 arranques registrados desde el 08-18, y ese aviso va al journal,
    que no lee nadie. ADR-20260801-bot-memoria-y-perfil fija que el agente corre
    con un recorte de skills; en esta maquina corre con la superficie entera y
    la unica senal estaba enterrada.

    Aqui se saca a la superficie que SI se mira: el latido diario del doctor
    avisa al movil cuando algo diverge, asi que a partir de ahora esto insiste
    todos los dias hasta que se instale o se decida que no se instala.

    ⚠ Lo que NO hace: instalarlo. El repo no define QUE 15 skills entran (el
    doc 29 da la regla por superficie, no la lista), asi que inventarla aqui
    seria decidir por el humano una cosa que el RFD 30 tiene abierta.
    """
    titulo("8 · El perfil recortado del bot")
    puente = raiz / "setup" / "telegram-bridge"
    sys.path.insert(0, str(puente))
    try:
        import botprofile
    except ImportError as exc:
        na("perfil del bot", f"no se pudo importar botprofile ({exc})")
        return
    finally:
        sys.path.pop(0)

    ruta, motivo = botprofile.resolver()
    if ruta:
        ok(motivo)
        return
    diverge("el agente del puente NO usa el perfil recortado: " + motivo,
            "ADR-20260801-bot-memoria-y-perfil fija ~15 skills y los secretos "
            "denegados por ruta. Sin perfil, la superficie del agente que "
            "contesta al movil es mayor que la que se decidio. El aviso "
            "existia desde el 08-18 y vivia solo en el journal.")


def main():
    breve = "--breve" in sys.argv[1:]
    import platform
    print(f"doctor · {platform.node()} · {platform.system()} "
          f"{platform.release()} · {date.today()}")
    print("Solo LEE. No arregla nada.\n")

    raiz = raiz_repo()
    if raiz is None:
        print("[ERROR] no se pudo localizar el repo (git rev-parse fallo).",
              file=sys.stderr)
        return 2
    print(f"repo: {raiz}")

    revisa_unit(raiz)
    revisa_hooks(raiz)
    revisa_snippet(raiz)
    revisa_disco()
    revisa_exencion(raiz)
    revisa_aviso()
    revisa_vault(raiz)
    revisa_perfil_bot(raiz)

    print("\n" + "═" * 70)
    if divergencias:
        print(f"{len(divergencias)} DIVERGENCIA(S) entre lo desplegado y lo declarado:")
        for d in divergencias:
            print(f"  · {d}")
    else:
        print("Sin divergencias entre lo desplegado y lo que el repo declara.")
    if no_aplica and not breve:
        print(f"\n{len(no_aplica)} check(s) que esta maquina NO puede ejercer "
              f"—dicho, no fingido—:")
        for n in no_aplica:
            print(f"  · {n}")
    return 1 if divergencias else 0


if __name__ == "__main__":
    sys.exit(main())
