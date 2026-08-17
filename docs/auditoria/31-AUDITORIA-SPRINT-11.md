---
title: Auditoría del sprint 11 — el gate ya existe en Linux, pero el daemon no puede arrancar ahí
tags: [auditoria, sprint11, linux, telegram, seguridad, portabilidad]
created: 2026-08-17
updated: 2026-08-17
status: cerrada
type: auditoria
project: atloos
base: 30e4f2c
---

# Auditoría del sprint 11

**Veredicto: aceptado.** Las cinco entregas están, la calidad es la más alta de
la serie, y **tres de mis cinco puntos de partida eran falsos o cortos** — los
corrigió midiendo. Cero bloqueantes en lo entregado.

**Pero la respuesta a la pregunta que importa —*«¿el setup ya es funcional desde
Linux con el daemon?»*— es NO**, y no por lo que hizo el sprint 11 sino por lo
que tenía prohibido tocar. Cinco huecos, y el primero es de seguridad.

> **[R]** replicado por mí sobre `30e4f2c` desde el puente · **[AR]**
> autorreportado, no replicable desde aquí · **[H]** lo dijo el humano.

---

## 1 · Lo que repliqué y confirmo

**La base [R].** `main` = `8856a83` con el sprint 10 dentro; rama en `30e4f2c`.
`git diff 9bc278f main` vacío: partir de `main` era partir de donde mandaba el
encargo. Correcto, y bien comprobado antes de moverse.

**El cableado de hooks funciona, y con los matchers buenos [R].** Corrí
`sync-hooks.sh` contra un `HOME` de laboratorio con `~/.claude` presente:

```
  [OK] settings.json actualizado (backup en settings.json.bak)
  hooks cableados: 6
     PreToolUse   matcher= mcp__graphiti
     PreToolUse   matcher= Bash|PowerShell      ← el arreglo del sprint 7 sobrevivió
     PostToolUse  matcher= Write|Edit|MultiEdit
     Stop ×2 · PreCompact
```

**El arnés de paridad tiene la forma correcta [R].** Exit 0, y en una máquina sin
PowerShell **declara `Modo: PARCIAL` en grande** y dice qué no pudo ejercer. Es
lo contrario del arnés que finge cobertura — la enfermedad que este repo lleva
cuatro sprints persiguiendo.

**`setup/scripts/py` está limpio [R].** Shebang de bash, **0 CR en el blob**, y
`.gitattributes:56` con una regla explícita para el fichero sin extensión. Vio el
agujero de la política por extensión y lo cerró en el mismo commit.

**Los tres documentos existen**: `28-INVENTARIO-PORTABILIDAD-LINUX.md`,
`29-QUE-DEL-SETUP-LLEGA-AL-PUENTE.md`, `30-RFD-MULTIAGENTE-EN-TELEGRAM.md`.

---

## 2 · H1 · **BLOQUEANTE** — las denegaciones de secretos fallan abiertas en Linux

Lo encontró él, no lo tocó porque se lo prohibí, y **es lo primero que hay que
arreglar**. Lo reproduje generando la regla con el código real:

```
$ python3 -c "…el mismo bucle de tg_daemon.py…"
Read(/home/floreano/.ssh\**),Read(/home/floreano/.aws\**),
Read(/home/floreano/.gnupg\**),Read(/home/floreano/.config/gh\**)

  la ruta real a proteger:  /home/floreano/.ssh/id_ed25519
  el patrón generado:       Read(/home/floreano/.ssh\**)
```

**La barra invertida está escrita a mano** (`f"Read({d}\\**)"`). En Linux el
separador es `/`, así que **ese patrón no casa con nada** y la denegación no
deniega. Lo mismo en la segunda barrera del modo escritura de T2:
`Write({repo}\\**),Edit({repo}\\**)`.

> **Arrancar el daemon hoy en la SER8 significa un bot sin protección de secretos
> y sin barrera de escritura sobre el repo.** No falla ruidosamente: falla
> abierto y en silencio, y se activa **el día del despliegue**, no antes.

Es el mismo modo de fallo que el CRLF del sprint 9 —inerte en Windows, letal al
cruzar de plataforma— pero esta vez en la capa de permisos.

---

## 3 · H2 · `sync-hooks.sh` sale **0** sin hacer nada en una máquina virgen

