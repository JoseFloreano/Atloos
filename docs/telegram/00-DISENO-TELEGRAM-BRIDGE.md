# Puente Telegram ↔ Atloos — Diseño preliminar (pre-ADR)

> **Fecha:** Agosto 2026 (investigado con fuentes primarias el 2026-08-01)
> **Estado (2026-08-01):** IMPLEMENTADO — T0 (avisos), T1 (chat lectura), T2
> (escritura por worktree) y T3 (memoria/tokens) operan en `setup/telegram-bridge/`
> (`notify_telegram.py`, `tg_daemon.py`, `gitops.py`, `progress.py`, `vaultio.py`).
> Este doc conserva el diseño original; lo vigente vive en los RFDs 02-06 de esta
> carpeta y en el ADR del puente (vault). Ojo: donde este doc diga
> `setup/scripts/` para el script de avisos, la ruta real es `setup/telegram-bridge/`.
> **Origen:** dos ideas del usuario — (1) recibir respuestas largas por Telegram ("mándamelo por telegram"), (2) chatear con Claude Code desde Telegram con selector de proyecto por comando y continuidad cross-session.

---

## 0. El hallazgo que simplifica todo: NO necesitas ngrok

Un bot de Telegram tiene dos modos de recibir mensajes: webhook (Telegram te llama → requiere URL pública HTTPS) y **long polling** (`getUpdates`: tu bot llama saliente a api.telegram.org y espera — funciona detrás de NAT, sin puerto abierto, sin certificado, sin túnel). Para un bot personal el polling es el modo correcto; el webhook solo aporta a escala/multi-instancia. Y para la vía 1 (solo ENVIAR) ni siquiera hay bot escuchando: `sendMessage` es un POST HTTPS saliente y ya.

**Respuesta a tu pregunta de proveedores**: no existe "pago único por URL permanente" — los dominios son alquiler anual por diseño (ICANN/registries cobran cuotas anuales; máximo se prepagan ~10 años). Si algún día hiciera falta URL pública estable, el ranking real (verificado 2026-08-01):

