# Reglas de negocio, y el alcance negativo

## Qué es una regla de negocio

El *Business Rules Manifesto* (Business Rules Group) dice tres cosas útiles:

- Las reglas son **un activo de negocio más duradero que cualquier
  plataforma**.
- Se expresan en **lenguaje natural y de forma declarativa** — *qué debe ser
  verdadero*, no *qué debe hacer el sistema*.
- **«Ninguna regla se asume nunca.»** Si no está escrita, no existe: vive en la
  cabeza de alguien y se irá con esa persona.

### El criterio operativo, con una advertencia

⚠ Vas a oír *"la RN sobrevive a un cambio de tecnología"*. Es una **paráfrasis
legítima** del Manifesto, pero **no está formulada así en ninguna fuente
primaria**. Úsala como heurística; **no la presentes como cita.**

Tres criterios mejor respaldados, y más fáciles de aplicar:

1. **Independencia de implementación** — la regla se puede cumplir a mano, con
   otro software, o sin software.
2. **Propiedad del negocio, no de TI** — quien puede cambiarla es quien manda
   en el dominio, no quien mantiene el código.
3. **Forma declarativa** — *«qué debe ser verdadero»* frente a *«qué debe hacer
   el sistema»*.

## El ejemplo que enseña el matiz

- **RN**: *un préstamo no puede aprobarse con score < 600.*
- **RF derivado**: *el sistema marca para revisión manual las solicitudes con
  score < 650.*

**Los umbrales no coinciden, y está bien.** 600 es la regla del negocio; 650 es
un margen de seguridad que el sistema aplica para que ningún caso límite se
apruebe solo. Son **artefactos distintos**, no el mismo número reformulado.

Por eso van en capas separadas: si mañana Riesgos sube la regla a 620, el 650
puede quedarse, subir a 670 o desaparecer — pero es **una decisión**, no una
consecuencia automática. Fundidos en un único documento, ese matiz se pierde y
alguien "corrige la inconsistencia" borrando el margen.

## Tablas de decisión y DMN

Valen cuando la lógica es **combinatoria** —a partir de ~4-5 condiciones
cruzadas la prosa se vuelve inmanejable, y es justo donde EARS se rompe— **y**
además **cambia a menudo**. Las dos condiciones, no una.

**DMN 1.5** es el estándar si hace falta formalizarlas.

⚠ **Un motor de reglas para <10 reglas es sobre-ingeniería.** Una tabla en el
documento y un `match` en el código hacen el trabajo, y se leen mejor. El motor
se justifica cuando quien cambia las reglas **no es quien despliega**.

## Alcance negativo

La referencia con nombre y origen verificable es **MoSCoW · "Won't have this
time"** (DSDM / Agile Business Consortium). Lo que la hace valiosa no es la
sigla: es que el "won't" se **registra formalmente**, con el mismo peso que el
"must", para que no se reintroduzca informalmente tres semanas después.

Los ***Non-Goals*** de los design docs hacen lo mismo y son convención de
industria, **sin fuente primaria que los posea**. Dilo así si los citas.

**Numéralos con la misma numeración que el alcance positivo** (N-01, N-02…) y
di **por qué** queda fuera: *"no ahora"*, *"no nunca"* y *"no sabemos"* son
tres estados distintos, y confundirlos es lo que produce la discusión de la
semana 6.
