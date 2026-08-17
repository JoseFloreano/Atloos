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

## Los dos matices que salieron del cuerpo (sprint 10)

**Por qué las FKs se indexan aunque «ya estén indexadas».** No lo están: Postgres
crea el índice de la PK, **no** el del lado que apunta. Sin él, los
`DELETE`/`UPDATE` del **padre** hacen scan de la tabla hija: el índice los
**protegen** a ellos y a los joins, y los **joins** por esa columna tampoco tienen por dónde entrar. Es
la excepción a «no indexes por si acaso» porque no es especulación: la
restricción ya declaró que esa columna se consulta.

**El índice parcial exige que la query repita el predicado.** Un
`WHERE deleted_at IS NULL` en el índice solo se usa si **la query debe incluir el
mismo predicado** para usarlo — literalmente, no equivalente. Es el modo de fallo típico:
se crea el índice parcial, la query filtra por otra cosa, y el índice no se toca
nunca mientras sigue costando en cada escritura.
