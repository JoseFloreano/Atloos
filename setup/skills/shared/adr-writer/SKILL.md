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
   crearía archivos en conflicto).

   Frontmatter obligatorio, las 4 secciones, las dos reglas que más se saltan
   (`summary` y el vocabulario de `status`) y **la excepción del ADR cosechado**,
   en [`references/formato-adr.md`](references/formato-adr.md).

4. Añade el wikilink `[[ADR-YYYYMMDD-tema]]` en `10-Projects/<proyecto>/_PROJECT.md`.

   ⚠ **Con OTROS agentes vivos, NO toques `_PROJECT.md`**: el wikilink queda
   pendiente en tu nota de sesión y `session-close` lo consolida
   (`references/formato-adr.md`).
5. **Regenera el índice** por ruta absoluta — la skill corre desde el cwd de
   cualquier proyecto y `sync-skills` instala el script en `~/.claude/scripts/`,
   misma ruta en toda máquina, con OneDrive o sin él:

   ```bash
   py "$HOME/.claude/scripts/adr-index.py" "<vault>/10-Projects/<proyecto>/ADRs"
   ```

   **En Cowork no existe esa ruta**: escribe el ADR y **deja anotado que el
   índice quedó pendiente**. No edites `_INDEX.md` a mano: se genera.
6. *(Solo con graphiti-memory)* guarda el episodio con el `group_id` del
   proyecto — nunca otro. Es asíncrono: no esperes confirmación.
7. Verifica: el archivo existe, el wikilink está en `_PROJECT.md`, el índice
   quedó regenerado, y el status de cualquier ADR reemplazado quedó en
   `superseded`.
