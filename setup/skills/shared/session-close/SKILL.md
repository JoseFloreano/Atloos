---
name: session-close
description: >
  Ritual de cierre de sesión de trabajo: actualiza el estado y pendientes del
  proyecto en el vault, añade la entrada del daily note y ofrece cosechar
  diseño/hallazgos sueltos. Use when the user says "cerramos", "cierra la
  sesión", "terminamos por hoy", "listo por hoy", "wrap up", "end of session",
  or hands off work for the day. Es el complemento humano del hook anti-drift
  (que solo exige pendientes al detectar código sin registrar).
---

# Session Close

El cierre completo que el hook no exige (el hook solo cubre pendientes, una vez).
Deja el vault listo para que `project-resume` arranque en frío mañana o en la
otra laptop.

## Requisitos

- Vault en `DevSetup/ObsidianVault/` (OneDrive o home — la raíz que exista).
  En Cowork: carpeta del vault conectada; commitea de vuelta lo que edites.

## Pasos

1. **Rota el historial antes de tocar nada.** Lo hecho en esta sesión va a
   `10-Projects/<proyecto>/sessions/YYYY-MM-DD-<tarea>.md` (frontmatter de
   `templates/session-import.md`). De `_PROJECT.md` se tocan **solo** tres
   secciones: Estado actual (en presente), Pendientes y Próximo paso.

   **Prohibidas las secciones `## Hecho`**: ese archivo describe cómo está el
   proyecto hoy, no cómo llegó hasta aquí.

2. **`_PROJECT.md` del proyecto activo** — **reléelo ENTERO justo antes de
   editar**: pudo cambiar desde que arrancaste (el auditor y otras sesiones
   también escriben en él; ya pasó). Actualiza tres secciones, corto:
   - *Estado actual*: 2-4 líneas de dónde quedó el proyecto HOY.
   - *Pendientes*: lo que quedó abierto (checkboxes), borrando lo ya cerrado.
   - *Próximo paso*: la primera acción concreta de la siguiente sesión — el
     regalo más valioso para el tú de mañana.
   Actualiza `updated:` del frontmatter.
3. **Daily note** (`daily/YYYY-MM-DD.md`): añade un bullet por proyecto tocado
   hoy con lo esencial. Créala si no existe.
4. **Cosechas colgando** — revisa y ofrece (no fuerces):
   - ¿Plan de Superpowers completado sin cosechar? → `design-doc-harvest`.
   - ¿Decisión tomada hoy sin ADR? → `adr-writer`.
   - ¿Bug no-obvio resuelto sin registrar? → `memory-keeper`.
5. **Grafos** — complementan al vault, no lo reemplazan:
   - *Graphiti*: los episodios ya los escriben las cosechas del paso 4. Es
     **asíncrono** (~25s): no esperes confirmación. Sin Graphiti, omite en
     silencio: el vault es la fuente primaria.
   - *Graphify*: si el repo lo usa, verifica **SIEMPRE** (no solo con cambios
     estructurales) hook + edad del snapshot, y reporta el desfase en días →
     [`references/grafos-y-estado-del-repo.md`](references/grafos-y-estado-del-repo.md).
6. *(Solo Claude Code)* Si existe `.claude/vault-dirty.json` en el repo,
   bórralo — el cierre manual deja el flag del hook en cero.
7. **Tamaño, backlog y estado del repo.** `wc -l` (blando 120, duro 150) y
   cuenta los checkboxes de primer nivel: **>12** → propón crear
   `pendientes.md`; **≤8** entre activos y backlog → propón disolverlo; si ya
   existe, **recalcula su N**. En el mismo gesto actualiza (o añade si falta)
   `Estado del repo: <sha corto> · <fecha>` con el `origin/main` real.
   Mecánica: [`backlog`](references/backlog-pendientes.md) ·
   [`estado del repo`](references/grafos-y-estado-del-repo.md).
   **Avisa, no bloquees.**
8. **Verifica y despide**: **relee las secciones que editaste** (el reporte
   de una edición no es la edición: un old_string que casó a medias deja
   fragmentos rotos), confirma qué se actualizó y responde con el "próximo
   paso" anotado — así la sesión termina con el arranque de la siguiente ya
   escrito.

## Qué NO hacer

- No reescribas `_PROJECT.md` completo ni lo infles: es un resumen vivo, no un log.
- No dupliques en el daily lo que ya quedó en ADRs/bugs — un bullet con wikilink basta.
