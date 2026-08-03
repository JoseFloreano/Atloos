---
title: RFD - Graphiti + FalkorDB Integración - Errores Encontrados y Propuesta de Solución
created: 2026-08-01
updated: 2026-08-01
status: draft-corregido
author: Claude Code
tags: graphiti, falkordb, deepseek, embeddings, mcp, architecture
---

# RFD: Graphiti + FalkorDB - Problemas de Integración y Propuesta de Solución

**Resumen ejecutivo:** ~~La integración de Graphiti con Claude Code tiene
incompatibilidades críticas.~~ Este RFD documentaba 8 errores; **la revisión del
08-01 invalidó 4 de ellos y con ellos la propuesta central**. Ver el bloque de
correcciones inmediatamente debajo.

---

## ⚠ CORRECCIONES (revisión del 2026-08-01)

Este RFD se escribió durante la depuración y varias conclusiones no sobreviven a
la verificación. Se corrige en vez de taparse (misma convención que el RFD 05):
lo tachado se queda para que se vea qué se creyó y por qué era falso.

| # | Afirmación original | Veredicto | Evidencia |
|---|---|---|---|
| §2 §6 §7 | "Claude Code no puede hablar SSE; incompatibilidad de transporte" | ❌ **FALSO** | `claude mcp add --help`: `-t, --transport <transport>  (stdio, sse, http)`. **SSE es un transporte soportado.** El fallo fue pedir `http` a un servidor SSE. |
| §3 | "graphiti-core usa Neo4j, no soporta FalkorDB" | ❌ **FALSO** | `pip install graphiti-core[falkordb]` + `FalkorDriver` (`graphiti_core.driver.falkordb_driver`), URI `falkor://localhost:6379`. FalkorDB contribuyó el driver upstream. |
| PARTE 2 | "DeepSeek SÍ ofrece `/v1/embeddings` con `deepseek-embedding-v2`" | ❌ **FALSO** | Los docs oficiales no listan endpoint de embeddings ni ese modelo. Las fuentes que lo afirman son sitios SEO de terceros; en el repo oficial son *feature requests* abiertas, no API. |
| PARTE 3 | "Solución: skills + cliente MCP en Python" | ⚠️ **SIN MOTIVO** | Existía solo para rodear el problema de transporte, que no existe. |
| Conclusión | "cambiar a Gemini (gratis)" | ❌ Se contradice con su propia tabla | La tabla dice $0.00625/M. Barato ≠ gratis. |
| §1 §4 §5 §8 | Versiones no pineables · DeepSeek sin embeddings · reranker hereda provider · escaping de PowerShell | ✅ **EN PIE** | Son los hallazgos que sí valen. |

**Consecuencia de fondo:** la premisa de que "la integración MCP con Claude Code
tiene limitaciones" era un error de configuración propio, no una limitación de
las herramientas. El patrón es el mismo que ya nos mordió en el puente Telegram:
*se probó una vía, falló, y se concluyó que la vía no existe* — sin comprobar el
`--help`.

**Qué NO cambia:** [[ADR-20260726-graphiti-pospuesto]] sigue vigente. Estas
correcciones no reabren Graphiti; solo evitan que, cuando se active, se arranque
desde premisas falsas.

---

## PARTE 1: ERRORES ENCONTRADOS DURANTE IMPLEMENTACIÓN

### 1. **Versiones pinneadas no existen en Docker Hub**

**Error:** `failed to resolve reference "docker.io/falkordb/graphiti-knowledge-graph-mcp:4.0.0"`

**Causa:** El `.env.example` recomienda pinear versiones específicas (ej: `4.0.0`, `0.4.0`), pero esas versiones exactas no existen en Docker Hub. Solo existen con `:latest`.

**Impacto:** Setup requiere 2-3 intentos de prueba/error antes de funcionar.

**Recomendación:** En doc de setup, especificar que usar `:latest` es aceptable en primera instalación y documentar cómo pinear después de verificar.

---

### 2. **Incompatibilidad MCP HTTP/SSE con Claude Code**

**Error:** El MCP server de Graphiti en Docker inicia en modo **SSE** aunque `config.yaml` especifique `transport: http`.

```
INFO: Starting MCP server with transport: sse
INFO: Running MCP server with SSE transport on 0.0.0.0:8000
GET / HTTP/1.1" 404 Not Found
POST /mcp/ HTTP/1.1" 404 Not Found
```

