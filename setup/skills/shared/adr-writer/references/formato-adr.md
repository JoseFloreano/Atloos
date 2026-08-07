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

