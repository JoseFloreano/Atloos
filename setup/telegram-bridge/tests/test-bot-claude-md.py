#!/usr/bin/env python3
"""
test-bot-claude-md.py — Regla a regla: qué conserva y qué tira la versión bot.

POR QUÉ EXISTE (2026-08-18). `bot_claude_md()` recortaba de un `## ` al
siguiente. En el `CLAUDE.md` de Atloos «Memory Rules» es el ÚLTIMO encabezado
`##`, así que su bloque llegaba hasta el final del fichero y sustituirlo se
llevaba por delante TODO lo que el snippet escribe después de las reglas
numeradas: párrafos sueltos, sin encabezado propio. **3 443 → 1 254 caracteres**,
medido.

Y no se perdían las órdenes imposibles que ese recorte existe para quitar —esas
son las reglas numeradas, y su exclusión es correcta—. Se perdían TRES que el
bot sí puede cumplir: el disparador de Graphify, el criterio de merge a `main`,
y la higiene de salida, que es la que más factura mueve en una sesión por
Telegram. Más el sello `snippet vN`, sin el cual una copia no puede decir qué
versión lleva.

POR QUÉ REGLA A REGLA Y NO POR TAMAÑO. Un arnés que midiera «el resultado pesa
más de N caracteres» daría verde conservando la basura y tirando lo bueno. Lo
que importa no es cuánto sobrevive: es CUÁL. Cada caso de aquí nombra una regla
concreta y dice si debe estar o no, con su motivo — que es lo que convierte el
recorte en una decisión auditable en vez de un efecto colateral del parseo.

EL CASO QUE MÁS IMPORTA NO ES NINGUNO DE LOS ANTERIORES. Es §D: **la función no
puede lanzar**. `create_worktree` la llama dentro de un `try/except OSError`, así
que un `TypeError` o un `AttributeError` se propaga y **ninguna conversación
nueva del bot podría abrirse**. El riesgo de tocar este fichero nunca fue
recortar de más: era romper el arranque. Por eso §D ejerce entradas hostiles
contra la función SIN la red del envoltorio, y luego comprueba que la red existe.

Uso:  setup/scripts/py setup/telegram-bridge/tests/test-bot-claude-md.py  [repo]
Salidas: 0 todos los casos OK · 1 alguno falló
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gitops                                                    # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

results = []


def caso(nombre, condicion, detalle=""):
    results.append(bool(condicion))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion and detalle:
        print(f"          {detalle}")


# El CLAUDE.md real de Atloos, en su forma que importa: «Memory Rules» es el
# ÚLTIMO `##` y todo lo demás son párrafos sueltos detrás. Se copia aquí en vez
# de leer el fichero porque `CLAUDE.md` está gitignorado — en un worktree o un
# clon nuevo no está, y un arnés que dependiera de él no correría donde más
# falta hace.
ORIGINAL = """# Atloos

Repo de docs + scripts del setup.

## Active Project: `atloos`

## Memory Rules — NON-NEGOTIABLE (anti cross-project hallucination)

1. Graphiti searches: ALWAYS `group_ids: ["atloos", "dev-global"]`.
   Never omit, never broaden, never `"main"`.
2. `add_episode`: ALWAYS `group_id: "atloos"`.
3. Vault: only `10-Projects/atloos/`, `brain/`, `daily/`.
6. Tu avance y tus pendientes van SIEMPRE a tu nota
   `10-Projects/atloos/sessions/YYYY-MM-DD-<tu-tarea>.md`.

At session start: `search_facts("recent decisions", group_ids=["atloos"])`, then read `10-Projects/atloos/_PROJECT.md`.

**Graphify — antes de la PRIMERA búsqueda de la sesión corre `graphify query "<lo que ibas a buscar>"`.** Su salida es la LISTA DE CANDIDATOS.

After completing each coding task: update Pendientes/Estado en TU nota de sesión (regla 6).

When saving decisions/bugs/conventions → `memory-keeper` skill. Architecture decisions → `adr-writer` skill.

**Para integrar CUALQUIER rama a `main`, el criterio es la skill `workstream-merge-gate`** — no otra.

**Higiene de salida — pide la respuesta, no el material** (medido en Atloos: −91 % a −99 % de bytes): `git log --oneline -n 50`, `git diff --stat`.

If the `graphiti-memory` MCP is unavailable, skip Graphiti silently — the vault is the primary record.

