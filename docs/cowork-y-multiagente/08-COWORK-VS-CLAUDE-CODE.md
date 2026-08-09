# Cowork vs Claude Code: Análisis por Tipo de Tarea
## En qué es mejor cada uno y qué implica para el setup estándar compartido

> **Fecha:** Julio 2026
> **Contexto:** Extiende la investigación de los docs 00–07 (basada solo en Claude Code) hacia un setup estándar para ambos productos, con variaciones mínimas por producto.
> **Metodología:** Capacidades verificadas contra documentación oficial de Anthropic (support.claude.com, julio 2026) + observación directa del entorno de Cowork. Se marca explícitamente lo que es inferencia.

---

## 1. El modelo mental: no son competidores, son superficies distintas del mismo motor

Anthropic documenta que Cowork usa "la misma arquitectura agéntica que Claude Code, sin terminal". La diferencia no está en el modelo ni en la metodología — está en **dónde se ejecuta y a qué tiene acceso**:

```
CLAUDE CODE (CLI)                       COWORK
─────────────────────                   ─────────────────────
Corre EN tu laptop                      Corre en un sandbox cloud de Anthropic
Acceso directo al filesystem            Acceso a tu disco vía "puente" del
y toolchain local (compiladores,        desktop app: carpetas conectadas,
Docker, emuladores, git)                staging de archivos (snapshots)

Sesión atada a la terminal              Sesión persistente cross-device
donde la abriste                        (empiezas en desktop, sigues en móvil)

Muere si cierras la laptop              Sigue trabajando con la laptop cerrada

localhost es TU localhost               localhost es el del container cloud
(Graphiti MCP :8000 directo)            (tu :8000 NO es alcanzable directo)

Config: CLAUDE.md, settings.json,       Config: instrucciones de proyecto,
hooks, CLAUDE_CONFIG_DIR                carpetas conectadas, connectors,
                                        plugins, scheduled tasks
```

Dos detalles del sandbox de Cowork que cambian decisiones (observados directamente):

1. **El container cloud tiene red completa** (npm, pip, git clone, web) y persiste durante la sesión. Es un Linux real donde Claude puede instalar y ejecutar lo que necesite — pero es **efímero**: se recicla al terminar la sesión.
2. **La VM local del desktop app (donde Cowork toca tus archivos) NO tiene red** y no ve el resto de tu máquina — solo las carpetas que conectaste. No puede ejecutar Docker de tu host, ni `flutter run`, ni tocar `~/.claude/`.

**Implicación central**: todo lo que en los docs 00–07 asume "Claude vive en tu máquina" (MCPs en localhost, hooks sobre tu filesystem, Graphify sobre repos locales, Docker) es territorio natural de Claude Code. Todo lo que asume "trabajo largo, investigación, documentos, no depende de tu toolchain" es territorio natural de Cowork.

---

## 2. Tabla comparativa de capacidades (verificada)

