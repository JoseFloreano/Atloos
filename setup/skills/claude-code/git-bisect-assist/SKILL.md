---
name: git-bisect-assist
description: >
  Encuentra el commit exacto que introdujo una regresión usando git bisect de
  forma asistida (idealmente automatizada con bisect run). Use when the user says
  "¿qué commit rompió esto?", "esto funcionaba antes", "encuentra la regresión",
  "bisect", "desde cuándo falla", or when a bug is known to be a regression (it
  worked in some previous version). NO usar para bugs sin historia conocida —
  para eso está systematic-debugging (Superpowers).
---

# Git Bisect Assist

Búsqueda binaria del commit culpable. Complementa a `superpowers:systematic-debugging`: esta
skill encuentra el CUÁNDO/DÓNDE (commit); aquella encuentra el POR QUÉ (causa raíz).

## Requisitos

- Repo git local con historia suficiente y toolchain para ejecutar la prueba —
  solo Claude Code. Working tree limpio (o `git stash` primero, avisando).

## Pasos

1. **Consigue un reproductor determinista** antes de tocar bisect: un comando que
   sale 0 si funciona y ≠0 si falla (test existente, o escribe uno mínimo ahora).
   Si el fallo es intermitente, NO uses bisect — usa `flaky-test-hunter` primero.
2. **Delimita el rango:** `good` = último commit/tag donde el usuario confirma que
   funcionaba (pregunta si no lo sabe; prueba candidatos: releases, inicio de sprint);
   `bad` = HEAD o donde falla.
3. **Automatiza si se puede:**
   ```bash
   git bisect start <bad> <good>
   git bisect run <comando-reproductor>   # sale solo
   ```
   Si el reproductor no es automatizable (visual/manual), guía el bisect manual:
   ejecuta, pregunta al usuario "¿funciona? [s/n]", marca `git bisect good|bad`.
   Son ~log2(N) iteraciones — dilo para calibrar expectativas.
4. **Al encontrar el commit:** `git bisect reset` SIEMPRE (no dejes el repo en
   estado bisect). Muestra `git show <sha> --stat` y el diff relevante.
5. **Del commit a la causa:** el commit culpable es evidencia, no diagnóstico —
   continúa con `superpowers:systematic-debugging` fase 1 usando ese diff como pista principal.
6. **Registra** con `memory-keeper`: síntoma, commit culpable (sha + título),
   causa raíz y fix — las regresiones repetidas en la misma zona son señal de
   arquitectura (regla de Superpowers: 3+ → cuestionar el diseño).

## Trampas conocidas

- Commits que no compilan a mitad del rango: `git bisect skip` en vez de adivinar.
- El reproductor debe correr rápido — con suites lentas, reduce al test mínimo antes.
- Si `good` resulta también fallar, el rango está mal: retrocede más, no fuerces.
