---
name: flaky-test-hunter
description: >
  Diagnostica y estabiliza tests intermitentes: los que "a veces pasan, a veces
  fallan" sin cambios de código. Use when the user says "test flaky", "falla a
  veces", "intermitente", "en CI falla pero local pasa", "re-corre y pasa", or
  when a test fails non-deterministically. Cubre pytest, Jest/Vitest y Flutter.
  NO usar para fallos deterministas — eso es systematic-debugging.
---

# Flaky Test Hunter

Convierte "a veces falla" en una causa concreta y un fix. Complementa a
`superpowers:systematic-debugging` (que exige reproducción consistente — justo lo que un
flaky no da hasta que esta skill lo arrincona).

## Requisitos

- Toolchain local para correr la suite — solo Claude Code.

## Pasos

1. **Confirma que es flaky:** corre el test solo, N veces (empieza con 20):
   - pytest: `pytest ruta::test -x --count=20` (plugin pytest-repeat; sin él, loop en bash)
   - Jest/Vitest: loop o `--retry=0` explícito para no enmascarar
   - Flutter: `flutter test --plain-name "..."` en loop
   Registra la tasa de fallo. 0/20 fallos ≠ estable: sube N o cambia condiciones (paso 3).
2. **Clasifica por síntoma** — las 5 familias, en orden de frecuencia:
   a) **Timing/asincronía**: sleeps fijos, awaits faltantes, animaciones →
      esperas condicionales (ver `superpowers:condition-based-waiting` de Superpowers).
   b) **Orden/aislamiento**: pasa solo pero falla en suite (o al revés) → estado
      compartido, fixtures que filtran; prueba orden aleatorio (`pytest -p randomly`,
      Jest `--randomize`) para confirmarlo.
   c) **Concurrencia real**: race conditions del código bajo test — esto se vuelve
      bug de producto, no de test; escala a `superpowers:systematic-debugging`.
   d) **Recursos externos**: red, puertos ocupados, filesystem, reloj → mockear o aislar.
   e) **Aleatoriedad sin semilla**: fija la seed y expónla en el output del test.
3. **Reproduce agravando la condición sospechada:** carga de CPU en paralelo,
   `--timeout` reducido, orden aleatorio, red desconectada — el flaky que se vuelve
   determinista bajo estrés ya confesó su familia.
4. **Arregla la causa, no el síntoma:** prohibido "subir el sleep" o añadir retries
   ciegos — eso esconde el bug y encarece la suite. Si el fix real no es viable hoy,
   **cuarentena explícita**: marca skip/quarantine con comentario `FLAKY: <causa
   sospechada, fecha, issue>` — nunca lo dejes fallando intermitente (entrena al
   equipo a ignorar rojos).
5. **Verifica la estabilización:** re-corre N×2 veces con orden aleatorio. Solo
   entonces se cierra.
6. **Registra** con `memory-keeper`: test, familia de causa, fix — los flaky
   reinciden por familias, y la memoria evita re-diagnosticar.