| Capacidad | Claude Code | Cowork | Notas |
|-----------|-------------|--------|-------|
| Ejecución de código | En tu máquina (toolchain real) | Sandbox cloud (Linux efímero) | Cowork no puede compilar contra tu entorno local |
| Acceso a archivos locales | Directo, en vivo | Vía puente: snapshot al leer, commit explícito al escribir | Requiere desktop app abierto |
| MCPs localhost (Graphiti :8000) | ✅ Directo | ⚠️ Solo como MCP local proxied por el desktop app | Docs oficiales: "local connectors requiring MCP servers function exclusively through the desktop app" |
| Connectors remotos (GitHub, Drive, Slack) | ✅ | ✅ (registry integrado, más fácil) | |
| CLAUDE.md automático | ✅ | ❌ — usa instrucciones globales/por proyecto y archivos de contexto en carpetas conectadas | El equivalente funcional existe, el mecanismo es otro |
| Skills (SKILL.md, progressive disclosure) | ✅ | ✅ (vía plugins; trae skills de documentos preinstaladas) | |
| Plugins (marketplace) | ✅ | ✅ — hooks y subagents de plugins funcionan en Cowork y Code, no en chat web | Docs oficiales de plugins |
| Hooks sobre TU filesystem (prettier post-write, etc.) | ✅ | ❌ en tu disco (el hook correría en el sandbox) | |
| Subagents / orquestación paralela | ✅ | ✅ (+ workflows de fan-out masivo) | |
| Scheduled tasks | ⚠️ Requiere tu máquina encendida (cron/Task Scheduler) | ✅ Corren en la nube sin que tu laptop exista | Ventaja estructural de Cowork |
| Sesión persistente cross-device / móvil | ❌ | ✅ | |
| Trabajo desatendido largo | ⚠️ Terminal abierta | ✅ Diseñado para eso | |
| Tool search / lazy loading de schemas MCP | Opt-in (`ENABLE_TOOL_SEARCH`) | ✅ Nativo por defecto (deferred tools) | El hallazgo H3 ya viene mitigado de fábrica en Cowork |
| Browser automation | Vía Playwright MCP | Vía Claude in Chrome (tu Chrome real, con tus sesiones) | Enfoques distintos: browser limpio vs tu browser logueado |
| Computer use (clic/teclado en tu desktop) | ❌ | ✅ (desktop app) | |
| Multi-cuenta | `CLAUDE_CONFIG_DIR` + aliases | Cambio de cuenta en el app (sin equivalente a CONFIG_DIR) | |
| Generación de documentos (docx/xlsx/pptx/pdf) | Posible pero manual | ✅ Skills dedicadas preinstaladas | |
| Artifacts persistentes (dashboards HTML) | ❌ | ✅ (galería del desktop app) | |
| Costo de uso | Según plan/API | Consume "significativamente más" cuota que chat (docs oficiales) | |

---

## 3. En qué es mejor Claude Code

### 3.1 Todo el ciclo de desarrollo activo sobre repos locales

Compilar C++ con tu CMake y tu `compile_commands.json`, `flutter run` con hot reload contra emulador, pytest contra tu venv, npm dev server, git worktrees. Cowork no puede ejecutar nada de esto **contra tu entorno**: su VM local no tiene red ni toolchain, y su sandbox cloud no es tu máquina. Este es el caso de uso para el que se hizo toda la arquitectura de los docs 00–07.

### 3.2 El stack de memoria tal como está diseñado

- **Graphiti MCP en localhost:8000**: conexión directa, sin puente, sin depender de que el desktop app esté abierto.
- **Graphify**: corre como CLI sobre el repo local; el hook post-commit que actualiza el grafo solo tiene sentido donde vive el repo.
- **Hooks deterministas** (PostToolUse con Prettier, PreToolUse de seguridad, Stop con backup-graph.sh): son un mecanismo de Claude Code sobre tu filesystem. En Cowork no existen sobre tu disco.
- **clangd-lsp**: necesita el language server corriendo junto al código.

### 3.3 Iteración rápida con feedback inmediato

Cuando el loop es "edita → compila → mira el error → edita", la latencia del puente de Cowork (stage → editar en cloud → commit de vuelta) es inaceptable. Claude Code edita en vivo.

### 3.4 Control fino de contexto y tokens

`CLAUDE.md` < 500 tokens, rules con path scoping, elegir MCPs por sesión, `/compact` — el control granular del hallazgo H4 es de Claude Code. En Cowork el overhead base lo gestiona el producto (bien, pero sin tu control).

### 3.5 Trabajo offline o con datos sensibles que no deben salir de tu máquina

Claude Code procesa localmente (las llamadas al modelo van a la API, pero los archivos no se suben a un sandbox). En Cowork, todo archivo con el que trabaja se copia al container cloud.

---

## 4. En qué es mejor Cowork

### 4.1 Investigación continua (exactamente lo que estás haciendo ahora)

