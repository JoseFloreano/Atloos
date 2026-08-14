---
name: requirements-designer
description: >
  Traduce lo que el negocio pide a lo que el dato soporta (fase 0) y produce el
  documento de requisitos con las tres capas separadas —funcionales en EARS, no
  funcionales con número y unidad, reglas de negocio— más alcance negativo
  numerado y traspaso nominal a quien diseña. Use when the user says "desarrolla
  el MVP de X", "quiero una herramienta/un sistema que X", "necesito que
  detecte/avise/prediga X", "haz X para <persona>", "¿se puede hacer X con estos
  datos?", "¿esto es viable?", "levanta los requisitos", "define el alcance",
  "los criterios de aceptación", or ANTES de `schema-designer` y `api-design`,
  que ya los suponen conocidos. Reparto con `superpowers:brainstorming`: esa es
  para **no sé qué construir**; la fase 0, para **sé qué quiero y no sé si se
  puede**. Si aplican las dos, brainstorming primero. NO usar para un cambio
  pequeño ni antes de haber explorado el comportamiento — eso es burocracia.
---

# Requirements Designer

## Fase 0 · ¿lo soporta el dato? — va PRIMERA y es la prioridad

La asimetría que lo ordena todo: **el humano no sabe qué quiere porque no sabe
qué es viable; el agente no sabe qué es importante porque no conoce el negocio.**

No se pasa sin las tres columnas llenas, una fila por promesa:

**qué se puede medir · con qué error · qué decisión de negocio depende de ello.**

Tu mejor respuesta no es *«no se puede»*, es reformular — como el *«no es ML»*
de `ml-problem-framing`:

> **«Eso no se puede detectar, pero sí se puede medir por corte.»**

**Repetir la imposibilidad no es analizar viabilidad.** En campo el agente gastó
turnos declarando muerto el detector intradía **en vez de replantear qué sí
podía hacerse por corte**; la regla que lo desatascó la escribió el humano. Al
segundo turno con la misma conclusión, para.

Y si no puedes decir **a quién le duele y cómo se nota**, lo que falta no es un
documento.

Las preguntas, las salidas y el ejemplo: `references/viabilidad.md`.

**Cuándo NO usarla**, que es lo que la salva: cambio pequeño o bug conocido ·
antes de explorar · sola desde ingeniería. **Ajusta el rigor a la complejidad** y
dilo al bajarlo. Los cinco fallos: `references/cuando-no-usarla.md`.

## Las tres capas — mezclarlas es el fallo clásico

- **RF** · qué hace → en EARS, y **se puede escribir un test**.
- **RNF** · con qué calidad → **número + unidad + instrumento**.
- **RN** · qué es cierto en el dominio → **sobrevive sin ese software**.

## Pasos

0. **Fase 0.** Su salida —viable, viable reformulado o no viable— se acepta
   explícitamente antes de seguir.
1. **RF en EARS**, numerados; seis plantillas en `references/ears-y-medida.md`.
   Con más de ~3 precondiciones EARS se rompe: pasa a tabla de decisión.
2. **RNF con fit criterion**: *"p95 < 300 ms con 500 concurrentes, medido con
   k6"*, nunca *"rápido"*. `references/rnf-y-calidad.md` (**ISO 25010:2023, 9
   características**; con 8 y sin *Safety*, obsoleto).
3. **RN aparte de los RF que las implementan**: el umbral de negocio y el que
   aplica el sistema no tienen por qué coincidir
   (`references/reglas-de-negocio.md`).
4. **Alcance negativo numerado**, misma numeración que el positivo — y lo
   descartado en fase 0 entra aquí.
5. **Traspaso nominal**: qué RF/RN van a `schema-designer` (entidades y grano) y
   cuáles a `api-design` (superficie y contrato). Sin esto se archiva.
6. **Al menos un RF convertido en condición de `/goal`** con
   `claude-code:goal-forge` (en Cowork para en el 5).
7. **Verifica**: ¿fase 0 cerrada? ¿cada RNF con número, unidad e instrumento?
   ¿cada RF con un test posible? ¿alcance negativo? ¿destinatario por requisito?
   Si falta algo, dilo en vez de entregarlo.
