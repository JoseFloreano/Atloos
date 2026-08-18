---
title: Auditoría del sprint 14 — cerrados §3 y §4, y un check nuevo que pone la suite roja fuera de la Legion
tags: [auditoria, sprint14, disparadores, contexto, dependencias, ser8]
created: 2026-08-18
updated: 2026-08-18
status: cerrada
type: auditoria
project: atloos
base: 09b0699
---

# Auditoría del sprint 14

**Veredicto: aceptado, con un hallazgo que hay que cerrar antes del alta de la
SER8.** Los dos números de la auditoría 33 quedan cerrados, y el trabajo sobre
disparadores es el mejor razonamiento de diseño que ha salido de esta serie.

**Pero el arnés nuevo introduce una dependencia no declarada que pone la suite
roja en cualquier máquina que no sea la Legion** — tercera aparición de «mismo
commit, dos veredictos».

---

## 1 · Lo que repliqué y confirmo

**El estado [R].** `main` = `aeae49d` con el sprint 13 dentro; rama en `09b0699`.
`origin/main` sigue en `8fe6a9f` — **sin pushear**, como él declara.
`git worktree list` = **2**, solo el del bot: el fantasma `sprint13-verify`
desapareció.

**Los ficheros llegaron donde debían [R]:** `docs/ecosistema/32` (190 líneas) y
`docs/auditoria/33` (166) entraron al repo — la procedencia colgante queda
cerrada. `34-RFD-CONTEXT-EDITING.md` (7 KB) y `cruce-plan-vault.md` (4,2 KB)
existen.

**La regla 6 desapareció de los dos gemelos [R].** Ni «2+ sesiones» ni ninguna
variante. La regla 6 es ahora *«Tu avance y tus pendientes van SIEMPRE a tu
nota»*. Y la cabecera del snippet dice **935 tokens / 3 370 caracteres**; medí
**3 371** — un carácter de diferencia por cómo cada uno recorta el comentario.
**Coherente.**

**Los tres grados quedan escritos** en `disparadores.md`, y la fila de la regla 6
marcada `CERRADO`.

---

## 2 · Su decisión sobre la regla 6 es mejor que mi encargo

Yo pedí «reanclar o retirar». Él hizo una tercera cosa que no se me ocurrió:
**quitó la condición y dejó la rama segura como regla**.

> *«La pregunta era la equivocada: una de las dos ramas es segura en los dos
> casos. Escribir siempre en tu nota de sesión no cuesta nada, así que la
> condición solo servía para no cumplirse.»*

Y lo verificó donde importa: el hook `Stop` ya acepta esa escritura
(`check-vault-updated.py:147-159`) y `session-close` ya consolida. **La regla
inerte también se pagaba**: −8 tokens en los tres `CLAUDE.md`.

**Y no tocó `skill-forge`, correctamente.** Mi propio «Qué NO hacer» prohibía
cambiar una `description:` sin medir, y una sesión ciega no se monta desde
dentro. Entregó la medición lista para ejecutar. Eso es cumplir el contrato, no
incumplir el encargo.

---

## 3 · Su reclasificación de los `py` es correcta y mi cifra era pobre

Yo conté **16** con `'"py"\|py -m\|py setup'`. Él contó **22** con
`(?<![\w./-])py(?![\w-])` y los clasificó: **17 de prosa** que explica el
problema, **1 de mecanismo**, **2 de patrones de allowlist**, **2 órdenes
copiables** — y solo una de esas necesitaba etiqueta.

**Mi «los 16 `py` fuera» era un objetivo mal formulado.** Borrar prosa que
explica por qué `py` no existe en Linux **borra la explicación**. Y su decisión
de no extender el arnés al puente está bien fundada:

> *«En seco daba 8 hallazgos, 7 falsos positivos. Un check ruidoso se acaba
> desactivando.»*

Es la regla que este repo aprendió en el sprint 7 y aquí se aplicó **antes** de
que costara algo.

---

## 4 · H1 · **El check 6 pone la suite roja sin `tiktoken`** — y no está declarado

Corrí la suite desde el puente sobre un árbol de laboratorio limpio:

```
── Check 6 · el snippet de memoria, medido (BLOQUEA) ──────────────────────
  [FALLA] sin tiktoken no se puede medir el snippet
          (No module named 'tiktoken'): no se estima, se dice
exit=1
```

**No pude ejercer mis dos mutaciones** —cabecera que declara de menos, y cuerpo
por encima del techo— porque el check muere antes de llegar a ellas. Su
comportamiento con `tiktoken` presente queda **[AR]**: él lo demuestra, yo no lo
puedo replicar.

Y el problema no es el fallo honesto —*«no se estima, se dice»* es la regla de la
casa, bien aplicada—. El problema son tres cosas juntas:

1. **La dependencia no está declarada en ningún instalador.**
   `setup/telegram-bridge/requirements.txt:16` dice, literal: *«`tiktoken` NO va
   aquí: no es dependencia de arranque»* — correcto para el puente, **pero
   entonces no está en ninguna parte**, y ahora la suite entera depende de ella.
2. **La SER8 nace roja.** Ya arrastra la exención de `test-suelo-python` hasta el
   2026-11-17; con esto suma un segundo rojo permanente. **Una suite que nunca
   está verde deja de leerse**, y el día que se ponga roja de verdad nadie lo va
   a notar. Es el argumento que escribí en la auditoría 31 y sigue vigente.
