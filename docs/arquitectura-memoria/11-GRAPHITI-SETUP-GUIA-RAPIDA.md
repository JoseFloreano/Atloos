---
title: Resumen - Setup Graphiti Mejorado (DeepSeek + Ollama)
created: 2026-08-01
status: ready
---

# Setup Graphiti Mejorado - Guía Rápida

Basado en investigación de los 8 errores encontrados durante implementación.

## El Problema

El setup inicial de Graphiti tenía muchos bugs. La solución anterior usaba OpenAI para embeddings ($0.02-0.05/mes extra).

## La Solución: DeepSeek LLM + Ollama Embeddings

```
Costo anterior: $0.25 (DeepSeek LLM) + $0.05 (OpenAI embeddings) = $0.30/mes
Costo nuevo:   $0.25 (DeepSeek LLM) + $0 (Ollama embeddings) = $0.25/mes
Ahorro: 17% + eliminada dependencia de OpenAI API
```

### Stack Nuevo

| Componente | Solución | Costo |
|-----------|----------|-------|
| **Database** | FalkorDB (Docker) | $0 |
| **LLM** | DeepSeek (cloud API) | $0.25/mes |
| **Embeddings** | Ollama local (nomic-embed-text) | $0 |
| **MCP Server** | Graphiti (Docker) | $0 |
| **CLI** | Python + skill graphiti-memory | $0 |
| **TOTAL** | | **$0.25/mes** |

---

## Setup en 5 pasos

### 1. Copiar docker-compose mejorado

```powershell
Copy-Item "$env:LOCALAPPDATA\graphiti\docker-compose-ollama.yml" `
          "$env:LOCALAPPDATA\graphiti\docker-compose.yml" -Force
```

### 2. Levantar con Ollama incluido

```powershell
cd "$env:LOCALAPPDATA\graphiti"
docker compose up -d
```

### 3. Descargar modelo de embeddings

```powershell
docker exec graphiti-ollama ollama pull nomic-embed-text
```

Espera ~2-3 minutos mientras descarga (700MB).

### 4. Verificar que todo funciona

```powershell
docker ps | Select-String graphiti
# Deben estar corriendo 3 containers:
# - graphiti-falkordb
# - graphiti-ollama
# - graphiti-mcp-server
```

### 5. Usar desde Claude Code

```powershell
# Agregar un episodio
python C:\Users\jlflo\.claude\skills\shared\graphiti-memory\graphiti_client.py add "tu contexto"

# Buscar hechos
python C:\Users\jlflo\.claude\skills\shared\graphiti-memory\graphiti_client_py search "palabra clave"

# Ver episodios
python C:\Users\jlflo\.claude\skills\shared\graphiti-memory\graphiti_client.py episodes
```

---

## Qué cambió

### ANTES

- ❌ Versiones pinneadas no existían
- ❌ DeepSeek + OpenAI (dos APIs)
- ❌ MCP server incompatible con Claude Code CLI
- ❌ Documentación incompleta

### AHORA

- ✅ Docker pull automático de última versión
- ✅ DeepSeek LLM + Ollama embeddings (una API cloud)
- ✅ Python MCP client vía skill graphiti-memory
- ✅ Documentación completa + RFD con 8 errores encontrados

---

## Beneficios

1. **Más barato:** $0.25/mes en lugar de $0.30/mes
2. **Más simple:** Una API key en lugar de dos
3. **Confiable:** Embeddings local = sin dependencia de terceros
4. **Rápido:** Ollama local es instántaneo (sin latencia de red)
5. **Privado:** Embeddings no salen del equipo

---

## Documentación Completa

Ver `10-RFD-GRAPHITI-INTEGRACION-ERRORES.md` para:
- Detalles de los 8 errores encontrados
- Por qué DeepSeek embeddings no es viable
- Comparativa de alternativas
- Propuesta de arquitectura final

---

## Troubleshooting

### "Image pull failed for ollama/ollama"

Ollama es una imagen grande (~3GB). Si falla:

```powershell
docker pull ollama/ollama  # Reintentar
# O usar imagen más ligera:
docker pull ollama/ollama:0.1.0
```

### "nomic-embed-text download stuck"

Ollama está descargando. Monitorear:

```powershell
docker logs graphiti-ollama --follow
```

Ctrl+C para salir. El proceso continúa en background.

### "Graphiti MCP says 'DEEPSEEK_API_KEY vacía'"

En Windows, la key no se propagó al container. Reinicia Docker:

```powershell
cd "$env:LOCALAPPDATA\graphiti"
docker compose restart
```

---

## Próximos pasos

- [ ] Reemplazar docker-compose.yml con versión Ollama (arriba)
- [ ] Hacer `docker compose up -d`
- [ ] Ejecutar `docker exec graphiti-ollama ollama pull nomic-embed-text`
- [ ] Probar: `python graphiti_client.py add "Test"`
- [ ] Listo para usar desde sesiones de Claude Code
