# Arquitectura Final Recomendada
## Decisión consolidada, justificación, diagrama y plan de implementación

> **Banner (2026-08-01):** Graphiti + FalkorDB está **POSPUESTO** por decisión
> propia (`ADR-20260726-graphiti-pospuesto`; errores de integración en el RFD 10
> de esta carpeta). El checklist de instalación de este doc NO es el camino
> vigente — cuando se active, la guía es el `arquitectura-memoria/11`. Nota: `uv tool install
> graphifyy` (doble "y") es el nombre REAL del paquete en PyPI (verificado
> 2026-08-01, graphify no existe) — no lo "corrijas".

---

## 1. La decisión

Después de investigar exhaustivamente los frameworks agénticos, sistemas de memoria, estrategias de sincronización y benchmarks disponibles (junio–julio 2026), la arquitectura recomendada para el caso específico de **2-3 laptops, múltiples cuentas Claude, stack React/Flutter/Python/C++, OneDrive** es:

```
MEMORIA DE CODEBASE   → Graphify (AST, 0 tokens)          [prioridad alta]
MEMORIA DE SESIONES   → Obsidian vault (markdown + MCP)   [prioridad alta]
MEMORIA TEMPORAL      → Graphiti + FalkorDB (Docker)       [prioridad media]
METODOLOGÍA           → Superpowers plugin                 [prioridad alta]
SINCRONIZACIÓN        → git dotfiles + OneDrive vault      [base]
MULTI-CUENTA          → CLAUDE_CONFIG_DIR + aliases        [base]
```

Esta arquitectura no es la más sofisticada posible — es la más adecuada para el caso de uso específico, basada en los hallazgos críticos de la investigación.

---

## 2. Por qué esta arquitectura y no otra

### Por qué Graphify y no solo CLAUDE.md

Un CLAUDE.md bien escrito (<500 tokens) describe *qué hace* el proyecto y *cómo trabajar en él*. No puede describir eficientemente *qué función llama a qué*, *qué archivos dependen de un módulo*, o *cuál es el blast radius de un cambio*. Graphify provee eso con cero tokens propios (AST mode). Es el complemento natural de CLAUDE.md, no su reemplazo.

### Por qué Obsidian y no solo Graphiti para memoria de sesiones

Graphiti cobra LLM en escritura (~$0.001-0.003 por episodio). Para decidiones de arquitectura que se registran 2-3 veces por sesión, el costo es trivial. Pero para convenciones, procedimientos y conocimiento referencial que se consulta frecuentemente pero cambia poco, un archivo markdown en Obsidian es **instantáneo, gratuito y humanamente inspeccionable**.

La división es: Obsidian para conocimiento estable y procedimental; Graphiti para hechos que evolucionan temporalmente.

### Por qué la Estrategia A de OneDrive (datos locales + backups)

FalkorDB escribe continuamente en `dump.rdb` y `appendonly.aof`. OneDrive puede interrumpir esas escrituras. El riesgo de corrupción del grafo, aunque bajo en uso normal, es inaceptable porque la corrupción puede ser silenciosa y descubrirse días después. La Estrategia A elimina ese riesgo completamente.

### Por qué Superpowers y no un framework personalizado

Superpowers tiene más de 200,000 instalaciones documentadas y fue creado por alguien con conocimiento profundo de cómo funciona internamente Claude Code. Las 14 Skills cubren los casos más comunes de desarrollo agéntico. El costo de mantenimiento es cero (zero-dependency, actualizado por la comunidad). Construir un framework personalizado desde cero tiene un costo de oportunidad alto versus implementar directamente.

---

## 3. Diagrama de arquitectura completo

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CLAUDE CODE (CLI)                              │
│                                                                     │
│  ~/.claude/CLAUDE.md (<500 tokens)                                  │
│  ~/.claude/settings.json                                            │
│  ~/.claude/agents/ (flutter-expert, cpp-pro, python-expert...)      │
│                                                                     │
│  Plugins activos:                                                   │
│  • superpowers@claude-plugins-official                              │
│  • clangd-lsp@claude-plugins-official (C++)                         │
│  • graphify (skill global o por proyecto)                           │
└──────────────────────┬──────────────────────────────────────────────┘
                       │ MCP (HTTP / stdio)
                       │
          ┌────────────┼────────────────────────────┐
          │            │                            │
          ▼            ▼                            ▼
   ┌─────────────┐ ┌──────────────┐          ┌────────────────────┐
   │  filesystem │ │   context7   │          │  graphiti-memory   │
   │     MCP     │ │     MCP      │          │      (HTTP)        │
   │             │ │  (docs vivos)│          │  localhost:8000    │
   └──────┬──────┘ └──────────────┘          └────────┬───────────┘
          │                                           │
          ▼                                           ▼
   Vault Obsidian                             ┌──────────────────┐
   (~/OneDrive/DevSetup/                      │  Graphiti MCP    │
    ObsidianVault/)                           │    Server        │
   ┌────────────────────────┐                 └────────┬─────────┘
   │ 10-Projects/           │                          │
   │   react-dashboard/     │                          ▼
   │     _PROJECT.md        │                 ┌──────────────────┐
   │     ADRs/              │                 │    FalkorDB      │
   │     bugs/              │                 │  (Docker local)  │
   │ brain/ (topic notes)   │                 │                  │
   │ daily/ (journal)       │                 │  group_id:       │
   └────────────────────────┘                 │  react-dashboard │
          │                                   │  flutter-app     │
          │ Obsidian Git                       │  python-api      │
          ▼                                   │  dev-global      │
   Git repo (backup)                          └────────┬─────────┘
   + OneDrive sync (.md)                               │
                                                       │ BGSAVE cada 4h
                                                       ▼
                                              OneDrive/DevSetup/
                                              graphiti-data/backups/
                                              graphiti_20260712.rdb
