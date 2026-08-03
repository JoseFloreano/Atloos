# ClaudeSetup

Memoria persistente y skills para **Claude Code + Cowork**, sincronizadas entre
2-3 laptops. Repo de documentación y scripts: no contiene código de aplicación.

Tres piezas vivas: el **vault de Obsidian** (memoria durable, con git), las
**skills** (metodología reutilizable) y los **hooks anti-drift** (lo que
garantiza que la memoria se actualice). Encima de eso, un **puente de Telegram**
para trabajar desde el móvil.

> **Antes de tocar nada:** lee
> [`docs/arquitectura-memoria/07-HALLAZGOS-CRITICOS-REFERENCIA-RAPIDA.md`](./docs/arquitectura-memoria/07-HALLAZGOS-CRITICOS-REFERENCIA-RAPIDA.md).
> Son 10 datos que cambian decisiones de arquitectura y evitan errores caros.

**El mapa completo de la documentación está en
[`docs/00-INDICE-GENERAL.md`](./docs/00-INDICE-GENERAL.md)** — con el estado de
cada doc. Este README no lo duplica: se desfasaría.

```
docs/       el porqué de cada decisión (ver el índice general)
setup/      lo ejecutable: scripts, skills, hooks, puente Telegram
_archive/   derivados de mantenimiento (ver _archive/README.md)
```

---

## Prerrequisitos

