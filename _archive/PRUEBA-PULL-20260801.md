# Archivo de prueba para `/pull` — 2026-08-01

Este archivo existe **solo** para verificar el comando `/pull` del puente
Telegram (el gap de C4 del RFD 02, implementado en `801e7b1`).

## Cómo se usa

1. Desde el móvil, abre o retoma una conversación en modo escritura cuya rama
   `tg/*` naciera **antes** de este commit.
2. `/pull` — debe rebasar la rama sobre `main` y traer este archivo.
3. Comprueba que este archivo aparece en el worktree y que **el trabajo de la
   rama sigue ahí** (el rebase no debe perder nada).

## Qué se está probando

- Que `/pull` detecta que la rama está detrás y cuenta cuántos commits.
- Que el rebase conserva el trabajo propio de la rama.
- Que **invalida el verde de `/test`** y lo avisa: cambiar la base significa
  que los tests anteriores ya no cubren este código.
- Que ante conflicto **aborta y deja la rama intacta** (para eso habría que
  provocar un choque en el mismo archivo; este no lo provoca).

## Después

Borrar este archivo cuando `/pull` quede validado. No documenta nada del setup:
es un canario desechable, como los que se usaron para el aislamiento de T2.
