# RFD — Fase T2 del puente Telegram: modo escritura

> **Versión:** v2 (2026-08-01) — revisada por el usuario y el auditor
> **Estado:** propuesta aprobada para implementar; **no** aprobada como fase
> (eso requiere auditoría externa tras las pruebas)
> **Contexto previo:** `00-DISENO-TELEGRAM-BRIDGE.md` §2 · `ADR-20260801-puente-telegram`
> **Continuación futura:** `03-RFD-T3-T4-DESARROLLO-PARALELO.md` (T5) ·
> `05-RFD-T4-CONTINUAR-DESDE-AVISO.md` (T4)
> **Método:** brainstorming de Superpowers (spec previa al plan de implementación).
>
> **Qué cambió en v2:** se mantienen §3 (opción A), C0, C3 y C8. Se reescriben
> C2, C4, C5 y C6 por el modelo de **worktrees** (§4), que resuelve el
> aislamiento de forma estructural en vez de por confianza. Detalle en §7.

---

## 1. Problema

T1 dejó un daemon que **lee y conversa** desde Telegram: allowlist, selector de
proyecto por `cwd`, continuidad por `--resume`, TTL de 24 h, lock de un vuelo
por chat, `/model`. 10/10 pruebas. Lo que no puede hacer es **cambiar nada**.

T2 le da escritura. Es el salto cualitativo del puente: pasa de ser una consulta
remota a ser un agente con acceso de escritura a tu disco, gobernado desde un
canal cuyo username es público. Todo lo que sigue existe para que ese salto sea
reversible y acotado.

## 2. Objetivo (desglosado de las decisiones tomadas)

**O1. Desarrollo completo desde el móvil.** No son retoques: implementar
features, refactorizar y publicar. El móvil como estación de trabajo real.

**O2. Dos modos conmutables por comando, como en Claude Code.** Lectura por
defecto; modo auto bajo demanda.

**O3. Confirmación explícita para lo irreversible.** Refinado en v2: lo
irreversible es **lo que toca `main`**, y solo eso lleva botón (§4, C4).

**O4. Bash con lista blanca.** Tests, linters y git de lectura — nada más.

**O5 (v2). El bot nunca escribe en el árbol de trabajo del usuario.** Ni un
byte. Es la decisión estructural de esta versión.

**No objetivos:** aprobación por cada acción del agente (rechazada: hace
inusable el trabajo real), `--dangerously-skip-permissions`, y el desarrollo
**paralelo** de varias conversaciones a la vez (RFD 03, horizonte T3/T5).

## 3. Caso central A: arquitectura de las aprobaciones *(sin cambios en v2)*

El CLI headless **no tiene `--permission-prompt-tool`** (verificado el
2026-08-01): no puede delegar una pregunta de permiso a mitad de ejecución. Solo
el Agent SDK de Python (`can_use_tool`) permite interceptar cada llamada.

| | **A. Flags del CLI** *(elegida)* | **B. Agent SDK** | **C. Hook PreToolUse** |
|---|---|---|---|
| Cómo | `--allowedTools` ampliado por modo + `--permission-mode` por modo (ver C0); los git ops los ejecuta el daemon | `claude-agent-sdk` intercepta cada tool y la reenvía como botón | Hook que bloquea `Bash(git commit\|push)` con `CLAUDE_TG_BOT=1` |
| Granularidad | Por comando del daemon | Por acción del agente | Por acción, pero **solo bloquea** |
| Cambio sobre T1 | Pequeño (núcleo probado intacto) | Reescritura del núcleo | Media (pieza nueva) |
| Dependencias | Ninguna | `claude-agent-sdk` 0.2.128 | Ninguna |
| Puede preguntar | Sí, desde el daemon | Sí, por acción | **No** (hook síncrono) |

**Elegida: A.** La única ventaja real de B —aprobación por acción— es justo la
descartada por inusable: pagaríamos una reescritura y una dependencia por una
capacidad que no se usaría. C duplica en una pieza nueva lo que la lista blanca
ya resuelve, y encima no puede preguntar.

**Consecuencia aceptada:** el agente **no puede** commitear, publicar ni
mergear. Esas operaciones las ejecuta el daemon, nunca el agente. Es una
limitación deliberada: hace imposible que una inyección de prompt logre
publicar algo, porque el canal de publicación no pasa por el agente.

