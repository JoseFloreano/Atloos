# Limitaciones y puntos débiles de los subagentes

> **Promovido:** 2026-08-05 a `docs/subagentes/05` desde el doc de trabajo del
> usuario (2026-08-04), sin reescribir su contenido. Su **§3** es la
> especificación de las skills de la fase W2 del RFD 04. La investigación
> externa que lo complementa (y coincide con su taxonomía) es el doc 06.

**Fecha:** 4 ago 2026 · **Base empírica:** una jornada con **22 despachos** —implementadores,
revisores, arregladores y pases de medición— sobre dos planes y ocho ramas fusionadas.

> **Para qué es este documento:** no es una queja ni una lista de buenas prácticas genéricas.
> Es el registro de **qué falló de verdad**, con el caso concreto al lado, para poder decidir
> qué cambiar en las skills. Todo lo que sigue ocurrió; nada es hipotético.

---

## 0 · La conclusión, primero

**El desfase casi nunca vino de la capacidad del modelo. Vino del traspaso.**

El error más caro del día —un plan de siete tareas que modificaba un módulo que la compuerta
no lee— lo cometió el **autor del plan**, no quien lo ejecutó. Un modelo más capaz con el
mismo brief habría hecho el mismo trabajo inútil, solo que más caro.

Corolario incómodo, con evidencia: **el peor test del día lo escribió el modelo más capaz**
(un «test que prueba que el test puede fallar» que resultaron ser tres constantes comparadas
entre sí), y **los mejores hallazgos salieron del modelo barato** (la contaminación de
`os.environ`; la negativa a fingir un arreglo de un flaky).

---

## 1 · Taxonomía de fallos observados

### 1.1 🔴 El brief con premisa falsa

**Caso:** el plan v1 daba por hecho que la densidad se calculaba en un solo sitio. Había
**dos implementaciones divergidas**, y la compuerta solo leía una. Tres de sus siete tareas
—incluida una recalibración— habrían trabajado sobre código muerto.

**Causa:** el autor leyó un módulo, lo tomó por *el* módulo, y **nunca hizo `grep` de quién
consume el valor que iba a cambiar**.

**Coste:** el plan entero reescrito antes de ejecutarse. Lo cazó una auditoría externa, no
el proceso.

> **Regla que faltaba:** *antes de cambiar el valor de un campo, greppea quién lo consume.*
> Una vez añadida, la siguiente tarea encontró **cuatro consumidores** que el plan no listaba.

### 1.2 🔴 El reporte sin artefacto

**Dos veces el mismo día:**

- Un agente reportó su tarea completa; **el fichero de reporte nunca se escribió** (puso el
  contenido en otro sitio). Despaché la revisión con una entrada inexistente.
- Otro reportó el trabajo terminado —23 ficheros arreglados, suite verde tres veces— y
  **nunca commiteó**. La rama seguía en `main`.

**Causa raíz distinta en cada uno:** el primero, ambigüedad sobre dónde va el reporte; el
segundo, **el encargo no llevaba un paso explícito de «commit y push»** mientras que otros
encargos sí.

> **Regla:** *verificar el artefacto, no el reporte.* Un `git log -1` y un `Test-Path` cuestan
> una llamada. **Es el mismo patrón que perseguimos en el código —la compuerta que pasa en
> vacío— con el coordinador de compuerta.**

### 1.3 🟠 El contexto que el brief no puede saber

Un brief se escribe una vez; el mundo cambia mientras el agente trabaja. Casos reales:

| lo que el brief no sabía | consecuencia |
|---|---|
| la ruta del worktree **ya estaba ocupada** por otro agente vivo | `git worktree add` habría fallado |
| la rama que le mandaban consultar **estaba sin commitear** en otro worktree | no habría encontrado nada |
| los **números de línea** los había movido la tarea anterior | referencias muertas |
| tres tests fallan **solo en orden de suite completa** | habría diagnosticado un repo roto |
| un worktree nuevo da **~256 fallos** hasta copiar 4 artefactos fuera de git | ídem |

