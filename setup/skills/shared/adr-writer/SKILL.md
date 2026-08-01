---
name: adr-writer
description: >
  Documenta una decisión de arquitectura como ADR en el vault de Obsidian del
  proyecto activo (y en Graphiti si está disponible). Use when the user decides
  between technologies or approaches, says "decidimos usar", "vamos con", "por qué
  elegimos", "ADR", "deja registrado que", or rejects an alternative after
  discussion. Also use al final de una sesión donde se tomó una decisión de diseño
  que aún no quedó documentada.
---

# ADR Writer

Registra decisiones de arquitectura de forma que sobrevivan entre sesiones y
productos (Claude Code y Cowork comparten el vault).

## Cuándo usar

- Se eligió una tecnología/enfoque sobre alternativas (aunque el usuario no diga "ADR").
- Se rechazó explícitamente una opción ("no usamos X porque...") — los "por qué NO" valen tanto como los "por qué sí".

## Requisitos

- Vault de Obsidian en `DevSetup/ObsidianVault/`, bajo OneDrive (multi-laptop)
  o bajo el home / `%USERPROFILE%` (single-laptop) — usa la raíz que exista.
  Si no es accesible, ofrece guardar el ADR como `docs/adr/` dentro del repo.
- MCP `graphiti-memory` — **opcional**: si no está disponible (típico en Cowork),
  omite el paso 6 sin avisar error; el vault es la fuente primaria.

## Pasos

1. Identifica el **proyecto activo** (regla de aislamiento: nunca escribas en la
   carpeta de otro proyecto). Ruta destino: `10-Projects/<proyecto>/ADRs/`.
2. Busca ADRs existentes sobre el mismo tema en esa carpeta. Si existe uno
   (similitud > 80%), actualízalo y marca el anterior como `superseded` — no dupliques.
3. Crea `ADR-YYYYMMDD-tema-kebab.md` (fecha de hoy — NO uses numeración
   consecutiva: dos laptops offline generarían el mismo número y OneDrive
   crearía archivos en conflicto):

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

4. Añade el wikilink `[[ADR-YYYYMMDD-tema]]` en `10-Projects/<proyecto>/_PROJECT.md`.
5. **Regenera el índice**. Esta skill se instala globalmente y corre desde el
   cwd de cualquier proyecto, así que el script hay que invocarlo por ruta
   absoluta — vive en el repo ClaudeSetup, y esa ruta es estable entre laptops
   porque el repo viaja dentro de OneDrive:

   ```bash
   py "$HOME/OneDrive/Documentos/Mis_Documentos/Proyectos/Coding/Python/Otros/ClaudeSetup/setup/scripts/adr-index.py" "<vault>/10-Projects/<proyecto>/ADRs"
   ```

   (PowerShell: `py "$env:USERPROFILE\OneDrive\Documentos\Mis_Documentos\Proyectos\Coding\Python\Otros\ClaudeSetup\setup\scripts\adr-index.py" "<vault>\10-Projects\<proyecto>\ADRs"`)

   Verifica que la línea del ADR nuevo aparece en `ADRs/_INDEX.md`. Si el script
   avisa de un `status:` ausente en otro ADR, arréglalo de paso: un ADR sin
   estado es invisible para la auditoría del vault.
6. *(Solo si graphiti-memory está disponible)* guarda el episodio con
   `group_id: "<proyecto>"` — nunca otro group_id — usando el formato de
   `memory-instructions.md`. No esperes confirmación (es asíncrono).
7. Verifica: el archivo existe, el wikilink está en `_PROJECT.md`, el índice
   quedó regenerado, y el status de cualquier ADR reemplazado quedó en
   `superseded`.