Su demo en la SER8 es real y la creo. **Pero no cubre el camino de una máquina
nueva**, que es justo el que va a recorrer la SER8 desde cero. Medido por mí, dos
corridas idénticas salvo por la existencia del directorio:

| `HOME` de laboratorio | Salida | Hooks | Exit |
|---|---|---:|---:|
| **sin `~/.claude`** | `[WARN] no se encontró ningún config dir; nada que hacer` | **0** | **0** |
| con `~/.claude` | `[OK] settings.json actualizado` | 6 | 0 |

**En la secuencia real —`setup-new-machine.sh` en una máquina donde Claude Code
todavía no ha creado su config— el instalador reporta éxito y deja la máquina sin
capa 3.** Y el `setup-new-machine.sh` no distingue: para él exit 0 es exit 0.

> Ley uno de la casa, aplicada al propio instalador: **el código de salida no es
> el estado.** Aquí el script *es* quien establece el estado, y devuelve éxito
> habiendo hecho nada.

El arreglo es barato y hay dos formas defendibles —salir ≠ 0, o crear el
directorio— pero **la que no vale es la de hoy**.

---

## 4 · H3 · El daemon **no puede arrancar** en la SER8 — y faltan tres piezas, no una

Esta es la respuesta directa a la pregunta. Ninguna es culpa del sprint 11:

**a) No hay unit de systemd.** `setup/telegram-bridge/README.md:193`, literal:
*«El arranque 24/7 con `systemd` llega cuando exista la mini PC — no lo montes
aquí.»* **La mini PC ya existe.** No hay ningún `.service` en el repo [R].

**b) No hay `requirements.txt`, y el puente tiene dependencia externa [R].**
`tg_daemon.py:39` hace `from telegram import (BotCommand, InlineKeyboardButton,
…)` — **`python-telegram-bot`**, que no es stdlib. En Ubuntu 24.04 un
`pip install` pelado **falla** por PEP 668 (`externally-managed-environment`):
hace falta un venv o `--break-system-packages`, y el manual no lo dice.

**c) `projects.json` es de Windows por diseño [R].** El ejemplo trae
`"path": "C:\\Users\\TU_USUARIO\\…"` y `"test": "py -m pytest -q"`. Ese `test` no
arranca en Linux porque `gitops` lo ejecuta con argv **sin shell**, y `py` no
existe. Sin `test` válido, **`/merge` queda bloqueado por diseño** — el bot no
podrá integrar nada.

---

## 5 · H4 · El matiz del perfil del bot — su frase era más absoluta que el código

Dice el reporte: *«El bot corre con 0 de 6 hooks.»* **Es cierto a medias, y la
versión exacta es más interesante.**

`tg_daemon.py:146` → `BOT_PROFILE_DIR = ""    # vacío = config normal`, y solo en
`:1250` se exporta `CLAUDE_CONFIG_DIR` **si** ese valor está puesto. Es decir:

- **Sin perfil de bot** → usa `~/.claude`, la que `sync-hooks` sí cablea → **con
  hooks**.
- **Con perfil de bot** (la optimización de T3, la que ahorra tokens) →
  `CLAUDE_CONFIG_DIR` apunta a un directorio que `sync-hooks` no toca → **sin
  ninguno de los seis**.

> **Encender el ahorro de tokens apaga la capa de seguridad, en silencio.** Esa
> es la frase, y es peor que «el bot no tiene hooks»: es que **la configuración
> recomendada** es la desprotegida, y nada avisa al cambiar.

Su hallazgo es bueno y la consecuencia la clavó (*«el camino barato es el
desprotegido»*). Solo el enunciado necesitaba el condicional.

---

## 6 · H5 · La SER8 nace condenada a 21/22

Su punto 4 de «fallos del entorno» es correcto y **el defecto es mío**:
`test-suelo-python.py` exige un **3.10 real** para compilar, y Ubuntu 24.04 trae
**3.12**. En la máquina de destino ese arnés **no puede dar verde nunca**.

Eso no es un rojo cosmético: **una suite que nunca está verde deja de leerse**, y
el día que se ponga roja de verdad nadie lo notará. Hay dos salidas defendibles y
hay que elegir una:

