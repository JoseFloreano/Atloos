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
propia intención antes de actuar, y esa clasificación no ocurre. *«Antes de tu
primer `grep` de exploración en una sesión»* nombra un **momento reconocible
desde fuera**: o has hecho `grep` o no. La sustitución viaja en
`memory-snippet.md` y el arnés `test-claude-md-drift.py` caza la línea vieja por
su nombre.

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
