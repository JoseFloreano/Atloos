# Higiene de contexto y ciclo de vida del vault — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bajar el arranque de sesión de ~36 KB a ~8-9 KB dándole a cada pieza de conocimiento del vault un destino y un final, sin perder nada de lo ya escrito.

**Architecture:** Un script determinista genera `ADRs/_INDEX.md` desde el frontmatter; las skills pasan a leer el índice y filtrar por estado en vez de leerlo todo; `_PROJECT.md` adopta un esqueleto cerrado y el historial rota a `sessions/`; los RFDs se cosechan a ADR y se borran redirigiendo antes sus referencias.

**Tech Stack:** Python 3 (solo stdlib), Markdown, PowerShell para el sync de skills. Dos repos git: `ClaudeSetup` y `obsidian-vault`.

**Diseño de origen:** `docs/arquitectura-memoria/09-RFD-HIGIENE-VAULT.md` (v2) · **Spec:** `docs/superpowers/specs/2026-08-01-higiene-vault-design.md`

## Global Constraints

- **Intérprete: `py`**, nunca `python` (el bare `python` apunta al stub de Microsoft Store y falla).
- **Solo stdlib.** Prohibido PyYAML o cualquier dependencia nueva.
- **Todo archivo generado: UTF-8 sin BOM y saltos `\n`.** En Python: `open(p, "w", encoding="utf-8", newline="\n")`. El BOM ya se perdió 2 veces en este repo.
- **Ningún dato variable en archivos generados** (fechas de generación, contadores, rutas absolutas): rompen la idempotencia.
- **Los `.ps1` se guardan con BOM UTF-8** (regla inversa, ya existente en el repo).
- **Dos repos, dos commits.** El vault (`ObsidianVault/`) tiene su propio git con remoto `JoseFloreano/obsidian-vault`; el repo `ClaudeSetup` es otro. Nunca mezclar.
- **Flujo de skills:** se editan en `setup/skills/`, se hace mirror a `OneDrive/DevSetup/claude-skills/` y luego `sync-skills.ps1`. Sin eso, los cambios no llegan a Claude Code.
- **Rutas de trabajo:**
  ```bash
  REPO="$HOME/OneDrive/Documentos/Mis_Documentos/Proyectos/Coding/Python/Otros/ClaudeSetup"
  VAULT="$HOME/OneDrive/DevSetup/ObsidianVault"
  P="$VAULT/10-Projects/claude-setup"
  ADRS="$P/ADRs"
  ```
- **Fuera de alcance:** migrar `alphadogs` o `tt1-revisor-chatbot`; hooks nuevos; subcarpetas temáticas en `ADRs/`; renombrar notas de sesión existentes; tocar los 4 hooks anti-drift, `sync-hooks.ps1`, `memory-keeper` o `project-onboard`.

---

### Task 1: Script generador del índice de ADRs

**Files:**
- Create: `setup/scripts/adr-index.py`
- Test: `setup/scripts/tests/test-adr-index.py`

**Interfaces:**
- Consumes: nada (primera tarea).
- Produces: CLI `py setup/scripts/adr-index.py <ruta-carpeta-ADRs> [--check]`. Exit 0 = ok · 1 = error (carpeta inexistente o sin ADRs) · 2 = solo con `--check`, el índice está desfasado. Genera `<ruta>/_INDEX.md`. Las tareas 4 y 6 invocan este CLI.

- [ ] **Step 1: Escribe el test que falla**

Crear `setup/scripts/tests/test-adr-index.py`:

```python
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
        linea = [l for l in index_text(d).splitlines() if "Con pipe" in l][0]
        check("6. '|' del summary escapado", r"A \| no B" in linea, linea)
        # Ojo: el backslash no impide que split('|') corte — hay que quitar los
        # escapes antes de contar columnas, o el test falla por su propia culpa.
        sin_escapes = linea.replace(r"\|", "")
        check("6b. la fila mantiene 4 columnas",
              len([c for c in sin_escapes.split("|") if c.strip()]) == 4, linea)

    # --- Caso 9: errores ---
    with tempfile.TemporaryDirectory(prefix="adridx3-") as tmp:
        vacia = proyecto(tmp)
        rc, _, err = run(vacia)
        check("9a. carpeta sin ADRs -> exit 1", rc == 1, f"rc={rc}")
        rc, _, err = run(os.path.join(tmp, "no-existe"))
        check("9b. carpeta inexistente -> exit 1", rc == 1, f"rc={rc}")

    fallos = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(fallos)}/{len(results)} casos OK")
    if fallos:
        print("FALLAN: " + ", ".join(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Córrelo para verificar que falla**

```bash
cd "$REPO" && py setup/scripts/tests/test-adr-index.py
```

Esperado: falla inmediatamente — el script no existe todavía (`can't open file ... adr-index.py`).

