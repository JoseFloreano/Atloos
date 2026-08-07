# El contrato del revisor

El revisor es la pieza que más defectos encontró el 2026-08-04. También la que
más fácil se degrada si se despacha mal.

---

## 1 · Mutar, no opinar

**No** pidas "revisa si el test es bueno". Pide:

> **"Aplica esta mutación al código y enséñame que el test sale ROJO.
> Después revierte y confirma que no queda residuo."**

Con esa instrucción se cazaron **4 de las 6** compuertas vacías de ese día
(doc 05 §3.8). Las seis eran tests que no podían fallar:

- un barrido que reventaba con `UnicodeDecodeError` antes de mirar nada;
- un `isinstance(r, APIRoute)` que en ese FastAPI veía **cero** rutas;
- el "test que prueba que el test puede fallar": **tres constantes** comparadas
  entre sí;
- un test de frontera verde ante un mutante `abs()` plausible;
- un assert que **se autosatisfacía con el nombre del `def`**;
- un test verde aunque las dos compuertas apuntaran a la misma constante.

Ninguna se caza leyendo. Todas se cazan ejecutando. Es la diferencia medida
entre un juez LLM puro (<42% de acuerdo con ground truth) y uno con ejecución
de código (~72%) [R].

---

> **Esto aplica igual a un DISEÑO, no solo a código.** Auditar un diseño
> aprobado antes de escribir el spec es el mismo patrón —contexto limpio, no
> confiar en el reporte— una fase antes. Ahí la "mutación" es atacar la
> afirmación: *¿qué comando demostraría que esta carga es la que dice?*

## 2 · Contexto limpio

El revisor **NO recibe el razonamiento del implementador**. Recibe:

- el **brief** de la tarea,
- el **diff real** (empaquetado a archivo, que nunca entró al contexto del
  coordinador),
- el **reporte del implementador tratado como afirmaciones sin verificar**.

Dilo literal en el despacho: **"Do not trust the report — trátalo como claims
sin verificar."**

El crítico rinde **mejor** limpio (Cognition, doc 06 §3). Y el matiz que la
convergencia de 2026 dejó claro: *"comparte contexto completo" aplica a quien
ESCRIBE; su inverso aplica a quien VERIFICA.*

---

## 3 · Si el implementador tocó un test o un fixture

Es el **disparador 6** de la escalación, y aquí es donde se decide si fue
legítimo. **Los tres criterios** (doc 05 §1.6):

1. ¿Alguno de esos tests existía para fijar **el borde de lo que cambió**?
2. ¿El fixture nuevo **pierde poder de discriminación**?
3. ¿Se tocó solo el **dato de entrada**, o también la **lógica**?

**Sin estos tres criterios la revisión es una opinión; con ellos es una
comprobación.** El caso real: un agente cambió un fixture para que nueve tests
siguieran pasando tras subir un umbral —huele a "ajusto el test hasta que
pase"— y la revisión lo **exoneró** aplicándolos.

Complemento estructural (doc 06 ⑤): lo ideal es que el verde venga de tests que
el implementador **no escribió ni pudo editar**. Forzar al agente a escribir sus
propios tests da **cambio neto cero** en éxito — son print-debugging (25 prints
vs 5,2 asserts por tarea) [AR].

---

## 4 · El tiempo de ejecución es una señal

**Repórtalo siempre.** Una corrida imposiblemente rápida o absurdamente lenta
contra el histórico es el **detector de errores más barato** que hubo ese día, y
no estaba en ninguna skill.

- **3,6 segundos** contra 1,5 M de filas destapó un script de medición que no
  llamaba a `load_dotenv()` y comparaba MySQL contra un fixture CSV. Su
  conclusión falsa —"18 de 18 semanas movidas"— habría redirigido el diseño.
- **845 s** donde suelen ser 189 destapó la saturación de la máquina, que otro
  agente estuvo a punto de diagnosticar como bug de concurrencia.

Si el número no es plausible, **no es verde**: investiga antes de aprobar.

---

## Veredicto

Doble, como el reviewer de SDD, con `file:line` obligatorio en cada issue:

- **Spec Compliance:** ✅ / ❌ / ⚠️ — ¿hace lo que el brief pedía?
- **Task Quality:** Approved / Needs-fixes — ¿está bien hecho?

Un issue sin `file:line` no es accionable y no cuenta.