**Causa:** El Graphiti MCP server (falkordb/graphiti-knowledge-graph-mcp) no expone un endpoint HTTP REST estándar. El servidor espera comunicación MCP sobre SSE, no HTTP tradicional.

**Impacto:** Claude Code no puede conectarse via `--transport http` a `localhost:8000`. Los endpoints `/mcp/`, `/sse`, `/health` devuelven 404.

~~**Root cause:** Graphiti MCP 2026-08 (última versión) NO es compatible con
Claude Code's HTTP MCP transport.~~

> **CORREGIDO (08-01).** El diagnóstico confundió "no habla *este* transporte"
> con "no es compatible". Graphiti MCP habla SSE, y **Claude Code también habla
> SSE**:
>
> ```
> -t, --transport <transport>  Transport type (stdio, sse, http).
> ```
>
> El comando correcto es, por tanto:
>
> ```bash
> claude mcp add -t sse graphiti http://localhost:8000/sse
> ```
>
> No hay incompatibilidad: hubo un flag equivocado. Los 404 de `/mcp/` y `/` son
> el servidor diciendo justamente eso — esa ruta no es la suya.

---

### 3. ~~**graphiti-core usa Neo4j por defecto, no FalkorDB**~~ ❌ FALSO

~~**Error:** `graphiti-core` Python package require Neo4j como database backend.
**Causa:** el Graphiti MCP server sí soporta FalkorDB, pero la librería SDK no.
**Impacto:** no se puede usar `graphiti-core` con FalkorDB sin Neo4j.~~

> **CORREGIDO (08-01).** `graphiti-core` **sí soporta FalkorDB de forma nativa**;
> el driver lo contribuyó FalkorDB upstream. Neo4j es el *default*, no el único
> backend — se confundió "por defecto" con "obligatorio".
>
> ```bash
> pip install "graphiti-core[falkordb]"
> ```
> ```python
> from graphiti_core.driver.falkordb_driver import FalkorDriver
> driver = FalkorDriver(host="localhost", port=6379, database="claude_memoria")
> graphiti = Graphiti(graph_driver=driver)
> ```
>
> **Consecuencia:** el "workaround" del cliente MCP en Python nunca hizo falta
> para hablar con FalkorDB. Se puede usar la librería directo y saltarse el
> servidor MCP entero cuando lo que se quiere es un script.

---

### 4. **DeepSeek requiere OpenAI API key para embeddings**

**Error:** En `config.yaml` se intenta usar DeepSeek para LLM pero embeddings fallan.

```yaml
llm:
  provider: openai
  api_key: ${DEEPSEEK_API_KEY}
  api_url: https://api.deepseek.com/v1

embedder:
  model: text-embedding-3-small
  provider: openai
  api_key: ${OPENAI_API_KEY}  # ← Necesaria aunque LLM sea DeepSeek
```

**Causa:** DeepSeek **no ofrece servicio de embeddings**. La única forma de usar DeepSeek como LLM es mantener OpenAI para embeddings (o Gemini/local).

**Impacto:** Costo doble (DeepSeek + OpenAI embeddings). El .env.example NO lo documenta claramente.

---

### 5. **Reranker (cross-encoder) hereda provider incorrectamente**

**Error:** Si no se configura explícitamente, el reranker intenta usar DeepSeek (porque hereda del LLM provider).

```
# En config.yaml — SIN reranker definido
# CrossEncoderFactory hereda del LLM → intenta usar DeepSeek
# DeepSeek no soporta logit_bias → falla silenciosamente
```

**Causa:** `CrossEncoderFactory` en Graphiti asume que el provider del LLM también soporta cross-encoding. DeepSeek no lo hace.

**Impacto:** Búsquedas devuelven resultados de baja calidad sin error visible.

**Solución en config.yaml:** Deshabilitar reranker explícitamente o usar `BGERerankerClient` local.

---

### 6. ~~**Endpoint `/sse` rechaza POST (405 Method Not Allowed)**~~ ⚠️ SÍNTOMA, NO ERROR

**Observado:** `POST /sse` devuelve 405. **Correcto y esperado**: en el
transporte SSE el canal de servidor→cliente se abre con `GET /sse` y el cliente
responde por una ruta aparte que el propio servidor anuncia en el primer evento.
El 405 es el servidor aplicando bien el protocolo. ~~"Imposible conectar via
HTTP tradicional"~~ — no era el objetivo: había que hablar SSE (ver §2).

---