- [ ] **Step 3: Escribe el script**

Crear `setup/scripts/adr-index.py`:

```python
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
        # Comparación en BYTES, no en texto: leer en modo texto traduciría un
        # `\r\n` del disco a `\n` y --check diría "al día" sobre un archivo que
        # ya no cumple el requisito de saltos `\n`.
        actual = b""
        if os.path.isfile(destino):
            with open(destino, "rb") as f:
                actual = f.read()
        if actual != contenido.encode("utf-8"):
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
```

- [ ] **Step 4: Corre los tests hasta que pasen**

```bash
cd "$REPO" && py setup/scripts/tests/test-adr-index.py
```

Esperado: `16/16 casos OK` y exit 0. Si el caso 4b falla, revisa `primera_frase_de_decision`: debe cortar en el primer `". "` y quedarse solo con la primera frase.

> **Delta de ejecución (ronda de fix 1):** la revisión añadió un caso **6c** —
> un ADR cuyo `title:` lleva un `|`— como guarda de regresión frente a que
> alguien vuelva a meter el título en la fila sin escapar. Con él, el total
> final es **17/17**. Es una guarda, no un test de comportamiento: con el
> formato correcto el título no llega a la fila y el caso no puede fallar.

- [ ] **Step 5: Pruébalo contra los ADRs reales, sin escribir**

```bash
cd "$REPO" && py setup/scripts/adr-index.py "$ADRS" --check; echo "exit=$?"
```

Esperado: `exit=2` (aún no existe `_INDEX.md`) y en stderr dos avisos de `status:` ausente — los dos ADRs que usan `estado:` en español. **No lo generes todavía**: eso es la Task 8.

- [ ] **Step 6: Commit**

```bash
cd "$REPO"
git add setup/scripts/adr-index.py setup/scripts/tests/test-adr-index.py
git commit -m "feat(vault): script determinista de indice de ADRs con arnes de contrato"
```

---

### Task 2: `project-resume` lee el índice y filtra por estado

**Files:**
- Modify: `setup/skills/claude-code/project-resume/SKILL.md` (paso 3)
- Modify: `setup/skills/cowork/project-resume/SKILL.md` (paso 3)

**Interfaces:**
- Consumes: el CLI y el formato de `_INDEX.md` de la Task 1.
- Produces: nada que otras tareas consuman.

- [ ] **Step 1: Sustituye el paso 3 de la versión de Claude Code**

Texto actual a reemplazar:

```
3. Lee los **últimos ~3 ADRs** de `10-Projects/<nombre>/ADRs/` (por la fecha del
   nombre, descendente) y revisa `bugs/` por issues abiertos relevantes a la
   tarea de hoy.
```

Texto nuevo:

```
3. Lee `10-Projects/<nombre>/ADRs/_INDEX.md` — una línea por decisión, con su
   `summary`. **No abras los ADRs completos por defecto.** Abre uno entero solo
   si su fecha es ≥ la de la nota más reciente de `sessions/` (se decidió algo
   que aún no viviste) o si la tarea de hoy lo toca directamente.
   Si `_INDEX.md` no existe, el proyecto aún no está migrado: lee los ~3 ADRs
   más recientes como antes y avisa al usuario de que falta generar el índice
   (`py setup/scripts/adr-index.py <ruta ADRs>`).
4. Revisa `bugs/` **solo los `status: open`** (vocabulario cerrado:
   `open | fixed | invalid | wontfix`). Los cerrados se abren únicamente si la
   tarea de hoy los roza.

   > Presupuesto de arranque: si lo que vas a leer pasa de ~10 KB, algo está mal
   > — dilo en vez de leerlo.
```