## 4. Caso central B: aislamiento por worktree *(nuevo en v2)*

### El modelo

**Una conversación = una rama = un worktree.**

```
Repo del usuario (OneDrive)          Worktrees del bot (LOCAL, fuera de OneDrive)
main  ← intocable                    %LOCALAPPDATA%\claude-tg-worktrees\
árbol de trabajo del usuario           <proyecto>\tg\<fecha>-<slug>\   ← rama tg/<fecha>-<slug>
  ← el bot NUNCA lo toca               <proyecto>\tg\<fecha>-<otro>\   ← otra conversación
```

- El worktree se crea **perezosamente**: al primer `/write on` de una
  conversación, no antes. Las conversaciones de solo lectura no crean ninguno.
- `/new` en modo escritura ⇒ rama + worktree nuevos. `/chat <n>` retoma **esa**
  rama con su worktree. `/chats` muestra la rama de cada conversación.
- **Nunca** `git checkout` de rama en el árbol compartido: cambiar de rama bajo
  los pies del usuario es exactamente el daño que este modelo evita.
- Los worktrees viven **fuera de OneDrive** (`%LOCALAPPDATA%`): un checkout
  entero dentro de la carpeta sincronizada provocaría tormentas de sync y
  lecturas de bytes obsoletos. Mismo criterio que el fix A4 y el `.git` del vault.

### Por qué resuelve el problema de raíz

El aislamiento deja de depender de que el bot "se porte bien": **no comparte
archivos con el usuario**. Puedes estar editando en la laptop con cambios sin
commitear mientras el bot desarrolla, y ninguno ve al otro. Es también lo que
deja pagado el paralelismo futuro del RFD 03 sin haberlo buscado.

### Detalles obligatorios

1. **Copiar `CLAUDE.md` al worktree.** Está gitignorado (es artefacto de
   instancia), así que un worktree nace **sin Memory Rules** si no se copia —
   el agente perdería el aislamiento de memoria del proyecto.
2. **Validar que la rama no esté ya montada** en otro worktree antes de crearlo
   (git lo rechaza; hay que reportarlo con sentido, no con un stacktrace).
3. **`.tg/` en el `.gitignore` del worktree**: es el canal de progreso
   (C2), no debe acabar en un commit.
4. **Reconciliación al arrancar**: contrastar `state.json` con
   `git worktree list` real. Worktrees huérfanos (en el estado pero no en
   disco, o al revés) → **reportar, nunca borrar solos**.

## 5. Casos de diseño

### C0. Permisos: lista blanca **y frontera de directorio** *(CORREGIDO 2026-08-01)*

> 🚨 **Esta sección estaba equivocada y produjo un agujero de aislamiento real.**
> Decía: "T2 **no usa** `acceptEdits`: mantiene `dontAsk`". Con eso, el agente
> podía escribir **en cualquier parte del disco**, incluido el árbol del usuario
> — justo lo que este RFD promete impedir. Canario y evidencia en
> [[2026-08-01-telegram-t2]].

**El error de razonamiento.** T1 mostró que con `--allowedTools "Read,Grep,Glob"`
y `dontAsk` una escritura se denegaba (`permission_denials: 1`), y se concluyó
que "`dontAsk` era la barrera". **Falso**: se denegó porque `Write` no estaba en
la lista blanca, no por el modo. Al ampliar la lista en modo auto, el mismo flag
dejó de proteger nada. La evidencia era correcta; la extrapolación no.

**Verificado el 2026-08-01** (mismo prompt, escribir dentro y fuera del cwd):

| `--permission-mode` | Dentro del cwd | Fuera del cwd |
|---|---|---|
| `dontAsk` | sí | 🚨 **sí — no hay frontera de directorio** |
| `acceptEdits` | sí | ✅ **denegado** |

**Son dos mecanismos ortogonales y hacen falta los dos:**

| Qué limita | Mecanismo |
|---|---|
| **Qué herramientas** puede usar | `--allowedTools` (lista blanca) |
| **Dónde** puede escribir | `--permission-mode acceptEdits` (frontera = cwd) |

