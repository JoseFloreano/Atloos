---
title: RFD 36 — El anti-drift y los gates contra el modo concurrente: dos comprobaciones que no pueden pasar donde más falta hacen
tags: [rfd, hooks, anti-drift, gate, multiagente, paralelismo, worktree]
created: 2026-08-18
updated: 2026-08-18
status: propuesto
type: rfd
project: atloos
decisiones: [D28, D29, D30, D31, D32]
---

# RFD 36 — Dos comprobaciones que no pueden pasar en el escenario para el que existen

> Leyenda: `[H]` lo midió el humano · `[C]` leído del código, con fichero y línea
> · `[AR]` inferencia del agente, no comprobada con un comando.

**El patrón, dicho una vez:** este repo lleva la jornada cazando comprobaciones
que se diseñaron para la sesión solitaria y se ejercen en un mundo concurrente.
Aquí está el mismo defecto **en la propia infraestructura de vigilancia**: el
anti-drift del vault y el gate de merge. Los dos son correctos en el escenario
que suponen y ninguno de los dos puede pasar en el que este proyecto usa de
verdad — trabajo autónomo con hasta 3 frentes, que es precisamente cuando no hay
nadie mirando.

Este documento **no ejecuta nada**. Es lectura, diagnóstico y propuesta, con las
mediciones que hay que hacer antes de tocar código de la máquina que vigila los
merges.

---

## 0 · La medición que lo abre

**[H]** Con un coordinador y tres subagentes vivos:

```
nota de sesión escrita   17:07:55
siguiente edición de código  17:08:31
                             ─────────
                             36 s de desfase
```

`check-vault-updated` bloqueó igual. Y volverá a bloquear escriba cuando escriba
el coordinador, porque no es un problema de cuándo se escribe.

**[H]** Sale abierto al tercer aviso, así que no bloquea nada de forma
permanente. El coste medido es **ruido y tres escrituras por tanda** — que es
exactamente la dosis a la que un aviso empieza a ignorarse.

---

## 1 · El anti-drift: un predicado que la concurrencia hace imposible

### 1.1 Dónde está exactamente

**[C]** `setup/hooks/check-vault-updated.py:152-166`:

```python
last_edit = float(state.get("last_code_edit", 0))
satisfied = os.path.getmtime(project_md) >= last_edit
# …o cualquier sessions/*.md con mtime >= last_edit
```

**[C]** `setup/hooks/mark-code-dirty.py:84-88`: `last_code_edit` se pisa con
`time.time()` en **cada** `Write|Edit|MultiEdit` de código del proyecto.

El predicado no dice *«el vault está desfasado»*. Dice:

> **el vault es más nuevo que la última edición de código del mundo.**

Con escritores concurrentes eso no es una condición: es una carrera contra gente
que el coordinador no controla. **No existe un instante en el que escribir la
nota lo haga verdadero y siga siéndolo.** Los 36 s no son mala suerte; son el
único desenlace posible mientras haya un frente vivo. Solo la quiescencia lo
satisface, y la quiescencia es justo lo que no hay durante una tanda.

**No es un fallo de implementación.** La cabecera del propio hook declara su
escenario: *«termina el código, registra»*. Es correcto para la sesión
solitaria. Lo que falla es que ese supuesto ya no describe el modo de trabajo.

### 1.2 La opción (a) —ignorar las ediciones de subagente— es la peor de las dos

Se propuso *«que el hook ignore las ediciones cuyo autor sea un subagente, o
compare contra el último `last_code_edit` del coordinador»*. **No.** Dos razones,
la segunda de fondo:

1. **[C]** El hook ya filtra por `session_id` (`check-vault-updated.py:121-127`)
   y ante una discrepancia **borra el flag y sale mudo**. Si resultara que los
   subagentes traen id propio, el anti-drift no estaría siendo pesado en modo
   multi-agente: estaría **apagado**, y lo que bloqueó fueron las ediciones del
   propio coordinador. **[AR]** No sé cuál de las dos es cierta desde la lectura;
   se mide en un minuto (M1).
2. **En este modo el código lo escriben mayoritariamente los subagentes.**
   Ignorar sus ediciones apaga el hook justo en la tanda que más deuda genera.
   Es el mismo error que este documento denuncia, con el signo cambiado: una
   salvaguarda que se calla en su escenario.

