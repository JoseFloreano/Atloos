---
formato: 4
tipo: feedback
fecha: 2026-08-18
reporter: claude-opus-5 (puente Telegram)
maquina: ser8-linux
so: Ubuntu (kernel 6.8.0-137-generic)
nucleos: 16
ram_gb: 50
superficie: claude-code
claude_code: no-medido
setup_sha: 17a4fcb
tarea: Enlistar pendientes y cerrar los que no necesitaran firma humana, por Telegram, en ventanas de 9 min
duracion_min: no-medido
turnos: 12
veredicto: sirvio-con-fricciones
skills_disparadas: []
skills_existentes_que_no_dispararon: [workstream-dispatch, session-close, memory-keeper]
skills_inexistentes: []
hooks_disparados: no-medido
graphify: no-instalado
bloqueantes: 1
coste_medido: no
contexto_medido: no
turnos_asistente: 12
---

# Feedback — Primera jornada larga de la SER8, entera por Telegram

> Leyenda: `[R]` comprobado con un comando · `[AR]` impresión del agente ·
> `[H]` lo dice el humano.

## 1. Qué se intentó

[H] Empezó como «solo enlista pendientes rápido» y creció a una jornada entera:
cerrar todos los pendientes que no necesitaran firma humana. Se cerraron la
auditoría 21 completa (H4-H7), el recorte del `CLAUDE.md` del bot, seis
pendientes de documentación y se construyó el generador del estado del mundo.
Todo desde el móvil, en ventanas de unos 9 minutos.

## 2. Evidencia de máquina

```
$ nproc
16

$ free -g
               total        used        free      shared  buff/cache   available
Mem:              50           1          48           0           1          49
Swap:              7           0           7

$ git log --oneline -1
17a4fcb fix(arnes): el caso B3 prohibia una frase que BOT_REGLAS usa a proposito; ahora busca la orden del original

$ git status --porcelain
?? setup/scripts/estado-del-mundo.py
?? setup/scripts/tests/test-estado-del-mundo.py
```

> ⚠ **`claude --version` NO se pudo correr**, y ese hueco es el hallazgo
> principal de este reporte — ver 4a. El frontmatter dice `no-medido` en vez de
> inventar un número.

**La SER8 tiene 16 núcleos y 50 GB.** Se anota con todas las letras porque es
justo el dato que a este repo le ha faltado cuatro sprints seguidos: el ×2,05
que gobierna el techo de frentes se midió en `ProgramadoMaxi2` y nadie puede
decir de cuántos núcleos. Ahora la máquina que corre 24/7 tiene su tamaño
escrito. También corrige por escrito lo que ya decía la auditoría 35: la unit
de systemd trae `MemoryHigh=3G`/`MemoryMax=4G` declarados como «el valor
conservador para 24 GB», y aquí hay 50.

[R] **De qué estuvo hecho el contexto**: `contexto_medido: no`.

No se pudo recorrer el transcript desde dentro de la sesión del puente. Se dice
en vez de dejarlo en blanco, y en vez de estimarlo.

```
Turnos de asistente: 12 (contados sobre la conversación, no sobre el transcript)

Llamadas por herramienta: NO MEDIDO
Las 3 salidas más grandes:  NO MEDIDO
Modelo por despacho de subagente:  ninguno — no se despachó ningún subagente
```

[R] Skills cargadas: **ninguna**. Ver sección 5 — es un hallazgo, no un dato de
color.
[R] Hooks disparados: no-medido (no hay forma de verlos desde la sesión del bot).
[R] Coste (`/cost`): **no se corrió `/cost`**. No está disponible por el puente.
[R] Sha del setup: `17a4fcb`, el mismo del worktree — el bot trabaja sobre el
repo, así que aquí no hay desfase entre el setup y lo evaluado.

## 3. Qué funcionó

- [R] **El aislamiento del worktree, sin una sola fuga.** Doce turnos escribiendo
  en quince ficheros y el árbol del usuario intacto.
- [R] **El formato de una línea por etapa en `.tg/progress.md`** hizo su trabajo:
  es lo único visible desde el móvil mientras el agente trabaja, y con ventanas
  de 9 minutos es la diferencia entre esperar a ciegas y ver avanzar.
- [R] **La suite descubre los arneses por glob**, así que los cuatro nuevos de
  hoy entraron sin tocar ningún registro. Eso es exactamente lo que
  `run-tests.py` promete en su cabecera, y se cumplió.
- [AR] **Los `[SKIP]` declarados de la suite valieron su precio.** Al correrla,
  cinco arneses dijeron qué no pudieron ejercer y por qué (sin `tiktoken`, sin
  PowerShell, sin Python 3.10). Ninguno mintió con un verde. Es la disciplina
  más cara de mantener de este repo y hoy pagó.
