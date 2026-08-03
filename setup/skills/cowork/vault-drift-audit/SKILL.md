---
name: vault-drift-audit
description: >
  (Cowork) Audita qué proyectos del vault quedaron desfasados respecto al
  código: compara la frescura de cada _PROJECT.md contra la actividad real del
  repo y reporta drift, pendientes zombis y notas huérfanas. Use when the user
  says "audita el vault", "qué está desactualizado", "drift", "revisa qué
  proyectos están atrasados", or como revisión periódica (quincenal). Solo
  lectura por defecto; propone las actualizaciones y las aplica solo si el
  usuario aprueba.
---

# Vault Drift Audit (Cowork)

La red de seguridad del sistema anti-drift: lo que el hook y session-close
dejen pasar, esto lo detecta en frío. (Auditoría R3: el memory rot es lento
e invisible — se caza con revisiones periódicas, no en caliente.)

## Requisitos

- Carpeta del vault conectada (`ObsidianVault/`). Sin ella, PARA y pídela.
- Opcional pero recomendado: carpeta(s) de repos conectadas — sin ellas el
  audit se limita a señales internas del vault (frontmatter `updated`, mtimes).

## Pasos

1. **Inventario**: lista `10-Projects/*/` y stage-a solo los `_PROJECT.md`
   (no las carpetas completas — anti-dump). Lee `updated:` del frontmatter y
   el mtime real de cada uno.
2. **Drift código↔vault** (si hay repo conectado): para cada proyecto, compara
   la fecha del último commit (`git log -1 --format=%ci` vía los archivos del
   repo o pídele al usuario correrlo) contra el `updated` del `_PROJECT.md`.
   **Drift = código con actividad posterior al vault por más de ~7 días.**
3. **Señales internas** (siempre): pendientes con checkboxes intactos por >30
   días (pendientes zombis), `_PROJECT.md` sin sección "Próximo paso", y
   `codebase-map.md` más viejo que el último cambio estructural conocido.
   **ADRs: todos los estados, no solo `accepted`** — `proposed` estancado >14
   días y contradicciones sin `superseded` (tabla en `references/checks.md`).
   Además (detalle y comandos en `references/checks.md`): índice de ADRs
   desfasado (`adr-index.py --check`), `_PROJECT.md` por encima de 120 líneas o
   con secciones `## Hecho`, y notas de `sessions/` ya cosechadas con más de 30
   días — candidatas a `_archive/`.
4. **Reporte por proyecto**, ordenado por severidad de drift: qué está
   desfasado, evidencia (fechas), y la actualización mínima propuesta.
5. **Solo si el usuario aprueba**: aplica las actualizaciones propuestas
   (respetando el aislamiento — un proyecto a la vez) y commitea de vuelta
   los archivos editados a la carpeta conectada.
6. **Poda de skills** (mismo ciclo quincenal): ¿qué skills no se han disparado
   este mes? Heurística gratis: pregunta al usuario cuáles recuerda haber usado
   y revisa el `git log` de `claude-skills/` buscando skills sin ediciones ni
   menciones. Las que nadie usa → candidatas a poda o fusión con `skill-forge`
   (decide él, no tú). **NUNCA un pase LLM automático sobre el catálogo
   completo** — lección del Curator de Hermes: 91M tokens quemados (`ecosistema/16` §R7).
7. Cierra sugiriendo la causa si hay patrón: si el mismo proyecto driftea
   repetidamente, el hook/ritual no está corriendo en esa laptop — revisarlo.

## Qué NO hacer

- No inventes estado: si no puedes determinar qué pasó en el código, reporta
  "indeterminado — requiere repo conectado", no adivines.
- No toques proyectos sin drift ni reorganices el vault de paso.
