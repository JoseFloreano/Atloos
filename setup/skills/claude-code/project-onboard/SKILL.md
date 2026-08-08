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
7. *(Opcional — si el repo usará Graphify)* instala el hook git post-commit que
   mantiene `codebase-map-snapshot.md` fresco en el vault (el `codebase-map.md`
   curado NO lo toca nadie automáticamente — RFD 10 C2). ⚠ Antes de correr
   `graphify claude install`, lee los 3 avisos de `setup/hooks/README.md`:
   registra `PreToolUse` no documentados (peligroso con agentes en paralelo),
   es una primera pasada y no una respuesta, y su hook cuenta en el
   presupuesto de máquina:
   `cp setup/hooks/git-post-commit-graph-report.sh .git/hooks/post-commit` +
   `chmod +x` (ver `hooks/README.md`). Sin Graphify, omite sin avisar.

   ⚠ **Tras instalar, SUSTITUYE la línea que `graphify claude install` escribe
   en el `CLAUDE.md` del proyecto** —*"For codebase questions, first run
   `graphify query`"*— por el disparador. Esa línea es la que el agente lee de
   verdad; dejarla intacta deja la mala instrucción en pie (F14, incumplida 2
   jornadas de 2). Déjala así:

   ```markdown
   Antes de tu primer `grep` de exploración en una sesión, corre
   `graphify query`. Su salida es la LISTA DE CANDIDATOS, no la respuesta:
   confírmala con `Read` y da por hecho que le faltan sitios (en campo: 5 de 9
   sitios, con los 2 decisivos fuera).
   ```
8. **Verifica**: existe `10-Projects/<nombre>/_PROJECT.md`; el `CLAUDE.md` del
   proyecto contiene el snippet y NO queda ningún `<project-name>` sin reemplazar.

## Referencias

- `references/memory-snippet.md` — bloque a insertar en el CLAUDE.md del proyecto
  (~230 tokens; reemplaza `<project-name>`).
