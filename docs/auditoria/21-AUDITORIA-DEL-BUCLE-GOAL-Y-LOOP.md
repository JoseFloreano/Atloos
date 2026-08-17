# Auditoría de la implementación del bucle (`/goal` y `/loop`)

> **Fecha:** 2026-08-11 · **Autor:** Claude Code (sesión del puente Telegram).
> **Alcance:** lo que el RFD 18 (`ecosistema/18-RFD-EL-BUCLE-GOAL-Y-LOOP.md`)
> propuso y lo que quedó en el disco: las cuatro piezas P1–P4, la arbitración de
> D1 y D2, el cableado, el arnés y los dos hooks vecinos de `Stop`.
> **Método:** lectura del RFD y del código, y verificación cruzada de cada
> afirmación contra el fichero que la sostiene. Las citas llevan `fichero:línea`.
> **Base:** el árbol de trabajo de la rama `tg/20260811-…`. **Sin sha**: esta
> sesión no tuvo shell, así que no hay `git rev-parse` que citar.
>
> ⚠ **Lo que esta auditoría NO hizo, y cambia cómo hay que leerla:** no corrió
> el arnés. `test-goal-evidence-guard.py` declara 20 casos y el `README` de
> hooks los da por buenos; **yo leí el código, no vi el verde**. Por la ley 1 de
> la casa, eso me pone del lado del reporte y no del artefacto: donde digo
> "el arnés cubre X" léase "el arnés *declara* cubrir X". El primero que corra
> `py setup/hooks/tests/test-goal-evidence-guard.py` cierra ese hueco.

---

## 0. Veredicto

**Implementación fiel al RFD y de buena factura, con un agujero en el sitio
exacto que la pieza venía a tapar.**

Las cuatro piezas existen, están cableadas y tienen arnés. D2 —la avería que el
RFD midió sin arreglar— se arbitró de verdad y con evidencia: el caso E.3 pasó
de documentar el fallo a fijar su ausencia. El canario existe y es el caso
correcto.

Pero el guard comprueba que la evidencia **existe y es fresca**, no que **diga
verde** (H1), y solo protege a quien pasó por `goal-forge` (H3). Es decir: la
ley 1 se cuela un nivel más abajo, y la defensa es opt-in por convención — que
es literalmente el fallo que `auditoria/11` acaba de nombrar.

Ninguno de los ocho hallazgos pide rediseño. Los dos primeros son un caso de
arnés y unas veinte líneas de hook cada uno.

| Pieza del §12 del RFD | Estado |
|---|---|
| **P1** `goal-forge` | ✅ `setup/skills/claude-code/goal-forge/` — `SKILL.md` con los 5 puntos + `references/mecanica-goal.md` |
| **P2** `goal-evidence-guard` | ✅ `setup/hooks/goal-evidence-guard.py`, cableado en `sync-hooks.ps1:41`, con `.claude/goal.json` en `.gitignore:11` |
| **P3** `loop.md` de la casa | ✅ `.claude/loop.md` (~3 KB de los 25 KB de tope) |
| **P4** condición de meta en el despacho | ✅ `workstream-dispatch/references/plantilla-despacho.md:195-223` |
| **D1** ¿envuelto o desnudo? | ✅ arbitrada (b): envuelto, con canario |
| **D2** ¿qué dispara el anti-drift? | ✅ arbitrada (b): por ediciones sin registrar |
| **D3** navegador · **D4** mini PC | ⬜ fuera del alcance de esta auditoría |

---

## 1. Lo que está bien, y por qué cuenta

**El contrato sha↔HEAD se heredó entero.** `goal-evidence-guard.py:148-156`
aplica al cierre de turno el mismo criterio que `merge-gate-guard` aplica al
merge: una evidencia anterior al último commit no es evidencia de este estado.
No es una reimplementación: es la misma primitiva movida de evento, que es
justo lo que pedía C10 de `auditoria/19`.

