# Los 8 bloques obligatorios de todo despacho

Cada bloque corresponde a un fallo que **ya ocurrió** — los siete primeros el
2026-08-04 (`docs/subagentes/05-LIMITACIONES-OBSERVADAS.md`), el octavo el
2026-08-11, cuando las ramas sin destino declarado llegaron a 92. Ninguno es
opcional. Si uno no aplica, dilo explícitamente en el despacho en vez de
omitirlo en silencio.

---

## 1 · Contexto mínimo + brief por ARCHIVO

Una línea de contexto y el **PATH** del brief de SU tarea. **Nunca pegues el
plan completo ni mandes al subagente leerlo entero** — la regla dura de
Superpowers 6 es *"Never make a subagent read the whole plan file"*, y es de
donde sale su −60% de costo (doc 06 ①, [AR]).

```
Contexto: estamos endureciendo la compuerta de perímetro del repo X.
Tu tarea:  .superpowers/sdd/<plan>/task-3-brief.md      ← LEE SOLO ESTE
Tu carpeta: .superpowers/sdd/<plan>/frentes/3/          ← TUYA, nadie más escribe
Tu reporte: .superpowers/sdd/<plan>/frentes/3/report.md
```

**Cada frente recibe su propia subcarpeta** (`frentes/<n>/`) para predicciones,
notas y reporte. En campo un agente **sobrescribió el fichero de predicciones de
otro** por compartir ruta: fallo de montaje, no de agente. Se parcheó a media
jornada y dejó de pasar.

El reporte largo va a archivo; al coordinador vuelven ≤15 líneas (bloque 7).

---

## 2 · Estado del mundo — GENERADO, no escrito a mano

> Un brief se escribe una vez; el mundo cambia mientras el agente trabaja.

Lo que el brief **no puede saber** y hay que inyectar (doc 05 §1.3 y §3.2):

- **Ramas vivas y qué ficheros toca cada una** — otro frente puede estar en los
  tuyos.
- **Base real de la rama** (`git merge-base`), no la que asumió el plan.
- **DOS baselines de la suite**, no uno: el del **checkout principal** y el de un
  **worktree recién creado**. No son el mismo número, y esa diferencia ES el
  inventario que falta.
- **Artefactos fuera de git**: `.env`, datasets, carpetas de datos — **ruta y
  cómo obtenerlos**, no solo su nombre.
- **Flags opt-in que mueven la suite**, con su estado actual.
- **Colisiones vivas**: worktrees ocupados, ramas sin commitear en otro worktree.
- **Trampas de entorno de ese día**: tests que solo fallan en orden de suite
  completa, etc.

**Y su reverso — qué SOBRA.** Los tres rojos de la jornada 2 no fueron cosas
ausentes, fueron cosas **presentes**: un padrón que la suite no esperaba, una
variable en el `.env`, un fixture con fechas mentirosas. Preguntar solo por lo
que falta deja fuera la mitad del inventario:

- **Qué hay en disco que la suite NO espera**: padrones, datasets de pruebas
  anteriores, artefactos dejados por otro frente.
- **Qué variables de entorno están puestas** y mueven el comportamiento —
  **con su valor**, no solo su nombre. `DEBUG=1` y `DEBUG=0` no son el mismo
  inventario.
- **La mitigación, que en campo se escribió después de perder la corrida**:
  `os.environ.setdefault(...)` en `conftest.py` para **neutralizar el entorno**,
  de modo que la suite no dependa de lo que haya en la máquina.

> **El inventario no es una lista de lo que falta: es la DIFERENCIA entre la
> máquina y lo que la suite supone.**

> **El baseline no es un número: es un número más el estado de cuatro
> interruptores.** En campo, **42 de 51 skips eran una sola variable**, y
> **cuatro frentes perdieron una corrida entera** diagnosticando inventario
> ausente como daño — uno reportó 256 rojos, otro 294.

**Genéralo con comandos** (`git worktree list`, `git branch -v`, el runner de
tests en ambos sitios) y pega la salida. Escrito de memoria, este bloque miente:
los números de línea los movió la tarea anterior.

### La FIRMA del fallo del entorno, por adelantado

El inventario dice qué hay. La firma dice **cómo se ve cuando falta**, y esa es
la parte que convierte un diagnóstico en un arreglo.

> **Seis subagentes reportaron los mismos 2 tests rojos como «preexistentes».**
> No lo eran: eran **artefactos ausentes en su worktree**. A partir del quinto
> brief se les dio **la firma exacta —196 skips + esos 2 rojos concretos, con su
> nombre—** y **los siguientes la resolvieron en vez de reportarla.**

La diferencia entre los cuatro primeros y los dos últimos no fue el modelo ni la
tarea: fue una línea en el brief. Así que el bloque 2 lleva, además del
inventario:

- **La firma numérica esperada de una corrida sana**: cuántos pasan, cuántos
  fallan, **cuántos se saltan**. El conteo de skips es la señal más barata que
  existe y casi nadie la pasa.
