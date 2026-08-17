# Atloos

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
| **Python ≥ 3.10** | Windows: launcher `py`. Linux/macOS: `python3` | Hooks, arneses y puente Telegram |
| **Obsidian** | [obsidian.md](https://obsidian.md) | Vault de memoria |
| **uv** *(opcional)* | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | Instalar Graphify |
| **Docker** *(opcional)* | [docker.com](https://www.docker.com/products/docker-desktop) | Solo para Graphiti — **pospuesto**, ver abajo |

### El intérprete de Python: una regla, no dos verdades

**No hay un literal que sirva en las dos plataformas**, y la salida obvia
también está rota. Medido el 2026-08-16 en las dos máquinas de este setup:

| | `py` | `python3` | `python` |
|---|---|---|---|
| **Windows** | Python 3.12.10 **real** | existe y **miente**: alias de la Store, «Python was not found» | igual, miente |
| **SER8** (Ubuntu 24.04) | **no existe** | Python 3.12.3 real | Python 3.12.3 real |

Lo peligroso es la casilla del medio: en Windows `command -v python3` dice que
sí. **«El comando existe» no es evidencia de que ejecute.**

Por eso la regla es **resolver, no elegir un literal**:

| Dónde | Qué se escribe |
|---|---|
| Comandos de este repo | `setup/scripts/py <script>` |
| Comandos desde cualquier otro proyecto (skills) | `"$HOME/.claude/scripts/py" <script>` |
| Dentro de un `.py` que ya corre | `sys.executable` |
| Un hook, que no puede pagar un subproceso | `"py" if os.name == "nt" else "python3"` |
| `GATE_TEST_CMD` | se declara con un lanzador cualquiera; `gate-test.py` lo cambia por el intérprete que ya está corriendo |

`setup/scripts/py` prueba cada candidato **ejecutándolo** antes de elegirlo, que
es lo único que distingue al lanzador real del stub. `sync-skills` lo instala en
`~/.claude/scripts/` de cada máquina. Que ninguna skill vuelva a mandar un
comando de una sola plataforma lo vigila
`setup/scripts/tests/test-comandos-portables.py`.

Comprobación rápida (`claude --version` debe responder; los hooks necesitan `py`
en Windows, no `python`: el `python` pelado apunta al stub de Microsoft Store):

```bash
claude --version
py --version          # Windows
```

### El suelo de Python es **3.10**, y es un contrato, no una sugerencia

Todo `.py` del repo tiene que **compilar** con 3.10. Lo vigila
`setup/scripts/tests/test-suelo-python.py`, que compila los 40 ficheros con un
intérprete **real** del suelo cuando la máquina lo tiene.

**Por qué 3.10 y no 3.12.** El suelo lo fija la máquina más vieja que corre esto
hoy, y hoy es el puente (Ubuntu 22.04, Python **3.10.12**) — que además es donde
se corren las auditorías. Subirlo a 3.12 no arreglaría nada: convertiría en «no
soportada» la máquina desde la que se descubrió el problema. Y no cuesta nada:
el repo es stdlib pura y los 40 ficheros ya compilan en 3.10.

> **Por qué existe el contrato.** Un arnés del sprint 9 usaba un backslash
> dentro de la expresión de una f-string — legal solo desde **3.12** (PEP 701).
> En Windows compilaba; en 3.10 el fichero **ni se importaba** y la suite daba
> **18/19 sin decir por qué**. Que la SER8 se salvara (Ubuntu 24.04 trae 3.12)
> era accidente, no diseño.

⚠ El check **compila**; no busca el texto del backslash. Un `grep` cazaría esa
forma y ninguna otra. Y `ast.parse(..., feature_version=(3,10))` **tampoco
sirve** —medido: daba verde sobre el fichero roto—, porque no cambia el
tokenizador y toda la familia PEP 701 se le escapa.

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
  setup/scripts/py setup/telegram-bridge/notify_telegram.py "hola desde Claude Code"
  setup/scripts/py setup/telegram-bridge/notify_telegram.py --file informe.md "te mando esto"
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

**El borrado es siempre opt-in.** Sin `-Prune` el script **no destruye nada**:
si detecta skills huérfanas las grita con el comando de poda y **no reescribe el
manifest**, para que la corrida siguiente siga recordándolas. Nació de un fallo
de campo en el que una enumeración parcial borró 2 skills imprimiendo `[OK]`,
así que el guard compara **conjuntos de nombres**, no conteos: +1 nueva y −1
subenumerada dan el mismo número.

Además instala en **`~/.claude/scripts/`** —misma ruta en toda máquina,
independiente de dónde esté clonado el repo— los scripts que las skills invocan:

```bash
ls ~/.claude/scripts/          # adr-index.py  notify_telegram.py  gate-test.py  run-tests.py
```

Esa ruta estable no es cosmética: el 2026-08-07 `notify-telegram` falló desde
otro proyecto por mandar buscar el script "en el repo Atloos", y no hay
relación de rutas entre dos árboles distintos.

**Los cinco hooks de Claude Code** — qué garantiza cada uno, cómo probarlos y qué
se rompe si los tocas: [`setup/hooks/README.md`](./setup/hooks/README.md).

| Hook | Evento | En una línea |
|---|---|---|
| `mark-code-dirty.py` | PostToolUse | Marca que la sesión editó código **de este proyecto** |
| `check-vault-updated.py` | Stop | Si hubo código y el vault no se actualizó, bloquea el cierre |
| `memory-flush.py` | PreCompact | Pausa la compactación una vez si el vault sigue desfasado |
| `validate-graphiti-group-id.py` | PreToolUse | Ningún episodio de Graphiti sin `group_id` válido |
| `merge-gate-guard.py` | PreToolUse (Bash) | **W3 del RFD 04**: bloquea el merge a `main` que no pasó por la compuerta |

Los tres primeros son anti-drift del vault; los dos últimos son compuertas. El
`merge-gate-guard` existe porque en la prueba deliberada del 2026-08-07 la skill
`workstream-merge-gate` **no llegó a correr** en 3 de 4 escenarios —ganó el
trigger otra skill— y se colaron 2 merges a `main` sin confirmación. Una
convención escrita volvió a fallar; un arnés, no.

Hay además un hook de **git** (`post-commit`) que, en los commits que tocan
código, regenera con Graphify un **`codebase-map-snapshot.md`** recortado (~2 KB)
en el vault. **Nunca toca el `codebase-map.md` curado**: ese tiene un humano como
único escritor. Se instala por repo.

---

## Qué hay en `setup/`

La tabla de componentes —qué es cada archivo y para qué sirve— vive en
[`setup/README.md`](./setup/README.md), junto con el **registro de secretos**
(cada credencial con su ruta, su consumidor y cómo rotarla) y el detalle del
modo single-laptop.

Un apunte que no está ahí: `setup/scripts/` contiene `adr-index.py`, que
regenera el índice de ADRs del vault y sabe verificarse a sí mismo:

```bash
setup/scripts/py setup/scripts/adr-index.py <ruta-a-la-carpeta-ADRs> --check   # rc=0 si está al día
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

**Los seis arneses.** Todos salen `rc=0` cuando el setup está sano, ninguno toca
tu instalación real —trabajan sobre carpetas de laboratorio— y se corren desde
la raíz del repo:

```bash
setup/scripts/py setup/scripts/tests/test-sync-guard.py        # el guard del sync no borra por accidente
setup/scripts/py setup/scripts/tests/test-skill-paths.py       # ninguna skill manda a una ruta inalcanzable
setup/scripts/py setup/scripts/tests/test-adr-index.py         # el índice de ADRs
setup/scripts/py setup/hooks/tests/test-mark-code-dirty.py     # el flag de código sucio
setup/scripts/py setup/hooks/tests/test-memory-flush.py        # la pausa de compactación
setup/scripts/py setup/hooks/tests/test-merge-gate-guard.py    # la compuerta de merge
```

Salida de la corrida del 2026-08-08, tras `sync-skills` + `sync-hooks`:

```
test-sync-guard.py          rc=0   Todo verde.
test-skill-paths.py         rc=0   Sin hallazgos: todo lo ejecutable se resuelve por ruta estable.
test-adr-index.py           rc=0   19/19 casos OK
test-mark-code-dirty.py     rc=0   12/12 casos OK
test-memory-flush.py        rc=0   11/11 casos OK
test-merge-gate-guard.py    rc=0   11/11 casos OK
```

`test-skill-paths` merece un apunte: caza la **clase** de fallo del 08-07 —una
skill que manda ejecutar algo por una ruta que no existe fuera de este repo— y
en sus dos primeras corridas cazó dos líneas escritas por el propio agente que
lo construyó. Si una línea es legítimamente del repo (un test, por ejemplo),
se declara con `[repo]` en la misma línea: la excepción queda por escrito y es
greppable.

Lo demás:

```bash
claude mcp list                                  # los MCP registrados y su salud
setup/scripts/py setup/scripts/adr-index.py <ruta-ADRs> --check
```

Del puente Telegram: manda un mensaje de prueba con `notify_telegram.py` (arriba)
y comprueba que llega al móvil.

---

## Protocolo al cambiar de laptop

1. En la laptop que dejas: cierra la sesión con la skill `session-close` — deja
   el vault con estado, pendientes y próximo paso.
2. Espera a que OneDrive diga "Actualizado", y que el vault haya hecho push.
3. En la nueva: escenario **A** de arriba, y `sync-skills` + `sync-hooks`.

El riesgo real no es la máquina: es abrir la laptop nueva con un vault a medio
escribir. Por eso el cierre va antes que el viaje.
