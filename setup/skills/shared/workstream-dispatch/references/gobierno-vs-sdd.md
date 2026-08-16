# Quién gobierna qué cuando SDD también está cargada

## El fallo, medido

`workstream-dispatch` se declaraba *«capa DELGADA sobre
`superpowers:subagent-driven-development`»*. En campo eso **no basta**, y es un
fallo de la regla W2 (dos piezas que se solapan sin árbitro declarado):

> Las dos definen el ciclo de despacho **con vocabularios distintos**, y el
> agente usó **una mezcla sin que ninguna gobernara**: **no despachó revisores
> por tarea** —lo pide SDD— y **usó 5 frentes** contra el máximo de 3 —lo pide
> esta—. **Ninguna de las dos advirtió del conflicto.**

Lo caro no fue elegir mal: fue que nadie supiera que había una elección. Una
skill que dice ser "delgada" sobre otra está describiendo su *intención de
diseño*, no dando una regla de desempate — y en la sesión real solo sirven las
reglas de desempate.

## El reparto

| Materia | Manda | Por qué |
|---|---|---|
| El **ciclo**: controller → implementer → reviewer | `superpowers:subagent-driven-development` | es su aportación original y está probada fuera de aquí |
| **Un revisor por tarea** | SDD | y **no es opcional** por estar usando esta skill |
| Los **8 bloques** del despacho | esta skill | salen de 22 despachos locales, SDD no los tiene |
| **Ownership por archivo** (un solo owner) | esta skill | |
| **Escalación** y el coordinador de juez | esta skill | |
| **Límites numéricos** (3 frentes) | esta skill | medido una vez, en OTRO proyecto — ver abajo |
| Cualquier número en el que discrepen | **el más restrictivo** | la regla de desempate general |

## Las dos afirmaciones que hay que poder repetir

1. **El revisor por tarea de SDD sigue siendo obligatorio.** Usar esta skill no
   sustituye la revisión: la revisión es del ciclo, y el ciclo es de SDD. Un
   despacho sin revisor está incompleto aunque los 8 bloques estén perfectos.
2. **El máximo de 3 frentes no lo relaja SDD.** SDD no fija un techo porque no
   conoce tu máquina; esta skill pone uno con fecha (ver abajo), y quien quiera
   subirlo lo sube **midiendo**, no discutiendo.

## El 3 es un dato con fecha, no un criterio

No es una preferencia estética ni una regla de prudencia genérica; pero tampoco
es un techo demostrado. Es **una medición del 2026-08-10, autorreportada y sin
repetir**, y **de la suite de otro proyecto**:

| Frentes | Duración de la suite | Factor |
|---:|---:|---:|
| 3 | ~330 s | — |
| **5** | **677 s** | **×2,05** |

Y además, con 5 frentes **una prueba de latencia falló por carga, no por
código** — un rojo que costó diagnosticar y que no tenía nada que arreglar.

⚠ **Sus tres grietas** (`references/medir-el-techo.md`): el ×2,05 **no es de
este repo** —mide una suite de pytest de ~3 960 tests en otro proyecto, mientras
la de Atloos son 18 arneses seriales de 43 s—; la **máquina no consta** y el
presupuesto supone 8 núcleos cuando `FLOREANO_LEGION` tiene **24**; y la
explicación candidata —una fuga de `-n auto`— **sigue sin comprobar**, porque el
repo donde habría que mirarla no está en esta laptop. Así que el 3 es
**conservador y provisional**, y se **revisa al cambiar de máquina o de
runner**.

Las dos consecuencias, que van juntas:

- **Paralelizar de más no acelera: multiplica el reloj de todos.** El cuello es
  la CPU y la RAM de la máquina, no la coordinación ni el modelo.
- **Bajo esa carga, un rojo puede no ser un rojo.** Enlaza con el reverso del
  criterio del reloj de `workstream-merge-gate`: el suelo de duración detecta
  verdes falsos, pero convertirlo en techo produciría rojos falsos, y con 5
  frentes ya los hay sin ayuda de nadie.

## Si te descubres eligiendo

Has entendido mal. La única elección legítima es la de la tabla; todo lo demás
es acumulación de las dos. Y si aparece un conflicto que la tabla no cubre,
eso es un hallazgo: anótalo en el fichero de decisiones del día (bloque 3) y
resuélvelo por escrito antes de despachar, no a mitad.
