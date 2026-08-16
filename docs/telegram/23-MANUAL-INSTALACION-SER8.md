---
title: Manual de instalación del servidor 24/7 — Beelink SER8 con Ubuntu Server 24.04 LTS
tags: [servidor, telegram, linux, manual, ser8]
created: 2026-08-13
updated: 2026-08-13
status: activo
type: manual
project: atloos
maquina: Beelink SER8 · Ryzen 7 8845HS · 1×24 GB DDR5-5600 (una ranura libre)
---

# Manual de instalación del SER8 — de la caja al servidor 24/7

**Para alguien que no ha instalado Linux nunca.** Cada sección dice qué vas a
hacer, por qué, los comandos exactos, y **qué ver en pantalla para saber que
salió bien**. Si algo no coincide con lo que aquí dice, para y mira la Parte 11
antes de seguir.

Las tres decisiones ya tomadas:

| | |
|---|---|
| **Windows** | se borra entero; el disco completo para Linux |
| **Sistema** | **Ubuntu Server 24.04.4 LTS** (Noble Numbat), soporte hasta abril 2029 |
| **Escritorio** | ninguno. Se administra por SSH desde la laptop |

> **Por qué Server y no Desktop**: un escritorio gráfico se come 1,5-2 GB de RAM
> de forma permanente, y en tu presupuesto de 32 GB con reserva para staging eso
> es dinero. Además añade una superficie de fallo que no necesitas en una
> máquina que va a estar encendida a las 4 de la mañana sin nadie mirando.

> **Por qué 24.04 y no la 26.04, que ya salió**: la 26.04 lleva cuatro meses en
> la calle. Cuando algo falle —y va a fallar— vas a buscar el error en Google.
> Con la 24.04 casi todo lo que encuentres va a coincidir con lo que tienes
> delante. Esa es la ventaja real en una primera instalación, y vale más que dos
> años extra de soporte. En 2029 reinstalas, y para entonces ya sabrás hacerlo.

---

## Parte 0 · Lo que necesitas tener a mano antes de empezar

**Físico:**

- El SER8, su fuente y el cable de corriente.
- **Una memoria USB de 8 GB o más.** Se borra entera, así que que no tenga nada.
- **Un monitor y un cable HDMI** (el SER8 tiene HDMI 2.1 y dos DisplayPort).
  Solo hace falta para la instalación; después se desconecta y no vuelve.
- **Un teclado USB.** Ratón no hace falta: el instalador de Server es de texto.
- **Un cable de red** del router al SER8. El SER8 tiene 2,5 GbE.
  **No uses WiFi para esto.** Un servidor 24/7 va por cable: es más estable, más
  rápido y te evita configurar la WiFi a ciegas desde una consola de texto.

**En la laptop (Windows):**

- Navegador para descargar la ISO.
- **Rufus** — para grabar la ISO al USB. Se descarga de <https://rufus.ie>.
- PowerShell (ya lo tienes).

**Tiempo:** entre 60 y 90 minutos la primera vez, sin prisa. La instalación en
sí son 15 minutos; el resto es configuración y comprobaciones.

**Reserva un rato en el que no te corra prisa.** La única parte irreversible es
el borrado del disco, y llega en la Parte 4.

> ### ⚠ ANTES DE EMPEZAR: la máquina llegó con 24 GB, no con 32
>
> Llegó **un solo módulo de 24 GB** (Micron `CT24G56C46S5.C8C`) y una ranura
> libre. Eso significa dos cosas, y las dos van antes de esta guía:
>
> 1. **No abras la máquina ni le cambies el sistema operativo hasta haber
>    documentado el faltante y abierto la reclamación al vendedor.** Instalar
>    Linux borra Windows, y con él las capturas que prueban lo que te
>    entregaron. Está todo en `24-RAM-DEL-SER8-QUE-COMPRAR.md`.
> 2. **Con un solo módulo la memoria va en canal simple**, a la mitad de ancho
>    de banda. Si vas a meter el segundo módulo —y deberías—, **hazlo antes de
>    instalar**: así corres MemTest86 una sola vez y no reinstalas nada.
>
> **Orden correcto:** reclamar → comprar el módulo → instalarlo → MemTest86 →
> y entonces sí, esta guía desde la Parte 1.

---

## Parte 1 · Descargar Ubuntu y comprobar que llegó entero

### 1.1 Descargar la ISO

Abre <https://releases.ubuntu.com/noble/> y descarga:

```
ubuntu-24.04.4-live-server-amd64.iso
```

Son unos 3 GB. Guárdalo en `Descargas`.

> ⚠ **Que sea `live-server`, no `desktop`.** Son dos ficheros distintos y solo
> uno es el que quieres.

### 1.2 Comprobar el hash — y sí, hay que hacerlo

Una descarga cortada produce un USB que arranca a medias y falla en mitad de la
instalación con un error que no dice nada. Dos minutos aquí te ahorran una hora
de confusión.

Abre **PowerShell** y ejecuta:

```powershell
cd ~\Downloads
Get-FileHash .\ubuntu-24.04.4-live-server-amd64.iso -Algorithm SHA256 | Format-List
```

Tarda medio minuto. Te da una línea `Hash : ` con 64 caracteres.