Búsqueda web paralela, fetch de docs, síntesis con fuentes, workflows de verificación adversarial multi-agente. La sesión no muere si cierras la laptop, y puedes revisar avances desde el teléfono. Para "seguir investigando opciones para mejorar el setup" — este documento incluido — Cowork es la herramienta correcta.

### 4.2 Tareas largas desatendidas y programadas

Scheduled tasks corren en la nube **sin que ninguna laptop esté encendida** — algo que Claude Code no puede ofrecer estructuralmente. Casos para tu setup: digest semanal de novedades de Graphiti/Graphify/Superpowers (releases, breaking changes), auditoría periódica del vault (duplicados, notas sin wikilinks, frontmatter faltante), reporte de estado del proyecto. Matiz importante: una scheduled task solo puede tocar tu disco si el desktop app está abierto en ese momento; para trabajo puramente cloud (investigar, redactar, avisar) no necesita nada.

### 4.3 Curación masiva del vault de Obsidian

El vault son archivos .md en OneDrive — Cowork los stage-ea por lotes (hasta 50 por llamada), procesa en el sandbox y commitea de vuelta. Ideal para trabajo estructural en frío: crear los ADRs retroactivos de la Fase 1, normalizar frontmatter en 200 notas, detectar duplicados (>80% similitud), generar índices con Dataview-queries, fusionar notas. Claude Code puede hacerlo también, pero gasta tu sesión de trabajo; en Cowork lo delegas y te vas. **La escritura en caliente** (documentar la decisión que acabas de tomar mientras codeas) sigue siendo de Claude Code.

### 4.4 Documentos como entregable

Reportes en Word, presentaciones, spreadsheets con fórmulas, PDFs — Cowork trae skills dedicadas preinstaladas. Para el análisis, la documentación y los reportes de este proyecto, es el camino corto.

### 4.5 Tu browser real (Claude in Chrome)

Playwright MCP en Claude Code levanta un browser limpio. Claude in Chrome opera tu Chrome con tus sesiones ya iniciadas: revisar un dashboard interno, GitHub logueado, probar un flujo que requiere tu cuenta. Complementarios, no equivalentes.

### 4.6 Prototipos y experimentos sin ensuciar tu máquina

El sandbox cloud instala lo que quiera (pip, npm, binarios) y desaparece al terminar. Perfecto para "prueba si esta librería hace X" sin tocar tus venvs. Contra-cara: como es efímero, cualquier setup se reconstruye por sesión — no sirve para infra persistente como FalkorDB.

### 4.7 Artifacts persistentes

Dashboards HTML que viven en la galería del desktop app y se actualizan entre sesiones — por ejemplo, un tablero de estado de la implementación del setup (fases 0–4, qué laptop tiene qué).

---

## 5. Matriz de decisión por tarea concreta de TU proyecto

| Tarea | Herramienta | Por qué |
|-------|-------------|---------|
| Implementar Fases 0–3 (instalar plugins, MCPs, Docker, vault) | **Claude Code** (+ scripts) | Todo ocurre en tu máquina; Cowork no puede ejecutar los scripts de bootstrap en tu host |
| Codear en React/Flutter/Python/C++ | **Claude Code** | Toolchain, hot reload, tests, hooks |
| Preguntas de arquitectura sobre codebase local ("¿quién llama a X?") | **Claude Code** | Graphify vive junto al repo |
| Codebase que ya está en GitHub, análisis puntual | **Cowork** viable | Clona al sandbox, analiza, reporta — sin ocupar tu máquina |
| Documentar decisión recién tomada (ADR en caliente) | **Claude Code** | Está en contexto en el momento |
| Curación masiva del vault (ADRs retroactivos, frontmatter, duplicados) | **Cowork** | Trabajo por lotes, desatendido, sobre .md de OneDrive |
| Guardar/consultar memoria Graphiti durante coding | **Claude Code** | MCP localhost directo |
| Investigación de mejoras al setup, comparativas, benchmarks | **Cowork** | Web research + workflows + sesión persistente |
| Reportes, análisis en MD/docx, presentaciones | **Cowork** | Skills de documentos, entrega directa |
| Digest semanal de releases (Graphiti, Graphify, Superpowers) | **Cowork** (scheduled task) | Corre en la nube sin laptop |
| Backup de FalkorDB cada 4h | **Ni uno ni otro** — cron/Task Scheduler local | Determinista, no necesita LLM; Claude Code solo lo configura |
| Verificación visual de UI React | **Ambos** | Code+Playwright (browser limpio) o Cowork+Chrome (tu sesión) |
| Bootstrap de laptop nueva | **Claude Code** | `setup-new-machine.ps1/sh` corre en el host |
| Monitorear/redirigir trabajo desde el teléfono | **Cowork** | Único con sesiones cross-device |

