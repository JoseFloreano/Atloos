# El disparador — por qué una instrucción correcta no se cumple

Detalle de la regla 1 del `SKILL.md`. Los dos casos son de campo, con coste
medido, y fallaron por la misma razón: **decían QUÉ, no decían CUÁNDO.**

## El formato de la descripción

Qué hace en una frase + `Use when...` + **frases gatillo literales del usuario**
+ anti-triggers (*«NO usar si...»*). Las frases gatillo se copian de cómo habla
el usuario, no de cómo nombramos nosotros la tarea: es justo ahí donde se abre
la distancia que mata el disparo.

## Caso 1 · Graphify — la instrucción que dice qué y no dice cuándo

La línea que escribe `graphify claude install` en el `CLAUDE.md` dice *«for
codebase questions, first run graphify query»*. Es correcta y se incumplió
**3 jornadas de 3** con la herramienta instalada y al día (`graphify: no-usado`
en los dos reportes de campo, y la tercera jornada confirmó que el `CLAUDE.md`
seguía con la línea vieja).

> **La instrucción no dice cuándo, solo dice qué.** — el humano, 2026-08-11

El corolario, que es la parte accionable:

> **Un disparador que exige que el agente se autodiagnostique el tipo de
> pregunta no se dispara nunca.**

*«Cuando sea una pregunta sobre el código»* obliga al agente a clasificar su
propia intención antes de actuar, y esa clasificación no ocurre. La sustitución
viaja en `memory-snippet.md` y el arnés `test-claude-md-drift.py` caza la línea
vieja por su nombre.

### ❌ REFUTADO (2026-08-17): el arreglo de este caso también fallaba

Esta misma sección afirmaba que *«antes de tu primer `grep` de exploración en
una sesión»* nombraba «un momento reconocible desde fuera: o has hecho `grep` o
no». **Falso, y medido**: con el grafo fresco y el hook corriendo —las dos
hipótesis de infraestructura descartadas por la máquina— el resultado fue
**0 invocaciones de `graphify query` en 532 minutos**, contra **170 llamadas de
búsqueda** en la misma sesión.

La palabra que lo rompía era **«de exploración»**:

> *«El disparador se ancla en "tu primer `grep` de exploración", cuya frontera
> tengo que juzgar yo. Un agente que no sabe dónde está algo no se dice "voy a
> explorar": se dice **"voy a confirmar"**.»* — el agente, 2026-08-17

Un adjetivo de una sola palabra devolvió el disparador a la clase que este caso
existía para cerrar. **La cuarta vez que un disparador bien escrito no dispara.**

### La regla, ahora en su forma dura

> **Ancla en algo que se CUENTA, no en algo que se CLASIFICA.**

«La primera búsqueda de la sesión» es un **contador**: no admite adjetivo, no
tiene frontera que juzgar, y el agente sabe si va por la primera o por la
décima. «La primera búsqueda *de exploración*» es una **categoría**, y toda
categoría se evalúa desde dentro — que es donde el agente siempre tiene una
historia para no estar en ella.

Prueba barata al escribir un disparador: **táchale todos los adjetivos.** Si sin
ellos dispara demasiado, el problema no es el disparador, es que la herramienta
cuesta demasiado para dispararse siempre; arregla el coste, no la frontera.

### La ley del disparador (sprint 14)

> **Un disparador se ancla en un evento del HARNESS —arranque de sesión, uso de
> una herramienta, aparición de un fichero—, nunca en una autoevaluación del
> agente y nunca en algo que el agente no puede observar.**

Son **tres** grados, y se arreglan distinto:

| Grado | Ancla | Qué pasa | Cura |
|---|---|---|---|
| ✅ Sano | Evento del harness | Dispara siempre | — |
| ⚠ Autoevaluación | «si es complejo», «de exploración» | Dispara **a veces**, y menos de lo que crees | Quítale el adjetivo hasta que quede un contador |
| ❌ Inobservable | «si hay 2+ sesiones a la vez» | **No dispara nunca** | Reanclar a algo visible, o **quitar la condición** |

**El inobservable es el peor y no lo parece.** Una autoevaluación falla y deja
rastro raro; un inobservable **se lee como una regla cubierta** y el contrato
aparenta protección que nunca existió. El agente no puede ver otras sesiones:
no es que le cueste juzgarlo, es que ese dato no está en su mundo.

**Y la salida barata, cuando la condición no se puede evaluar: quitar la
condición.** Si una de las dos ramas es segura en TODOS los casos, esa rama es
la regla, sin `si`. Es lo que se hizo con la regla 6 del `CLAUDE.md`
(2026-08-17): decía *«si hay 2+ sesiones, escribe solo en tu nota de sesión»*, y
ahora dice *«escribe siempre en tu nota de sesión»*. La rama segura no costaba
nada —el hook `Stop` ya aceptaba las dos vías y `session-close` ya consolidaba—,
así que la condición solo servía para no cumplirse. De paso el snippet **bajó 8
tokens**: la regla inerte también se pagaba en cada proyecto.