Ahora abre <https://releases.ubuntu.com/noble/SHA256SUMS> en el navegador. Busca
la línea que termina en `ubuntu-24.04.4-live-server-amd64.iso` y compara.

**Tienen que ser idénticos.** No hace falta leer los 64 caracteres: compara los
primeros seis y los últimos seis. Si no coinciden, borra el fichero y descarga
otra vez.

### 1.3 Grabar el USB con Rufus

1. Enchufa el USB.
2. Abre Rufus (no necesita instalación).
3. **Dispositivo**: elige tu USB. **Míralo dos veces** — Rufus borra lo que
   selecciones sin preguntar mucho.
4. **Elección de arranque** → `SELECCIONAR` → busca la ISO.
5. **Todo lo demás, déjalo como está.** Rufus detecta solo que es GPT/UEFI.
6. `EMPEZAR`. Si pregunta entre «modo Imagen ISO» y «modo Imagen DD», elige
   **Imagen ISO** (la opción recomendada, que viene marcada).
7. Acepta el aviso de que se borrará todo.

Termina en 3-5 minutos. Cuando la barra diga `LISTO`, cierra Rufus y **expulsa
el USB** con el icono de la bandeja antes de sacarlo.

---

## Parte 2 · La BIOS del SER8

Aquí es donde se decide que la máquina arranque del USB y —lo que más importa
para un servidor— que **vuelva sola después de un apagón**.

### 2.1 Entrar en la BIOS

1. Con el SER8 **apagado**, conecta el monitor por HDMI, el teclado USB y el
   cable de red. **Aún no metas el USB de Ubuntu.**
2. Enchufa la corriente y pulsa el botón de encendido.
3. **En cuanto pulses, empieza a dar toques a la tecla `Supr` / `Delete`**, una
   vez cada medio segundo. No la mantengas pulsada: toques.

Deberías ver una pantalla azul y gris con pestañas arriba (`Main`, `Advanced`,
`Chipset`, `Security`, `Boot`, `Save & Exit`). Eso es la BIOS (AMI Aptio).

> **Si se salta a Windows sin parar:** apaga del todo (mantén el botón 5
> segundos), y vuelve a intentarlo — pero esta vez **usa un puerto USB trasero**
> para el teclado y empieza a tocar `Supr` **antes** de pulsar encender. El
> teclado a veces tarda en despertar y se pierde la ventana. La otra tecla útil
> es **`F7`**, que abre directamente el menú de arranque.

Te mueves con las **flechas**, entras con **Enter**, vuelves con **Esc**.
El ratón no hace nada aquí.

### 2.2 Los tres ajustes que hay que tocar

**a) Desactivar Secure Boot.**
Pestaña `Security` (o `Boot`, según versión) → `Secure Boot` → ponlo en
**`Disabled`**.

> Ubuntu **sí** arranca con Secure Boot activado, pero desactivarlo elimina de
> golpe una familia entera de fallos raros durante la instalación y con drivers
> de terceros. En una máquina que no va a viajar y está en tu casa, no pierdes
> nada relevante.

**b) Encendido automático tras un corte de luz. Este es EL ajuste del servidor.**

Busca en la pestaña `Chipset` o en `Advanced` una opción llamada alguna de
estas —el nombre cambia según la versión de BIOS—:

- `Restore AC Power Loss`
- `State After G3`
- `AC Back` / `After Power Failure` / `Power On After Power Fail`

Ponla en **`Power On`** (o `Always On` / `Last State`, lo que ofrezca).

> ⚠ **No pude verificar la ruta exacta del menú para tu versión concreta de
> BIOS**, así que puede estar en `Chipset → South Bridge` o en
> `Advanced → ACPI Settings`. Recorre las dos pestañas leyendo los nombres; la
> opción existe en el SER8, está confirmada. Si no la encuentras, sigue adelante
> y vuelve luego: **la comprobación real es la de la Parte 10.4**, tirar del
> cable y ver si vuelve sola.
>
> Sin esto, un apagón de dos segundos deja tu servidor apagado hasta que alguien
> vaya físicamente a pulsar el botón. Es la diferencia entre un servidor y un
> ordenador que suele estar encendido.

**c) Orden de arranque.**
Pestaña `Boot` → pon el USB el primero. Si no aparece todavía, no importa: lo
haremos con `F7` en la Parte 3.

### 2.3 Guardar

`Save & Exit` → **`Save Changes and Reset`** → `Yes`. La máquina se reinicia.

> **Lo que NO vas a tocar:** el modo de 65 W, las curvas de ventilador y
> cualquier cosa con «overclock». El SER8 viene a 54 W sostenidos y con eso le
> sobra para lo que va a hacer. **Y no actualices la BIOS** — una actualización
> de BIOS que sale mal deja la máquina muerta, y no tienes ningún problema que
> resolver con ella.

---

## Parte 3 · Arrancar desde el USB

1. Con la máquina apagada, **mete el USB de Ubuntu** (mejor en un puerto USB
   3.0, los azules de atrás).