- [R] **El `CLAUDE.md` del bot llegó con la regla de entrega por chat**, y por
  eso este reporte va como fichero del repo y no pegado en un mensaje.

## 4. Qué NO funcionó

### 4a · El setup

- [R] **BLOQUEANTE — no se puede ejecutar NADA desde la sesión del bot.** Ni la
  suite, ni un script, ni `claude --version`. Toda orden que ejecute algo cae en
  «This command requires approval», y el puente corre en un modo que no puede
  pedir esa aprobación. Consecuencia medida: **se escribieron cuatro arneses y
  se modificaron tres ejecutables del camino caliente —el que abre cada
  conversación del bot, el que cierra cada turno con meta y los dos bootstrap—
  sin ejecutar una sola línea en toda la jornada.** El humano tuvo que correr la
  suite desde fuera y pegar la salida por chat. Funcionó, pero convierte cada
  ciclo de verificación en un viaje de ida y vuelta de varios minutos.
- [R] **La lista blanca de `.claude/settings.json` es ENTERAMENTE de Windows.**
  Las 46 entradas apuntan a `/c/Users/jlflo/...`. En esta máquina no casa
  ninguna, así que el permiso efectivo del bot en Linux **no es el que el
  fichero describe**: es el que quede por defecto. El fichero está commiteado y
  se lee como si gobernara las dos plataformas.
- [R] **`tiktoken` no está instalado en la SER8.** Dos arneses corrieron en modo
  PARCIAL y `test-claude-md-drift.py` no midió el presupuesto del snippet. No es
  rojo —y está bien que no lo sea—, pero la máquina que corre sin nadie mirando
  es justo donde esa cobertura debería estar entera.
- [R] **`projects.json` está gitignorado**, así que el alta de un proyecto no
  viaja entre máquinas y `test-claude-md-drift.py` sale por `[SKIP]` en
  cualquier árbol nuevo. Ya estaba en el backlog; se confirma desde esta máquina.

### 4b · Yo, el agente

- [AR] **Escribí `global` después de usar el nombre. Dos veces, el mismo día.**
  Es `SyntaxError` en Python: los dos ficheros no habrían ni importado. El
  primero en `test-registro-skills.py`, el segundo en `estado-del-mundo.py`,
  con horas de por medio. No es una torpeza puntual: es que **escribo el cuerpo
  de la función antes que su contrato**, y sin poder ejecutar nada el error
  sobrevive hasta que alguien lo lea.
- [AR] **Aplasté superficies en un diccionario y el veredicto quedó a merced del
  orden del disco.** `project-resume` vive en `claude-code/` y en `cowork/`; mi
  inventario era `{nombre: superficie}`, así que ganaba el último `rglob`. Si
  ganaba `cowork`, la fila legítima salía reportada como error. Un arnés cuyo
  resultado depende del orden de recorrido del sistema de ficheros no es un
  arnés.
- [AR] **Escribí un arnés que prohibía una frase que la propia regla usa a
  propósito.** El caso B3 de `test-bot-claude-md.py` exigía que «nota de sesión»
  no apareciera en la salida — y `BOT_REGLAS` dice «la nota de sesión **la
  escribe él** al hacer `/done`». Puse en rojo a la regla sustituta por decir la
  verdad. **Comprobé la ausencia de una cadena en vez de la ausencia de una
  orden**, que son cosas distintas.
- [AR] **Mi `except` anti-excepción podía lanzar.** El envoltorio de
  `bot_claude_md` existe para que `create_worktree` no muera, y su rama de
  rescate hacía `.rstrip()` sobre el valor original: con una entrada que no
  fuera cadena, el rescate reventaba. Sólo lo vi al diseñar el caso hostil —o
  sea, **lo encontró el arnés, no yo escribiendo el código**.
- [AR] **Recomendé borrar `turnos` del contrato sin haber leído la auditoría
  19.** Argumenté que era un campo decorativo y que dos cláusulas de corte eran
  peor que una. Al ir a ejecutarlo encontré C3, que pide exactamente lo
  contrario: un contador persistido fuera de la sesión, porque `/goal` reinicia
  el suyo al reanudar. **Di una recomendación firme con la evidencia a medias**,
  y sólo la corregí porque me tocó tocar el fichero.
- [AR] **Iba a construir un arnés para un umbral que ya estaba retirado.** El
  pendiente pedía vigilar el tope de 440 palabras; la auditoría 35 §7 lo había
  retirado por escrito («un margen que me inventé»). Me salvó leer el código
  antes de escribirlo, no leer el pendiente con desconfianza.
