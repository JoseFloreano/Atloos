---
name: project-onboard
description: >
  Da de alta un proyecto NUEVO en el sistema de memoria: crea su carpeta en el
  vault de Obsidian y graba las reglas de aislamiento en el CLAUDE.md del
  proyecto. Use when el usuario dice "engancha este proyecto", "da de alta este
  proyecto en la memoria", "configura la memoria de este proyecto", "onboard
  this project", "nuevo proyecto en el vault", o al empezar en un repo que aún
  no tiene carpeta en 10-Projects/. NO usar si el proyecto ya existe en el vault
  (para eso está project-resume).
---

# Project Onboard

Engancha un proyecto nuevo a la memoria durable. Tras esto, las skills
`adr-writer` y `memory-keeper` funcionan solas para ese proyecto, con el
aislamiento activo.

## Requisitos

- Vault en `OneDrive/DevSetup/ObsidianVault/` (Windows:
  `%USERPROFILE%\OneDrive\DevSetup\ObsidianVault`). Si no existe, PARA y avisa:
  falta montar el vault.
- MCP `graphiti-memory` — **opcional**: si no está, omite el paso 6 sin avisar error.

## Pasos

1. Determina el **nombre del proyecto** en kebab-case (derívalo del nombre de la
   carpeta del repo; confírmalo con el usuario si es ambiguo). Ese nombre = carpeta
   del vault = `group_id` de Graphiti. Debe ser único.
2. **Search-before-create**: comprueba si ya existe `10-Projects/<nombre>/` en el
   vault. Si existe, PARA — el proyecto ya está enganchado; sugiere `project-resume`.
3. Crea en el vault `10-Projects/<nombre>/` con subcarpetas `ADRs/`, `bugs/`, `sessions/`.
4. Crea `10-Projects/<nombre>/_PROJECT.md` copiando `templates/project-note.md`
   del vault; rellena `title`, `project`, `created`/`updated` (hoy) y el stack.
   Mantenlo corto.
5. Añade las reglas de memoria al `CLAUDE.md` del proyecto (créalo si no existe):
   pega el contenido de `references/memory-snippet.md` reemplazando **todas** las
   apariciones de `<project-name>` por el nombre real. Si ya hay una sección
   "Memory Rules", no la dupliques: actualízala.
6. *(Solo si graphiti-memory está disponible)* copia la plantilla `.graphiti.json`
   a la raíz del proyecto ajustando `project_id`/`group_id` al nombre. Si Graphiti
   no está montado, omite este paso.
7. *(Opcional — si el repo usará Graphify)* instala el `.git/hooks/post-commit` que
   mantiene fresco el `codebase-map-snapshot.md` del vault, y **borra la línea
   vieja** que escribe `graphify claude install`: el disparador bueno ya viaja
   en el snippet (paso 5). Antes de instalar nada, lee
   `references/graphify-al-enganchar.md`. Sin Graphify, omite sin avisar.
8. **Da el proyecto de alta en el puente** — no editando `projects.json` a mano,
   sino con el validador, que es el único que comprueba las cinco casillas:

   ```bash
   setup/scripts/py setup/telegram-bridge/altas.py <ruta absoluta> [comando de test]
   ```

   (desde el móvil, lo mismo: `/alta <ruta> [test]`, que además recarga en
   caliente). Devuelve un checklist: ruta · git · nombre · carpeta en el vault ·
   comando de test resoluble **en el PATH del daemon**. Salida 0 = dado de alta.

   **Enganchar sin dar de alta no engancha nada comprobable**: de ahí saca
   `test-claude-md-drift.py` los `CLAUDE.md` vivos, así que un proyecto ausente
   **nunca se audita**. Pasó: el proyecto de los cuatro reportes de campo no
   estaba, y nada lo dijo.
   ⚠ El registro es **por máquina** (gitignorado, rutas absolutas): en la otra
   laptop se repite el alta allí, y **no se copia el fichero** — una ruta de
   Windows en Linux la descarta el daemon con un aviso que va al journal, no al
   chat.
9. **Verifica**: existe `10-Projects/<nombre>/_PROJECT.md`; el `CLAUDE.md` del
   proyecto contiene el snippet y NO queda ningún `<project-name>` sin
   reemplazar. Y `setup/scripts/py setup/scripts/tests/test-claude-md-drift.py <CLAUDE.md>` [repo]
   comprueba que el snippet llegó entero y caza la línea vieja de Graphify.

## Referencias

- `references/memory-snippet.md` — bloque a insertar en el CLAUDE.md del proyecto
  (~300 tokens; reemplaza `<project-name>`).
- `references/graphify-al-enganchar.md` — qué instalar, qué borrar y los cuatro
  avisos, si el repo usará Graphify (paso 7).