**El guard tiene fondo.** `MAX_BLOQUEOS = 3` (`:48`) y, al agotarse, sale
ABIERTO **diciendo por qué** (`:124-130`): a esa altura el problema ya no es que
falte evidencia, es que la condición está mal forjada. Un guard sin cláusula de
corte es otro bucle sin fondo, y este no lo es.

**El mensaje de bloqueo enseña.** `:76-89` no dice "denegado": nombra la
condición forjada, el comando que la prueba, por qué el evaluador de `/goal` la
cerraría y cuántos bloqueos quedan. El arnés lo fija como aserción propia
(`test-goal-evidence-guard.py:182-183`), que es la forma correcta de impedir que
un mensaje útil se degrade a un `exit 2` seco.

**D2 se arregló midiendo, no opinando.** `check-vault-updated.py:17-32` explica
la avería y la arbitración; `:174-199` la implementa con `edits` (tamaño de la
deuda) y `silenced_at` (dónde se agotó la última tanda), re-armando cada
`VAULT_DRIFT_EVERY` ediciones —10 por defecto (`:42`)— y con `0` como escotilla
explícita al comportamiento viejo. El anti-drift dejó de apagarse en el
escenario que más lo necesita. Además el hook ganó arnés propio
(`tests/test-check-vault-updated.py`) en vez de seguir viviendo prestado en §E
del arnés del vecino.

**El canario es el caso correcto** (`test-goal-evidence-guard.py:223-241`):
condición *"los tests pasan"*, suite en rojo, sin evidencia en disco → exit 2.
Es la prueba que separa esta implementación de `/goal` desnudo, y está donde
tiene que estar.

---

## 2. Hallazgos

### H1 · El guard comprueba existencia y frescura, no veredicto — ALTA

`goal-evidence-guard.py` verifica tres cosas: que el artefacto existe (`:133`),
que su `sha` casa con HEAD (`:148-155`) y, si no lleva `sha`, que se escribió
después de forjar la meta (`:162-169`). **En ningún punto mira si el artefacto
dice que el comando salió bien.** La cabecera lo declara —*"No juzga la calidad
de la evidencia"* (`:31`)— pero la consecuencia no está dicha.

Con `gate-verde.json` da igual, y por una razón concreta: `gate-test.py:99-109`
**solo escribe el fichero con exit 0**; en rojo no escribe nada y lo dice. Ahí
existir *es* el veredicto, y por eso el patrón funciona.

El problema es que **el contrato de `goal-forge` no exige esa semántica**. Sus 5
puntos (`SKILL.md:29-41`) piden "el comando que lo prueba", no "un artefacto que
solo existe si el comando salió 0". Y el propio arnés usa como caso legítimo
`` `ruff check .` deja salida.txt`` (`test-goal-evidence-guard.py:210` y `:216`)
— un artefacto que `ruff` escribe igual en verde que en rojo. Una meta forjada
así **cierra con la suite rota**: el guard ve el fichero, ve que es posterior a
la meta, y abre.

Es la ley 1 colándose un nivel por debajo de la pieza que existe para impedirlo.

**Fix propuesto:** un 6º punto en el contrato de `goal-forge` — *"el artefacto no
debe existir (o no debe actualizarse) si el comando falló; si no puedes
garantizarlo, envuélvelo con `gate-test.py`"* — y un caso en el arnés que lo
fije: artefacto presente pero con veredicto rojo dentro → bloquea. Cambiar
además el ejemplo de `salida.txt` del arnés, que hoy enseña el anti-patrón.

### H2 · Una meta muerta sigue guardando — MEDIA

`/goal` es de sesión: una meta activa por sesión, y muere cuando la sesión
muere (`SKILL.md:56`, RFD §7.1). Pero `.claude/goal.json` es un fichero en
disco **sin dueño**: no lleva `session_id`, y el hook recibe el del payload y lo
descarta a propósito (`:100`, *"payload Stop: se valida, no se usa"*).