2. Enciende y da toques a **`F7`**.
3. Sale una lista corta de dispositivos. Elige la entrada que lleve `UEFI` y el
   nombre de tu USB (por ejemplo `UEFI: SanDisk ...`). **Si hay dos entradas
   iguales y solo una dice `UEFI`, elige la que dice `UEFI`.**
4. Enter.

Verás una pantalla negra con texto blanco corriendo, y luego un menú morado
donde pone `Try or Install Ubuntu Server`. Déjalo o pulsa Enter.

**Un minuto de texto pasando.** Es normal. Si aparece algún mensaje suelto de
`usb6-port1: Cannot enable`, ignóralo: es un aviso cosmético conocido del SER8 y
no afecta a nada.

---

## Parte 4 · El instalador, pantalla por pantalla

El instalador es de texto. **Te mueves con flechas, `Tab` salta entre campos y
botones, `Enter` acepta, `Espacio` marca casillas.** Abajo siempre hay un botón
`[ Done ]`.

### 4.1 Idioma

`English` — déjalo. **Sí, en inglés.** Los mensajes de error en inglés son los
que vas a poder buscar en Google y encontrar respuesta. El teclado sí lo pondrás
en español en el paso siguiente.

### 4.2 Actualizar el instalador

Si ofrece `Update to the new installer`, elige **`Continue without updating`**.
Menos piezas móviles.

### 4.3 Teclado

`Layout: Spanish` · `Variant: Spanish`. Baja al campo y usa las flechas.

> **Compruébalo ahí mismo**: hay un campo de prueba en algunas versiones. Si no,
> recuerda que en teclado español la `ñ` está a la derecha de la `l` y el guion
> `-` está donde el signo de interrogación en el americano. Lo vas a necesitar
> al escribir la contraseña.

### 4.4 Tipo de instalación

**`Ubuntu Server`** — la primera opción, no la `(minimized)`.

> La minimizada quita herramientas de diagnóstico que vas a echar de menos
> exactamente el día que algo falle.

### 4.5 Red

Debería aparecer tu interfaz de cable (algo como `enp1s0` o `eno1`) ya con una
**IP asignada por DHCP** — algo tipo `192.168.1.47/24`.

- **Si ves una IP: perfecto.** `Done`. La IP fija la ponemos después, con
  calma, desde SSH.
- **Si no ves IP**, comprueba el cable y que el router esté encendido. Sin red
  la instalación puede seguir, pero te complica todo lo demás.

**Apunta esa IP en un papel.** La vas a necesitar en la Parte 5.

### 4.6 Proxy

Vacío. `Done`.

### 4.7 Mirror

Déjalo como venga. `Done`.

### 4.8 Disco — **esta es la pantalla irreversible**

Elige **`Use an entire disk`**.

Abajo, en el desplegable, aparece tu NVMe (algo como
`nvme0n1  local disk  953.869G`). Si el SER8 tiene un solo disco, solo hay uno.

- **NO marques** `Set up this disk as an LVM group`. Para un servidor de una
  sola máquina, LVM añade una capa que tendrías que entender el día que algo
  vaya mal, y no te da nada a cambio.
- **NO marques** el cifrado (LUKS). Un disco cifrado **pide la contraseña por
  teclado en cada arranque**, y tu servidor tiene que arrancar solo después de
  un apagón, sin nadie delante. Son incompatibles.

`Done`. Sale el resumen del particionado. `Done` otra vez.

> ### ⚠ Aquí sale el aviso de destrucción
>
> ```
> Confirm destructive action
> Selecting Continue below will begin the installation process and
> result in the loss of data on the disks selected to be formatted.
> ```
>
> **`Continue` borra Windows y todo lo que haya en ese disco, para siempre.**
> Es el punto de no retorno. Si tenías algo en la máquina que quieras conservar,
> este es el último momento. Viene de fábrica, así que casi seguro no hay nada.
>
> Cuando estés listo: `Continue`.

### 4.9 Tu usuario

```
Your name:              Jose Floreano
Your servers name:      atloos-server
Pick a username:        jose
Choose a password:      (una buena, y apúntala)
Confirm your password:  (otra vez)
```

- **`Your servers name`** es el nombre de la máquina en la red. En minúsculas y
  sin espacios. `atloos-server` está bien.
- **El username en minúsculas y sin acentos.** Va a ser tu carpeta
  (`/home/jose`) y parte de cada comando SSH.
- **La contraseña no se ve al escribirla**, ni con asteriscos. La pantalla no se
  mueve. **Es normal, sigue escribiendo.**
- **Apúntala en un sitio seguro ahora mismo.** Sin ella no puedes hacer nada
  como administrador, y no hay «he olvidado mi contraseña».

### 4.10 Ubuntu Pro

`Skip for now`. Es gratis hasta 5 máquinas y da parches extra, pero añade una
cuenta y una capa que no necesitas hoy. Se puede activar más adelante.

### 4.11 SSH — **no te saltes esta**

```
[X] Install OpenSSH server
```

**Márcalo con `Espacio`.** Sin esto no puedes entrar desde la laptop y tendrías
que reinstalar o pelearte con el monitor.

`Import SSH identity` → `No`. Las claves las ponemos después.

### 4.12 Snaps

**No marques ninguno.** Docker lo instalaremos por su repositorio oficial, que
es mejor que el snap. `Done`.

