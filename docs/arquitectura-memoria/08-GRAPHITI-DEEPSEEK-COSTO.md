# Graphiti + DeepSeek: compatibilidad, configuración y ahorro de tokens
## ¿Sirve DeepSeek como LLM de extracción del grafo, y cuánto cuesta de verdad?

> **Fecha:** 2026-08-01 (todo verificado ese día; repo getzep/graphiti v0.29.3 clonado y leído)
> **Pregunta:** abaratar la extracción de Graphiti (hoy OpenAI, H7) sin romper calidad. Complementa el doc 03 (Graphiti/FalkorDB) y la evaluación de rutas baratas (Gemini pospuesto, Groq).
> **Veredicto:** compatible SÍ, con dos matices; costo con palancas ≈ **$0.40-0.60 USD/mes** (200 episodios) vs ~$6 del mini de OpenAI. Ahorro absoluto ~$5/mes — vale solo si el A/B de calidad sale bien y se resuelve el modo thinking.

---

## 1. Compatibilidad (verificada en código)

- El README de Graphiti nombra a **DeepSeek explícitamente** como proveedor soportado vía `OpenAIGenericClient` (cualquier endpoint OpenAI-compatible `/v1`), con la advertencia general: funciona mejor con servicios que soporten Structured Output; otros "may result in incorrect output schemas and ingestion failures".
- **Matiz 1 — structured output degradado:** DeepSeek solo soporta `response_format: json_object` (NO `json_schema`; verificado en su referencia de API). Graphiti lo contempla: `structured_output_mode="json_object"` inyecta el schema Pydantic en el prompt y reintenta ante fallos de validación (4 intentos, tenacity). Sus propios docs advierten "the API may occasionally return empty content" — episodios ocasionalmente fallidos son esperables. Un peldaño menos fiable que OpenAI.
- El **MCP server** detecta base_url ≠ api.openai.com y cambia solo a `OpenAIGenericClient`; el modo se controla con `${LLM_STRUCTURED_OUTPUT_MODE}`.
- Issues de DeepSeek en getzep/graphiti: búsqueda full-text bloqueada desde el sandbox (no verificable al 100%); vía web no apareció ninguno dedicado. Los fallos reportados del camino genérico (#1007, #912, #1204) se concentran en modelos chicos/locales.

## 2. Modelo y el matiz que importa

- **DeepSeek V4** (2026-04-24): `deepseek-v4-pro` (1.6T MoE/49B activos) y `deepseek-v4-flash` (284B/13B activos), contexto 1M. Los alias `deepseek-chat`/`deepseek-reasoner` se **deprecaron el 2026-07-24**.
- **Recomendado: `deepseek-v4-flash` en NO-thinking** — extracción de entidades no necesita razonamiento largo; thinking multiplica output y latencia en las 4-8 llamadas por episodio.
- **Matiz 2 — thinking por defecto:** V4 arranca con thinking activado; se apaga con `extra_body={"thinking":{"type":"disabled"}}`, que Graphiti **no envía hoy** (verificado en `openai_generic_client.py`). Opciones: (a) probar si el alias `deepseek-chat` sigue vivo como no-thinking (curl antes de decidir — el atajo), (b) subclase de ~10 líneas de `OpenAIGenericClient` (uso como librería), (c) aceptar thinking y perder la mitad del ahorro.
- Los tokens de razonamiento se facturan como output normal ($0.28/M); mismo precio por token en ambos modos (detalle exacto V4 en docs oficiales: parcialmente no verificable).

## 3. Embeddings y reranker (mezcla de proveedores)

- **DeepSeek NO ofrece embeddings** (confirmado en su referencia de API). Graphiti permite mezclar: LLM DeepSeek + embedder OpenAI `text-embedding-3-small` (~centavos/mes) o local (Ollama nomic-embed-text, con reserva de calidad de retrieval).
- **Reranker: NO usar DeepSeek.** `OpenAIRerankerClient` usa `logit_bias` con IDs de token del tokenizer de OpenAI — en el de DeepSeek apuntan a tokens arbitrarios. Dejarlo en OpenAI (gpt-4.1-nano, max_tokens=1, costo ínfimo) o `BGERerankerClient` local gratis. Con FalkorDB solo afecta búsquedas, no `add_episode`; a nuestra escala también es razonable no rerankear.
- ⚠ **Trampa del MCP server:** en `mcp_server/config/config.yaml`, LLM y embedder comparten `${OPENAI_API_URL}`/`${OPENAI_API_KEY}` — apuntar solo la variable a DeepSeek ROMPE el embedder. Hay que separar variables en el yaml (config abajo). Y `CrossEncoderFactory` hereda el provider del LLM: el reranker se iría a DeepSeek solo — o se ajusta factories.py, o se deja caer al BGE local.

## 4. Precios oficiales (api-docs.deepseek.com/quick_start/pricing, 2026-08-01)

| Modelo | Input cache hit | Input cache miss | Output |
|---|---|---|---|
| deepseek-v4-flash | **$0.0028/M** | $0.14/M | $0.28/M |
| deepseek-v4-pro | $0.003625/M | $0.435/M | $0.87/M |
| gpt-5.4-mini (referencia, fuente terciaria — verificar en openai.com) | $0.075/M | $0.75/M | $4.50/M |

## 5. Palancas de ahorro de tokens (fase 2, verificadas en código v0.29.3)

| Palanca | Ahorro | Cómo | Nota |
|---|---|---|---|
| **1. Thinking OFF** | La mayor: 2-5× del gasto total | Alias `deepseek-chat` si vive, o subclase con `extra_body` | Sin esto, el ahorro se esfuma |
| **2. Context caching de DeepSeek** | ~25-35% del input (hit = 50× más barato) | NADA — automático y gratis | Los prompts de Graphiti resultaron **cache-friendly**: bloques estáticos (system + reglas + entity types) van PRIMERO, y en modo json_object el schema se añade AL FINAL del último mensaje → no rompe el prefijo. TTL "horas a días" |
| **3. Recortar episodios previos** | Sube la fracción cacheable a ~45-55% del input | `add_episode(..., previous_episode_uuids=[2-3 uuids])` en vez del default (10) | Trade-off: peor resolución de correferencias y dedup |
| **4. Sin entity_types con atributos** | Elimina 1 llamada LLM POR NODO | No pasar entity_types con campos | Verificado: `node_operations.py` salta la llamada si no hay model_fields |
| **5. add_episode_bulk para backfills** | ~20-40% (estimación, sin cifra oficial) | Lotes (cron nocturno) | Los docs de Zep dicen que bulk pierde invalidación de aristas — **desactualizados**: el código v0.29.3 SÍ la hace |
| Muertas/irrelevantes | — | — | **Off-peak ya NO existe** en V4 (tarifa plana verificada; el 50-75% nocturno era era V3/R1). `MAX_REFLEXION_ITERATIONS` es vestigio (nada la lee). `small_model` no ayuda (no hay tier bajo flash). `update_communities` ya es False. Tamaño de episodio deja de importar para costo con caching — prioriza calidad (1 tema, 1-4K tokens) |

Inventario real de llamadas por episodio (v0.29.3): extract_nodes (1) + extract_edges (1) + dedupe condicional (0-1) al modelo principal; timestamps por arista, resolve_edge y resúmenes de nodos en lotes de 30 al small_model. **Típico sin tipos custom: 4-8 llamadas.**

## 6. Costo estimado — 200 episodios/mes (ESTIMACIÓN, supuestos: 6 llamadas, ~24K in / 2.5K out por episodio)

| Escenario | $/mes |
|---|---|
| Flash con thinking ON (default si no lo apagas) | ~$2-6 |
| Flash no-thinking | ~$0.82 |
| + caching caliente | **~$0.60** |
| + previos limitados a 3 | **~$0.40** |
| Referencia gpt-5.4-mini | ~$6 |
| Embeddings (siguen en OpenAI) | ~$0.02-0.05 |

Verificar la fracción cacheable real con `prompt_cache_hit_tokens` en las respuestas del API (DeepSeek lo reporta por request).

## 7. Config concreta

**Librería (FalkorDB local):**

```python
llm_client = OpenAIGenericClient(
    config=LLMConfig(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        model="deepseek-v4-flash",       # probar antes si "deepseek-chat" sigue vivo (no-thinking)
        small_model="deepseek-v4-flash",
        base_url="https://api.deepseek.com/v1",
    ),
    structured_output_mode="json_object",  # CRÍTICO: DeepSeek no soporta json_schema
)
graphiti = Graphiti(
    graph_driver=FalkorDriver(host="localhost", port=6379),
    llm_client=llm_client,
    embedder=OpenAIEmbedder(config=OpenAIEmbedderConfig(
        api_key=os.environ["OPENAI_API_KEY"], embedding_model="text-embedding-3-small")),
    cross_encoder=OpenAIRerankerClient(config=LLMConfig(api_key=os.environ["OPENAI_API_KEY"])),
)
```

**MCP server** — editar `config.yaml` para separar variables (imprescindible):

```yaml
llm:
  model: ${MODEL_NAME:deepseek-v4-flash}
  structured_output_mode: ${LLM_STRUCTURED_OUTPUT_MODE:json_object}
  providers:
    openai:
      api_key: ${DEEPSEEK_API_KEY}
      api_url: ${DEEPSEEK_API_URL:https://api.deepseek.com/v1}
embedder:
  model: ${EMBEDDER_MODEL:text-embedding-3-small}
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      api_url: https://api.openai.com/v1
```

## 8. Plan de adopción propuesto

1. ✅ **HECHO 2026-08-01 (§9)**: `deepseek-chat` responde y es no-thinking → vía (a), sin subclase.
2. ⚠ **PARCIAL 2026-08-01 (§10)** — hecho sin brazo de control (no hay key de OpenAI). **A/B con 5-10 episodios reales** (mismos episodios, config actual vs DeepSeek): comparar entidades/aristas extraídas y fallos de schema. No hay benchmarks publicados de calidad — el A/B es la única evidencia que cuenta (H10).
3. Si pasa: cambiar el config.yaml del MCP (variables separadas), registrar ADR, y monitorear `prompt_cache_hit_tokens` + episodios fallidos la primera semana.
4. Si `deepseek-chat` murió y no queremos subclase: posponer — con thinking el ahorro (~$0-4/mes) no paga la fricción.

## 9. Sondeo del §8.1 — ejecutado el 2026-08-01 (key propia, 4 llamadas reales)

**El alias `deepseek-chat` NO murió, y responde en no-thinking.** Es la vía (a)
del §8.1: la que no necesita subclase. Resultados crudos:

| Prueba | Status | Modelo devuelto | Thinking |
|---|---|---|---|
| `GET /v1/models` | 200 | solo `deepseek-v4-flash` y `deepseek-v4-pro` — los alias **no se listan** | — |
| `deepseek-chat` | 200 | `deepseek-v4-flash` | **NO-thinking limpio** (sin `reasoning_content`, sin `reasoning_tokens`) |
| `deepseek-v4-flash` a secas | 200 | `deepseek-v4-flash` | **THINKING ON**: 62 reasoning tokens + `reasoning_content` de 266 chars |
| `deepseek-v4-flash` + `thinking:{type:disabled}` | 200 | `deepseek-v4-flash` | NO-thinking — **la API acepta el parámetro** |
| ídem + `response_format: json_object` | 200 | `deepseek-v4-flash` | NO-thinking, JSON válido |

**Matiz 2 confirmado y cuantificado**: en el MISMO prompt, thinking ON no solo
añadió 62 tokens de razonamiento — infló el prompt de **35 → 114 tokens**
(~79 de preámbulo inyectado). Sobre 4-8 llamadas/episodio es justo el 2-5× que
anticipaba la palanca 1 del §5.

**Por qué importa el alias para el MCP server**: `config.yaml` no tiene dónde
meter un `extra_body`, así que `model: deepseek-chat` es la **única** vía
zero-code a no-thinking en modo MCP. En modo librería hay dos.

⚠ **Reservas** (van al ADR si se adopta):
- El alias está **deprecado desde el 2026-07-24 y no aparece en `/v1/models`**.
  Funciona hoy; puede desaparecer sin aviso. Plan B ya identificado: subclase de
  ~10 líneas o `thinking:{type:disabled}` en modo librería.
- `prompt_cache_hit_tokens` salió **0 en las 4** llamadas — esperable con
  prompts de juguete sin prefijo repetido. **No dice nada** sobre la fracción
  cacheable del §6: eso solo se mide con los prompts reales de Graphiti (A/B).

**Re-verificar** (el alias puede morir): POST a `api.deepseek.com/v1/chat/completions`
con `{"model":"deepseek-chat",...}` y mirar si la respuesta trae
`message.reasoning_content` o `usage.completion_tokens_details.reasoning_tokens`.
La key vive en `%LOCALAPPDATA%\deepseek\.env` (fuera de git y de OneDrive);
leerla del archivo, nunca pasarla por la línea de comandos.

## 10. Prueba de extracción del §8.2 — ejecutada el 2026-08-01

⚠ **NO es el A/B completo: falta el brazo de control.** No hay key de OpenAI en
la máquina, así que se midió DeepSeek en **absoluto**, sin línea base. **H10
sigue sin satisfacerse**: nada de lo de abajo dice "mejor o peor que OpenAI",
solo "funciona / no funciona" y a qué precio.

**Montaje**: `graphiti-core` 0.29.3 como librería en venv aislado · LLM
`deepseek-chat` · `structured_output_mode=json_object` · embedder **local**
(fastembed ONNX bge-small, 384 dims — NO el `text-embedding-3-small` de
producción) · **sin reranker** · FalkorDB en contenedor **efímero**
(`docker run --rm`, sin volumen) · group_id desechable `ab-deepseek` · 8
episodios reales del vault (2 ADRs, 2 bugs, 2 convenciones, 2 features).

| Episodio | Entidades | Aristas | Llamadas | in | out | cache hit |
|---|---|---|---|---|---|---|
| adr-graphiti-pospuesto | 9 | 8 | 2 | 3.388 | 1.002 | 1.280 |
| adr-vault-git-separate | 5 | 3 | 6 | 8.346 | 654 | 1.280 |
| bug-bom-powershell | 4 | 2 | 6 | 9.316 | 700 | 1.280 |
| bug-elseif-invalid | 4 | 3 | 8 | 10.789 | 809 | 1.536 |
| convencion-interprete-hooks | 9 | **0** | 4 | 8.463 | 900 | 2.304 |
| convencion-bom-ps1 | **1** | **0** | 3 | 6.508 | 75 | 2.304 |
| telegram-t0 | 9 | 9 | 12 | 18.371 | 1.442 | 3.200 |
| hook-precompact | 3 | 2 | 6 | 10.766 | 400 | 2.816 |
| **TOTAL** | **44** | **27** | **47** | **75.947** | **5.982** | **16.000** |

**Los números que importan:**
- **0 episodios fallidos, 0 reintentos de schema** en 8/8. El matiz 1 (json_object
  degradado, "may occasionally return empty content") **no se manifestó**.
- **0 reasoning tokens en las 47 llamadas** → no-thinking confirmado bajo carga
  real, no solo en prompts de juguete.
- **Caché: 21,1% del input** (16.000/75.947). Por debajo del 25-35% estimado en
  el §5 palanca 2, pero del mismo orden. Crece por episodio (1.280 → 3.200): el
  prefijo se calienta, así que en régimen sería mayor.
- **5,9 llamadas/episodio de media** — dentro del "4-8 típico" del §5.
- **Costo medido: $0,00126/episodio → ~$0,25/mes a 200 episodios/mes.** Es la
  MITAD de la estimación optimista del §6 ($0,40-0,60) y **~24× más barato que
  los ~$6 de gpt-5.4-mini**. (El input real por episodio, ~9,5K, resultó menor
  que los 24K supuestos.)

**Calidad a ojo — bien:** entidades correctas y específicas (`Graphiti`,
`FalkorDB`, `backup-graph.ps1`, `@floreanoclaudebot`), **sin hechos inventados**
en ninguna de las 27 aristas; nombres de relación informativos
(`REJECTED_FOR_USE_WITH`, `AVOIDS_SYNC_WITH`, `HAD_LOST_BOM_IN`); y el **dedup
cross-episodio funciona** (`git`, `OneDrive`, `BOM`, `sync-hooks.ps1` se
reutilizan como el mismo nodo).

**Calidad a ojo — mal (3 defectos reales):**
1. **Idioma inconsistente**: 4 de 8 episodios produjeron summaries y hechos en
   **inglés** pese a que todo el corpus está en español. Inaceptable para un
   vault en español si se repite.
2. **Sobre-fragmentación**: `convencion-interprete-hooks` sacó **9 entidades de
   una convención de 2 frases**, con ruido (`convencion`, `comando python`
   duplicando `python`, `interprete de los hooks de Claude Code`) y **0 aristas**.
3. **Pérdida de contenido por dedup**: `convencion-bom-ps1` sacó **1 entidad y 0
   aristas** — el contenido real (`.ps1` CON BOM, `plugin.json` SIN BOM) **no
   quedó en el grafo**: se fusionó con un nodo previo cuyo summary habla de otra
   cosa. En una corrida anterior, ese mismo episodio sin nodos previos sí
   extrajo las 3 entidades correctas.

⚠ **Sin brazo de control no se puede atribuir**: los 3 defectos pueden ser de
DeepSeek o del pipeline de Graphiti. Solo el A/B con OpenAI lo separaría.

**Veredicto: ADOPTAR CON RESERVAS** — viable y baratísimo, con los 3 defectos
anotados para vigilancia. Ver `ADR-20260801-deepseek-extraccion-graphiti`.

**Bugs de terceros encontrados de paso** (backend **Kuzu**, que en 0.29.3 sale
DEPRECADO — "upstream no longer maintained"): (1) `add_episode` evalúa
`group_id != self.driver._database` y `KuzuDriver` nunca inicializa `_database`
→ `AttributeError` con **cualquier** group_id explícito; (2) `Table
RelatesToNode_ doesn't have an index with name edge_name_and_fact` al guardar
aristas → 6 de 8 episodios fallaron. **No usar Kuzu.** Además, `falkordb` 1.6.2
solo funciona con `redis` **7.x** (con 6.x falta `redis.driver_info`; con 8.x
peta por `himport_registry`).

## Fuentes

getzep/graphiti v0.29.3 (README, openai_generic_client.py, node_operations.py, bulk_utils.py, prompts/, mcp_server/) · api-docs.deepseek.com (pricing, json_mode, function_calling, thinking_mode, kv_cache, api reference, news V4, rate limits) · help.getzep.com (configuration, adding-episodes) · issues #1007/#912/#1204/#1193 · fuentes terciarias marcadas (morphllm, pricepertoken, deepseek.ai no-oficial). **No verificable:** issues "deepseek" por búsqueda full-text; calidad de extracción vs OpenAI; fracción cacheable exacta; billing de reasoning tokens V4 en doc oficial. ~~vida del alias deepseek-chat~~ → **verificada el 2026-08-01, ver §9**.

---

*Doc 08 de la subserie arquitectura-memoria. Decisión de adopción → ADR tras el A/B del §8.*