Renumera los pasos siguientes (el antiguo 4 pasa a 5, y así).

- [ ] **Step 2: Aplica el mismo cambio en la versión de Cowork**

Texto actual a reemplazar en `setup/skills/cowork/project-resume/SKILL.md`:

```
3. Lista `ADRs/` y stage-a los **últimos ~3** (por la fecha `ADR-YYYYMMDD-*` en
   el nombre, descendente); revisa `bugs/` por issues abiertos relevantes.
```

Texto nuevo (mantiene el lenguaje de *stage-ar* propio de Cowork):

```
3. Stage-a **solo `ADRs/_INDEX.md`** y léelo: una línea por decisión con su
   `summary`. Stage-a un ADR completo únicamente si su fecha es ≥ la de la nota
   más reciente de `sessions/`, o si la tarea de hoy lo toca. Si `_INDEX.md` no
   existe, el proyecto no está migrado: stage-a los ~3 ADRs más recientes y
   dilo.
4. Revisa `bugs/` **solo los `status: open`** (`open | fixed | invalid | wontfix`).
```

Renumera los pasos siguientes.

- [ ] **Step 3: Verifica que ninguna de las dos skills sigue pidiendo leer 3 ADRs**

```bash
cd "$REPO" && grep -rn "3 ADRs\|últimos ~3\|ultimos ~3" setup/skills/*/project-resume/SKILL.md
```

Esperado: solo aparecen dentro de la frase de degradación ("si `_INDEX.md` no existe").

- [ ] **Step 4: Commit**

```bash
cd "$REPO"
git add setup/skills/claude-code/project-resume/SKILL.md setup/skills/cowork/project-resume/SKILL.md
git commit -m "feat(skills): project-resume lee el indice de ADRs y filtra bugs por estado"
```

---

### Task 3: `session-close` rota el historial y vigila el tope

**Files:**
- Modify: `setup/skills/shared/session-close/SKILL.md`

**Interfaces:**
- Consumes: el contrato de `_PROJECT.md` (Task 7 lo formaliza en la plantilla; esta tarea lo aplica al ritual).
- Produces: nada que otras tareas consuman.

- [ ] **Step 1: Añade el paso de rotación**

Insertar como primer paso del ritual, antes de los existentes:

```
1. **Rota el historial antes de tocar nada.** Lo hecho en esta sesión va a
   `10-Projects/<proyecto>/sessions/YYYY-MM-DD-<tarea>.md` (frontmatter de
   `templates/session-import.md`). De `_PROJECT.md` se tocan **solo** tres
   secciones: Estado actual (en presente), Pendientes y Próximo paso.

   **Prohibido crear secciones `## Hecho` en `_PROJECT.md`.** Ese archivo
   describe cómo está el proyecto hoy, no cómo llegó hasta aquí.
```

- [ ] **Step 2: Añade el chequeo del tope al final del ritual**

```
N. **Comprueba el tamaño de `_PROJECT.md`** (`wc -l`). Si pasa de **120
   líneas**, di qué sección conviene rotar a `sessions/` y ofrécelo — el tope
   duro es 150. **Avisa, no bloquees**: esto es una convención, no un hook.
```

- [ ] **Step 3: Verifica la coherencia interna de la skill**

```bash
cd "$REPO" && grep -n "Hecho\|120\|sessions/" setup/skills/shared/session-close/SKILL.md
```

Esperado: la prohibición de `## Hecho`, el tope de 120 y la ruta de `sessions/` aparecen y no se contradicen con pasos previos.

- [ ] **Step 4: Commit**

```bash
cd "$REPO"
git add setup/skills/shared/session-close/SKILL.md
git commit -m "feat(skills): session-close rota el historial a sessions/ y vigila el tope de _PROJECT.md"
```

---

### Task 4: `adr-writer` escribe el frontmatter nuevo y regenera el índice

**Files:**
- Modify: `setup/skills/shared/adr-writer/SKILL.md`

**Interfaces:**
- Consumes: CLI de la Task 1 (`py setup/scripts/adr-index.py <ruta ADRs>`).
- Produces: ADRs con `summary:` — la celda "Decisión" del índice depende de ello.

- [ ] **Step 1: Fija el frontmatter obligatorio**