- **La firma de los fallos de entorno CONOCIDOS**, con el nombre exacto del test
  y qué artefacto le falta:

  ```
  Si ves EXACTAMENTE estos 2 rojos:
      tests/test_carga.py::test_padron_completo
      tests/test_carga.py::test_padron_delta
  …y 196 skips, NO son preexistentes: te falta data/padron.csv en el worktree.
  Tráelo con `<comando>` y vuelve a correr ANTES de reportar nada.
  ```

- **Y la orden que lo cierra**: *un rojo que coincide con una firma conocida se
  arregla, no se reporta.* Sin esa frase el frente hace lo educado —informar— y
  te devuelve el trabajo hecho a medias.

> **Un frente que sabe cómo se ve el fallo del entorno lo arregla; uno que no,
> lo diagnostica mal y te lo devuelve como hallazgo.**

⚠ Y el reverso, para no crear el fallo opuesto: la firma es una **lista cerrada**
de fallos conocidos. Un rojo que NO esté en ella se reporta siempre — nunca se
asume que «será del entorno». Convertir la firma en una excusa genérica sería
peor que no darla.

### La regla que cierra el bloque 2: `[SUPUESTO]`

**Toda afirmación de hecho lleva su comando de verificación, o se marca
`[SUPUESTO]`** — y entonces el frente la verifica **antes** de construir encima.

```
La densidad se calcula en `metrics.py:88`  (verificado: grep -rn "densidad(" src/)
[SUPUESTO] El endpoint /v1 no tiene otros consumidores — verifícalo antes de tocarlo.
```

Es el *"greppea quién consume"* del `subagentes/05` §1.1, aplicado **al lado del
coordinador**: de diez despachos reales, **cuatro llevaban datos falsos**, y los
cuatro eran del brief, no del agente. El riesgo no es la capacidad del modelo:
es el traspaso.

---

## 3 · El fichero de decisiones del día

Ruta real, verificada contra el layout de SDD en este repo:

```
.superpowers/sdd/<plan>/decisiones-del-dia.md     ← hermano de progress.md
```

Va **aparte de `progress.md`** a propósito: el ledger es por tarea, y las
decisiones son transversales entre frentes. Mezclarlas las vuelve imposibles de
encontrar cuando un despacho dice "lee esto".

- **Su único escritor es el coordinador.** Los subagentes lo LEEN.
- El despacho **ordena leerlo** antes de empezar.
- ⚠ **Tras una compactación, el coordinador lo relee —junto con `progress.md`—
  ANTES de volver a despachar.** Sin ledger, "controllers have re-dispatched
  entire completed task sequences": el coordinador olvida qué terminó y lo
  vuelve a mandar (doc 06 ⑦).
- ⚠ El workspace está gitignorado: es andamiaje por máquina. Lo que deba
  sobrevivir a la jornada va al vault o al mensaje de commit.

Existe porque dos agentes, el mismo día y sin saber uno del otro, **ensancharon
la misma allow-list de seguridad** para que sus reportes pasaran la compuerta.
La decisión correcta era la contraria. No fue fallo de los agentes: no había
sitio compartido donde constara.

---

## 4 · Ownership y fronteras

- **Lista explícita de archivos que el subagente POSEE.** Un solo owner por
  archivo, **sin excepción** (doc 06 ②).
- **Lo compartido no se toca**: se pide al coordinador, que aplica el cambio.
- Con 2+ frentes, los **contratos de interfaz** viven en archivo aparte
  read-only; los no-owners solo importan. Cambiar el contrato = avisar al
  coordinador y a los dependientes.
- **Todo "no toques X" dice también qué SÍ se puede hacer con X.** «No borres» y
  «no modifiques» son cosas distintas, y un agente elige la lectura que le
  permite terminar (doc 05 §1.7 — pasó, y la ambigüedad era del encargo).

---

## 5 · Presupuesto con número

- **Procesos y RAM permitidos**, con cifra. Un agente aislado **no puede ver a
  sus hermanos**: lanzó carga sintética, provocó `MemoryError` en procesos
  vecinos y estuvo a punto de destruir trabajo en vuelo (doc 05 §1.8). Con ~15
  procesos simultáneos la suite pasó de 189 s a **845 s**.
- **Carga sintética prohibida** salvo autorización explícita.
- **Orden de magnitud del esfuerzo** (effort scaling, doc 06 ③): «tarea simple =
  pocos tool calls». Si vas muy por encima, **párate y repórtalo** — puede ser
  que la tarea no sea la que creías.

---

## 6 · Predicción obligatoria

Cuando el cambio pueda mover un número observable (cobertura, conteo de la
suite, filas, latencia):

> **Predice el número ANTES de medir. Mide. Si no coincide → `NEEDS_CONTEXT`,
> no sigas.**

Cuando el encargo la llevaba, el agente la verificó y reportó la coincidencia.
Cuando faltó, un cambio de umbral movió el veredicto de dos sujetos **sin que
nadie lo notara** (doc 05 §2).

Es además la única atribución que funciona: la post-hoc identifica el paso
decisivo el **14,2%** de las veces (Who&When, doc 06 §2.4 [R]).

