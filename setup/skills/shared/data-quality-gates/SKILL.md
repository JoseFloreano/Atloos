---
name: data-quality-gates
description: >
  Añade validación de datos en 4 capas (entrada, transformación, salida,
  monitoreo) a cualquier código que mueva o transforme datos — porque en
  datos "corre sin error" no significa "es correcto". Use when the user says
  "valida este pipeline", "carga estos datos", "el ETL", "importa este
  CSV/JSON a la base", "transforma estos datos", or when writing any code
  that moves data between systems. Para DISEÑAR un pipeline nuevo desde cero
  usa pipeline-designer (que invoca esta skill en su paso 5); esta aplica
  cuando el código ya existe o la carga es puntual.
---

# Data Quality Gates

Un pipeline que termina en verde puede haber cargado la mitad de las filas,
duplicado la otra mitad y llenado de nulos una columna clave. El código de
movimiento de datos se entrega CON sus validaciones, no se ofrecen después.

**Vocabulario (compartido con pipeline-designer):** una FILA inválida se
registra en rechazados y se continúa — abortando solo si los rechazos superan
el umbral de pipeline-designer (>5% de la corrida o >1.000 absolutos). Una
COMPUERTA rota (schema de entrada distinto, conteo inexplicable, integridad
de salida violada) detiene el batch SIEMPRE.

## Requisitos

- Poder ejecutar queries contra el destino (psql/dbt/MCP DB read-only). Si no
  se puede (Cowork sin conexión): entrega las queries de verificación listas
  para copiar, pide el resultado, y NO des la carga por validada hasta verlo.

## Las capas

Las capas 1-3 aplican a TODO movimiento de datos, incluido el one-off (ahí
son solo asserts + dos queries de verificación). La capa 4 SOLO a jobs
recurrentes — ponérsela a un script de una corrida es sobre-ingeniería.

1. **Entrada** (antes de procesar nada): schema esperado — columnas y tipos,
   falla rápido si la fuente cambió; decisión explícita de nulos por columna
   (rechazar/default/permitir); duplicados sobre la clave natural — en cargas
   por upsert se absorben y solo se reportan, en cargas append son
   bloqueantes.
2. **Transformación**: `filas_out` explicable respecto a `filas_in` (el join
   que multiplica o el filtro que vacía se detectan aquí); rangos de valores
   (montos no negativos, fechas posibles, categorías del catálogo).
3. **Salida** (ANTES del commit): integridad referencial — toda FK resuelve;
   invariantes de negocio (ej. suma de pagos ≤ total de la factura),
   ejecutadas dentro de la transacción para poder abortarla. En cargas por
   lotes con commits intermedios: la compuerta rota detiene los lotes
   siguientes y registra hasta dónde quedó — la idempotencia permite reanudar.
4. **Monitoreo** (solo recurrentes): frescura, volumen contra la mediana
   histórica, dónde registrar las corridas, y el canal que hace que una alerta
   llegue sola. Los cuatro, con sus defaults: `references/monitoreo.md`.

## Cómo aplicarlo

- Con dbt: capas 1-3 son tests (not_null, unique, relationships,
  accepted_values + custom) generados JUNTO al modelo.
- Con Python/SQL a mano: asserts/queries en el propio script, que abortan la
  transacción si una compuerta falla.

## Verifica antes de terminar

Muestra las compuertas con números reales ("10,432 cargadas, 0 duplicados,
3 rechazadas por monto negativo — listado en `_rejected_rows`"). Un pipeline
sin sus validaciones está entregado a medias.
