---
name: schema-designer
description: >
  Diseña esquemas de base de datos en el orden correcto — entidades,
  relaciones, grano, claves, índices, migración — con ERD validado ANTES de
  escribir DDL. Use when the user says "diseña el esquema", "modela la base
  de datos", "qué tablas necesito", "diseña las tablas para X", or when a new
  feature needs new entities. El DDL resultante sigue sql-conventions; la
  migración final pasa por migration-auditor.
---

# Schema Designer

El error clásico es empezar por el `CREATE TABLE`. El esquema se diseña como
modelo, se valida, y solo entonces se convierte en SQL — cambiar un modelo en
texto cuesta minutos; cambiar una tabla en producción, una migración.

## Requisitos

- Ninguno (el ERD es texto/Mermaid, funciona en Claude Code y Cowork). Si hay
  MCP de DB read-only, úsalo para inspeccionar el esquema existente; si no,
  pide el DDL actual o los modelos del ORM.

## Pasos — en este orden, sin saltar

1. **Entidades**: lista los sustantivos que EL PEDIDO necesita persistir —
   el alcance lo fija el pedido, no el dominio. Entidades adyacentes que
   detectes van a una lista "fuera de alcance" de una línea, sin columnas ni
   relaciones. Marca lo que NO es entidad (valores calculables, catálogos
   triviales que pueden ser CHECK/enum).
2. **Relaciones**: cardinalidad (1-1, 1-N, N-M) y obligatoriedad por par.
   Toda N-M → tabla puente; si la relación tiene atributos propios (fecha,
   estado), es entidad.
3. **Grano**: por tabla, una frase de qué es UNA fila ("una fila = un pago de
   una factura"). Si no sale la frase, el diseño está mal. Objetivo de
   normalización: 3NF; desnormaliza solo con una query concreta que lo
   motive, anotándolo en el ERD ("duplicado a propósito: X, se actualiza vía Y").
4. **Transversales — pregunta UNA VEZ, antes del ERD**: ¿multi-tenant?
   (entonces `tenant_id NOT NULL` en toda tabla y dentro de toda clave
   única), ¿soft-delete o borrado real? (consistente en todo el esquema),
   ¿se requiere `created_by`/`updated_by`? Registra la respuesta y aplícala
   a todas las tablas — esto no se retrofitea barato.
5. **Claves**: PK según sql-conventions §3; claves únicas de negocio →
   `UNIQUE`; FKs con su `ON DELETE` razonado.
6. **ERD antes del DDL**: modelo en Mermaid (`erDiagram`) con entidades,
   relaciones y columnas clave. Preséntalo y espera acuerdo ANTES de escribir
   SQL. Sin usuario disponible (sesión desatendida/subagente): NO te
   detengas — entrega ERD + supuestos numerados + DDL juntos, marcado
   "DISEÑO NO VALIDADO — revisar ERD antes de ejecutar", y jamás ejecutes la
   migración tú mismo.
7. **Índices**: derivados de las queries previsibles (listados, búsquedas,
   joins), según sql-conventions §10-11.
8. **Migración**: DDL final como migración de la herramienta del proyecto
   (nunca suelto) y SIEMPRE por migration-auditor — en tablas nuevas el
   checklist se resuelve en segundos.

## Qué NO hacer

- No escribas DDL en los pasos 1-5, ni "de ejemplo".
- No modeles para requisitos hipotéticos — el esquema crece con migraciones,
  no con columnas muertas ni entidades "por si luego".
- No uses EAV/JSON como esquema por pereza de modelar; JSONB solo para datos
  genuinamente sin esquema, y dilo.

## Verifica antes de terminar

Cada tabla tiene grano en una frase, PK, FKs con constraint, las
transversales del paso 4 aplicadas de forma consistente, y el ERD precedió
al DDL. Decisión de diseño no obvia → `adr-writer`.
