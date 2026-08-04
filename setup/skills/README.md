# Skills Modulares — Carpeta única en OneDrive para Claude Code y Cowork

Sistema de skills compartido entre productos: **una carpeta en OneDrive es la fuente
de verdad**, y cada producto la consume por su mecanismo nativo. Añadir una skill
nueva = crear una carpeta + correr un script (o nada, si ya tienes el watcher).

## La estructura (fuente de verdad)

```
OneDrive/DevSetup/claude-skills/
├── shared/            ← skills que sirven a AMBOS productos
│   └── adr-writer/
│       └── SKILL.md
├── claude-code/       ← solo Claude Code (asumen terminal/toolchain local)
├── cowork/            ← solo Cowork (asumen sandbox cloud, documentos, web)
├── _template/         ← plantilla para crear skills nuevas
│   └── SKILL.md
└── _build/            ← generado por sync-skills (NO editar a mano)
    ├── dev-skills/    ← plugin para Cowork
    └── dev-skills.zip
```

Esta carpeta se crea automáticamente la primera vez que corres `sync-skills.ps1`
(seed desde `setup/skills/` del repo). OneDrive la replica a todas tus laptops.

> **Sin OneDrive (single-laptop):** los scripts caen automáticamente a
> `%USERPROFILE%\DevSetup\claude-skills` (`~/DevSetup/claude-skills`) — todo lo
> demás de este README aplica igual. Ver "Modo single-laptop" en `setup/README.md`.

## Cómo llega cada skill a cada producto

| Producto | Mecanismo | Qué recibe |
|----------|-----------|------------|
| Claude Code | `sync-skills.ps1/.sh` **copia** (nunca symlink — hallazgo H8) a `~/.claude/skills/` y a cada `~/.claude-*/skills/` (multi-cuenta) | `shared/` + `claude-code/` |
| Cowork | El mismo script empaqueta un plugin `dev-skills` (carpeta + .zip en `_build/`); lo instalas una vez en el desktop app: **Customize → Plugins → subir plugin** | `shared/` + `cowork/` |

El uso es **automático en ambos**: los dos productos descubren skills por
*progressive disclosure* — solo el `name` + `description` entran al contexto, y el
agente carga el cuerpo cuando la tarea coincide con la descripción. No hay que
invocarlas manualmente ni configurar nada más.

> **La descripción ES el trigger.** Una skill con mala descripción no se usa nunca.
> Ver reglas en `_template/SKILL.md`.

## El cuarto consumidor: el perfil `bot` (puente Telegram)

Las sesiones del daemon de Telegram **no son un cuarto directorio**, sino un
**subconjunto** de `shared/` + `claude-code/`. Cada `description` entra al
contexto en *cada* invocación, así que cargar las 29 cuesta tokens en tareas
donde muchas no aplican jamás (decisión: `ADR-20260801-bot-memoria-y-perfil`, en el vault).

**Criterio de inclusión.** Entra si sirve para *leer o escribir código desde un
worktree aislado*. Queda fuera si:

- **toca el vault** — en el bot la memoria la escribe el daemon, no el agente;
- **necesita herramientas fuera de la lista blanca** de Bash del bot;
- **no tiene sentido en ese contexto** (notificar por Telegram desde Telegram,
  dar de alta proyectos, cerrar sesiones, mantener el propio setup).

### Registro

| Skill | Categoría | Bot | Por qué |
|---|---|:---:|---|
| adr-writer | shared | ✗ | Escribe en el vault (lo hace el daemon) |
| agentic-system-design | shared | ✓ | Diseño de sistemas al implementar |
| api-design | shared | ✓ | Desarrollo |
| authn-authz-review | shared | ✓ | Revisión, solo lectura |
| context-engineering | shared | ✓ | Diseño de prompts/agentes |
| data-quality-gates | shared | ✓ | Desarrollo con datos |
| deploy-planner | shared | ✗ | Entrevista larga; mal encaje en móvil |
| design-doc-harvest | shared | ✗ | Cosecha al vault |
| memory-keeper | shared | ✗ | Escribe en el vault |
| migration-auditor | shared | ✓ | Revisión de migraciones |
| model-benchmark | shared | ✗ | Necesita web; `WebFetch` denegado en el bot |
| pipeline-designer | shared | ✓ | Desarrollo |
| python-api-design | shared | ✓ | Desarrollo |
| python-conventions | shared | ✓ | Desarrollo |
| schema-designer | shared | ✓ | Desarrollo |
| session-close | shared | ✗ | Ritual de vault |
| skill-forge | shared | ✗ | Mantiene el setup; requiere sync manual |
| sql-conventions | shared | ✓ | Desarrollo |
| web-security-review | shared | ✓ | Revisión, solo lectura |
| api-evolution | claude-code | ✓ | Desarrollo |
| dependency-audit | claude-code | ✗ | `npm audit`/`pip-audit` no están en la lista blanca |
| flaky-test-hunter | claude-code | ✓ | Los comandos de test sí están permitidos |
| gdb-sanitizers-runbook | claude-code | ✗ | Toolchain C++ fuera de la lista blanca |
| git-bisect-assist | claude-code | ✗ | Requiere git ops que el agente no puede ejecutar |
| notify-telegram | claude-code | ✗ | El bot **es** Telegram |
| project-onboard | claude-code | ✗ | Crea carpetas del vault |
| project-resume | claude-code | ✗ | Lee el vault; lo sustituye la inyección del daemon (C1b) |
| secrets-scan | claude-code | ✓ | Escaneo de solo lectura |
| token-audit | claude-code | ✗ | Analiza el setup local, no el proyecto |