Consecuencia concreta: forjas una meta hoy, no la cumples, cierras. Mañana, en
cualquier sesión de ese proyecto —incluida una que no use `/goal`— los tres
primeros cierres de turno se bloquean por una meta que ya no existe. Y
`/goal clear` no borra el fichero: `goal-forge` no tiene paso de limpieza
(`SKILL.md:43-52`).

El hook hermano ya resolvió exactamente esto:
`check-vault-updated.py:120-127` compara `state["session_id"]` con el del
payload y **borra el flag huérfano** antes de decidir nada.

**Fix propuesto:** `goal-forge` escribe `session_id`; el guard, si no casa,
borra `goal.json` y sale 0. Un caso en el arnés (meta de otra sesión → no
interviene y el fichero desaparece). Es el mismo gesto, copiado del vecino.

### H3 · La protección es opt-in por convención — MEDIA

El guard solo actúa si existe `goal.json` (`:111-112`), y `goal.json` solo
existe si se pasó por `goal-forge`. Un `/goal …` escrito a mano —lo natural, lo
que hará cualquiera con prisa— no deja rastro en disco: el guard fail-opens y
queda `/goal` desnudo, con un evaluador que cierra metas leyendo reportes.

Está **declarado** en D1·b del RFD (*"mitigable con fail-open fuera de las
condiciones que sí lo nombran"*), así que no es una sorpresa. Pero nada detecta
la ausencia, y esa es la diferencia entre un hueco conocido y un hueco medido.
Es, punto por punto, el patrón que `auditoria/11` bautizó —arreglamos el caso,
no la clase— y el sesgo que el propio autor del RFD 18 declaró en su §17.

No hay fix barato y correcto: el payload de `Stop` no trae la condición de la
meta, así que el hook no puede saber que hay un `/goal` activo sin forjar. Lo
que sí es barato es la honestidad:

- que `goal-forge` y `hooks/README.md` digan **en primera línea** que sin forjar
  no hay guard;
- que el criterio de éxito §16.1 del RFD se anote como *"probado en laboratorio,
  no en campo"* hasta que exista una jornada real.

### H4 · El campo `turnos` se escribe y nadie lo lee — MEDIA

`goal-forge` manda escribirlo (`SKILL.md:48`) y el arnés lo escribe
(`test-goal-evidence-guard.py:72`). **Ningún consumidor lo usa**: el guard no lo
lee, y la cláusula de corte real vive en el texto de la condición, impuesta por
`/goal`. Es un campo decorativo que aparenta control — y un campo que aparenta
control es peor que no tenerlo, porque el siguiente lector asume que alguien
cuenta los turnos.

**Fix:** o se usa (el guard puede avisar al acercarse al tope) o se quita del
contrato.

### H5 · `goal-forge` y `requirements-designer` no tienen fila en el registro — MEDIA

`setup/skills/README.md:63-95` tiene 31 filas —21 `shared/` + 10
`claude-code/`— y **ninguna es `goal-forge` ni `requirements-designer`**, las dos
skills nacidas con el bucle. La regla del propio fichero (`:101-105`): *"toda
skill nueva añade su fila en el mismo PR"* y *"si una fila falta, el perfil bot
la excluye por defecto"*.

O sea: hoy el bot no las ve **por omisión, no por decisión**. Para `goal-forge`
la exclusión probablemente es la correcta —el guard sale 0 con `CLAUDE_TG_BOT`
(`:96-97`), así que en una sesión del bot forjarías metas sin guard, que es el
peor de los dos mundos— pero eso merece una fila con su motivo escrito, no un
hueco.

Es exactamente **F0** (D7 de `auditoria/19`): el catálogo que no distingue lo
construido de lo propuesto, y que se votó hacer **antes** del bucle
precisamente para que `goal-forge` naciera vigilada. Nació sin vigilar.

### H6 · Fail-open mudo si git no responde — BAJA

`goal-evidence-guard.py:148-156`: si el artefacto trae `sha` pero
`git rev-parse HEAD` falla —repo sin git, git ausente, timeout de 10 s—,
`git_head` devuelve `""` (`:62-63`), la condición `if head and …` es falsa y el
hook sale 0 **sin decir nada**. El chequeo fuerte se degrada en silencio a "el
fichero existe".

Es coherente con el fail-open de la casa, pero no está declarado en la cabecera
junto a los otros dos y no tiene caso en el arnés. Un fail-open que nadie
escribió es indistinguible de un bug.

### H7 · Las versiones mínimas están documentadas, no comprobadas — BAJA

`hooks/README.md:224-226` fija las tres dependencias —`/goal` v2.1.139+, el
`stop: true` de `ScheduleWakeup` v2.1.202+, el filtro de skills auto-invocables
v2.1.196+— y dice *"conviene comprobar en `setup-new-machine`"*. Ni
`setup-new-machine.ps1` ni `setup-new-machine.sh` mencionan ninguna. En una
laptop con Claude Code viejo, `/goal` simplemente no existe y el fallo es
silencioso. El RFD lo pidió en su §17 y quedó a medias: la mitad documental
sí, la ejecutable no.

### H8 · Un criterio de éxito de cuatro — INFORMATIVO

El §16 del RFD puso cuatro varas medibles. Estado real:

| # | Criterio | Estado |
|---|---|---|
| 1 | El canario: una meta con condición falsa no se cierra | ✅ en el arnés (§C) — *declarado, no corrido por mí* |
| 2 | Una jornada real en `/loop` con `loop.md`, y el número de disparos del anti-drift contado | ❌ sin evidencia |
| 3 | Un frente despachado corriendo en `/goal` sin humano, con `main` intacta | ❌ sin evidencia |
| 4 | Coste del bucle medido contra la misma tarea a mano | ❌ sin evidencia |

**La maquinaria está construida y probada en laboratorio; no hay evidencia de
campo** — que es la vara que el propio RFD puso, y la que distingue "funciona"
de "creemos que funciona".

Del §15.1 (seguridad, primer paso del orden de trabajo): `docs/tmp/` sí está
ignorado y la regla sí está commiteada (`.gitignore:44-49`, con el motivo
escrito). Pero **el fichero con el JWT sigue en disco y viajando por OneDrive**;
ignorar no es borrar. La revocación del token en altari.ai no es verificable
desde aquí y sigue siendo el paso pendiente.

---

## 3. Qué hacer, en orden

1. **H1** — el 6º punto del contrato de `goal-forge` + su caso de arnés, y
   cambiar el ejemplo `salida.txt` que hoy enseña el anti-patrón. Es el único
   hallazgo que deja pasar una meta falsa.
2. **H2** — `session_id` en `goal.json`, borrado del huérfano, caso en el arnés.
   Copiar el gesto de `check-vault-updated.py:120-127`.
3. **Correr el arnés** y pegar la salida. Mientras no exista ese verde, esta
   auditoría y el `README` de hooks son dos reportes sobre un artefacto que
   nadie miró.
4. **H5** — las dos filas del registro, con motivo. Cierra F0 para las skills
   del bucle.
5. **H4** y **H6** — decidir `turnos` (usarlo o quitarlo) y declarar el
   fail-open de git.
6. **H7** — la comprobación de versión en `setup-new-machine`.
7. **H3 y H8** — no se arreglan con código: se arreglan con una jornada real de
   `/loop` que produzca los criterios 2, 3 y 4. Hasta entonces, decirlo así.

---

## 4. Nota de higiene del índice (fuera de alcance, pero visto)

`docs/00-INDICE-GENERAL.md` **no lista los cuatro docs más recientes**:
`skills/17`, `ecosistema/18`, `auditoria/19` y `telegram/20`. Este doc (21) sí
se añadió. No los añadí yo porque tres de ellos han cambiado de estado desde que
se escribieron —el 18, sin ir más lejos, sigue marcado 🔴 *"Propuesta — pide
decisión"* cuando D1 y D2 ya están arbitradas y P1–P4 construidos— y un índice
que declara mal el estado es peor que uno incompleto. **Decidir el estado de esos
cuatro es del usuario, no de esta auditoría.**