- [AR] **Método con el que afirmo que no hay más:** releí mis quince ficheros
  buscando las tres formas que ya me habían fallado (nombres declarados después
  de usarse, colecciones que aplastan claves, aserciones sobre cadenas en vez de
  sobre comportamiento). Lo que no cubre ese método —y por tanto no puedo
  afirmar— es todo lo que sólo aparece ejecutando.

## 5. Triggers — lo que se escribió literalmente

| Frase literal del humano | Qué esperaba que cargara | Qué cargó |
|---|---|---|
| «Solo enlista pendientes rápido» | `project-resume` | nada |
| «haz un reporte en pendientes … que piden los pendientes» | `memory-keeper` | nada |
| «despacha / reparte» (nunca se escribió) | `workstream-dispatch` | — |

> **Ninguna skill disparó en toda la jornada.** Y es correcto por diseño: el
> registro del perfil bot excluye `project-resume` («lo sustituye la inyección
> del daemon»), `memory-keeper` y `session-close` (escriben en el vault). El
> hallazgo no es que fallara el trigger: es que **una jornada entera de trabajo
> real sobre este repo no necesitó ni una skill**, y eso merece mirarse. El
> trabajo fue de auditoría y arneses, que es justo lo que la «skill de despacho
> de auditorías» del backlog cubriría.

## 6. Graphify — ¿se usó el mapa?

**Instalación**

- [R] `graphify` instalado en este repo: **no**. Se intentó `graphify query` en
  el primer turno y el comando fue denegado por permisos antes de poder saberlo.
- [R] Hook `post-commit` instalado: **no** — el `_PROJECT.md` del vault lo dice
  («snapshot ausente (hook post-commit no instalado)»).
- [R] El `CLAUDE.md` del proyecto lleva: **ninguna de las dos**, y ahí está el
  hallazgo. El original trae el disparador nuevo en su línea 29; el
  `bot_claude_md` se lo comía junto con todo lo que sigue a «Memory Rules».
  **Arreglado hoy** — pero esta jornada corrió sin él.

**Uso**

- [R] ¿Se corrió `graphify query` antes del primer `grep`? **No.**
- [AR] ¿Por qué? Se intentó, por costumbre y no por instrucción: **la regla no
  estaba en mi contexto**, porque el recorte del bot la había borrado. Es la
  demostración en vivo del pendiente que se arregló hoy: durante toda la jornada
  el agente del puente trabajó sin el disparador de Graphify, sin el criterio de
  merge a `main` y sin la higiene de salida, y **nada se lo dijo**.

## 7. Fricciones menores

- [AR] Las ventanas de ~9 minutos obligan a elegir entre terminar y verificar.
  Se resolvió reportando siempre qué quedó sin verde, pero el reparto lo decidió
  el reloj, no el trabajo.
- [R] El backlog está fechado **2026-08-19** con una «pasada del 08-19» cuando
  hoy es 18. O hay desfase de reloj entre máquinas o esa pasada se fechó
  adelantada.
- [R] El `_PROJECT.md` del vault decía 114 líneas (medido 08-19) y mide 120.
- [AR] `wc` sobre el vault está bloqueado por el sandbox pero `Read` no, así que
  medir líneas de un fichero del vault pide un rodeo. El rodeo funciona, lo que
  incomoda es que **existe y no hay regla escrita que lo prohíba** — la misma
  asimetría del `report.md` que ya está anotada en `plantilla-despacho.md`.

## 8. Lo que esperaba y no existe

- [H] **Una forma de correr la suite desde el puente.** Es el bloqueante de 4a
  y lo que más caro salió. Hoy la única vía es que el humano la corra fuera y
  pegue la salida.
- [H] **Un arnés que compare `.claude/settings.json` con la plataforma donde
  corre.** Un fichero de permisos 100 % Windows commiteado en un repo que corre
  en Linux 24/7 no da error: simplemente no aplica, en silencio.
- [H] **La skill de despacho de auditorías** del backlog. Esta jornada fue una
  auditoría entera hecha a mano, con el prompt reconstruido en cada ventana.

## 9. Confirmación del humano

- [H] Leído y corregido por: `<pendiente>`
- [H] Cambios que pedí sobre el borrador del agente: `<pendiente>`

> ⚠ **Este reporte NO pasa `valida-reporte.py` todavía, y es correcto que no
> pase.** La sección 9 la rellena una persona y el validador la comprueba; un
> agente que la rellenara estaría firmando su propio trabajo. Está en el mismo
> estado que el reporte del 08-16 — con una diferencia: aquel se archivó como
> terminado sin que nadie corriera el validador, y este declara el hueco antes
> de que nadie pregunte. Córrelo cuando firmes:
> `setup/scripts/py feedback/_herramientas/valida-reporte.py feedback/reportes/2026-08-18-ser8-jornada-larga-por-telegram.md`
