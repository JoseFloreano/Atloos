# Skills y Frameworks Agénticos para Claude Code
## Catálogo justificado: Superpowers, Graphify, MCPs y subagents por stack

---

## 1. La jerarquía de extensibilidad de Claude Code

Claude Code organiza sus extensiones en capas con distintos niveles de alcance y persistencia:

```
CLAUDE.md global       → instrucciones siempre presentes (cargadas en todo contexto)
    │
    ├── Skills         → instrucciones modulares (progressive disclosure — se cargan cuando son relevantes)
    ├── Commands       → acciones slash (ahora absorbidos por Skills en Claude Code 2.x)
    ├── Subagents      → instancias Claude aisladas con contexto propio
    ├── Plugins        → contenedor empaquetable (skills + hooks + MCPs + agents)
    ├── Hooks          → scripts deterministas en eventos del ciclo de vida
    └── MCP Servers    → herramientas externas via Model Context Protocol
```

**Principio clave**: las Skills se cargan por *progressive disclosure* — Claude solo las carga cuando son relevantes para la tarea actual. Un CLAUDE.md que lista Skills no carga su contenido completo en cada sesión; solo carga el nombre y descripción. Esto hace que tener muchas Skills sea eficiente en tokens.

---

## 2. obra/Superpowers: el framework de metodología

### Qué es

`obra/Superpowers` es el framework agéntico de referencia, creado por Jesse Vincent (ex-Anthropic, Prime Radiant). No es un framework de código — es una **metodología de desarrollo de software** para agentes, implementada como 14 Skills para Claude Code.

Disponible en el marketplace oficial de Anthropic desde enero 2026:

```bash
/plugin install superpowers@claude-plugins-official
```

### Las 14 Skills incluidas

| Skill | Qué hace |
|-------|----------|
| `verification-before-completion` | Claude verifica su trabajo antes de marcar como hecho |
| `subagent-driven-development` | Usar subagents para paralelizar tareas |
| `test-driven-development` | TDD como metodología para el agente |
| `brainstorming` | Sesión estructurada de exploración de ideas |
| `writing-plans` | Generar planes detallados antes de implementar |
| `using-git-worktrees` | Patrones de git worktrees para desarrollo paralelo |
| `systematic-debugging` | Protocolo de debugging paso a paso |
| + 7 más | Metodologías adicionales de desarrollo |

### Por qué es zero-dependency

Las Skills de Superpowers son archivos SKILL.md con frontmatter YAML — sin dependencias npm, pip o binarios. Se instalan como parte del plugin en `~/.claude/plugins/`. No agregan overhead de MCP ni requieren servicios externos.

### Los comandos más útiles

```bash
/superpowers:brainstorm    # Sesión de exploración antes de implementar
/write-plan                # Plan detallado antes de codificar
/execute-plan              # Ejecutar el plan paso a paso con verificación
```

**Cuándo usar Brainstorm:** antes de iniciar una feature compleja, para explorar el espacio de soluciones sin commitear a una dirección prematuramente.

**Cuándo usar Write-Plan:** cuando la tarea tiene múltiples pasos interdependientes. El plan actúa como anchor para que Claude no se pierda a mitad de la implementación.

---

## 3. Graphify: el grafo del codebase

### Qué es (revisitado desde la perspectiva de skills)

Graphify se instala como skill de Claude Code:

```bash
graphify install               # registra el skill en tu perfil global
graphify install --project     # registra en el proyecto actual (commiteable)
```

Después de instalar, disponible como:

```bash
/graphify .                    # analiza el directorio actual
/graphify . --include "*.dart" # solo archivos Dart
/graphify . --out custom-dir   # directorio de salida personalizado
```

### Por stack: cómo configurar Graphify

**React / Next.js:**
```bash
# En la raíz del monorepo (si tienes múltiples packages):
graphify merge-graphs \
  apps/dashboard/graphify-out/graph.json \
  packages/ui/graphify-out/graph.json

# Cross-repo merge (nuevo en v0.5.0):
graphify merge-graphs repo1/graphify-out/graph.json repo2/graphify-out/graph.json
```

**Flutter / Dart:**
```bash
# Graphify soporta Dart via tree-sitter
/graphify . --include "*.dart"
# Genera grafo de providers, widgets, y dependencias
```

**Python:**
```bash
/graphify .  # detecta automáticamente .py
# Genera grafo de clases, funciones, imports, decoradores
```

