# Encargo · SER8 — instalar y EJERCER el timer del vault

> **Este fichero viaja con el repo para que llegue con el `git pull`, y SE BORRA
> al terminar.** Es un encargo operativo, no documentación: en cuanto el timer
> esté instalado y ejercido, deja de ser cierto y pasa a ser una instrucción
> caducada esperando a que alguien la siga por error. Su predecesor
> (`_archive/PROMPT-ser8-alta-vault-y-daemon.md`) se quedó aquí después de
> cumplirse y hubo que podarlo en otra sesión, como pendiente. La poda es el
> paso 5 del bloque 7 y **no es opcional**.

## 1 · Contexto y tarea

El vault es un repo git. En las laptops lo sincroniza el plugin Git de Obsidian.
**La SER8 no tiene Obsidian**, así que en la única máquina que corre el daemon
24/7 nadie hace `pull` ni `push` salvo cuando hay conversación. `vault-sync.sh`
+ su timer son el sustituto del plugin. **Están escritos y NO instalados.**

Tu tarea: **instalarlo y probarlo por los dos lados.** Este fichero es tu brief
completo — no hace falta que leas ningún plan.

---

## 2 · Estado del mundo

### Verificado desde la Legion hoy (2026-08-20), con su comando

```
git rev-parse --short origin/main                 -> f81919e
git log --oneline -- setup/telegram-bridge/vault-sync.sh
      f81919e  fix(portabilidad): el vault-sync que decia "todo bien" ...
      56e4a9b  fix(puente): la guarda de la ventana de revision ...
      9274859  Necesito hacer muy sencillo el dar de al...
py setup/scripts/run-tests.py                     -> 42/42 verde, 2 CON ALGO SIN MEDIR
```

🔴 **LO PRIMERO, Y NO ES OPCIONAL: `git pull` antes de tocar nada.**
`f81919e` arregla un **fail-open mudo** de `vault-sync.sh`: con un intérprete que
no funciona salía **`0` — "al día, nada que hacer"** — y no sincronizaba nada.
Instalar la versión anterior es instalar un timer que miente. Detalle en
`bugs/bug-vault-sync-fail-open-mudo.md` del vault.

### De las notas del vault, fechadas y por escrito (no medido hoy)

| Cosa | Valor | Fuente |
|---|---|---|
| Repo | `/home/floreano/projects/personal/Atloos` (**no** en `$HOME`) | alta 08-18 |
| venv | `~/.local/share/claude-telegram/venv` | alta 08-18 |
| Secretos | `~/.config/claude-telegram/.env` (600, fichero real, fuera del repo) | alta 08-18 |
| systemd | unit de usuario `claude-telegram`, `enabled` + `active` | alta 08-18 |
| Linger | **`Linger=yes` YA puesto** — no repitas `enable-linger` | alta 08-18 |
| Python | 3.12.3 | alta 08-18 |

`[SUPUESTO]` **Todo lo de arriba es del 08-18 y no lo he medido hoy.**
Verifícalo antes de construir encima:

```
cd /home/floreano/projects/personal/Atloos && git log --oneline -1
ls ~/.local/share/claude-telegram/venv/bin/python
systemctl --user is-enabled claude-telegram && loginctl show-user "$USER" -p Linger
setup/scripts/py -c "import sys;sys.path.insert(0,'setup/telegram-bridge');import vaultio;print(vaultio.vault_root())"
```

`[SUPUESTO]` **La ruta del vault**: la resuelve `vaultio.vault_root()`, no la
adivines. El comando de arriba te la da.

### Fuera de git (ya debe estar; si falta, PARA y dilo)

```
~/.local/share/claude-telegram/venv        el venv del daemon
~/.config/claude-telegram/.env             600 · COPIAR nunca enlazar · NUNCA `source`
setup/telegram-bridge/projects.json        por-máquina y gitignorado: NO viaja con el clon
<vault>/.git                               el vault tiene que ser repo git CON remoto
```

### Firma de una corrida sana — establece la TUYA antes de tocar nada

La firma que conozco es la de **Windows**: `42/42 verde · 2 CON ALGO SIN MEDIR`.
**En la SER8 no va a ser esa**, y las diferencias esperadas son:

- `test-skill-catalog.py` corre en **modo PARCIAL**: `tiktoken` no está en el
  venv (conocido desde el 08-18). **No es un rojo.**
- El caso *"ruta de Windows en Linux"* de `test-deny-env-de-proyectos.py` **sí**
  corre ahí; el que se salta en Windows es el otro.
- `avisos-por-corte` se salta si ese repo no está en esa máquina.

**Orden que cierra el bloque:** corre la suite **ANTES** de cambiar nada y
apunta el número. Un rojo que coincida con una firma conocida de arriba **lo
arreglas, no lo reportas**. Un rojo que **no** esté en esa lista se reporta
siempre — la firma es lista cerrada, no excusa genérica.

---

## 3 · Decisiones del día

Apunta cada decisión no obvia en `docs/tmp/decisiones-ser8-timer-vault.md`
(gitignorado). Lo que deba sobrevivir va a la nota de sesión o al commit.

---

## 4 · Ownership

**POSEES y puedes escribir:**

