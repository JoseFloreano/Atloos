# Formato del ADR — frontmatter y secciones

Detalle del paso 3 de `adr-writer`. Lo consume `setup/scripts/adr-index.py`.

   Frontmatter obligatorio (el índice de `ADRs/_INDEX.md` se genera de aquí —
ver `setup/scripts/adr-index.py`):

```yaml
---
title: <título de la decisión>
date: YYYY-MM-DD
status: proposed
# status: proposed | accepted | rejected | superseded-by: ADR-YYYYMMDD-<tema>
summary: <UNA frase: qué se decidió. Es la celda que se lee en ADRs/_INDEX.md>
tags: [<tema>, <subsistema>]
project: <slug>
---
```

`summary` no es opcional: el script solo cae a `decision:` y luego a la
primera frase bajo `## Decisión` como último recurso para ADRs viejos que no
lo tienen — no es permiso para omitirlo en uno nuevo. Sin `summary`, quien
arranque una sesión ve el título del ADR en el índice y nada más. El
vocabulario de `status` es el de MADR, en inglés — nunca `estado:` en
español, porque el script (y `vault-drift-audit`) solo reconocen `status:`.

Secciones: **Contexto** (qué problema), **Decisión** (qué se eligió),
**Alternativas rechazadas** (y por qué), **Consecuencias** (trade-offs aceptados).
Máximo ~300 palabras — un ADR es un registro, no un ensayo.


## La excepción que rompe la regla de la fecha (paso 3)

La regla general es fechar con **hoy** y **NO usar numeración consecutiva**: dos
laptops offline generarían el mismo número y OneDrive crearía archivos en
conflicto.

⚠ **Excepción: un ADR COSECHADO se fecha con la fecha de la DECISIÓN**, no con
hoy. Fecharlo hoy rompe el orden del índice y **miente sobre cuándo se decidió**.
Para que se vea la diferencia entre cuándo se decidió y cuándo se registró, añade
dentro la línea:

```markdown
🌾 Cosechado el YYYY-MM-DD de `<origen>`
```

## Las dos reglas que más se saltan

- **`summary` no es opcional** — es la celda que se lee en el índice, así que un
  ADR sin ella entra en `_INDEX.md` como una fila muda.
- El vocabulario de `status` es **MADR en inglés**, nunca `estado:` en español:
  **el script solo reconoce `status:`**, así que un ADR en español no aparece
  con su estado y nadie lo nota hasta que hay que buscar los `superseded`.

## Y por qué el paso 4 no toca `_PROJECT.md` con otros agentes vivos

Es la misma doctrina que aplica `check-vault-updated.py`, **con la que este paso
se contradecía**. En campo, con **7 worktrees vivos**, cada agente improvisaba y
el conteo de ADRs se desincronizó. Un archivo, un escritor: el wikilink queda
**pendiente en tu nota de sesión** y `session-close` lo consolida.