### 4.13 A esperar

Empieza la instalación. Tarda entre 5 y 20 minutos según lo que tarde en
descargar actualizaciones. Verás un log corriendo.

Cuando termine, el botón de abajo cambia a **`Reboot Now`**. Púlsalo.

**Cuando te diga `Please remove the installation medium, then press ENTER`:
saca el USB y pulsa Enter.**

---

## Parte 5 · Primer arranque y entrar desde la laptop

### 5.1 El primer arranque

La máquina arranca y acaba mostrando algo así:

```
atloos-server login:
```

Escribe tu usuario, Enter, la contraseña (no se ve), Enter.

Ya estás dentro. El prompt queda así:

```
jose@atloos-server:~$
```

### 5.2 Averiguar la IP

```bash
ip -4 addr show scope global
```

Busca la línea `inet` — algo como `inet 192.168.1.47/24`. **Esa es la IP.**

### 5.3 Entrar por SSH desde la laptop

Ya puedes desconectar el monitor y el teclado del SER8, y dejarlo con solo la
corriente y el cable de red.

En la laptop, abre **PowerShell**:

```powershell
ssh jose@192.168.1.47
```

(con tu usuario y tu IP)

La primera vez pregunta:

```
The authenticity of host '192.168.1.47' can't be established.
ED25519 key fingerprint is SHA256:xxxxx...
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Escribe **`yes`** completo y Enter. Luego la contraseña.

**Si ves el prompt `jose@atloos-server:~$` en la ventana de PowerShell, has
terminado la parte difícil.** Todo lo que queda son comandos que copias y pegas.

> **Truco**: en PowerShell se pega con **botón derecho del ratón**, no con
> Ctrl+V.

### 5.4 Entrar sin contraseña, con clave

Escribir la contraseña cada vez es molesto y, peor, te empuja a poner una fácil.
Las claves SSH lo arreglan.

**En la laptop** (PowerShell), si no tienes clave ya:

```powershell
ssh-keygen -t ed25519 -C "laptop-floreano"
```

Enter tres veces (acepta la ruta por defecto y deja la passphrase vacía, o
ponla si prefieres).

Ahora cópiala al servidor. Windows no trae `ssh-copy-id`, así que:

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh jose@192.168.1.47 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Te pide la contraseña **una última vez**.

**Compruébalo**: cierra la sesión (`exit`) y vuelve a entrar:

```powershell
ssh jose@192.168.1.47
```

**Si entra sin pedir contraseña, funcionó.**

### 5.5 Cerrar la puerta de la contraseña

⚠ **Solo haz esto cuando el paso 5.4 funcione**, o te quedas fuera y tienes que
volver a conectar el monitor.

```bash
sudo nano /etc/ssh/sshd_config.d/99-atloos.conf
```

`nano` es el editor. Pega esto (botón derecho):

```
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
```

Guarda con **`Ctrl+O`**, Enter, y sal con **`Ctrl+X`**.

```bash
sudo systemctl restart ssh
```

**Sin cerrar la ventana actual**, abre **otra** PowerShell y entra otra vez. Si
entra, perfecto. Si no, todavía tienes la primera ventana abierta para
arreglarlo — por eso no se cierra.

---

## Parte 6 · IP fija

Si la IP cambia, tus scripts, tus túneles y tus atajos dejan de funcionar un
martes por la mañana sin explicación.

**Hay dos formas y la primera es mejor:**

### 6.1 Opción A — reserva en el router (recomendada)

Entra en tu router (normalmente `192.168.1.1` en el navegador), busca
`DHCP` → `Reserva de direcciones` / `Static DHCP` / `Address Reservation`, y ata
la MAC del SER8 a la IP que ya tiene.

La MAC la ves con:

```bash
ip link show
```

Es el `link/ether xx:xx:xx:xx:xx:xx` de tu interfaz de cable.

**Por qué es mejor**: el router sigue siendo la única fuente de verdad de quién
tiene qué IP. No hay forma de crear un conflicto.

### 6.2 Opción B — fijarla en el servidor

Si tu router no lo permite:

```bash
sudo nano /etc/netplan/50-cloud-init.yaml
```

Déjalo así, **cambiando `enp1s0` por tu interfaz real y las IPs por las tuyas**:

```yaml
network:
  version: 2
  ethernets:
    enp1s0:
      dhcp4: false
      addresses:
        - 192.168.1.50/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [1.1.1.1, 8.8.8.8]
