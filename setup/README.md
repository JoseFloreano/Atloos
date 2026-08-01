# Setup Multi-Laptop con OneDrive — Claude Code + Cowork

Setup compartido entre Claude Code y Cowork, diseñado para 2-3 laptops
sincronizadas via OneDrive. Ver análisis de división de trabajo entre
productos en `docs/cowork-y-multiagente/08-COWORK-VS-CLAUDE-CODE.md`.

## Componentes de este directorio

| Componente | Archivos | Aplica a |
|-----------|----------|----------|
| **Skills modulares** (carpeta única en OneDrive, dividida en shared / claude-code / cowork) | `skills/` (seed + template + README), `sync-skills.ps1/.sh` | Ambos |
| **Memoria por proyecto** (aislamiento estricto anti-alucinación) | `memory-instructions.md` (snippet CLAUDE.md ~230 tokens), `cowork-project-instructions.md` (Cowork), skill `memory-keeper`, `graphiti-project-template.json` | Ambos |
| **Enforcement del aislamiento** (garantía determinista, no solo instrucciones) | `hooks/validate-graphiti-group-id.py` + `hooks/README.md` | Claude Code |
| **Graphiti + FalkorDB** (memoria temporal, resto de este README) | `docker-compose.yml`, `config.yaml`, `.env.example`, `backup-graph.ps1/.sh`, `restore-graph.ps1/.sh` | Claude Code (Cowork solo vía puente del desktop app) |
| **Bootstrap laptop nueva** | `setup-new-machine.ps1/.sh` (incluye sync de skills y tareas programadas de backup) | Ambos |
| **Tareas programadas** (patrón "heartbeat barato") | `templates/scheduled-task-prompt.md` | Ambos |

### Skills: el flujo corto

```
OneDrive/DevSetup/claude-skills/{shared,claude-code,cowork}   ← fuente de verdad
  → sync-skills.ps1/.sh copia a ~/.claude*/skills/            ← Claude Code
  → y empaqueta _build/dev-skills.zip                          ← subir 1 vez a Cowork
Skill nueva: carpeta + SKILL.md + re-correr sync. Detalles: skills/README.md
```

### Tareas programadas: siempre con gate sin LLM

Todo scheduled task periódico (Cowork o cron con `claude -p`) se escribe con
`templates/scheduled-task-prompt.md`: **gate barato antes del modelo** (si no
hay nada que hacer, Claude no se invoca), sesión fresca por corrida y
convención "nada que reportar → responde solo `OK`". Sin eso, una tarea horaria
paga contexto completo para decir "no hay nada". Origen: R1 del doc
`ecosistema/16-AHORRO-TOKENS-ROBADO-DE-HERMES-OPENCLAW.md`.

### Modo single-laptop (sin OneDrive)

Para quien trabaja en **una sola laptop** o no usa OneDrive: todo el setup
funciona igual con la raíz `DevSetup/` en el home en vez de OneDrive.

```
Activación:  setup-new-machine.ps1 -Local     |  LOCAL=1 bash setup-new-machine.sh
             (o automático: si no existe la carpeta de OneDrive, los scripts
              caen solos a modo local y lo avisan)

Qué cambia:                      multi-laptop            single-laptop
  Raíz DevSetup                  OneDrive\DevSetup\      %USERPROFILE%\DevSetup\ (~/DevSetup)
  Skills (claude-skills/)        viajan por OneDrive     misma carpeta, local
  Backups del grafo              a OneDrive              a ~\DevSetup\graphiti-data\backups
  Vault de Obsidian              OneDrive + git remote   local + git remote (GitHub) ← OBLIGATORIO aquí

Qué NO cambia: datos vivos de FalkorDB (siempre locales), .env local, hooks,
skills, memoria por proyecto, plugin de Cowork, scripts de backup/restore.
```

⚠️ **La advertencia importante del modo local:** los backups del grafo quedan
en el mismo disco que los datos — protegen contra corrupción, no contra falla
del disco. Compensa con: (1) remote git del vault en GitHub (aquí deja de ser
opcional), y (2) copia periódica de `DevSetup/graphiti-data/backups/` a disco
externo o nube. Migrar a multi-laptop después es trivial: mueve `~/DevSetup/`
dentro de OneDrive y re-corre el setup.

### Regla de flujo git multi-laptop (lección de la primera instalación)

Los archivos que Claude escribe en disco NO están en git hasta commitear. Antes
de trabajar el repo desde otra laptop: `git add + commit + push` en la actual, y
`git pull` en la otra ANTES de editar — si no, un pull posterior pisa versiones
nuevas con base vieja (ya pasó: revirtió los bootstrap a pre-auditoría). Si un
pull toca `setup/`, verifica rápido: `grep GraphitiLocal setup-new-machine.ps1`.
Además: todo `.ps1` de este repo lleva **UTF-8 con BOM** (powershell.exe lee sin
BOM como ANSI y los caracteres `─`/`—` rompen el parseo); el `plugin.json` del
plugin de Cowork va **sin BOM** y el zip con rutas `/` y el plugin root en la raíz.

### Memoria por proyecto: la regla de oro

