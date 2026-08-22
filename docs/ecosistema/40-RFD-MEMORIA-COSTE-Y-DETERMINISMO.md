# 40 · RFD — Memoria, coste y determinismo

**Estado:** en curso · **Fase 1 cerrada el 2026-08-22**
**Autor:** Claude (Cowork), auditor externo
**Corpus:** 22 transcripts + 151 subagentes del proyecto `AlphaDogs`, 222 MB,
2026-05-25 → 2026-08-22, copiados por Floreano a `Downloads/`.
**Precios:** `platform.claude.com/docs/en/about-claude/pricing`, consultados 2026-08-22.

Marcas: **[R]** medido por mí · **[AR]** autorreportado · **[doc]** documentación oficial
con URL · **[ND]** no documentado.

---

# FASE 1 · La economía del contexto

## Resumen de la fase en cinco líneas

1. La factura **sí cuadra** — mi sospecha era mía, no del reporte, y me equivoqué por
   usar un precio de memoria en vez de medirlo.
2. El segundo modelo Opus **no son los subagentes**: es **una sesión resucitada
   desde el 25 de mayo** que se ha llevado el **47 %** del gasto del proyecto.
3. La ventana es de **1 M**, y el contexto medio de esa sesión es de **523 711
   tokens por llamada**. Se paga medio millón de tokens en cada turno.
4. **Nunca has compactado a mano.** Las 7 compactaciones del corpus son
   `trigger: "auto"` a ~1 000 000 de tokens. El automático llega antes que tú.
5. **Compactar al 35 % en vez de al techo habría ahorrado el 53 %**, y el umbral
   **no necesita un hook: es un ajuste** (`CLAUDE_CODE_AUTO_COMPACT_WINDOW`).

---

## 1 · Los precios, y mi error

**[doc]** Tarifas por millón de tokens, verbatim de la documentación oficial:

| Modelo | Entrada | Salida | Caché escritura 5m | 1h | Caché lectura |
|---|---|---|---|---|---|
| Opus 5 / 4.8 / 4.7 | $5 | $25 | $6.25 | $10 | **$0.50** |
| Sonnet 5 | $2 | $10 | $2.50 | $4 | $0.20 |
| Haiku 4.5 | $1 | $5 | $1.25 | $2 | $0.10 |
| Fable 5 | $10 | $50 | $12.50 | $20 | $1 |

Y lo que decide media investigación: **no hay sobreprecio por contexto largo.**
*«Claude 4.6 and later models include the full 1M token context window at standard
pricing. A 900k-token request is billed at the same per-token rate as a 9k-token
request.»* **[doc]**

### 🔴 P1 REFUTADA — la descomposición del `/usage` sí cuadra

Recalculada línea por línea con esas tarifas:

| Modelo | Recalculado | Declarado | Desvío |
|---|---|---|---|
| `opus-5` | $154.95 | $156.82 | +1,2 % |
| `opus-4-8` | $233.80 | $240.13 | +2,6 % |
| `haiku-4-5` | $2.37 | $2.70 | (±$0,33) |
| **Total** | **$391.12** | **$399.65** | **2,1 %** |

Un 2 % de residuo se explica solo con que parte de la caché se escribiera a 1 h
($10/M en vez de $6.25/M). **Cuadra.**

> **Por qué me equivoqué, y es la cuarta vez esta semana.** Dije que «1,1 m de
> salida ya son ~$82 y 355 m de caché deberían pasar de $500». Eso sale de
> tarifar Opus a **$15/$75**, que es el escalón *anterior*. Opus 5 cuesta
> **$5/$25** — un tercio. Usé un número recordado como si estuviera medido, que
> es exactamente lo que audito en los demás. La regla de la casa aplicada a mí:
> **un precio es un dato del presente, y el brief no conoce el presente.**

---

## 2 · Quién es el segundo Opus — **P2 refutada en su forma, y lo que hay debajo es peor**

Mi predicción era «`opus-4-8` son los subagentes». **No lo es.** **[R]**

En este corpus el análogo es **`claude-opus-4-7`**, y está concentrado en **una
sola sesión**: `bb77a05b`, cuyo transcript va del **2026-05-25** al **2026-08-21**.
**Tres meses de conversación resucitada**, clavada en un modelo que ya no es el que
eliges.

```
bb77a05b   46,9 MB   12 099 líneas   5 871 llamadas   claude-opus-4-7
           contexto MEDIO por llamada: 523 711 tokens
           coste reconstruido: $2 313,07
```

**Es el 47 % de los $4 958 del proyecto entero.** Una sesión que no muere paga su
historia completa en cada turno, para siempre.

### Coste reconstruido de `AlphaDogs` **[R]**

| Modelo | Origen | Llamadas | USD |
|---|---|---|---|
| `claude-opus-4-7` | sesión principal | 5 871 | **2 313,07** |
| `claude-opus-5` | sesión principal | 7 701 | 1 547,51 |
| `claude-opus-5` | subagente | 7 236 | 724,78 |
| `claude-sonnet-5` | subagente | 7 180 | 350,54 |
| `claude-fable-5` | sesión principal | 42 | 14,71 |
| `claude-opus-4-7` | subagente | 98 | 7,49 |
| | | | **4 958,11** |

Sesiones principales **78 %**, subagentes **22 %**.

### Pero el modelo del subagente **sí** diverge, y eso responde media D17

De los **151 subagentes**: **62 corrieron en `claude-sonnet-5`** mientras la sesión
principal iba en `opus-5`; 79 en `opus-5`; 10 en `opus-4-7`. **[R]**

Y cada despacho deja un `.meta.json` con **`agentType`, `model`, `spawnDepth`,
`toolUseId`**. **[R]** El orden de resolución está documentado: variable
`CLAUDE_CODE_SUBAGENT_MODEL` → parámetro por invocación → campo `model` del
subagente → modelo de la conversación principal. **[doc]**

⚠ **Por qué 62 cayeron a Sonnet no está documentado.** **[ND]** Queda como
pregunta abierta, no como hecho.

### Y el dato que más importa para la fase 3

**145 de los 151 subagentes son `general-purpose`. Sólo 6 son `Explore`.** **[R]**

Hablamos de «meter subagentes con roles específicos». Hoy el reparto es **96 % un
solo rol**. No hay que rediseñar la orquestación para tener roles: hay que
**usar** los que ya se pueden declarar.

---

## 3 · De qué está hecho el contexto

**La ventana es de 1 M**, medida y no supuesta: el máximo observado en una sola
llamada es **1 002 624 tokens**. **[R]**