| Herramienta | Instalación | Para qué |
|---|---|---|
| **Claude Code** | `npm install -g @anthropic-ai/claude-code` | El agente |
| **Python 3** | Windows: launcher `py`. Linux/macOS: `python3` | Hooks y puente Telegram |
| **Obsidian** | [obsidian.md](https://obsidian.md) | Vault de memoria |
| **uv** *(opcional)* | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | Instalar Graphify |
| **Docker** *(opcional)* | [docker.com](https://www.docker.com/products/docker-desktop) | Solo para Graphiti — **pospuesto**, ver abajo |

Comprobación rápida (`claude --version` debe responder; los hooks necesitan `py`
en Windows, no `python`: el `python` pelado apunta al stub de Microsoft Store):

```bash
claude --version
py --version          # Windows
```

---

## Quickstart

Tres escenarios. Elige uno; no son acumulativos.

> ⚠ **Sobre `setup-new-machine.ps1` / `.sh`.** Son de la época en que Graphiti
> era el centro del setup: **verifican Docker primero y hacen `exit 1` si falta**
> (`setup-new-machine.ps1:71`, `setup-new-machine.sh:58`). Como Graphiti está
> **pospuesto**, hoy no son el camino principal — montan un componente apagado.
> Úsalos solo si vas a levantar Graphiti; para todo lo demás, los pasos de abajo
> bastan y no necesitan Docker.

### A · Laptop nueva, con OneDrive (multi-laptop)

El caso normal: ya tienes el setup en otra máquina y `DevSetup/` sincronizado.
Son dos scripts, sin Docker de por medio.

```powershell
# Windows (PowerShell)
.\setup\sync-skills.ps1        # skills → ~/.claude/skills (+ zip para Cowork)
.\setup\sync-hooks.ps1         # hooks  → ~/.claude/hooks + cablea settings.json
```

```bash
# macOS / Linux
./setup/sync-skills.sh
```

Después, abre Obsidian → *Open folder as vault* → `DevSetup/ObsidianVault/`.
Con eso tienes memoria y skills vivas en la máquina nueva.

### B · Single-laptop, sin OneDrive

Igual que A: los scripts de sync resuelven la raíz por su cuenta y caen a
`~/DevSetup` cuando no encuentran OneDrive. La durabilidad la da el remoto git
del vault, no la carpeta sincronizada.

Si además vas a levantar Graphiti, el bootstrap tiene modo local explícito:

```powershell
.\setup\setup-new-machine.ps1 -Local     # requiere Docker
```

```bash
LOCAL=1 bash setup/setup-new-machine.sh  # requiere Docker
```

### C · Puente Telegram — trabajar desde el móvil

Lo más útil del repo hoy y lo que más cambia el día a día. Cuatro fases, y la
primera se monta en cinco minutos:

| Fase | Qué da |
|---|---|
| **T0 · Avisos** | "Mándamelo por telegram": al acabar una tarea larga, el resultado te llega al móvil. Solo envía — sin bot escuchando, sin daemon, sin URL pública ni túnel |
| **T1 · Chat** | Le preguntas al repo desde el móvil, en **solo lectura** |
| **T2 · Escritura** | Desarrolla en un **worktree aislado**, con `/commit`, `/test`, `/pull` y `/merge` con botón |
| **T3 · Memoria** | El bot lee el `_PROJECT.md` del vault y escribe su nota de sesión al cerrar |

**El procedimiento completo está en
[`setup/telegram-bridge/README.md`](./setup/telegram-bridge/README.md)**: crear
el bot con @BotFather, obtener el `chat_id`, el `.env`, arrancar el daemon y la
lista de comandos. No lo repito aquí — un procedimiento en dos sitios acaba
divergiendo.

Lo único que conviene saber antes de empezar:

- Las credenciales van en `setup/telegram-bridge/.env`, **nunca en el repo ni en
  OneDrive**. Compruébalo antes del primer commit:

  ```bash
  git check-ignore -v setup/telegram-bridge/.env
  # imprime: .gitignore:16  setup/telegram-bridge/.env
  ```

- El envío es stdlib pura, sin dependencias:

  ```bash
  py setup/telegram-bridge/notify_telegram.py "hola desde Claude Code"
  py setup/telegram-bridge/notify_telegram.py --file informe.md "te mando esto"
  ```

- El daemon (T1+) sí necesita `python-telegram-bot`; el README del puente lo detalla.

---

## Skills y hooks

Las skills se editan en `setup/skills/{shared,claude-code,cowork}` y se
distribuyen con un script; los hooks son otro mecanismo y tienen el suyo.

```powershell
.\setup\sync-skills.ps1        # skills → ~/.claude/skills + zip para Cowork
.\setup\sync-skills.ps1 -NoCoworkBuild
.\setup\sync-hooks.ps1         # hooks → ~/.claude/hooks + cablea settings.json
.\setup\sync-hooks.ps1 -NoWire # solo copia, sin cablear
```

```bash
./setup/sync-skills.sh                  # OneDrive en ~/OneDrive
NO_COWORK_BUILD=1 ./setup/sync-skills.sh
```

`sync-skills` **copia, nunca enlaza** (OneDrive en Windows no soporta symlinks) y
solo gestiona lo que él mismo instaló, así que es seguro repetirlo. Cowork es el
único paso manual: hay que subir el zip a mano en Customize → Plugins.

**Los cuatro hooks anti-drift** — qué garantiza cada uno, cómo probarlos y qué
se rompe si los tocas: [`setup/hooks/README.md`](./setup/hooks/README.md).

| Hook | Evento | En una línea |
|---|---|---|
| `mark-code-dirty.py` | PostToolUse | Marca que la sesión editó código **de este proyecto** |
| `check-vault-updated.py` | Stop | Si hubo código y el vault no se actualizó, bloquea el cierre |
| `memory-flush.py` | PreCompact | Pausa la compactación una vez si el vault sigue desfasado |
| `validate-graphiti-group-id.py` | PreToolUse | Ningún episodio de Graphiti sin `group_id` válido |

Hay además un hook de **git** (`post-commit`) que regenera el `codebase-map.md`
con Graphify en los commits que tocan código. Se instala por repo.

---

## Qué hay en `setup/`

La tabla de componentes —qué es cada archivo y para qué sirve— vive en
[`setup/README.md`](./setup/README.md), junto con el **registro de secretos**
(cada credencial con su ruta, su consumidor y cómo rotarla) y el detalle del
modo single-laptop.

Un apunte que no está ahí: `setup/scripts/` contiene `adr-index.py`, que
regenera el índice de ADRs del vault y sabe verificarse a sí mismo:

```bash
py setup/scripts/adr-index.py <ruta-a-la-carpeta-ADRs> --check   # rc=0 si está al día
```

---

## Graphify — grafo del codebase

```bash
uv tool install graphifyy   # sí, doble "y": es el nombre real en PyPI
graphify install            # registra la skill en Claude Code
```

`graphify` (una sola "y") es el **comando**; `graphifyy` es el **paquete**.
Verificado contra pypi.org el 2026-08-01: `graphify` no existe como paquete. No
lo "corrijas".

---

## Graphiti + FalkorDB — componente opcional, **pospuesto**

**No es parte del camino de instalación.** Está apagado por decisión propia
(`ADR-20260726-graphiti-pospuesto`, en el vault): el vault de Obsidian es la
única memoria durable hasta que se cumpla alguno de los criterios de activación.

Los errores de integración están documentados en
[`docs/arquitectura-memoria/10-RFD-GRAPHITI-INTEGRACION-ERRORES.md`](./docs/arquitectura-memoria/10-RFD-GRAPHITI-INTEGRACION-ERRORES.md)
— ojo, con correcciones: cuatro de los ocho "errores" resultaron falsos.

Cuando se active, la guía es
[`docs/arquitectura-memoria/11-GRAPHITI-SETUP-GUIA-RAPIDA.md`](./docs/arquitectura-memoria/11-GRAPHITI-SETUP-GUIA-RAPIDA.md).
Los archivos (`docker-compose.yml`, `config.yaml`, `.env.example`,
`graphiti-project-template.json`) ya están en `setup/`, en su raíz.

---

## Verificar que funciona

```bash
claude mcp list                  # los MCP registrados y su salud
py setup/scripts/adr-index.py <ruta-ADRs> --check
```

Del puente Telegram: manda un mensaje de prueba con `notify_telegram.py` (arriba)
y comprueba que llega al móvil. Los hooks se prueban con la suite de
`setup/hooks/tests/`, documentada en el README de hooks.

---

## Protocolo al cambiar de laptop

1. En la laptop que dejas: cierra la sesión con la skill `session-close` — deja
   el vault con estado, pendientes y próximo paso.
2. Espera a que OneDrive diga "Actualizado", y que el vault haya hecho push.
3. En la nueva: escenario **A** de arriba, y `sync-skills` + `sync-hooks`.

El riesgo real no es la máquina: es abrir la laptop nueva con un vault a medio
escribir. Por eso el cierre va antes que el viaje.
