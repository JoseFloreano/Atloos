#!/usr/bin/env python3
"""
test-mergepol.py — Arnés de la guarda de la ruta PR del `/merge`.

EL CASO QUE MANDA ES EL 3. Con `gh` presente, el `/merge` abría el PR y lo
integraba **en la línea siguiente**: sin ventana de revisión, y sin que ninguna
de las dos guardas del camino local (árbol en `base`, árbol limpio) aplicara al
remoto. Eso está contenido hoy porque `gh` no está instalado (firma B1) — o sea,
**por la ausencia de un binario**: un `apt install` que lo arrastre cambiaba la
ruta en silencio, en la máquina 24/7.

Los otros dos que importan:
  · 6 — `auto` sigue existiendo, pero hay que ESCRIBIRLO. Que el comportamiento
    viejo esté a un env var de distancia es correcto; que fuera el default sin
    que nadie lo decidiera, no.
  · 8 — un valor mal escrito NO abre la ruta insegura. Un `CLAUDE_TG_PR_MERGE=Auto`
    con mayúscula que cayera en "auto" sería el fallo de siempre con otra cara.
    Aquí cae a `ventana` **diciéndolo**.

Y el 9: el motivo NUNCA va vacío. Este módulo nace de una contención que nadie
había declarado; un default mudo repetiría el fallo con otra cara.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-mergepol.py
Salidas: 0 todo verde · 1 algún caso falló
"""
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir)))
import mergepol  # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'OK  ' if ok else 'FALLA'}] {name}" + (f" -- {detail}" if detail and not ok else ""))


def main():
    # --- Caso 1: sin declarar nada, el default es la ventana ---
    m, motivo = mergepol.modo({})
    check("1. sin la variable declarada -> 'ventana'", m == "ventana", f"m={m!r}")

    # --- Caso 2: y ese default se DICE (no es mudo) ---
    check("2. el default trae motivo legible", bool(motivo) and "ventana" in motivo.lower(),
          f"motivo={motivo!r}")

    # --- Caso 3: EL CASO. Un PR recién abierto NO se integra en la misma pulsación ---
    d = mergepol.decidir("ventana", pr_creado_ahora=True)
    check("3. PR abierto en esta pulsación -> NO se integra",
          d["integrar"] is False and bool(d["motivo"]), f"d={d!r}")

    # --- Caso 4: un PR que ya existía sí se integra (la ventana ya ocurrió) ---
    d = mergepol.decidir("ventana", pr_creado_ahora=False)
    check("4. PR preexistente -> sí se integra", d["integrar"] is True, f"d={d!r}")

    # --- Caso 5: 'off' no integra NUNCA, ni con PR viejo ---
    malos = [pr for pr in (True, False)
             if mergepol.decidir("off", pr_creado_ahora=pr)["integrar"]]
    check("5. 'off' no integra en ningún caso", not malos, f"integró con creado={malos!r}")

    # --- Caso 6: 'auto' integra, pero hay que escribirlo a mano ---
    d_auto = mergepol.decidir("auto", pr_creado_ahora=True)
    m_auto, motivo_auto = mergepol.modo({mergepol.VAR: "auto"})
    check("6. 'auto' integra de una, y solo si se declara",
          d_auto["integrar"] is True and m_auto == "auto"
          and mergepol.modo({})[0] != "auto", f"d={d_auto!r} m={m_auto!r}")

    # --- Caso 7: y 'auto' dice que no hay ventana, no lo hace callando ---
    check("7. 'auto' declara que se salta la revisión",
          "sin ventana" in d_auto["motivo"].lower() or "revisi" in d_auto["motivo"].lower(),
          f"motivo={d_auto['motivo']!r}")

    # --- Caso 8: un valor que no se entiende cae al modo MÁS restrictivo ---
    # No al default: un `offf` mal tecleado cayendo en 'ventana' daría MENOS
    # restricción de la que su autor quiso, y `Auto` no puede abrir la ruta
    # permisiva por vía de una normalización que nadie validó. Falla cerrado.
    malos = [(c, mergepol.modo({mergepol.VAR: c})[0])
             for c in ("si", "1", "true", "ventanita", "offf", "auto ventana", "-")
             if mergepol.modo({mergepol.VAR: c})[0] != "off"]
    check("8. valor no reconocido -> 'off' (el más restrictivo)", not malos, f"malos={malos!r}")

    # --- Caso 8b: y ese valor se NOMBRA, con su forma cruda ---
    _m, motivo3 = mergepol.modo({mergepol.VAR: " ventanita "})
    check("8b. el valor inválido se nombra tal como se escribió",
          "ventanita" in motivo3, f"motivo={motivo3!r}")

    # --- Caso 8c: mayúsculas y espacios sí se normalizan (es la misma palabra) ---
    variantes = [(c, mergepol.modo({mergepol.VAR: c})[0]) for c in
                 ("OFF", " off ", "Ventana", "AUTO")]
    check("8c. ' OFF ' / 'Ventana' / 'AUTO' son sus modos, no basura",
          [v[1] for v in variantes] == ["off", "off", "ventana", "auto"], f"{variantes!r}")

    # --- Caso 8d: la política solo gobierna si la ruta PR se va a tomar ---
    # `merge_squash` va por el remoto solo con URL **y** `gh`. Con una pr_url
    # vieja en el estado y `gh` desinstalado el merge es LOCAL, y bloquearlo
    # aquí sería bloquear de más — que también es un fallo: una guarda en la que
    # no se confía se acaba apagando.
    tabla = [(("https://pr", "/usr/bin/gh"), True), (("https://pr", None), False),
             (("", "/usr/bin/gh"), False), (("", None), False)]
    malos_ap = [(args, mergepol.aplica(*args)) for args, esperado in tabla
                if mergepol.aplica(*args) != esperado]
    check("8d. aplica() exige PR **y** gh (si no, manda la ruta local)",
          not malos_ap, f"malos={malos_ap!r}")

    # --- Caso 9: ninguna combinación devuelve motivo vacío ---
    vacios = []
    for modo_ in mergepol.MODOS:
        for creado in (True, False):
            if not mergepol.decidir(modo_, creado).get("motivo", "").strip():
                vacios.append((modo_, creado))
    for crudo in ("", "off", "auto", "ventana", "basura"):
        if not mergepol.modo({mergepol.VAR: crudo})[1].strip():
            vacios.append(("modo", crudo))
    check("9. ningún camino devuelve un motivo vacío", not vacios, f"vacíos={vacios!r}")

    # --- Caso 10: la variable real del entorno no altera el veredicto del arnés ---
    # (se inyecta un dict a propósito; si `modo()` mirara os.environ igual, este
    # arnés diría cosas distintas según la máquina donde corre)
    os.environ[mergepol.VAR] = "auto"
    try:
        m4, _ = mergepol.modo({})
    finally:
        os.environ.pop(mergepol.VAR, None)
    check("10. el entorno inyectado manda sobre os.environ", m4 == "ventana", f"m={m4!r}")

    # --- Caso 11: el default de os.environ sigue siendo 'ventana' en esta máquina ---
    os.environ.pop(mergepol.VAR, None)
    check("11. sin variable en esta máquina -> 'ventana'",
          mergepol.modo()[0] == "ventana", f"m={mergepol.modo()!r}")

    print()
    fallos = [n for n, ok, _ in results if not ok]
    print(f"[test-mergepol] {len(results) - len(fallos)}/{len(results)} en verde.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