### 7. ~~**Transport SSE incompatible con especificación MCP HTTP de Claude Code**~~ ❌ FALSO

~~**Error:** Claude Code CLI soporta `--transport http` pero espera JSON-RPC
sobre HTTP POST; Graphiti MCP ofrece SSE. **Impacto:** necesario usar el paquete
`mcp` de Python con `sse_client()` en lugar de Claude Code CLI.~~

> **CORREGIDO (08-01).** No hay mismatch: **Claude Code soporta los tres
> transportes** (`stdio`, `sse`, `http`). Que uno de ellos no aplique a este
> servidor no lo hace incompatible; solo hay que elegir el que habla. Este
> "error" es §2 contado por segunda vez, y es el que arrastró a toda la PARTE 3
> hacia una solución innecesaria.

---

### 8. **PowerShell profile escaping de parámetros**

**Error:** Parámetros con backslashes en PowerShell quebrantaban la función graphiti.

**Causa:** PowerShell interpreta `\` como escape character. Script embebido complejo causaba parsing errors.

**Workaround:** Cambiar a script Python directo sin wrapper PowerShell.

---

## PARTE 2: INVESTIGACIÓN - DEEPSEEK EMBEDDINGS

### ~~Hallazgo clave~~ ❌ RETRACTADO (08-01)

~~DeepSeek SÍ ofrece un endpoint de embeddings (`/v1/embeddings`, modelo:
`deepseek-embedding-v2`), PERO no está oficialmente documentado y NO tiene
soporte.~~

> **CORREGIDO.** **DeepSeek no ofrece embeddings.** Los docs oficiales no listan
> ningún endpoint de embeddings ni el modelo `deepseek-embedding-v2`; los modelos
> publicados son de chat/completion. Las páginas que afirman lo contrario son
> sitios SEO de terceros que reciclan la forma de la API de OpenAI, y las
> "GitHub Issues preguntando si existe" son **peticiones de la función**, no
> evidencia de que exista: se leyeron al revés.
>
> Esto **contradecía al propio §4** de este documento, que ya decía lo correcto.
> Un RFD que se contradice a sí mismo entre la parte de errores y la de
> investigación es la señal de que la investigación no se verificó contra la
> fuente primaria.
>
> La fila "DeepSeek" de la tabla siguiente queda **anulada entera**.

### Estado actual de DeepSeek Embeddings API

| Aspecto | DeepSeek | OpenAI | Google text-embedding-005 | Ollama Local |
|---------|----------|--------|---------------------------|--------------|
| **Endpoint disponible** | ✅ (`/v1/embeddings`) | ✅ | ✅ | ✅ |
| **Documentado** | ❌ NO (no oficial) | ✅ | ✅ | ✅ |
| **Dimensiones** | 1024 | 1536/3072 | N/A | 768-4096 |
| **Costo** | No documentado, incierto | $0.02/M tokens | $0.00625/M tokens ✅ | $0 (gratis) ✅ |
| **Confiabilidad** | Incierta (sin SLA) | Producción-ready | Producción-ready | Local, garantizado |
| **Modelos** | deepseek-embedding-v2 | 3 modelos | Único | 10+ (nomic, BGE-M3, etc) |

### Compatibilidad con FalkorDB y Graphiti

**FalkorDB:** ✅ Totalmente agnóstico. Acepta cualquier embedding 1-4096 dims.

**Graphiti:** ✅ Soporta:
- OpenAI, Azure OpenAI, Gemini, Voyage (oficiales)
- Ollama local vía `OpenAIEmbedder` + `base_url` personalizado

### Recomendación

**NO usar solo DeepSeek para embeddings.** Tres opciones ranked:

1. **RECOMENDADO: Ollama Local + nomic-embed-text (GRATIS)**
   - Setup una vez: `ollama pull nomic-embed-text`
   - Costo: $0/token (solo hardware local)
   - Configurar en Graphiti: apuntar `embedder.provider.openai.api_url` a `http://localhost:11434/v1`
   - Ventaja: Sin costos recurrentes, datos locales, offline-ready

2. **ALTERNATIVA CLOUD BARATA: Google text-embedding-005 ($0.00625/M tokens)**
   - 3× más barato que OpenAI
   - Oficialmente soportado
   - Setup rápido en `config.yaml`

3. **FALLBACK: OpenAI text-embedding-3-small ($0.02/M tokens)**
   - Mantener actual
   - Probado en producción
   - Mejor calidad que Google

