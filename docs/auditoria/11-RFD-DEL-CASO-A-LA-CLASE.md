# RFD — Del caso a la clase: los cuatro fallos de la segunda campaña

> **Estado:** PROPUESTA — **2 decisiones abiertas (D1, D2) que arbitra el
> usuario**. Pendiente de auditoría externa (Cowork).
> **Fecha:** 2026-08-07 · **Autor:** Opus (laptop, con el código delante) —
> **flujo invertido respecto al RFD 10**: allí escribió el auditor y auditó el
> implementador; aquí al revés, y Cowork audita al final.
> **Origen:** `subagentes/08-SEGUNDA-CAMPANA-REAL.md` — retrospectiva de la
> jornada del 2026-08-07 en `recomendador-cobranza` (16 frentes, 9 ramas,
> 3.174 verdes). **Es una auditoría a las correcciones del RFD 10**, no un
> reporte nuevo: califica las 5 recomendaciones del día anterior.
> **Contexto:** `auditoria/10-RFD-ENDURECIMIENTO-DE-CAMPO.md` (implementado el
> 08-07) · `subagentes/07-PRIMERA-CAMPANA-REAL.md` (jornada 1) ·
> `arquitectura-memoria/12-RFD-BACKLOG-DE-PENDIENTES.md` ·
> `ADR-20260801-higiene-vault` · `ADR-20260801-bot-memoria-y-perfil`.

---

## 1. Problema

El RFD 10 se implementó el 08-07 y la jornada siguiente lo calificó con
números. **Cuatro de cinco recomendaciones cumplidas**, y la mejor medida es
inequívoca: el aprovisionamiento en el brief llevó las **corridas perdidas por
inventario de 4 a 0**.

Pero los cuatro fallos nuevos **comparten forma**, y es la misma que ya nos mordió
con `notify-telegram` ese mismo día:

> **Arreglamos el caso y no la clase.**

- El aprovisionamiento cubrió lo **ausente** y no lo **presente** → 3 rojos caros.
- La instrucción de graphify cambió de **sitio** pero no de **forma** → segundo
  día con cero invocaciones, incumplida idéntica.
- El umbral del backlog **avisa** pero no muerde → tercer día avisando de lo
  mismo, con el archivo a 2,8× de su límite duro.
- Y el vault **acumula sin poder retractarse** → sirvió tres hechos refutados con
  la misma autoridad que los verdaderos.

Este RFD ataca las cuatro clases. Ninguno es hipotético: todos tienen la medición
al lado.

## 2. Los fallos

Numeración continua desde el RFD 10 (F1–F12) y el fix de rutas (F13).

| # | Fallo | Daño medido |
|---|---|---|
| **F14** | La instrucción de graphify no tiene un momento reconocible: *"primera media hora"* / *"first run graphify query"* | **2 jornadas, 0 invocaciones**, con la herramienta al día (`graph.json` regenerado a las 20:08) y la orden escrita en el `CLAUDE.md` del proyecto |
| **F15** | El bloque 2 del brief pregunta qué **falta**, nunca qué **sobra** | 3 rojos caros por entorno **presente**: padrón nuevo en disco (**31 tests**), `COB_EF_CURSOR_MAX_MIN=45` en el `.env` (**2 tests**), un fixture que mentía con fechas |
| **F16** | El umbral del backlog **avisa y nadie actúa** | 3.er día con el mismo aviso: `_PROJECT.md` a **425 líneas / 13 checkboxes** (límites 120/150, umbral 12) y **tres** ficheros de pendientes vivos en vez de uno |
| **F17** | **Ninguna skill sabe retirar un hecho falso.** `memory-keeper` guarda, `adr-writer` decide, `session-close` consolida | 3 hechos del vault refutados por medición el mismo día; uno costó **media jornada** de razonamiento sobre una premisa falsa. Se corrigieron a mano, fichero por fichero |

**Y uno que el reporte no vio, propio:**

| # | Fallo | Evidencia |
|---|---|---|
| **F18** | El **snapshot generado vive en el vault** y se reescribe en cada commit | **212 KB** dentro de OneDrive, regenerados varias veces al día. Es el patrón que H2/A1 prohibieron para FalkorDB y que motivó sacar el `.git` del vault. No lo introdujo el RFD 10 —antes pasaba igual— pero **lo institucionalizó** al darle nombre propio |

