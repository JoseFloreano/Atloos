---
name: design-doc-harvest
description: >
  Cosecha los documentos de diseño de Superpowers (specs de brainstorming y
  planes de writing-plans) cuando la implementación termina: destila lo durable
  a un ADR en el vault y BORRA los docs de trabajo del repo (git conserva la
  historia). Use when the user says "ya quedó implementado", "terminé el plan",
  "cosecha el diseño", "limpia los docs de superpowers", "harvest", or al cerrar
  un execute-plan completado. NO usar con planes a medias — solo se cosecha lo
  terminado.
---

# Design Doc Harvest

El eslabón que le falta a Superpowers: specs y planes son andamiaje temporal;
lo durable vive en el vault. Esta skill cierra el pipeline
`brainstorming → council → writing-plans → execute → harvest → adr-writer`.

## Requisitos

- Repo del proyecto accesible con git (Claude Code; en Cowork solo si la carpeta
  del repo está conectada — si no, genera el ADR y deja al usuario el borrado).
- Skill `adr-writer` disponible (hace el registro en vault + Graphiti).

## Pasos

1. **Localiza los docs terminados**: `docs/superpowers/{specs,plans}/*.md` y los
   **RFDs** de `docs/**/*RFD*.md`. **Cuándo se cosecha y cuándo NO**, y cómo se
   redirigen las referencias:
   [`references/cuando-y-como-cosechar.md`](references/cuando-y-como-cosechar.md).
   Regla dura: *auditado* = **condiciones de auditoría CERRADAS**, no "hubo
   auditoría". Con varios features mezclados, confirma con el usuario cuáles.
2. **Verifica que está completado de verdad**: checkboxes marcados o el usuario
   lo confirma. Un plan a medias NO se cosecha.
3. **Destila lo durable**: la decisión y su porqué, las **alternativas
   rechazadas** (los "por qué NO" valen igual), los trade-offs aceptados, y los
   **deltas** entre diseño e implementación — ahí suele estar el aprendizaje.
   NO copies el spec completo: código, comandos y checkboxes son memory rot.
4. **Registra con `adr-writer`** (un ADR por decisión mayor, no un mega-ADR),
   citando el commit/PR de la implementación. **Si la decisión ya tiene ADR, la
   cosecha lo ENRIQUECE — no crea otro** (por qué, en la reference). Si
   cosechaste una nota de `sessions/`, márcala `harvested: true`.
5. **Redirige las referencias entrantes antes de borrar.** "Git conserva la
   historia" es cierto para el contenido y **falso para los enlaces**. Grepea
   en TODO el repo **y en el vault**, no solo en `docs/`. Solo cuando el grep
   deje de devolver huérfanas se borra. Comandos y precedentes en la
   reference.

5b. **Si el RFD vive en el VAULT y no en el repo, el paso 6 NO aplica**: se
   archiva con un cartel al ADR, nunca `git rm`. Detalle en la reference.

6. **Borra los docs cosechados** con `git rm` — SOLO con el ADR ya escrito y la
   **lista exacta aprobada por el usuario**. Es seguro: git conserva la historia
   y el ADR apunta al sha.
7. **Verifica**: el ADR existe con su wikilink en `_PROJECT.md`, no quedan
   restos del feature, y el grep de referencias da cero.

## Qué NO hacer

- No cosechar planes incompletos ni specs de features abandonados (esos se
  borran sin ADR, con confirmación — no todo diseño merece memoria).
- No copiar documentos completos al vault (el vault es conocimiento durable,
  no archivero de andamiaje).
- No borrar nada sin el ADR escrito primero y la lista aprobada.