| Modo | `--allowedTools` | `--permission-mode` |
|---|---|---|
| Lectura (defecto) | `Read,Grep,Glob` | `dontAsk` — correcto aquí: sin `Write` no hay nada que acotar |
| Auto | `Read,Grep,Glob,Edit,Write` + Bash de C3 | **`acceptEdits`** |

`--disallowedTools` es la **segunda barrera**: `git commit`/`push`/`merge`, y
además `Write(<repo>\**),Edit(<repo>\**)` con la ruta real del proyecto (el
worktree vive en `%LOCALAPPDATA%`, así que no estorba al trabajo legítimo).

**Lección que aplica a todo el RFD:** probar que algo *no ocurre por defecto* no
es probar que *no puede ocurrir*. Las pruebas a-h pasaban con el agujero abierto
porque ninguna intentó escribir fuera. Toda promesa de aislamiento necesita un
canario que intente violarla.

### C1. Conmutación de modo (O2)

`/write on` → modo auto · `/write off` → lectura · estado visible en `/status`.

- Ámbito: **por conversación** (v2). Es la unidad que tiene rama y worktree;
  atarlo al chat haría que `/chat` cambiara de permisos sin decirlo.
- Al reiniciar el daemon el modo **no se restaura**: arranca en lectura.
- `/write on` crea el worktree si la conversación aún no tiene, y avisa de qué
  queda habilitado y en qué rama se trabaja.

### C2. Checkpoints de progreso *(v2 — reemplaza la caducidad del modo escritura)*

La caducidad a 30 min de v1 se **elimina**: con el trabajo aislado en un
worktree, dejar el modo escritura abierto ya no pone en riesgo el árbol del
usuario, y cortar una tarea de 40 minutos por inactividad sería absurdo.

En su lugar, **visibilidad**: durante invocaciones en modo escritura, cada
**30 minutos** el daemon envía un checkpoint con el tiempo transcurrido y la
última etapa reportada.

Mecanismo: el prompt de cada invocación en modo escritura instruye al agente a
mantener `.tg/progress.md` en el worktree — **una línea por etapa completada**.
El daemon lo lee en su timer. Si el archivo no existe o no ha cambiado, el
checkpoint lo dice igual (tiempo transcurrido, sin etapa nueva): un silencio de
40 minutos es peor que un "sigo en ello".

### C3. Lista blanca de Bash (O4) *(sin cambios de criterio; ahora corre dentro del worktree)*

| Categoría | Comandos |
|---|---|
| Tests | `npm test`, `npm run test:*`, `pytest`, `py -m pytest`, `flutter test` |
| Calidad | `npm run lint`, `npm run build`, `ruff`, `eslint`, `flutter analyze` |
| Git de lectura y staging | `git status`, `git diff`, `git log`, `git add` |

Denegado siempre: `git commit`, `git push`, `git merge`, `git reset --hard`,
`rm`, `mv`, `curl`, `wget`, `ssh`, instaladores (`npm install`, `pip install`)
y **todo lo no listado** — es lista blanca: lo que no está, no corre.

El comando de test concreto de cada proyecto se declara en `projects.json`
(§6), porque "correr los tests" no significa lo mismo en un repo de Python que
en uno de Flutter.

### C4. Flujo de git *(v2 — reescrito: el botón se mueve a `/merge`)*

El criterio de v2: **botón solo para lo que afecta a `main`**. Commitear y
publicar en una rama `tg/*` son operaciones reversibles que no tocan el trabajo
de nadie; exigir confirmación ahí era fricción sin seguridad.

| Comando | Qué hace | Botón |
|---|---|---|
| `/diff` | Resumen de cambios del worktree; diff completo como adjunto si es largo | — |
| `/commit` | Sin mensaje: pide al agente que proponga uno y te lo muestra para confirmar o sustituir. Con mensaje: usa el tuyo | — |
| `/test` | Corre el comando de test declarado del proyecto, dentro del worktree | — |
| `/push` | Publica la rama `tg/*`. Si hay remoto y `gh`, crea/actualiza el PR y manda el link (revisar el diff en la app de GitHub) | — |
| `/merge` | Integra en `main` (squash por defecto; vía PR si existe, local si no) | **Sí, caduca a 5 min** |
| `/done` | Tras merge o abandono: quita el worktree, borra la rama local si está mergeada, archiva la conversación | — |

