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

  > **Por qué es obligatorio y no una formalidad, que es lo que faltaba escrito.**
  > Un worktree de agente **no nace en el HEAD de tu sesión: nace en `main`.**
  > No es un descuido de nadie, es lo que hace la herramienta —
  > `telegram-bridge/gitops.py:204-205` resuelve `default_branch(repo)` y se lo
  > pasa a `git worktree add`, y el `isolation: 'worktree'` del despacho hace lo
  > propio. Así que el agente abre los ojos en un árbol que puede estar muchos
  > commits por detrás de lo que tú acabas de escribir, **y todo lo que ve es
  > coherente**: la suite pasa, el fichero existe, el código compila. Nada le
  > dice que está mirando un repo viejo.
  >
  > De ahí que el hash vaya en el brief y no en la cabeza del coordinador: es el
  > único dato con el que el agente puede **descubrir** el desfase en vez de
  > sufrirlo. Sin él, un frente que "no encuentra" tu función recién escrita
  > diagnostica un bug donde hay un `git worktree add main`.

- **DOS baselines de la suite**, no uno: el del **checkout principal** y el de un
  **worktree recién creado**. No son el mismo número, y esa diferencia ES el
  inventario que falta.

  > **¿Y quién audita el baseline DEL COORDINADOR?** Nadie lo hacía, y ese es el
  > agujero: el coordinador declara el baseline en el brief, así que su número
  > entra como verdad en todos los frentes a la vez. En campo el suyo traía **97
  > skips donde la suite completa salta 83**, y lo destapó **un subagente
  > comparando su corrida con la declarada** — no el coordinador revisando la
  > suya. Quien mide no puede ser el único que verifica su medida.
  >
  > De ahí la regla práctica: **el brief pide al frente que reporte su conteo
  > aunque coincida.** Un frente que dice "83 skips, como el brief" cuesta una
  > línea; el que calla deja al coordinador creyendo que su número se confirmó
  > cuando nadie lo miró. Y una discrepancia entre los dos **no es ruido: es el
  > inventario apareciendo**.
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

Dicho en una línea, que es como viajaba en el cuerpo de la skill hasta que se
extrajo aquí: **sin firma, seis frentes te devuelven el mismo rojo mal
diagnosticado; un verde con skips de más no es código sano, es un artefacto que
falta.**

⚠ Y el reverso, para no crear el fallo opuesto: la firma es una **lista cerrada**
de fallos conocidos. Un rojo que NO esté en ella se reporta siempre — nunca se
asume que «será del entorno». Convertir la firma en una excusa genérica sería
peor que no darla.

### El manifiesto de lo que git NO versiona — con tamaño y origen

El inventario de arriba dice qué mirar. Esto dice **qué copiar antes de correr
nada**, y va en el despacho como tabla cerrada:

```
FUERA DE GIT (traer ANTES de la primera corrida):
  .venv/            ~400 MB   crear: <lanzador> -m venv .venv && pip install -r req.txt
  .env                 2 KB   copiar del checkout principal (NO enlazar — ver abajo)
  data/padron.csv      9,6 MB  copiar de <ruta>
  db/*.sqlite          179 MB  copiar de <ruta>
SKIPS ESPERADOS CON TODO PRESENTE: 83     ← si ves más, te falta algo
```

**El tamaño no es decoración**: es lo que distingue «cópialo» de «enlázalo» y lo
que avisa de que el frente va a tardar. 179 MB × 3 frentes es una decisión, no un
detalle.

> ⚠ **El verde silencioso.** Sin el CSV la suite **no falla: finge.** Cae a un
> dataset sintético a propósito y salta **~115 tests de más**, con exit 0.
> Descubrirlo costó **tres corridas de gate**. Un rojo se ve; un skip no.

Por eso el **conteo de skips esperado** viaja en la firma y no como comentario:
es el único detector de este fallo. La duración no lo caza —la corrida es
completa, solo que de menos cosas—, y el exit code menos aún.

### Y la decisión que faltaba: se aprovisiona el worktree, no se mueve el árbol

Estaba implícita, y lo implícito se pagó tres veces (B1 de la auditoría 22, el
CSV de hoy, y los `.venv` ausentes de once frentes). **Se decide así:**

**El frente aprovisiona su worktree con el manifiesto de arriba, y el gate corre
donde trabaja el frente.** No se centraliza en el checkout principal.