3. **El repo ya tiene el patrón correcto y este check no lo usó.**
   `test-sync-hooks-paridad.py:235` imprime `Modo: PARCIAL` cuando falta
   PowerShell, dice qué no pudo ejercer y **no tumba la suite**. Lo elogié en la
   auditoría 33 la semana pasada.

> **Y hay un matiz de fondo que conviene ver:** el número que ahora **bloquea** la
> suite se mide con `o200k`, el tokenizador de **OpenAI**, como proxy del de
> Claude. Convertir un proxy de otro proveedor en requisito duro de todas las
> máquinas es mucho peso para una cifra aproximada.

**Las tres salidas son defendibles y hay que elegir una**: declarar `tiktoken` en
`setup-new-machine` (las dos versiones) y en un `requirements` del arnés · o
degradar a `PARCIAL` como su hermano · o mover el check a un arnés opcional que
no entre en `run-tests.py`. **Lo que no vale es dejarlo como está antes de
desplegar.**

---

## 5 · El hallazgo suyo que vale más que el encargo

**D3 del RFD 34**, que yo no pedí:

> `memory-flush.py` es un hook **PreCompact**. Si el corte de contexto evita o
> retrasa la compactación, **ese hook deja de dispararse** — y con él la última
> red que obliga a volcar al vault.

Es **la tercera vez que aparece la misma forma**: el perfil del bot que ahorraba
tokens y apagaba los seis hooks (sprint 12), la exención que silenciaba el suelo
(sprint 12), y ahora una optimización de contexto que apagaría el volcado de
memoria. **Una optimización que desactiva una vigilancia, en silencio.**

Su orden —**flush → clear → compact**— es la respuesta correcta y no estaba en
ningún sitio.

**Y D5 cierra la pregunta que te interesaba**: `clear_tool_uses_20250919` **no se
expone en `claude-code` 2.1.234** ni en `--help` ni en `settings.json`; es
parámetro de la Messages API. **Hoy el ×32 no se puede activar desde nuestro
harness.** Declaró el límite de la medición —mide la superficie documentada, no
prueba que no haya vía interna— que es exactamente como hay que decirlo.

---

## 6 · Su mea culpa 1 es el mejor de la serie

> *«El `Remove-Item -Recurse -Force` lleva escrito desde hace sprints en
> `workstream-merge-gate/references/por-que-cada-paso.md` §Paso 7. En el sprint
> 13 lo reporté como fallo del entorno. Era fallo mío, y de los caros: convertí
> una respuesta que ya existía en una deuda nueva.»*

**Eso invalida un ítem que yo di por bueno en la auditoría 33** (lo listé como
«novena entrada del mismo problema»). No era un problema del repo: era una
respuesta escrita que ninguno de los dos leyó. **Lo retiro de la lista de
pendientes.**

---

## 7 · Lo menor

- **443 palabras contra mi ≤440.** Está declarado y argumentado, y el arnés real
  avisa a 450. **Mi 440 es un margen que me inventé y que ningún check mide** —
  aceptado sin objeción.
- **Commiteó mi auditoría 33 con un `git add -A`** y lo declaró. Entra como
  entraron la 21 y la 31. Sin objeción, y agradezco que lo dijera.
- **`origin/main` sigue en `8fe6a9f`.** Dos sprints sin empujar.

---

## 8 · La corrección de memoria para el alta de la SER8

Va **como paso**, no como nota al pie. La unit trae `MemoryHigh=3G` /
`MemoryMax=4G`, declarados como el valor conservador **para 24 GB**. La SER8
tiene **56**.

**Texto para añadir al prompt de `_archive/PROMPT-ser8-alta-vault-y-daemon.md`,
justo antes de habilitar el servicio:**

```
PASO N · Ajusta la memoria de la unit ANTES de habilitarla

  La plantilla trae MemoryHigh=3G / MemoryMax=4G. Ese es el valor conservador
  para una máquina de 24 GB y ESTA TIENE 56. Compruébalo tú:

      free -g            # total visible, no el de la caja

  El cgroup NO es solo el daemon: cada invocación lanza un `claude` hijo que
  vive dentro, así que el techo cubre daemon + agentes concurrentes.

  Fila que aplica (tabla de docs/telegram/23-MANUAL...:847-858):
      56 GB  ->  MemoryMax=16G   MemoryHigh=12G

  ⚠ Si lo dejas en 4G el fallo NO se ve como error: el agente muere por OOM,
    systemd lo reinicia a los 30 s (Restart=on-failure) y desde Telegram
    parece que "el bot se olvidó de lo que estaba haciendo". Diagnosticar eso
    después cuesta una tarde.

  Comprobación, con el servicio ya arriba:
      systemctl --user show claude-telegram -p MemoryMax -p MemoryHigh -p MemorySwapMax
      # MemoryMax=17179869184  MemoryHigh=12884901888  MemorySwapMax=0
```

---

## 9 · Antes de pegar el prompt de alta

1. **`tiktoken`** — H1. O se declara, o el check degrada. **Va primero**: sin
   esto la SER8 nace con la suite roja por dos motivos distintos.
2. **Pushear.** `origin/main` en `8fe6a9f`, dos sprints por detrás.
3. **Empujar el vault.** Sigue siendo el bloqueo de siempre.
4. **Integrar el sprint 14.**

Con esas cuatro, el prompt se pega con el paso de §8 añadido.

---

**Escrito por el auditor externo desde el puente, sobre `09b0699`.** Fichero
nuevo en `docs/auditoria/`, **sin commitear**.
