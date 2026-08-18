# El contrato del revisor

El revisor es la pieza que más defectos encontró el 2026-08-04. También la que
más fácil se degrada si se despacha mal.

---

## 0 · Antes de revisar nada: el brief sin `MODELO:` se RECHAZA

**Criterio de salida, no costumbre.** Si el brief que despachó ese frente no
trae la línea `MODELO:`, el revisor **devuelve el brief y no revisa**. Un brief
incompleto no se arregla revisando lo que produjo.

Por qué es del revisor y no del coordinador: el coordinador es justo quien
acaba de olvidarlo. En la sesión del 2026-08-17 el tier caro se llevó **el
100 %** de los despachos y el barato **no se usó ni una vez**, con frentes que
eran transcripción — y no por desacuerdo con la doctrina, que ya estaba
escrita, sino porque `MODELO:` **hay que acordarse de ponerlo y nada lo echaba
de menos**. Esto es lo que lo echa de menos.

Los tres defectos que rechaza, y solo estos tres:

1. **No hay línea `MODELO:`.** Ausente ≠ «usa el defecto»: es un hueco.
2. **`MODELO: caro` sin `CATEGORIA:` ni `PORQUE:`.** El caro se justifica; si
   no, la justificación es «me salió así».
3. **`MODELO: barato` con `PORQUE:`.** Señal de que se copió la línea de otro
   frente sin leerla — el barato es el defecto y no lleva justificación.

La tabla de defectos por tipo de frente está en `plantilla-despacho.md` §5. Y
su atajo sirve también aquí: **si el brief nombra el comando que comprueba el
resultado, el frente es barato**; si no lo nombra, lo que falta no es el tier,
es el criterio de terminado.

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

## 1b · La enfermedad CONTRARIA: el test que no puede pasar

§1 caza el test que **no puede fallar**. Pide también el simétrico, porque el
mismo instrumento apunta en las dos direcciones y **solo se usaba en una**:

> **"Revierte al comportamiento CORRECTO y enséñame que el test sale VERDE.
> Si sigue rojo sobre código bueno, el test es el defecto."**

El 2026-08-14, pedirlo explícitamente destapó **dos tests que salían rojos en
falso**. No los habría encontrado nadie: un rojo no despierta sospecha, se
atribuye al código y se "arregla" tocando lo que estaba bien.

**Por qué cuesta lo mismo que un verde falso, y no menos.** Un verde falso deja
pasar un defecto una vez. Un rojo falso enseña a desconfiar de la compuerta, y
una compuerta de la que se desconfía se desactiva —está escrito para el reloj en
`criterio-del-reloj.md`: *"Un gate que grita en falso se desactiva, y entonces
no queda gate"*—. El daño del primero es un bug; el del segundo es quedarse sin
el instrumento.

Los dos defectos van al veredicto con la misma severidad y con su `file:line`.
Un test demasiado estricto **no** es "mejor pasarse de cauto": es un test que no
mide lo que dice medir, igual que el que se autosatisface con el nombre del
`def`.

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
