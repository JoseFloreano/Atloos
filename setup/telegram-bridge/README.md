# Puente Telegram — Vía 1: notificaciones (fase T0)

"Mándamelo por telegram": al terminar una tarea larga, Claude Code te manda el
resultado al móvil. **Solo envía** — no hay bot escuchando, ni daemon, ni URL
pública, ni túnel (`sendMessage` es un POST HTTPS saliente).

Diseño: `docs/telegram/00-DISENO-TELEGRAM-BRIDGE.md` §1 · ADR:
`10-Projects/claude-setup/ADRs/ADR-20260801-puente-telegram.md`

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
py notify_telegram.py "Prueba desde Claude Code"
```

Debe llegar al móvil e imprimir `Enviado: mensaje de N caracteres`.

```bash
# Mensaje largo → resumen + adjunto .md automático
py -c "print('línea de prueba ' * 500)" | py notify_telegram.py

# Adjuntar un archivo concreto
py notify_telegram.py "Informe listo" --file ../../docs/00-INDICE-GENERAL.md
```

### 5. Usarlo desde Claude Code

Ya está: pídele **"mándamelo por telegram"** o **"avísame por telegram cuando
termine"** y la skill `notify-telegram` hace el resto.

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