Añadir al paso donde se escribe el ADR:

```
Frontmatter obligatorio (el índice se genera de aquí):

```yaml
---
title: <título de la decisión>
date: YYYY-MM-DD
status: proposed | accepted | rejected | superseded-by: ADR-YYYYMMDD-<tema>
summary: <UNA frase: qué se decidió. Es la celda que se lee en el índice>
tags: [<tema>, <subsistema>]
---
```

`summary` no es opcional: sin él, quien arranque una sesión ve el título y nada
más. Nada de `estado:` en español — el vocabulario es el de MADR, en inglés.
```

- [ ] **Step 2: Añade el paso de regeneración del índice**

Justo después del paso 4 (el del wikilink en `_PROJECT.md`):

```
5. **Regenera el índice**:

   ```bash
   py setup/scripts/adr-index.py "<vault>/10-Projects/<proyecto>/ADRs"
   ```

   Verifica que la línea del ADR nuevo aparece en `ADRs/_INDEX.md`. Si el script
   avisa de un `status:` ausente en otro ADR, arréglalo de paso: un ADR sin
   estado es invisible para la auditoría del vault.
```

- [ ] **Step 3: Verifica**

```bash
cd "$REPO" && grep -n "summary\|adr-index" setup/skills/shared/adr-writer/SKILL.md
```

Esperado: `summary` marcado como obligatorio y la llamada al script presente.

- [ ] **Step 4: Commit**

```bash
cd "$REPO"
git add setup/skills/shared/adr-writer/SKILL.md
git commit -m "feat(skills): adr-writer fija el frontmatter con summary y regenera el indice"
```

---

### Task 5: `design-doc-harvest` cubre el ciclo de vida de los RFDs

**Files:**
- Modify: `setup/skills/shared/design-doc-harvest/SKILL.md`

**Interfaces:**
- Consumes: nada.
- Produces: el procedimiento que la Task 9 usará (parcialmente) para el ADR de cierre.

- [ ] **Step 1: Amplía el paso 1 a los RFDs**

Texto actual:

```
1. **Localiza los docs del trabajo terminado**: `docs/superpowers/specs/*.md` y
   `docs/superpowers/plans/*.md` (o la ruta que fije el CLAUDE.md).
```

Texto nuevo:

```
1. **Localiza los docs del trabajo terminado**: `docs/superpowers/specs/*.md`,
   `docs/superpowers/plans/*.md` y los **RFDs** de `docs/**/*RFD*.md` (o la ruta
   que fije el CLAUDE.md).

   Un RFD se cosecha según su estado:

   | Estado del RFD | Qué se hace |
   |---|---|
   | Propuesta abierta / en discusión | se queda |
   | Aprobado pero **no** implementado | se queda |
   | Implementado **y con las condiciones de auditoría cerradas** | cosecha → ADR → `git rm` |
   | Abandonado | se borra sin ADR, con confirmación |

   "Auditado" significa **condiciones de auditoría cerradas**, no "hubo
   auditoría". Un RFD con la auditoría aprobada *con condiciones* pendientes NO
   se cosecha.
```

- [ ] **Step 2: Añade la regla de "enriquecer, no duplicar" al paso 4**

Añadir al final del paso 4 (el de `adr-writer`):

```
   **Si la decisión ya tiene ADR, la cosecha lo enriquece — no crea otro.**
   Dos ADRs sobre el mismo asunto reproducen en la capa durable la divergencia
   que la cosecha venía a eliminar.
```

- [ ] **Step 3: Añade la redirección de referencias como paso previo al borrado**

Insertar ANTES del paso de `git rm`:

```
5. **Redirige las referencias entrantes.** "Git conserva la historia" es cierto
   para el contenido y falso para los enlaces:

   ```bash
   grep -rl -E "RFD NN|NN-RFD" docs/
   ```

   Actualiza cada cita para que apunte al ADR resultante. Solo cuando el grep
   deje de devolver referencias huérfanas se borra el archivo. (Precedente: el
   RFD 02 lo citaban 9 documentos.)
```

Renumera los pasos siguientes.

- [ ] **Step 4: Verifica que el orden es correcto**