El motivo no es la comodidad, es que la alternativa es peor: correr el gate en el
checkout principal exige **hacer checkout de la rama ahí**, es decir mover el
árbol de trabajo del humano — que es exactamente lo que rompió una sesión en
directo (*«suspende los merge ahorita estoy presentando»*). Un gate que para
verificar tiene que desplazar a quien lo invoca no es una compuerta: es una
interrupción.

Tres reglas que la hacen operativa:

1. **El manifiesto es del repo, no del despacho.** Se escribe una vez y el
   despacho lo cita; si cada brief lo reinventa, se desincroniza — que es la
   enfermedad de siempre.
2. **`.env` se COPIA, nunca se enlaza.** Un symlink hace que dos frentes lean y
   escriban el mismo fichero de secretos, y basta que uno lo reescriba para
   mover el entorno del otro sin dejar rastro. Y **nunca se hace `source` de
   él** — ver las reglas de shell en `references/higiene-de-shell.md`.
3. **La primera corrida del frente valida el aprovisionamiento**, comparando su
   conteo de skips contra el declarado. Si no casa, el frente **no reporta**:
   arregla y repite.

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

## 5 · Presupuesto con número — MODELO y NÚCLEOS por frente

**El barato es el DEFECTO. El caro es el que se justifica:**

```
MODELO: barato                          ← no lleva PORQUE: es el defecto
MODELO: caro   CATEGORIA: <mecánico|con juicio>   PORQUE: <una línea>
NUCLEOS: <n>                            ← workers de test de ESTE frente
```

### El defecto por TIPO de frente, para no decidirlo ocho veces

**Por qué existe esta tabla.** Escrito arriba está que el barato es el defecto,
y aun así en la sesión del 2026-08-17 **el tier caro se llevó el 100 % de los
despachos y el barato no se usó ni una vez** — con varios frentes que eran
transcripción o arreglos mecánicos. La causa no fue desacuerdo: es que `MODELO:`
**hay que acordarse de ponerlo en cada llamada, y nada lo pide ni lo echa de
menos**. Una doctrina que depende de la memoria no es un defecto, es una
aspiración. Esto la convierte en una consulta.

| Tipo de frente | Tier | Por qué |
|---|---|---|
| Transcripción, extracción, reformateo | **barato** | La salida se compara con la entrada |
| Renombrado, mover ficheros, barrido mecánico | **barato** | Un `grep` posterior dice si quedó completo |
| Aplicar un patrón ya decidido en N sitios | **barato** | El patrón lo fijó otro; esto es ejecutarlo |
| Escribir un arnés para un contrato ya escrito | **barato** | Su mutación dice si sirve |
| Implementar con plan cerrado y suite verde | **barato** | La suite es el verificador |
| Diseño, o elegir entre enfoques | **caro** | No hay con qué comparar la salida |
| Revisión adversarial | **caro** | Su trabajo es ver lo que el otro no vio |
| Arbitraje entre dos frentes que discrepan | **caro** | Decide, y de la decisión cuelga el resto |
| Diagnóstico de un fallo que nadie entiende | **caro** | Si supieras la forma, sería mecánico |

**El corte NO es «fácil contra difícil», y confundirlo es lo que hace que todo
acabe en caro** — cualquier tarea parece difícil vista de cerca. El corte es
**si una respuesta equivocada se delata sola**:

- Arriba, equivocarse **hace ruido**: no compila, el arnés se pone rojo, el
  `grep` encuentra los sitios que faltan. Barato + verificador gana a caro sin
  verificador, y además deja evidencia.
- Abajo, una respuesta equivocada **se parece exactamente a una correcta** y
  sobrevive hasta producción. Ahí el tier es la única defensa.

Corolario práctico: **si al escribir el brief puedes nombrar el comando que
comprueba el resultado, el frente es barato.** Si no puedes, no es que sea caro
— es que el brief aún no está terminado.

⚠ **`MODELO:` ausente no es «usa el defecto»: es un brief incompleto.** Ver el
criterio de salida en `revisor.md` §0.

### El presupuesto de núcleos, y la palanca correcta

Un frente no compite solo por contexto: compite por CPU con los otros. El
reparto se decide **al despachar**, porque el número depende de cuántos frentes
haya vivos y eso no lo sabe el frente.