## 3. Objetivos

**O1.** Que las instrucciones tengan un **momento de disparo reconocible**, no
una intención (F14).
**O2.** Que el brief transporte el entorno **completo**: lo que falta y lo que
sobra (F15).
**O3.** Que un umbral que se cruza tres días seguidos **deje de ser un log**
(F16).
**O4.** Que el vault pueda **retractarse**: un hecho refutado no debe servirse
con la autoridad de uno verdadero (F17).
**O5.** Cero regresiones: presupuestos de palabras respetados, y las skills de
Superpowers no se tocan.

## 4. Casos de diseño

### C1 · La instrucción de graphify cambia de FORMA, no de sitio (F14) 🔴

Ayer movimos el consejo a `hooks/README.md` y `project-onboard` §7. Fue
insuficiente: el texto seguía diciendo *"úsalo en la primera media hora"*
([`hooks/README.md:156`](../../setup/hooks/README.md)), que **no nombra un
momento**. Un mandato incumplido 2 de 2 veces no está mal obedecido: está mal
colocado.

**Redacción nueva, con disparador y expectativa calibrada:**

> **Antes de tu primer `grep` de exploración en una sesión, corre
> `graphify query`. Su salida es la LISTA DE CANDIDATOS, no la respuesta:
> confírmala con `Read` y da por hecho que le faltan sitios.**

La segunda frase importa tanto como la primera, y ahora tiene número: sobre la
pregunta más cara del día devolvió **5 de 9 sitios en 1,7 s** (contra ~40 min a
mano) — pero **omitió los dos decisivos**, y **49 de 65 `loc=` eran `L1`**: señala
el fichero, no la línea. Vendérselo como "orientación" era generoso; es una
**primera pasada con omisiones garantizadas**.

⚠ **Dos sitios, no uno.** La frase que el agente lee de verdad —*"For codebase
questions, first run `graphify query`"*— **la escribe `graphify claude install`
en el `CLAUDE.md` del proyecto**, no nosotros. Cambiar solo nuestra doc dejaría
la mala instrucción en pie. `project-onboard` §7 debe decir explícitamente:
**sustituye esa línea por el disparador** tras instalar.

### C2 · El bloque 2 pregunta también qué SOBRA (F15) 🔴

Hoy pide *"artefactos fuera de git: ruta y cómo obtenerlos"*
([`plantilla-despacho.md:44`](../../setup/skills/shared/workstream-dispatch/references/plantilla-despacho.md)) —
solo lo **ausente**. Los tres rojos de hoy fueron lo **presente**: un padrón que
la suite no esperaba, una variable en el `.env`, un fixture con fechas mentirosas.

El bloque 2 gana su reverso:

- **Qué hay en disco que la suite NO espera** (padrones, datasets de pruebas
  anteriores, artefactos de otro frente).
- **Qué variables de entorno están puestas** y mueven el comportamiento — con su
  valor, no solo su nombre.
- **La mitigación que el reporte ya escribió después de perderlo**:
  `os.environ.setdefault` en `conftest.py` para **neutralizar el entorno**, de
  modo que la suite no dependa de lo que haya en la máquina.

> El inventario no es una lista de lo que falta: es la **diferencia** entre la
> máquina y lo que la suite supone.

### C3 · El umbral del backlog deja de ser solo aviso (F16) — **D1, decides tú**

[`session-close:56-61`](../../setup/skills/shared/session-close/SKILL.md) dice
**propón**. Es deliberado —"avisa, no bloquees"— pero tres días con el mismo
aviso y el archivo a **2,8× del límite duro** dan la razón al reporte:
*avisar sin que nadie actúe no es una compuerta, es un log*.

| | (a) Seguir avisando | (b) **Escalar el aviso por reincidencia** | (c) Aplicarlo solo |
|---|---|---|---|
| Cómo | igual que hoy | la 1.ª vez propone; a partir de la **2.ª con el mismo umbral cruzado**, lo dice como **incumplimiento del contrato** con el número de días, y `vault-drift-audit` lo sube a hallazgo | `session-close` crea el backlog sin preguntar |
| Respeta "avisa, no bloquees" | sí | **sí** — sigue sin ejecutar sin OK | **no** |
| Riesgo | el log eterno que ya tenemos | que el usuario lo ignore igual, pero **con constancia escrita** | mueve pendientes sin que nadie lo pida |