```bash
cd "$REPO" && grep -n "grep -rl\|git rm\|enriquece" setup/skills/shared/design-doc-harvest/SKILL.md
```

Esperado: la redirección aparece **antes** del `git rm` en el orden del archivo.

- [ ] **Step 5: Commit**

```bash
cd "$REPO"
git add setup/skills/shared/design-doc-harvest/SKILL.md
git commit -m "feat(skills): design-doc-harvest cosecha RFDs y redirige referencias antes de borrar"
```

---

### Task 6: `vault-drift-audit` con tres chequeos nuevos y cuerpo adelgazado

**Files:**
- Modify: `setup/skills/cowork/vault-drift-audit/SKILL.md`
- Create: `setup/skills/cowork/vault-drift-audit/references/checks.md`

**Interfaces:**
- Consumes: `adr-index.py --check` (Task 1), el tope de 120 líneas (Task 3), la marca de nota cosechada (Task 8).
- Produces: nada.

- [ ] **Step 1: Mide el cuerpo actual**

```bash
cd "$REPO" && wc -w < setup/skills/cowork/vault-drift-audit/SKILL.md
```

Esperado: ~452. El tope sano es 500, así que los chequeos nuevos van a `references/`, no al cuerpo.

- [ ] **Step 2: Crea `references/checks.md`**

```markdown
# Chequeos del audit — detalle operativo

Comandos y umbrales. El cuerpo de la skill solo dice QUÉ mirar; aquí está el CÓMO.

## Índice de ADRs desfasado

```bash
py setup/scripts/adr-index.py "<vault>/10-Projects/<proyecto>/ADRs" --check
```

Exit 2 = el índice no refleja los ADRs de la carpeta (alguien escribió uno a
mano). Se arregla corriendo el mismo comando sin `--check`.

## Tope de `_PROJECT.md`

```bash
wc -l < "<vault>/10-Projects/<proyecto>/_PROJECT.md"
```

- \> 120 líneas: proponer qué rotar a `sessions/`.
- \> 150 líneas: reincidencia — el ritual de cierre no se está aplicando en esa
  laptop; revisar por qué antes de proponer nada más.
- Cualquier sección `## Hecho`: es historial en el sitio equivocado, siempre.

## Notas de sesión cosechadas

Una nota con `harvested: true` en el frontmatter y más de ~30 días de antigüedad
es candidata a `10-Projects/<proyecto>/_archive/`. **Proponer, nunca mover sin
aprobación**: el usuario decide qué deja de estar a la vista.

## Frontmatter de ADRs

```bash
grep -L "^status:" <vault>/10-Projects/<proyecto>/ADRs/ADR-*.md
```

Cualquier archivo listado es invisible para el chequeo de ADRs contradictorios.
```

- [ ] **Step 3: Añade tres líneas al cuerpo de la skill**

En el paso 3 ("Señales internas"), añadir:

```
   Además (detalle y comandos en `references/checks.md`): índice de ADRs
   desfasado (`adr-index.py --check`), `_PROJECT.md` por encima de 120 líneas o
   con secciones `## Hecho`, y notas de `sessions/` ya cosechadas con más de 30
   días — candidatas a `_archive/`.