**C++ / CMake:**
```bash
# Requiere compile_commands.json para resolución de tipos
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ..
/graphify . --include "*.cpp,*.h,*.hpp"
# Combinar con clangd-lsp para resolución de símbolos completa
```

### El GRAPH_REPORT.md como puente Obsidian-Graphify

Graphify genera `graphify-out/GRAPH_REPORT.md` con formato compatible con Obsidian (wikilinks, frontmatter YAML). Este archivo puede copiarse al vault:

```bash
# En hook post-commit de git:
cp graphify-out/GRAPH_REPORT.md \
   ~/OneDrive/DevSetup/ObsidianVault/10-Projects/[proyecto]/graph-report.md
```

Resultado: el grafo del codebase es navegable tanto desde Claude Code (via Graphify skill) como desde Obsidian (via wikilinks).

---

## 4. Los MCPs esenciales: justificación y configuración

### ¿Cuántos MCPs son demasiados?

**Datos medidos**: cada MCP agrega 10,000–20,000 tokens de esquema de herramientas al inicio de cada sesión. Con 5 MCPs = hasta 70,000 tokens de overhead silencioso.

`ENABLE_TOOL_SEARCH` (activo desde Claude Code 2.1.7, enero 2026) carga schemas lazy — solo cuando Claude necesita esa herramienta específica. Esto reduce el overhead de 70,000 a ~8,700 tokens (85% menos).

**Regla práctica**: máximo 8-10 MCPs conectados, con `ENABLE_TOOL_SEARCH` activo. Desconectar MCPs que no se usan en la sesión actual.

### Los 6 MCPs esenciales

#### 1. Filesystem — acceso a archivos del proyecto

```bash
claude mcp add filesystem -s user -- \
  npx -y @modelcontextprotocol/server-filesystem /ruta/al/proyecto
```

Justificación: Claude Code ya tiene acceso a archivos, pero el MCP de filesystem permite acceso explícito y controlado a directorios específicos fuera del proyecto actual (ej: el vault de Obsidian, carpetas de referencia).

#### 2. GitHub — integración con repositorios

```bash
claude mcp add --transport http github \
  https://api.githubcopilot.com/mcp/
```

Justificación: issues, PRs, CI status, búsqueda cross-repo. Especialmente valioso para C++ con proyectos de múltiples repositorios y Flutter con packages externos.

#### 3. Context7 — documentación en vivo

```bash
claude mcp add context7 -s user -- \
  npx -y @upstash/context7-mcp@latest
```

Justificación crítica: Claude fue entrenado con documentación hasta agosto 2025. Next.js 16, Flutter 3.x, React 19 — sus APIs pueden haber cambiado. Context7 inyecta la documentación actualizada de la versión exacta que estás usando, evitando que Claude genere APIs deprecadas.

Por stack:
- React/Next.js: docs de App Router, Server Components, React 19 concurrent features
- Flutter: docs de Riverpod, Hooks, Material 3
- Python: docs de FastAPI, Pydantic v2, asyncio
- C++: docs de CMake moderno, Conan, C++23

#### 4. Playwright — verificación visual en navegador

```bash
claude mcp add playwright -s user -- \
  npx -y @playwright/mcp@latest
```

Justificación: para proyectos React/Next.js, permite a Claude verificar el resultado visual de su trabajo en un navegador real, no solo analizar el código. El snapshot de Playwright antes de interactuar es el patrón recomendado.

#### 5. Sequential Thinking — razonamiento estructurado

```bash
claude mcp add sequential-thinking -s user -- \
  npx -y @modelcontextprotocol/server-sequential-thinking
```

Justificación: para problemas complejos de C++ o debugging de Flutter, fuerza a Claude a pensar paso a paso con revisión explícita antes de concluir. Reduce errores en razonamiento multi-paso.

#### 6. Graphiti Memory — memoria temporal (ver doc 03)

```bash
claude mcp add --transport http graphiti-memory \
  http://localhost:8000/mcp/ -s user
```

### MCPs adicionales por stack específico

**Para C++ / CMake:**
```bash
# clangd-lsp — inteligencia de símbolos C/C++ via Language Server
/plugin install clangd-lsp@claude-plugins-official

# Alternativa: servidor MCP de clangd
claude mcp add clangd -s project -- felipeerias/clangd-mcp-server
# Requiere: compile_commands.json generado por CMake
```