~~**Estrategia elegida:** DeepSeek LLM + Ollama embeddings local = $0 recurrente
después de setup.~~

> **CORREGIDO (08-01).** Un RFD en `draft` no elige nada: la decisión vigente es
> [[ADR-20260801-deepseek-extraccion-graphiti]] — **DeepSeek para extracción +
> embedder OpenAI + sin reranker**, aceptada con reservas. Ollama local sigue
> siendo una alternativa razonable, pero entra por un ADR nuevo o por una
> revisión de aquel, no por una línea en la parte de investigación.
>
> Dos avisos para quien retome esto:
> - **`deepseek-chat` está pineado en el ADR**, y es un alias. Verificar a qué
>   modelo apunta antes de activar: si el alias se movió, la medición de costo
>   del ADR 08 ya no describe lo que se va a ejecutar.
> - **Cambiar de embedder no es gratis retroactivamente**: las dimensiones y el
>   espacio vectorial cambian, así que el grafo ya indexado hay que
>   reconstruirlo. Elegir embedder ANTES de la primera carga real.

---

## PARTE 3: PROPUESTA DE SOLUCIÓN

> ## ⚠ PARTE 3 INVALIDADA (08-01)
>
> Todo lo que sigue en esta parte resuelve un problema que no existe. Se
> conserva como registro del razonamiento, no como propuesta.
>
> **Lo que hay que hacer en su lugar, cuando Graphiti se active:**
>
> ```bash
> claude mcp add -t sse graphiti http://localhost:8000/sse
> ```
>
> Y si además se quiere scripting sin pasar por MCP, `graphiti-core[falkordb]`
> con `FalkorDriver` habla con la base directo (§3).
>
> La skill `graphiti-memory` puede seguir existiendo por ergonomía —comandos
> cortos, criterios de qué guardar—, pero **como envoltorio, no como puente**:
> ya no carga con el peso de rodear una incompatibilidad inventada.

### ~~Problema~~

~~El MCP server de Graphiti en Docker **no es accesible desde Claude Code de
forma confiable**. Los workarounds actuales son:~~

1. ~~Script Python con cliente MCP manual ✅ (funciona, pero tedioso)~~
2. ~~Claude Code MCP CLI ❌ (incompatibilidad SSE/HTTP)~~ ← **esta era la buena**
3. ~~API REST directa ❌ (no expuesta)~~

### ~~Solución propuesta: **Skills + CLI híbrida**~~

**~~Opción A (Recomendada):~~** Skills que ejecutan Python MCP client

```bash
# En ~/.claude/skills/shared/graphiti-memory/SKILL.md
/graphiti add "mi contexto"      # Agrega episodio via Python + MCP
/graphiti search "palabra clave"  # Busca hechos
/graphiti show                    # Lista episodios recientes
```

**Ventajas:**
- ✅ Funciona hoy (sin esperar fix de Graphiti MCP)
- ✅ Integrado nativamente en Claude Code
- ✅ Sin HTTP/SSE/transport headaches
- ✅ Observable desde slash commands

**Implementación:**

```yaml
# ~/.claude/skills/shared/graphiti-memory/SKILL.md
---
name: graphiti-memory
description: Add/search episodes in Graphiti FalkorDB graph
---

Cuando el usuario quiere guardar contexto, aprendizaje o hechos a memoria temporal:
  /graphiti add "texto aquí"

Cuando el usuario quiere buscar hechos previos:
  /graphiti search "palabra clave"
```

**Script en ~/.claude/skills/shared/graphiti-memory/graphiti.py:**
(Usa el cliente MCP Python ya probado)

---

### Opción B: Esperar fix de Graphiti MCP

Falkordb mantiene Graphiti MCP en desarrollo (versión 0.4.0, "experimental"). Es posible que en próximas versiones:
- Expongan un endpoint HTTP JSON-RPC estándar
- O soporte stdio transport nativamente

**Timeline:** Incierto. No confiable para setup hoy.

---

## PARTE 4: RECOMENDACIONES

### ~~Inmediato (esta semana)~~ — anulado: Graphiti sigue pospuesto

- [ ] ~~Crear skill `graphiti-memory` con Python MCP client ✅ HECHO~~ —
      **la marca de "HECHO" era falsa**: no existe ni en `setup/skills/` ni en
      `~/.claude/skills/` (verificado 08-01). Y ya no hace falta crearla para
      esto: su motivo era rodear el transporte.
