# Puente Telegram — Vía 1: notificaciones (fase T0)

"Mándamelo por telegram": al terminar una tarea larga, Claude Code te manda el
resultado al móvil. **Solo envía** — no hay bot escuchando, ni daemon, ni URL
pública, ni túnel (`sendMessage` es un POST HTTPS saliente).

Diseño: `docs/telegram/00-DISENO-TELEGRAM-BRIDGE.md` §1 · ADR:
`10-Projects/atloos/ADRs/ADR-20260801-puente-telegram.md`

| Pieza | Qué es |
|---|---|
| `notify_telegram.py` | El script. Solo stdlib (`urllib`, `json`, `pathlib`) |
| `.env` | Tus credenciales. **Ignorado por git** — nunca se versiona |
| Skill `notify-telegram` | Lo que hace que Claude lo use solo al pedírselo |

---

## Setup en 5 pasos

### 1. Crear el bot (@BotFather)

En Telegram, habla con **@BotFather**:

```
/newbot
→ nombre visible:  Claude Notifier
→ username:        lo_que_sea_bot     (debe terminar en "bot")
```

Te devuelve un **token** con la forma `123456789:AAE...`. Trátalo como una
contraseña: quien lo tenga puede escribir como tu bot.

### 2. Obtener tu `chat_id`

Telegram no te lo dice: hay que provocarlo con un mensaje.

1. **Escríbele algo al bot** (busca su username y manda "hola"). Sin este paso
   `getUpdates` viene vacío — un bot no puede iniciar conversación contigo.
2. Consulta las actualizaciones (sustituye `<TOKEN>`):

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates"
```

Busca `"chat":{"id":987654321,...}` → ese número es tu `TELEGRAM_CHAT_ID`
(en chats privados es positivo; en grupos es negativo).

### 3. Crear el `.env`

```bash
cp .env.example .env    # PowerShell: Copy-Item .env.example .env
notepad .env            # pega token y chat_id, guarda
```

Comprueba que git lo ignora (debe imprimir la ruta):

```bash
git check-ignore -v setup/telegram-bridge/.env
```

**Restringir permisos** (equivalente Windows del `chmod 600`) — deja el archivo
legible solo por tu usuario:

```powershell
icacls .env /inheritance:r /grant:r "$env:USERNAME:(R,W)"
icacls .env          # verificar: solo tu usuario en la lista
```

### 4. Probar

```bash
setup/scripts/py setup/telegram-bridge/notify_telegram.py "Prueba desde Claude Code"
```

Debe llegar al móvil e imprimir `Enviado: mensaje de N caracteres`.

```bash
# Mensaje largo → resumen + adjunto .md automático
setup/scripts/py -c "print('línea de prueba ' * 500)" \
  | setup/scripts/py setup/telegram-bridge/notify_telegram.py

# Adjuntar un archivo concreto
setup/scripts/py setup/telegram-bridge/notify_telegram.py "Informe listo" \
  --file docs/00-INDICE-GENERAL.md