```

- [ ] **Step 4: Verifica que el cuerpo no se disparó**

```bash
cd "$REPO" && wc -w < setup/skills/cowork/vault-drift-audit/SKILL.md
```

Esperado: por debajo de 500.

- [ ] **Step 5: Commit**

```bash
cd "$REPO"
git add setup/skills/cowork/vault-drift-audit/
git commit -m "feat(skills): vault-drift-audit vigila indice, tope y notas cosechadas"
```

---

### Task 7: Sincroniza las skills y actualiza las plantillas del vault

**Files:**
- Modify: `OneDrive/DevSetup/claude-skills/**` (mirror)
- Modify: `$VAULT/templates/project-note.md`
- Modify: `$VAULT/templates/adr.md`

**Interfaces:**
- Consumes: las skills editadas en las tasks 2-6.
- Produces: plantillas que la Task 8 usa como molde de `_PROJECT.md`.

- [ ] **Step 1: Mirror + sync de las skills**

Flujo del repo: mirror por categoría (rm + cp de las tres tocadas), luego sync.

```bash
SK="$HOME/OneDrive/DevSetup/claude-skills"
rm -rf "$SK/shared" "$SK/claude-code" "$SK/cowork"
cp -r "$REPO/setup/skills/shared" "$REPO/setup/skills/claude-code" "$REPO/setup/skills/cowork" "$SK/"
ls "$SK"/shared/adr-writer/SKILL.md "$SK"/cowork/vault-drift-audit/references/checks.md
```

Esperado: los dos archivos existen — confirma que el mirror arrastró también el `references/` nuevo.

```powershell
cd "$REPO"; .\setup\sync-skills.ps1
```

Esperado: el conteo de skills **no cambia** (no añadimos ninguna) y el zip de Cowork se regenera. El zip hay que re-subirlo a mano en Cowork (Customize → Plugins): es el único paso manual del sync.

- [ ] **Step 2: Reescribe `$VAULT/templates/project-note.md`**

```markdown
---
title: <Proyecto>
tags: [project]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: active
type: project
project: <slug>
---

# <Proyecto>

## Qué es
<2-4 líneas: qué es y dónde vive el código.>

## Estado actual
<Presente, no historia. Cómo está el sistema HOY.>

## Decisiones clave
<!-- wikilinks a los ADRs; el detalle vive en ADRs/_INDEX.md -->

## Bugs abiertos
<!-- solo status: open; los cerrados se quedan en bugs/ -->

## Convenciones que difieren del default

## Pendientes

## Próximo paso

<!--
Tope: 120 líneas (duro 150). PROHIBIDAS las secciones "## Hecho": lo que pasó
va a sessions/YYYY-MM-DD-<tarea>.md. session-close lo verifica al cerrar.
-->
```

- [ ] **Step 3: Actualiza el frontmatter de `$VAULT/templates/adr.md`**

Sustituye su frontmatter por:

```yaml
---
title: <título de la decisión>
date: YYYY-MM-DD
status: proposed
# status: proposed | accepted | rejected | superseded-by: ADR-YYYYMMDD-<tema>
summary: <UNA frase: qué se decidió. Es la celda que se lee en ADRs/_INDEX.md>
tags: []
project: <slug>
---
```

El cuerpo (Contexto / Decisión / Alternativas consideradas / Consecuencias) no cambia.

- [ ] **Step 4: Commit del vault (repo distinto)**

```bash
cd "$VAULT"
git add templates/project-note.md templates/adr.md
git commit -m "feat(templates): contrato de _PROJECT.md y frontmatter de ADR con summary"
```

---

### Task 8: Migración del vault de `claude-setup`

**Files:**
- Create: `$P/sessions/2026-08-01-telegram-t0.md`
- Create: `$P/sessions/2026-07-26-cowork-adrs-y-bugs.md`
- Create: `$P/sessions/2026-07-24-onboarding-y-sync-hooks.md`
- Modify: `$P/sessions/20260801-ahorro-tokens-r1-r5-r7.md`
- Modify: `$P/sessions/20260801-registro-secretos-y-esqueletos.md`
- Modify: `$P/_PROJECT.md`
- Modify: `$P/ADRs/ADR-20260801-os-servidor-24-7.md`, `$P/ADRs/ADR-20260801-puente-telegram.md` (y `summary:` en los otros 3)
- Create: `$P/ADRs/_INDEX.md` (generado)

**Interfaces:**
- Consumes: script de la Task 1, plantillas de la Task 7.
- Produces: el vault migrado que la Task 9 verifica.

- [ ] **Step 1: Punto de retorno**

```bash
cd "$VAULT" && git add -A && git commit -m "chore: punto de retorno antes de migrar claude-setup" && git log -1 --format=%H
```

Guarda el sha: es el rollback si algo sale mal.

- [ ] **Step 2: Re-verifica el inventario (el archivo se ha movido durante el diseño)**

```bash
grep -n "^## " "$P/_PROJECT.md"; wc -l < "$P/_PROJECT.md"
```

Esperado: 6 secciones `## Hecho`. Si aparecen más (otra sesión escribió), añádelas al mapa del paso 3 antes de seguir.

- [ ] **Step 3: Mueve cada bloque a su destino**

Mapa (el contenido se mueve **textualmente**, sin reescribir):

| Sección de `_PROJECT.md` | Destino |
|---|---|
| `## Hecho (2026-08-01) — Telegram T0` | **nueva** `sessions/2026-08-01-telegram-t0.md` |
| `## Hecho (2026-08-01) — Ahorro de tokens: R1, R5 y R7` | fusionar en `sessions/20260801-ahorro-tokens-r1-r5-r7.md` |
| `## Hecho (2026-08-01) — Registro de secretos` | fusionar en `sessions/20260801-registro-secretos-y-esqueletos.md` |
| `## Hecho (2026-07-26, Cowork)` | **nueva** `sessions/2026-07-26-cowork-adrs-y-bugs.md` |
| `## Hecho esta sesión (2026-07-24)` | **nueva** `sessions/2026-07-24-onboarding-y-sync-hooks.md` |
| `## Hecho (2026-08-01) — Fix del falso positivo` | 1 línea en Estado actual + `[[bug-mark-code-dirty-falso-positivo]]` |

Frontmatter de las notas nuevas (con **la fecha real del trabajo**, no la de hoy):

```yaml
---
title: <lo que dice el encabezado del bloque>
tags: [session, claude-setup]
created: <fecha real>
updated: <fecha real>
status: done
type: session
project: claude-setup
harvested: false
---
```

En las dos notas que se fusionan, el bloque entra como sección propia al final:
`## Lo que quedó registrado en _PROJECT.md (migrado el 2026-08-01)`.

- [ ] **Step 4: Verifica que no se perdió nada ANTES de reescribir `_PROJECT.md`**

```bash
grep -rl "Curator de Hermes"  "$P/sessions/"   # ahorro de tokens
grep -rl "floreanoclaudebot"  "$P/sessions/"   # Telegram T0
grep -rl "separate-git-dir\|post-commit"  "$P/sessions/"   # Cowork 07-26
grep -rl "sync-hooks.ps1"     "$P/sessions/"   # onboarding 07-24
```

Cada comando debe devolver al menos un archivo. **Si alguno sale vacío, para**: ese bloque no llegó a su destino.

- [ ] **Step 5: Reescribe `_PROJECT.md` con el esqueleto**

Aplica el molde de la Task 7 conservando el contenido vivo. Reglas:

- "Estado actual" en presente, ≤12 líneas.
- "Bugs abiertos": hoy **ninguno** (los 3 están cerrados) — deja la sección con una línea que lo diga y el puntero a `bugs/`.
- Conserva los wikilinks existentes: `[[20260801-ahorro-tokens-r1-r5-r7]]`, `[[20260801-registro-secretos-y-esqueletos]]`, `[[2026-08-01-telegram-t2]]`.
- Añade los wikilinks a las 3 notas nuevas en Estado actual.
- Objetivo: **≤120 líneas**.

```bash
wc -l < "$P/_PROJECT.md"; grep -c "^## Hecho" "$P/_PROJECT.md"
```

Esperado: ≤120 y `0`.

- [ ] **Step 6: Unifica el frontmatter de los 5 ADRs**

Los dos con `estado:` en español pasan a `status:` (`propuesta`→`proposed`, `aceptada`→`accepted`) y **los cinco** reciben `summary:` de una frase. Quita el comentario inline del ADR del servidor.

```bash
grep -L "^status:" "$ADRS"/ADR-*.md    # sin salida = todos migrados
grep -L "^summary:" "$ADRS"/ADR-*.md   # sin salida = todos tienen resumen
```

- [ ] **Step 7: Genera el índice y comprueba la idempotencia**

```bash
cd "$REPO"
py setup/scripts/adr-index.py "$ADRS" && sha256sum "$ADRS/_INDEX.md"
py setup/scripts/adr-index.py "$ADRS" && sha256sum "$ADRS/_INDEX.md"
py -c "d=open(r'$ADRS/_INDEX.md','rb').read(); assert not d.startswith(b'\xef\xbb\xbf'); assert b'\r\n' not in d; print('encoding OK')"
```

Esperado: mismo hash las dos veces, `encoding OK`, y **cero avisos** de `status:` en stderr.

- [ ] **Step 8: Commit del vault**

```bash
cd "$VAULT"
git add "10-Projects/claude-setup"
git commit -m "refactor(vault): _PROJECT.md al contrato nuevo, historial rotado a sessions/ e indice de ADRs"
```

---

### Task 9: Cierre — ADR de la decisión y verificación de extremo a extremo

**Files:**
- Create: `$P/ADRs/ADR-20260801-higiene-vault.md`
- Modify: `$P/ADRs/_INDEX.md` (regenerado)
- Modify: `$P/_PROJECT.md` (wikilink en Decisiones clave)
- Modify: `docs/telegram/05-RFD-T3-MEMORIA-Y-TOKENS.md` (referencia cruzada)

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: el registro durable de la decisión.

- [ ] **Step 1: Escribe el ADR con la skill `adr-writer`**

Contenido mínimo: la decisión (tres capas con caducidad, contrato de `_PROJECT.md`, índice generado, ciclo de RFDs), las alternativas rechazadas **con su umbral de reapertura** (subcarpetas temáticas: ~25-30 ADRs o un segundo eje real), los trade-offs (convención sin enforcement duro) y el delta diseño↔implementación si lo hubo. `summary:` de una frase.

- [ ] **Step 2: Regenera el índice y comprueba que ahora son 6 líneas**

```bash
cd "$REPO" && py setup/scripts/adr-index.py "$ADRS" && grep -c "^| 2026-" "$ADRS/_INDEX.md"
```

Esperado: `6`.

- [ ] **Step 3: Mide el presupuesto de arranque**

```bash
py -c "import os; p=r'$P'; a=r'$ADRS'; t=os.path.getsize(p+'/_PROJECT.md')+os.path.getsize(a+'/_INDEX.md'); print(t, 'bytes')"
```

Esperado: **~8 000-9 000 bytes** (partíamos de ~36 000).

- [ ] **Step 4: Ensayo en seco de la cosecha del RFD 02**

```bash
cd "$REPO" && grep -rl -E "RFD 02|02-RFD" docs/ | wc -l
```

Esperado: `9`. No se cosecha nada aquí — es la comprobación de que el paso de redirección de la Task 5 tiene material real sobre el que operar.

- [ ] **Step 5: Referencia cruzada en el RFD 05**

Añadir a su cabecera: `> **Depende de:** RFD 09 §3.1 — el contrato de _PROJECT.md es precondición del extracto de ~2K chars de C1b.`

**Coordina antes de tocarlo**: ese documento puede tener otro agente trabajándolo.

- [ ] **Step 6: Regresión de los hooks (no se tocaron, pero comparten el vault)**

```bash
cd "$REPO"
py setup/hooks/tests/test-mark-code-dirty.py
py setup/hooks/tests/test-memory-flush.py
py setup/scripts/tests/test-adr-index.py
```

Esperado: 12/12, 11/11 y 17/17.

- [ ] **Step 7: Prueba humana — `project-resume` en sesión nueva**

Arranca una sesión nueva de Claude Code en el repo y corre `/project-resume`.

Criterio: **¿te dejó al día sin que echaras de menos nada?** Si tuviste que abrir tres ADRs a mano, el `summary` del índice es malo — mejóralo, no vuelvas a leerlos todos. Anota el resultado: es la evidencia de la auditoría posterior.

- [ ] **Step 8: Commits finales**

```bash
cd "$VAULT" && git add "10-Projects/claude-setup" && git commit -m "docs(vault): ADR de higiene del vault e indice regenerado"
cd "$REPO"  && git add docs/telegram/05-RFD-T3-MEMORIA-Y-TOKENS.md && git commit -m "docs(rfd): referencia cruzada al RFD 09 desde T3"
```

---

## Notas de ejecución

- **El RFD 09 y este plan NO se cosechan aquí.** Se cosechan cuando esto esté implementado *y auditado*, siguiendo la regla del propio RFD (§3.5). Cosecharlos ahora sería violar la norma que acabamos de escribir.
- Si una task falla a mitad, el rollback está en el sha del Step 1 de la Task 8 (vault) y en `git revert` del commit correspondiente (repo). Nunca dejes el vault a medias entre dos contratos.
- El `_PROJECT.md` cambiará bajo tus pies si hay otra sesión abierta en este proyecto: re-verifica el inventario (Task 8, Step 2) justo antes de reescribirlo.
