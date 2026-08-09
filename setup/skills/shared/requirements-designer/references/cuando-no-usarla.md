# Cuándo NO usar esta skill

Los cinco fallos reales del spec-driven con agentes, documentados por quien lo
usó en campo (Nearform, 2026). No son teoría: son las cinco formas en que un
documento de requisitos deja de ayudar y empieza a estorbar.

## 1. Spec detallado sin entender el problema

El más caro. Produce **tres días de implementación limpia y completamente
equivocada** — y limpia es lo peligroso: nada en el código delata que va hacia
el sitio erróneo, porque el código cumple el spec.

**Señal de que estás aquí:** puedes escribir los `shall` pero no puedes decir a
quién le duele el problema ni cómo se nota que desapareció.

## 2. Aplicarlo a todo

Un cambio de dos líneas con un documento de requisitos delante: **el overhead
supera al trabajo**. Y no es solo tiempo perdido — enseña al equipo que el
proceso es teatro, y a la tercera nadie lo lee.

**Una skill de requisitos que se dispara para un cambio trivial es este fallo,
literalmente.** Por eso el anti-trigger está en la descripción y no enterrado
aquí.

## 3. Especificar antes de explorar

Con un agente delante, explorar es barato: pídele que enseñe el comportamiento
actual, que pruebe dos formas, que te muestre qué se rompe. **Media hora de
exploración cambia el spec más que medio día de redacción.**

Especificar primero convierte suposiciones en requisitos, y un requisito ya no
se cuestiona: se implementa.

## 4. Las omisiones pequeñas se amplifican

Un modelo **rellena los huecos con supuestos** —y lo hace bien, de forma
plausible y coherente—, así que el supuesto no se ve: se propaga por el resto
del documento y por el código que sale de él.

**Mitigación:** al terminar, relee buscando lo que NO dijiste. Cada campo sin
regla de validación, cada estado sin transición, cada error sin comportamiento
es un hueco que alguien va a rellenar por ti.

## 5. Specs escritos solo por ingeniería

Sin producto ni diseño, el documento es coherente y parcial a la vez. Los RNF
son los que más lo sufren: ingeniería escribe latencia y disponibilidad, y
nadie escribe *inclusivity* ni *user assistance* — que en ISO 25010:2023 son
categorías de primer orden.

---

## La regla que sale de los cinco

> **Ajusta el rigor a la complejidad, y declara el ajuste.**

No hay tabla de umbrales, y sería falsa si la hubiera. Lo que sí se puede
exigir es que la decisión sea **explícita**: *"esto va sin RNF formales porque
es un cambio interno de un endpoint ya medido"* es una frase que alguien puede
discutir. Bajar el rigor en silencio, no.

Y si decides no usar la skill, **dilo y sigue**. Una skill que se disparó y
entregó medio documento es peor que una que no se disparó: el medio documento
se archiva y luego se cita como si fuera completo.