`snippet v6 · 2026-08-17` — si tu copia dice otra, va atrás.
"""


def main():
    print("bot_claude_md — qué conserva y qué tira\n")
    salida = gitops.bot_claude_md(ORIGINAL)

    print("A · lo que el bot SÍ puede cumplir y por tanto DEBE sobrevivir")
    caso("el disparador de Graphify", "graphify query" in salida,
         "el bot corre en un worktree con el repo: el CLI de grafo sí aplica")
    caso("el criterio de merge a `main`", "workstream-merge-gate" in salida,
         "es la regla que gobierna la integración; perderla es perder el gate")
    caso("la higiene de salida", "Higiene de salida" in salida and "−91" in salida,
         "la regla que más factura mueve en una sesión por Telegram")
    caso("el sello de versión del snippet", "snippet v6" in salida,
         "sin él, una copia no puede decir qué versión de las reglas lleva")
    caso("las convenciones del proyecto (el encabezado y el proyecto activo)",
         "# Atloos" in salida and "Active Project" in salida)

    print("\nB · lo que NO aplica en el puente y debe irse")
    caso("las reglas numeradas de Graphiti/vault", "add_episode" not in salida)
    caso("el arranque con `search_facts`", "search_facts" not in salida)
    # ⚠ NO se busca la frase «nota de sesión»: `BOT_REGLAS` la usa a propósito
    # —«la nota de sesión la escribe él al hacer /done»— así que prohibirla
    # ponía en rojo a la regla sustituta por decir la verdad. El primer intento
    # de este caso hacía exactamente eso. Se busca la ORDEN del original, que es
    # lo que debe desaparecer: el bot no actualiza pendientes en el vault.
    caso("la orden de actualizar Pendientes/Estado en el vault",
         "update Pendientes/Estado" not in salida,
         "es la orden que el daemon cumple por él; dejarla es pedir lo imposible")
    caso("`memory-keeper` / `adr-writer` (escriben en el vault)",
         "memory-keeper" not in salida and "adr-writer" not in salida)
    caso("el fallback del MCP `graphiti-memory`", "graphiti-memory" not in salida)

    print("\nC · la sustitución, no solo el recorte")
    caso("entran las reglas del puente", "versión puente Telegram" in salida)
    caso("y la que dice que lo pedido por chat se entrega por chat",
         "ARCHIVO:" in salida)
    # El defecto exacto que motivó todo esto, medido como se midió en campo.
    caso("no se cae la cola entera: la salida no colapsa a las reglas del bot",
         len(salida) > len(gitops.BOT_REGLAS) + 400,
         f"salida={len(salida)} chars — si ronda los 1 254 medidos en campo, "
         f"el corte volvió a llevarse todo lo que sigue a «Memory Rules»")

    print("\nD · no puede lanzar: si lanza, el bot no abre conversaciones")
    # Contra la función DESNUDA (`_bot_claude_md`), sin el envoltorio que
    # captura: un fallo tapado por el `except` es un fallo que nadie ve.
    for etiqueta, entrada in (("vacío", ""),
                              ("sin encabezados", "texto suelto\n"),
                              ("solo el encabezado", "## Memory Rules\n"),
                              ("sección vacía", "## Memory Rules\n\n\n"),
                              ("sin salto final", "## Memory Rules\n\n1. x")):
        try:
            gitops._bot_claude_md(entrada)
            ok, detalle = True, ""
        except Exception as exc:
            ok, detalle = False, f"{type(exc).__name__}: {exc}"
        caso(f"`_bot_claude_md` no lanza con {etiqueta}", ok, detalle)

    # Y la red, con la entrada que de verdad la rompía: algo que NO es cadena.
    # `read_text` devuelve `str`, así que en producción no debería pasar — pero
    # «no debería» es exactamente lo que cubre un fail-safe, y este caso destapó
    # que la propia rama de rescate hacía `.rstrip()` sobre el valor original y
    # lanzaba DENTRO del `except`. El envoltorio que existe para no lanzar,
    # lanzaba.
    for etiqueta, entrada in (("None", None), ("un entero", 123),
                              ("una lista", ["## Memory Rules"])):
        try:
            r = gitops.bot_claude_md(entrada)
            ok, detalle = isinstance(r, str), f"devolvió {type(r).__name__}"
        except Exception as exc:
            ok, detalle = False, (f"se escapó {type(exc).__name__}: con esto "
                                  f"`create_worktree` muere y el bot no abre "
                                  f"conversaciones nuevas")
        caso(f"el envoltorio sobrevive a {etiqueta}", ok, detalle)

    print("\nE · un CLAUDE.md ajeno no se toca")
    ajeno = "# Otro proyecto\n\n## Convenciones\n\nUsa tabs.\n"
    caso("sin sección Memory Rules se devuelve tal cual",
         gitops.bot_claude_md(ajeno).strip() == ajeno.strip())

    fallos = results.count(False)
    print(f"\n{len(results) - fallos}/{len(results)} casos OK")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
