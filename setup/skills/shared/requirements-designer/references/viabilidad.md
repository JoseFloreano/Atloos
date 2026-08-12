# Fase 0 — traducir lo que el negocio pide a lo que el dato soporta

Detalle de la fase 0 del `SKILL.md`. Sale de una fricción con coste medido
(reporte de campo del 2026-08-10), no de un manual.

## Por qué existe

El humano no siempre sabe qué quiere **porque no sabe qué es viable**, y el
agente no sabe qué es importante **porque no conoce el negocio**. Es una
asimetría, no una falta de información: ninguno de los dos puede resolverla
solo, y el documento de requisitos escrito antes de resolverla es un documento
impecable sobre algo que no se puede construir.

La petición que la motivó fue *«desarrollar el MVP de avisos por corte»*. Nadie
dijo «levanta los requisitos». Por eso la fase 0 no es una sección más: cambia
**cuándo** carga la skill.

## Las tres columnas

No se pasa de fase 0 hasta que las tres están llenas para cada cosa que el
sistema promete. Una fila por promesa.

| qué se puede medir | con qué error | qué decisión de negocio depende de ello |
|---|---|---|
| lo que el dato disponible soporta de verdad, con su **grano** y su **latencia** | el error real: sesgo, huecos, retraso de llegada, cobertura | qué hace alguien distinto según el número; si no cambia ninguna decisión, la medida sobra |

Las tres preguntas que llenan las columnas:

1. **¿Qué dato existe, con qué grano y con cuánto retraso llega?** No «qué dato
   hay» — cuándo está disponible. Un dato que llega a T+1 no soporta una
   promesa intradía, y esa es la muerte silenciosa de la mitad de los MVPs.
2. **¿Qué error tiene esa medida y quién lo va a notar?** Un error del 15 % es
   irrelevante para priorizar una ruta y letal para facturar.
3. **¿Qué decisión cambia?** Si la respuesta es «ninguna, pero estaría bien
   verlo», la fila no es un requisito: es un dashboard, y va al alcance
   negativo.

## La mejor respuesta posible

Tiene la misma jerarquía que el *«no es ML»* de `ml-problem-framing`: la salida
más valiosa no es el plan, es la **reformulación**.

> **«Eso no se puede detectar, pero sí se puede medir por corte.»**

La forma es siempre la misma: *no <lo pedido>, pero sí <lo que el dato
aguanta>, y con eso se decide <la misma decisión de negocio o una vecina útil>*.
Si el tercer hueco queda vacío, la reformulación no vale: has cambiado el
objetivo, no lo has salvado.

## El antipatrón, medido en campo

El agente pasó turnos repitiendo que el detector intradía estaba muerto **en vez
de replantear qué sí podía hacerse por corte**. La regla que desatascó el diseño
la escribió el humano:

> *«capa 1 por corte, y 2 y 3 solo si la 1 dicta que se deben ejecutar»*

A partir de ahí el diseño avanzó solo. Es decir: el desbloqueo no necesitó dato
nuevo ni técnica nueva — necesitó **reordenar la promesa alrededor de lo que el
dato ya soportaba**. Eso es trabajo de fase 0, y lo hizo el humano porque el
agente estaba ocupado teniendo razón.

**Repetir la imposibilidad no es analizar viabilidad.** El bucle se reconoce
así: dos turnos seguidos cuya conclusión es la misma imposibilidad, con
argumentos distintos. Al segundo, para y cambia de tarea: ya no toca demostrar
que no se puede, toca proponer qué sí.

## Cómo se cierra la fase 0

Con una de estas tres, escrita, y **nunca con un «depende»**:

1. **Viable como se pidió** → sigue a los RF con el alcance intacto.
2. **Viable reformulado** → escribe la reformulación con sus tres columnas y
   **haz que el humano la acepte explícitamente** antes de seguir. Es un cambio
   de alcance, no un detalle técnico.
3. **No viable con el dato de hoy** → di qué dato lo haría viable, con su grano
   y su latencia, y para. Ese dato es el requisito, y probablemente es un
   proyecto distinto.

Cualquiera de las tres se lleva al **alcance negativo numerado** (paso 5): lo
que se descartó en fase 0 es lo que vuelve en la semana 6 disfrazado de idea
nueva.

## Ejemplo trabajado — PENDIENTE

**No hay ejemplo aquí a propósito.** El material real —los mensajes literales
del desatasco y los intentos inviables que lo precedieron— lo tiene el usuario y
no llegó con el encargo del sprint 2.

Un caso ficticio en la única sección de la skill que enseña a distinguir lo
viable de lo que suena viable sería exactamente el relleno que el RFD 17 §4.2
manda evitar: enseñaría la forma del razonamiento sin su fricción, que es lo
único que aquí vale.

**Qué hace falta para cerrarlo**, en concreto:

- La petición literal inicial y qué se entendió de ella.
- Los intentos inviables, con **por qué** murió cada uno (qué dato faltaba, qué
  grano, qué latencia).
- Los turnos del bucle de imposibilidad, para poder señalar dónde se debió
  parar.
- El mensaje del humano que lo desatascó, literal.
- El diseño final por capas y cuál fue la decisión de negocio que sobrevivió.

Con eso, este bloque se rellena con las tres columnas del caso y la
reformulación tal como se produjo.
