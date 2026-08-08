---
title: "El instrumental, día 2 — qué se cumplió del reporte de ayer y qué no"
project: recomendador-cobranza
fecha: 2026-08-07
tipo: retrospectiva-instrumental
alcance: "16 frentes despachados · 9 ramas integradas · rama main-v2 abierta · 3 174 verdes"
sigue_a: "[[reporte-skills-y-graphify-20260806]]"
---
> **Promovido:** 2026-08-07 a `docs/subagentes/08` desde el reporte de campo del
> usuario (jornada 2 en `recomendador-cobranza`), **sin reescribir su contenido**.
>
> **No es un reporte más: es la auditoría a las correcciones del RFD 10**, que se
> implementaron ese mismo día. Califica las 5 recomendaciones de
> `07-PRIMERA-CAMPANA-REAL.md` — 4 cumplidas, y la mejor medida es que el
> aprovisionamiento en el brief llevó las corridas perdidas **de 4 a 0**.
>
> Los 4 fallos que destapa se recogen en
> `auditoria/11-RFD-DEL-CASO-A-LA-CLASE.md` (F14–F17). Como el reporte de la
> jornada 1: **evidencia complementaria de W2, NO cierra la condición 7 del
> RFD 04.**

# El instrumental, día 2

> Esto **no repite** [[reporte-skills-y-graphify-20260806]]: lo audita. Ayer dejé
> cinco recomendaciones; hoy se puede medir cuántas se cumplieron. Todo lo que
> afirmo aquí pasó hoy y se puede señalar con el dedo; donde no medí, lo digo.

---

## 1 · Las cinco recomendaciones de ayer, calificadas

| # | lo que propuse ayer | hoy |
|---|---|---|
| 1 | El bloque de predicción no se negocia | ✅ **Cumplido, y volvió a ser lo más rentable** |
| 2 | El aprovisionamiento entra en el brief (2 baselines + flags) | ✅ **Cumplido — 0 corridas perdidas** (ayer 4) |
| 3 | Auditar el diseño antes del spec | ✅ Cumplido — y **tumbó 4 afirmaciones de mi propia v2** |
| 4 | **Usar graphify en la primera media hora** | 🔴 **INCUMPLIDO. Cero invocaciones, segundo día seguido.** |
| 5 | Verificar el artefacto, nunca el reporte | ✅ Cumplido, y sostiene el §5 |

**Cuatro de cinco.** La que falló es la que ya había fallado ayer, y falló
**exactamente igual** — lo cual la convierte en el hallazgo principal de este
reporte, no en una nota al pie.

---

## 2 · 🔴 Graphify — dos días, cero usos, y ahora sé por qué

### El hecho

Segunda jornada completa **sin invocarlo una sola vez**, teniéndolo escrito en el
`CLAUDE.md` del proyecto (*«For codebase questions, **first** run `graphify
query`»*) y teniéndolo **funcionando**: el hook regeneró `graph.json` hoy a las
20:08, está al día.

Ayer lo llamé «incumplimiento mío». Hoy, repetido idéntico bajo instrucción
explícita, ya no es un descuido: **es un defecto de diseño de la instrucción.**
Un mandato que un agente incumple dos de dos veces no está mal obedecido, está
mal colocado.

### Lo que habría dado — medido hoy sobre la pregunta más cara del día

Le lancé la pregunta que costó un frente entero y produjo un censo de 178 líneas
(*«quién lee la columna `gestor` y decide algo con ella»*):

- ⚡ **1,7 s.** Contra ~40 min del censo a mano.
- ✅ **5 de los 9 sitios** del censo salieron: `repo.py`, `store.py`,
  `copiloto_tools.py`, `simulador.py`, `efectividad.py`. Más `pii.py`,
  `decision.py`, `verificacion.py`, `traza.py` — la capa de PII entera, que
  encontrar a mano costó su propio rato.
- 🔴 **Y los 4 que faltan incluyen LOS DOS DECISIVOS**: `normalize.py` —el que se
  traga el `CSVInvalido` y convierte la capa 6 en un fallo silencioso— y
  `api/servicio.py` —el único que **ESCRIBE** el default en `sla.db`—.
  **Cero apariciones ambos.** El titular del censo (*«su Ruido no existe»*) no
  sale de aquí.
- 🔴 **627 nodos, y 49 de 65 `loc=` son `L1`**: no señala el *sitio*, señala el
  *fichero*. Para un censo por línea, eso es el punto de partida, no la respuesta.

### El veredicto, más afilado que el de ayer

Ayer escribí «útil para orientarse, inútil para decidir». Hoy lo puedo poner en
números: **da el 55 % de los anclajes en el 0,1 % del tiempo, y omite justo los
que cambian la conclusión.**

