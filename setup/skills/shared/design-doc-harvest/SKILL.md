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

1. **Localiza los docs del trabajo terminado**: `docs/superpowers/specs/*.md`,
   `docs/superpowers/plans/*.md` y los **RFDs** de `docs/**/*RFD*.md` (o la ruta
   que fije el CLAUDE.md).

   Un RFD se cosecha según su estado:

   | Estado del RFD | Qué se hace |
   |---|---|
   | Propuesta abierta / en discusión | se queda |
   | Aprobado pero **no** implementado | se queda |
   | Implementado, con la **auditoría abierta o con condiciones pendientes** | se queda — todavía NO se cosecha |
   | Implementado **y con las condiciones de auditoría cerradas** | cosecha → ADR → **redirigir referencias (paso 5)** → `git rm` |
   | Abandonado | **redirigir referencias (paso 5)** → borrar sin ADR, con confirmación |

   "Auditado" significa **condiciones de auditoría cerradas**, no "hubo
   auditoría". Un RFD con la auditoría aprobada *con condiciones* pendientes NO
   se cosecha.

   Si hay varios features mezclados, lista y confirma con el usuario CUÁLES
   corresponden a lo ya implementado.
2. **Verifica que está completado de verdad**: los checkboxes del plan están
   marcados o el usuario lo confirma. Un plan a medias NO se cosecha — se queda.
3. **Destila lo durable** (esto es lo que sobrevive; el resto es andamiaje):
   - La decisión de diseño final y su porqué
   - Alternativas rechazadas y por qué (los "por qué NO" valen igual)
   - Trade-offs aceptados conscientemente
   - **Deltas**: qué cambió entre el diseño original y lo realmente implementado
     — ahí suele estar el aprendizaje más valioso
   NO copies el spec/plan completo al vault: ejemplos de código, comandos y
   checkboxes son basura futura (memory rot).
4. **Registra con `adr-writer`** (un ADR por decisión mayor, no un mega-ADR).
   En cada ADR incluye: referencia al commit/PR de la implementación, y la nota
   "docs de trabajo cosechados y borrados — historia completa en git: <sha>".

   **Si la decisión ya tiene ADR, la cosecha lo enriquece — no crea otro.**
   Dos ADRs sobre el mismo asunto reproducen en la capa durable la divergencia
   que la cosecha venía a eliminar.

   Si el contenido cosechado incluye una nota de `sessions/` (frontmatter de
   `templates/session-import.md`), marca `harvested: true` en esa nota al
   terminar: es lo que la hace elegible para archivar más adelante
   (`vault-drift-audit` la propone para `_archive/` solo cuando ese campo está
   en `true`).
5. **Redirige las referencias entrantes.** "Git conserva la historia" es cierto
   para el contenido y falso para los enlaces:

   ```bash
   # sustituye NN por el número real: para el RFD 02 -> "RFD 02|02-RFD"
   # OJO al alcance: TODO el repo, no solo docs/ — y también el vault
   grep -rn -E "RFD 02|02-RFD" . --exclude-dir=.git --exclude-dir=.superpowers
   grep -rn -E "RFD 02|02-RFD" <vault>/10-Projects/<proyecto>/
   ```

   Copiado literal con `NN` el comando no matchea nada — no confundas "cero
   resultados porque no sustituiste NN" con "no hay referencias entrantes": lo
   segundo lleva a borrar y reproducir el mismo huérfano que este paso existe
   para evitar.

   **Buscar solo en `docs/` no basta**, y es un error ya cometido: al cosechar
   el RFD 09 quedaron citas colgando en `_archive/` (dos prompts que apuntaban
   al diseño borrado) y en el propio ADR del vault. Los ADR y las notas del
   vault también citan documentos del repo: el enlace roto se ve igual de mal
   desde ahí.

   Actualiza cada cita para que apunte al ADR resultante. Solo cuando el grep
   deje de devolver referencias huérfanas se borra el archivo. (Precedente real:
   al cosechar el RFD 02 hubo que redirigir **31 líneas en 10 archivos** — casi
   todas en una subserie distinta, `subagentes/`, que seguía en vuelo. Las
   referencias entrantes casi siempre son más de las que parecen: cuéntalas con
   el grep, no de memoria.)
6. **Borra los docs cosechados** — SOLO después de que el/los ADR existen y el
   usuario aprobó la lista exacta de archivos:
   ```bash
   git rm docs/superpowers/specs/<...>.md docs/superpowers/plans/<...>.md
   git commit -m "chore: harvest design docs -> ADR-YYYYMMDD-<tema> (vault)"
   ```
   Borrar es seguro: ambos archivos fueron commiteados por Superpowers y git
   conserva la historia; el ADR apunta al sha.
7. **Verifica**: ADR(s) en `10-Projects/<proyecto>/ADRs/` con wikilink en
   `_PROJECT.md`; `docs/superpowers/` sin restos del feature; commit de limpieza
   hecho.

## Qué NO hacer

- No cosechar planes incompletos ni specs de features abandonados (esos se
  borran sin ADR, con confirmación — no todo diseño merece memoria).
- No copiar documentos completos al vault (el vault es conocimiento durable,
  no archivero de andamiaje).
- No borrar nada sin el ADR escrito primero y la lista aprobada.
