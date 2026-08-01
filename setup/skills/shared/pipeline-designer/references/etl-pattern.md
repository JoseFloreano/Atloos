# Patrón ETL canónico — esqueleto anotado

Ejemplo de referencia: API paginada → PostgreSQL (psycopg 3). Es un PATRÓN,
no código a pegar: adapta nombres, clave natural y umbrales. Cada bloque
mapea a un paso del SKILL.md. Corregido tras auditoría adversarial (doc 06):
el cursor se persiste en la MISMA transacción que su batch, los umbrales se
miden sobre el acumulado y la conexión usa autocommit explícito.

```python
import os, time, random, logging
import httpx, psycopg

API = "https://api.ejemplo.com/v1/orders"
UMBRAL_RECHAZO = 0.05   # sobre el ACUMULADO de la corrida, no por página
MAX_RECHAZOS   = 1000   # techo absoluto: 4.9% de 10M filas no es "todo bien"
MIN_MUESTRA    = 200    # no juzgar la fuente con menos de N filas vistas

log = logging.getLogger("pipeline.orders")

# Conexión con autocommit=True: así `conn.transaction()` es el ÚNICO límite
# transaccional real. Con el default (False), cualquier query previa abre una
# transacción implícita y transaction() degrada a SAVEPOINT — y nada se
# commitea nunca. (Docs psycopg 3: basic/transactions.html)
conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)

# ---- Paso 2: extracción — generador SIN efectos secundarios --------------
def extraer(conn, session):
    cursor = leer_estado(conn, "orders_cursor")   # None en la primera corrida
    while True:
        resp = con_backoff(session, API, params={"after": cursor, "limit": 100})
        data = resp.json()
        if not isinstance(data.get("items"), list):   # schema drift del sobre
            raise RuntimeError("envelope inesperado de la API — fuente rota")
        siguiente = data.get("next_cursor")
        yield data["items"], siguiente   # página + cursor que la CUBRE
        if not siguiente:
            break
        cursor = siguiente   # solo en memoria — se persiste al cargar (cargar())

# ---- Paso 2: rate limiting + reintentos de 5xx y red ----------------------
REINTENTABLES = {429, 500, 502, 503, 504}

def con_backoff(session, url, params, max_intentos=5):
    for intento in range(max_intentos):
        ultimo = intento == max_intentos - 1
        try:
            resp = session.get(url, params=params)
        except httpx.TransportError:          # timeout, reset, DNS
            if ultimo:
                raise
            time.sleep((2 ** intento) + random.random())
            continue
        if resp.status_code in REINTENTABLES:
            if ultimo:
                resp.raise_for_status()
            try:
                espera = float(resp.headers.get("Retry-After", ""))
            except ValueError:                # ausente o formato HTTP-date
                espera = (2 ** intento) + random.random()
            time.sleep(min(espera, 60))
            continue
        resp.raise_for_status()
        return resp

# ---- Paso 3: fallos parciales — umbral sobre el acumulado -----------------
def transformar(filas, stats):
    ok, rechazadas = [], []
    for f in filas:
        try:
            ok.append(validar(f))   # validar() normaliza sus errores a ValueError
        except (ValueError, KeyError, TypeError) as e:
            rechazadas.append((f.get("id"), str(e)))
            log.warning("rechazada %s: %s", f.get("id"), e)
    stats["ok"] += len(ok)
    stats["rech"] += len(rechazadas)
    total = stats["ok"] + stats["rech"]
    if stats["rech"] > MAX_RECHAZOS or (
            total >= MIN_MUESTRA and stats["rech"] / total > UMBRAL_RECHAZO):
        raise RuntimeError(f"{stats['rech']}/{total} rechazos — fuente rota")
    return ok, rechazadas

# ---- Paso 4: upsert por clave natural = idempotencia ----------------------
# El WHERE exige updated_at NOT NULL y que la fuente lo actualice SIEMPRE.
# IS DISTINCT FROM permite aplicar correcciones con el MISMO timestamp y hace
# que la segunda corrida toque 0 filas. Si la fuente no tiene updated_at
# confiable: elimina la condición <= y deja solo IS DISTINCT FROM (última
# escritura gana; sigue siendo idempotente).
SQL_UPSERT = """
INSERT INTO orders (external_id, customer_id, amount, status, updated_at)
VALUES (%(external_id)s, %(customer_id)s, %(amount)s, %(status)s, %(updated_at)s)
ON CONFLICT (external_id) DO UPDATE
SET customer_id = EXCLUDED.customer_id,
    amount      = EXCLUDED.amount,
    status      = EXCLUDED.status,
    updated_at  = EXCLUDED.updated_at
WHERE orders.updated_at IS NULL
   OR (orders.updated_at <= EXCLUDED.updated_at
       AND (orders.customer_id, orders.amount, orders.status)
           IS DISTINCT FROM (EXCLUDED.customer_id, EXCLUDED.amount, EXCLUDED.status));
"""
# OJO si optimizas: executemany ejecuta statements separados (misma clave dos
# veces en el batch NO falla). Un solo INSERT multi-VALUES o COPY+merge SÍ
# falla con "cardinality violation" ante claves repetidas — deduplica antes:
#   {f["external_id"]: f for f in sorted(filas, key=lambda x: x["updated_at"])}.values()

# ---- Paso 2+4: carga ATÓMICA — filas + rechazos + cursor + verificación ---
def cargar(conn, filas, rechazadas, cursor_siguiente):
    with conn.transaction():   # BEGIN/COMMIT reales (autocommit=True)
        with conn.cursor() as cur:
            cur.executemany(SQL_UPSERT, filas)
            if rechazadas:
                cur.executemany(
                    "INSERT INTO _rejected_rows (pipeline, source_id, reason) "
                    "VALUES ('orders', %s, %s)", rechazadas)
            verificar_salida(cur, len(filas))   # capa 3 ANTES del commit:
                                                # si falla, TODO revierte
            if cursor_siguiente is not None:
                guardar_estado(cur, "orders_cursor", cursor_siguiente)
    # Crash en cualquier punto ⇒ o batch+cursor commiteados JUNTOS, o ninguno.
    # La re-corrida re-descarga a lo sumo la última página y el upsert la
    # absorbe (at-least-once + idempotencia = sin huecos ni duplicados).

# ---- Loop principal — donde vive el orden correcto ------------------------
def correr(conn, session):
    stats = {"ok": 0, "rech": 0}
    try:
        for filas, siguiente in extraer(conn, session):
            ok, rechazadas = transformar(filas, stats)
            cargar(conn, ok, rechazadas, siguiente)
        registrar_corrida(conn, stats, "success")   # capa 4
    except Exception:
        registrar_corrida(conn, stats, "failed")
        raise

def registrar_corrida(conn, stats, estado):
    conn.execute(
        "INSERT INTO _pipeline_runs (pipeline, run_at, rows_loaded, "
        "rows_rejected, status) VALUES ('orders', now(), %s, %s, %s)",
        (stats["ok"], stats["rech"], estado))
```

