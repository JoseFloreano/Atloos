# Notas por motor — migration-auditor

Complemento del checklist de 6 puntos. Casos que cambian el veredicto según
el motor. Verificado contra documentación oficial (ago 2026): postgresql.org
/docs, dev.mysql.com/doc, sqlite.org.

## PostgreSQL

**Índices**
- `CREATE INDEX CONCURRENTLY`: no bloquea escrituras, pero (a) NO puede
  correr dentro de transacción — Alembic:
  `with op.get_context().autocommit_block():`; (b) hace dos escaneos y
  **espera a que terminen todas las transacciones abiertas** que puedan usar
  la tabla: con transacciones largas o `idle in transaction`, se cuelga
  indefinidamente. "CONCURRENTLY = seguro" es condicional a no tener
  transacciones largas. Si falla, deja un índice `INVALID`: dropearlo o
  `REINDEX INDEX CONCURRENTLY` (PG 12+).
- `UNIQUE` online: `ADD CONSTRAINT ... UNIQUE` directo construye el índice
  bajo ACCESS EXCLUSIVE. Patrón seguro: `CREATE UNIQUE INDEX CONCURRENTLY`
  → `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE USING INDEX`.

**Columnas y tipos**
- `ADD COLUMN ... DEFAULT <constante>` es instantáneo desde PG 11; con
  default volátil (`now()`, `gen_random_uuid()`), columnas identity o
  generadas, SÍ reescribe tabla e índices.
- Toda reescritura necesita ~2× el espacio en disco (copia temporal de tabla
  + índices): un `int→bigint` de 500 GB puede llenar el disco.
- Cambio binario-compatible (`varchar(50)`→`varchar(100)`, `varchar`→`text`)
  no reescribe — pero `ALTER TYPE` toma ACCESS EXCLUSIVE aunque sea breve:
  combinar con `lock_timeout`.
- `int→bigint` arrastra dependencias: la secuencia/identity y las columnas
  FK de las tablas hijas deben migrar coordinadamente. El patrón "columna
  paralela + backfill por lotes + rename" incluye a las referenciantes.
- `SET NOT NULL` seguro en dos pasos: `ADD CONSTRAINT ... CHECK (col IS NOT
  NULL) NOT VALID` → `VALIDATE CONSTRAINT` → `SET NOT NULL` (PG 12+ usa el
  check y no re-escanea). Ojo con los locks: `VALIDATE` toma SHARE UPDATE
  EXCLUSIVE **durante todo el escaneo** — es seguro porque el lock es débil
  (no frena DML), NO porque sea breve; sí bloquea otros DDL/VACUUM mientras
  dura. Los locks fuertes-pero-breves son los del ADD CONSTRAINT y el SET
  NOT NULL final.

**Foreign keys**
- `ADD FOREIGN KEY` directo valida bajo SHARE ROW EXCLUSIVE **en las DOS
  tablas** — congela las escrituras de la tabla referenciada (típicamente la
  caliente: `users`) durante toda la validación. "Solo afecta a la tabla
  hija" es falso. Variante online: `ADD CONSTRAINT ... FOREIGN KEY ... NOT
  VALID` (lock breve) → `VALIDATE CONSTRAINT` (lock débil, largo).

**Operación**
- `lock_timeout` corto (ej. `2s`) al inicio de todo DDL en producción: mejor
  fallar y reintentar que encolarse tras un lock y frenar todo el tráfico
  que llega detrás. Por sesión, no global.
- Enums: `ALTER TYPE ... ADD VALUE` no corría en bloque de transacción antes
  de PG 12, y el valor nuevo no es usable hasta el commit — trampa clásica
  en Alembic.
- **Réplicas**: rewrites y backfills masivos generan WAL proporcional a lo
  tocado → lag de réplicas físicas y disco lleno en el primario si un slot
  se atrasa; trocear el backfill con pausas si el lag crece. Con replicación
  lógica el DDL NO se replica: aplicar coordinado en publisher y suscriptores.

## MySQL / MariaDB (InnoDB)

- Orden de preferencia: **`ALGORITHM=INSTANT`** primero (ADD COLUMN desde
  8.0.12 — es el default —, DROP COLUMN desde 8.0.29; límite de 64
  row-versions que al agotarse fuerza rebuild), luego `INPLACE`, último
  `COPY`. Pedir siempre `ALGORITHM=.../LOCK=NONE` explícitos: si la
  operación no los soporta, FALLA con error en vez de degradar en silencio
  a tabla bloqueada.
- Cambios de tipo: casi siempre COPY (sin DML concurrente). Matices: extender
  VARCHAR es INPLACE solo si los length-bytes no cambian (0-255 → 0-255, o
  ≥256 → mayor); cruzar la frontera de 256 bytes es COPY; añadir valores AL
  FINAL de un ENUM/SET es INSTANT.
- Para tablas grandes con COPY inevitable: gh-ost o pt-online-schema-change.
- Todo DDL hace **COMMIT implícito** de la transacción activa (rompe
  herramientas que envuelven migraciones en transacción) y encola un
  metadata lock exclusivo tras las transacciones largas — la misma cola de
  locks descrita para Postgres, incluso con INSTANT.
- DDL atómico POR SENTENCIA desde MySQL 8.0 (antes: archivos de metadata con
  commits intermedios); en MariaDB desde 10.6.1. Una migración de varias
  sentencias sigue sin ser atómica en conjunto → rollback documentado por
  sentencia.
- `utf8mb4`: el límite de longitud de índice se mide en BYTES (767 u
  3072 según row format) — cambiar charset de una columna indexada puede
  excederlo (~191 chars con prefijo en utf8mb4).

## SQLite

- `ALTER TABLE` solo soporta RENAME (tabla/columna), ADD COLUMN y DROP
  COLUMN (3.35+, y falla si la columna es PK/UNIQUE, indexada o referida por
  constraint/trigger/vista/columna generada). Todo lo demás es el patrón de
  12 pasos de sqlite.org: crear tabla nueva → copiar → dropear vieja →
  renombrar. NO uses el atajo de "renombrar la vieja primero": desde
  3.25/3.26 corrompe referencias (anti-patrón que generan ORMs viejos).
- `PRAGMA foreign_keys=OFF` es **no-op dentro de una transacción**: debe
  ejecutarse ANTES del `BEGIN`. Una herramienta que envuelve la migración
  entera en transacción deja las FKs activas en silencio y el patrón de 12
  pasos falla o dispara acciones referenciales. Cerrar siempre con `PRAGMA
  foreign_key_check`.
- FKs desactivadas por defecto: confirmar `PRAGMA foreign_keys=ON` en cada
  conexión, o la integridad referencial es ilusoria.
- Un solo escritor a la vez; en modo WAL las LECTURAS siguen durante la
  migración (en rollback-journal, no). Aun así: migrar al arranque de la
  app, no en caliente.

## Transversal

DDL y backfill masivo de datos: SIEMPRE separados (DDL rápido primero;
backfill por lotes con commits intermedios después). En PG es práctica (el
lock del DDL se retiene hasta el commit de su transacción); en MySQL es
forzoso (el DDL commitea la transacción por ti).