---

## 7 · Contrato de reporte y salida

**Un commit atómico por tarea, y paso explícito de commit y push. SIEMPRE.**

Atómico porque es lo que da trazabilidad de qué agente hizo qué (GSD, doc 06 ⑩):
sin eso, reconstruirlo después es la atribución post-hoc que no funciona.

Explícito porque un agente reportó 23 ficheros arreglados y suite verde tres
veces, y **nunca commiteó** — su encargo, a diferencia de otros, no llevaba el
paso (doc 05 §1.2).

Al coordinador vuelven **≤15 líneas**:

```
ESTADO: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
COMMITS: <hash> <hash>          ← el coordinador los verifica con git log -1
REPORTE: <path del reporte largo>
RESUMEN: 2-3 líneas
CONCERNS: lo que no cuadra, si lo hay
```

**Abortar es una salida legítima, y dilo en el despacho:**

> **Mal trabajo es peor que ningún trabajo.** Si la tarea es imposible o la
> premisa es falsa, devuelve `BLOCKED`/`NEEDS_CONTEXT`: no se penaliza.

No es cortesía. En ImpossibleBench, dar la opción explícita de abortar baja el
gaming del **54% al 9%** (doc 06 §2.2 [R]).

### El criterio de salida se escribe UNA vez y sirve para dos cosas

Todo despacho dice ya cuándo está hecho. Escríbelo como **estado final medible +
el comando que lo prueba**, y ese mismo objeto vale como condición de meta si el
frente va a correr desatendido:

> **HECHO cuando** `py setup/hooks/tests/test-merge-gate-guard.py` [repo] imprime
> `23/23 casos OK`, sin tocar `sync-hooks.ps1`, **o para a los 20 turnos**.

Tres partes y ninguna sobra:

- **El comando, nombrado dentro.** Sin él la condición se satisface con una
  afirmación — y el evaluador de `/goal` **no ejecuta herramientas**: cierra
  metas leyendo lo que el propio agente dijo en el turno. *"El código queda
  limpio"* no es criterio; *"`ruff check .` sale 0"* sí.
- **Las restricciones**, lo que no debe cambiar por el camino. Es el mismo
  ownership del bloque 4, dicho en forma comprobable.
- **La cláusula de corte** (`o para a los N turnos`). Sin ella el frente no
  tiene fondo, y un bucle sin fondo gasta hasta que alguien mira.

Si el frente va a correr en `/goal`, no la escribas a ojo: fórjala con
`claude-code:goal-forge` (superficie Claude Code), que impone este contrato y
rechaza lo que solo puede satisfacer una afirmación. El hook `goal-evidence-guard`
la comprueba **contra el disco** al cerrar cada turno, así que una condición que
nombra bien su artefacto es lo que separa un frente desatendido de una máquina de
producir reportes.

Sin meta, el criterio no se pierde: se queda donde siempre, en el contrato de
reporte de arriba. Escribirlo así solo lo deja listo por si el frente se suelta.

---

## 8 · Destino de la rama — se decide AL DESPACHAR, no después

El bloque más barato de escribir y el único que se pagó en horas.

> Se llegó a **92 ramas remotas**. Bajarlas a 17 se comió una parte de la sesión
> **sin producir nada**. El diagnóstico del propio coordinador:
>
> *«El fallo no fue paralelizar: fue no incluir "qué pasa con esta rama cuando
> el frente acabe" en el propio despacho.»*

Después del hecho, la pregunta no tiene respuesta barata: para decidir si una
rama se borra hay que reconstruir qué era, si se integró, si alguien depende de
ella. Al despachar cuesta una línea, porque el contexto está delante.

**Campo obligatorio del despacho**, con uno de tres valores y nunca vacío:

```
DESTINO DE LA RAMA: se integra | se borra | se queda
  · se integra → a `main` por `workstream-merge-gate`, y la rama se borra tras
                 el squash (`git branch -D`: tras squash, `-d` no la reconoce).
  · se borra   → el trabajo es exploratorio o desechable. Di QUÉ se conserva de
                 él (el reporte, un ADR, nada) y bórrala al cerrar el frente.
  · se queda   → SOLO con dueño y fecha de revisión. Una rama que «se queda»
                 sin las dos cosas es una rama huérfana con otro nombre.
```

### Las dos reglas que lo hacen funcionar

1. **`se queda` exige dueño y fecha.** Es el valor que se elige por defecto
   cuando nadie quiere decidir, y por eso es el que necesita fricción. Sin dueño
   y sin fecha, el valor correcto es `se borra`.
2. **El destino se ejecuta al cerrar el frente, no «cuando toque».** Va en el
   mismo paso que la verificación del artefacto; si el coordinador cierra un
   frente sin ejecutar su destino, la deuda ya está creada.

### Y el remoto cuenta

Borrar la rama local no borra `origin/<rama>`. Las 92 eran **remotas**. Si el
destino es `se borra` y la rama se publicó, el cierre incluye
`git push origin --delete <rama>` — o no se ha borrado nada.