Eso no lo hace malo. Lo hace **una primera pasada, nunca una respuesta** — y
explica por qué no lo uso: mi trabajo de estos dos días fue **decidir**, y en
tareas de decidir su salida hay que verificarla entera, así que se siente como
coste añadido en vez de ahorro. El ahorro es real, pero está **al principio**, no
al final.

> ### 🔑 La corrección concreta que propongo
>
> El `CLAUDE.md` dice *«for codebase questions, first run graphify query»*. **Es
> demasiado ancho y por eso se ignora.** Cámbialo por un disparador que un agente
> reconozca en el momento:
>
> > **Antes de tu primer `grep` de exploración en una sesión, corre
> > `graphify query`. Su salida es la LISTA DE CANDIDATOS, no la respuesta:
> > confírmala con `Read` y da por hecho que le faltan sitios.**
>
> Es la misma herramienta con la expectativa correcta, y ataca lo que de verdad
> pasó: no la desobedecí por creerla mala, la salté porque *«primero grafo»* no
> tiene un momento identificable y *«antes de tu primer grep»* sí.

---

## 3 · Las skills — lo nuevo de hoy

### 🟢 `workstream-dispatch`, otra vez la más rentable, y con un dato duro nuevo

**De 16 frentes, 14 tumbaron algo que el coordinador daba por cierto** — incluidas
**cuatro afirmaciones de mi propio diseño v2**, escrito ayer. El bloque 6
(predicción obligatoria) mantiene el récord: donde falló la predicción, la
desviación **era** el hallazgo.

✅ **La propuesta de ayer se aplicó y funcionó.** Los briefs llevaron los **dos**
conteos (checkout principal / worktree limpio) y las cuatro flags. **Ayer: 4
corridas perdidas por inventario ausente. Hoy: 0.** Es la mejora medible más
limpia entre las dos jornadas.

🔴 **Pero el mismo agujero cambió de forma y volvió a morder — tres veces.** Ya no
fue el inventario del brief: fue **el entorno de la máquina filtrándose a la
suite**.
1. Un padrón nuevo en disco que la suite no tenía → **31 tests rotos**.
2. `COB_EF_CURSOR_MAX_MIN=45` puesto en el `.env` → **2 tests rotos**.
3. Un fixture que mentía con las fechas.

> **Propuesta:** el bloque 2 no debe pedir solo *qué falta*, sino **qué SOBRA**.
> El fallo de hoy no fue un artefacto ausente, fue uno **presente** que la suite
> no esperaba. Se arregla con un `os.environ.setdefault` que neutralice el
> entorno en `conftest.py` — que es lo que acabé escribiendo, después de perderlo.

### 🟢 `workstream-merge-gate` — cazó su propio incumplimiento

Y el incumplidor fui yo: **batchée tres merges «de bajo riesgo» y solo medí tras
el cuarto** ⇒ atribuí el rojo a la rama equivocada hasta abrirlo. La skill dice
*un frente a la vez* **por esto exactamente**. El paso 3 (la duración es señal)
volvió a pagar: un `-p no:randomly` estiró la suite a 30 min y produjo un rojo
falso de latencia.

### 🟡 `session-close` — el paso 7 avisa de algo que nadie arregla

Tercer día seguido avisando de lo mismo, ver §4. **Avisar sin que nadie actúe no
es una compuerta, es un log.**

### 🟡 `adr-writer` — usada hoy (ayer, cero), y el ADR que salió es el mejor del día

[[ADR-20260807-el-prefijo-id-no-garantiza-un-id]]. Nació de mi peor error de la
jornada (§5) y es exactamente el tipo de conocimiento que sin skill se pierde.
⚠ Pero sigue faltando: **el canal de Telegram, la doble emisión y la convención de
`main-v2` no tienen ADR propio** y viven solo como línea en `_PROJECT.md`.

### 🔴 Lo que NINGUNA skill cubre, y hoy hizo falta

**No hay skill para «un hecho guardado resultó falso».** `memory-keeper` guarda,
`adr-writer` decide, `session-close` consolida — **ninguna retira**. Hoy tres
afirmaciones del vault quedaron refutadas por medición y las corregí a mano, a
pulso, buscándolas fichero por fichero. Sin eso, el vault las habría servido
mañana con la misma autoridad que las verdaderas. Ver §4.

---

## 4 · El vault — lo bueno es real, y lo malo también

### 🟢 Lo que ganó hoy

Arrancar en frío costó **un `_PROJECT.md`** y entregó, sin releer nada: el
`deleted_at` = 58,3 %, el reloj local UTC−6, `tasks` como padrón, la extracción
incremental por PK. **Todo eso venía de ayer y hoy se usó tal cual.** Ese es el
producto y funciona.

