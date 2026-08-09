# Requisitos no funcionales: categorías y calidad de la redacción

## ISO/IEC 25010 — usa la de **2023**, no la de 2011

⚠ **La vigente tiene 9 características, no 8.** La revisión de 2023 es reciente
y **casi ningún checklist que circula la ha incorporado**. Señal rápida: *si
enumera 8 características y no menciona Safety, está obsoleto* — y con él, el
material que lo copió.

Las nueve: **Functional Suitability · Performance Efficiency · Compatibility ·
Interaction Capability · Reliability · Security · Maintainability ·
Flexibility · Safety**.

Lo que cambió, que es donde está el valor:

| 2011 | 2023 |
|---|---|
| Usability | **Interaction capability** (+ *user engagement*, *inclusivity*, *user assistance*, *self-descriptiveness*) |
| Portability | **Flexibility** (+ **scalability** como subcaracterística explícita) |
| Reliability · *maturity* | Reliability · **faultlessness** |
| Security | + **resistance** |
| — | **Safety**, característica nueva de primer nivel |

Tres consecuencias prácticas:

- **`scalability` ya no hay que colarla** dentro de *performance*: tiene sitio
  propio bajo *Flexibility*. Deja de discutirse dónde va.
- **`inclusivity` y `user assistance` son categorías de primer orden.** Si el
  documento no las toca, es una omisión, no una decisión — a menos que la
  declares.
- **`Safety` no es `Security`.** Security es contra un adversario; safety es
  contra el daño, adversario o no. Un sistema puede ser seguro y peligroso.

## ISO/IEC/IEEE 29148:2018 — las 9 características de UN requisito

Sucesor de IEEE 830, reafirmado en 2024. Un requisito individual debe ser:

**necesario · apropiado · no ambiguo · completo · singular · factible ·
verificable · correcto · conforme**

⚠ **Marcado como derivado, no como cita del estándar.** El texto de 29148 está
tras paywall; lo accesible y verificable es la *Guide to Writing Requirements*
de **INCOSE**, armonizada con el estándar. Cuando cites estas nueve, di que
vienen de INCOSE armonizado con 29148 — no las presentes como transcripción.

De las nueve, las dos que más trabajo ahorran al revisar:

- **Singular**: un requisito, una cosa. La palabra "y" en un `shall` casi
  siempre marca dos requisitos disfrazados de uno.
- **Verificable**: si nadie sabe qué comprobaría que se cumple, no es un
  requisito. Es la misma regla que el fit criterion, dicha desde el estándar.

## Sobre el coste de los defectos de requisitos

Vas a encontrarte dos números citados en todas partes. **No los uses:**

- **La curva 1-10-100 de Boehm** es una simplificación posterior de datos cuyos
  ratios reales iban de **1:5 a 1:200** según el estudio. El "1-10-100" es una
  regla mnemotécnica, no un hallazgo.
- **El Standish CHAOS report** lo refutaron **Eveleens & Verhoef en *IEEE
  Software* (2010)** por metodología no transparente.

Lo honesto es decir esto:

> **No hay evidencia cuantitativa sólida y actual sobre el coste de los
> defectos de requisitos. Hay consenso cualitativo sobre la dirección del
> efecto —arreglarlos tarde cuesta más— y nada defendible sobre la magnitud.**

Si necesitas justificar el esfuerzo de esta skill, justifícalo con el proyecto
que tienes delante, no con un número prestado que no aguanta una revisión.