```

> Estos ejemplos usan `setup/scripts/py` —el resolutor— y rutas desde la raíz
> del repo, no `py` y rutas relativas a esta carpeta: `py` no existe en Linux y
> era el motivo de que estas líneas se copiaran y fallaran en la SER8.

### 5. Usarlo desde Claude Code

Ya está: pídele **"mándamelo por telegram"** o **"avísame por telegram cuando
termine"** y la skill `notify-telegram` hace el resto.

---

---

# Fase T1 — Chat desde Telegram (`tg_daemon.py`)

Escribirle al bot y que **Claude Code responda leyendo el repo que elijas**.
Long polling saliente: sigue sin haber URL pública ni túnel.

> **T1 es SOLO LECTURA.** El bot lee y conversa; no edita, no ejecuta comandos.
> `/write on` y el botón de merge llegan en T2. (El triage con
> modelo barato sigue en el backlog, T3-bis.)

## Requisitos

Las dependencias están **declaradas y ancladas** en `requirements.txt`
(`python-telegram-bot==22.8`, la versión medida en la Legion el 2026-08-17). El
comando NO es el mismo en las dos plataformas:

```bash
# Linux (SER8, Ubuntu 24.04)
bash setup/telegram-bridge/install-deps.sh
```

```powershell
# Windows (Legion)
py -m pip install -r setup/telegram-bridge/requirements.txt
```

> ⚠ **En Linux no basta `pip install`, y el `py` de estas páginas no existe
> allí.** Ubuntu 24.04 rechaza el `pip install` pelado con
> `externally-managed-environment` (PEP 668), así que `install-deps.sh` crea un
> **venv fuera del repo** —bajo `$XDG_DATA_HOME` o `~/.local/share`, nunca
> dentro, porque esto vive en OneDrive— e **importa el módulo para comprobar
> que quedó instalado**: un `pip` que sale 0 no es evidencia de que el daemon
> arranque. Al terminar imprime la ruta del intérprete, que es la que necesita
> el `ExecStart` de la unit de systemd.
>
> Si `python3 -m venv` falla, en Debian/Ubuntu falta el paquete:
> `sudo apt install python3-venv`. El script lo dice y sale ≠ 0.

Más el `.env` de arriba con **una clave nueva**:

```
TELEGRAM_ALLOWED_USER_ID=987654321
```

Es tu `user_id` de Telegram (en chat privado coincide con el `chat_id` del paso 2;
si falta, el daemon usa `TELEGRAM_CHAT_ID`). **Sin allowlist el daemon no arranca**:
cualquiera puede escribirle a un bot porque su username es público.

## Configurar los proyectos

```bash
cp projects.example.json projects.json    # PowerShell: Copy-Item
notepad projects.json
```

Mapea `nombre → ruta absoluta del repo`. El nombre es lo que escribes en
`/p <nombre>`; **usa el mismo que la carpeta del vault** (`10-Projects/<nombre>`)
para que la memoria del proyecto case. `projects.json` está en `.gitignore`
(contiene rutas de tu máquina).

## Arrancar

```bash
py tg_daemon.py        # Windows · Ctrl+C para parar
```

```bash
# Linux: con el intérprete del venv, no con python3 del sistema
"${XDG_DATA_HOME:-$HOME/.local/share}"/claude-telegram/venv/bin/python tg_daemon.py
```

Debe imprimir `Daemon en marcha (long polling)`. Los eventos van a
`logs/daemon-YYYYMM.log` (sin contenidos de mensajes ni token).

## Comandos

| Comando | Qué hace |
|---|---|
| `/p <proyecto>` | Activa un proyecto. Sin argumento o con nombre inexistente → lista |
| *(mensaje normal)* | Consulta al proyecto activo. Sin proyecto → error + lista |
| `/new` | Empieza conversación nueva (la anterior queda en `/chats`) |
| `/chats` | Lista las conversaciones guardadas del proyecto, numeradas |
| `/chat <n>` | Retoma la conversación n |
| `/model [m]` | Ver o cambiar modelo (`opus`, `sonnet`, `haiku`, `fable`, `default`) |
| `/status` | Proyecto, conversación, modo, rama, si hay invocación en vuelo |
| `/progress [live\|off]` | Última etapa del trabajo en curso; `live` = panel que se auto-edita. No lo bloquea un vuelo en curso |

Los de **escritura** (`/write`, `/diff`, `/commit`, `/test`, `/push`, `/merge`,
`/done`) están en la sección T2, más abajo.

## Comportamiento que conviene conocer

- **Una invocación por chat**: si escribes mientras trabaja, responde `⏳` en vez
  de encolar (dos `--resume` concurrentes entrelazan el transcript).
- **TTL de 24 h**: tras un día sin actividad en un proyecto, el siguiente mensaje
  abre sesión nueva y lo avisa. Un `--resume` eterno arrastra contexto que se
  paga en cada turno; la continuidad durable la da el vault, no el transcript.
- **Los mensajes enviados con el daemon apagado SE PIERDEN.** Al arrancar usa
  `drop_pending_updates=True`, así que Telegram descarta la cola acumulada. Es
  **a propósito**: sin eso, al reiniciar el bot te contestaría de golpe a
  mensajes de hace horas — invocando a Claude por cada uno — y responder a
  preguntas viejas fuera de contexto es peor que no responder. Si no estás
  seguro de si está vivo, mándale `/status`: si no contesta, no está corriendo.
- **Timeout de 10 min** por consulta: si se pasa, mata el proceso y te avisa.
- **Máx. 15 turnos** por mensaje.
- **Respuestas largas**: >4096 caracteres → resumen + `.md` adjunto (misma
  política que T0, código compartido).
- Si Claude intenta algo fuera de lectura, el mensaje incluye
  `🔒 N acción(es) bloqueada(s)` — es el modo lectura mordiendo, no un error.

## Dejarlo corriendo en Windows

Por ahora, **una ventana de terminal** abierta con `py tg_daemon.py` es
suficiente y lo más fácil de depurar (el polling muere al cerrarla o apagar el
equipo — asumido para v1).

Si prefieres que arranque solo al iniciar sesión, Task Scheduler básico:

```powershell
$py  = (Get-Command py).Source
$dir = "<ruta>\setup\telegram-bridge"
$a = New-ScheduledTaskAction -Execute $py -Argument "tg_daemon.py" -WorkingDirectory $dir
$t = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "TelegramDaemon" -Action $a -Trigger $t
```

Para pararlo: `Stop-ScheduledTask -TaskName TelegramDaemon` (o cierra la ventana).
El arranque 24/7 con `systemd` llega cuando exista la mini PC — no lo montes aquí.

---

# Fase T2 — Modo escritura (`/write`)

Desarrollo real desde el móvil. Diseño completo: `ADR-20260801-puente-telegram`.

## La idea en una frase

**El bot nunca escribe en tu árbol de trabajo.** Al hacer `/write on`, la
conversación recibe **su propia rama y su propio worktree**, fuera de OneDrive:

```
Tu repo (OneDrive)              Worktree del bot (LOCAL)
main + tus cambios sin          %LOCALAPPDATA%\claude-tg-worktrees\
commitear ← intactos              <proyecto>\<fecha>-<slug>\  ← rama tg/<fecha>-<slug>
```

Puedes estar editando en la laptop mientras el bot desarrolla: no se ven.

**1 conversación = 1 rama = 1 worktree.** `/new` en escritura abre rama nueva;
`/chat <n>` retoma la suya; `/chats` muestra cuál es la de cada una.

## Comandos de escritura

| Comando | Qué hace | Botón |
|---|---|---|
| `/write on` \| `off` | Activa/desactiva el modo. Crea la rama y el worktree la primera vez | — |
| `/diff` | Resumen de cambios; el diff completo llega como adjunto si es largo | — |
| `/commit [mensaje]` | Commitea en la rama. Sin mensaje, el agente propone uno | — |
| `/test` | Corre el comando de test del proyecto dentro del worktree | — |
| `/push` | Publica la rama; con `gh`, crea/actualiza el PR y manda el link | — |
| `/pull` | Trae `main` a la rama de la conversación; si trajo cambios, el verde de `/test` caduca y hay que repetirlo | — |
| `/merge` | Integra en `main` (squash) | **Sí** |
| `/done` | Quita worktree, borra la rama y archiva la conversación | — |

## Las tres reglas que gobiernan T2

1. **Los git ops los ejecuta el daemon, nunca el agente.** El agente puede
   editar y correr tests; `git commit`, `push` y `merge` están **denegados**
   para él. Si lo intenta, verás `🔒 N acción(es) bloqueada(s)`. Así ninguna
   inyección de prompt puede publicar nada.
2. **Botón solo para `/merge`**, que es lo único que toca `main`. Caduca a los
   5 minutos.
3. **`/merge` exige tests en verde** posteriores al último commit. Si commiteas
   después de un `/test`, el verde caduca y hay que repetirlo.

## Durante tareas largas

- **Timeout de 90 minutos** en escritura (10 en lectura); hasta **60 turnos**
  por invocación (15 en lectura).
- **Checkpoint cada 30 minutos** con el tiempo transcurrido y la última etapa:
  el agente va anotando su avance en `.tg/progress.md` (excluido de los commits).
- `/chat` y `/p` responden `⏳` mientras hay una invocación en curso — cambiar
  de conversación a mitad de vuelo entregaría la respuesta a la equivocada. El
  desarrollo **paralelo** es una idea futura (RFD 03), no está en T2.

## Configurar los tests (necesario para `/merge`)

El comando de test sale, en este orden:

1. **`.claude/settings.json` del repo**, bajo `env.GATE_TEST_CMD` — archivo
   versionado, así que viaja entre máquinas y se ve en el diff:

   ```json
   { "env": { "GATE_TEST_CMD": "py setup/scripts/run-tests.py" } }
   ```

2. **`projects.json`**, como fallback para repos que no declaran nada:

   ```json
   { "mi-repo": { "path": "C:\\ruta\\al\\repo",   "test": "py -m pytest -q" } }
   { "mi-repo": { "path": "/home/tu/ruta/repo",   "test": "python3 -m pytest -q" } }
   ```

   > **El primer token se resuelve, no se copia.** Si el comando empieza por
   > `py`, `python3` o `python`, el daemon lo cambia por el intérprete que ya
   > lo está ejecutando (`testcmd.argv`), así que `py -m pytest -q` también
   > corre en Linux. Cualquier otro ejecutable (`npm`, `flutter`, `pytest`) se
   > lanza tal cual y tiene que estar en el `PATH`. Aquí se corre **argv sin
   > shell**: `&&`, `||`, `|` y `;` se rechazan con un mensaje, no se ejecutan.

El **repo gana** sobre `projects.json` a propósito: `projects.json` es
por-máquina y no viaja, así que si ganara él, la copia vieja de otra laptop
seguiría imponiendo su verde. En `atloos` ese verde era `py -m compileall`, que
solo comprueba que los archivos parsean — un `/merge` desde el móvil entraba a
`main` sin ejecutar un solo arnés.

El comando debe ser **un ejecutable con sus argumentos**, sin `&&`, `||`, `|`
ni `;`: aquí se corre argv sin shell y un metacarácter se rompería (en la
laptop, donde `gate-test.py` usa shell, funcionaría — esa asimetría es justo lo
que se evita). Si necesitas encadenar, envuélvelo en un script.

Sin comando declarado por ninguna vía, `/test` avisa y **`/merge` queda
bloqueado** (no hay verde posible). Se acepta el formato viejo de
`projects.json` (`"nombre": "ruta"`), sin tests.

## Recuperación

- ¿El bot hizo un desastre? `/done` sin mergear: se borra la rama y el worktree.
  Tu `main` y tu árbol nunca supieron que existió.
- `/done` **se niega** si quedan cambios sin commitear en archivos trackeados
  (no te hace perder trabajo). La basura de los tests (`__pycache__`) no cuenta.
- Si el daemon muere con worktrees vivos, al arrancar **reconcilia** contra
  `git worktree list` y reporta discrepancias — nunca borra por su cuenta.

## Seguridad de T1 (lo que NO se negocia)

1. **Allowlist primero**: cualquier `user_id` distinto se descarta en silencio,
   antes de procesar nada. No respondemos ni "no autorizado": eso confirmaría
   que el bot existe. El intento sí queda en el log.
2. **Solo lectura real**: `--allowedTools Read,Grep,Glob` + `--permission-mode
   dontAsk` (deniega en vez de preguntar; en headless una pregunta colgaría el
   proceso). **Nunca** `--dangerously-skip-permissions`.
   En **escritura** el modo es `acceptEdits` + una segunda barrera que limita
   `Write`/`Edit` al repo del proyecto: `dontAsk` NO impone frontera de
   directorio (verificado con canario — commit `2e44223`). Y en ambos modos se
   **deniega la lectura** de rutas con secretos (`.env` del bridge, `~/.ssh`,
   `~/.aws`) con rutas absolutas — los globs `Read(**/.env)` no funcionan.
3. **`CLAUDE_TG_BOT=1`** en el entorno de cada invocación: el hook anti-drift
   `check-vault-updated.py` sale en silencio (no hay humano que cierre el vault).
   *(Consecuencia conocida y no resuelta: en un servidor 24/7 ese hook no
   dispararía nunca, que es donde nadie mira. Auditoría del RFD 19.)*
4. Los logs guardan eventos y longitudes, **no** el contenido de los mensajes ni
   el token.

### La allowlist tiene que incluir el runner del repo

Las entradas `Bash(...)` de `WRITE_TOOLS` nombran suites genéricas (`pytest`,
`npm test`, `ruff`, `flutter test`). **Los arneses de esta casa no encajan en
ninguna**: se corren como `py setup/scripts/run-tests.py` y, desde el sprint 11,
como `setup/scripts/py setup/scripts/run-tests.py` — **las dos formas están en
la lista**, porque la primera es la que declara el repo y la segunda es la que
el agente teclea en Linux. Sin una entrada para
eso, el agente del puente tiene prohibido correr los tests de su propio repo —
y eso no es teórico: una auditoría escrita desde el móvil
(`docs/auditoria/21-AUDITORIA-DEL-BUCLE-GOAL-Y-LOOP.md`) tuvo que declarar en su
cabecera que no había visto un solo verde, por esta razón exacta.

La entrada es **estrecha a propósito** —el path del runner, nunca `Bash(py:*)`,
que sería ejecutar cualquier cosa— y la vigila
`tests/test-perfil-bot.py`, que no compara contra una constante copiada: resuelve
la declaración con el **mismo** `testcmd.resolver` que usa `/test`. Si mañana el
repo declara otro runner y nadie toca la allowlist, ese arnés se pone rojo.
También fija las dos mitades del canario: el modo **lectura** sigue sin poder
correrlo, y un comando arbitrario sigue sin colarse.

Si enganchas otro proyecto cuyo runner no sea `pytest` ni `npm test`, esto hay
que repetirlo para él.

---

# Fase T3 — memoria y tokens (`ADR-20260801-bot-memoria-y-perfil`)

Cuatro piezas, todas del lado del daemon (el agente no gana permisos):

- **Perfil de skills propio**: cada invocación corre con `CLAUDE_CONFIG_DIR`
  apuntando a **`~/.claude-tg`** (subset de ~15 skills) — las ~29 del perfil
  normal costaban 4-5K tokens fijos por invocación.

  > **Ese nombre no es estético: es lo que hace que el perfil tenga hooks.**
  > `wire-hooks.py` (y `sync-hooks.ps1`) cablean `~/.claude` y `~/.claude-*`.
  > El nombre viejo, `%LOCALAPPDATA%\claude-tg-profile`, no casaba con ese
  > glob, así que encender el ahorro de tokens dejaba al bot con **0 de 6
  > hooks, en silencio** — la configuración recomendada era la desprotegida
  > (auditoría 31, H4). Desde entonces el daemon **se niega** a usar un perfil
  > sin hooks cableados: cae a la config normal y lo dice en el log. Si tienes
  > el nombre viejo, renómbralo y corre
  > `setup/scripts/py setup/scripts/wire-hooks.py`.
- **`CLAUDE.md` versión bot**: al crear el worktree se genera una copia SIN las
  órdenes de vault/Graphiti (incumplibles desde el worktree; solo peso muerto).
- **Briefing inyectado**: la primera invocación de cada conversación lleva un
  extracto del `_PROJECT.md` + el `codebase-map.md` curado + un resumen fresco
  del `codebase-map-snapshot.md` (≤800 chars), leídos por el daemon —
  el agente arranca sabiendo el estado del proyecto sin pedir permisos.
- **Nota de sesión al vault**: en `/done`, el DAEMON escribe
  `sessions/<fecha>-tg-<slug>.md` (rama, commits, etapas). El agente nunca toca
  el vault; la memoria durable la escribe código nuestro.

---

## Detalles de implementación

- **Texto plano, sin `parse_mode`** — decisión deliberada. Los resúmenes traen
  código, `<`, `>`, `&` y markdown; con `parse_mode=HTML/Markdown` un solo
  carácter mal escapado devuelve **HTTP 400 y el aviso nunca llega**. En texto
  plano no hay nada que escapar y los emoji/acentos viajan bien (UTF-8).
- **Límites** (Bot API): texto 4096 chars, documento 50 MB, ~1 msg/s por chat.
  Si el mensaje excede 4096 → resumen de ~800 chars + el texto completo como
  `claude-notify-<fecha>.md` adjunto.
- **Credenciales**: entorno primero, `.env` como fallback. El token **nunca**
  se imprime: los errores lo sustituyen por `<TOKEN-OCULTO>` (viaja en la URL).
- **Red**: timeout 15 s y **un** reintento ante 429/5xx respetando
  `Retry-After`. Códigos de salida: `0` ok · `1` uso/configuración · `2` red/API.

## Troubleshooting

| Síntoma | Causa y arreglo |
|---|---|
| `Faltan credenciales` | No hay `.env` ni variables de entorno. Paso 3 |
| `getUpdates` devuelve `{"result":[]}` | No le has escrito al bot todavía, o ya consumiste los updates. Manda otro mensaje y repite |
| `HTTP 400: chat not found` | `chat_id` mal copiado (¿te llevaste el `id` del `from` en vez del de `chat`?) |
| `HTTP 401: Unauthorized` | Token incorrecto o revocado. `/revoke` en BotFather y actualiza el `.env` |
| `HTTP 403: bot was blocked by the user` | Desbloquea el bot en Telegram |
| `HTTP 429` | Rate limit; el script ya reintenta una vez respetando `Retry-After` |
| Sale `PruebaÃ¡` o similar | Consola en cp1252. El script fuerza UTF-8; si persiste, `chcp 65001` |

## Seguridad

- El `.env` está en `.gitignore` y **no debe copiarse a OneDrive ni a la carpeta
  de skills** (anti-patrón S5: las skills se sincronizan y empaquetan).
- El token no aparece en logs ni en mensajes de error.
- Esta vía **solo envía**. No hay endpoint escuchando, así que no hay superficie
  de ataque entrante — eso llega (con allowlist) en la fase T1 del daemon.
- Si el token se filtra: `/revoke` en @BotFather invalida el viejo al instante.