Todo acceso a memoria (Graphiti y vault) va SIEMPRE filtrado al proyecto activo
+ `dev-global`. Nunca consultar ni escribir memoria de otro proyecto — es la
defensa principal contra alucinaciones cross-proyecto. El snippet
`memory-instructions.md` (Code) y `cowork-project-instructions.md` (Cowork)
implementan la misma regla en ambos productos; reemplaza `<project-name>` al
copiarlos.

---

# Graphiti + FalkorDB — Memoria temporal

> **Estado (julio 2026): POSPUESTO por decisión propia.** El setup arranca sin
> Graphiti — el vault de Obsidian (vía skills `adr-writer`/`memory-keeper`)
> cubre la memoria esencial con la suscripción de Claude, sin API keys ni
> Docker. Criterio para activarlo: si tras 3–4 semanas extrañas el
> razonamiento temporal ("¿qué usábamos en marzo?"), se monta en una tarde.
>
> **Sin costo de API al activarlo:** la extracción de entidades puede correr
> con el free tier de **Gemini** (ruta 2 del `.env.example` — recomendada:
> ~1,500 req/día y ~1M tokens/min sobran para ~10 episodios/sesión) o de
> **Groq** (ruta 3 — rapidísimo, pero su límite real es ~6k tokens/MINUTO:
> usa el modelo 70b y `SEMAPHORE_LIMIT=2`). La suscripción de Claude NO puede
> usarse para esto: Graphiti llama al LLM por API desde su propio server.

## Arquitectura

```
Claude Code (laptop 1/2/3)
      │ HTTP MCP
      ▼
Graphiti MCP Server (:8000)   ◄── extrae entidades con LLM en escritura
      │
      ▼
FalkorDB (:6379)               ◄── grafo temporal persistente
      │
      ▼
/var/lib/falkordb/data/        ◄── volumen Docker
      │
      ├── dump.rdb             ← snapshot periódico (para backups a OneDrive)
      └── appendonly.aof       ← WAL para durabilidad máxima
```

## ⚠️ El problema real de OneDrive + FalkorDB

FalkorDB (basado en Redis) mantiene **locks activos** sobre `dump.rdb`
y `appendonly.aof` mientras está corriendo. OneDrive en Windows intenta
sincronizar archivos abiertos y puede generar:

- Corrupción del RDB si OneDrive interrumpe una escritura mid-snapshot
- Conflictos de sync si dos laptops tienen el container corriendo simultáneamente
- Locks que bloquean la sync de OneDrive silenciosamente

### Estrategia A — Recomendada (y la que implementan los scripts tras la auditoría doc 09)

```
Datos vivos:  %LOCALAPPDATA%\graphiti\data   (Win)   ← disco LOCAL, nunca OneDrive
              ~/.local/share/graphiti/data   (Unix)
.env local:   junto a los datos (API keys fuera de OneDrive — fix A4)
Backups:      backup-graph.ps1/.sh cada 4h → OneDrive/DevSetup/graphiti-data/backups/

Al cambiar de laptop:
  docker compose stop                  # fuerza BGSAVE final
  backup-graph.ps1 / .sh               # snapshot → OneDrive (avisa si hay fork)
  En la otra laptop: restore-graph.ps1 / .sh
```

⚠️ **NUNCA restaures copiando `dump.rdb` a mano** (fix A3): con AOF activo el
server carga del AOF e ignora el .rdb — "restaura" sin error y sin datos.
`restore-graph` hace el procedimiento correcto (recovery sin AOF → verifica
DBSIZE → regenera AOF) y falla ruidosamente si los datos no cargaron.

**Pros**: Sin riesgo de corrupción, rendimiento máximo, restore verificado.
**Contras**: El grafo no se sincroniza en tiempo real entre laptops.

### Estrategia B — Datos en OneDrive (solo si un laptop a la vez)

```
FALKORDB_DATA_PATH=/ruta/onedrive/graphiti-data/falkordb
```

Requiere protocolo estricto:
- Solo UN container activo por vez
- Antes de cambiar: `docker compose stop graphiti-falkordb`
- Esperar a que OneDrive sincronice (verificar ícono sin conflictos)
- En nueva laptop: `docker compose up -d`

**Pros**: Sync automático del grafo completo.
**Contras**: Riesgo de corrupción si se olvida el protocolo.

### Estrategia C — FalkorDB Cloud (la más limpia para multi-laptop)

```yaml
# En .env:
# FALKORDB_URI=falkor://tu-instancia.falkordb.cloud:6379
# No necesitas Docker para FalkorDB — solo para el MCP server
```

FalkorDB Cloud es la opción recomendada por su equipo para acceso
multi-dispositivo. El MCP server sigue corriendo localmente en Docker,
pero se conecta a la instancia cloud en vez de localhost.

**Pros**: Grafo siempre disponible desde cualquier laptop, sin sync manual.
**Contras**: Requiere cuenta, tiene costo en volumen alto.

## Estructura de archivos (post-auditoría: local vs OneDrive)