| Modelo | Llamadas | Contexto **medio** | Máximo visto |
|---|---|---|---|
| `claude-opus-4-7` | 5 969 | **523 711** | 999 719 |
| `claude-opus-5` | 14 937 | 207 708 | 999 034 |
| `claude-sonnet-5` (subagentes) | 7 180 | 161 312 | 459 099 |

### Composición, por bytes de contenido **[R]**

**Sesión larga `bb77a05b` (11,8 MB de contenido):**

| % | Qué |
|---|---|
| **45,0 %** | `tool_result` |
| 17,9 % | argumentos de `Edit` |
| 16,3 % | texto |
| 12,5 % | argumentos de `Write` |
| 3,2 % | `TodoWrite` |

**≈ 77 % es tráfico de herramienta** — resultados releídos más los argumentos de
las escrituras. La entrada individual mayor: **118 KB en un solo `tool_result`**.

**Sesión reciente `7d2d649b` (3,6 MB):** texto 38,4 % · `tool_result` 27,7 % ·
argumentos de `Agent` 12,2 % · `Bash` 11,2 %. Entrada mayor: **un `tool_result` de
572 KB**. El perfil **cambia según el tipo de jornada**: la de desarrollo es
tráfico de herramienta, la de coordinación es texto y despachos.

**Existe descarga a disco** (`tool-results/toolu_*.txt`, 10 ficheros). **[R]**
Cuándo ocurre, con qué umbral y **si el resultado descargado sigue contando en el
contexto** no está documentado. **[ND]** Es una pregunta abierta con dinero
dentro.

---

## 4 · El punto de compactación

### 4.1 🔴 Tu hábito no existe — las 7 compactaciones son automáticas

**[R]** Todas las marcas `compact_boundary` del corpus:

```
2026-05-28  trigger=auto  preTokens=  970 097  postTokens= 9 697  134 s
2026-06-03  trigger=auto  preTokens=  999 418                     114 s
2026-06-26  trigger=auto  preTokens=1 002 447                     136 s
2026-06-30  trigger=auto  preTokens=1 002 226                     125 s
2026-07-03  trigger=auto  preTokens=1 000 627                     104 s
2026-08-01  trigger=auto  preTokens=1 002 444                     139 s
2026-08-21  trigger=auto  preTokens=1 002 624  postTokens=36 452  154 s
                                    cumulativeDroppedTokens=966 172
```

**Cero `trigger: "manual"` en tres meses.** Dijiste que sueles compactar al ver el
97 %; el automático llega antes **siempre**, a ~100 %. No es un reproche: es que
**la palanca que creías tener en la mano la tiene el sistema**, y está puesta en el
peor sitio posible.

Y el resumen es brutalmente eficaz: de 970 097 quedan **9 697** (1,0 %); de
1 002 624 quedan **36 452** (3,6 %).

### 4.2 🔴 P8 REFUTADA — compactar antes es **monótonamente** más barato

Yo predije que habría un óptimo intermedio porque «compactar invalida la caché y
eso se paga». **La cuenta dice que ese contrapeso es dos órdenes de magnitud
demasiado pequeño**: como el contexto post-compactación es el 1–3,6 % del previo,
reescribir la caché cuesta **~$0,23**, mientras que rodar a 470 k cuesta **~$0,24
por llamada** sólo en lectura de caché.

Simulación sobre la curva real de las dos sesiones grandes:

| Umbral | Compactaciones | Contexto medio | USD simulado | Ahorro |
|---|---|---|---|---|
| **100 % (hoy)** | 9 / 1 | 471 564 / 476 108 | 1 627 / 405 | — |
| 80 % | 11 / 2 | 376 005 / 414 923 | 1 347 / 361 | 17 % / 11 % |
| 65 % | 13 / 2 | 313 166 / 313 789 | 1 162 / 287 | 29 % / 29 % |
| 50 % | 16 / 3 | 246 838 / 254 475 | 968 / 244 | **40 % / 40 %** |
| **35 %** | 23 / 4 | 174 035 / 180 215 | 755 / 190 | **54 % / 53 %** |
| 25 % | 29 / 7 | 123 847 / 132 514 | 608 / 156 | 63 % / 61 % |
| 15 % | 46 / 11 | 76 900 / 75 933 | 471 / 115 | 71 % / 72 % |

*(`bb77a05b` / `7d2d649b`. Las dos sesiones, con perfiles distintos, dan la misma
curva a menos de dos puntos.)*

**Control del modelo, declarado:** simulado a 1 M sobre `bb77a05b` = **$1 627**
frente a **$2 313** medidos → **subestima un 30 %**. Las cifras absolutas son un
**suelo**; lo que vale son los **porcentajes**, porque los dos brazos cargan el
mismo sesgo. Lo que el modelo no cobra: fallos de caché a precio de entrada
($5/M frente a $0,50/M), escrituras a 1 h y el despacho de subagentes.

### 4.3 🔴 P7 REFUTADA — no hace falta un hook, es un ajuste