---

## 6. Implicaciones para el setup estándar compartido

### 6.1 Lo que ya es compartible sin cambios (la base común)

La decisión más afortunada de tu investigación es que **la capa de memoria durable es markdown en OneDrive**. Eso es agnóstico al producto:

- **Vault de Obsidian**: Claude Code lo lee vía filesystem/MCP; Cowork lo lee conectando la carpeta del vault. Mismo vault, mismas convenciones, mismos ADRs.
- **`memory-instructions.md` y las reglas de memoria** (search-before-save, group_id, qué guardar): el contenido es idéntico para ambos; solo cambia dónde se inyecta (CLAUDE.md en Code, instrucciones de proyecto en Cowork).
- **git dotfiles**: sigue siendo la fuente de verdad; Cowork además puede *leer* el repo para tener el contexto del setup (como esta sesión).
- **Skills**: el formato SKILL.md es el mismo ecosistema; los plugins (incluido Superpowers) se instalan en ambos, y hooks/subagents de plugins funcionan en ambos según los docs oficiales.

### 6.2 Las variaciones mínimas por producto

```
COMÚN (OneDrive + git)
├── Vault Obsidian (.md)              ← ambos leen/escriben
├── memory-instructions.md            ← mismo contenido, distinto punto de inyección
├── Convenciones, ADRs, templates     ← idénticos
├── Skills / plugins                  ← mismo ecosistema
│
├── VARIANTE CLAUDE CODE
│   ├── CLAUDE.md (<500 tokens) + @imports
│   ├── settings.json + hooks
│   ├── MCPs: graphiti (localhost), context7, filesystem→vault
│   └── CLAUDE_CONFIG_DIR por cuenta
│
└── VARIANTE COWORK
    ├── Instrucciones de proyecto (equivalente al CLAUDE.md, mismo texto base)
    ├── Carpetas conectadas: Atloos + ObsidianVault
    ├── Connectors del registry (GitHub, Drive) en vez de MCPs npx
    └── Scheduled tasks para lo periódico
```

Recomendación práctica: mantener en el repo un `context/CORE-INSTRUCTIONS.md` único (las <500 tokens de reglas + memoria) y que tanto el CLAUDE.md como las instrucciones de proyecto de Cowork sean wrappers de 5 líneas sobre ese archivo. Un solo lugar que editar.

### 6.3 El punto de fricción real: Graphiti

Es la única pieza de la arquitectura que no se comparte limpio:

| Opción | Cómo lo vería Cowork | Costo |
|--------|---------------------|-------|
| Status quo (MCP en localhost, Estrategia A) | Solo si registras graphiti-memory como MCP local en el desktop app (se proxea por el puente, requiere app abierto) | 0 extra — **empezar aquí** |
| Estrategia C (FalkorDB Cloud) + MCP server aún local | Igual que arriba — mover solo la DB al cloud no expone el MCP a Cowork | Costo mensual, sin ganancia para Cowork por sí sola |
| Graphiti MCP server hosteado remoto (además de FalkorDB Cloud) | Connector remoto: accesible desde Cowork en la nube, sin desktop app, incluso en scheduled tasks | Infra propia o servicio; la opción "full compartido" si Cowork se vuelve intensivo |