### 1.3 La opción (b) —gracia— es la correcta, con una condición que no es opcional

**Propuesta P1.** Satisfacción en dos grados:

| Grado | Condición | Qué hace |
|---|---|---|
| **Fuerte** | `mtime(nota) >= last_code_edit` | como hoy: borra el flag |
| **Con frentes vivos** | `mtime(nota) + GRACIA >= last_code_edit` | `exit 0` **sin borrar el flag** |

`GRACIA` por entorno (`VAULT_DRIFT_GRACIA`), sugerido **600 s**, con la misma
higiene que `VAULT_DRIFT_EVERY` (`check-vault-updated.py:68-82`): basura o
ausente → defecto; negativo se lee como basura, porque un número inválido no
puede desactivar el anti-drift en silencio.

**La condición que la hace correcta: no borrar el flag.** **[C]** Hoy satisfacer
implica `os.remove(flag_path)` (`:165`), y eso mata también el contador `edits`,
que es *el tamaño de la deuda*. Si la gracia borrara, cada nota resetearía la
deuda y el re-armado cada N ediciones (`:174-181`) dejaría de acotar nada: el
hook volvería a ser «una vez por tanda», que es exactamente la avería D2 que el
RFD 18 ya arbitró y que la cabecera de este fichero documenta como resuelta.

Con el flag vivo, el comportamiento resultante es el que se quiere en una tanda
multi-frente: **el hook no se calla, se espacia.** Escribes tu nota, te deja
cerrar el turno, y vuelve a exigir cuando la deuda ha crecido otras N ediciones.

**Fuerte:** ~6 líneas, no toca el contrato de nadie más, y es coherente con la
filosofía que el propio hook declara — *el disparador es la causa (la deuda), no
el síntoma (el reloj)*. La gracia solo relaja el síntoma y deja la causa intacta.

**Débil, y hay que decirlo:** una gracia es una ventana, y una ventana se puede
explotar. Un agente que escribiera una nota vacía cada 9 minutos satisfaría el
hook para siempre sin registrar nada. **No lo mitigo**: el hook no puede juzgar
el contenido de la nota, y fingir que sí sería peor. Lo que sí acota el daño es
que el contador de deuda sigue vivo — la nota vacía calla el aviso, no la cuenta.

### 1.4 El agujero en la dirección contraria, que ya existe hoy

**[C]** `check-vault-updated.py:156-163`: la vía multi-agente acepta **cualquier**
`sessions/*.md` con `mtime >= last_edit`. Cualquiera: de otro frente, de otro
día, de otro agente. **La nota de otro satisface tu Stop.**

O sea que el camino multi-agente **ya es laxo hoy**, y la gracia de P1 es una
concesión pequeña encima de algo que no era estricto. **No propongo arreglarlo**:
el hook no tiene forma de saber cuál nota es «la tuya» —no conoce al autor— y
cualquier heurística de nombre sería una convención escrita, que en esta casa no
muerde. Lo que sí propongo es **que quede escrito en el comentario del código**,
porque hoy el fichero se lee como si esa rama fuese equivalente a la fuerte y no
lo es.

---

## 2 · «Los gates siempre en background»: son tres cosas, con riesgos distintos

La intuición es buena; el enunciado mezcla tres problemas que no comparten ni
solución ni peligro. Uno de ellos ya costó un incidente medido en campo.

### 2a · Paralelizar los 29 arneses dentro de `run-tests.py` — sí, y es lo barato

**[C]** `setup/scripts/run-tests.py:123-138` es un `for` con `subprocess.run`
secuencial. Cada arnés es un proceso aparte con su `cwd`; **[C]** 22 de los
ficheros de test usan `tempfile` o HOME de laboratorio, así que a primera vista
son aislados. Un pool de 4-8 son ~15 líneas (recoger la salida por arnés y
emitirla en orden, para no interleavear el informe).