**[doc]** El umbral del auto-compact **es configurable**: `/autocompact <tokens>`,
la variable `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, o `settings.json` bajo `env`.
Rango aceptado 100 K – 1 M.
Fuente: `code.claude.com/docs/en/model-config.md`.

Lo que **no** existe **[doc]**: un hook que dispare por porcentaje de ventana. Los
hooks son por evento. `PreCompact` **reacciona** a una compactación ya decidida y
puede bloquearla (exit 2 o `decision: "block"`), pero **no puede provocarla**.
Si pudiera modificar qué se preserva, no está documentado **[ND]**.

También **[doc]**: `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` fuerza la ventana a 200 K —
que es otra forma, más brusca, de conseguir lo mismo.

### 4.4 El precio que no es dinero

Compactar al 35 % son **23 compactaciones en vez de 9** en la sesión larga. A
103–154 s medidos cada una, eso es **~50 minutos de reloj** — y, sobre todo,
**23 eventos de pérdida de memoria en vez de 9**.

Por eso el orden **flush → clear → compact** deja de ser higiene y pasa a ser la
condición del ahorro: **si el `PreCompact` no salva lo durable, bajar el umbral te
ahorra dinero y te cuesta memoria.** Adelantar el punto multiplica cualquier fallo
suyo por 2,5.

### 4.5 Y la palanca que dábamos por buena **no está disponible**

**[doc]** `clear_tool_uses` / *context editing* **no está expuesto en Claude Code**:
ni ajuste, ni bandera, ni comando, ni variable. Es parámetro de la Messages API.

Eso **confirma la causa externa** con la que RFD 34 está parado — y, a la vez, lo
degrada de prioridad: **el umbral de compactación da la mayor parte del mismo
beneficio y sí se puede tocar hoy.**

---

## 5 · Decisiones que te tocan arbitrar

| # | Decisión | Mi lectura |
|---|---|---|
| **D40-1** | ¿Se baja `CLAUDE_CODE_AUTO_COMPACT_WINDOW`? ¿A cuánto? | **Sí, a 350 000.** Ahorro medido ~53 % con 23 compactaciones en tres meses. El 25 % ahorra más y multiplica los eventos de pérdida; el 50 % es el escalón tímido. |
| **D40-2** | ¿Qué se hace con las sesiones eternas? | **Un tope de vida.** Una sesión de tres meses en un modelo viejo se llevó el 47 % del gasto. Se cierra por calendario o se declara que se acepta pagarla. |
| **D40-3** | ¿Se fija el modelo por tipo de subagente? | **Sí**, y ahora se puede: el orden de resolución está documentado y el `.meta.json` lo registra. Sin fijarlo, 62 de 151 despachos eligieron modelo solos. |
| **D40-4** | ¿Se convierte el `PreCompact` en condición dura antes de bajar el umbral? | **Sí, y va primero.** Bajar el umbral sin flush fiable cambia dinero por memoria — que es justo tu síntoma. |
| **D40-5** | ¿Se degrada RFD 34 (context editing)? | **A parado con causa confirmada.** No está expuesto en Claude Code. El umbral lo sustituye por ahora. |
| **D40-6** | ¿Se investiga la descarga a `tool-results/`? | Pregunta con dinero dentro y **sin documentar**: si lo descargado sigue contando en contexto, cambia el cálculo del 45 %. |

---

## 6 · Predicciones de la fase 1, contra lo medido

| # | Predicción | Resultado |
|---|---|---|
| P1 | La descomposición del `/usage` no cuadra | 🔴 **REFUTADA** — cuadra al 2,1 %. Error mío, por tarifar de memoria. |
| P2 | `opus-4-8` son los subagentes | 🔴 **REFUTADA** — es una sesión de tres meses. Pero el modelo del subagente **sí** diverge: 62 de 151 a Sonnet. |
| P7 | No existe hook por umbral; sólo `PreCompact` | 🟡 **MITAD** — no hay hook, pero **hay ajuste**, que era lo que hacía falta. |
| P8 | El óptimo no está en un extremo (la caché invalidada se paga) | 🔴 **REFUTADA** — la curva es monótona; el contrapeso es 100× demasiado pequeño. |
| P6 | El grueso del contexto es salida de herramienta releída | 🟢 **SOSTENIDA** en la sesión de desarrollo (77 %); **matizada** en la de coordinación (38 % texto). |

**Cuatro de cinco predicciones mías cayeron o se matizaron.** Es el resultado que
se quería: si hubieran salido todas, la medición no habría hecho falta.

## 7 · Alcance de esta fase

Sólo `AlphaDogs`. El repo de cobranza y el del reporte del 08-20 **no están
montados**; de ellos sólo tengo el `/usage` pegado, que es lo único `[AR]` que uso.
No he tocado código ni configuración de ninguna máquina.

---

# Adenda de la fase 1 — 2026-08-22

Arbitrado por Floreano: **D40-1 sí · D40-2 sí · D40-3 aplazada a la fase 3 ·
D40-4 sí · D40-5 y D40-6 a investigar.** Aquí van las dos investigaciones y la
respuesta a una pregunta suya que **corrige una recomendación mía**.

## 8 · ¿Una sesión vieja se autocompacta más? — medido, y no

Pregunta literal: *«¿entre más vida tiene una sesión, más veces se autocompacta?
¿el autocompacto termina con mayor porcentaje de contexto, o la cantidad es fija?»*

Las 6 compactaciones de `bb77a05b`, en orden **[R]**:

| # | Fecha | pre | post | post % | Llamadas desde la previa |
|---|---|---|---|---|---|
| 1 | 2026-05-28 | 970 097 | 9 697 | 1,0 % | 866 |
| 2 | 2026-06-03 | 999 418 | 11 168 | 1,1 % | 971 |
| 3 | 2026-06-26 | 1 002 447 | 23 005 | 2,3 % | 907 |
| 4 | 2026-06-30 | 1 002 226 | 15 969 | 1,6 % | 873 |
| 5 | 2026-07-03 | 1 000 627 | 25 357 | 2,5 % | 661 |
| 6 | 2026-08-01 | 1 002 444 | 15 076 | 1,5 % | 867 |
| — | *(otra sesión)* | 1 002 624 | 36 452 | 3,6 % | 841 |

**Las dos respuestas:**

- **No, no se compacta más a menudo con la edad.** El intervalo es
  **866 · 971 · 907 · 873 · 661 · 867** llamadas — media **857**, plano a lo largo
  de tres meses. La cadencia la fija **la velocidad a la que se llena el
  contexto**, no la edad de la sesión.
- **El resto no es fijo, pero tampoco crece.** Oscila entre **9 697 y 25 357**
  (1,0 %–2,5 %), sin tendencia. El resumen no se va degradando.

### 🟠 Y esto corrige mi propio D40-2

Escribí que una sesión eterna «paga su historia completa en cada turno, para
siempre». **Es falso, y el dato de arriba lo desmiente:** cada ~857 llamadas la
compactación la deja en ~16 000 tokens. Una sesión de tres meses no es una bola de
nieve; es una cadena de tramos de ~857 llamadas.

Entonces, ¿por qué costó el doble por llamada? **$0,394 frente a $0,201** de las
sesiones en Opus 5. Porque su contexto **medio** es 523 711 frente a 207 708 — y
eso no es por su edad, es porque **es una sesión de alto volumen que vuelve a
llenar el millón una y otra vez**, mientras las sesiones cortas mueren en la parte
baja de la curva sin llegar nunca al techo.

**Consecuencia para D40-2:** el argumento de coste que le puse **no se sostiene**.
Cerrar la sesión por calendario hace lo mismo que compactar —resetear el
contexto— y además pierde el hilo. **D40-1 ya se lleva ese ahorro.** Lo que sí
queda en pie de D40-2 es otra cosa, y no es dinero: la sesión lleva **clavado
`claude-opus-4-7` desde mayo** (mismo precio que Opus 5, pero no es el modelo que
eliges). **D40-2 se re-encuadra: no es un tope de coste, es un tope de *pin de
modelo*.**

## 9 · D40-5 · Context editing — parado, con causa confirmada **[doc]**

`context_management` con `edits: [{type: "clear_tool_uses_20250919", ...}]`, cabecera
beta `context-management-2025-06-27`. Dos estrategias: limpiar resultados de
herramienta y **limpiar bloques de pensamiento** (`clear_thinking_20251015`) — esta
segunda importa porque tus sesiones corren en `effort: xhigh`.

Ejemplo oficial: **70 000 → 25 000 tokens (−64 %)** en una conversación.

**No está expuesto fuera de la Messages API.** Ni ajuste, ni bandera, ni comando
en Claude Code. **La causa externa de RFD 34 queda confirmada** — y a la vez el
RFD baja de prioridad, porque D40-1 da un −53 % medido y sí se puede tocar hoy.

## 10 · D40-6 · La descarga a `tool-results/` — **existe, funciona, y casi no dispara**

**Cómo se ve, medido [R].** Un `Grep` cuya salida pesaba 33,5 KB aparece en el
transcript así:

```
"<persisted-output> Output too large (33.5KB). Full output saved to:
 …\tool-results\toolu_01McejToWe4rc8PsNLpkc9EC.txt  Preview (…)"