**`/merge` está deshabilitado si `/test` no pasó en esa rama después del último
commit.** No es una recomendación: el daemon lo bloquea. Un merge a `main` desde
el móvil sin verde es la forma más fácil de romper algo sin verlo.

Los git ops los ejecuta **el daemon**, nunca el agente (§3). No existe camino
por el que el agente commitee, publique o mergee.

**Gap detectado (2026-08-01) — falta `/pull`.** La tabla de arriba no tiene
forma de traer `main` a una rama `tg/*` mientras la conversación sigue
abierta. Una conversación larga (checkpoints de 30 min, sin caducidad — C2)
puede quedarse trabajando días sobre una rama que nació de un `main` viejo;
si mientras tanto se mergea otra cosa, la rama se desfasa y el `/merge`
final llega con más conflicto del necesario. Pendiente diseñar `/pull`
(rebase o merge de `main` dentro del worktree, con el mismo criterio de
botón que C4: probablemente sin botón si es fast-forward, con aviso si trae
conflictos). No entra en el alcance de T2 (§7); queda anotado para T3.

### C5. Concurrencia con la laptop *(v2 — resuelto por construcción)*

v1 proponía "avisar si el árbol está sucio". Con worktrees **el problema
desaparece**: el bot trabaja en otro directorio y otra rama. Puedes tener
cambios sin commitear en la laptop mientras el bot desarrolla, y son
invisibles entre sí.

Lo único que sigue compartido es el **repositorio git** (`.git` común a todos
los worktrees). Por eso `/merge` es la única operación que necesita cuidado, y
por eso lleva botón y verde de tests.

### C6. Red de seguridad y recuperación *(v2 — más fuerte)*

La red ya no es "el bot no puede commitear", sino que **su trabajo vive en otra
rama y otro directorio**:

- Descartar todo = `/done` sin merge: se borra el worktree y la rama. `main` y
  tu árbol nunca supieron que existió.
- El riesgo residual de v1 —archivos no versionados sobrescritos— **también
  desaparece**: el worktree parte de un checkout limpio de la rama.

### C7. Auditoría

Por invocación en modo auto se registra: modo, **rama y worktree**,
herramientas concedidas y `permission_denials`. `/commit`, `/push` y `/merge`
registran el hash resultante. Sin contenidos de archivos ni token.

### C8. Defensa ante inyección de prompt *(sin cambios de criterio; reforzada)*

1. **Lista blanca de Bash** (C3): una inyección exitosa no obtiene shell.
2. **`WebFetch` denegado** también en modo auto.
3. **Canal de publicación fuera del agente** (§3): no puede commitear, publicar
   ni mergear ⇒ no puede exfiltrar por git.
4. **Aislamiento por worktree** (§4, v2): aunque lograra escribir algo hostil,
   lo escribe en una rama desechable que tú revisas antes de mergear.

Daño máximo acotado a: "modificó archivos de una rama desechable, sin publicar
y sin ejecutar nada fuera de la lista".

### C9. Costo y tiempo

Las tareas de escritura son largas. **El timeout pasa de 10 a 90 minutos en
modo escritura** (en lectura se queda en 10): el de 10 mataba cualquier
desarrollo real. Los checkpoints (C2) hacen que esa espera sea visible.

Se mantiene `--max-turns 15` y se recomienda `/model` para bajar a
sonnet/haiku en tareas mecánicas. El tope de costo por tarea sigue siendo T3.

### C10. Cambio de conversación durante un vuelo *(v2)*

Mientras hay una invocación en curso, `/chat` y `/p` responden **⏳** igual que
un mensaje normal. Cambiar de conversación a mitad de vuelo entregaría la
respuesta a la conversación equivocada.

El paralelismo real —seguir con otro proyecto mientras el primero corre— está
diseñado como idea en el **RFD 03** y queda fuera de T2.

## 6. Formato de `projects.json` (ampliado)

```json
{
  "claude-setup": {
    "path": "C:\\ruta\\al\\repo",
    "test": "py -m pytest -q"
  }
}
```

Se mantiene la compatibilidad con el formato de T1 (`"nombre": "ruta"`): sin
`test` declarado, `/test` avisa de que el proyecto no lo tiene configurado y
`/merge` queda bloqueado (no hay verde posible).

## 7. Alcance

