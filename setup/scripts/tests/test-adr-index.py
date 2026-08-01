#!/usr/bin/env python3
"""
test-adr-index.py — Arnés de contrato de setup/scripts/adr-index.py.

Lanza el script como subproceso sobre carpetas temporales de ADRs falsos y
verifica el formato, los fallbacks, la idempotencia y los bytes del archivo
generado. Solo stdlib. Nunca toca el vault real.

Uso:  py setup/scripts/tests/test-adr-index.py
"""
import hashlib
import os
import subprocess
import sys
import tempfile

SCRIPT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "adr-index.py"))

results = []


def run(adrs_dir, *args):
    p = subprocess.run([sys.executable, SCRIPT, adrs_dir, *args],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def make_adr(adrs_dir, name, frontmatter="", body=""):
    os.makedirs(adrs_dir, exist_ok=True)
    path = os.path.join(adrs_dir, name)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        if frontmatter:
            f.write("---\n" + frontmatter.strip() + "\n---\n\n")
        f.write(body or "# Titulo del cuerpo\n")
    return path


def index_text(adrs_dir):
    with open(os.path.join(adrs_dir, "_INDEX.md"), "r", encoding="utf-8") as f:
        return f.read()


def index_bytes(adrs_dir):
    with open(os.path.join(adrs_dir, "_INDEX.md"), "rb") as f:
        return f.read()


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'OK  ' if ok else 'FALLA'}] {name}" + (f" -- {detail}" if detail and not ok else ""))


def proyecto(tmp):
    """Estructura real: <tmp>/claude-setup/ADRs/"""
    d = os.path.join(tmp, "claude-setup", "ADRs")
    os.makedirs(d, exist_ok=True)
    return d