Lo que **sí** queda observable, como red y no como disparador: `git worktree
list` enseña árboles que tú no creaste, y `Edit` fallando con *«File has been
modified since read»* es la colisión de verdad — la regla 7, que es la versión
comprobable de lo que la 6 intentaba adivinar.

### Dos parientes del inobservable, encontrados antes (2026-08-01)

Cosechados de un prompt derivado del RFD 09 —**podado el 2026-08-19**, su
texto sigue en git—. **Los dos son la misma ley vista por otro lado**, y
llegaron meses antes de que la ley se escribiera:

- **«Una marca (`harvested`) que una auditoría leía y que nadie escribía: la
  regla no podía dispararse jamás.»** El ancla existía y era observable — pero
  **nadie producía el dato**. Es el inobservable por el lado del escritor.
  → **Si defines un estado, define quién lo escribe.**
- **«Un chequeo colocado después del paso de despedida: un chequeo que nunca
  corre.»** Aquí el ancla es correcta y el problema es **dónde está puesto**.
  Un disparador sano en el sitio equivocado no dispara igual.
  → **Un check después del último paso no es un check.**

> **Y el corolario que unifica los cuatro grados:** un disparador puede fallar
> por su ancla (autoevaluación), por su dato (inobservable), por su productor
> (nadie escribe el estado) o por su posición (después del final). **Los cuatro
> se leen como cobertura**, y por eso hay que buscarlos a propósito.

### Barrido de la clase — dónde más se pide autoclasificarse

Revisadas las 29 `description:` de `setup/skills/` más las órdenes del
`CLAUDE.md` del proyecto (2026-08-17):

| Sitio | Disparador | Veredicto |
|---|---|---|
| `CLAUDE.md` · graphify | «tu primer `grep` **de exploración**» | **En clase — corregido** a «la primera búsqueda» |
| `skill-forge` · description | «or **al detectar un gap que merece** skill propia» | **En clase.** Exige juzgar que hay hueco *y* que merece skill. Nada lo cuenta |
| `CLAUDE.md` · regla 6 | «**Multi-agent** (2+ sesiones a la vez)» | **Era un INOBSERVABLE — CERRADO (2026-08-17)** quitando la condición: la rama segura pasa a ser la regla. Ver «La ley del disparador» |
| `adr-writer` · description | «(y en Graphiti **si está disponible**)» | Falso positivo: disponibilidad se comprueba, no se juzga |
| `requirements-designer` · description | «**Si aplican las dos**, brainstorming primero» | Falso positivo: regla de precedencia entre skills, no disparador |
| `session-close` · description | «el hook … **al detectar** código sin registrar» | Falso positivo, y es el buen ejemplo: quien detecta es `mark-code-dirty`, que **cuenta ediciones** |

De los dos «en clase», la **regla 6 quedó cerrada** (2026-08-17). Sigue abierto
`skill-forge`: cambiar una `description:` mueve cuándo carga la skill, y eso se
**mide** —§ «La prueba, que es barata»—, no se improvisa.

#### Pendiente medido · el recambio de `skill-forge`, listo para ejecutar

**Cambio propuesto**, en su `description:`:

```
-  ..., or al detectar un gap que merece skill propia.
+  ..., or cuando una instrucción se repite a mano por TERCERA vez en el repo.
```

«Al detectar un gap que **merece**» pide dos juicios encadenados (hay hueco · y
vale una skill). «La tercera vez» es un **contador**, y además nombra la
evidencia: si no puedes señalar las tres, no hay skill que crear.

**Las 5 frases, en sesión NUEVA y desde fuera del repo.** Las 3 primeras deben
cargar `skill-forge`; las 2 últimas **no** (son las vecinas más cercanas):

| # | Frase | Esperado |
|---|---|---|
| 1 | «la skill no dispara, arréglala» *(la petición real que falló, literal)* | **carga** |
| 2 | «llevo tres sprints copiando esta misma instrucción a mano» | **carga** |
| 3 | «crea una skill para esto» | **carga** |
| 4 | «documenta esta decisión de arquitectura» | NO (es `adr-writer`) |
| 5 | «guarda esto para que no se olvide» | NO (es `memory-keeper`) |

Se corre **antes y después** del cambio y se anotan las dos tablas. Si la 1 no
carga después, el cambio no sirve por bien escrito que esté. **Hasta que exista
esa medición, la `description` no se toca** — cambiarla a ciegas es apostar
cuándo carga una de las 39.

## Caso 2 · `requirements-designer` — la descripción que no cubría la petición real

La petición literal fue *«desarrollar el MVP de avisos por corte para Josué»*.
Los disparadores de entonces eran *«levanta los requisitos»*, *«define el
alcance»*, *«escribe la especificación»*, *«los criterios de aceptación»*:
**ninguno casa**. La skill existía, era buena y no cargó.