**Entra en T2:** `/write on|off` por conversación · worktree por conversación ·
lista blanca de Bash · `/diff`, `/commit`, `/test`, `/push`, `/merge` (con
botón y verde), `/done` · checkpoints de 30 min · timeout de 90 min ·
reconciliación al arrancar · auditoría ampliada · README y pruebas.

**No entra** (T3+): triage con modelo barato, tope de costo, rate limiting,
systemd, `/pull` (traer `main` a una rama `tg/*` en vuelo — gap de C4),
**desarrollo paralelo** (RFD 03/T5).

## 8. Criterios de éxito

1. En modo lectura, T2 se comporta **exactamente** como T1 (sin regresiones).
2. **Aislamiento (pasivo):** un archivo modificado y sin commitear en la laptop
   queda byte-idéntico tras un desarrollo completo del bot (hash antes/después).
2b. **Aislamiento (activo) — CANARIO OBLIGATORIO:** se le pide explícitamente al
   agente, en modo escritura, que edite un archivo FUERA del worktree (ruta
   absoluta del repo del usuario). Debe **fallar**, y el archivo quedar
   byte-idéntico. Sin esta prueba el criterio 2 no significa nada: solo
   demuestra que no lo hace cuando nadie se lo pide.
3. El worktree tiene `CLAUDE.md` y el agente ve las Memory Rules.
4. `/commit` funciona sin botón; el commit queda en `tg/*` y `main` no se mueve.
5. `/merge` deshabilitado sin `/test` verde; con verde + botón → squash en
   `main`. Botón caducado (>5 min) no ejecuta.
6. Un intento del agente de `git push`/`commit` **falla** y se reporta.
7. Checkpoint a los ~30 min con la etapa correcta leída de `.tg/progress.md`.
8. Matar el daemon con un worktree vivo → al reiniciar reconcilia y `/chat`
   retoma rama y worktree.
9. `/done` limpia worktree y rama; `/chats` deja de ofrecerla como activa.

## 9. Desviaciones respecto al diseño original y a v1

Respecto al **diseño §3** (que asignaba a T2 "`/chats`, `/chat <n>`, `/write
on|off`, aprobaciones por botones inline, troceo >4096"):

- `/chats`, `/chat <n>` y el troceo **ya se implementaron en T1**; `/model` se
  adelantó a T1 a petición del usuario.
- **"Aprobaciones por botones inline" cambia de significado dos veces**: el
  diseño las concebía por acción del agente (vía SDK); v1 las puso en
  commit/push; **v2 las deja solo en `/merge`**, que es lo único irreversible
  para terceros.

Respecto a **v1 de este RFD**:

| Sección | v1 | v2 | Por qué |
|---|---|---|---|
| §4 | no existía | Aislamiento por worktree | Convierte el aislamiento en estructural en vez de confiar en el agente |
| C1 | modo por chat | modo por conversación | La conversación es la unidad que tiene rama y worktree |
| C2 | caducidad a 30 min | checkpoints cada 30 min | Con worktree no hay riesgo que caducar; el problema real era el silencio |
| C4 | botón en commit y push | botón solo en `/merge`, con verde de tests | Commit/push en rama son reversibles; el riesgo está en `main` |
| C5 | avisar de árbol sucio | innecesario | Los worktrees eliminan la concurrencia sobre archivos |
| C6 | red = "no puede commitear" | red = rama desechable | Más fuerte: también protege archivos no versionados |
| C9 | timeout 10 min | 90 min en escritura | 10 min mata cualquier desarrollo real |
| C10 | no contemplado | `/chat` y `/p` bloqueados en vuelo | Evita entregar la respuesta a la conversación equivocada |

## 10. Respuestas a las preguntas abiertas de v1

1. **¿La lista blanca cubre tus stacks?** Se resuelve por diseño: el comando de
   test es **por proyecto** en `projects.json` (§6), no una lista global. La
   lista blanca de C3 cubre lo transversal (git de lectura, linters comunes).
2. **¿30 minutos de caducidad?** Anulada: no hay caducidad (C2). Los 30 minutos
   pasan a ser el intervalo de los checkpoints.
3. **¿`/write on` por chat o por proyecto?** Por **conversación** — más fino que
   ambas opciones de v1, y es lo coherente con "1 conversación = 1 rama".
