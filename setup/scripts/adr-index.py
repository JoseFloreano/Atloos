#!/usr/bin/env python3
"""
adr-index.py — Genera ADRs/_INDEX.md desde el frontmatter de los ADRs.

Por qué existe: `project-resume` leía los 3 ADRs más recientes enteros en cada
arranque (~13 KB). Con el índice lee ~1 KB y abre el ADR completo solo cuando la
tarea lo pide (RFD 09 §3.3).

Determinista a propósito: sin LLM, sin marcas de tiempo, sin contadores. El
archivo generado debe ser byte a byte idéntico entre corridas y entre laptops —
de ahí UTF-8 sin BOM y '\\n' explícito (en este repo el BOM ya se perdió 2 veces).

Uso:
    py setup/scripts/adr-index.py <ruta-carpeta-ADRs>
    py setup/scripts/adr-index.py <ruta-carpeta-ADRs> --check

Salidas: 0 ok · 1 error · 2 (solo con --check) el índice está desfasado.
"""
import os
import re
import sys

FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
FECHA_EN_NOMBRE = re.compile(r"^ADR-(\d{4})(\d{2})(\d{2})-")
ENCABEZADO_DECISION = re.compile(r"^##\s+Decisi[oó]n\s*$", re.I | re.M)


def parse_frontmatter(texto: str) -> dict:
    """Frontmatter plano `clave: valor`. No es YAML: los ADRs no lo necesitan."""
    m = FRONTMATTER.match(texto)
    if not m:
        return {}
    campos = {}
    for linea in m.group(1).splitlines():
        linea = linea.split(" #")[0].rstrip()      # comentario inline
        if not linea.strip() or linea.lstrip().startswith("#") or ":" not in linea:
            continue
        clave, valor = linea.split(":", 1)
        campos[clave.strip().lower()] = valor.strip().strip('"').strip("'")
    return campos


def primera_frase_de_decision(texto: str) -> str:
    """Primera frase bajo '## Decisión'. Último recurso para el summary."""
    m = ENCABEZADO_DECISION.search(texto)
    if not m:
        return ""
    parrafo = []
    for linea in texto[m.end():].splitlines():
        if linea.strip() == "" and parrafo:
            break
        if linea.startswith("#"):
            break
        if linea.strip():
            parrafo.append(linea.strip())
    frase = " ".join(parrafo).replace("**", "").replace("`", "")
    corte = frase.find(". ")
    if corte != -1:
        frase = frase[:corte + 1]
    return frase.strip()


def leer_adr(ruta: str) -> dict:
    nombre = os.path.basename(ruta)
    with open(ruta, "r", encoding="utf-8", errors="replace") as f:
        texto = f.read()
    fm = parse_frontmatter(texto)

    fecha = fm.get("date", "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha):
        m = FECHA_EN_NOMBRE.match(nombre)
        fecha = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else "0000-00-00"

    titulo = fm.get("title", "")
    if not titulo:
        for linea in texto.splitlines():
            if linea.startswith("# "):
                titulo = linea[2:].strip()
                break
    if not titulo:
        titulo = nombre[:-3]

    # Solo `status:`. Aceptar `estado:` en español enmascararía justo el problema
    # que este índice viene a destapar (RFD 09 §1.2).
    estado = fm.get("status", "")
    if not estado:
        estado = "unknown"
        print(f"aviso: {nombre} no declara 'status:' — se indexa como 'unknown'",
              file=sys.stderr)

    resumen = fm.get("summary") or fm.get("decision") or primera_frase_de_decision(texto)

    return {"archivo": nombre[:-3], "fecha": fecha, "estado": estado,
            "titulo": titulo, "resumen": resumen or "—"}


def escapar(valor: str) -> str:
    return valor.replace("|", r"\|").strip()


def construir_indice(adrs: list, proyecto: str) -> str:
    lineas = [
        f"# ADRs — {proyecto}",
        "",
        "> Índice generado por `setup/scripts/adr-index.py`. No editar a mano:",
        "> los cambios se pierden en la siguiente generación.",
        "",
        "| Fecha | Estado | ADR | Decisión |",
        "|---|---|---|---|",
    ]
    for a in adrs:
        lineas.append(
            f"| {a['fecha']} | {escapar(a['estado'])} | [[{a['archivo']}]] | {escapar(a['resumen'])} |")
    return "\n".join(lineas) + "\n"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    solo_check = "--check" in sys.argv[1:]
    if len(args) != 1:
        print("uso: adr-index.py <ruta-carpeta-ADRs> [--check]", file=sys.stderr)
        return 1

    carpeta = os.path.abspath(args[0])
    if not os.path.isdir(carpeta):
        print(f"error: no existe la carpeta {carpeta}", file=sys.stderr)
        return 1

    archivos = sorted(f for f in os.listdir(carpeta)
                      if f.startswith("ADR-") and f.endswith(".md"))
    if not archivos:
        print(f"error: no hay ADR-*.md en {carpeta}", file=sys.stderr)
        return 1

    adrs = [leer_adr(os.path.join(carpeta, f)) for f in archivos]
    adrs.sort(key=lambda a: (a["fecha"], a["archivo"]), reverse=True)

    proyecto = os.path.basename(os.path.dirname(carpeta))
    contenido = construir_indice(adrs, proyecto)
    destino = os.path.join(carpeta, "_INDEX.md")

    if solo_check:
        actual_bytes = b""
        if os.path.isfile(destino):
            with open(destino, "rb") as f:
                actual_bytes = f.read()
        if actual_bytes != contenido.encode("utf-8"):
            print(f"desfasado: {destino} no coincide con los ADRs de la carpeta",
                  file=sys.stderr)
            return 2
        return 0

    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        f.write(contenido)
    print(f"{len(adrs)} ADRs indexados en {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
