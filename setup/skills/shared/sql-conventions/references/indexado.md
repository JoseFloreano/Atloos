# Indexado — las excepciones declarables

Complemento del §10 del cuerpo. La regla es *FKs indexadas por defecto*; esto
es lo que puedes **declarar** para no indexar una, y el porqué.

## Por qué la regla existe

PostgreSQL crea un índice para una PK y para un `UNIQUE`, pero **no para una
FK**. La consecuencia se paga en dos sitios y ninguno de los dos es la query
obvia:

1. **`DELETE`/`UPDATE` en la tabla PADRE.** Para comprobar que ninguna fila
   hija apunta al registro que se toca, el motor escanea la tabla hija entera.
   Con la hija grande, un borrado del padre pasa de milisegundos a minutos.
2. **Los joins** que recorren la relación en sentido hijo → padre.

## Las dos excepciones que puedes declarar

- **Tablas catálogo diminutas** (<~1k filas y estables). El escaneo secuencial
  es más barato que el índice, y el planificador lo elegirá de todos modos.
- **FKs a padres inmutables que ninguna query usa** para filtrar. Si el padre
  nunca se borra ni se actualiza, el coste 1 no existe; si además ninguna
  query filtra por esa columna, el índice solo cuesta escrituras.

**Declararlas es parte del trabajo, no una opción.** Escribe la razón junto a
la migración: la excepción no declarada es indistinguible del olvido, y quien
la lea dentro de seis meses añadirá el índice "por si acaso" — que es justo lo
que la regla prohíbe.

## Fuera de eso: no indexes por si acaso

Cada índice se paga en **cada** `INSERT`, `UPDATE` y `DELETE` de la tabla, más
espacio en disco y más trabajo de vacuum. Un índice que ninguna query usa es
coste puro. Si no puedes nombrar la query que lo motiva, no lo crees — es el
punto 4 del checklist de `migration-auditor`.
