---
title: Análisis del reporte del 08-17 — dónde se fue $310,91, y si la higiene de logs ayudó
tags: [analisis, coste, higiene, contexto, subagentes, feedback]
created: 2026-08-18
updated: 2026-08-18
status: cerrado
type: analisis
project: atloos
fuente: feedback/reportes/2026-08-17-programadomaxi2-geo-y-sprint-2.md
---

# Dónde se fue $310,91 — y la respuesta a «¿ayudó la higiene?»

**Respuesta corta: la higiene estaba puesta, tu tesis es correcta, y se queda
corta. El ahorro no es lineal: se multiplica por los turnos que quedan.** Pero la
regla que escribimos mide la cosa equivocada, y la sesión trae el número que lo
prueba.

---

## 1 · La higiene sí estaba desplegada — verificado

**[R]** El reporte declara `setup_sha: 4f0a6a8+`. Ese sha es
*«docs(auditoria): la 31 entra al repo»*, **ancestro de `main`**, y lleva la
línea de higiene en el snippet:

```
$ git show 4f0a6a8:…/references/memory-snippet.md | grep -c "Higiene de salida"
1
```

Así que la pregunta no es si estaba: **es si sirvió**. Y eso el reporte **no lo
puede contestar**, porque mide el coste total y no mide **de qué está hecho el
contexto**. Ese es el primer hueco, y es del formato, no del agente.

---

## 2 · La factura, descompuesta — y no es lo que parece

Reconstruí el `/cost` con la estructura de precios de la familia (`input P`,
`output 5P`, `cache read 0,1P`, `cache write 1,25P`). **El ajuste cae a 0,1 % y
0,3 %**, así que esto no es una estimación: es una descomposición.

| | input | output | **cache read** | cache write |
|---|---:|---:|---:|---:|
| **sonnet-5** ($141,79) | 1,7 % | 13,7 % | **63,7 %** | 20,9 % |
| **opus-5** ($169,12) | 0,3 % | 13,0 % | **80,8 %** | 5,9 % |

> **$226,72 de $310,91 — el 73 % de la factura — es cache read.**
> El *output*, que es lo que intuitivamente parece caro, es el **13 %** en los
> dos modelos. Y el cache read es el **99,1 %** de los tokens que movió el
> coordinador y el **96,8 %** de los del subagente.

**Traducción: no pagas por lo que el modelo escribe. Pagas por lo que el modelo
vuelve a leer.**

---

## 3 · El multiplicador, que es lo que tu tesis no dice todavía

**272,6 M de cache read ÷ 1 132 turnos = 241 k tokens releídos por turno.**
Releer ese contexto una vez cuesta ~**$0,12**. Y se releyó 1 132 veces.

De ahí sale el número que gobierna todo:

| Basura metida en el contexto | Coste en **esta** sesión |
|---|---:|
| 1 k tokens | **$0,57** |
| 10 k tokens | **$5,66** |
| 50 k tokens | **$28,30** |

Un `git log --stat` de los que medimos en el sprint 8 —**222 314 bytes**, unos
55 k tokens— metido pronto en una sesión así **cuesta unos $30**. No 55 k
tokens: 55 k **por cada turno que venga después**.

> **Tu tesis —«más higiene, más ahorro»— es correcta y se queda corta.**
> No es proporcional al tamaño de la salida: es proporcional al tamaño
> **multiplicado por los turnos restantes**. Por eso la higiene vale más al
> principio de la sesión que al final, y eso no está escrito en ningún sitio.

---

## 4 · Pero la regla que escribimos mide lo que no gasta

`higiene-de-salida.md` tiene ocho filas y todas dicen lo mismo: **haz que ESTA
salida sea más pequeña**. El gasto real es

```
bytes  ×  número de llamadas  ×  turnos restantes
```

y la regla **solo tiene término para el primer factor**. La sesión trae la
medición que lo demuestra:

**[R] 170 llamadas de búsqueda (`Grep`/`grep`/`rg`). 0 de `graphify query`.**

Aunque cada una de esas 170 fuera perfectamente higiénica —1-2 k tokens—, son
**170-340 k tokens** de contexto acumulado, releídos más de mil veces. **La
higiene por comando no puede con eso**: lo que hace falta es no traer las 170
salidas al contexto del coordinador.

---

## 5 · Las tres palancas que quedan, con su número

**a) Buscar DENTRO de un subagente.** Un subagente devuelve **solo su mensaje
final**: sus 170 greps nunca entran en el contexto del coordinador. Es la
compresión con pérdida que ya escribí en el RFD 26 §4.5 —*«subagentes, cuyo
retrieve es volver a preguntar»*— y esta sesión es su caso de campo: el
coordinador despachó implementadores pero **buscó él mismo**.