Lección: **priorizar algo dentro de una skill no sirve si el cambio no toca
cuándo carga.** La prioridad escrita en una skill que nadie invoca no existe.

## Cuando ensanchar el trigger pisa a una vecina

Ensanchar mete a la skill a competir con las que **sí** disparan en esa misma
frase. Entonces la desambiguación va **en la `description`**, en las palabras
del usuario y no en las nuestras — la forma que usa `workstream-merge-gate`:

- `superpowers:brainstorming` → **no sé qué construir**.
- `requirements-designer` fase 0 → **sé qué quiero y no sé si se puede**.

Y si aplican las dos, se dice cuál va primero.

## Los límites: dos unidades distintas, y un carácter que no se admite

Confundir las unidades costó una subida bloqueada (sprint 3, S1). Son medidas
diferentes de cosas diferentes y **ningún número traduce a la otra**:

| Qué | Unidad | Tope | Quién lo impone |
|---|---|---|---|
| Cuerpo del `SKILL.md` | **palabras** | ≤450 (duro 500) | nuestro, `test-skill-catalog.py` |
| `description` | **caracteres** | **≤1024** (aviso a 950) | la **especificación** de Agent Skills |
| `name` | caracteres | ≤64 | ídem |
| **Frontmatter entero** | **angulares** | **ninguno** | el parser que lee la subida |

### El tercero no es un número, y por eso se escapó dos años

**`<algo>` en el frontmatter rompe la subida.** El angular se parsea como
etiqueta abierta. `requirements-designer` llevaba `"haz X para <persona>"` entre
sus frases gatillo —una notación de hueco, escrita sin malicia— y **bloqueaba la
subida de la skill entera**.

Y no se veía, porque **Claude Code escapa los angulares de la `description`** a
propósito:

> *«in text that reaches Claude, such as the description, it also escapes angle
> brackets so the text can't imitate Claude Code's internal formatting»*

Es la **tercera vez con la misma asimetría** —el tope de 1024, el escalar plano
multilínea, y ahora esto—: Code **tolera** 1536 caracteres *y* escapa los
angulares, así que la skill carga **aquí** y falla al **subirla**. El patrón no es
el angular; es que el repo medía el lado que se ve. Lo mide el **check 5**, y
solo en el frontmatter: en el cuerpo los angulares son legítimos (`<project-name>`
en `memory-snippet.md`, `<mecánico|con juicio>` en la plantilla de despacho), y
bloquearlos ahí sería el falso positivo que acaba con el check apagado.

**El arreglo no es borrar la frase gatillo**, que es la razón de ser de la skill:
es quitarle los angulares. `<persona>` → **`Fulano`** — que en español ya se lee
como hueco *y* como nombre, así que el disparador no pierde nada y de paso se
acerca a cómo habla el usuario, que es lo que este documento pide en su primera
sección.

⚠ **Claude Code no aplica el límite de 1024.** Trunca `description` +
`when_to_use` a **1536** en el listado, y encima es configurable
(`skillListingMaxDescChars`). Así que una skill de 1074 caracteres **carga y
funciona en tu sesión** y revienta el día que la subes. Eso fue exactamente lo
que pasó con `requirements-designer` al ganar la fase 0: 1074, cincuenta por
encima, sin que nada del repo lo dijera.

**Se mide la description resuelta**, no el texto crudo: el frontmatter usa
escalares plegados (`>`), y lo que se valida es la cadena de una línea. El
arnés lo hace por ti (check 4), y en la banda 951-1024 avisa antes de cortar.

> Existe además `skills-ref validate ./mi-skill`, el validador de referencia de
> la especificación. **No está instalado en este sistema y adoptarlo es otra
> conversación** — se nombra para que sepas que el arnés no es la única fuente.

## La prueba, que es barata

3 frases que DEBEN dispararla y 2 que NO (las vecinas más cercanas), corridas en
**sesión nueva y desde fuera del repo**. Una de las 3 tiene que ser la petición
real que falló, literal — no su versión limpia. Si con esa no carga, la mejora
no sirve por bien escrita que esté.

## El coste de reputación, que no es un problema de redacción

Un disparador impecable no vence a una herramienta que se percibe lenta: en
campo se reportó que *«los hooks de graphify tardaban mucho»*. Medido en este
repo (334 ficheros, 3,1 MB, copia aislada): el **hook** de reconstrucción
(`graphify update`) tarda **5,6 s** y corre en cada commit de código; la
**consulta** (`graphify query`) tarda **0,5 s**. Son cosas distintas y la lenta
no es la que se evita — pero la resistencia se transfiere igual. Si tu skill
depende de una herramienta con hook caro, **dilo en el cuerpo y da el número de
la consulta**, o el usuario pagará el del hook en su cabeza.
