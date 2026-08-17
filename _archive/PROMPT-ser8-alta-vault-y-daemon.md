# PROMPT — Alta de la SER8: vault, capa 3 y daemon bajo systemd

**Escrito el 2026-08-17**, tras verificar la auditoría 31 y cerrar H1, H2 y H3b.
Para pegar en una sesión de Claude Code **abierta en la SER8**.

Va en `_archive/` por instrucción explícita del humano y porque es un prompt
operativo de un solo uso, como `PROMPT-higiene-vault-trabajo.md`. **Se poda sin
ceremonia** cuando la SER8 esté dada de alta: lo que sobreviva de aquí tiene que
acabar en `setup/telegram-bridge/README.md` o en `setup/README.md`, que es donde
un agente lo busca para operar. Si lees esto y la SER8 ya corre el daemon, este
fichero está de más.

## Antes de pegar nada: dos cosas en la Legion

Las dos son de empujar a GitHub, y sin ellas la SER8 recibe un setup viejo.

1. **El vault.** Su último commit era `ca9a615` (08-12) con cambios sin
   commitear hasta el 08-17. Desde la carpeta del vault:
   `git add -A && git commit -m "..." && git push`
2. **El repo.** `main` iba 2 commits por delante de `origin/main`, más los 4 de
   la rama `fix/20260817-separadores-linux-daemon`. Integrar por
   `workstream-merge-gate` y pushear.

## Las rutas elegidas, y por qué ésas

| Cosa | Ruta | Por qué |
|---|---|---|
| Vault | `~/DevSetup/ObsidianVault` | Es donde el **código** lo busca sin OneDrive: `vaultio.py:31-42`, `setup/hooks/check-vault-updated.py:53-65`. Clon normal: el `--separate-git-dir` de la Legion existe solo para sacar el `.git` de OneDrive |
| `.env` del puente | `~/.config/claude-telegram/.env` | Ya está en la lista de búsqueda de `notify_telegram.py:55-64` → **cero cambios de código**. El `/etc/atloos/telegram.env` de `setup/README.md:102` es columna «ruta futura (Debian)» y el código no lo lee |
| venv | `~/.local/share/claude-telegram/venv` | Misma raíz que usa `gitops.worktrees_root()` como fallback Unix, y fuera del repo |
| systemd | unit de **usuario** + `enable-linger` | Todo lo que el daemon necesita vive en `$HOME` (venv, vault, worktrees, `.env`). Root no aporta y sí quita: el bot ejecuta Claude Code **con escritura** en T2 |

## El prompt