```
~/.config/systemd/user/claude-telegram-vault.service     (fuera del repo)
~/.config/systemd/user/claude-telegram-vault.timer       (fuera del repo)
setup/telegram-bridge/claude-telegram-vault.timer.example   ← SOLO su cabecera de ESTADO
<vault>/10-Projects/atloos/sessions/2026-08-20-ser8-timer-vault.md
_archive/PROMPT-ser8-timer-vault.md                      ← este fichero, para BORRARLO
```

**NO TOCAS** — y lo que SÍ puedes hacer con cada uno:

- `vault-sync.sh` — recién arreglado y con arnés de 17 casos. **Puedes leerlo,
  ejecutarlo con `--verboso` y correr su arnés.** No lo edites: si crees que
  está mal, devuelve `NEEDS_CONTEXT` con el caso que lo demuestre.
- `tg_daemon.py`, `mergepol.py`, `altas.py`, `vaultio.py` — solo lectura.
- `_PROJECT.md` y `pendientes.md` del vault — **no los escribes**, ni al acabar.
  Un archivo, un escritor: los consolida `session-close`.

---

## 5 · Presupuesto

**Un solo frente, serializado.** No despaches subagentes ni paralelices: esto es
una instalación en la máquina 24/7 y la evidencia es secuencial por naturaleza.

---

## 6 · Predicción obligatoria

**Antes** de correr la suite por primera vez, escribe tu predicción de
`N/M verde · K sin medir`. Mide. **Si no coincide → `NEEDS_CONTEXT`, no sigas**:
un conteo que no cuadra es inventario ausente, no daño.

Lo mismo antes del caso C: predice el exit code y si habrá mensaje al móvil.

---

## 7 · Criterio de salida — TRES condiciones, cada una con su comando

No son una meta con "y": son tres, y se cumplen en orden. Ninguna la puede
satisfacer una afirmación tuya.

**A · Instalado y con próximo disparo real**

```
systemctl --user is-enabled claude-telegram-vault.timer     -> imprime "enabled"
systemctl --user list-timers claude-telegram-vault --all    -> NEXT no vacío y LEFT < 20min
```

**B · El lado que CALLA (vault al día)**

```
setup/telegram-bridge/vault-sync.sh --verboso ; echo "exit=$?"
```
→ `exit=0`, dice que está al día, y **cero mensajes al móvil**. Confírmalo mirando
el chat, no solo el log.

**C · El lado que HABLA (conflicto fabricado)**

⚠ **Con un fichero de usar y tirar, JAMÁS con una nota real.** Usa
`<vault>/_scratch/prueba-conflicto-20260820.md`, y bórralo en las dos puntas al
terminar. Edita la MISMA línea en la laptop (y pushea) y en la SER8 (sin
pushear). Entonces:

```
setup/telegram-bridge/vault-sync.sh --verboso ; echo "exit=$?"
git -C <vault> status
```
→ `exit=1`, llega el **🔴 al móvil**, `status` **NO** está en rebase, y el
fichero local conserva la versión del servidor. Las cuatro cosas, o no cuenta.

**Cláusula de corte: si a los 15 turnos no tienes A+B+C, para y reporta lo que
falta.** Mal instalado es peor que sin instalar.

### Al cerrar

1. Sella la cabecera del `.example`: cambia el aviso *"sin probar en campo
   todavía"* por **`PROBADO 2026-08-20 en floreano-server`** con las tres
   evidencias en una línea cada una.
2. Escribe tu nota en `sessions/`. Nada de `_PROJECT.md`.
3. **BORRA ESTE FICHERO**: `git rm _archive/PROMPT-ser8-timer-vault.md`, en el
   MISMO commit que sella el `.example`. Git conserva la historia y el criterio
   de `_archive/README.md` es explícito: *"se poda sin ceremonia cuando deja de
   servir"*. Lo durable ya vive en dos sitios que sí se quedan — la cabecera
   sellada del `.example` y tu nota de sesión —, así que no se pierde nada.
   ⚠ Si sales por la cláusula de corte **sin** A+B+C, **NO lo borres**: sigue
   sirviendo, y decir que se cumplió borrándolo es el modo de fallo obvio.
4. **Commit atómico + push explícito.** Un frente reportó 23 ficheros arreglados
   tres veces y nunca commiteó.
5. Al coordinador vuelven **≤15 líneas**.

---

## 8 · Destino de la rama

**SE INTEGRA.** Rama `ser8/timer-vault`, a `main` por `workstream-merge-gate`
(verde posterior al último commit, squash, OK humano), y **se borra tras el
squash** (`git branch -D`: tras un squash, `-d` no la reconoce).

---

## Fuera de alcance — dilo si te lo encuentras, no lo hagas

- **El timer del vault no tiene ningún arnés.** `test-unit-systemd.py` solo
  cubre `claude-telegram.service.example`. Es un hueco real y **no es tuyo hoy**.
- **Reiniciar el daemon.** El `pull` trae `tg_daemon.py` cambiado (deny de los
  `.env` de proyectos + la política de `mergepol`). El timer **no** lo necesita.
  Si crees que hay que reiniciarlo, **pregunta** — es la máquina 24/7.