```

**2,4 KB en el transcript contra 34 KB en disco: −93 %.** Y responde la pregunta
que estaba sin documentar: **lo descargado NO cuenta en el contexto.** Sólo cuentan
el puntero y la vista previa.

**Pero el mecanismo apenas se usa.** En los 222 MB del corpus hay **10** ficheros
descargados. En la sesión `bb77a05b` sola hay **3 333 `tool_result`** y sólo **2**
llevan `persisted-output`. Y no es que la función no existiera: hay resultados de
**48, 50 y 54 KB EN LÍNEA el 2026-07-26 con la versión 2.1.220**, la misma en la
que ya funcionaba la descarga.

⇒ **No es una regla global de tamaño.** Disparó sobre salidas de `Grep` y de
`Bash`; resultados igual de grandes de otras herramientas siguieron en línea. El
umbral y el criterio por herramienta **no están documentados** **[ND]**.

⇒ **Conclusión:** hoy la descarga es una **válvula para extremos**, no una
estrategia de contexto. Si se pudiera bajar su umbral —o aplicarla a las
herramientas que de verdad pesan— sería el equivalente local de `clear_tool_uses`,
que es la palanca que no tenemos. **Es la pregunta con más dinero dentro de las que
quedan abiertas.**

### ⚠ Y un hallazgo lateral que no buscaba

El mayor de esos ficheros (**1,2 MB**, sesión `7d2d649b`) es la salida de un barrido
que **incluyó ficheros `.env`**:

```
./backend/.env:211:# RAG_EMBEDDINGS_PATH=…
```

Esos ficheros viven en `~/.claude/projects/…/tool-results/`, **fuera del repo**, así
que ningún `.gitignore` los cubre y ninguna auditoría los mira. No es una fuga —es
tu máquina— pero **es un sitio donde se acumula salida de herramienta sin
caducidad y con contenido de `.env` dentro**. Merece una decisión, aunque sea
«se acepta».

## 11 · Decisiones actualizadas

| # | Estado |
|---|---|
| **D40-1** · bajar `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | ✅ **Arbitrada: sí.** Sugerido 350 000 (−53 % medido). |
| **D40-2** · sesiones eternas | ✅ Arbitrada: sí — pero **re-encuadrada**: no es coste, es el pin de modelo (§8). |
| **D40-3** · fijar modelo por tipo de subagente | ⏸ Aplazada a la fase 3. |
| **D40-4** · `PreCompact` fiable **antes** de bajar el umbral | ✅ Arbitrada: sí. **Va primero.** |
| **D40-5** · RFD 34 | ✅ Cerrada: parado con causa confirmada; degradado de prioridad. |
| **D40-6** · descarga a `tool-results/` | 🔵 **Nueva pregunta abierta:** ¿se puede bajar su umbral? Es el `clear_tool_uses` que sí tenemos. |
| **D40-7** *(nueva)* | ¿Qué se hace con los ficheros de `tool-results/` — caducidad, o se acepta que acumulen salida con `.env` dentro? |

---

# FASE 2 · La memoria

**Cerrada el 2026-08-22.** Alcance: el vault de Obsidian y el repo `Atloos`, los
dos montados. El repo del reporte del 08-20 **no tiene carpeta en este vault** —
los proyectos son `alphadogs`, `atloos`, `reclutamiento-ai` y
`tt1-revisor-chatbot`—, así que la queja de «~70 ADRs» queda **[AR]** y no la uso
como dato.

## Resumen de la fase en cinco líneas

1. **La deriva existe y se mide: 11,8 %** de las citas comprobables del vault
   apuntan a algo que ya no está.
2. **Seis de ellas son ADRs citando documentos que este repo borró**, y hay un
   commit que enseña el mecanismo con las manos en la masa.
3. **`vault-drift-audit` no comprueba ni una cita.** Lo dice él mismo: se limita a
   `frontmatter updated` y mtimes. El detector existe y mide relojes.
4. El **presupuesto de arranque de 10 KB se pasa en un 52 %** sólo con dos
   ficheros — y **nada lo mide**. Es la instancia nº 10 del patrón.
5. **`sessions/` es el 78 % de la carpeta**: 71 notas, 620 KB, y sólo se leen las
   de los últimos 2-3 días. Unas 65 son **memoria de sólo escritura**.

---

## 12 · La deriva, medida

### 12.1 Primero, el fallo de mi instrumento

Mi primera pasada dio **25,0 %**. Antes de enseñártela la revisé y tenía un bug:
`lstrip("./")` no quita el prefijo `./`, **quita todos los puntos y barras
iniciales**, así que `.claude/settings.json` se convertía en
`claude/settings.json` y salía «rota» una ruta que existe. Siete citas cayeron por
eso.

```
>>> '.claude/settings.json'.lstrip('./')
'claude/settings.json'
```

Corregido con `re.sub(r"^\./", "", …)`. **La cifra buena es 11,8 %**, y la de 25 %
era mía. Lo cuento porque un número de auditoría sin su instrumento auditado es
justo lo que persigo en los demás.

### 12.2 La cifra **[R]**

Sobre los 102 ficheros `.md` de `10-Projects/atloos`:

| | |
|---|---|
| Spans en backticks | 4 715 |
| Con forma de fichero del repo | 247 distintas |
| **Comprobables** (llevan carpeta y extensión) | **203** |
| Existen | 179 |
| **ROTAS** | **24 → 11,8 %** |