```
LOCAL (por máquina — nunca se sincroniza):
%LOCALAPPDATA%\graphiti\  |  ~/.local/share/graphiti/
├── docker-compose.yml    # copiado desde el repo/dotfiles
├── .env                  # API keys + pins de versión (fix A4: FUERA de OneDrive)
├── data/                 # datos vivos de FalkorDB (fix A1: FUERA de OneDrive)
├── config/config.yaml
└── scripts/              # backup-graph + restore-graph

OneDrive (solo artefactos terminados y portables):
OneDrive/DevSetup/
├── claude-dotfiles/               # repo git (configs de Claude Code)
├── claude-skills/                 # skills shared/claude-code/cowork (+ _build/)
└── graphiti-data/backups/         # snapshots con timestamp + manifiestos
    ├── graphiti_20260712_120000.rdb
    └── graphiti_20260712_120000.manifest.json
```

> **Vault de Obsidian (pendiente al crearlo — auditoría R6):** decidir UN
> mecanismo primario de sync. Recomendado: vault en OneDrive + Obsidian Git
> con remote en GitHub y el directorio `.git` FUERA de la carpeta OneDrive
> (evita miles de archivos pequeños del .git en la sync).

## Aislamiento multi-proyecto con group_id

Graphiti usa `group_id` para aislar la memoria entre proyectos en la
misma instancia de FalkorDB. Desde PR #1209, FalkorDB usa una única
base de datos `GRAPHITI` con filtrado por `group_id`:

```
FalkorDB (una sola BD: "GRAPHITI")
├── group_id: "react-dashboard"    → memoria del proyecto React
├── group_id: "flutter-app"        → memoria del proyecto Flutter
├── group_id: "python-api"         → memoria del proyecto Python
├── group_id: "dev-global"         → preferencias globales del dev
└── group_id: "dev-conventions"    → convenciones compartidas
```

En CLAUDE.md de cada proyecto añadir:
```markdown
## Memory
- Always use group_id: "nombre-proyecto" for project-specific memory
- Use group_id: "dev-global" for personal preferences and conventions
- Search before saving: call search_facts first
```

## Configuración de Claude Code

### MCP (scope user — aplica a todos los proyectos)
```bash
claude mcp add --transport http graphiti-memory http://localhost:8000/mcp/ -s user
```

### Verificar
```bash
claude mcp list
# graphiti-memory: http://localhost:8000/mcp/ (http)
```

### .graphiti.json por proyecto
Copia `config/graphiti-project-template.json` a la raíz de cada
proyecto como `.graphiti.json` y ajusta `project_id` y `group_id`.

El archivo es detectado vía `GRAPHITI_PROJECT_DIR` env var (no por CWD).
En Claude Code, configura esto en el hook SessionStart o en .env del proyecto.

## Caveats importantes

1. **Structured output con Anthropic**: Graphiti usa JSON schema para
   extraer entidades. Anthropic tiene soporte experimental — puede fallar
   con haiku o en prompts complejos. Usar OpenAI (gpt-4.1-mini) o Gemini
   para el LLM de extracción es más estable.

2. **add_episode es asíncrono**: El episodio se encola y procesa en ~25s.
   Los hechos no aparecen en search_facts inmediatamente tras add_episode.

3. **Costo de escritura**: Cada add_episode llama al LLM para extraer
   entidades (~1-3 llamadas internas). Con SEMAPHORE_LIMIT=3 y uso intenso
   puedes consumir bastante de tu rate limit. Monitoriza en el dashboard.

4. **No confundir con Graphify**: Graphiti = memoria de sesiones (qué se
   decidió, qué se aprendió). Graphify = estructura del codebase (qué
   función llama a qué). Son complementarios, no reemplazos.

5. **Recuperación de .rdb**: SOLO con `restore-graph.ps1` / `restore-graph.sh`.
   El viejo método (`docker cp` + restart) NO funciona con AOF activo — el
   server ignora el dump.rdb y "restaura" nada (auditoría A3). Haz un
   simulacro de restore al terminar el setup y luego mensualmente.

## Comandos útiles

```bash
# Levantar / bajar (el .env vive LOCAL — fix A4)
GL=~/.local/share/graphiti   # Windows: $env:LOCALAPPDATA\graphiti
docker compose --env-file $GL/.env -f $GL/docker-compose.yml up -d
docker compose --env-file $GL/.env -f $GL/docker-compose.yml stop

# Ver logs
docker logs graphiti-mcp-server -f
docker logs graphiti-falkordb -f

# Backup manual (siempre antes de cambiar de laptop)
$GL/scripts/backup-graph.sh ~/OneDrive

# Restore (NUNCA copies dump.rdb a mano — ver caveat 5)
$GL/scripts/restore-graph.sh

# Verificar grafo en FalkorDB Browser
open http://localhost:3000

# Ver tamaño del grafo
docker exec graphiti-falkordb redis-cli DBSIZE
docker exec graphiti-falkordb redis-cli INFO memory | grep used_memory_human

# Limpiar grafo de un proyecto (irreversible)
# docker exec graphiti-falkordb redis-cli DEL "graphiti:group_id:nombre-proyecto"

# Verificar MCP desde Claude Code
claude mcp list
```
