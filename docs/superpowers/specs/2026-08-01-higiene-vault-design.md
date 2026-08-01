# Spec — Higiene de contexto y ciclo de vida del vault

> **Diseño de origen:** `docs/arquitectura-memoria/09-RFD-HIGIENE-VAULT.md` (v2, validada)
> **Fecha:** 2026-08-01 · **Estado:** listo para plan de implementación
> **Qué NO hace este documento:** re-discutir el diseño. Las decisiones y su
> porqué viven en el RFD; aquí está el *cómo*, con contratos exactos y
> verificación. Si algo del spec contradice al RFD, gana el RFD.

---

## 1. Alcance

Implementar las seis piezas del §3 del RFD y migrar el proyecto `claude-setup`.

**Fuera de alcance** (explícito, para que nadie lo añada por su cuenta):
migrar `alphadogs` ni `tt1-revisor-chatbot`; hooks nuevos; reorganizar carpetas
por temas; renombrar notas de sesión existentes (§7.4); tocar los 4 hooks
anti-drift, `sync-hooks.ps1`, `sync-skills.ps1`, `memory-keeper` ni
`project-onboard`.

## 2. Entregas y orden

Son **dos repos distintos** con commits separados:

| # | Entrega | Repo | Depende de |
|---|---|---|---|
| **E1** | Script, tests y skills | `ClaudeSetup` | — |
| **E2** | Plantillas del vault | `obsidian-vault` | E1.1 (formato del índice) |
| **E3** | Migración de `claude-setup` en el vault | `obsidian-vault` | E1.1, E1.2 |
| **E4** | ADR de la decisión + cosecha del RFD | ambos | E1–E3 completas |

Orden obligatorio: **E1.1 → E1.2 → resto de E1 → E2 → E3 → E4**. El script y su
test van primero porque el formato del índice es el contrato del que dependen
`adr-writer`, `project-resume` y las plantillas.

---

## 3. E1.1 — `setup/scripts/adr-index.py`

Script nuevo. Sin dependencias externas (stdlib). Es el único componente con
código real de este spec.

### Interfaz

```
py setup/scripts/adr-index.py <ruta-carpeta-ADRs> [--check]
```

- Sin `--check`: escribe `<ruta>/_INDEX.md`. Exit 0 si todo fue bien.
- Con `--check`: **no escribe**; compara lo que generaría con lo que hay.
  Exit 0 si coinciden, **exit 2 si difieren** (lo usará `vault-drift-audit`),
  exit 1 ante error real.

### Lectura de cada `ADR-*.md`

Parser de frontmatter mínimo y propio (`---` … `---`, pares `clave: valor`, sin
YAML anidado). **No usar PyYAML**: no está garantizado en las laptops y el
frontmatter de los ADRs es plano.

| Campo | Origen | Fallback |
|---|---|---|
| `date` | clave `date:` | la fecha del nombre `ADR-YYYYMMDD-*` |
| `status` | clave `status:` | `unknown` + aviso a stderr |
| `title` | clave `title:` | primer encabezado `# ` del cuerpo |
| `summary` | clave `summary:` | clave `decision:`, y si no, la primera frase bajo `## Decisión` |

Ficheros ignorados: cualquiera que no case `ADR-*.md` — en particular el propio
`_INDEX.md`. Un ADR ilegible no aborta el índice: se emite su línea con lo que
se pudo extraer y un aviso por stderr.

### Salida exacta

```markdown
# ADRs — <nombre-del-proyecto>

> Índice generado por `setup/scripts/adr-index.py`. No editar a mano:
> los cambios se pierden en la siguiente generación.

| Fecha | Estado | ADR | Decisión |
|---|---|---|---|
| 2026-08-01 | accepted | [[ADR-20260801-puente-telegram]] | Daemon propio con long polling, sin túnel |
```

Reglas de formato, todas verificables:

1. **UTF-8 sin BOM** y saltos `\n` explícitos (`newline="\n"` al abrir). El BOM
   ya se perdió dos veces en este repo (bugs B1/B4) y aquí rompería la
   idempotencia entre laptops.
2. **Sin marca de tiempo ni contador** en el archivo. Cualquier dato variable
   haría fallar el criterio "regenera byte a byte idéntico".