*(La primera opción está sustentada en los docs oficiales de conectores locales; el detalle de proxeo conviene validarlo empíricamente en la primera sesión de prueba — está marcado como paso de verificación en la sección 7.)*

Mientras tanto, hay un mitigante barato: como el vault ya duplica las decisiones importantes (ADRs), **Cowork tiene acceso a la memoria esencial vía vault aunque no vea Graphiti**. La memoria temporal fina (¿qué era verdad en marzo?) queda como capacidad exclusiva de las sesiones de Code hasta decidir si vale la pena exponer el MCP.

### 6.4 Hallazgos de los docs 00–07 releídos desde Cowork

| Hallazgo original | Estado en Cowork |
|-------------------|------------------|
| H3 — MCPs cuestan 10–20k tokens c/u | Mitigado de fábrica: Cowork carga schemas bajo demanda (tool search nativo). La disciplina de "pocos connectors" sigue aplicando |
| H4 — CLAUDE.md <500 tokens | Aplica igual a las instrucciones de proyecto de Cowork — mismo principio, otro nombre |
| H8 — Symlinks en OneDrive | Irrelevante para Cowork (no usa symlinks), sigue vigente para Code |
| H9 — No cambiar MCPs mid-sesión | Menos crítico en Cowork (deferred loading), sigue vigente en Code |
| H2 — FalkorDB fuera de OneDrive | Sin cambios — es un problema del host, no del producto |
| Anti-patrón "dump de memoria" | Aplica doble en Cowork: cada archivo stage-ado entra al contexto; conectar el vault entero y pedir "léelo todo" es el mismo error |

### 6.5 La división de trabajo recomendada (una línea)

> **Claude Code es las manos; Cowork es el gabinete.** Code toca el código y tu máquina; Cowork investiga, redacta, cura la memoria, vigila el ecosistema y trabaja mientras duermes. El vault en OneDrive es el cerebro compartido entre ambos.

---

## 7. Próximos pasos sugeridos (no ejecutados aún)

1. **Validar el puente Graphiti→Cowork**: cuando Docker + Graphiti estén corriendo (Fase 3), registrar el MCP local en el desktop app y probar desde una sesión Cowork. Es el único supuesto de este doc que requiere confirmación empírica.
2. **Conectar el vault de Obsidian como carpeta de Cowork** desde el día en que exista (Fase 0), para que ambas superficies compartan memoria desde el inicio.
3. **Extraer `CORE-INSTRUCTIONS.md`** único y hacer wrappers por producto (sección 6.2).
4. **Definir las primeras 2 scheduled tasks de Cowork**: digest semanal del ecosistema + auditoría quincenal del vault.
5. Añadir a `setup/` un `cowork-project-instructions.md` (gemelo de `memory-instructions.md` adaptado a Cowork).

---

## 8. Fuentes

| Fuente | Qué sustenta |
|--------|--------------|
| [Get started with Claude Cowork](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork) | Ejecución remota, scheduled tasks en la nube, plugins/MCP, proyectos, límites de memoria y cuota |
| [Use Claude Cowork on web, desktop, and mobile](https://support.claude.com/en/articles/15520349-use-claude-cowork-on-web-desktop-and-mobile) | Sesiones cross-device, qué agrega el desktop app, MCPs locales solo vía desktop app |
| [Use plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude) | Hooks y subagents de plugins funcionan en Cowork; skills cross-platform |
| [Let Claude use your computer in Cowork](https://support.claude.com/en/articles/14128542-let-claude-use-your-computer-in-cowork) | Computer use, permisos por app, requisitos del desktop |
| Observación directa del entorno Cowork (esta sesión) | Sandbox cloud con red, VM local sin red, staging/commit de archivos, tool search nativo, workflows, artifacts |
| Docs 00–07 de este repo | Toda la arquitectura base de Claude Code |

---

*Este documento extiende la serie de investigación 00–07. Válido para: Claude Code 2.x y Cowork (julio 2026). Revisar tras cambios mayores de producto — Cowork evoluciona rápido.*