```

> ⚠ **YAML es sensible a la indentación.** Solo espacios, nunca tabuladores, y
> los niveles como están arriba. Un espacio de más y no arranca la red.

Compruébalo antes de aplicarlo de verdad:

```bash
sudo netplan try
```

Ese comando aplica los cambios y **los revierte solos en 120 segundos** si no
confirmas. Es la red de seguridad: si te equivocas y pierdes la conexión, en dos
minutos vuelve como estaba. Si todo va bien, pulsa Enter para confirmar.

Después:

```bash
sudo netplan apply
```

**Elige una IP fuera del rango que reparte el DHCP del router** (mira en el
router qué rango usa; si reparte de .100 a .200, usa .50).

---

## Parte 7 · Convertirlo en un servidor de verdad

A partir de aquí todo es copiar y pegar en la sesión SSH.

### 7.1 Actualizar

```bash
sudo apt update && sudo apt upgrade -y
```

La primera vez baja bastante. Si al final dice que hace falta reiniciar:

```bash
sudo reboot
```

Espera un minuto y vuelve a entrar por SSH.

### 7.2 Zona horaria y reloj

```bash
sudo timedatectl set-timezone America/Mexico_City
timedatectl
```

Debe decir `Time zone: America/Mexico_City` y
`System clock synchronized: yes`.

> **Por qué importa**: todos los logs, los cron, y las marcas de tiempo de tus
> reportes de feedback llevan esta hora. Si está mal, cada investigación
> posterior empieza con una resta mental.

### 7.3 Cortafuegos

```bash
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status verbose
```

Cuando pregunte, `y`. **Fíjate en el orden**: primero se permite SSH, luego se
enciende. Al revés te quedas fuera.

`ufw status` debe mostrar `Status: active` y una regla para el 22.

### 7.4 Actualizaciones de seguridad automáticas

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Di que sí. Esto instala solo los parches de **seguridad**, no versiones nuevas
de todo. En una máquina expuesta 24/7 es lo mínimo.

### 7.5 fail2ban

```bash
sudo apt install -y fail2ban
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

Banea IPs que fallen el login repetidamente. Con las contraseñas ya
desactivadas el riesgo es bajo, pero es gratis.

### 7.6 Que los logs no se coman el disco

```bash
sudo nano /etc/systemd/journald.conf.d/limite.conf
```

```
[Journal]
SystemMaxUse=500M
MaxRetentionSec=1month
```

```bash
sudo systemctl restart systemd-journald
```

> Sin esto, un servicio que falla en bucle escribe gigas de log durante un fin
> de semana y te quedas sin disco. Es un modo de fallo aburrido y clásico.

### 7.7 Swap

Con 24 GB de RAM y agentes que tienen fugas de memoria conocidas, **esto no es
opcional como lo sería con 64 GB**. La swap evita que el kernel mate procesos al
azar cuando algo se dispara.

```bash
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Y que solo se use cuando de verdad haga falta:

```bash
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swap.conf
sudo sysctl -p /etc/sysctl.d/99-swap.conf
```

Comprueba:

```bash
free -h
```

Debe salir una línea `Swap:` con `8,0Gi`.

### 7.8 Herramientas básicas

```bash
sudo apt install -y git curl wget htop ncdu tmux rsync build-essential ca-certificates gnupg
```

- **`htop`** — ver qué está consumiendo RAM y CPU. Se sale con `q`.
- **`ncdu`** — ver qué carpeta se está comiendo el disco.
- **`tmux`** — **este te va a salvar**: deja procesos corriendo aunque cierres
  la sesión SSH. Ver Parte 8.5.

---

## Parte 8 · Lo específico de atloos

### 8.1 Git

```bash
git config --global user.name "Jose Floreano"
git config --global user.email "jlfloreano@hotmail.com"
git config --global init.defaultBranch main
```

### 8.1b Cómo llega el repo a esta máquina — **`git clone`, NO la carpeta**

> ⚠ **Este paso faltaba en el manual** y es el que decide si los scripts
> arrancan. Lo cazó la auditoría 27.

```bash
cd ~
git clone <url-del-remoto-privado> Atloos
cd Atloos
```

**NO copies ni sincronices la carpeta de OneDrive.** Entre las dos laptops el
repo viaja hoy por OneDrive y funciona porque las dos son Windows. Aquí no:

- Los `.sh` de OneDrive llegan con **CRLF**, y `bash` muere con
  `$'\r': command not found` — un error que **no menciona el fin de línea**.
  Reproducido sobre el commit `e2ec4d5`: la misma suite daba **18/18 en Windows
  y 17/18 en Linux**, y el que caía era el hook `post-commit`.
- Afecta a `setup-new-machine.sh`, `sync-skills.sh` y
  `setup/hooks/git-post-commit-graph-report.sh` — o sea, **al primer minuto de
  la instalación**.
- Un clone no tiene el problema: el repo lleva `.gitattributes` desde el sprint
  9 (`* text=auto`, `*.sh text eol=lf`) y git escribe los ficheros con el fin de
  línea correcto para esta máquina.

**Compruébalo antes de seguir**, que cuesta un segundo:

```bash
py setup/scripts/tests/test-eol-blobs.py; echo "exit=$?"   # [repo]
bash setup/hooks/git-post-commit-graph-report.sh; echo "exit=$?"
```

Los dos tienen que salir con `exit=0`. Si el segundo dice `command not found`
de algo raro, **copiaste la carpeta en vez de clonarla**: borra y clona.

⚠ Y lo que **sí** hay que traer a mano, porque git no lo versiona:
`setup/telegram-bridge/.env` y `projects.json`. **Cópialos, no los enlaces**
(`workstream-dispatch/references/higiene-de-shell.md` §1).

### 8.2 Claude Code — por apt, no por curl

La documentación ofrece dos vías. **Para este servidor, apt es la correcta.**

```bash
sudo install -d -m 0755 /etc/apt/keyrings
sudo curl -fsSL https://downloads.claude.ai/keys/claude-code.asc \
  -o /etc/apt/keyrings/claude-code.asc
