#!/usr/bin/env python3
"""
test-perfil-hooks.py — El ahorro de tokens no puede apagar la capa 3.

EL CASO QUE MANDA es el 3: un perfil completo (skills + credenciales) pero SIN
hooks cableados NO se usa. Hasta la auditoria 31 se usaba, y en silencio: el bot
corria con 0 de 6 hooks justo en la maquina que trabaja sin humano delante, y la
configuracion RECOMENDADA (la que ahorra tokens) era la desprotegida.

El caso 5 es el otro lado del contrato: un perfil bien cableado SI se usa. Sin
el, "arreglar" esto seria tan facil como no usar perfil nunca, que apaga el
ahorro entero y nadie se enteraria hasta la factura.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-perfil-hooks.py
Salidas: 0 todo verde · 1 algun caso fallo
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir)))
import botprofile  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

results = []


def check(nombre, condicion, detalle=""):
    results.append((nombre, bool(condicion)))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle}")


def perfil(home, nombre, skills=True, creds=True, hooks=True):
    """Fabrica un perfil de laboratorio y devuelve su ruta."""
    base = Path(home) / nombre
    if skills:
        (base / "skills").mkdir(parents=True, exist_ok=True)
        (base / "skills" / "una-skill").mkdir(exist_ok=True)
    else:
        base.mkdir(parents=True, exist_ok=True)
    if creds:
        (base / ".credentials.json").write_text("{}", encoding="utf-8")
    if hooks is not None:
        contenido = {"hooks": {"Stop": [{"hooks": [{"type": "command",
                                                    "command": "x"}]}]}} if hooks else {}
        (base / "settings.json").write_text(json.dumps(contenido), encoding="utf-8")
    return base


def main():
    print("Arnes del perfil del bot: hooks o no hay perfil\n")

    # --- 1. El nombre nuevo es el que wire-hooks sabe encontrar ---
    # `wire-hooks.py` recorre `~/.claude` y `~/.claude-*`. Si el perfil no casa
    # con ese glob, el instalador no lo cablea y volvemos al agujero original.
    check("1. el nombre del perfil casa con el glob `~/.claude-*` de wire-hooks",
          botprofile.NOMBRE.startswith(".claude-") and botprofile.NOMBRE != ".claude",
          f"NOMBRE={botprofile.NOMBRE!r}: wire-hooks no lo va a cablear nunca")

    with tempfile.TemporaryDirectory(prefix="perfilbot-") as tmp:
        # --- 2. Sin ningun perfil -> config normal, sin drama ---
        ruta, motivo = botprofile.resolver(home=tmp, localappdata=tmp)
        check("2. sin directorio de perfil -> config normal",
              ruta == "" and motivo, f"ruta={ruta!r} motivo={motivo!r}")

    with tempfile.TemporaryDirectory(prefix="perfilbot-") as tmp:
        # --- 3. EL CASO QUE MANDA: perfil completo pero SIN hooks -> NO se usa ---
        perfil(tmp, botprofile.NOMBRE, hooks=False)
        ruta, motivo = botprofile.resolver(home=tmp, localappdata=tmp)
        check("3. perfil con skills y credenciales pero SIN hooks -> NO se usa",
              ruta == "",
              f"se uso {ruta!r}: el bot correria con 0 de 6 hooks, que es "
              f"exactamente el hallazgo H4 de la auditoria 31")
        check("3b. y lo dice en voz alta (el motivo nombra los hooks)",
              "HOOKS" in motivo.upper(),
              f"motivo={motivo!r}: un motivo mudo es como esto vivio 16 dias")

    with tempfile.TemporaryDirectory(prefix="perfilbot-") as tmp:
        # --- 4. settings.json ausente cuenta como sin cablear ---
        perfil(tmp, botprofile.NOMBRE, hooks=None)
        ruta, _ = botprofile.resolver(home=tmp, localappdata=tmp)
        check("4. perfil sin settings.json -> NO se usa (no hay cableado posible)",
              ruta == "", f"se uso {ruta!r}")

    with tempfile.TemporaryDirectory(prefix="perfilbot-") as tmp:
        # --- 5. El otro lado: perfil bien cableado SI se usa ---
        base = perfil(tmp, botprofile.NOMBRE)
        ruta, motivo = botprofile.resolver(home=tmp, localappdata=tmp)
        check("5. perfil con hooks cableados -> SI se usa (el ahorro sigue vivo)",
              ruta == str(base),
              f"ruta={ruta!r} esperada={str(base)!r} motivo={motivo!r}")

    with tempfile.TemporaryDirectory(prefix="perfilbot-") as tmp:
        # --- 6. Sin credenciales -> config normal (invariante de T3) ---
        perfil(tmp, botprofile.NOMBRE, creds=False)
        ruta, motivo = botprofile.resolver(home=tmp, localappdata=tmp)
        check("6. perfil sin .credentials.json -> config normal",
              ruta == "" and "credentials" in motivo,
              f"ruta={ruta!r} motivo={motivo!r}")

    with tempfile.TemporaryDirectory(prefix="perfilbot-") as tmp:
        # --- 7. El nombre viejo se reconoce, pero pasa por la MISMA aduana ---
        perfil(tmp, botprofile.NOMBRE_VIEJO, hooks=False)
        ruta, motivo = botprofile.resolver(home=tmp, localappdata=tmp)
        check("7. el nombre viejo sin hooks tampoco se usa (misma aduana)",
              ruta == "", f"se uso {ruta!r}")
        check("7b. y el aviso dice que hay que renombrarlo",
              botprofile.NOMBRE in motivo,
              f"motivo={motivo!r}: sin la instruccion, el usuario no sabe que hacer")

    with tempfile.TemporaryDirectory(prefix="perfilbot-") as tmp:
        # --- 8. Con los dos presentes, gana el nuevo ---
        nuevo = perfil(tmp, botprofile.NOMBRE)
        perfil(tmp, botprofile.NOMBRE_VIEJO)
        ruta, _ = botprofile.resolver(home=tmp, localappdata=tmp)
        check("8. si coexisten los dos nombres, gana el nuevo",
              ruta == str(nuevo), f"ruta={ruta!r} esperada={str(nuevo)!r}")

    with tempfile.TemporaryDirectory(prefix="perfilbot-") as tmp:
        # --- 9. settings.json roto no revienta el arranque del daemon ---
        base = perfil(tmp, botprofile.NOMBRE)
        (base / "settings.json").write_text("{ esto no es json", encoding="utf-8")
        try:
            ruta, _ = botprofile.resolver(home=tmp, localappdata=tmp)
            ok, detalle = ruta == "", f"se uso {ruta!r} con settings.json ilegible"
        except Exception as exc:
            ok, detalle = False, f"revento: {type(exc).__name__}: {exc}"
        check("9. settings.json roto -> no revienta y no se usa", ok, detalle)

    fallos = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
