# ¿Hace falta deep learning en tabular? — el estado en 2026

**Respuesta corta: boosting es el default operativo, y no hay ganador único.**
La respuesta larga tiene tres piezas y la tercera exige escepticismo.

## 1 · Por qué los árboles ganan en tabular mediano

**Grinsztajn, Oyallon & Varoquaux** (NeurIPS 2022): 45 datasets, ~20.000 horas
de búsqueda de hiperparámetros. Los modelos de árboles siguen por delante en
tabular de tamaño mediano, y lo interesante no es el marcador sino **las tres
razones estructurales**, porque explican cuándo dejará de ser cierto:

1. **Robustez a features no informativas.** En tabular abundan las columnas que
   no aportan nada; los árboles simplemente no las eligen, y las redes se dejan
   arrastrar por ellas.
2. **Preservación de la orientación por columna.** Las redes son
   aproximadamente *rotation-invariant*: para ellas una combinación lineal de
   columnas es tan natural como una columna. En tabular eso es un desajuste,
   porque **cada columna tiene semántica propia** y mezclarlas destruye
   información que el árbol conserva gratis.
3. **Aprendizaje nativo de funciones irregulares.** Las fronteras reales de los
   datos tabulares son escalonadas y no suaves; el sesgo inductivo de las redes
   hacia funciones suaves juega en contra.

## 2 · El matiz de 2024: confirma en parte y refuta en parte

Un **benchmark de más de 300 datasets (2024)** matiza el resultado anterior:

- **CatBoost domina** en datasets grandes y en regresión.
- **TabR, ModernNCA y RealMLP igualan o superan** a los árboles en
  clasificación.
- **No hay un ganador único.** El resultado depende del tamaño, de la tarea y
  del presupuesto de tuning.

Conclusión práctica: «los árboles ganan siempre» ya no es cierto como
afirmación general; sigue siendo cierto como **apuesta por defecto** cuando
tienes poco tiempo y un dataset normal.

## 3 · TabPFN-2.5, con el escepticismo puesto

**TabPFN-2.5** (2025) es un *foundation model* tabular que predice en una pasada
sin entrenamiento por dataset. Es genuinamente interesante y **no ha ganado el
debate**:

⚠ Su titular de **«100 % win rate»** es **contra XGBoost por defecto, sin
ajustar**. Comparar un modelo cuidadosamente preentrenado contra un baseline sin
tunear no es una comparación justa, y es exactamente el error que el paso 2 del
workflow existe para impedir.

⚠ Está **limitado a ≤50K filas y ≤2K columnas**. Fuera de ahí no compite.

Dicho eso: dentro de su rango y sin tiempo para tunear, es una opción real.

## La heurística que se codifica

```
¿dataset tabular normal, con tiempo para tunear?      → boosting (default)
¿grande o de regresión?                               → CatBoost primero
¿pequeño-mediano (<100K) y sin tiempo de tunear?      → foundation model o DL
¿estructura no tabular en las mismas filas
  (texto largo, imagen, secuencia)?                   → DL para esa parte
en cualquier otro caso                                → boosting
```

**DL no es el default**, y elegirlo «porque es lo moderno» es justo la decisión
que la *Rule #4* de `ml-problem-framing` desaconseja: el primer modelo simple, y
la infraestructura bien.

## Y antes que todo esto

El paso 2 del workflow manda: **la regla de negocio que ya existe** y un
`DummyClassifier` van primero. La discusión árboles-contra-redes es interesante
y es la segunda pregunta; la primera es si el modelo supera al listón que ya hay.