3. Orden: **fecha descendente**; a igualdad de fecha, nombre de archivo
   ascendente (determinista).
4. El nombre del proyecto sale de la carpeta padre de `ADRs/`.
5. Los `|` del `summary` se escapan (`\|`) para no romper la tabla.
6. Termina en un único `\n`.

### Errores

Fail-fast, no fail-open: si la carpeta no existe o no hay ADRs, exit 1 con
mensaje claro. Es una herramienta invocada a mano o por una skill, no un hook —
aquí el silencio es peor que el error.

## 4. E1.2 — `setup/scripts/tests/test-adr-index.py`

Mismo patrón que `setup/hooks/tests/` (stdlib, carpeta temporal, una línea por
caso, exit 1 si algo falla). `sync-hooks.ps1` no copia esta carpeta y
`sync-skills.ps1` tampoco: son tests del repo.

Casos mínimos:

1. 3 ADRs bien formados → 3 líneas, orden fecha descendente.
2. **Idempotencia**: correr dos veces → SHA-256 idéntico.
3. ADR sin `date:` → toma la fecha del nombre del archivo.
4. ADR sin `summary:` → cae a `decision:`; sin ambas → primera frase de `## Decisión`.
5. ADR sin `status:` → `unknown` y aviso por stderr, sin abortar.
6. `summary` con `|` → escapado, tabla intacta.
7. `_INDEX.md` preexistente no se auto-incluye como ADR.
8. `--check` con índice al día → exit 0; tras tocar un ADR → **exit 2**.
9. Carpeta vacía o inexistente → exit 1 con mensaje.
10. **Bytes**: el archivo generado no empieza por BOM (`\xef\xbb\xbf`) y no
    contiene `\r\n`.

## 5. E1.3–E1.7 — Cambios en skills

Cada cambio es de texto en el `SKILL.md`; ninguno toca código.

### E1.3 `project-resume` (Claude Code y Cowork — **los dos**)

Paso 3 actual: *"lee los últimos ~3 ADRs de `ADRs/` … revisa `bugs/`"*. Pasa a:

- Leer **`ADRs/_INDEX.md`**. Si no existe, degradar al comportamiento actual y
  avisar de que falta generar el índice (proyectos aún sin migrar).
- Abrir un ADR completo **solo si** su fecha ≥ la de la nota más reciente de
  `sessions/`; en el resto de casos, decide el `summary` del índice.
- `bugs/`: leer **solo los `status: open`**. El vocabulario cerrado es
  `open | fixed | invalid | wontfix`.
- El presupuesto de arranque es explícito en la skill: *"si lo que vas a leer
  al arrancar pasa de ~10 KB, algo está mal — dilo en vez de leerlo"*.

La versión de Cowork mantiene su lenguaje de *stage-ar* carpetas.

### E1.4 `session-close`

- Paso nuevo antes de cerrar: lo hecho en la sesión va a
  `sessions/YYYY-MM-DD-<tarea>.md`; de `_PROJECT.md` **solo** se tocan Estado
  actual, Pendientes y Próximo paso.
- Contar las líneas de `_PROJECT.md` al cerrar. Si pasa de **120**, avisar y
  proponer qué rotar; **nunca bloquear** (§4.4 del RFD).
- Prohibición explícita: *"no crear secciones `## Hecho` en `_PROJECT.md`"*.

### E1.5 `adr-writer`

- Frontmatter del §3.4 del RFD (`title`, `date`, `status`, `summary`, `tags`),
  con `summary` **obligatorio** — es la celda del índice.
- Paso nuevo tras escribir el ADR: ejecutar `adr-index.py` sobre la carpeta.
- Se mantiene el wikilink en "Decisiones clave" de `_PROJECT.md`.

### E1.6 `design-doc-harvest`

Ampliar a los RFDs de `docs/**`, con la tabla de estados del §3.5 del RFD y
**dos pasos nuevos, en este orden**:

1. **Redirigir referencias antes de borrar**: `grep -rl` del nombre y del número
   del RFD en `docs/`, y actualizar cada cita al ADR resultante. Solo entonces
   `git rm`. (Hoy el RFD 02 lo citan 9 documentos.)
