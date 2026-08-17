# La cláusula de no-pérdida

**Todo frente cuyo criterio de aceptación sea NUMÉRICO —palabras, líneas,
tamaño, tiempo, cobertura— lleva al lado un criterio de NO-PÉRDIDA, y el frente
entrega LAS DOS medidas.**

Un número se cumple destruyendo; dos, no.

## De dónde sale

Sprint 4, 2026-08-14. Un frente mecánico recibió siete skills que bajar de
tamaño, con el criterio escrito con toda precisión: **las siete por debajo de
460 palabras, `description` intacta, arnés en exit 0**. Los acertó todos. Su
trabajo se descartó entero.

> **No extrajo: comprimió y borró.** 102 líneas del cuerpo sin destino en
> ninguna `references/`.

El diagnóstico que importa no es el del modelo:

> **La lección no es «el modelo barato no sirve»: es que el criterio de
> aceptación era numérico, y un criterio numérico se cumple destruyendo.**

El bloque 5 manda elegir modelo y presupuesto. El bloque 7 manda escribir cuándo
está hecho. **Ninguno mandaba comprobar que lo que salió de un sitio llegó a
otro** — y eso es un agujero del contrato, no del agente. Con el criterio así
escrito, borrar era una forma perfectamente válida de cumplirlo.

## Qué se escribe en el despacho

Al lado del criterio numérico del bloque 7, y con el mismo formato —estado final
medible más el comando que lo prueba:

```
HECHO cuando  setup/scripts/py setup/scripts/tests/test-skill-catalog.py [repo] da exit 0
              con las siete por debajo de 460 palabras
Y ADEMÁS      setup/scripts/py setup/scripts/no-perdida.py <dir> --base <sha> [repo] no deja
              ninguna palabra desaparecida sin justificar, UNA POR UNA, en el
              reporte
```

Las dos medidas viajan en el reporte del bloque 7. **Una sola no vale**: es
precisamente la configuración que ya falló.

## Cómo se mide, y por qué así

`setup/scripts/no-perdida.py`. Compara el **multiconjunto de palabras de
contenido** del cuerpo ANTES contra el del cuerpo DESPUÉS **más todos sus
destinos**, y reporta las palabras cuya cuenta cae a cero, cada una con la frase
de la que salió.

Se probaron tres métodos sobre el mismo caso real —las 7 skills del sprint 4— y
el tercero es el único que decide:

| Método | Resultado |
|---|---|
| línea a línea con puntuación | **21 falsos positivos** por reajustes de línea |
| 6-gramas de palabras | **160 «sin destino»**, casi todo ruido de junta |
| **multiconjunto de palabras de contenido** | **3 palabras de 1550** · el que decide |

La razón es estructural: **mover texto no cambia el multiconjunto**. Los otros
dos miden posición, y la posición es exactamente lo que una extracción legítima
cambia a propósito.

## ⚠ Cero NO es el criterio de aceptación

Reformular cambia palabras. Quien exija cero acabará prohibiendo reescribir, o
—peor— maquillando la reescritura para que salga el número: el mismo defecto,
un piso más arriba.

**El criterio es que cada desaparecida se justifique, una por una**, mirando la
frase de la que salió. Por eso el script las imprime con su contexto y por eso
su exit 1 significa *«hay N que mirar»*, no *«está mal»*.

> En el sprint 4 las tres desaparecidas —`contradicciones`, `probaron`,
> `reescriben`— resultaron ser **ideas que sobrevivieron con mejor redacción y
> más evidencia**. Ese es el resultado bueno, y solo se ve mirándolas.

## Dónde NO aplica

Cuando el criterio numérico mide algo que **se produce**, no algo que se
transforma: «que la cobertura suba a 80 %», «que la suite baje de 300 s». Ahí no
hay un antes cuyo contenido pueda perderse. La cláusula es para los criterios
que se cumplen **quitando**: acortar, mover, refactorizar, consolidar, migrar.
