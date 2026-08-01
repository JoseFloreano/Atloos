# DeepSeek para Graphiti — resumen simple

*Basado en `docs/arquitectura-memoria/08-GRAPHITI-DEEPSEEK-COSTO.md`, pruebas del 2026-08-01.*

## La pregunta que se estaba investigando

Graphiti (el sistema de memoria en grafo, todavía sin desplegar) necesita un
modelo de IA para "leer" cada nota y sacar de ahí entidades y relaciones.
Hoy el plan por defecto usa OpenAI, que cuesta ~$6 USD/mes. La pregunta era:
¿se puede usar DeepSeek en su lugar y ahorrar, sin perder calidad?

## Resultado corto

**Sí funciona, y es mucho más barato** (~$0.25/mes vs ~$6/mes, unas 24 veces
menos). Pero la prueba encontró **3 problemas de calidad** que hay que vigilar,
y todavía falta el paso más importante: comparar a DeepSeek contra OpenAI
lado a lado con las mismas notas, para saber si esos problemas son culpa de
DeepSeek o de Graphiti en general.

## Qué se probó de verdad

El 2026-08-01 se tomaron 8 notas reales del vault (2 ADRs, 2 bugs, 2
convenciones, 2 features) y se procesaron con DeepSeek en un entorno de
prueba aislado — no tocó los datos reales del vault.

- Las 8 notas se procesaron sin errores ni fallos.
- El costo medido confirmó la proyección: ~$0.25/mes a un ritmo de 200
  notas/mes.
- La velocidad y el "no-thinking" (que el modelo no gaste de más pensando
  antes de responder) funcionaron como se esperaba.

## Los 3 problemas encontrados

1. **Idioma mezclado** — la mitad de las notas generaron resúmenes en
   inglés, aunque todo el vault está en español. Si esto pasa seguido, no
   es aceptable.
2. **Ruido en notas cortas** — una convención de solo dos frases generó 9
   "entidades" distintas, la mayoría redundantes, y ninguna relación entre
   ellas. Demasiado ruido para el contenido real.
3. **Contenido perdido** — una nota se mezcló ("dedup") con una nota
   anterior que no tenía que ver, y su contenido específico no quedó
   reflejado en el grafo.

Importante: **no se sabe si estos problemas son de DeepSeek o de Graphiti**
en general — para saberlo hace falta correr la misma prueba con OpenAI y
comparar.

## Qué falta antes de decidir algo en firme

1. Repetir la prueba con OpenAI como línea base y comparar resultados.
2. Si DeepSeek sale bien parado en esa comparación, activarlo en el servidor
   real y vigilar la primera semana en producción.

## Veredicto actual

**"Adoptar con reservas"** — es viable y muy barato, pero no es un cambio
definitivo todavía. Además, Graphiti en sí sigue sin desplegarse en
producción por una decisión anterior (pospuesta), así que esto es
investigación preparatoria, no algo que ya esté en uso.