2. **Si la decisión ya tiene ADR, enriquecerlo**; no crear un segundo ADR sobre
   el mismo asunto.

Y afinar el disparador: *"implementado y auditado"* significa **condiciones de
auditoría cerradas**, no "hubo auditoría".

### E1.7 `vault-drift-audit`

Tres deberes nuevos: (a) `adr-index.py --check` por proyecto; (b) `_PROJECT.md`
por encima de 120 líneas, reincidencia incluida; (c) notas de `sessions/` ya
cosechadas con más de ~30 días → proponer `_archive/`.

**Restricción**: la skill está en **452 palabras** y el tope sano es 500. Mover
el detalle operativo (comandos, umbrales) a `references/checks.md` y dejar en el
cuerpo las tres líneas de qué comprobar.

## 6. E2 — Plantillas del vault

Repo `obsidian-vault`, carpeta `templates/`.

### `project-note.md`

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
<!-- solo status: open; los cerrados viven en bugs/ -->

## Convenciones que difieren del default

## Pendientes

## Próximo paso
```

Con una nota al pie del template, visible para quien lo use:

> Tope: 120 líneas (duro 150). **Prohibidas las secciones `## Hecho`**: lo que
> pasó va a `sessions/YYYY-MM-DD-<tarea>.md`. `session-close` lo verifica.

### `adr.md`

Frontmatter del §3.4, con `summary` obligatorio y el vocabulario de `status`
en un comentario. El cuerpo (Contexto / Decisión / Alternativas / Consecuencias)
no cambia.

## 7. E3 — Migración de `claude-setup`

### 7.1 Inventario (verificado 2026-08-01)

`_PROJECT.md` tiene **6 secciones `## Hecho`** en las líneas 62, 86, 102, 161,
166 y 172. **Re-verificar el inventario antes de tocar nada**: el archivo se ha
movido varias veces durante el diseño.

### 7.2 Mapa bloque → destino

| Sección | Destino | Tipo |
|---|---|---|
| Telegram T0 (08-01) | `sessions/2026-08-01-telegram-t0.md` | **nueva** |
| Ahorro de tokens R1/R5/R7 (08-01) | `sessions/20260801-ahorro-tokens-r1-r5-r7.md` | fusionar |
| Registro de secretos (08-01) | `sessions/20260801-registro-secretos-y-esqueletos.md` | fusionar |
| Cowork (07-26) | `sessions/2026-07-26-cowork-adrs-y-bugs.md` | **nueva** |
| Onboarding y sync-hooks (07-24) | `sessions/2026-07-24-onboarding-y-sync-hooks.md` | **nueva** |
| Fix `mark-code-dirty` (08-01) | 1 línea en Estado actual + `[[bug-mark-code-dirty-falso-positivo]]` | resumir |

Las notas nuevas llevan el frontmatter de `session-import.md` (`type: session`,
`project: claude-setup`) y **la fecha real del trabajo**, no la de la migración.

### 7.3 Reescritura de `_PROJECT.md`

Aplicar el esqueleto de E2 conservando el contenido vivo: Qué es, Estado actual
(reescrito en presente), Decisiones clave, Bugs abiertos (hoy: **ninguno** — los
3 están cerrados), Convenciones, Pendientes, Próximo paso. Objetivo: **≤120
líneas** desde las 186 actuales.

Los wikilinks existentes a notas de sesión (`[[20260801-ahorro-tokens-r1-r5-r7]]`,
`[[20260801-registro-secretos-y-esqueletos]]`, `[[2026-08-01-telegram-t2]]`)
**se conservan**.

### 7.4 Nombres de las notas nuevas — decisión

`sessions/` mezcla hoy dos estilos: `20260801-*` y `2026-08-01-*`. Las notas
**nuevas** usan `YYYY-MM-DD-`, que es lo que dicen `memory-instructions.md` y los
mensajes de los hooks. **Las existentes no se renombran**: hay wikilinks
apuntando a ellas y el beneficio no paga el riesgo de romperlos.

### 7.5 Frontmatter de los ADRs e índice

Unificar los 5 (los dos con `estado:` en español pasan a `status:`, añadiendo
`summary` a todos) y generar `_INDEX.md` con el script. El ADR del servidor
Debian se queda en `proposed`.

