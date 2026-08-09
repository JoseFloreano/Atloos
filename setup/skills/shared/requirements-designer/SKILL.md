---
name: requirements-designer
description: >
  Produce el documento de requisitos con las tres capas separadas —funcionales
  en EARS, no funcionales con número y unidad, reglas de negocio— más alcance
  negativo numerado y traspaso nominal a quien diseña. Use when the user says
  "qué necesita este proyecto", "levanta los requisitos", "define el alcance",
  "qué tiene que hacer el sistema", "escribe la especificación", "los criterios
  de aceptación", or ANTES de `schema-designer` y `api-design`, que diseñan
  suponiendo que los requisitos ya se conocen. NO usar para un cambio pequeño
  ni antes de haber explorado el comportamiento — eso es burocracia.
---

# Requirements Designer

Hoy hay un salto: `superpowers:brainstorming` idea,
`superpowers:writing-plans` planifica la **implementación**, y
`schema-designer` / `api-design` diseñan **suponiendo que los requisitos ya se
conocen**. Nadie los produce. Esta skill es ese eslabón.

## Cuándo NO usarla — va primero, porque es lo que la salva

- **Cambio pequeño o bug conocido.** El overhead supera al trabajo.
- **Antes de explorar.** Especificar lo que aún no has visto funcionar produce
  specs impecables y equivocados; tres días de implementación limpia hacia el
  sitio erróneo.
- **Sola, desde ingeniería.** Sin producto ni diseño, el documento hereda un
  solo punto de vista.

**Ajusta el rigor a la complejidad**, y dilo cuando decidas bajarlo. Los cinco
fallos medidos en campo: `references/cuando-no-usarla.md`.

## Las tres capas, separadas — mezclarlas es el fallo clásico

| | Qué es | La prueba de que está bien escrito |
|---|---|---|
| **RF** | qué hace el sistema | en EARS, y **se puede escribir un test** |
| **RNF** | con qué calidad | **número + unidad + instrumento de medida** |
| **RN** | qué es cierto en el dominio | **sobrevive sin ese software** |

## Pasos

1. **Entiende el problema antes de escribir nada.** Si no puedes decir a quién
   le duele y cómo se nota, para ahí: lo que falta no es un documento.
2. **RF en EARS**, numerados. Seis plantillas —ubicuo, evento, estado,
   opcional, no deseado, complejo— en `references/ears-y-medida.md`. Con más de
   ~3 precondiciones EARS se rompe: pasa a tabla de decisión.
3. **RNF con fit criterion.** *"Rápido"* no es un requisito; *"p95 < 300 ms con
   500 usuarios concurrentes, medido con k6"* sí. Categorías de calidad:
   `references/rnf-y-calidad.md` (**ISO 25010:2023, 9 características** — un
   checklist con 8 y sin *Safety* está obsoleto).
4. **RN aparte de los RF que las implementan.** Un umbral de negocio y el
   umbral que el sistema aplica **no tienen por qué coincidir**:
   `references/reglas-de-negocio.md`.
5. **Alcance negativo numerado**, con la misma numeración que el positivo. Es
   lo que impide la discusión de la semana 6.
6. **Traspaso nominal**: nombra qué RF/RN van a `schema-designer` (entidades y
   grano) y cuáles a `api-design` (superficie y contrato). Sin esto el
   documento se archiva, que es el destino habitual.
7. **Convierte al menos un RF en condición de `/goal`** con
   `claude-code:goal-forge` (en Cowork no existe: ahí para en el paso 6). Un
   requisito verificable y una condición de meta son el mismo objeto a dos
   altitudes; el ejemplo trabajado, en `references/ears-y-medida.md`.
8. **Verifica**: ¿cada RNF tiene número, unidad e instrumento? ¿cada RF admite
   un test? ¿hay alcance negativo? ¿cada requisito tiene destinatario? Si algo
   falta, no lo entregues: dilo.
