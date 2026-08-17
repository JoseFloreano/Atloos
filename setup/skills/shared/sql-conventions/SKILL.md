---
name: sql-conventions
description: >
  Convenciones SQL del setup: motor por defecto, tipos, naming, constraints,
  indexado y regla de migraciones — para que todo SQL generado salga con los
  mismos estándares. Use when the user says "crea una tabla", "escribe el SQL
  para", "agrega una columna", "haz una query", or before generating ANY
  DDL/DML in a project with database. Para diseñar un esquema completo usa
  `schema-designer`; para revisar una migración usa `migration-auditor`.
  Aquí solo viven convenciones.
---

# SQL Conventions

Nadie más conoce estas convenciones: aplícalas siempre, sin que te las pidan.
Las del proyecto (CLAUDE.md, docs) ganan sobre estas.

## Motor y dialecto

- Por defecto: **PostgreSQL**. Otro motor → dilo explícitamente y adapta el
  dialecto completo — nunca mezcles sintaxis de dos motores.
- Motor no claro → pregunta ANTES de escribir DDL; en sesión desatendida,
  asume PostgreSQL y márcalo como supuesto.

## Tipos

1. Fechas-hora: **`timestamptz`** siempre (UTC en la base; la zona es
   presentación). `timestamp` sin zona solo con justificación escrita.
2. Dinero y cantidades exactas: **`numeric`**, nunca `float`/`real`. Texto:
   `text`, salvo límite de negocio real (entonces `varchar(n)` + el porqué).
3. PK por defecto: `id bigint GENERATED ALWAYS AS IDENTITY` (no `serial`, es
   legado). UUID solo si los IDs nacen fuera de la base o se exponen
   públicamente — y dilo. No mezcles estrategias en un mismo esquema.

## Naming

4. Todo en `snake_case`, tablas en plural (`invoices`), columnas en singular.
   Timestamps con sufijo `_at`; booleanos con `is_`/`has_`.
5. FK: `<tabla_singular>_id` (`customer_id`). Con varias FKs a la misma tabla
   o autorreferencia, nombra por ROL: `manager_id`, `billing_address_id`.
6. Tablas puente: ambos nombres en orden alfabético (`courses_students`).
   Tablas de infraestructura de datos con prefijo `_` (`_pipeline_runs`) —
   salen por migración como cualquier otra.
7. Índices/constraints con nombre explícito y predecible:
   `ix_/fk_/ck_/uq_<tabla>_<detalle>` — nunca el autogenerado.

## Constraints

8. Toda FK como constraint, con `ON DELETE` decidido a propósito: `RESTRICT`
   explícito por defecto (ojo: el default del motor es `NO ACTION`);
   `CASCADE` solo para hijos que no viven sin el padre; `SET NULL` para
   referencias opcionales.
9. `NOT NULL` por defecto; nullable es la excepción que se justifica. Reglas
   de dominio simples → `CHECK`; defaults en la base cuando no dependen de
   lógica de negocio.

## Indexado

10. FKs indexadas por defecto — **Postgres NO las indexa solo**. Fuera de eso,
    no indexes "por si acaso": cada índice cuesta en cada escritura.
11. Índice compuesto: columnas de IGUALDAD antes que las de rango. Índice
    parcial para subconjuntos estables. El porqué de las dos, y las
    excepciones declarables: `references/indexado.md`.

## Migraciones

12. Nunca DDL suelto: todo cambio de esquema sale por la herramienta de
    migraciones del proyecto; si no hay, propón una. Excepción: entorno
    desechable o análisis one-off — DDL directo permitido, marcado "NO apto
    para producción".
13. Toda migración pasa por `migration-auditor` ANTES de ejecutarse.
    ⚠ **Instrucción, no garantía: ningún hook impone este paso.** Dilo, en vez
    de suponer una red que no existe.

## Verifica antes de terminar

¿Corre en el motor declarado? ¿Tipos según §1-3? ¿FKs con constraint e índice
(o excepción declarada)? ¿DDL fuera de migración? — corrígelo.