```

---

## 4. Flujo de trabajo diario

### Al iniciar una sesión de Claude Code

Claude Code ejecuta automáticamente (via CLAUDE.md + hooks):

1. **Carga** CLAUDE.md global + CLAUDE.md del proyecto
2. **Busca** en Graphiti: `search_facts(query="recent decisions and issues", group_ids=["proyecto", "dev-global"])`
3. **Lee** el `_PROJECT.md` del proyecto en Obsidian (via `@import` en CLAUDE.md)
4. Si es primera sesión en el proyecto: `graphify update .` para actualizar el grafo del codebase
5. Inicia la conversación con contexto completo sin que el desarrollador explique nada

### Durante la sesión

- Al tomar una decisión de arquitectura: Claude crea/actualiza el ADR en Obsidian y guarda un episodio en Graphiti
- Al resolver un bug no-obvio: Claude documenta en Obsidian y guarda en Graphiti
- Al implementar features: Claude consulta Graphify para entender la estructura antes de tocar archivos
- Context7 se activa automáticamente cuando Claude necesita documentación de librerías

### Al cerrar la sesión

1. Claude actualiza `_PROJECT.md` con el estado actual del proyecto
2. Añade entrada en daily note de Obsidian
3. Hook Stop: `backup-graph.sh` (si hay cambios en Graphiti)
4. Obsidian Git auto-commit con los cambios del vault

---

## 5. Plan de implementación por fases

### Fase 0 — Fundación (Día 1, ~2 horas)

**Objetivo**: Setup mínimo funcional que mejora inmediatamente.

- [ ] Instalar Superpowers: `/plugin install superpowers@claude-plugins-official`
- [ ] Optimizar CLAUDE.md global (< 500 tokens, patrón WHY/WHAT/HOW)
- [ ] Instalar Context7 MCP: `claude mcp add context7 -s user -- npx -y @upstash/context7-mcp@latest`
- [ ] Instalar Graphify: `uv tool install graphifyy && graphify install`
- [ ] Crear vault Obsidian en `~/OneDrive/DevSetup/ObsidianVault/`
- [ ] Instalar plugin Obsidian Git (auto-commit 10 min)

**Resultado**: Claude Code ya tiene acceso a documentación actualizada, metodología mejorada, y un grafo del codebase.

### Fase 1 — Memoria de sesiones (Días 2-3, ~3 horas)

**Objetivo**: Claude recuerda entre sesiones.

- [ ] Estructurar vault Obsidian (PARA + brain/ + daily/ + templates/)
- [ ] Instalar plugins: Templater, Dataview, Periodic Notes, Smart Connections
- [ ] Instalar Obsidian MCP: `claude mcp add obsidian-vault -s user -- npx -y @modelcontextprotocol/server-filesystem ~/OneDrive/DevSetup/ObsidianVault`
- [ ] Crear `_PROJECT.md` para cada proyecto activo
- [ ] Añadir sección Memory en CLAUDE.md de cada proyecto
- [ ] Crear ADRs retroactivos de las decisiones más importantes

**Resultado**: Claude recuerda el contexto de proyectos entre sesiones usando el vault.

### Fase 2 — Multi-dispositivo (Días 4-5, ~2 horas)

**Objetivo**: mismo setup en todas las laptops.

- [ ] Crear repo `claude-dotfiles` privado en GitHub
- [ ] Definir allowlist de archivos a versionar (CLAUDE.md, settings.json, agents/, skills/)
- [ ] Crear scripts `setup.sh` / `setup.ps1` de bootstrap
- [ ] Configurar aliases `claude-personal`, `claude-work` con `CLAUDE_CONFIG_DIR`
- [ ] Verificar que vault de Obsidian sincroniza correctamente en OneDrive
- [ ] Replicar setup en laptop 2 usando el script de bootstrap

**Resultado**: nueva laptop bootstrap en < 15 minutos.

### Fase 3 — Memoria temporal con Graphiti (Semana 2, ~3 horas)

**Objetivo**: grafo temporal para proyectos con hechos que cambian.

- [ ] Instalar Docker Desktop
- [ ] Clonar config de docker-compose.yml desde dotfiles
- [ ] Crear `.env` con API keys (OpenAI para extracción, no Anthropic)
- [ ] `docker compose up -d` — verificar que FalkorDB y MCP server arrancan
- [ ] `claude mcp add --transport http graphiti-memory http://localhost:8000/mcp/ -s user`
- [ ] Añadir sección Memory con instrucciones Graphiti en CLAUDE.md de cada proyecto
- [ ] Copiar `.graphiti.json` template a cada proyecto (ajustar `group_id`)
- [ ] Configurar cron/Task Scheduler para `backup-graph.sh` cada 4 horas
- [ ] Primera sesión de "onboarding" en cada proyecto (Claude guarda contexto inicial)