def main():
    with tempfile.TemporaryDirectory(prefix="adridx-") as tmp:
        # --- Caso 1: tres ADRs bien formados, orden por fecha descendente ---
        d = proyecto(tmp)
        make_adr(d, "ADR-20260726-viejo.md",
                 "title: Decision vieja\ndate: 2026-07-26\nstatus: accepted\nsummary: La primera")
        make_adr(d, "ADR-20260801-nuevo.md",
                 "title: Decision nueva\ndate: 2026-08-01\nstatus: accepted\nsummary: La ultima")
        make_adr(d, "ADR-20260730-medio.md",
                 "title: Decision media\ndate: 2026-07-30\nstatus: proposed\nsummary: La de en medio")
        rc, out, err = run(d)
        txt = index_text(d)
        filas = [l for l in txt.splitlines() if l.startswith("| 2026-")]
        check("1. tres ADRs -> 3 filas en orden descendente",
              rc == 0 and len(filas) == 3
              and "2026-08-01" in filas[0] and "2026-07-30" in filas[1]
              and "2026-07-26" in filas[2], f"rc={rc} filas={len(filas)}")
        check("1b. cabecera con el nombre del proyecto",
              txt.startswith("# ADRs — claude-setup"), txt.splitlines()[0] if txt else "vacio")
        check("1c. wikilink al ADR", "[[ADR-20260801-nuevo]]" in txt)

        # --- Caso 2: idempotencia ---
        h1 = hashlib.sha256(index_bytes(d)).hexdigest()
        run(d)
        h2 = hashlib.sha256(index_bytes(d)).hexdigest()
        check("2. idempotente (mismo SHA-256 en dos corridas)", h1 == h2, f"{h1[:12]} vs {h2[:12]}")

        # --- Caso 10: bytes (sin BOM, sin CRLF) ---
        raw = index_bytes(d)
        check("10. UTF-8 sin BOM y sin CRLF",
              not raw.startswith(b"\xef\xbb\xbf") and b"\r\n" not in raw)

        # --- Caso 7: _INDEX.md no se auto-incluye ---
        run(d)
        check("7. _INDEX.md no aparece como ADR", "[[_INDEX]]" not in index_text(d))

        # --- Caso 8: --check ---
        rc, _, _ = run(d, "--check")
        check("8a. --check con indice al dia -> exit 0", rc == 0, f"rc={rc}")
        make_adr(d, "ADR-20260802-otro.md",
                 "title: Otra\ndate: 2026-08-02\nstatus: accepted\nsummary: Nueva decision")
        rc, _, _ = run(d, "--check")
        check("8b. --check con ADR nuevo -> exit 2", rc == 2, f"rc={rc}")

    with tempfile.TemporaryDirectory(prefix="adridx2-") as tmp:
        # --- Caso 3: sin date -> fecha del nombre del archivo ---
        d = proyecto(tmp)
        make_adr(d, "ADR-20260715-sinfecha.md",
                 "title: Sin fecha\nstatus: accepted\nsummary: Deduce la fecha")
        run(d)
        check("3. sin date: -> fecha del nombre", "| 2026-07-15 |" in index_text(d))

        # --- Caso 4: fallbacks de summary ---
        make_adr(d, "ADR-20260716-decision.md",
                 "title: Con decision\nstatus: accepted\ndecision: Usar Debian 13 headless")
        make_adr(d, "ADR-20260717-cuerpo.md",
                 "title: Solo cuerpo\nstatus: accepted",
                 "# Solo cuerpo\n\n## Contexto\n\nAlgo.\n\n## Decisión\n\n"
                 "**Postgres 17** como motor por defecto. Lo demas se decide luego.\n")
        run(d)
        txt = index_text(d)
        check("4a. sin summary -> usa decision:", "Usar Debian 13 headless" in txt)
        check("4b. sin summary ni decision -> primera frase de ## Decisión",
              "Postgres 17" in txt and "Lo demas se decide luego" not in txt, txt)

        # --- Caso 5: sin status -> unknown + aviso ---
        make_adr(d, "ADR-20260718-sinestado.md", "title: Sin estado\nsummary: Nada")
        rc, out, err = run(d)
        check("5. sin status -> 'unknown' y aviso por stderr",
              rc == 0 and "unknown" in index_text(d) and "ADR-20260718-sinestado" in err,
              f"rc={rc} err={err[:60]}")

        # --- Caso 6: pipe escapado ---
        make_adr(d, "ADR-20260719-pipe.md",
                 "title: Con pipe\nstatus: accepted\nsummary: Elegimos A | no B")
        run(d)
        linea = [l for l in index_text(d).splitlines() if "Elegimos" in l][0]
        check("6. '|' del summary escapado", r"A \| no B" in linea, linea)
        # Ojo: el backslash no impide que split('|') corte — hay que quitar los
        # escapes antes de contar columnas, o el test falla por su propia culpa.
        sin_escapes = linea.replace(r"\|", "")
        check("6b. la fila mantiene 4 columnas",
              len([c for c in sin_escapes.split("|") if c.strip()]) == 4, linea)

        # --- Caso 6c: pipe en el titulo ---
        make_adr(d, "ADR-20260720-titulo-pipe.md",
                 "title: Eleccion A | o B\nstatus: accepted\nsummary: Usando opcion A")
        run(d)
        linea_tp = [l for l in index_text(d).splitlines() if "Usando opcion A" in l][0]
        sin_escapes_tp = linea_tp.replace(r"\|", "")
        check("6c. titulo con pipe no rompe columnas",
              len([c for c in sin_escapes_tp.split("|") if c.strip()]) == 4, linea_tp)

    # --- Caso 9: errores ---
    with tempfile.TemporaryDirectory(prefix="adridx3-") as tmp:
        vacia = proyecto(tmp)
        rc, _, err = run(vacia)
        check("9a. carpeta sin ADRs -> exit 1", rc == 1, f"rc={rc}")
        rc, _, err = run(os.path.join(tmp, "no-existe"))
        check("9b. carpeta inexistente -> exit 1", rc == 1, f"rc={rc}")

    # --- Caso 11: '#' dentro del summary no se trunca (ya no hay strip de
    # comentario inline: el vocabulario de status vive en su propia linea con
    # '#' al inicio, que el guard startswith("#") sigue filtrando aparte) ---
    with tempfile.TemporaryDirectory(prefix="adridx4-") as tmp:
        d = proyecto(tmp)
        make_adr(d, "ADR-20260721-issue.md",
                 "title: Con numeral\nstatus: accepted\n"
                 "summary: Cerramos el issue #12 con el fix")
        run(d)
        linea = [l for l in index_text(d).splitlines() if "Cerramos" in l][0]
        check("11. '#' en el summary no se trunca",
              "Cerramos el issue #12 con el fix" in linea, linea)

    # --- Caso 12: ADR guardado con BOM sigue leyendose bien ---
    with tempfile.TemporaryDirectory(prefix="adridx5-") as tmp:
        d = proyecto(tmp)
        path = os.path.join(d, "ADR-20260722-bom.md")
        contenido = ("---\ntitle: Con BOM\ndate: 2026-07-22\nstatus: accepted\n"
                     "summary: Sobrevive al BOM\n---\n\n# Con BOM\n")
        with open(path, "w", encoding="utf-8-sig", newline="\n") as f:
            f.write(contenido)
        rc, out, err = run(d)
        txt = index_text(d)
        linea = [l for l in txt.splitlines() if "Sobrevive al BOM" in l]
        check("12. ADR con BOM -> status y summary se leen bien",
              rc == 0 and len(linea) == 1 and "accepted" in linea[0]
              and "unknown" not in linea[0],
              f"rc={rc} err={err[:80]!r} linea={linea}")

    fallos = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    # Nota: ahora son 19 casos (6c cubre titulo con pipe; 11 y 12 son las
    # regresiones de la revision de rama: '#' en summary y BOM en ADR)
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