Tablas auxiliares (sus `CREATE TABLE` van en una migración — sql-conventions
§6 y §12): `_pipeline_state (key, value)` · `_rejected_rows (pipeline,
source_id, reason, at timestamptz DEFAULT now())` · `_pipeline_runs
(pipeline, run_at, rows_loaded, rows_rejected, status)`.

## Los 4 caminos feos que hay que probar (paso 7)

| Escenario | Resultado esperado |
|-----------|--------------------|
| La API devuelve una página repetida | upsert la absorbe (statements separados vía executemany) |
| Registro sin campo obligatorio | va a `_rejected_rows`, el batch sigue (umbral sobre acumulado) |
| Corte a mitad de batch (matar el proceso) | filas y cursor reverten JUNTOS; reanuda re-bajando ≤1 página, absorbida por upsert |
| Segunda corrida completa inmediata | 0 cambios netos (WHERE con IS DISTINCT FROM) |

## Límites del patrón — decidir en el contrato (paso 1)

- **Hard deletes**: el cursor incremental nunca los ve → el destino acumula
  zombis y las 4 pruebas pasan en verde igual. Mitigación: flags/eventos de
  borrado, reconciliación periódica de conjuntos de `external_id`, o full
  refresh programado (p. ej. semanal) como red de seguridad.
- **Timezones**: `updated_at` = `timestamptz` en destino y zona declarada en
  la fuente; comparar naive vs aware corrompe el WHERE del upsert en silencio.
- **Late-arriving data / empates de cursor**: orden de commit ≠ orden de
  timestamp en la fuente. Extrae desde `cursor − ventana de solape`
  (5-15 min) — el upsert absorbe el retrabajo — o usa cursor compuesto
  `(updated_at, id)`. El `next_cursor` opaco de la API debe ser estable y
  sin huecos; si no lo garantiza, cursor propio.
- **Backfill inicial**: la primera corrida (`cursor=None`) es un full crawl —
  dimensiona rate limits, corre fuera de pico, considera COPY a staging +
  merge para el volumen inicial.
- **Primera corrida**: `params={"after": None}` funciona porque httpx omite
  parámetros None — comportamiento de librería, no de HTTP; verifica con tu
  cliente.

## Portabilidad del upsert

- **MySQL**: `INSERT ... ON DUPLICATE KEY UPDATE` no acepta WHERE — mover el
  anti-pisado a expresiones: `updated_at = IF(VALUES(updated_at) >=
  updated_at, VALUES(updated_at), updated_at)` (ídem por columna).
- **SQLite ≥ 3.24**: soporta `ON CONFLICT ... DO UPDATE ... WHERE` como
  Postgres.
- Resto de diferencias por motor: `references/engine-notes.md` de
  migration-auditor.