> **Lo que más desfases evitó, medido a ojo por frecuencia de uso:** un bloque fijo de
> **«lo que el brief no puede saber»** en cada despacho, con colisiones vivas, estado real de
> la rama y convenciones aprendidas ese mismo día. Es gratis y debería ser obligatorio.

### 1.4 🟠 La deriva entre agentes paralelos

**Caso:** dos agentes, el mismo día, **ensancharon la misma allow-list de seguridad** para
que sus respectivos reportes pasaran la compuerta de perímetro. Ninguno sabía del otro. La
decisión correcta era la contraria —renombrar el fichero para cumplir la convención—, y cada
ensanchamiento afloja una compuerta que existe precisamente por su fricción.

> **El fallo no es de los agentes: es que no había un sitio compartido donde constaran las
> decisiones tomadas ese día.** Un fichero de decisiones vivas que cada despacho referencie
> lo habría evitado.

### 1.5 🟠 El test que no puede fallar

**Seis casos en un día**, escritos por modelos de las dos gamas:

1. Un barrido que **reventaba con `UnicodeDecodeError`** al entrar en `.venv`, antes de mirar nada.
2. Un test de perímetro que usa `isinstance(r, APIRoute)` y en ese FastAPI ve **cero rutas**.
3. El «test que prueba que el test puede fallar»: **tres constantes** comparadas entre sí.
4. Un test de frontera que pasaba verde ante un mutante `abs()` plausible.
5. Un assert que **se autosatisfacía con el nombre del `def`** (`inspect.getsource` incluye la firma).
6. Un test que seguía verde si alguien apuntaba **las dos** compuertas a la misma constante.

> **El único remedio que funcionó: instruir al revisor a MUTAR el código y confirmar el
> rojo.** No «revisa si el test es bueno» — *aplica esta mutación y enséñame que sale rojo*.
> Con esa instrucción se cazaron cuatro de los seis.

### 1.6 🟠 El alcance que se estira, y por qué no siempre es malo

Un agente cambió un **fixture de test** para que nueve tests siguieran pasando tras subir un
umbral. Huele exactamente a *«ajusto el test hasta que pase»*.

**La revisión lo exoneró** con tres criterios que vale la pena reutilizar:

1. ¿Alguno de esos tests existía para fijar **el borde** de lo que cambió?
2. ¿El fixture nuevo **pierde poder de discriminación**?
3. ¿Se tocó solo el **dato de entrada** o también la lógica?

> Sin esos tres criterios, la revisión es una opinión. Con ellos, es una comprobación.

### 1.7 🟠 La acción destructiva que se descubre en el reporte

Un agente modificó **tres ficheros preexistentes** que el encargo marcaba como intocables, y
lo declaró **pidiendo permiso retroactivo**. Verificado, resultó estar dentro de la letra del
encargo («los inmaduros se marcan, no se borran») y no perdió datos — pero la ambigüedad la
escribí yo.

> **Regla:** cuando un encargo diga «no toques X», decir también **qué sí se puede hacer con
> X**. «No borres» y «no modifiques» son cosas distintas, y un agente elige la lectura que le
> permite terminar.

### 1.8 🟠 Los recursos compartidos

Un agente lanzó carga sintética —60 copias y decenas de hilos ocupados— para reproducir un
fallo bajo carga. **Provocó `MemoryError` en procesos hermanos** y estuvo a punto de destruir
trabajo en vuelo. Lo detectó, los mató y **lo reportó**.

Con ~15 procesos simultáneos se midió una suite de **845 s contra 189 s** habituales, y un
`integrity_check` de sqlite cayendo por inanición — que otro agente estuvo a punto de
diagnosticar como bug de concurrencia.

> **Regla:** el presupuesto de máquina va **en el encargo**, con número. Y prohibir carga
> sintética salvo autorización explícita: un agente aislado **no puede ver** a sus hermanos.

### 1.9 🟡 La medición circular

Un pase de medición preguntó *«¿todos estos créditos tienen dueño resoluble?»* sobre un
conjunto **ya filtrado por esos mismos dueños**. Salía 100 % trivialmente. **El propio agente
lo cazó y lo rehízo** — pero solo porque el resultado le pareció demasiado limpio.