| Opción | Costo | URL estable | Nota |
|---|---|---|---|
| Long polling (recomendado) | $0 | no hay URL | cero infraestructura |
| Tailscale Funnel | $0 | sí (`*.ts.net`) | beta; puertos 443/8443 (compatibles con Telegram); banda limitada no publicada |
| Cloudflare Tunnel + dominio propio | ~$10-12 USD/**año** | sí (tu dominio) | el "serio"; túnel gratis, el dominio es lo recurrente |
| ngrok free | $0 | sí (dev domain asignado) | tope duro: 20.000 requests y 1 GB **al mes** |
| trycloudflare / localtunnel / serveo | $0 | NO (aleatoria) | solo demos |

## 1. Vía 1 — Notificaciones: "mándamelo por telegram" (esfuerzo: ~½ día)

Sin servidor, sin daemon, sin bot escuchando. Solo hace falta:

1. Crear el bot una vez con @BotFather → `TELEGRAM_BOT_TOKEN`; obtener tu `TELEGRAM_CHAT_ID` (le escribes al bot y lo lees de getUpdates una vez).
2. Script `notify-telegram.py` en `setup/scripts/`: POST a `api.telegram.org/bot<token>/sendMessage`. Reglas: texto ≤4096 chars (límite oficial) → si la respuesta es más larga, mandar resumen + archivo adjunto vía `sendDocument` (hasta 50 MB); ~1 msg/segundo por chat.
3. Skill `claude-code/notify-telegram`: "Use when the user says 'mándamelo por telegram', 'avísame por telegram', 'notifícame cuando termine'". Pasos: al terminar la tarea, componer resumen corto + archivo si excede 4096, ejecutar el script. Requisitos con fallback: sin `TELEGRAM_BOT_TOKEN` en el entorno → decirlo y entregar en el chat normal.
4. Credenciales SIEMPRE en `.env`/entorno (regla 5 del sistema de skills / anti-patrón S5) — jamás en la skill ni en OneDrive.

Variante opcional posterior: hook Stop "si la sesión duró >N min y hay flag de aviso pendiente, notificar" — pero la skill cubre el caso de uso tal como lo planteaste (tú lo pides explícitamente al lanzar la tarea larga).

## 2. Vía 2 — Chat desde Telegram con selector de proyecto

### 2.1 La mecánica que lo hace posible (verificada en docs oficiales)

- `claude -p "mensaje" --output-format json` devuelve `session_id`; `claude -p "mensaje" --resume <session_id>` continúa ESA conversación. Cada mensaje de Telegram = una invocación con `--resume`. Cross-session gratis: los IDs persisten en disco (`~/.claude/projects/...`).
- **El selector de proyecto es el `cwd`**: la sesión se busca/guarda según el directorio desde el que se invoca, y el CLAUDE.md/memoria del proyecto se cargan de ahí. El daemon mapea `proyecto → ruta` y spawnea con ese cwd. (Esto encaja perfecto con nuestro aislamiento de memoria por proyecto: el bot hereda las Memory Rules del CLAUDE.md del proyecto elegido.)
- Sin locking entre resumes concurrentes → el daemon serializa: UNA invocación en vuelo por chat (cola/mutex).

### 2.2 Protocolo de comandos (tu diseño, refinado)

```
/p <proyecto>      ← selector; sin proyecto activo, todo mensaje rebota con error + lista de proyectos
/chats             ← lista las conversaciones guardadas del proyecto activo (nombre + fecha)
/chat <n> | /new   ← reanudar conversación vieja | empezar una nueva
/status            ← proyecto activo, chat activo, si hay invocación en vuelo
/write on|off      ← escalar/desescalar permisos de escritura (default: off)
```

Estado del daemon (un JSON local): `chat_id de telegram → {proyecto_activo, session_id_activo, historial de sesiones por proyecto}`. Con eso, "seguir respondiendo con el mismo comando" es automático: si ya hay proyecto activo en ese chat, los mensajes van directo — el comando solo hace falta para cambiar.

### 2.3 Tres formas de construirlo (decisión para el ADR)

| Opción | Qué es | A favor | En contra |
|---|---|---|---|
| **A. Plugin oficial de Anthropic** (`--channels plugin:telegram@claude-plugins-official`) | Telegram inyecta mensajes en una sesión local YA corriendo; pairing por código + allowlist | Oficial, mínimo esfuerzo, relay de respuestas resuelto | UNA sesión activa — **no hay selector de proyectos**; research preview (puede cambiar) |
| **B. Importar RichardAtCT/claude-code-telegram** (2.5k★, MIT, v1.6.0 mar-2026, Python) | Bot completo: multi-repo `/repo`, persistencia por usuario+directorio, allowlist, rate limit, sandbox de directorios, audit log | Ya resuelve el 90% de tu diseño; auditable (protocolo de importación doc 05 §2 aplica igual que a skills) | Proyecto grande para leerlo completo línea a línea (obligatorio antes de correrlo — es un agente con tu filesystem) |
| **C. Daemon propio (~200-300 líneas, Python: `python-telegram-bot` + Agent SDK o CLI)** | Exactamente tu protocolo y nada más | Encaja 1:1 con el setup (skills, .env, vault); superficie mínima que auditar; el SDK Python permite reenviar aprobaciones de permisos como botones inline de Telegram (`can_use_tool`) | Hay que escribirlo y mantenerlo |

Ideas a robar de terceros aunque construyamos propio: relay de permission-prompts como inline keyboard (six-ddc/ccbot), `APPROVED_DIRECTORY` + tope de costo por usuario (RichardAtCT).

**Recomendación preliminar**: C (daemon propio) con el SDK de Python, robando los tres patrones de arriba — B queda como plan B si C se alarga. A no cumple el requisito multi-proyecto.

### 2.4 Seguridad — no negociable (el bot es un agente con tu filesystem)

1. **Telegram no restringe quién le escribe a un bot** (es público por username): allowlist de tu `user_id` con drop silencioso, ANTES de procesar nada. Es la única defensa y va la primera.
2. **Permisos de Claude**: default `--permission-mode plan` o `dontAsk --allowedTools "Read,Grep,Glob"` (solo lectura + responder). Escritura solo tras `/write on`, y con `acceptEdits` + tools acotadas — JAMÁS `--dangerously-skip-permissions` en el host (docs: solo en contenedor/VM; sin protección ante prompt injection).
3. **Prompt injection indirecta** (webs/archivos que Claude lea durante la tarea): deny a `WebFetch`/`Bash(curl *)` por default en sesiones de bot; confirmación por botón para todo lo destructivo.
4. **Un resume en vuelo por chat** (cola) — dos concurrentes entrelazan el transcript.
5. **Secretos**: token en `.env` (600); no loggear updates completos; deny de lectura sobre `~/.ssh`, `~/.aws`, `.env`.

### 2.5 Integración con NUESTRO setup (lo que ningún proyecto de terceros trae)

- **Hook anti-drift**: `check-vault-updated.py` (Stop, exit 2) dispararía en cada invocación del bot y no hay usuario para "cerrar". Decisión propuesta: el daemon exporta `CLAUDE_TG_BOT=1` y el hook lo respeta (skip silencioso); el cierre del vault queda para la sesión normal en la laptop.
- **Vault**: sesiones de bot en modo lectura no tocan el vault; si `/write on`, aplican las reglas 6-7 (nota de sesión propia, nunca copias) — el CLAUDE.md del proyecto ya las trae.
- **Dónde corre**: la laptop principal encendida (el polling muere si se apaga — asumido y aceptado para v1). Si algún día quieres 24/7: la opción barata NO es un túnel sino mover el daemon a una mini-máquina siempre encendida; se decide en otro ADR.
- **Cowork no participa**: este puente es Claude Code/local. Las respuestas de Cowork ya te llegan por la app/notificaciones.

## 3. Fases propuestas

- **T0 (½ día)**: BotFather + script + skill `notify-telegram` → la vía 1 completa. Valor inmediato, riesgo ~cero (solo envía).
- **T1 (1 día)**: daemon MVP — polling, allowlist, `/p` + error sin proyecto, `/new`, resume por chat, SOLO LECTURA.
- **T2 (½ día)**: `/chats`, `/chat <n>`, `/write on|off`, aprobaciones por botones inline, troceo de respuestas >4096 + sendDocument.
- **T3 (½ día)**: endurecimiento — rate limit, tope de costo, audit log, `CLAUDE_TG_BOT=1` en el hook, systemd/Task Scheduler para autoarranque.

## 4. Decisiones abiertas para el ADR (cuando vuelvas)

1. Opción A/B/C del §2.3 (recomiendo C).
2. Default de permisos: ¿`plan` (propone, no toca) o `dontAsk` read-only (responde rápido)?
3. ¿El bot puede escribir código alguna vez (`/write on`) o es solo consulta/lanzar-tareas en v1?
4. ¿Un solo bot para las dos vías (el daemon también sirve las notificaciones) o token/bot separados? (Recomiendo uno solo: mismo token, `sendMessage` no estorba al polling.)
5. Nombre y ubicación en el repo: `setup/telegram-bridge/` con su README, fuera de `skills/` (es un servicio, no una skill; solo `notify-telegram` es skill).

---

## Fuentes principales

Bot API v10.2 y FAQ (core.telegram.org/bots/api, /faq, /webhooks) · Claude Code headless, CLI reference, sessions, permission-modes, channels (code.claude.com/docs) · plugin oficial (github.com/anthropics/claude-plugins-official) · RichardAtCT/claude-code-telegram · six-ddc/ccbot · linuz90/claude-telegram-bot · ngrok.com/pricing · developers.cloudflare.com (Tunnel, TryCloudflare) · tailscale.com/kb/1223/funnel. Detalle completo con citas en los informes de investigación de esta sesión (2026-08-01).
