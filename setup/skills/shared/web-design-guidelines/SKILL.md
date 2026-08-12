---
name: web-design-guidelines
description: >
  Audita código de interfaz contra las Web Interface Guidelines de Vercel —
  accesibilidad, foco, estados, semántica, movimiento— y devuelve hallazgos en
  formato `fichero:línea`. Use when the user says "revisa mi UI", "audita la
  interfaz", "revisa la accesibilidad", "esto es accesible?", "revisa el UX",
  "compara esto con las buenas prácticas de web", "review my UI", "check
  accessibility", or antes de dar por terminada una pantalla. NO usar para
  decidir la DIRECCIÓN estética de un diseño (eso es `bundled:frontend-design`,
  el plugin oficial de Anthropic — ver Procedencia), ni para seguridad web (eso es
  `web-security-review`).
---

# Web Design Guidelines

Revisa ficheros de UI contra las Web Interface Guidelines y devuelve los
incumplimientos como `fichero:línea`, sin prosa.

## ⚠ Requisitos — léelo antes, porque condiciona todo

Esta skill **no contiene las reglas**: las descarga en cada revisión de

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

- **Necesita `WebFetch` y red.** Es su único requisito, y es duro.
- **Sin red no hay revisión**, y ese es el fallback honesto: **dilo y para**. No
  improvises un checklist de accesibilidad de memoria y lo presentes como si
  fueran las guidelines — sería inventar la autoridad que da valor al informe.
  Si quieres avanzar sin red, di explícitamente que estás revisando *"con
  criterio general, no contra las Web Interface Guidelines"*.
- **Las reglas pueden cambiar sin que este repo se entere.** Ver Procedencia.

## Pasos

1. **Descarga las guidelines frescas** de la URL de arriba, en cada revisión.
   No las caches entre sesiones: la versión de ayer no es la de hoy.
2. **Determina los ficheros a revisar.** Si el usuario no los dio, pregúntale
   por el fichero o el patrón. No revises el repo entero por tu cuenta.
3. **Aplica todas las reglas** del documento descargado, incluido su formato de
   salida — manda el documento, no tu criterio.
4. **Devuelve los hallazgos como `fichero:línea`**, uno por línea y sin
   párrafos de introducción. El valor de este informe es que se puede recorrer.
5. **Di cuántas reglas aplicaste y cuántos ficheros miraste.** Un informe sin
   denominador no se puede interpretar: cero hallazgos sobre dos ficheros no es
   lo mismo que cero sobre veinte.

## Procedencia y su límite — parte del contrato, no una nota al pie

- **Origen**: `vercel-labs/agent-skills`, skill `web-design-guidelines`.
- **Commit**: `7c180d9044c9ae2b442b567aad4e42a28dd5ed62` · **2026-07-24**.
- **Licencia**: MIT (permisiva; no exige compartir igual).
- **Importada**: 2026-08-11, por el protocolo de `bd-y-nube/05` §2. Adaptación:
  disparadores en español, requisitos con fallback declarado, y este bloque.

⚠ **El commit fija el envoltorio, no las reglas.** El original son ~176 palabras
cuya sustancia entera vive tras una URL, así que **el contenido que esta skill
aplica puede cambiar sin producir ningún diff aquí**. Es la enfermedad que este
repo persigue con tres arneses: un contenido con dos puntos de consumo donde
nada obliga a sincronizarlos.

**El motivo por el que se aceptó ya no vale.** Se dijo que vendorizar estaba
cerrado por no haber verificado la licencia de las reglas. Está verificada:
`vercel-labs/web-interface-guidelines` es **MIT** (`4e799d4`, 2026-04-06) y su
`command.md` existe. **Deuda abierta**: cachearlo con su commit y usar la red
solo para refrescarlo cerraría la enfermedad en vez de declararla.
