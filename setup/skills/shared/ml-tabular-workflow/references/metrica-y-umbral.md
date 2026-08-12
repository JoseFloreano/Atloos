# Métrica y umbral

Dos errores distintos y consecutivos: elegir la métrica que no ve el problema, y
dejar el umbral en `0.5` porque venía así.

## `accuracy` con desbalance: es aritmética, no opinión

Con 1 % de positivos, predecir siempre «negativo» da 99 % de acierto y cero
valor. No hace falta más argumento: la métrica no distingue el modelo del
constante trivial.

## *«ROC-AUC miente»* — el eslogan es falso; el mecanismo es real

**Como criterio de ranking, ROC y PR son equivalentes.** Davis & Goadrich (ICML
2006), **Teorema 3.2**: una curva domina a otra en el espacio ROC **si y solo
si** la domina en el espacio precision-recall. Un modelo que ordena mejor ordena
mejor en las dos. Repetir «ROC-AUC miente» sin esto es propagar un eslogan.

**Lo que cambia es la sensibilidad de la curva**, y ahí sí hay una diferencia
que importa:

- El **FPR** = FP / (FP + **TN**) lleva los verdaderos negativos en el
  denominador. En un problema desbalanceado los TN son mayoría abrumadora, así
  que un aumento grande de falsos positivos mueve el FPR muy poco: **la curva
  ROC absorbe el error**.
- La **precisión** = TP / (TP + FP) compara los falsos positivos contra los
  verdaderos positivos, que son pocos. El mismo aumento de FP hunde la precisión
  de golpe: **la curva PR reacciona**.

Por eso con desbalance fuerte se reporta PR-AUC (o average precision): no porque
ROC mienta sobre el orden, sino porque **su escala esconde la magnitud del coste
en la región donde vas a operar**.

**Saito & Rehmsmeier** (PLOS ONE, 2015) es la réplica empírica: sobre datos
desbalanceados, la ROC da una impresión visual optimista que la PR no da.

## El umbral es un hiperparámetro de negocio

No es una convención estadística y no hay razón para que sea `0.5`. `0.5` es el
punto neutro solo si un falso positivo y un falso negativo cuestan lo mismo, que
casi nunca es cierto.

El procedimiento:

1. **Escribe la matriz de coste** en unidades de negocio: cuánto cuesta un falso
   positivo, cuánto un falso negativo, cuánto vale un verdadero positivo. Si no
   sabes los números, pregúntalos — es la conversación que hace útil el modelo.
2. **Optimiza el umbral contra esa función**, no contra F1. En scikit-learn,
   `TunedThresholdClassifierCV` con un `scoring` construido desde la matriz, y
   con validación cruzada para no ajustar el umbral al ruido.
3. **Reporta el umbral junto a la métrica.** Un AUC sin umbral no dice qué se va
   a hacer distinto mañana.

### El ejemplo documentado (German Credit)

Con el coste asimétrico real del dataset:

| Umbral | Score de negocio |
|---|---|
| `0.5` (por defecto) | **−209** |
| optimizado (**~0.03**) | **−143** |

**~50 % de mejora sin tocar el modelo**: mismo entrenamiento, mismas features,
misma AUC. Solo movió el punto de corte. Es el mejor argumento disponible de que
el umbral no es un detalle de implementación.

## Qué reportar, siempre

- La métrica de ranking (PR-AUC con desbalance; ROC-AUC si está equilibrado).
- **El umbral elegido y por qué**, con la matriz de coste.
- La matriz de confusión **en ese umbral**, en números absolutos.
- El resultado del baseline en la misma métrica y el mismo umbral. Sin eso no se
  sabe si el modelo aportó algo.
