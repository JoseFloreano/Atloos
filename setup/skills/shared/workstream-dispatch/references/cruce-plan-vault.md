# El cruce plan ↔ vault — DISEÑO, no implementado

Diseño del paso 0 del despacho. **Nada de esto corre todavía**: es la
especificación para construirlo, con la decisión de dónde vive ya tomada.

## El fallo que lo pide, y por qué no lo cazó nada

El vault tenía `Incontactable` **deprecado desde v8, con ADR, fecha y dueño**.
El plan de sprints no lo recogía, y **se despachó un frente entero encima**.

La pieza que sí lee el vault, `project-resume`, corre **al arrancar la sesión**.
El plan se escribió **tres días después** y no volvió a cruzarse con el índice de
ADRs nunca. No falló la memoria: falló que **nadie vuelve a mirarla cuando el
plan se convierte en trabajo**.

> **Un plan es la última pieza que se escribe y la primera que se ejecuta. Entre
> las dos no hay ninguna aduana.**

## Dónde vive, y por qué NO es una skill nueva

**Decisión: sección de `workstream-dispatch`, no skill propia.** El repo tiene
39 skills y la disciplina es no crear una donde cabe una sección. Los tres
argumentos, en orden de peso:

1. **No tiene disparador propio.** Nadie dice nunca «valida mi plan contra el
   vault». Si fuera skill, sería una que no carga — el Caso 2 de
   `disparadores.md` literal: *la skill existía, era buena y no cargó*.
2. **Su momento ya está cubierto.** Se dispara cuando vas a escribir el primer
   brief, y ahí `workstream-dispatch` **ya está cargada**. Anclarlo a un evento
   que ya ocurre es la ley del disparador aplicada.
3. **Ahí es donde está el dinero.** El coste del fallo fue *un frente
   despachado*. La aduana tiene que estar antes de esa puerta, no en un sitio al
   que hay que acordarse de ir.

⚠ **Y la otra boca: las auditorías.** El humano lo pidió *«que se autovalide
cuando se hacen las auditorías»*, y ahí `workstream-dispatch` no está cargada.
La salida NO es duplicar: es que el encargo de auditoría **cite este fichero**,
igual que cita `higiene-de-salida.md`. Una referencia se cita desde donde haga
falta; una skill hay que invocarla.

## El criterio, tal cual salió del campo

> **Para cada dictamen / entidad de negocio que el plan nombre, ¿hay un ADR que
> lo declare deprecado, refutado o tachado?**

## Cómo se ejecuta — grep, no juicio

El disparador es un evento (**vas a escribir el primer brief**), y el cruce
tiene que ser mecánico o volverá a no hacerse.

1. **Saca los nombres propios del plan**: entidades de negocio, dictámenes,
   estados, nombres de tabla o de campo. Los que van en `Mayúscula`, en
   `backticks` o en **negrita** — no toda palabra.
2. **Cruza contra tres sitios del vault**, en este orden de coste:
   - `ADRs/_INDEX.md` — una línea por ADR con `Estado` y `summary`. La columna
     `Estado` ya trae `superseded-by:`; el `summary` trae los nombres.
   - `bugs/*.md` con `status: open`.
   - Cualquier línea `~~tachada~~` o con `❌ REFUTADO` en `_PROJECT.md` y en las
     notas de `sessions/`.
3. **Cada acierto BLOQUEA el despacho** y se resuelve nombrando el ADR: o el
   plan se corrige, o el ADR se supersede. **Lo que no vale es despachar y
   verlo luego** — que es exactamente lo que pasó.

**Falla cerrado a propósito:** si el vault no está montado, el cruce no se puede
hacer y eso **se dice**, no se salta en silencio. Un cruce que no corrió no es
un cruce que salió limpio — es la enfermedad que este repo lleva doce sprints
persiguiendo.

## Lo que este diseño NO resuelve, y hay que decirlo

- **Un nombre que el vault deprecó con otras palabras** se escapa: el cruce es
  textual. Caza `Incontactable` escrito igual; no caza «el dictamen ese de los
  no contactables».
- **El plan que no nombra la entidad** y aun así la asume. Ningún grep ve eso.
- Por las dos, el cruce es una **red, no una garantía**, y su reporte debe decir
  cuántos nombres cruzó — un «0 hallazgos» sobre 2 nombres extraídos de un plan
  de 40 no es una buena noticia, es un extractor que no funcionó.

## Criterio de terminado, cuando se construya

Un arnés que, sobre un vault de laboratorio con un ADR que deprecia `Fulano` y
un plan que nombra `Fulano`, **da rojo**; y sobre el mismo plan sin ese nombre,
verde. Con su mutación, como todo aquí.
