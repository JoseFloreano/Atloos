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

   **Prohibido crear secciones `## Hecho` en `_PROJECT.md`.** Ese archivo
   describe cómo está el proyecto hoy, no cómo llegó hasta aquí.

2. **`_PROJECT.md` del proyecto activo** — actualiza tres secciones, corto:
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
5. **Grafos (si están montados)** — complementan al vault, no lo reemplazan:
   - *Graphiti* (memoria temporal): las cosechas del paso 3 (`adr-writer`/
     `memory-keeper`) ya escriben los episodios al grafo. Es **asíncrono**
     (~25s): no esperes confirmación ni lo busques al instante. Si Graphiti no
     está montado, omite en silencio (el vault es la fuente primaria).
   - *Graphify* (estructura del código, local/Claude Code): el
     `codebase-map.md` se regenera SOLO con el hook git post-commit
     (`setup/hooks/git-post-commit-graph-report.sh`) — aquí NO se regenera
     nada. Única verificación: si hoy hubo cambios estructurales y el repo
     no tiene el hook (`.git/hooks/post-commit`), ofrece instalarlo
     (cp + chmod); un `graphify .` manual vale solo como parche de esta vez.
     En Cowork omite (es toolchain local).
6. *(Solo Claude Code)* Si existe `.claude/vault-dirty.json` en el repo,
   bórralo — el cierre manual deja el flag del hook en cero.
7. **Verifica y despide**: confirma qué se actualizó y responde con el
   "próximo paso" anotado — así la sesión termina con el arranque de la
   siguiente ya escrito.
8. **Comprueba el tamaño de `_PROJECT.md`** (`wc -l`). Si pasa de **120
   líneas**, di qué sección conviene rotar a `sessions/` y ofrécelo — el tope
   duro es 150. **Avisa, no bloquees**: esto es una convención, no un hook.

## Qué NO hacer

- No reescribas `_PROJECT.md` completo ni lo infles: es un resumen vivo, no un log.
- No dupliques en el daily lo que ya quedó en ADRs/bugs — un bullet con wikilink basta.
