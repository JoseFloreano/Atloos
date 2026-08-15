---
name: deck-or-brief
description: >
  Decide PRIMERO si habrá alguien exponiendo —sí: mazo navegable; no: informe de
  una página que se defiende solo— y produce el entregable de negocio como HTML
  autocontenido para `Artifact`, con la narrativa problema → evidencia →
  propuesta → números → el pedido. Use when the user says "hazme una
  presentación para X", "prepara un mazo para el comité", "necesito un informe
  ejecutivo de esto", "arma la propuesta para el cliente", "resume esto para
  dirección", "algo que pueda compartir con negocio". Desambiguación, y es donde
  esto se rompe: si piden un `.pptx` es `bundled:pptx`, NO esta; si piden un
  `.docx` o un informe Word es `bundled:docx`, NO esta; si lo que quieren es un
  gráfico o un cuadro de mando, `bundled:dataviz` manda en las decisiones de
  gráfico y esta pone el documento alrededor. Esta es para HTML autocontenido
  que se ve en el sitio y se comparte.
---

# Deck or Brief

## La pregunta que va primero, antes que cualquier decisión de formato

> **¿Va a haber alguien exponiendo?**
> Sí → **mazo navegable**. No → **informe de una página**.

No es preferencia estética. Cambia la **densidad por pantalla**, si hay **notas
del ponente**, y si el documento **tiene que sostenerse solo cuando nadie lo
explica**. Preguntarla después obliga a rehacerlo entero, igual que la fase 0
(`shared:requirements-designer`).

Qué cambia en cada rama, y qué hacer si te dicen "las dos":
`references/mazo-vs-informe.md`.

## Los dos antídotos contra el relleno

Esta familia tiende a producir diapositivas bonitas sin contenido. Los dos van
aquí y no en un reference porque son la condición de arranque:

- **Sin el pedido explícito no hay entregable.** Si no sabes qué se le pide a
  quien escucha —aprobar, financiar, decidir entre A y B, no hacer nada—,
  **pregúntalo antes de generar nada**. Un documento sin pedido es un informe de
  actividad.
- **Cada afirmación de negocio lleva su número, y el número lleva de dónde
  salió.** Sin las dos cosas, la afirmación se cae del documento.

## La narrativa, que es el 80 % del valor y no cambia entre formatos

**problema → evidencia → propuesta → números → el pedido.**
Los cinco tiempos: `references/narrativa.md`.

## El canal: son requisitos, no descubrimientos

`Artifact` publica **HTML autocontenido bajo CSP estricta**. Descubrirlo
fallando cuesta el documento entero:

- **Un solo fichero**: CSS y JS **en línea**, imágenes como `data:` URL.
- **Sin CDN y sin fuentes remotas.** Si no está en el fichero, no existe.
- **Nada de `localStorage` ni `sessionStorage`** — no están soportados y
  **rompen el artefacto**. El estado vive en variables de JavaScript.
- **Tema claro y oscuro**: el contenedor decide cuál se ve, no tú.
- **Que imprima**: `@media print` y `page-break-inside: avoid`. Un mazo que no
  se puede mandar en PDF acaba rehecho en PowerPoint, y entonces no sirvió.

El esqueleto que las cumple: `references/canal-artifact.md`.

## Pasos

1. **Pregunta si habrá alguien exponiendo** y **cuál es el pedido**. Las dos, y
   antes de nada. Carga `bundled:artifact-design` antes de escribir el fichero.
2. **Escribe la narrativa en texto plano** —cinco tiempos, sin HTML— y enséñala.
   Corregir el argumento cuesta una línea; corregirlo maquetado, una tarde.
3. **Tacha lo que no tiene número.** Lo que sobreviva es el documento.
4. **Maqueta** según la rama, con las cinco restricciones del canal.
5. **Gráficos: `bundled:dataviz` manda.** Esta decide dónde va y qué frase lo
   acompaña; no colores ni tipo.
6. **Verifica antes de entregar**: `shared:web-design-guidelines` es su revisor
   natural —accesibilidad, foco, estados—; que imprima; que se vea en los dos
   temas; y que **el pedido esté escrito, literal, en la última pantalla**.