### 1.10 🟡 El instrumento contaminado

Un script de medición **no llamaba a `load_dotenv()`**, así que comparó datos de MySQL contra
un fixture CSV y produjo *«18 de 18 semanas movidas»* — una conclusión que habría redirigido
el diseño entero.

> 🔑 **Lo cazó el TIEMPO DE EJECUCIÓN: 3,6 segundos es imposible contra 1,5 M de filas.**
> El mismo detector salvó otro pase (845 s donde suelen ser 189). **La duración de una corrida
> resultó ser el detector de errores más barato de la jornada**, y no está en ninguna skill.

---

## 2 · Lo que sí funcionó

| mecanismo | evidencia |
|---|---|
| **Válvulas «párate y dilo»** | Se usaron bien **cuatro veces**: un agente devolvió `NEEDS_CONTEXT` con cuatro preguntas en vez de adivinar; otro se negó a fingir el arreglo de un flaky; otro paró al ver que la premisa del encargo era falsa. |
| **Predicción antes de medir** | Cuando el encargo llevaba la predicción escrita, el agente la verificó y reportó la coincidencia. Cuando faltó, un cambio de umbral movió el veredicto de dos sujetos **sin que nadie lo notara** hasta que lo midió el coordinador. |
| **Revisor con permiso para mutar** | Cazó 4 de las 6 compuertas vacías. Un revisor **repitió la mutación por su cuenta** en vez de fiarse del reporte, y comprobó que el revert no dejaba residuo. |
| **Prohibir el atajo por nombre** | «Nada de `sleep`, reintentos, `xfail` ni subir timeouts» produjo un reporte honesto de *«no encontré causa raíz»* en vez de un parche que la escondiera. |
| **Aislamiento por worktree** | Ocho ramas en paralelo sin un solo conflicto de código. Lo que sí colisionó fue **lo compartido**: `.git`, la máquina, y las convenciones. |

---

## 3 · Qué cambiaría en las skills

**Del lado del coordinador:**

1. **Checklist de verificación de artefacto** antes de encadenar: rama tiene commits, fichero
   de reporte existe, worktree limpio. Hoy fallé esto **dos veces**.
2. **Bloque obligatorio de «estado del mundo»** en cada despacho, generado y no escrito a mano:
   ramas vivas y qué ficheros tocan, base real, conteo de la suite, trampas de entorno.
3. **Fichero de decisiones del día** que todo despacho referencie. Habría evitado que dos
   agentes tomaran la decisión contraria sobre la misma compuerta.
4. **Presupuesto de recursos con número** en el encargo, y prohibición de carga sintética.

**Del lado del contrato del implementador:**

5. **Paso explícito de commit y push, siempre**, y que el reporte devuelva **hashes** — que el
   coordinador verifica.
6. **«No toques X» debe decir qué SÍ se puede hacer con X.**
7. **Predicción obligatoria** cuando el cambio pueda mover un número observable: *predice,
   mide, y si no coincide, párate.*

**Del lado del revisor:**

8. **Instrucción de mutar, no de opinar.** «Aplica esta mutación y enséñame el rojo» es lo que
   más defectos encontró hoy, con diferencia.
9. **Los tres criterios del §1.6** cuando el implementador tocó un test.

**Transversal:**

10. **Enseñar el tiempo de ejecución como señal.** Una corrida imposiblemente rápida o
    absurdamente lenta es un detector de errores gratis, y hoy salvó dos conclusiones falsas.

---

## 4 · Lo que NO recomendaría cambiar

- **Escalonar modelos por complejidad**: hacerlo está bien y ahorra, pero **no es la palanca
  del desfase**. Hoy la evidencia va en las dos direcciones.
- **Meter más agentes en paralelo**: el techo real no fue el modelo ni la coordinación, fue la
  **memoria de la máquina**.
- **Alargar los briefs**: los que fallaron no eran cortos, eran **incompletos en un punto
  concreto** — casi siempre algo que había cambiado esa misma tarde.