Excluidas del denominador, y declaradas: 8 extensiones sueltas (`` `.ps1` ``), 4
ficheros del propio vault, 10 rutas de runtime (`state.json`, `/tmp/…`) y 22
nombres sin carpeta.

### 12.3 🔴 Lo que hay dentro: seis ADRs mandando a la puerta equivocada

De las 24 rotas, **seis son documentos que SÍ existieron en este repo y fueron
borrados** — confirmado con `git log --all --name-only` **[R]**:

| Documento citado | Quién lo cita |
|---|---|
| `docs/auditoria/10-RFD-ENDURECIMIENTO-DE-CAMPO.md` | **2 ADRs** + 1 sesión |
| `docs/telegram/05-RFD-T3-MEMORIA-Y-TOKENS.md` | **ADR del bot** |
| `docs/arquitectura-memoria/09-RFD-HIGIENE-VAULT.md` | **ADR de higiene** |
| `docs/arquitectura-memoria/12-RFD-BACKLOG-DE-PENDIENTES.md` | **ADR de higiene** |
| `docs/telegram/04-RFD-PROGRESO-EN-VIVO.md` | **ADR del puente** |
| `docs/subagentes/04-RFD-ADOPCION-WORKSTREAMS.md` | **ADR de workstreams** |

**Las carpetas existen. Los ficheros no.** No es que la estructura cambiara: es
que el documento al que el ADR apoya su decisión **ya no está**, y el ADR sigue
diciendo «ver X».

### 12.4 🔴 El mecanismo, con las manos en la masa

```
b1daa4f  2026-08-01  docs(telegram): renombra el RFD del paralelo a T5
                     y resuelve la colision 05
```

**El mismo día** en que el repo resolvió una colisión de numeración, se escribió
`ADR-20260801-bot-memoria-y-perfil.md` citando `05-RFD-T3-MEMORIA-Y-TOKENS.md`.
La renumeración se hizo en el código y **no se propagó a la memoria**.

Eso es la deriva entera en una línea: **un renombrado que nadie espejó.** Y es la
misma enfermedad que tu colisión D1/D4: etiquetas cortas y renumerables que se
citan como si fueran identidad.

### 12.5 Dos clases más que conviene nombrar

- **Deriva por acento.** El vault cita `ADRs/10-RFD-GRAPHITI-INTEGRACIÓN-ERRORES.md`;
  el real es `docs/arquitectura-memoria/10-RFD-GRAPHITI-INTEGRACION-ERRORES.md`.
  **Carpeta equivocada y una tilde.** Cualquier comprobador ingenuo la marcaría
  rota aunque la carpeta fuera buena.
- **La poda deja citas colgando.** Tres `_archive/PROMPT-*.md` citados y borrados a
  propósito — uno lo podé **yo** el 19 de agosto. Podar está bien; **podar sin
  barrer las citas es fabricar deriva**.

### 12.6 🔴 P5 CONFIRMADA — el detector mide relojes

`setup/skills/cowork/vault-drift-audit/SKILL.md`, línea 23, verbatim:

> «audit se limita a señales internas del vault (frontmatter `updated`, mtimes).»

Y sus pasos comparan mtimes contra `git log -1 --format=%ci`. **Cero comprobaciones
de cita.** Tienes el detector de deriva y detecta *cuándo se tocó un fichero*, no
*si lo que dice sigue siendo verdad*. Es la diferencia entre un reloj y un testigo.

### 12.7 P3 — sostenida en el fondo, refutada en la cifra

Predije «deriva baja, <10 %». **Bruta: 11,8 %** → falla por poco. Pero si se
cuenta sólo la **deriva con consecuencias** (ADRs apuntando a documentos
borrados), son **6 de 203 = 3,0 %**. Doy las dos y me quedo con la incómoda: el
11,8 % es la que un lint tendría que enseñar, porque el lint no sabe cuál duele.

---

## 13 · Higiene: qué falla de verdad en TU régimen

No repito las fallas genéricas de los dos documentos. Esto es lo que **tu** vault
incumple, medido.

### 13.1 🔴 El presupuesto de arranque se pasa en un 52 %, y nada lo mide

`project-resume` lo dice en su paso 3:

> «Presupuesto de arranque: si lo que vas a leer pasa de ~10 KB, algo está mal.»

Medido en `atloos` **[R]**:

| Fichero | Bytes |
|---|---|
| `_PROJECT.md` | 8 868 |
| `ADRs/_INDEX.md` | 6 357 |
| **Subtotal obligatorio** | **15 225 · 152 % del presupuesto** |
| `pendientes.md` | 24 265 |
| **Con el tablero** | **39 490 · 395 %** |

Y **`test-vault-topes.py` no lo mide**: comprueba el techo de líneas de las notas
(120 blando / 150 duro) y el presupuesto del snippet — **cero menciones** a
arranque, `project-resume` o `_INDEX`. **Instancia nº 10 del patrón de la casa:
un número escrito en un contrato que nada compara.**

El índice escala mal por diseño: 6 357 B para 16 ADRs ≈ **397 B por fila**. A 70
ADRs serían **~28 KB de índice solo** — casi el triple del presupuesto entero.
Tu queja del 08-20 es aritmética, no impresión.

### 13.2 🔴 `sessions/` es memoria de sólo escritura

| | atloos |
|---|---|
| Notas de sesión | **71** |
| Peso | **620 KB — el 78 % de la carpeta** |
| De agosto | **67** (≈ 2,2 al día) |

¿Quién las lee? `cowork_handoff.md`: *«las notas de los últimos 2-3 días»*.
`project-resume` sólo usa la **fecha** de la más reciente, para decidir qué ADRs
mirar. **Nadie lee las otras ~65.**

Eso es el «espejismo del historial» de esos documentos **en su forma real**: no son
`API_v1/v2/final`, es **una nota por sesión, para siempre**, que cuesta al
escribirla, no se lee nunca, y ensucia toda búsqueda semántica sobre el vault.

Y dos rompen la convención de nombre —`20260801-ahorro-tokens-r1-r5-r7.md` y
`20260801-registro-secretos-y-esqueletos.md`, sin guiones en la fecha—, así que
cualquier filtro por fecha **las salta en silencio**.

### 13.3 Lo que tu régimen YA cubre y no hay que volver a inventar

Para no venderte lo que ya tienes:

| Falla que describen los documentos | En tu casa |
|---|---|
| «Guardar versiones en vez de conocimiento» | **Cubierto**: RFD 12 manda *lo hecho se BORRA*; los ADRs se marcan `superseded`, no se duplican. |
| «Falta un índice maestro» | **Cubierto**: `ADRs/_INDEX.md` generado por `adr-index.py`, prohibido editar a mano. |
| «CLAUDE.md vago» | **Cubierto y de sobra**: la plantilla de despacho son 586 líneas con 8 bloques obligatorios. |
| «Un archivo, un escritor» | **Cubierto**: `check-vault-updated.py` y la doctrina del wikilink pendiente. |
| «Sistema de caducidad» | **PARCIAL**: existe por ítem (`suelo-exenciones.json`, «caduca 2026-10-08»), **no por nota**. Una nota de sesión de julio pesa lo mismo que la de ayer. |
| «Detección de deriva» | **NO cubierto** (§12.6). |

**Sólo dos huecos reales**: caducidad por nota y comprobación de citas. Todo lo
demás ya está, y adoptar los consejos tal cual sería trabajo repetido.

---

## 14 · Extractos deterministas del vault → briefs

La idea es tuya y la sostengo. Aquí está la especificación, apoyada en lo medido.

### 14.1 Qué es extraíble por REGLA, y qué no

**Extraíble (una máquina lo saca sin leer):**

- **Frontmatter de ADR**: `title`, `date`, `status`, `summary`, `tags`, `project`.
  Ya está normalizado y ya lo consume `adr-index.py`.
- **Filas del `_INDEX.md`**: generado, formato fijo.
- **Secciones de nombre fijo del ADR**: `## Contexto`, `## Decisión`,
  `## Alternativas rechazadas`, `## Consecuencias`.
- **Secciones numeradas de `pendientes.md`**: `## 1 · Firmas` … `## 5 · Parados`.
- **Ítems de tablero**: la línea `- [ ]` con su `(alta: fecha)`.

**No extraíble, y hay que decirlo:** la prosa de las notas de sesión. Son 620 KB
sin estructura declarada. Por eso el extracto **no puede salir de `sessions/`**.

### 14.2 El extracto sellado

Un extracto es un fragmento **más su procedencia comprobable**:

```
--- extracto ---
origen:  ADRs/ADR-20260819-gh-fuera-del-puente.md#Decisión
vault:   <sha256 del fichero de origen>
repo:    19d379f                      # HEAD del repo al extraer
citas:   setup/telegram-bridge/gitops.py@19d379f  (sha256 …)
         setup/telegram-bridge/tg_daemon.py@19d379f (sha256 …)
fecha:   2026-08-22
--- contenido ---
<el fragmento, literal>
```

Tres propiedades, y las tres son comprobables por una máquina:

1. **El fragmento viaja entero.** El receptor no vuelve al vault: lo que no está
   en el extracto no existe para él. Mata el «juego del teléfono» sin prohibir
   nada — no hay nada que prohibir si no hay a dónde ir.
2. **Las citas van con commit y hash.** Si el fichero cambió desde el sello, se
   sabe **sin discutir**: se recalcula el hash. Aquí es donde el 11,8 % del §12
   habría cantado solo.
3. **El sello es la fecha de caducidad.** Un extracto sellado contra `19d379f`
   usado tres semanas después es **sospechoso por construcción**, sin necesidad
   de que nadie recuerde revisarlo.

### 14.3 La regla del conflicto — y aquí discrepo de los dos documentos

`ObsidianGraphify.txt` propone que **el diseño mande** y el agente se detenga. Ya
argumenté por qué el 20 de agosto eso habría parado el día entero sobre mentiras.
Con el extracto sellado la regla se puede escribir sin elegir un rey:

> **Si el hash de una cita no coincide con el sello, el agente NO decide quién
> tiene razón: reporta la discrepancia con los dos valores y sigue con el
> CÓDIGO.** El extracto queda marcado como caducado para que el escritor de la
> memoria lo corrija al integrar.

No es «gana el vault» ni «gana el código»: es **gana el código para trabajar, y el
vault se entera**. La discrepancia deja de ser una opinión y pasa a ser un hash
distinto de otro hash.

### 14.4 Lo que esto NO resuelve

- No arregla la deriva ya existente; sólo impide fabricar más. Las 24 citas rotas
  de hoy hay que barrerlas a mano una vez.
- No sirve para `sessions/` (§14.1).
- Y cuesta: sellar exige calcular hashes al despachar. Es barato, pero no es
  gratis, y hay que decirlo antes de prometerlo.

---

## 15 · Decisiones de la fase 2

| # | Decisión | Mi lectura |
|---|---|---|
| **D40-8** | ¿Se construye el lint de citas? | **Sí, y es pequeño**: la comprobación son 40 líneas, y ya está escrita en `/tmp/deriva2.py`. Va donde ya mira `vault-drift-audit`, que hoy sólo ve relojes. |
| **D40-9** | ¿Se barren las 24 citas rotas de una vez? | **Sí**, y las 6 de ADRs primero: son las que sostienen decisiones. |
| **D40-10** | ¿Se mide el presupuesto de arranque de 10 KB? | **Sí.** Está incumplido al 152 % y es la instancia nº 10 del patrón. O se mide, o se sube el número y se dice por qué. |
| **D40-11** | ¿Caducidad por nota en `sessions/`? | **Sí, y es lo que más pesa**: 65 de 71 notas no las lee nadie. Rotar a `40-Archive/` a los N días, o dejar de escribirlas. |
| **D40-12** | ¿Se adopta el extracto sellado? | **Sí**, pero **después** de D40-8: sellar citas rotas es sellar mentiras. |
| **D40-13** | ¿Prohibición de etiquetas cortas renumerables (D1, D4, «05»)? | **Sí.** El commit `b1daa4f` enseña el mecanismo: el renombrado se hizo y la memoria no se enteró. O llevan prefijo de dueño (`RFD26-D18`), o no existen. |

## 16 · Predicciones de la fase 2

| # | Predicción | Resultado |
|---|---|---|
| P3 | Deriva de atloos **baja** (<10 %) | 🟡 **Bruta 11,8 % — falla.** Con consecuencias: 3,0 %. Doy las dos. |
| P5 | `vault-drift-audit` no comprueba ni una cita | 🟢 **CONFIRMADA**, y lo dice su propia línea 23. |

---

# FASE 3 · El determinismo de la ejecución

**Cerrada el 2026-08-22.**

## Resumen de la fase en cinco líneas

1. **El generador del estado del mundo existe, está en `main`, y no lo invoca
   nadie** — ni siquiera la plantilla que lo exige.
2. Y aunque se conectara, **no habría cazado ninguna de las dos premisas
   peligrosas del 08-20**: mide el mundo, no las afirmaciones del brief.
