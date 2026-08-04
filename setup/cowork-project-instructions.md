<!-- Gemelo de memory-instructions.md para COWORK.
     Pegar como "Instrucciones de proyecto" del proyecto de Cowork correspondiente
     (un proyecto de Cowork por proyecto de código — nunca uno genérico para todo).
     Reemplazar <project-name> antes de pegar. -->

## Project Identity — read this FIRST

- ACTIVE PROJECT: `<project-name>`
- This Cowork project belongs to `<project-name>` ONLY. All memory, vault access
  and deliverables in every session here are scoped to this project.

## Memory Isolation Rules — NON-NEGOTIABLE

Cross-project contamination causes hallucinations. Never mix knowledge between
projects.

1. In the Obsidian vault (connected folder `ObsidianVault/`), only read/write:
   - `10-Projects/<project-name>/` (this project: _PROJECT.md, ADRs/, bugs/)
   - `brain/` and `daily/` (shared knowledge, read mostly)
   Folders of OTHER projects under `10-Projects/` are OFF-LIMITS unless the
   user explicitly asks to consult them.
2. If the `graphiti-memory` MCP is available (requires the desktop app open):
   - Every search MUST use `group_ids: ["<project-name>", "dev-global"]`.
   - Every `add_episode` MUST use `group_id: "<project-name>"`.
   - If it is NOT available, skip Graphiti silently — the vault is the primary
     record; important decisions go to `10-Projects/<project-name>/ADRs/`.
3. If memory from another project seems relevant, say so and ask — never
   silently import context from another project.
4. If a retrieved fact conflicts with what the user says NOW, trust the present
   and update the vault note.

## Session workflow

- **Start**: read `10-Projects/<project-name>/_PROJECT.md` (stage it from the
  connected vault folder) before substantive work.
- **During**: architecture decisions → `adr-writer` skill; non-obvious bug root
  causes → `10-Projects/<project-name>/bugs/`.
- **End**: if project state changed, update `_PROJECT.md` and commit it back to
  the vault folder (files not committed back do NOT reach the user's disk).

## Skills

- The `dev-skills` plugin (shared + cowork skills, synced from
  `setup/skills/` del repo ClaudeSetup) should be installed. Use its skills
  automatically whenever a task matches their descriptions.
- Saving durable knowledge → `memory-keeper` skill; architecture decisions
  → `adr-writer` skill.
- The plugin's version is a date (YYYY.MM.DD). If it is more than ~30 days
  old, tell the user it may be stale and suggest re-uploading
  `setup/_build/dev-skills.zip` (Customize → Plugins).

## What Cowork should NOT attempt here

- Running the user's local toolchain (flutter, cmake, docker on their machine) —
  that is Claude Code territory; offer to prepare instructions/scripts instead.
- Editing code repos live on the user's disk beyond stage → edit → commit of
  specific files the user asked for.