**Recomendación: (b).** Es el mínimo que convierte el log en registro. (c)
rompería el contrato de todo el ritual por un caso.

⚠ Y hay un hallazgo debajo: ese proyecto tiene **tres ficheros de pendientes**
(`PENDIENTES.md` de 128 KB + dos fechados) que **no son** el `pendientes.md` del
RFD 12. El umbral no falló solo: **el RFD 12 nunca se aplicó ahí**. Consolidarlos
es trabajo de ese proyecto, no de este RFD, pero el aviso debe nombrarlo.

### C4 · `memory-keeper` aprende a refutar (F17) 🔴

Es el hallazgo de fondo, y **tenemos evidencia propia**: el estado falso de
Graphiti se propagó de una nota de sesión a `_PROJECT.md` —con wikilink roto
incluido— y hubo que corregirlo **a mano en tres sitios**. Nuestro
`bug-registro-graphiti-contradice-adr` es una retractación artesanal.

Hoy: `memory-keeper` **guarda**, `adr-writer` **decide**, `session-close`
**consolida**. Ninguna **retira**. Lo único parecido es `superseded`, y solo para
ADRs ([`adr-writer:35`](../../setup/skills/shared/adr-writer/SKILL.md)).

**Diseño — refutar, no borrar:**

1. `memory-keeper` gana un modo **refutación**: dado un hecho del vault que una
   medición contradice, **no lo borra** —el error enseña— sino que lo marca:

   ```
   > ❌ **REFUTADO (YYYY-MM-DD):** <qué resultó falso>.
   > **Medido en:** <comando//archivo/nota que lo refutó>. Lo correcto es <…>.
   ```

2. **Tachado en el índice**: donde el hecho aparezca en `_PROJECT.md` o en un
   índice, su línea va tachada con el enlace a la refutación. Es el patrón que ya
   usamos con los RFD cosechados, aplicado a hechos.
3. **`project-resume` no debe servir un hecho refutado como bueno**: si la línea
   está tachada, la menciona como refutada o no la menciona.
4. **`vault-drift-audit` gana un check**: un hecho refutado cuyo original sigue
   sin marcar en algún sitio → divergencia.

**Por qué no borrar**: borrar deja el hueco sin explicación y el mismo error
vuelve. La regla del repo es la misma que con la corrección del RFD 10 de
Graphiti: *se corrige en vez de taparse, y se ve qué se creyó y por qué era falso*.

### C5 · El snapshot generado sale del vault (F18) — **D2, decides tú**

El hook escribe **212 KB** de volcado dentro de OneDrive y los reescribe en cada
commit ([`git-post-commit-graph-report.sh:53`](../../setup/hooks/git-post-commit-graph-report.sh)).

| | (a) Dejarlo | (b) **Snapshot a `%LOCALAPPDATA%`, resumen al vault** | (c) Solo resumen |
|---|---|---|---|
| Cómo | igual | el volcado vive local; al vault va un `codebase-map-snapshot.md` **recortado** (cabecera + resumen, ~2 KB) | no se guarda volcado |
| Churn de OneDrive | alto, varias veces/día | **mínimo** | mínimo |
| ¿Se puede consultar el grafo entero? | sí, desde cualquier laptop | sí, en la que lo generó | no |
| Rompe algo | — | nada: el briefing del bot ya solo consume **119 chars** de él, y `vault-drift-audit` mide su **fecha**, no su tamaño | pierde el volcado |

**Recomendación: (b).** Es coherente con H2/A1 —datos vivos fuera de la carpeta
sincronizada, artefactos terminados dentro— y no rompe a ningún consumidor.

### C6 · Lo que NO se hace

- **Tocar `superpowers:brainstorming`** (regla de W2, otra vez).
- **Consolidar los `PENDIENTES-*.md` de `recomendador-cobranza`**: es trabajo de
  ese proyecto. Este RFD solo hace que el aviso lo nombre.
