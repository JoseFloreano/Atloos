# Fuga de datos — taxonomía, nombres y cómo se caza

La fuga es el fallo que produce el modelo excelente que no funciona. No es raro:
Kapoor & Narayanan (*Patterns*, 2023) documentaron fuga en **294 papers de 17
disciplinas**. Si tu resultado sorprende para bien, empieza por aquí.

## Los cuatro nombres que hay que usar

Nombrar mal la fuga hace que se arregle mal. Cuatro categorías, y cada una tiene
su antídoto distinto:

| Nombre | Qué pasa | Antídoto |
|---|---|---|
| **target leakage** | una feature contiene la etiqueta, o su consecuencia directa | auditar disponibilidad: ¿existe antes de que ocurra el evento? |
| **train-test contamination** | información del test entró al entrenamiento | todo `fit` dentro del pipeline y después del split |
| **temporal leakage** | se entrenó con futuro respecto al momento de predecir | split temporal, `gap`, purging y embargo |
| **group leakage** | el mismo sujeto/entidad aparece en train y en test | `GroupKFold` por la entidad, no por la fila |

## Las dos fuentes, y qué aporta cada una

**Kaufman, Rosset & Perlich** (KDD 2011) — el marco original:

- **«No time machine»**: ninguna feature puede contener información que no
  existiera en el momento legítimo de la predicción. Es el test mental más
  barato que hay y caza la mayoría de los casos.
- **Immediate trigger leakage**: la feature registra algo que ocurre *porque* el
  evento va a ocurrir. La llamada al servicio de bajas predice la baja.
- **Design-based leakage**: la fuga la introdujo el **diseño del dataset**, no
  el código. Se muestreó, se filtró o se unió de una forma que ya sabe la
  respuesta. Es la más difícil de ver porque no hay línea culpable.

**Kapoor & Narayanan** (*Patterns*, 2023) — la taxonomía operativa:

- **L1 · separación sucia**: normalizar, imputar, seleccionar features o
  codificar **antes** del split. Es la más común y la más fácil de evitar: todo
  dentro de un `Pipeline` de scikit-learn, y el `fit` solo sobre train.
- **L2 · features ilegítimas**: features que no estarán disponibles al predecir,
  o que son proxy de la etiqueta.
- **L3 · el test no representa**: el conjunto de evaluación no se parece al uso
  real — mal split temporal, mal split por grupo, o muestreo que cambió la
  proporción de clases sin decirlo.

Su instrumento —**«model info sheets»**, 21 preguntas— sirve tal cual como
checklist antes de dar un modelo por bueno.

## El caso más subestimado: target encoding sin out-of-fold

Codificar una categoría por la media de la etiqueta es potente y es una trampa:
si la media se calcula con la fila que estás codificando, cada fila lleva dentro
su propia respuesta. En categorías con pocos casos el efecto es brutal y el
modelo parece excelente en validación.

**El antídoto**: calcular la codificación **out-of-fold** — para cada fold, la
media se estima solo con los otros folds— y con suavizado hacia la media global
para categorías raras. En scikit-learn, `TargetEncoder` lo hace internamente por
defecto; si lo implementas a mano, la parte out-of-fold es lo primero que se
olvida.

## Split temporal: `gap`, purging y embargo

`TimeSeriesSplit` respeta el orden y admite `gap`, que es un mini-embargo ya
integrado: descarta las observaciones inmediatamente anteriores al bloque de
validación.

No basta cuando **la etiqueta se construye sobre una ventana**. Si la pregunta
es *«¿churn en los próximos 90 días?»*, la etiqueta de una fila de enero usa
datos hasta abril: entrenar con filas de febrero es entrenar con futuro aunque
las fechas de las features parezcan correctas.

- **Purging**: eliminar del entrenamiento las observaciones cuya **ventana de
  etiqueta** se solapa con el periodo de validación.
- **Embargo**: además, descartar un margen posterior, porque la autocorrelación
  hace que lo inmediatamente siguiente siga contaminado.

López de Prado, *Advances in Financial Machine Learning*, cap. 7. El origen es
financiero, pero la condición que lo motiva —etiquetas con ventana y series
autocorreladas— aparece igual en churn, en mantenimiento predictivo y en
demanda.

**Y el punto que se olvida**: el k-fold estándar asume i.i.d. Con datos
temporales no lo son, y **filtra por los bordes** de cada fold aunque el split
parezca limpio.

## Cómo se caza, en la práctica

1. **Ordena las features por importancia** y mira las tres primeras una por una:
   ¿de dónde sale ese dato y cuándo se rellena?
2. **Pregunta la fecha de cada campo**, no su valor. Un campo sin fecha de
   creación es sospechoso por defecto.
3. **Compara con el baseline.** Un salto enorme sobre la regla de negocio
   existente es señal de fuga antes que de talento.
4. **Simula el momento de servir**: reconstruye una fila usando solo lo que
   habría estado disponible entonces. Si no puedes, esa feature no vale.