⚠ **Esto no es el paralelismo del RFD 26.** Aquel es sobre la suite del proyecto
cliente (`recomendador-cobranza`, 4 756 tests, `pytest -n`); esto es sobre los
**29 arneses de Atloos**. Se nombra a propósito: la regla v4 del formato de
reportes existe porque un número de tiempo viajó cuatro sprints sin decir de qué
suite era.

**Fuerte:** devuelve reloj en el sitio donde el gate de ESTE repo se paga, sin
tocar semántica de evidencia ni contratos.

**Débil, dos avisos que no son teóricos:**

1. **Rompe el criterio del reloj.**
   `workstream-merge-gate/references/criterio-del-reloj.md` usa el **suelo de
   duración** como detector de verdes falsos — cazó dos que el exit code no vio
   (117 s y 146 s contra ~330 s). Paralelizar divide el reloj de pared y el suelo
   vigente pasa a ser basura **en la dirección peligrosa**: un umbral demasiado
   bajo acepta como buenas corridas incompletas. Si se paraleliza, el suelo debe
   reanotarse y anclarse a **la suma de tiempos por arnés** —que `run-tests.py`
   ya imprime (`:134`)— y no al de pared. El mismo documento ya dice la salida
   correcta: *«la duración es el detector, el conteo es el diagnóstico»*.
2. **Los tests sensibles a carga.** El mismo documento tiene medido el reverso:
   bajo carga aparecieron **rojos que no eran rojos** (uno que medía CPU, un
   `SIGTERM` de timeout). Con 8 arneses compitiendo, eso deja de ser un caso
   excepcional de jornada con frentes y pasa a ser el día a día del gate. Y un
   gate que grita en falso se desactiva.

### 2b · Background respecto a la sesión — no todavía, y hay un bug que arreglar antes

**[C]** Ya pasó, y está escrito en `merge-gate-guard.py:25-34` (reporte de campo
del 2026-08-11):

> «El gate corría en segundo plano sobre un SHA; mientras corría, edité y
> commiteé un documento sobre esa misma rama, y el `--ff-only` se llevó los dos
> commits. La evidencia de verde no cubría ese árbol.»

Ese agujero **concreto** está tapado: el guard compara hoy el árbol que viaja.
Pero queda otro abierto, y el background lo amplifica de segundos a minutos.

> **Hallazgo H1 — `gate-test.py` firma un `sha` y mide otra cosa.**
> **[C]** `setup/scripts/gate-test.py:239-263`: toma `sha = git rev-parse <rama>`
> al empezar, corre la suite **sobre el árbol de trabajo**, y escribe la
> evidencia sin volver a mirar. **Nada comprueba que el árbol esté limpio ni que
> no se haya movido durante la corrida.**

Los dos desenlaces son malos y ninguno se ve:

- si commiteas durante la corrida, `HEAD` avanza y la evidencia caduca sola
  (correcto, es el diseño);
- si **no** commiteas, la suite midió tu árbol sucio y la evidencia afirma que
  `HEAD` está verde — **y `HEAD` no es lo que corrió**. Nadie lo detecta, porque
  el guard compara commits y árboles de commits, no lo que se ejecutó.

**Propuesta P2 — la evidencia declara sobre qué corrió.** Capturar al empezar
`HEAD` y el hash de `git status --porcelain`, y **volver a comprobar los dos
antes de escribir**. Si algo se movió, no hay evidencia y se dice por qué (con la
primera línea sin acentos y prefijo estable, como ya hace el `NO CORRIO` de
`:250` — misma lección, misma forma).

Esto no es una mejora del background: **es un arreglo de corrección que vale
igual en primer plano**, y además es el prerrequisito para que el background sea
defendible.

> **Hallazgo H2 — background y `/goal` cierran metas en falso.**
> **[C]** `goal-evidence-guard.py:247-253` no distingue «el artefacto todavía no
> existe **porque está corriendo**» de «no existe porque nadie lo produjo».
> Con un gate en segundo plano, el guard consume sus 3 bloqueos esperando, sale
> abierto y **la meta se cierra sin evidencia** — en el bucle autónomo, que es
> justo el escenario del que este guard existe para proteger.