- **Automatizar la refutación**: decidir que un hecho es falso es juicio, no
  regla. `memory-keeper` da el formato; el humano (o el frente que midió) aporta
  la evidencia.
- **Cambiar el umbral 12/8 del RFD 12**: no es el número el que falló, es lo que
  pasa al cruzarlo.

## 5. Alcance

**Entra:** C1–C5 con sus verificaciones; promover el reporte de la jornada 2 a
`subagentes/08-SEGUNDA-CAMPANA-REAL.md` (banner, sin reescribir) —**hecho ya al
redactar este RFD**, para que sea auditable sin adjuntos sueltos.
**No entra:** C6; las cosechas pendientes (RFD 04, 10, 12), que siguen gateadas a
la auditoría externa del RFD 10.

## 6. Criterios de éxito

1. **F14**: la instrucción vive en los **dos** sitios —nuestra doc y la línea que
   `graphify claude install` escribe en el `CLAUDE.md`— con el disparador
   («antes de tu primer `grep`») y la expectativa («candidatos, no respuesta»).
   Verificable con `grep`: cero apariciones de *"primera media hora"*.
2. **F15**: el bloque 2 pide explícitamente lo **presente** (disco + variables con
   su valor) y menciona el `os.environ.setdefault` del `conftest.py`.
3. **F16** (según D1): el segundo cierre consecutivo con el umbral cruzado
   produce un mensaje distinto al primero, con el número de días.
4. **F17**: `memory-keeper` documenta el formato de refutación; `project-resume`
   no sirve un hecho tachado como bueno; `vault-drift-audit` gana su check.
   **Prueba sembrada**: refutar un hecho de laboratorio y ver que las tres piezas
   se comportan.
5. **F18** (según D2): tras un commit, el volcado no está en el vault y sí su
   resumen; el briefing del bot sigue midiendo ≤800 chars de extracto.
6. `wc -w` de todo cuerpo de skill editado **≤500**.
7. Los 7 bloques de la plantilla conservan numeración.

## 7. Riesgos

- **C1 depende de un tercero**: si `graphify claude install` se vuelve a correr,
  reescribe su línea y borra el disparador. Mitigación: `project-onboard` lo
  advierte; a la tercera reincidencia, tocará un check en el drift-audit.
- **C4 puede volverse burocracia**: si refutar cuesta más que corregir a mano,
  nadie lo usará —exactamente lo que pasó con `adr-writer` la jornada 1—. Por eso
  el formato es **tres líneas**, no una skill nueva.
- **C2 engorda el bloque 2 por segunda vez.** Vigilar que el despacho siga siendo
  generable en minutos; si estorba en la próxima campaña, se poda con evidencia.
- **Este RFD lo escribe quien implementó lo que se está criticando.** Sesgo obvio:
  tres de los cuatro fallos son de código mío de ayer. La auditoría externa de
  Cowork es el contrapeso — y el flujo invertido del RFD 10 ya demostró que
  funciona en las dos direcciones.

> **Nota de campo, al redactar este RFD (2026-08-07):** el arnés
> `test-skill-paths.py` —escrito ayer para cazar la clase de F13— cazó **una
> línea mía de ayer**: el propio check que añadí a `vault-drift-audit` mandaba
> correr el test por ruta del repo, en una skill que corre desde Cowork. Es la
> **tercera** vez en dos días que esta clase muerde, y la primera que la caza una
> máquina en vez de una jornada perdida. Sirve de evidencia para el patrón que
> este RFD ataca: cuando el arreglo es una convención escrita, vuelve; cuando es
> un arnés, no.

## 8. Trazabilidad

F14→`subagentes/08` §2 · F15→§3 (workstream-dispatch) · F16→§3 (session-close) y
§4(1) · F17→§3 y §4(3) · F18→hallazgo propio al verificar C2 del RFD 10.
Las cinco calificaciones del §1 de ese reporte son la evaluación de las cinco
recomendaciones de `subagentes/07` §5.

---

*RFD 11 de la subserie `auditoria/`. Aprobarlo = arbitrar D1 y D2 + auditoría sin
hallazgos bloqueantes. Implementarlo = prompt aparte, con la auditoría externa de
Cowork al final, como siempre.*