3. **El disparador de graphify dispara el 35 % de las veces.** Medido: 7 de 20
   sesiones lo corrieron antes del primer `Grep`.
4. **No tienes ningún hook `SessionStart`.** La mitad de reinyección del ciclo de
   compactación **no existe**, y es justo lo que hace seguro bajar el umbral.
5. **No te falta arquitectura: te faltan tres hooks** — y tu propia doctrina ya lo
   dice, en una línea que lleva meses escrita.

---

## 17 · El generador del estado del mundo

### 17.1 🔴 Está huérfano — confirmado

`setup/scripts/estado-del-mundo.py`, 422 líneas, con arnés propio, en `main`
desde el 08-18. **Nadie lo invoca** **[R]**: el `grep` sobre todo el repo sólo
devuelve menciones al fichero `.md` de salida en reportes de agosto y la línea
`?? setup/scripts/estado-del-mundo.py` del reporte de campo — o sea, **la propia
prueba de que entró sin seguimiento**.

Y lo que lo remata: **la plantilla que lo exige no lo nombra.**
`plantilla-despacho.md` tiene 586 líneas y en la 34 dice *«## 2 · Estado del
mundo — GENERADO, no escrito a mano»*. **Cero referencias al generador en todo
el fichero.** La regla está escrita, la herramienta está escrita, y **no hay una
sola línea que las una**.

Es el patrón del sprint 16 otra vez, un piso más arriba: *si defines un estado,
define quién lo escribe*. Aquí: si exiges que algo se genere, **nombra con qué**.

### 17.2 🔴 Y no habría cazado las dos premisas peligrosas

Sus siete secciones **[R]**: base y desfase · ramas vivas y colisiones ·
worktrees sucios · artefactos fuera de git · flags de entorno con su valor ·
firma de la suite · los dos baselines.

Todas describen **el mundo**. Las dos premisas que casi cuestan caro el 08-20 no
son del mundo, son **afirmaciones sobre el código**:

| Premisa que cayó | Qué habría hecho falta |
|---|---|
| «convierte el `Decimal` en `Conexion.consultar`» | *¿quién más llama a esta función?* |
| «ancla el frente en `ventana_instantes`» | *¿existe este símbolo en la rama base?* |

Ninguna de las dos es una sección del generador, y las dos son un `grep`.

**El hallazgo real de este frente:** el brief tiene **dos mitades** —el mundo
(generada, y la herramienta existe) y **las afirmaciones sobre el código**
(escrita a mano, y donde vivían las **once** premisas falsas)—. Nada genera la
segunda. **Por eso los frentes 6 y 7 son el mismo problema:** el extracto sellado
del §14 es exactamente el generador que le falta a esa mitad.

---

## 18 · Graphify — el disparador dispara el 35 % de las veces

### 18.1 La medida **[R]**

Sobre las 20 sesiones con actividad de herramienta del corpus:

| | |
|---|---|
| Llamadas a `graphify` | **131** |
| `Grep` | **285** |
| `Glob` | 48 |
| `Bash` (total) | 2 813 |
| Sesiones que usaron graphify **alguna vez** | 16 de 20 |
| Sesiones que lo corrieron **ANTES del primer `Grep`** | **7 de 20 · 35 %** |

Y el caso extremo es la sesión cara: `bb77a05b` hizo **227 `Grep` y 40 `Glob`**
contra 30 llamadas a graphify, y su **primer `Grep` fue el uso de herramienta
nº 6**, antes de cualquier consulta al grafo.

El disparador dice *«antes de la PRIMERA búsqueda de la sesión… "la primera" es
un contador, no una categoría: no clasifiques nada»*. Aun así, **dos de cada tres
sesiones lo saltan**. Por tu propia **ley del disparador** eso es **⚠
autoevaluación** de manual: dispara a veces, y su ausencia se lee como cobertura.

### 18.2 La cura, y ya está documentada **[DOC]**

`PreToolUse` admite `matcher: "Grep|Glob"` y su esquema de salida incluye:

```json
{ "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "…texto que entra al contexto de Claude…" } }
```

⇒ **Un hook puede correr `graphify query` con el mismo patrón e inyectar el
resultado, sin bloquear.** El agente deja de tener que acordarse **porque deja de
pedírsele**. ⚠ pasa a ✅.

Lo de «la primera de la sesión» no está documentado como estado del hook
**[ND]**, y **no hace falta**: el hook recibe `session_id`, así que se lleva su
propia marca en disco. Es detalle de implementación, no hueco de la herramienta.

### 18.3 Y esto ya lo decía tu propia doctrina

`agentic-system-design`, sección «Reglas de nuestro setup»:

> «**Enforcement determinista** donde importe (regla R2): validaciones y gates
> van en **hooks/código, no en el prompt**.»

El disparador de graphify vive **en el prompt**. Ése es el bug entero, y la regla
que lo prohíbe lleva meses escrita en tu propia skill.

---

## 19 · Orquestación — no falta arquitectura, faltan tres hooks

### 19.1 🔴 No tienes ningún hook `SessionStart`

Tus seis hooks **[R]**: `check-vault-updated` (Stop) · `goal-evidence-guard`
(Stop) · `mark-code-dirty` (PostToolUse) · `memory-flush` (**PreCompact**) ·
`merge-gate-guard` (PreToolUse `Bash|PowerShell`) · `validate-graphiti-group-id`.

Y lo verificado en la documentación **[DOC]**:

- **`PreCompact` puede BLOQUEAR pero NO puede modificar qué se preserva.** Tu
  `memory-flush.py` ya lo dice en su docstring — lo descubriste antes que yo, y
  bloquear era la implementación correcta dada esa limitación.
- **`SessionStart` acepta `matcher: "compact"`** y **su stdout entra directo al
  contexto** como texto que Claude puede ver y usar. No puede bloquear.

⇒ **El ciclo de compactación te falta a la mitad.**

```
   PreCompact (memory-flush)  →  compactación  →  ¿?
   ✅ salva lo durable            ✅ funciona      ❌ NADA lo devuelve
```

Después de cada compactación, **nada reinyecta la memoria durable**. Con 7
compactaciones en tres meses eso son 7 amnesias; **con D40-1 al 35 % serían 23**.

**Ésta es la pieza que hace seguro bajar el umbral**, y es el hallazgo con más
valor de toda la investigación: un `SessionStart` con `matcher: "compact"` que
escriba a stdout el `_PROJECT.md`, el tablero y el extracto sellado del §14.

### 19.2 🟢 D17 tiene mecanismo — y ahora el canario es de 20 minutos