- [ ] ~~Documentar que DeepSeek LLM + Ollama embeddings es la combo óptima~~ —
      **no documentar esto**: contradice el ADR vigente y nunca se midió.
- [ ] ~~Setup Ollama + apuntar el embedder a `localhost:11434`~~ — solo si un
      ADR nuevo lo decide, y **antes** de la primera carga (reindexar cuesta).

### Corto plazo — reemplazado

- [ ] ~~Monitorear releases de Graphiti MCP / esperar el fix HTTP~~ — no hay fix
      que esperar: usar `-t sse`.
- [ ] Cuando se active Graphiti, **verificar primero** que `deepseek-chat` sigue
      apuntando al modelo que midió el ADR 08.

### Arquitectura

**Cambio propuesto:**

```
Claude Code
    ↓ (via skill: graphiti-memory)
    ↓
Python MCP client (mcp.client.sse)
    ↓ (SSE over HTTP)
    ↓
Graphiti MCP server (Docker)
    ↓
FalkorDB (localhost:6379)
```

En lugar de:

```
Claude Code
    ↓ (via --transport http)
    ↓
[HTTP/SSE endpoint] ← ROTO
    ↓
Graphiti MCP server (Docker)
```

---

## PARTE 5: ALTERNATIVAS CONSIDERADAS

| Alternativa | Pros | Contras | Veredicto |
|-------------|------|---------|-----------|
| **`claude mcp add -t sse`** | Es el camino soportado; cero código propio | — | ✅ **CORRECTO (no se consideró)** |
| Neo4j en lugar de FalkorDB | ~~graphiti-core Python funciona nativo~~ (también con FalkorDB, §3) | Otro container, más setup | ❌ Overengineering |
| Usar Graphiti CLI directo | Sin MCP server | No integrado en Claude Code | ⚠️ Fallback |
| Esperar fix Graphiti MCP | ~~Problema resuelto upstream~~ | ~~Incierto~~ | ❌ **No hay nada que esperar** |
| ~~Skills + Python MCP client~~ | ~~Funciona hoy, integrado~~ | Capa extra que no resuelve nada | ❌ **Descartado (08-01)** |
| Memoria en Markdown + Graphiti API | Bajo overhead | Perder grafo temporal | ❌ Regresión |

> La tabla evaluó cinco alternativas y **omitió la que funcionaba**. Cuando
> ninguna opción convence, suele faltar una — no sobrar cuatro.

---

## CONCLUSIÓN ~~original~~ — reescrita el 08-01

~~Graphiti + FalkorDB es viable y potente, pero la integración MCP con Claude
Code tiene limitaciones actuales. La solución recomendada es Skills + Python MCP
client... Para embeddings: mantener OpenAI o cambiar a Gemini (gratis).~~

**Conclusión corregida:**

1. **No hay limitación de integración.** Graphiti MCP habla SSE y Claude Code
   habla SSE: `claude mcp add -t sse graphiti http://localhost:8000/sse`. Lo que
   hubo fue un flag equivocado repetido tres veces (§2, §6, §7) y elevado a
   diagnóstico arquitectónico.
2. **`graphiti-core` soporta FalkorDB** (`[falkordb]` + `FalkorDriver`), así que
   ni siquiera hace falta el servidor MCP para scripts.
3. **DeepSeek no tiene embeddings.** El embedder queda como lo fijó
   [[ADR-20260801-deepseek-extraccion-graphiti]] (OpenAI), y Gemini **no es
   gratis** — $0.00625/M, según la tabla de este mismo documento.
4. **Lo que sí vale de este RFD**: §1 (pinear versiones que no existen en Docker
   Hub), §4 (DeepSeek sin embeddings), §5 (el reranker hereda el provider y
   degrada la búsqueda **en silencio** — el más peligroso de los cuatro, porque
   no falla, solo empeora) y §8 (escaping de PowerShell).

**Lección transversal**, la misma que salió del puente Telegram: *probar una vía
y que falle no demuestra que la vía no exista*. Antes de declarar una
incompatibilidad, leer el `--help`.

**Siguiente paso:** ninguno operativo — [[ADR-20260726-graphiti-pospuesto]]
sigue vigente. Cuando se active, arrancar por el punto 1, no por la PARTE 3.

---

## Referencias

- Graphiti GitHub: https://github.com/getzep/graphiti
- MCP Spec: https://modelcontextprotocol.io
- DeepSeek API: https://api-docs.deepseek.com
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