**Propuesta P3 — el gate declara que está corriendo.** `gate-test.py` escribe un
`gate-corriendo.json` (`{pid, rama, sha, ts}`) al arrancar y lo borra al salir,
en el mismo directorio git común que la evidencia; `goal-evidence-guard` lo lee y
**avisa sin gastar bloqueo** mientras exista. **Débil:** un proceso muerto deja
el marcador huérfano y el guard se volvería permisivo — hay que caducarlo (ts +
tope) y **no** confiar en el pid solo, que en Windows se reutiliza.

Sin P2 y P3, «siempre en background» convierte dos salvaguardas en decorado.

### 2c · Gates de varios frentes a la vez — hoy hay una sola ranura

Este no se pidió y es el que más pesa si el objetivo real es *«los gates dejan
de ser el cuello con 3 frentes»*.

**[C]** La evidencia es **un único fichero** en el directorio git común:
`gate-verde.json`, sin la rama ni el árbol en el nombre — `gate-test.py:79-127` y
su gemela `merge-gate-guard.py:176-200` (duplicadas a propósito, vigiladas por
`test-gate-test.py`).

Dos frentes gateando a la vez escriben en la misma ranura. **[AR]** El desenlace:
A termina y escribe; B termina 10 s después y **pisa**; el merge de A se bloquea
con *«la evidencia es de la rama B»*; se re-corre el de A, que pisa el de B. **No
es inseguro** —falla cerrado, que es lo correcto— pero **serializa las
integraciones por accidente** y se lee como un fallo del gate cuando es una
colisión de nombres.

> **Y esto es lo que le falta a la P1 del RFD 25.** Aquella propuesta —la
> evidencia direccionable por contenido, `status: abierto`, D12 sin arbitrar—
> hace la evidencia **compartible**, pero no **plural**: con una sola ranura, el
> verde que A podría reutilizar lo ha pisado B antes de que llegue a usarlo. **La
> reutilización que P1 promete no puede ocurrir mientras el almacén sea un
> fichero.** La forma correcta es un almacén con una entrada por árbol
> (`gate-verde/<tree>.json`) — que además hace la poda trivial y explícita.

**Y una dependencia que hay que decir en voz alta:** P1 del RFD 25 direcciona por
`git rev-parse HEAD^{tree}`, que nombra el árbol **commiteado**. Si el worktree
está sucio, lo que se probó no es ese árbol. **P2 de este documento es un
prerrequisito de la corrección de P1**, no un extra: sin la comprobación de árbol
limpio, la evidencia por contenido estaría indexada por un contenido que nadie
ejecutó.

---

## 3 · Mediciones, antes de tocar nada

| # | Qué mide | Cómo | Qué decide |
|---|---|---|---|
| **M1** | Si las ediciones de subagente comparten `session_id` | un subagente edita un fichero no-`.md` del repo; leer `.claude/vault-dirty.json` y comparar con la sesión | si el anti-drift está **pesado** (P1 aplica) o **apagado** en multi-agente (problema distinto y peor) |
| **M2** | Cuánto tarda de verdad `run-tests.py` en serie, por arnés | la corrida ya imprime segundos por arnés (`:134`); anotar total y suma | establece el suelo vigente de **este** repo, que hoy no está escrito en ninguna parte |
| **M3** | Si los 29 arneses toleran el paralelismo | correr la versión con pool **3 veces** y comparar veredicto contra la serie | un solo intermitente ⇒ baja el pool o ese arnés se marca «serie» |
| **M4** | Si algún arnés escribe fuera de su laboratorio | correr la suite con el repo en `git status --porcelain` limpio y volver a mirarlo | detecta estado compartido antes de paralelizar |
| **M5** | Cuántos gates reutilizarían un verde ajeno | contar, en una jornada de frentes, cuántas veces se gatea un árbol ya gateado | **es la medición que el RFD 25 §8 declaró pendiente** y la que justifica (o no) todo 2c |

**M1 va primera y bloquea al resto del punto 1.** Las demás son independientes.

---

## 4 · Orden de ejecución propuesto

1. **M1** — cinco minutos, y decide si el punto 1 es el problema que creemos.
2. **P1 (gracia sin borrar el flag)** en `check-vault-updated.py`, con caso nuevo
   en `setup/hooks/tests/test-check-vault-updated.py`, junto al **A.5**, que ya
   cubre la vía multi-agente (`:220-225`).