**No es una tabla, es una fórmula** — una tabla nace rancia en cuanto cambias de
máquina, y esta nació rancia: se escribió para 8 núcleos y la Legion tiene 24.

```
workers por frente = max(1, (os.cpu_count() - 2) // frentes_vivos)
```

Los **2 reservados** son para el coordinador y el sistema. Sale así:

| Núcleos | 1 frente | 3 frentes | 5 frentes |
|---:|---:|---:|---:|
| 8 (SER8) | `-n 6` | `-n 2` | `-n 1` |
| 24 (Legion) | `-n 22` | `-n 7` | `-n 4` |

Se calcula al despachar, con la máquina delante:

```bash
"$HOME/.claude/scripts/py" -c "import os; n=os.cpu_count(); f=3; print(f'{n} nucleos, {f} frentes -> -n {max(1,(n-2)//f)}')"
```

⚠ **La palanca es `PYTEST_XDIST_AUTO_NUM_WORKERS`, NO `taskset`.** `pytest -n
auto` **ignora la afinidad**: pregunta a psutil primero, y `psutil.cpu_count()`
no respeta `sched_getaffinity`. Verificado en laboratorio — `taskset -c 0 pytest
-n auto` sigue creando 2/2 workers mientras `len(os.sched_getaffinity(0))` vale
1. Un `taskset` puesto para acotar un frente no acota nada y da la falsa
sensación de que sí.

Y las dos reglas de configuración:

- **`-n` NUNCA en `addopts`.** Lo elige quien invoca, porque el número depende
  de cuántos frentes haya vivos — y en `addopts` se convierte en una fuga: cinco
  frentes con `-n auto` heredado son 5 × núcleos procesos de test a la vez, con
  el `auto` contando los del **host**, no los del frente.
- **`--dist loadfile` sí en `addopts`**: agrupa por fichero, así que los tests
  que comparten estado de módulo caen en el mismo worker.

⚠ **En Atloos esto no aplica hoy y conviene saberlo**: no hay `pytest.ini` ni
`addopts`, pytest-xdist **no está instalado**, y la suite (`run-tests.py`)
corre cada arnés como subproceso **serial**. La fuga se buscó y no está
(sprint 8 · S3). La regla queda escrita para los otros proyectos y para el día
que aquí se adopte xdist.

### ⚠ Un campo obligatorio no es una decisión obligatoria

Este bloque existe desde el sprint 3, está bien escrito, cita por su nombre al
coordinador que falló… y **el mismo error se repitió con la regla delante**: doce
subagentes, **los doce en el modelo caro**, incluido un *fixer* cuyas tres
quintas partes eran editar comentarios. Y el diagnóstico es otra vez del propio
coordinador:

> *«Escribí el `PORQUE:` en los doce, así que el campo se rellenó sin cumplir su
> función: si todos dicen «el caro», el campo no está eligiendo nada.»*

La corrección no es disciplina, es diseño: **invertir la carga**. Un campo neutro
se rellena con lo de siempre y el formulario queda perfecto; **uno con valor por
defecto obliga a decir por qué te sales**. Es la tercera vez que este repo
aprende lo mismo con otro disfraz — la convención escrita no muerde, y ahora
también: **un campo que acepta cualquier valor tampoco.**

⚠ Y la **CATEGORIA va escrita al lado**, no en la cabeza: es lo que permite
mirar diez despachos y ver si «con juicio» significa algo o es la casilla que se
marca siempre.

Sale de un gasto medido: **$361,77 en una sola sesión**, con el **100 %** en
sesiones con subagentes, el **79 %** en sesiones de 8 h o más, el **73 %** por
encima de 150k de contexto y el **31 %** en agentes de propósito general
(*general-purpose*, sin backticks: es un tipo de agente, no una skill). Y el
diagnóstico es del propio coordinador:

> *«No usé un modelo más barato para ningún frente, ni siquiera para los
> mecánicos. Es un fallo de diseño mío, no del harness.»*

Nada obligaba a decidirlo, así que no se decidió. Ahora se decide **antes de
despachar**, que es cuando cuesta una línea.

**La regla, ya con la carga invertida:**

- **Frente mecánico** —mover ficheros, aplicar un patrón ya definido, correr un
  barrido, renombrar, propagar un cambio decidido— → **el barato, y sin
  justificar nada**. Si el brief te dice exactamente qué hacer, no estás pagando
  por razonar.