**Resultado**: memoria temporal funcionando con backups automáticos a OneDrive.

### Fase 4 — Stack-specific polish (Semana 3, ongoing)

**Objetivo**: optimizaciones específicas por lenguaje.

**C++:**
- [ ] `/plugin install clangd-lsp@claude-plugins-official`
- [ ] Verificar que CMake genera `compile_commands.json`
- [ ] CLAUDE.md de proyecto con checklist C++ Core Guidelines

**Flutter:**
- [ ] Instalar subagent `flutter-expert`
- [ ] Configurar Context7 con docs de Riverpod y Flutter 3.x

**React/Next.js:**
- [ ] Hook PostToolUse con Prettier para JSX/TSX
- [ ] Considerar Playwright MCP para verificación visual

**Python:**
- [ ] Subagent `python-expert`
- [ ] Verificar que uv está configurado como gestor de paquetes en CLAUDE.md

---

## 6. Métricas de éxito

¿Cómo saber si la arquitectura está funcionando?

| Métrica | Baseline (sin setup) | Objetivo |
|---------|---------------------|----------|
| Tokens por sesión (proyecto conocido) | 50,000–150,000 | < 15,000 |
| Tiempo re-explicando contexto | 10-20 min/sesión | < 2 min |
| Decisiones de arquitectura revertidas | Frecuente | Raro |
| Tiempo de bootstrap en laptop nueva | 2-4 horas | < 20 minutos |
| Búsqueda de "dónde está X en el código" | Claude lee 20-50 archivos | 1 consulta al grafo |

---

## 7. Anti-patrones a evitar

### Anti-patrón 1: CLAUDE.md como enciclopedia

Un CLAUDE.md de 3,847 tokens (generado automáticamente) carga 12× más overhead que uno de 312 tokens sin ganancia proporcional en calidad. Claude empieza a ignorar secciones después de ~150 instrucciones. La solución es Skills con progressive disclosure.

### Anti-patrón 2: Dump de memoria completo en cada sesión

Configurar Graphiti o Obsidian para cargar toda la memoria disponible al inicio de cada sesión produce el efecto opuesto: más tokens consumidos que ahorrados, con contexto irrelevante que contamina el razonamiento. El retrieval selectivo siempre gana al dump masivo.

### Anti-patrón 3: Demasiados MCPs conectados simultáneamente

Conectar 15 MCPs "por si acaso" agrega 150,000–300,000 tokens de overhead de esquemas. Conectar solo los MCPs necesarios para la sesión actual es fundamental. `ENABLE_TOOL_SEARCH` ayuda, pero no es sustituto de disciplina en la selección de MCPs.

### Anti-patrón 4: Sincronizar el directorio de datos de FalkorDB con OneDrive activo

El riesgo de corrupción es bajo pero existe, y la corrupción puede ser silenciosa. La Estrategia A (datos locales + backups periódicos) es la opción segura.

### Anti-patrón 5: Credenciales en git

`.env` con API keys, `.credentials.json` de Claude — nunca en git, nunca en OneDrive sin cifrado. El costo de una filtración de API keys supera cualquier conveniencia de sincronización.

---

## 8. Referencias y fuentes primarias

| Fuente | URL | Relevancia |
|--------|-----|-----------|
| obra/Superpowers | github.com/obra/Superpowers | Framework Skills oficial |
| Graphify | github.com/Graphify-Labs/graphify | Grafo de codebase |
| getzep/graphiti | github.com/getzep/graphiti | Grafo temporal MCP |
| FalkorDB Docs | docs.falkordb.com | Persistencia Docker |
| Graphiti PR #1209 | github.com/getzep/graphiti/pull/1209 | Arquitectura unificada group_id |
| Zylos Research | zylos.ai/research/2026-04-05... | Arquitecturas de memoria mid-2026 |
| lucasrosati/claude-code-memory-setup | github.com/lucasrosati/... | Caso 71.5× reducción tokens |
| Agent Memory Systems (CodePointer) | codepointer.substack.com | Comparativa Mem0/Letta/Graphiti/Cognee |
| Claude Code Token Efficiency | firecrawl.dev/blog/claude-code-token-efficiency | 12 formas de reducir tokens |
| Mem0 PR #4805 | github.com/mem0ai/mem0/pull/4805 | Eliminación del grafo OSS |
| FalkorDB Docker Docs | docs.falkordb.com/operations/docker.html | Persistencia y volúmenes |
| Microsoft OneDrive Symlinks | support.microsoft.com | Limitación documentada de symlinks |

---

*Este documento forma parte de la serie de investigación sobre arquitectura de memoria para Claude Code.*  
*Fecha: Julio 2026 | Válido para: Claude Code 2.x, Graphiti 0.17+, Graphify 0.5.x*