3. **P2 (árbol limpio y re-verificado)** en `gate-test.py`. Es corrección, no
   optimización: vale con o sin background, y es prerrequisito de todo lo demás.
4. **P3 (`gate-corriendo.json`)** + lectura en `goal-evidence-guard.py`. Sin
   esto, background + `/goal` cierra metas sin evidencia.
5. **Almacén plural de evidencia (2c)**, ligado a la arbitración de **D12** del
   RFD 25 — no antes, para no construir dos diseños del mismo objeto.
6. **Pool en `run-tests.py`**, con M2/M3/M4 hechas y el suelo reanotado.

Los puntos 3, 4 y 5 tocan la máquina que vigila los merges: **con la suite
delante, no a ojo.**

---

## 5 · Lo que no pude comprobar

- **[AR]** Si el payload de `PostToolUse` distingue al subagente del coordinador.
  No lo he inspeccionado; toda la sección 1.2 depende de M1 para pasar de
  inferencia a hecho.
- **[AR]** El desenlace de 2c (la ranura pisada) está derivado del código, **no
  reproducido**. Es una lectura de dos ficheros que resuelven la misma ruta; falta
  la corrida con dos frentes de verdad.
- **[AR]** No he medido nada de este repo: ni el suelo de `run-tests.py`, ni el
  aislamiento real de los 29 arneses. Toda la sección 2a es propuesta con avisos,
  no un resultado.
- **No he ejecutado la suite** en esta sesión. Todo lo de aquí sale de lectura.

---

## 6 · Decisiones que pido arbitrar

**D28 · ¿Se implementa la gracia (P1) con la condición de no borrar el flag?**
Mi voto: **sí**, después de M1. Si M1 dice que los subagentes traen id propio, se
retira: el problema sería otro y peor.

**D29 · ¿Se acepta que la vía multi-agente sea laxa (cualquier `sessions/*.md`
vale) y solo se documente?** Mi voto: **sí, documentar y no arreglar.** El hook no
conoce al autor, y una convención de nombres no muerde.

**D30 · ¿P2 (árbol limpio y re-verificado) entra ya, independientemente del
background?** Mi voto: **sí**. Es el único hallazgo de este documento que hace
que una evidencia pueda estar mintiendo hoy mismo.

**D31 · ¿«Siempre en background» se adopta como norma?** Mi voto: **no como
norma; sí como opción, y solo con P2 y P3 puestos.** Sin ellos convierte el
`goal-evidence-guard` en decorado en el escenario autónomo.

**D32 · ¿El almacén plural de evidencia se resuelve dentro de D12 (RFD 25) o
aparte?** Mi voto: **dentro**. Son el mismo objeto y dos diseños separados del
mismo fichero es la enfermedad que este repo ya se comió con `gate-verde.json`
duplicado en dos procesos.

---

## Fuentes y referencias cruzadas

- `setup/hooks/check-vault-updated.py`, `setup/hooks/mark-code-dirty.py` — el
  anti-drift, capa 1.
- `setup/hooks/goal-evidence-guard.py`, `setup/hooks/merge-gate-guard.py` — las
  dos compuertas.
- `setup/scripts/gate-test.py`, `setup/scripts/run-tests.py` — el productor de
  evidencia y el runner.
- `setup/skills/shared/workstream-merge-gate/references/criterio-del-reloj.md` —
  el suelo de duración y su reverso bajo carga.
- [RFD 25 — Dos coordinadores y el gate compartible](../ecosistema/25-RFD-DOS-COORDINADORES-Y-EL-GATE-COMPARTIBLE.md)
  — P1/D12, `status: abierto`. Este documento le añade la ranura plural y la
  dependencia del árbol limpio.
- [RFD 26 — Paralelismo, multiagente y coste](../ecosistema/26-RFD-PARALELISMO-MULTIAGENTE-Y-COSTE.md)
  — el paralelismo de la suite del proyecto cliente, que **no** es el de 2a.
- [RFD 18 — El bucle `/goal` y `/loop`](../ecosistema/18-RFD-EL-BUCLE-GOAL-Y-LOOP.md)
  — D2, de donde sale el contador de deuda que P1 tiene que preservar.