```
Estás en la SER8 (floreano-server, Ubuntu 24.04). Objetivo: dejar esta máquina
operativa como segunda máquina del setup Atloos —vault, capa 3 y daemon de
Telegram bajo systemd— sin declarar verde nada que no hayas corrido.

Datos medidos en la Legion el 2026-08-17. Verifícalos igual antes de apoyarte:
- Sin OneDrive, el vault se busca en $HOME/DevSetup/ObsidianVault
  (vaultio.py:31-42, setup/hooks/check-vault-updated.py:53-65).
- El .env del puente se lee de ~/.config/claude-telegram/.env
  (notify_telegram.py:55-64). El README anuncia /etc/atloos/telegram.env como
  "ruta futura (Debian)": NO la uses, el código no la lee.
- El comando de test declarado del repo es `py setup/scripts/run-tests.py`
  (.claude/settings.json → GATE_TEST_CMD), y `py` NO existe en Linux.

Reglas: Graphiti no se usa (pospuesto, el vault es la memoria). NO edites
10-Projects/atloos/_PROJECT.md —hay otra sesión activa—: escribe solo tu nota en
10-Projects/atloos/sessions/. Cada paso falla cerrado: exit 0 no es "quedó
hecho", comprueba el ESTADO. No inventes rutas ni versiones: mide.

PASO 0 · Preflight, y para si algo falta
  a) El repo: https://github.com/JoseFloreano/Atloos.git. Si ya está clonado,
     `git pull`; si no, clónalo en $HOME. `git log --oneline -n 6` tiene que
     incluir los commits de `install-deps.sh` y `requirements.txt`. Si no están,
     PARA: no llegaron a esta máquina y el resto no tiene sentido.
  b) `command -v claude && claude --version`. Si falta, instálalo y autentícalo
     (una vez, interactivo) antes de seguir.
  c) `python3 --version` (>= 3.10) y `python3 -m venv --help`. En Ubuntu suele
     faltar: `sudo apt install python3-venv`.
  d) ⚠ Si el daemon está corriendo en la Legion, PÁRALO ALLÍ primero
     (`Stop-ScheduledTask -TaskName TelegramDaemon`). Dos long-pollings con el
     mismo token se pelean por getUpdates y el bot responde a medias.

PASO 1 · Vault
  Clona https://github.com/JoseFloreano/obsidian-vault.git en
  ~/DevSetup/ObsidianVault (clon normal; el --separate-git-dir de la Legion
  existe solo para sacar el .git de OneDrive y aquí no hay OneDrive).
  Comprueba que existe 10-Projects/atloos/_PROJECT.md. Si su última nota de
  sessions/ es anterior al 2026-08-17, el vault no se pusheó: dilo y para.

PASO 2 · Capa 3 (skills + hooks)
  NO uses setup/setup-new-machine.sh: aborta si falta Docker (líneas 55-58) y
  Graphiti está pospuesto — te pararía por algo que no usamos. Corre:
    bash setup/sync-skills.sh
    bash setup/sync-hooks.sh
  Verifica el estado, no el exit: 6 .py en ~/.claude/hooks/ y sección hooks en
  ~/.claude/settings.json con PreToolUse (x2), PostToolUse, Stop (x2) y
  PreCompact. sync-hooks ahora CREA ~/.claude si no existe y sale != 0 si no
  instala nada; si ves exit 0 con 0 hooks es un bug nuevo y hay que decirlo.

PASO 3 · Dependencias del puente
  bash setup/telegram-bridge/install-deps.sh
  Debe imprimir la versión importada de python-telegram-bot (22.8) y la ruta del
  intérprete del venv. ⚠ Ese camino NUNCA se ha corrido en Linux —en la Legion
  solo se ejerció su rama de fallo—: si se rompe, arreglarlo es parte del
  encargo. Deja el venv en la ruta por defecto salvo motivo medido.

PASO 4 · Secretos y proyectos
  ~/.config/claude-telegram/.env (chmod 600) con TELEGRAM_BOT_TOKEN,
  TELEGRAM_CHAT_ID y TELEGRAM_ALLOWED_USER_ID. Los valores los pone el humano:
  no los inventes ni los eches al log.
  setup/telegram-bridge/projects.json (gitignorado) con rutas LINUX y un `test`
  que corra como argv SIN shell. Candidato para atloos:
  `setup/scripts/py setup/scripts/run-tests.py` — ese resolutor existe y es
  100755. Antes de darlo por bueno, que decidan los arneses, no tú:
    setup/scripts/py setup/telegram-bridge/tests/test-testcmd.py
    setup/scripts/py setup/telegram-bridge/tests/test-perfil-bot.py
  El segundo se pone rojo si el allowlist de escritura del bot no permite el
  comando declarado. Sin `test` válido, /merge queda bloqueado por diseño.

PASO 5 · El daemon a mano, ANTES de systemd
  Con el python del venv y cwd en setup/telegram-bridge. Debe imprimir "Daemon
  en marcha (long polling)". Pruébalo desde el móvil con /status y /p atloos. Si
  no responde, no pases al paso 6: una unit que arranca algo roto solo esconde
  el fallo.

PASO 6 · systemd, unit de USUARIO
  ~/.config/systemd/user/claude-tg.service + `loginctl enable-linger <usuario>`
  para que sobreviva sin sesión abierta. Usuario normal, NUNCA root: todo lo que
  necesita vive en $HOME y el bot ejecuta Claude Code con escritura en T2.
  La unit tiene que cumplir:
    - ExecStart con la ruta ABSOLUTA del python del venv (no `python3`)
    - WorkingDirectory = setup/telegram-bridge (el daemon escribe logs/ ahí)
    - EnvironmentFile = ~/.config/claude-telegram/.env
    - Restart=on-failure con RestartSec (no Restart=always ciego)
    - NADA de CLAUDE_CONFIG_DIR: apuntar a un perfil propio deja al bot SIN los
      6 hooks (auditoría 31, H4). El ahorro de tokens no paga la capa 3.
  Verifica de verdad: `systemd-analyze --user verify`, `systemctl --user status`,
  `journalctl --user -u claude-tg -n 50`, y si puedes reinicia la máquina y
  vuelve a probar el bot. Escribe un arnés para lo que sea comprobable en
  estático (que el ExecStart apunte al venv y no al python del sistema, que no
  aparezca CLAUDE_CONFIG_DIR) y déjalo en setup/scripts/tests/.

PASO 7 · Suite y registro
  setup/scripts/py setup/scripts/run-tests.py
  Esperado: 25 arneses. El único rojo aceptable hoy es test-suelo-python.py, que
  exige un 3.10 REAL y aquí hay 3.12. NO lo silencies ni le pongas un skip: hay
  una decisión abierta del humano con tres salidas (instalar 3.10, exención
  declarada con fecha, o subir el suelo a 3.12). Anota el número exacto.
  Cierra con tu nota de sesión en el vault: qué quedó operativo, qué NO, el
  número de la suite y las rutas reales que usaste. Si tocas código del repo va
  en rama —main es protegida y su merge lo gobierna workstream-merge-gate—.
```

## Lo que este prompt NO hace, a propósito

- No monta Graphiti (pospuesto por ADR, no es deuda).
- No integra nada a `main` desde la SER8.
- No da por bueno el paso 3: el camino del venv es exactamente el que **no se
  pudo ejercer** desde la Legion, donde solo se ejerció su rama de fallo.
- No toca el suelo de Python. Hay una decisión humana abierta y un `skip` puesto
  a la ligera la cierra en falso.