**Para React/Next.js:**
```bash
# Figma — para implementar designs exactamente
claude mcp add --transport http figma \
  https://mcp.figma.com/mcp

# Next.js DevTools — detectar errores de hidratación, routes, logs
claude mcp add next-devtools -s project -- npx next-devtools-mcp
```

**Para Flutter:**
No hay MCP específico de Flutter, pero Context7 con las docs de Riverpod y Flutter es suficiente para el 95% de los casos.

---

## 5. Subagents: cuándo y cómo usarlos

### El concepto

Un subagent es una instancia de Claude separada con su propio contexto aislado. Devuelve solo el resultado, protegiendo la ventana de contexto del agente principal.

```
Agente principal (ventana de contexto limitada)
    ├── Subagent A: "Implementa el componente de auth" (contexto aislado)
    ├── Subagent B: "Escribe tests para auth" (contexto aislado)
    └── Subagent C: "Revisa seguridad de la implementación" (contexto aislado)
```

### Cuándo usar subagents

**Sí usar:**
- Tareas paralelizables que no se afectan entre sí
- Tareas que consumen mucho contexto (leer muchos archivos)
- Validación o revisión independiente del trabajo principal
- Operaciones de un solo tipo (solo lectura, solo tests, solo documentación)

**No usar:**
- Cuando las subtareas se afectan entre sí (dependencias)
- Para tareas simples que no justifican el overhead de coordinación
- Cuando necesitas que el subagent tenga el historial del agente principal

### Subagents recomendados por stack

Del repositorio `VoltAgent/awesome-claude-code-subagents` (100+ subagents especializados):

```markdown
# Para Flutter:
flutter-expert          → UI components, Riverpod, testing
dart-analyzer           → análisis de código Dart

# Para Python:
python-expert           → FastAPI, async, testing con pytest
python-security         → análisis de seguridad

# Para React/Next.js:
react-specialist        → componentes, hooks, performance
nextjs-expert           → App Router, Server Components, RSC

# Para C++:
cpp-pro                 → CMake, templates, modern C++
cpp-security            → análisis de vulnerabilidades

# Universales:
code-reviewer           → revisión de PRs
test-writer             → generación de tests
doc-writer              → documentación de APIs
```

---

## 6. Hooks: control determinista del ciclo de vida

### Los hooks más valiosos documentados

**Formateo automático post-escritura (PostToolUse):**
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": "npx prettier --write \"$CLAUDE_TOOL_INPUT_FILE_PATH\" 2>/dev/null || true"
      }]
    }]
  }
}
```
Justificación: "CLAUDE.md dice qué hacer; los hooks lo garantizan."

**Seguridad — bloquear comandos peligrosos (PreToolUse):**

> El matcher es `Bash|PowerShell`, no `Bash` a secas: las dos herramientas
> entregan el comando en el mismo `tool_input.command`, y en Windows la de
> PowerShell va por despliegue progresivo. Un ejemplo con `Bash` solo enseña la
> frontera mal dibujada que este repo ya pagó tres veces (sprint 7).
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash|PowerShell",
      "hooks": [{
        "type": "command",
        "command": "echo \"$CLAUDE_TOOL_INPUT\" | grep -qE 'rm -rf /|DROP TABLE|DELETE FROM' && exit 2 || exit 0"
      }]
    }]
  }
}
```

**Actualización automática del grafo post-commit:**
```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "git diff --name-only HEAD~1 2>/dev/null | grep -q '\\.' && graphify update . --quiet || true"
      }]
    }]
  }
}
```

---

## 7. Tabla de decisión: qué instalar primero

Para empezar desde cero con el stack React + Flutter + Python + C++:

| Prioridad | Componente | Tiempo setup | Impacto |
|-----------|------------|--------------|---------|
| 1 | Superpowers plugin | 2 min | Mejora metodología inmediatamente |
| 2 | CLAUDE.md global optimizado (<500 tokens) | 30 min | Base de todo |
| 3 | Context7 MCP | 5 min | Evita APIs deprecadas |
| 4 | Graphify instalado y skip inicial | 10 min | Grafo del codebase |
| 5 | Obsidian vault + Git | 30 min | Memoria de sesiones |
| 6 | clangd-lsp (si C++ es prioridad) | 15 min | Inteligencia C++ |
| 7 | Graphiti + Docker (si necesitas temporal) | 2-3 horas | Memoria temporal avanzada |

---

*Siguiente: [Arquitectura Final Recomendada](./06-ARQUITECTURA-FINAL-RECOMENDADA.md)*