gpg --show-keys /etc/apt/keyrings/claude-code.asc
```

**Comprueba que la huella sea exactamente:**

```
31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE
```

Si no coincide, para y no instales nada. Si coincide:

```bash
echo "deb [signed-by=/etc/apt/keyrings/claude-code.asc] https://downloads.claude.ai/claude-code/apt/stable stable main" \
  | sudo tee /etc/apt/sources.list.d/claude-code.list
sudo apt update
sudo apt install -y claude-code
claude --version
```

> **Por qué apt y no `curl | bash`**: la instalación nativa **se actualiza sola
> en segundo plano**. En tu laptop eso es cómodo; en un servidor que corre
> agentes desatendidos significa que la versión puede cambiar debajo de un
> proceso en marcha, sin que quede rastro de cuándo. Con apt la versión solo
> cambia cuando tú corres `sudo apt upgrade`, y queda en el log. Además usas el
> canal `stable`, que va una semana por detrás y **se salta las versiones con
> regresiones graves** — exactamente lo que quieres en la máquina que no
> vigilas.
>
> Y esto te da de paso el campo `setup_sha` que le falta a tus reportes de
> feedback: en esta máquina la versión es una respuesta, no una suposición.

**Autenticar** — necesita cuenta Pro, Max, Team o Enterprise:

```bash
claude
```

Te da una URL. **Cópiala y ábrela en el navegador de la laptop**, autoriza, y
pega el código de vuelta en la terminal. Sal con `/exit`.

### 8.3 Las mitigaciones de la fuga de memoria

Esto es lo que investigamos para el dimensionado. Va aquí porque es el momento
en que aplica.

```bash
sudo nano /etc/environment.d/99-claude.conf
```

```
CLAUDE_CODE_RESUME_INTERRUPTED_TURN=1
CLAUDE_CODE_RETRY_WATCHDOG=1
```

> ⚠ **Aquí había un `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=3`. Sale, y no
> vuelve.** Se quita por tres razones, y se escriben para que no se re-añada:
>
> 1. **Es un cap arbitrado en contra**, escondido en un fichero de entorno —
>    el sitio que nadie relee. **[H]** *«lo que quiero es ir logrando ir
>    aumentando la capacidad de subagentes»* (2026-08-16).
> 2. **Los dos manuales decían números distintos**: este `=3` y
>    `20-DIMENSIONADO…` un `=6`. Dos ajustes del mismo servidor, sin árbitro.
> 3. **El 3 desciende del ×2,05**, que se quedó **sin explicación** (auditoría
>    27 §7): una medición autorreportada, de la suite de **otro proyecto**, sin
>    máquina anotada. **Y ninguno de los dos números se midió en esta máquina.**
>
> El defecto de Claude Code es **20**. Se deja el defecto.

**En su lugar, mide en ESTA máquina — un paso, la primera semana:**

```bash
# Con una jornada real corriendo, mira el pico de memoria por proceso:
systemctl --user status claude-* | grep -i memory
ps -o rss=,comm= -C node --sort=-rss | head -5      # RSS en KB
free -m
```

Con ese número —**RSS del pico real**, no una estimación— escribe el techo
**con fecha y máquina**, igual que
`setup/skills/shared/workstream-dispatch/references/medir-el-techo.md`, que es
donde vive el procedimiento y la lista de lo que invalida una medición. **No lo
repitas aquí**: enlázalo, o serán dos números otra vez.

> **Y la barrera real de un headless de 24 GB no es la CPU: es la RAM** — y
> Linux ya tiene el mecanismo, así que no hace falta poner techo a la ambición
> (RFD 26 §1.4). El límite va en la unit, **en función de la RAM instalada**:

**Y el cinturón de seguridad de verdad**, para cuando lo pongas como servicio:
en el `[Service]` de cada unidad systemd que lance un agente, pon

```ini
MemoryHigh=3G
MemoryMax=4G
OOMPolicy=kill
Restart=on-failure
RestartSec=30
StartLimitBurst=10
StartLimitIntervalSec=600
```

`MemoryHigh` **frena** el proceso (lo mete a recuperar memoria) antes de que
`MemoryMax` lo **mate**: el primero avisa, el segundo corta. `MemoryMax` hace
que una fuga mate **ese** proceso en vez de tumbar la máquina entera;
`StartLimitBurst` generoso evita que systemd se rinda y deje el servicio muerto
tras tres reinicios rápidos.

> **Esto es lo que sustituye al cap de subagentes**, y es mejor que él: falla
> cerrado contra el OOM **sin poner techo a la ambición**. Un cap dice «no
> lances más de 3» aunque quepan 6; `MemoryMax` deja lanzar los que quepan y
> mata solo al que se desmadra.

**Los números salen de la RAM instalada, no de la costumbre.** Con `T` = GB
totales, reservando ~8 GB para sistema + Docker + coordinador:

```
MemoryMax  por frente ≈ (T − 8) / frentes_previstos
MemoryHigh por frente ≈ MemoryMax × 0,75
```

| RAM instalada | 3 frentes | 5 frentes |
|---:|---:|---:|
| **24 GB** (la de compra) | `MemoryMax=5G` · `High=3G` | `MemoryMax=3G` · `High=2G` |
| 56 GB (si metes el módulo de 32) | `MemoryMax=16G` · `High=12G` | `MemoryMax=9G` · `High=7G` |

Los `3G/4G` de arriba son el valor **conservador** para arrancar con 24 GB;
súbelos con el RSS medido en la mano, no antes.

### 8.4 Docker, para el staging

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

**Cierra la sesión SSH y vuelve a entrar** para que el grupo tenga efecto. Luego:

```bash
docker run --rm hello-world
```

Si imprime `Hello from Docker!`, listo.

Y **pon un límite a los logs de Docker**, que es otra forma clásica de llenar un
disco sin enterarse:

```bash
sudo nano /etc/docker/daemon.json
```

```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
```

```bash
sudo systemctl restart docker
```

### 8.5 tmux — para que no se muera lo que dejaste corriendo

**Si lanzas algo por SSH y cierras la ventana, el proceso muere.** Con tmux, no.

```bash
tmux new -s trabajo      # crear una sesión llamada "trabajo"
# ... lanza lo que sea ...
# Ctrl+B, sueltas, y luego D   → te sales dejándolo corriendo
tmux attach -t trabajo   # volver a entrar, incluso desde otra máquina
tmux ls                  # ver qué sesiones hay
```

Apréndete solo eso: `tmux new -s`, `Ctrl+B` `D`, y `tmux attach -t`.

---

## Parte 9 · Llegar al servidor desde fuera de casa

Vas a querer entrar desde el móvil o desde otro sitio. **No abras puertos en el
router.** Es la forma más rápida de acabar en los escaneos automáticos de medio
mundo.

**Tailscale** monta una red privada entre tus dispositivos sin tocar el router:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Te da una URL, la abres en el navegador, inicias sesión, y ya. Instala Tailscale
también en la laptop y en el móvil, con la misma cuenta.

A partir de ahí entras con el nombre de la máquina desde cualquier sitio:

```bash
ssh jose@atloos-server
```

Es gratis para uso personal y hasta 100 dispositivos.

---

## Parte 10 · Las comprobaciones finales

**No des el servidor por bueno hasta pasar las cinco.** Es tu propia ley: el
reporte no es el artefacto.

### 10.1 Sobrevive a un reinicio

```bash
sudo reboot
```

Espera un minuto. Entra por SSH. **Si entra, bien.**

### 10.2 Todo lo que debe estar arriba, está arriba

```bash
systemctl is-active ssh docker fail2ban
systemctl --failed
```

Los tres deben decir `active`. `systemctl --failed` debe decir
`0 loaded units listed`.

### 10.3 Los números de la máquina

```bash
free -h                 # ¿la RAM que esperas y 8 GB de swap?
df -h /                 # ¿cuánto disco libre?
nproc                   # deben ser 16 (8 núcleos, 16 hilos)
sudo apt install -y lm-sensors && sensors
```

**Apunta estos números.** Son tu línea base: el día que la máquina vaya rara,
la pregunta es «¿comparado con qué?».

**Y comprueba los módulos y los canales de memoria:**

```bash
sudo apt install -y dmidecode
sudo dmidecode -t memory | grep -E "Size|Locator|Speed|Rank|Part Number"
```

> ⚠ **La máquina llegó con 24 GB en UN solo módulo, no con 32 GB en dos.**
> Con un módulo, la memoria trabaja en **canal simple** y el ancho de banda es
> aproximadamente la mitad. `dmidecode` te lo confirma: si solo un `Locator`
> tiene `Size`, estás en canal simple. Lo que hay que hacer con eso está en el
> documento `24-RAM-DEL-SER8-QUE-COMPRAR.md`, y **conviene resolverlo antes de
> instalar** — ver la nota de la Parte 0.

### 10.4 La prueba del apagón — la que de verdad importa

1. Con el servidor encendido y funcionando, **quita el cable de corriente**.
2. Espera diez segundos.
3. Vuelve a enchufarlo. **No toques el botón de encendido.**
4. Espera un minuto y entra por SSH.

**Si entra, tienes un servidor.** Si no arranca solo, vuelve a la Parte 2.2b: la
opción de la BIOS no quedó puesta, o está en otro sitio del menú.

> Esta prueba es la única que distingue un servidor de un ordenador que suele
> estar encendido, y es la que nadie hace.

### 10.5 Desde el móvil

Con Tailscale instalado en el móvil y una app de SSH (Termius, JuiceSSH),
conéctate. **Desde datos móviles, no desde tu WiFi** — si estás en la misma red
no has probado nada.

---

## Parte 11 · Si algo sale mal

| Síntoma | Qué pasa y qué hacer |
|---|---|
| **No entro en la BIOS con `Supr`** | El teclado despierta tarde. Apaga del todo (botón 5 s), usa un **USB trasero**, y empieza a tocar `Supr` **antes** de pulsar encender. Prueba también `F7`. |
| **El USB no aparece en `F7`** | Regrábalo con Rufus en «Imagen ISO». Prueba otro puerto (mejor un USB 3.0 trasero). Comprueba que Secure Boot está en `Disabled`. |
| **Se apaga solo al arrancar el instalador** | Es el fallo del hilo del foro de Beelink. Casi siempre es Secure Boot activo o un USB mal grabado. Si persiste: en el menú morado pulsa `e`, añade **`nomodeset`** al final de la línea que empieza por `linux`, y arranca con `Ctrl+X`. |
| **Pantalla negra tras instalar** | Es normal en servidor sin escritorio si el monitor entra en reposo. Prueba a entrar por SSH antes de dar nada por perdido. |
| **`ssh: connect to host ... Connection refused`** | El servidor está encendido pero SSH no. Conecta monitor y teclado y corre `sudo systemctl status ssh`. Si no está, no marcaste la casilla de la Parte 4.11: `sudo apt install openssh-server`. |
| **`Connection timed out`** | La IP cambió, o el cable, o el cortafuegos. Mira la lista de clientes del router para encontrarlo. |
| **`Permission denied (publickey)`** | La clave no llegó bien y ya cerraste la contraseña. Conecta monitor y teclado, y comprueba `cat ~/.ssh/authorized_keys`. |
| **Me quedé fuera del todo** | No se pierde nada: monitor + teclado + tu contraseña de la Parte 4.9, y desde ahí se arregla todo. **Por eso esa contraseña se apunta.** |
| **La red no funciona tras tocar netplan** | Si usaste `sudo netplan try`, espera 120 s y vuelve sola. Si usaste `apply`, monitor y teclado, y edita otra vez `/etc/netplan/50-cloud-init.yaml`. |
| **`sudo: command not found` o similar tras pegar** | Pegaste un comando partido. Vuelve a copiarlo entero, en una sola línea. |

---

## Apéndice · Los comandos que vas a usar cada semana

```bash
# Estado general
htop                       # qué consume qué (salir con q)
df -h                      # disco
free -h                    # RAM
systemctl --failed         # ¿algo caído?