**b) El modelo del subagente, que el propio agente declara no haber puesto nunca.**
**[R]** $141,79 en `sonnet-5`, **35 % del uso bajo `general-purpose`**, y
`haiku-4-5` costó **$0,0030** en toda la sesión — es decir, **no se usó**. Varios
despachos eran transcripción o arreglos mecánicos. A grandes rasgos, mover la
mitad de ese trabajo al tier barato son **~$45-50 de esta factura**.
Y la causa está bien diagnosticada por él: *«es el parámetro que hay que recordar
poner en cada llamada, sin nada que lo pida ni lo eche de menos»*.

**c) `graphify query`: cero usos en 532 minutos, con el grafo fresco.** **[R]** Las
dos hipótesis del humano quedaron refutadas por la máquina —el hook corrió, el
grafo estaba a un minuto del último commit—, así que no fue infraestructura.

> **Y su explicación es la mejor lección de diseño de disparadores del proyecto:**
> el disparador se ancla en *«tu primer `grep` de exploración»*, y **eso obliga al
> agente a clasificar su propia búsqueda**. Un agente que no sabe dónde está algo
> no se dice «voy a explorar»: se dice **«voy a confirmar»**. Por eso no disparó
> 170 veces seguidas.
>
> **Un disparador que depende del juicio del agente sobre su propio estado no es
> un disparador.** El ancla barata es el arranque de sesión.

---

## 6 · Lo que este reporte cierra: el ×2,05 por fin tiene máquina

**[R]** `maquina: programadomaxi2` · **16 núcleos** · **16 GB**.

Eso cierra el agujero que arrastramos desde el sprint 2 y **desmiente las tres
versiones que hemos tenido**: no eran 8 núcleos (mío), no era
`FLOREANO_LEGION`/24 (mi errata del sprint 8), y `ProgramadoMaxi2` **es la
máquina**, no el proyecto.

Y cambia la causa. El reporte mide tres corridas de la misma suite y el mismo
SHA: `24 failed @ 394 s` · `0 failed @ 324 s` · `21 failed @ 1 238 s`, y **los
mismos ficheros `0 failed @ 23 s` aislados**. Todos los fallos son tests que
lanzan `subprocess` sobre scripts que importan pandas.

> **Con 16 GB, el techo no lo pone el núcleo: lo pone la memoria.** El ×2,05 se
> razonó con CPU durante cuatro sprints sobre una máquina cuyo cuello era la RAM.

⚠ Y un dato que jubila otro número: **la suite limpia tarda hoy 551 s con 4 985
tests**. El «suelo de ~330 s» que arrastra `medir-el-techo.md` es de una suite
más pequeña y **ya no vale como referencia**.

---

## 7 · Lo que hay que añadir al formato de feedback

Para poder contestar «¿ayudó la higiene?» con `[R]` y no con opinión, el reporte
necesita **de qué está hecho el contexto**, no solo cuánto costó:

- **Llamadas por herramienta**, con bytes de salida acumulados. El agente ya
  contó las invocaciones con un script para la sección de graphify — es el mismo
  trabajo, dos columnas más.
- **El turno en el que entró cada salida grande.** Un volcado en el turno 50 de
  1 132 cuesta veinte veces más que el mismo volcado en el turno 1 000.
- **Modelo por despacho.** Hoy solo se sabe el agregado del `/cost`.

Sin esas tres, la próxima vez volveremos a estar donde estamos: sabiendo el total
y adivinando la causa.

---

## 8 · Del reporte, lo que hay que subrayar

**Se corrigió a sí mismo con la máquina delante.** Había escrito que `adr-writer`
no disparó —de memoria— y el `/cost` la lista con 1 %. Lo movió y **dejó escrito
el fallo**: *«reporté de memoria un dato que era medible, en un reporte cuya
regla primera es separar `[R]` de `[AR]`»*.

**Declaró el árbol sucio.** `dirty: true` en el manifiesto, con la consecuencia
dicha: *«cualquier conclusión sobre qué skill había instalada vale hasta donde
valga ese árbol»*.

**Y el hallazgo estructural del humano es el más caro de la sesión**: el vault
tenía la respuesta —`Incontactable` deprecado desde v8, con ADR, fecha y dueño— y
**nada obliga a un plan escrito tres días después a volver a cruzarse con los
ADRs**. Un despacho entero se construyó encima. Es la misma forma que perseguimos
en el setup: **un número escrito que nadie vuelve a mirar**, aplicado al vault.
