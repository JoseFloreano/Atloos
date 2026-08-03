# Investigación Técnica: Arquitectura de Memoria y Productividad para Claude Code
## Índice General y Resumen Ejecutivo

> **Fecha de investigación:** Julio 2026  
> **Alcance:** Setup multi-laptop (2-3 dispositivos), múltiples cuentas Claude, sincronización OneDrive  
> **Stack objetivo:** React/JSX, Flutter/Dart, Python, C++ y más

---

## Índice de Documentos

| # | Documento | Tema central |
|---|-----------|--------------|
| 01 | [Obsidian como Memoria Externa](./01-OBSIDIAN-MEMORIA-EXTERNA.md) | Por qué Obsidian, estructura de vault, plugins, MCP |
| 02 | [Grafos vs Markdown: Análisis Comparativo](./02-GRAFOS-VS-MARKDOWN.md) | Cuándo usar cada sistema, benchmarks, hallazgos críticos |
| 03 | [Graphiti + FalkorDB: Memoria Temporal](./03-GRAPHITI-FALKORDB-MEMORIA-TEMPORAL.md) | Arquitectura de grafo temporal, setup Docker, aislamiento multi-proyecto |
| 04 | [OneDrive: Estrategias de Sincronización](./04-ONEDRIVE-SINCRONIZACION-MULTI-LAPTOP.md) | Estrategias A/B/C, riesgos documentados, protocolo multi-laptop |
| 05 | [Skills y Frameworks Agénticos](./05-SKILLS-FRAMEWORKS-AGENTICOS.md) | Superpowers, Graphify, MCPs esenciales por stack |
| 06 | [Arquitectura Final Recomendada](./06-ARQUITECTURA-FINAL-RECOMENDADA.md) | Decisión consolidada, diagrama, plan de implementación |
| 07 | [Hallazgos Críticos H1–H10](./07-HALLAZGOS-CRITICOS-REFERENCIA-RAPIDA.md) | ⭐ Referencia rápida — leer antes de cualquier decisión |
| 08 | [Graphiti con DeepSeek: costo](./08-GRAPHITI-DEEPSEEK-COSTO.md) | Compatibilidad, palancas de ahorro y config para cuando se active |
| 08b | [Resumen funcional DeepSeek](./08b-RESUMEN-FUNCIONAL-DEEPSEEK.md) | Complemento operativo del 08 |
| RFD 10 | [Graphiti: errores de integración](./10-RFD-GRAPHITI-INTEGRACION-ERRORES.md) | Draft — 8 errores y propuesta de skills en vez de MCP HTTP |
| 11 | [Graphiti: guía rápida de setup](./11-GRAPHITI-SETUP-GUIA-RAPIDA.md) | DeepSeek + Ollama; deriva del RFD 10 |

---

## Resumen Ejecutivo

### El problema que resuelve esta investigación

Claude Code es una herramienta de IA extremadamente potente, pero tiene una limitación estructural fundamental: **cada sesión comienza desde cero**. No hay memoria de sesiones anteriores, no hay contexto acumulado del proyecto, no hay recuerdo de decisiones de arquitectura tomadas la semana pasada.

Para un desarrollador trabajando en 2-3 laptops con múltiples proyectos simultáneos (React, Flutter, Python, C++), esto se traduce en:

- Re-explicar el contexto del proyecto en cada sesión
- Claude re-leyendo cientos de archivos que ya "conocía" la sesión anterior
- Decisiones de arquitectura olvidadas y potencialmente revertidas
- Convenciones de código que el agente ignora repetidamente
- Tokens y dinero desperdiciados en contexto que debería ser persistente

### Las tres capas del problema

```
Capa 1: CONTEXTO DE CODEBASE
"Claude, ¿qué función llama a AuthService?"
→ Sin grafo: Claude lee 200 archivos para responder
→ Con grafo: 1 consulta, resultado en <1ms

Capa 2: MEMORIA DE SESIONES
"Recuerda que decidimos usar Riverpod sobre Bloc porque..."
→ Sin memoria: re-explicar en cada sesión
→ Con Graphiti/Obsidian: recuperado automáticamente

Capa 3: CONFIG MULTI-DISPOSITIVO
"Mismo setup en laptop del trabajo y en casa"
→ Sin estrategia: configurar desde cero cada vez
→ Con OneDrive + git dotfiles: bootstrap en 5 minutos
```

### Hallazgos críticos de la investigación

**Hallazgo 1 — Los grafos no siempre ganan:**  
Mem0 eliminó su capa de grafo en v3 OSS (abril 2026) porque en benchmarks el grafo perdía en consultas simples, era 3× más lento y costaba 2× más tokens. Los grafos son superiores para relaciones complejas y consultas temporales, no para recuperación simple de hechos.

**Hallazgo 2 — Archivos planos son más potentes de lo esperado:**  
Letta demostró en agosto 2025 que poner transcripciones en archivos planos logra 74% en el benchmark LOCOMO de memoria, por encima del 68.5% del grafo de Mem0. Los LLMs modernos están entrenados para búsqueda iterativa en archivos.

**Hallazgo 3 — OneDrive + FalkorDB es incompatible directamente:**  
FalkorDB mantiene locks activos sobre `dump.rdb` y `appendonly.aof`. OneDrive puede interrumpir escrituras mid-snapshot. La solución es datos locales + snapshots periódicos a OneDrive, no sincronización directa del directorio de datos.

**Hallazgo 4 — El costo de tokens viene de los MCPs, no del código:**  
Cada MCP conectado carga 10,000–20,000 tokens de esquema en cada sesión. 5 MCPs = hasta 70,000 tokens de overhead silencioso antes de escribir una sola línea. `ENABLE_TOOL_SEARCH` reduce esto en ~85%.

**Hallazgo 5 — Graphify en modo AST puro no consume tokens propios:**  
El primer pass de Graphify usa Tree-sitter (análisis estático) — cero llamadas a LLM, cero costo. El grafo del codebase se construye gratuitamente. Solo el segundo pass (PDFs, imágenes, markdown semántico) usa LLM.

### Arquitectura recomendada (decisión final)

```
┌─────────────────────────────────────────────────────────┐
│                    CLAUDE CODE                          │
│  CLAUDE.md global (<500 tokens)                         │
│  Skills: Superpowers + Graphify                         │
│  MCPs activos: filesystem, github, context7,            │
│               graphiti-memory, obsidian                 │
└─────────────────┬───────────────────────────────────────┘
                  │
     ┌────────────┴─────────────┐
     │                         │
     ▼                         ▼
GRAFO DE CODEBASE         MEMORIA DE SESIONES
(Graphify / AST)          (Graphiti + Obsidian)
  0 tokens propios          ~500ms por escritura
  Graphify-out/             FalkorDB local
  persistente               Backups → OneDrive
  por proyecto              group_id por proyecto
```

### Principio guía

> **El retrieval gana sobre el dump.**  
> Un sistema de memoria que carga todo en contexto en cada sesión gasta más tokens de los que ahorra. La arquitectura correcta carga solo lo que se necesita, cuando se necesita, desde la fuente más eficiente para ese tipo de dato.

---

*Continúa en los documentos individuales para análisis detallado de cada capa.*
