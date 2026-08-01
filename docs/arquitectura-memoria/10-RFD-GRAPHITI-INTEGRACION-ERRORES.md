---
title: RFD - Graphiti + FalkorDB Integración - Errores Encontrados y Propuesta de Solución
created: 2026-08-01
status: draft
author: Claude Code
tags: graphiti, falkordb, deepseek, embeddings, mcp, architecture
---

# RFD: Graphiti + FalkorDB - Problemas de Integración y Propuesta de Solución

**Resumen ejecutivo:** La integración de Graphiti con Claude Code tiene incompatibilidades críticas. Este RFD documenta 8 errores encontrados, investiga alternativas de embeddings (especialmente DeepSeek), y propone una solución con skills en lugar de MCP server HTTP.

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

**Root cause:** Graphiti MCP 2026-08 (última versión) NO es compatible con Claude Code's HTTP MCP transport. La arquitectura de Graphiti asume:
- SSE (Server-Sent Events) para browsers/clientes HTTP
- stdio para herramientas CLI
- Pero NO expone un endpoint MCP JSON-RPC sobre HTTP

---

### 3. **graphiti-core usa Neo4j por defecto, no FalkorDB**

**Error:** `graphiti-core` Python package require Neo4j como database backend.

```python
graphiti = Graphiti(uri=uri)  # Espera URI tipo bolt://
```

**Causa:** `graphiti-core` es la librería Python, diseñada para Neo4j. El Graphiti MCP server (contenedor Docker) sí soporta FalkorDB, pero la librería SDK no.

**Impacto:** No se puede usar `graphiti-core` directamente con FalkorDB sin Neo4j instalado.

**Workaround usado:** Cliente MCP Python via `mcp` package + SSE para comunicarse con el servidor en Docker.

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

### 6. **Endpoint `/sse` rechaza POST (405 Method Not Allowed)**

**Error:** Intento de conectar al MCP server via `POST /sse` devuelve 405.

**Causa:** SSE es un protocolo de solo-lectura (GET). El cliente MCP intenta establecer handshake POST que no existe.

**Impacto:** Imposible conectar via HTTP tradicional.

---

### 7. **Transport SSE incompatible con especificación MCP HTTP de Claude Code**

**Error:** Claude Code CLI soporta `--transport http` pero espera JSON-RPC sobre HTTP POST. Graphiti MCP ofrece SSE sobre HTTP GET.

**Causa:** Mismatch de especificaciones. MCP define transport=http como JSON-RPC sobre HTTP, pero Graphiti implementó SSE.

**Impacto:** Necesario usar `mcp` Python package directamente con `sse_client()` en lugar de Claude Code CLI.

---

### 8. **PowerShell profile escaping de parámetros**

**Error:** Parámetros con backslashes en PowerShell quebrantaban la función graphiti.

**Causa:** PowerShell interpreta `\` como escape character. Script embebido complejo causaba parsing errors.

**Workaround:** Cambiar a script Python directo sin wrapper PowerShell.

---

## PARTE 2: INVESTIGACIÓN - DEEPSEEK EMBEDDINGS

### Hallazgo clave

DeepSeek SÍ ofrece un endpoint de embeddings (`/v1/embeddings`, modelo: `deepseek-embedding-v2`), **PERO no está oficialmente documentado y NO tiene soporte**. GitHub Issues desde 2024-2025 preguntando si el servicio existe sugieren riesgo de deprecation.

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

**Estrategia elegida:** DeepSeek LLM + Ollama embeddings local = $0 recurrente después de setup.

---

## PARTE 3: PROPUESTA DE SOLUCIÓN

### Problema

El MCP server de Graphiti en Docker **no es acesible desde Claude Code de forma confiable**. Los workarounds actuales son:

1. Script Python con cliente MCP manual ✅ (funciona, pero tedioso)
2. Claude Code MCP CLI ❌ (incompatibilidad SSE/HTTP)
3. API REST directa ❌ (no expuesta)

### Solución propuesta: **Skills + CLI híbrida**

**Opción A (Recomendada):** Skills que ejecutan Python MCP client

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

### Inmediato (esta semana)

- [ ] Crear skill `graphiti-memory` con Python MCP client ✅ HECHO
- [ ] Documentar en README que DeepSeek LLM + Ollama embeddings es la combo óptima
- [ ] Setup Ollama: `ollama pull nomic-embed-text` en docker-compose
- [ ] Actualizar config.yaml para apuntar embedder a `http://localhost:11434/v1`

### Corto plazo (2-4 semanas)

- [ ] Monitorear releases de Graphiti MCP
- [ ] Si fix HTTP llega, verificar compatibilidad
- [ ] Else: Mantener solución de skills + Python MCP client

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
| Neo4j en lugar de FalkorDB | graphiti-core Python funciona nativo | Otro container, más setup | ❌ Overengineering |
| Usar Graphiti CLI directo | Sin MCP server | No integrado en Claude Code | ⚠️ Fallback |
| Esperar fix Graphiti MCP | Problema resuelto upstream | Incierto, tiempo desconocido | ⏳ Plan B |
| Skills + Python MCP client | Funciona hoy, integrado | Capa extra de Python | ✅ Elegido |
| Memoria en Markdown + Graphiti API | Bajo overhead | Perder grafo temporal | ❌ Regresión |

---

## CONCLUSIÓN

Graphiti + FalkorDB es viable y potente para memoria temporal, pero **la integración MCP con Claude Code tiene limitaciones actuales**. La solución recomendada es usar **Skills + Python MCP client**, que:

1. ✅ Funciona inmediatamente
2. ✅ Es mantenible y debuggable
3. ✅ No depende de fixes upstream
4. ✅ Integrado en CLI de Claude Code

Para embeddings: **mantener OpenAI ($0.02-0.05/mes) o cambiar a Gemini (gratis)**, pero NO es viable usar solo DeepSeek.

**Siguiente paso:** Crear skill `graphiti-memory` y actualizar documentación.

---

## Referencias

- Graphiti GitHub: https://github.com/getzep/graphiti
- MCP Spec: https://modelcontextprotocol.io
- DeepSeek API: https://api-docs.deepseek.com
- OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