# Actualizar
sudo apt update && sudo apt upgrade -y

# Logs
journalctl -u NOMBRE -f    # seguir el log de un servicio en vivo
journalctl -p err -b       # solo errores desde el último arranque

# Servicios
sudo systemctl status NOMBRE
sudo systemctl restart NOMBRE

# Apagar y reiniciar
sudo reboot
sudo poweroff
```

**Dos costumbres que valen más que cualquier comando:**

1. **`Tab` autocompleta.** Escribe tres letras y pulsa `Tab`. Evita más errores
   que cualquier otra cosa.
2. **Antes de pegar un comando con `sudo` que hayas sacado de internet, léelo.**
   Si no entiendes qué hace, pregunta antes de ejecutarlo.

---

## Lo que queda abierto después de esto

- **D9 · staging permanente o bajo demanda.** El SER8 tiene **un segundo slot
  M.2 libre**: es el sitio natural para los volúmenes de Docker y las bases de
  datos de staging, separados del disco del sistema. Decisión tuya.
- **D10 · `--bare`.** Aplica al arrancar los agentes, no a la instalación.
- **La RAM.** Llegó 1×24 GB con una ranura libre. Qué comprar, a qué precio y
  por qué no conviene devolver la máquina: `24-RAM-DEL-SER8-QUE-COMPRAR.md`.
  **La ranura libre es de un solo uso**: lo que metas ahí es lo que hay, porque
  ampliar después significa tirar ese módulo.
- **Copias de seguridad.** Un servidor sin copia de seguridad es un servidor que
  todavía no ha perdido nada. No entra en este manual, pero entra en pendientes.

---

## Fuentes

- [Ubuntu 24.04 LTS (Noble) — descargas y SHA256SUMS](https://releases.ubuntu.com/noble/)
- [Ciclo de vida de las versiones de Ubuntu](https://ubuntu.com/about/release-cycle)
- [Notas de la 26.04 LTS Resolute Raccoon (la descartada, para el registro)](https://documentation.ubuntu.com/release-notes/26.04/)
- [Claude Code — instalación avanzada, repositorio apt y huella de la clave](https://code.claude.com/docs/en/setup)
- [Repositorio apt de Docker — suites disponibles](https://download.docker.com/linux/ubuntu/dists/)
- [Análisis del Beelink SER8 (specs, térmicas, consumo)](https://www.notebookcheck.net/Beelink-SER8-PC-review-Mac-Mini-inspired-design-with-an-AMD-Ryzen-7-8845HS.857066.0.html)
- [Foro Beelink — teclas `Supr` (BIOS) y `F7` (arranque)](https://bbs.bee-link.com/d/9195-cannot-get-into-bios-setup-delete-or-boot-options-f7-menu)
- [Foro Beelink — apagones al instalar Linux en el SER8](https://bbs.bee-link.com/d/443-ser8-unable-to-install-linux)
- [Foro Beelink — reinicio tras corte de corriente en el SER8](https://bbs.bee-link.com/d/3644-ser8-bios-restart-on-power-fail)
- [Foro Beelink — el aviso `usb6-port1: Cannot enable` en Linux](https://bbs.bee-link.com/d/5075-ser8-8845hs--usb6-port1-cannot-enable-message-on-linux)