- **Frente con juicio** —diseñar, arbitrar, auditar, decidir entre opciones,
  cualquier cosa que pueda equivocarse de forma cara— → **el caro, con su
  `PORQUE:`**. Aquí el `PORQUE:` no es burocracia: es la frase que alguien podrá
  contrastar contra lo que el frente acabó haciendo.
- **El revisor NO baja de modelo** aunque el frente que revisa sea mecánico: su
  trabajo es encontrar lo que el otro no vio, y ahí el ahorro se paga en
  hallazgos perdidos. Es la única excepción que no pide justificación.
- **Ante la duda, el caro** — pero la duda se escribe en el `PORQUE:`, para que
  la próxima vez haya un dato en vez de un reflejo.

### ⚠ Y el barato NO viene solo: va atado a la no-pérdida

El reverso está medido, y es del mismo mes. En el sprint 4 el frente mecánico
con el modelo barato **acertó los siete números y destruyó contenido**: no
extrajo, comprimió y borró. Así que las dos reglas viajan juntas o ninguna:

> **Frente mecánico con criterio de aceptación NUMÉRICO → barato **sí**, y
> entonces la cláusula de NO-PÉRDIDA es obligatoria**, con las dos medidas en el
> reporte. `references/no-perdida.md`.

Abaratar sin la segunda medida es cambiar un coste visible —la factura— por uno
invisible —el contenido que ya no está—. Ese cambio no es un ahorro.

⚠ **Aquí no van precios.** Cambian, y una tabla desactualizada en una skill es
peor que ninguna: lo que se fija es **la obligación de elegir y justificar**. Los
números del día se miran donde vivan (`/cost`, el panel), no aquí.

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

> ⚠ **`REPORTE:` hoy no se puede cumplir tal como está escrito, y está medido.**
> El harness bloqueó **5 de 5** los intentos de subagentes de escribir su
> `report.md` con `Write`. O sea que la regla *"el reporte largo va a fichero"*
> pide algo que el permiso no concede — y **no es un fallo de los agentes**.
>
> Lo que lo hace un problema de diseño y no una molestia: **el rodeo está
> siempre a una línea** (`Bash` escribe el mismo fichero que `Write` no puede) y
> **no hay ninguna regla escrita que ese rodeo desobedezca**. Es la misma
> asimetría `Write`-de-fichero-nuevo contra `Bash` que apareció en el reporte
> del 2026-08-17. Una compuerta que se salta legalmente no es una compuerta: es
> fricción que enseña a rodearla, y lo que se aprende rodeando no se desaprende.
>
> **La decisión está abierta y es de las dos que hay: o cambia la regla —el
> reporte vuelve entero al coordinador y se paga el contexto— o cambia el
> permiso.** Hasta que se tome, di en el despacho con qué herramienta esperas
> que se escriba, para que el frente no gaste una vuelta descubriéndolo.

**Abortar es una salida legítima, y dilo en el despacho:**

> **Mal trabajo es peor que ningún trabajo.** Si la tarea es imposible o la
> premisa es falsa, devuelve `BLOCKED`/`NEEDS_CONTEXT`: no se penaliza.

No es cortesía. En ImpossibleBench, dar la opción explícita de abortar baja el
gaming del **54% al 9%** (doc 06 §2.2 [R]).

### El criterio de salida se escribe UNA vez y sirve para dos cosas

Todo despacho dice ya cuándo está hecho. Escríbelo como **estado final medible +
el comando que lo prueba**, y ese mismo objeto vale como condición de meta si el
frente va a correr desatendido:

> **HECHO cuando** `setup/scripts/py setup/hooks/tests/test-merge-gate-guard.py` [repo] imprime
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

### ⚠ Si el criterio es NUMÉRICO, no viaja solo

**Un número se cumple destruyendo.** Un frente mecánico acertó los siete números
del sprint 4 —las siete skills bajo 460 palabras, `description` intacta, arnés en
exit 0— y su trabajo se descartó entero: **no extrajo, comprimió y borró**, 102
líneas sin destino. El agujero era del contrato, no del modelo.

Así que todo criterio de aceptación numérico —palabras, líneas, tamaño, tiempo—
**lleva al lado un criterio de NO-PÉRDIDA, y el frente entrega LAS DOS medidas**.
Cómo se escribe y cómo se mide (`setup/scripts/no-perdida.py`):
`references/no-perdida.md`.

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