- el manual instala un 3.10 (deadsnakes) en la SER8, o
- el arnés admite una **exención por máquina, declarada y con fecha** — nunca un
  `skip` genérico, que en dos sprints se vuelve costumbre.

---

## 7 · Lo que concedo: tres de mis cinco puntos estaban mal

**1 · «`py` en ~10 ficheros» — falso.** Son **~45 sitios en 44 ficheros**. Mi
grep usó un patrón estrecho y me quedé con la primera pantalla. Él midió.

**2 · «Los tres `%LOCALAPPDATA%` gobiernan la raíz de worktrees» — falso.**
Gobiernan **tres raíces distintas** (worktrees, `.env`, perfil del bot) y **las
tres tienen fallback Unix escrito a mano**: la clase entera da **cero roturas**.
Lo di por roto leyendo el nombre de la variable, no el código.

**3 · «La contención de verdad en la SER8 es la RAM» — ya no.** Con 56 GB midió
**~50,8 GiB visibles** y **~39 disponibles para frentes**: caben ~9 por memoria.
Mi premisa cayó al recalcularla, que era justo lo que le pedí. Y hace bien en
avisar de que **si arbitro leyendo la frase de mi encargo, arbitro sobre un
cuello que ya no existe**.

**Y una ironía que me toca.** Su punto 5 dice que en la SER8 el fichero quedó
como `config.txt`. Es exactamente la trampa de la que le avisé… **después** de
que la pisara. El aviso llegó por chat y **no está en el manual**, que es donde
habría servido. Quinto hueco conocido del doc 23.

---

## 8 · Lo que valoro, y no es cortesía

**Integró el sprint 10 por el gate antes de empezar**, con los siete pasos y el
OK humano, en vez de trabajar sobre una rama sin integrar como venía pasando
desde el sprint 7. Eso solo ya desatasca el tablero.

**La decisión de `py` está resuelta, no elegida.** Medir que en Windows
`command -v python3` **dice que sí y miente** (alias del Store) es exactamente el
tipo de comprobación que evita un arreglo que rompe el otro lado. Y dejar
`GATE_TEST_CMD` intacto argumentando `shell=True` en `cmd.exe` es la contención
correcta.

**El mea culpa es el mejor de la serie**: sustituyó en bloque antes de mirar el
alcance, tocó el daemon que tenía prohibido, lo cazó revisando el diff y lo
revirtió. Y **declaró la deuda que no cerró** (los dos envoltorios comparten la
lista, no la implementación) en vez de dejarla implícita.

---

## 9 · Qué falta para que el setup sea funcional en Linux con el daemon

En orden de ejecución, no de gravedad:

| # | Qué | Por qué va ahí |
|---|---|---|
| **1** | **Los dos separadores `\` del daemon** | Seguridad. Sin esto, desplegar es abrir los secretos |
| **2** | **Unit de systemd para el daemon** | Hoy no hay forma de que arranque solo |
| **3** | **`requirements.txt` + venv** (PEP 668) | `python-telegram-bot` no está y `pip` pelado falla |
| **4** | **`projects.json` en formato Linux** | Sin `test` válido, `/merge` queda bloqueado |
| **5** | **`sync-hooks.sh` que no mienta en máquina virgen** | Exit 0 con cero hooks |
| **6** | **El perfil del bot, con hooks** | Ahorrar tokens no puede apagar la capa 3 |
| **7** | **Los 26 `py` del daemon y su `.env`** | Deuda que él declaró y no tocó |
| **8** | **La suite verde en la SER8** | O 3.10, o exención declarada con fecha |
| **9** | **`.claude/settings.json:51`**, allowlist muerta | Él la vio y no la borró: era diagnóstico |

⚠ **Y una que no está en su lista y sale de la suya**: el daemon cumple **5 de 8**
criterios del gate. Le faltan el reloj y los tests que el implementador no
escribió, y **los dos verdes falsos de campo (117 s y 146 s) habrían pasado por
su `/merge`**. Antes de dejarlo integrar solo en una máquina 24/7, eso se cierra
o se declara aceptado por escrito. Es tu firma.

---

**Escrito por el auditor externo desde el puente, sobre `30e4f2c`.** Fichero
nuevo en `docs/auditoria/`, **sin commitear**.