## 8. E4 — Cierre

1. ADR de esta decisión con `adr-writer` (incluye el umbral de reapertura de las
   subcarpetas: ~25-30 ADRs).
2. Referencia cruzada en `docs/telegram/05-RFD-T3-MEMORIA-Y-TOKENS.md` al §3.1
   del RFD 09. **Coordinar antes**: ese documento puede tener otro agente
   trabajándolo.
3. El RFD 09 **no se cosecha aquí**: se cosecha cuando esto esté implementado y
   auditado, siguiendo su propia regla.

## 9. Verificación

Un comando por criterio de aceptación del §7 del RFD. Rutas usadas:

```bash
VAULT="$HOME/OneDrive/DevSetup/ObsidianVault"
P="$VAULT/10-Projects/claude-setup"
ADRS="$P/ADRs"
```

```bash
# 1. Tope y ausencia de historial
wc -l < "$VAULT/10-Projects/claude-setup/_PROJECT.md"        # <= 120
grep -c "^## Hecho" "$VAULT/10-Projects/claude-setup/_PROJECT.md"   # 0

# 2. Nada perdido: una frase característica de cada bloque migrado
grep -rl "Curator de Hermes"  "$VAULT/10-Projects/claude-setup/sessions/"
grep -rl "floreanoclaudebot"  "$VAULT/10-Projects/claude-setup/sessions/"
grep -rl "separate-git-dir"   "$VAULT/10-Projects/claude-setup/sessions/"

# 3. Idempotencia del índice (hash, dos corridas)
py setup/scripts/adr-index.py "$ADRS" && sha256sum "$ADRS/_INDEX.md"
py setup/scripts/adr-index.py "$ADRS" && sha256sum "$ADRS/_INDEX.md"   # igual
py -c "d=open(r'$ADRS/_INDEX.md','rb').read(); assert not d.startswith(b'\xef\xbb\xbf'); assert b'\r\n' not in d; print('encoding OK')"

# 4. Frontmatter uniforme
grep -c "^status:" "$ADRS"/ADR-*.md | grep -v ":1$"   # sin salida = todos

# 5. Presupuesto de arranque
py -c "import glob,os; print(sum(os.path.getsize(f) for f in ['$P/_PROJECT.md','$ADRS/_INDEX.md']))"   # ~8-9 KB

# 6. Ensayo en seco de la redirección de referencias
grep -rl -E "RFD 02|02-RFD" docs/ | wc -l    # 9 -> lista que tendría que actualizarse

# 7. Tests
py setup/scripts/tests/test-adr-index.py
py setup/hooks/tests/test-mark-code-dirty.py     # regresión: no se tocaron los hooks
py setup/hooks/tests/test-memory-flush.py
```

Y una prueba de extremo a extremo que no es un comando: **`project-resume` en una
sesión nueva** sobre el proyecto migrado. Criterio humano: ¿el arranque te dejó
al día sin que echaras de menos nada? Si hubo que abrir tres ADRs a mano, el
`summary` del índice no es suficientemente bueno y hay que mejorarlo — no volver
a leerlos todos.

## 10. Rollback

- **E1** (repo): revertir el commit. Sin estado que deshacer.
- **E2/E3** (vault): el vault tiene git propio con remoto en GitHub y auto-commit
  del plugin. **Commitear el vault ANTES de empezar E3** para tener un punto de
  retorno limpio; si la migración sale mal, `git checkout` de la carpeta del
  proyecto.
- El riesgo real no es técnico sino de pérdida de contenido: por eso el criterio
  §9.2 se comprueba **antes** de reescribir `_PROJECT.md`, no después.

## 11. Descubrimientos durante el spec

- **Dos estilos de nombre** en `sessions/` (§7.4). Resuelto: los nuevos con
  `YYYY-MM-DD-`, los viejos se quedan.
- **T2 no tiene sección `## Hecho`** pese a estar implementado: su estado vive en
  Pendientes con wikilink a la nota. Es justo el comportamiento que el contrato
  quiere, y confirma que la rotación es viable.
- **`bugs/` queda vacío de abiertos** tras el fix del 08-01, así que el ahorro de
  10 KB del §3.3(c) es inmediato y no hipotético.