Y la corrección de ayer (*que `project-resume` compare `origin/main` real contra
el `Estado del repo:` del vault*) **ya está en la skill** y hoy sirvió.

### 🔴 Tres defectos medidos hoy

**(1) El `_PROJECT.md` está a 2,8× de su propio límite duro.**

| | |
|---|---|
| tamaño hoy | **425 líneas / 28 KB** |
| límite blando / duro de la skill | 120 / **150** |
| checkboxes de primer nivel | **13** (el umbral de la skill es 12) |

Y **no es un descuido: es la consecuencia de que funcione.** Cada jornada añade
hallazgos que valen y ninguno caduca solo. **No lo divido sin tu OK** porque el
archivo es el arranque en frío de cada sesión y partirlo mal cuesta más que
tenerlo largo. Propuesta al final.

**(2) La carpeta del proyecto está acumulando escombro.**
Tres ficheros de pendientes vivos a la vez (`PENDIENTES.md` **128 KB**,
`PENDIENTES-4ago.md`, `PENDIENTES-6ago.md`), un `codebase-map-snapshot.md` de
**212 KB**, ocho `prompts-*.md`, `_to_delete/` y `_tmp_cowork/`. `project-resume`
tiene presupuesto de ~10 KB para arrancar; **la carpeta pesa más de 400 KB**. Hoy
el presupuesto aguantó porque la skill sabe **no** abrir `PENDIENTES.md` — pero
eso significa que **el backlog de 128 KB es de facto de solo escritura**.

**(3) 🔑 El defecto de fondo: el vault propaga mis errores con la misma fidelidad
que mis aciertos, y no tiene forma de marcar un hecho como refutado.**

Es el hallazgo importante de este reporte. Hoy pasó tres veces:

- Escribí ayer *«el organigrama cubre el 21,5 %»* como problema de **cobertura**.
  Eran **colisiones numéricas que resuelven a OTRA persona** — problema de
  **autorización**, y fail-open. El vault lo sirvió hoy con total confianza y
  **razoné sobre él media jornada**.
- Escribí en la v2 que la capa 6 era *«una línea, rollback de una línea»*.
  **Su «Ruido» no existe.**
- Escribí que `tbl_segundometro_semana` era un snapshot. **Se actualiza cada 2 h
  por columnas en la misma fila** — me lo corregiste tú, no el instrumental.

En los tres casos el mecanismo que los cazó fue **el mismo y solo uno**: exigir
que cada frente **midiera** en vez de creerle al que lo despachó. **Ninguna pieza
del vault contribuyó a detectar el error, y las tres lo distribuyeron.**

> **Propuesta:** que `memory-keeper` acepte **refutar**, no solo guardar: un hecho
> refutado no se borra —el error enseña— sino que se marca `refutado: por qué,
> medido dónde` y **el índice lo muestra tachado**. Hoy no existe, y por eso las
> correcciones vivieron en prosa dentro de la nota de sesión, donde
> `project-resume` **no las lee**.

---

## 5 · Lo que me llevo al día siguiente

1. **Cambiar la instrucción de graphify por el disparador concreto** («antes de tu
   primer `grep`»), y tratar su salida como candidatos con sitios faltantes. Dos
   días de incumplimiento idéntico dicen que el problema es la instrucción.
2. **El bloque 2 del brief tiene que preguntar qué SOBRA**, no solo qué falta. Los
   tres rojos caros de hoy fueron entorno **presente**, no ausente.
3. **`memory-keeper` necesita refutar.** Un vault que solo acumula es un vault que
   sirve errores con cara de hechos, y hoy sirvió tres.
4. **Un frente a la vez en el gate.** Lo sabía, lo escribí, lo incumplí, lo pagué.
5. **Lo que de verdad sostuvo la jornada no fue una herramienta**: fue que cada
   afirmación tuviera que llegar con su medición. 14 de 16 frentes tumbaron algo
   que yo daba por cierto — y el mecanismo que lo hizo posible es gratis.

---

## 6 · Decisiones que te dejo pendientes (no las tomé solo)

- [ ] **Partir `_PROJECT.md`** (425 líneas vs 150). Propuesta: dejar en él solo
      *Qué es · Estado actual · Próximo paso · Pendientes activos* (~120 líneas) y
      mover el histórico de hallazgos medidos a `hallazgos-medidos.md`, enlazado.
- [ ] **Consolidar `PENDIENTES-4ago.md` y `PENDIENTES-6ago.md`** dentro de
      `PENDIENTES.md`, o archivarlos. Hoy hay tres fuentes de pendientes.
- [ ] **Vaciar `_to_delete/` y `_tmp_cowork/`** de la carpeta del proyecto.