**15 skills** entran al perfil bot (el universo del registro son `shared/` +
`claude-code/`; las 2 de `cowork/` quedan fuera A PROPÓSITO — el bot corre sobre
Claude Code — y por eso no tienen fila). El conteo vivo sale de esta tabla, no
de esta frase.

**Mantenimiento**: toda skill nueva añade su fila **en el mismo PR** (misma regla
que el registro de secretos del `setup/README.md`). La lista se revisa en el
`vault-drift-audit` quincenal, junto con la poda de skills sin uso. Si una fila
falta, el perfil bot la excluye por defecto — mejor perder una skill que colar
ruido en cada invocación.

## Añadir una skill nueva (el flujo completo)

```
1. Copia _template/ →  shared/mi-skill/   (o claude-code/ o cowork/, según aplique)
2. Edita SKILL.md    →  name + description con triggers + cuerpo corto
3. Corre sync:
     Windows:      .\sync-skills.ps1
     macOS/Linux:  ./sync-skills.sh
4. Claude Code: la skill ya está (nueva sesión la ve).
   Cowork: re-sube _build/dev-skills.zip solo si la skill es shared/ o cowork/.
```

En las demás laptops: OneDrive sincroniza la carpeta sola; solo corre el paso 3.

> ⚠️ **El sync lee de la FUENTE, no del repo.** Un `git pull` actualiza
> `setup/skills/` del repo, pero `sync-skills` copia desde
> `claude-skills/`. Si editas una skill en el repo, **espeja primero**
> (`robocopy setup\skills\<cat> <fuente>\<cat> /MIR`, o `cp -r`) o el cambio no
> llega a ninguna parte. El seed automático desde el repo solo ocurre la primera
> vez, cuando la carpeta fuente aún no existe.

### Scripts auxiliares (`~/.claude/scripts/`)

`sync-skills` instala además los `.py` de `setup/scripts/` en
`~/.claude/scripts/` de cada config dir. Existe porque varias skills
(`adr-writer`, `project-resume`, `vault-drift-audit`) invocan `adr-index.py`
por ruta absoluta —corren desde el cwd de cualquier proyecto— y esa ruta
necesita ser la misma en toda máquina. Antes apuntaba al repo **dentro de
OneDrive**: inerte en modo single-laptop y atada al árbol de carpetas de una
laptop concreta. Es el mismo patrón que `sync-hooks` con `~/.claude/hooks/`.

**En Cowork no existe** (no es una máquina tuya): las skills que dependen del
script deben decir qué hacer sin él, no asumir que corrió.

## Reglas del sistema

1. **Kebab-case** en nombres de carpeta: `adr-writer`, no `ADR Writer`.
2. **Un `SKILL.md` por carpeta**, frontmatter YAML con `name` y `description` obligatorios.
3. **Cuerpo corto** (< 500 palabras). Material extenso va en archivos junto al
   SKILL.md (`references/`, `scripts/`) — el agente los lee solo si los necesita
   (progressive disclosure, mismo principio que CLAUDE.md < 500 tokens, hallazgo H4).
4. **Conflictos de nombre**: si una skill existe en `shared/` y en la carpeta de un
   producto, **gana la del producto** (es más específica). Evítalo de todas formas.
5. **Sin secretos**: las skills viajan por OneDrive y se empaquetan en plugins.
   API keys y rutas de máquina van en `.env` / settings, nunca en una skill.
6. **`_build/` es desechable**: lo regenera el script en cada corrida.

## Decidir en qué carpeta va una skill

| La skill... | Carpeta |
|-------------|---------|
| Solo describe metodología, formato o convenciones | `shared/` |
| Ejecuta comandos de tu toolchain local (flutter, cmake, docker, git hooks) | `claude-code/` |
| Depende de MCP en localhost sin fallback | `claude-code/` |
| Asume web research, documentos (docx/pptx/xlsx), sandbox cloud | `cowork/` |
| Usa el vault de Obsidian o Graphiti **con fallback documentado** | `shared/` (declara el fallback en la skill) |

## Verificar que funciona

- **Claude Code**: `ls ~/.claude/skills/` debe listar tus skills; en sesión, pide
  algo que coincida con la descripción y observa que la invoque.
- **Cowork**: en Customize → Plugins debe aparecer `dev-skills` con sus skills;
  igual — pide algo que coincida con un trigger.