Dos hechos que se juntan:

- **Fase 1 [R]:** cada despacho deja `.meta.json` con **`agentType`, `model`,
  `spawnDepth`, `toolUseId`**. La divergencia de modelo es real y observable
  (62 de 151 a Sonnet).
- **Fase 3 [DOC]:** el esquema de salida de `PreToolUse` incluye
  **`updatedInput`**, *«modifies the `tool_input` object that Claude Code will
  use when executing the tool»*.

⇒ **Un hook `PreToolUse` con `matcher` sobre la herramienta de despacho puede
reescribir el modelo y el tipo de agente de forma determinista.** Enrutado por
rol sin arquitectura nueva, con enforcement en código y no en el prompt —
exactamente la regla R2.

⚠ **Lo que NO he verificado:** que `updatedInput` funcione sobre **esa**
herramienta en concreto. Eso sigue siendo tu canario D17. Pero ha dejado de ser
«¿existe algún mecanismo?» para ser **«¿este mecanismo concreto acepta estos dos
campos?»** — una tarde se convirtió en veinte minutos.

### 19.3 Los hooks que hoy no usas y resuelven cosas tuyas **[DOC]**

De los 31 eventos documentados, tres tocan pendientes vivos del tablero:

| Hook | Qué desbloquea |
|---|---|
| `SessionStart` (`compact`) | La reinyección que falta (§19.1). |
| `SubagentStart` / `SubagentStop` | Punto de aplicación **por despacho**: fijar modelo, sellar el brief, exigir el reporte. Hoy no hay ninguno. |
| `TaskCompleted` | El gate como evento, que es la prueba deliberada que el sprint 5 dejó fuera (**D13**, sin arbitrar desde el 08-14). |

Y un dato de portabilidad: **`.claude/settings.json` del repo registra CERO
hooks** **[R]**. Los seis scripts existen en `setup/hooks/` y su cableado vive
**fuera del repo**, por máquina. Es la misma enfermedad que el
`sync-hooks.ps1` sin `.sh`: la capa que hace determinista todo lo demás **no
está versionada donde vive el resto**.

### 19.4 El veredicto sobre los dos documentos, con tu doctrina en la mano

Tu `agentic-system-design` tiene una escalera de cuatro escalones y una regla:
**subir sólo si el escalón anterior falla, y escribir por qué**.

Los dos documentos que me pasaste saltan directos al escalón 3-4
(*orchestrator-workers* con Estratega/Dispatcher/Ejecutor). **Tu evidencia medida
dice que lo que falla es el escalón 2**: enforcement determinista ausente —el
disparador en el prompt, el generador sin conectar, la reinyección inexistente—.
Subir de escalón sin arreglar el anterior multiplica despachos, y el despacho se
paga en escritura de caché.

Y hay una frase de tu `context-engineering` que **condena el ajuste actual** sin
que nadie lo hubiera notado:

> «**Compaction**: resumir-y-continuar en fronteras de **fase**, no a mitad de
> una tarea.»

El auto-compact a 1 M dispara **donde caiga el techo** — a mitad de tarea por
construcción, siempre. Tu propia doctrina ya lo desaprobaba.

Y su pregunta de verificación (c) —*«¿qué pasa en el turno 50: qué creció sin
límite?»*— tiene ahora dos respuestas medidas: **el contexto, hasta 1 M**, y
**`sessions/`, hasta 620 KB**.

---

## 20 · Decisiones de la fase 3

| # | Decisión | Mi lectura |
|---|---|---|
| **D40-14** | ¿Se crea el hook `SessionStart` (`matcher: compact`) que reinyecta la memoria durable? | **Sí, y es lo primero de todo.** Cierra la amnesia y es la condición de D40-1. Es el mayor retorno de la investigación entera. |
| **D40-15** | ¿Se conecta `estado-del-mundo.py` a `workstream-dispatch`, nombrándolo en la plantilla? | **Sí.** Está escrito, probado y en `main` desde el 08-18 sin que nada lo llame. |
| **D40-16** | ¿Se le añade la mitad que falta —«¿quién llama a esto?» y «¿existe este símbolo en la base?»— o eso lo cubre el extracto sellado? | **El extracto sellado (§14).** El generador mide el mundo; las afirmaciones del brief son otra mitad y ya tienen diseño. |
| **D40-17** | ¿Graphify pasa a `PreToolUse` con `additionalContext`? | **Sí.** 35 % de disparo medido, y tu regla R2 ya lo exige. |
| **D40-18** | ¿Se corre el canario D17 sobre `updatedInput` en la herramienta de despacho? | **Sí, y ahora son 20 minutos.** De ahí sale D40-3 (fijar modelo por rol), que dejaste aplazada. |
| **D40-19** | ¿El cableado de hooks se versiona en el repo? | **Sí.** Hoy `.claude/settings.json` registra cero y el cableado vive por máquina. La capa que da determinismo es la única sin versionar. |

## 21 · Predicciones de la fase 3

| # | Predicción | Resultado |
|---|---|---|
| P4 | `estado-del-mundo.py` existe y **no** está enganchado | 🟢 **CONFIRMADA** — y ni la plantilla que lo exige lo nombra. |
| P6 | El ahorro está en contexto × turnos, no en despachar mejor; ninguna de las tres arquitecturas propuestas lo toca | 🟢 **CONFIRMADA.** Las palancas medidas son el umbral de compactación (−53 %) y tres hooks. Ninguna de las tres arquitecturas menciona ni el umbral ni un hook. |

---

# Cierre — qué sale de las tres fases

**Lo que NO hay que construir:** una arquitectura de roles. La orquestación que
tienes funciona; lo que falla son las entradas y el enforcement.

**Lo que sí, en orden de retorno medido:**

1. **`SessionStart` (`compact`) que reinyecta** — condición de todo lo demás (D40-14).
2. **Bajar `CLAUDE_CODE_AUTO_COMPACT_WINDOW` a ~350 000** — **−53 % medido** (D40-1).
3. **El lint de citas** — 11,8 % de deriva, 40 líneas de código (D40-8).
4. **Graphify a `PreToolUse`** — de 35 % a 100 % de disparo (D40-17).
5. **Conectar el generador** — escrito, probado, sin llamar desde el 08-18 (D40-15).
6. **Caducidad en `sessions/`** — 65 de 71 notas no las lee nadie (D40-11).

Ninguna es un rediseño. Cinco de las seis son un fichero nuevo o una línea
cambiada. Y las tres que más devuelven —el hook, el umbral y el lint— **caben en
una tarde**.
