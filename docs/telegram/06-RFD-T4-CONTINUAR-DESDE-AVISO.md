# RFD — T4: continuar la conversación en Telegram tras un aviso

> **Estado:** IDEA REGISTRADA — no diseñada en detalle, no aprobada.
> Horizonte: después de T2 (auditado) y T3 base (daemon 24/7).
> **Origen:** idea del usuario (2026-08-01), refinada en conversación —
> descartó "resumir la sesión exacta" por chocar con el aislamiento de T2 y
> propuso crear una copia con rama, igual que T2, pero disparada desde un
> aviso.
> **Contexto:** `00-DISENO-TELEGRAM-BRIDGE.md` §1 (vía 1, avisos) ·
> `02-RFD-T2-MODO-ESCRITURA.md` (aislamiento por worktree) ·
> `03-RFD-T5-DESARROLLO-PARALELO.md` (T5 — antes T4, renumerado hoy para
> dejar este hueco libre).

---

## 1. La idea, en palabras del usuario

Hoy "mándamelo por Telegram" (T0) es de una sola vía: Claude avisa y ahí
termina. La idea: que cada aviso incluya un comando corto para **seguir
conversando desde ahí** — pero no reanudando la sesión original (eso pisaría
tu árbol real, ver §2), sino creando una conversación T2 nueva (rama +
worktree) **con un traspaso de contexto ya redactado**, para que no arranque
en frío.

La ventaja no es solo ahorrarte los pasos de `/p` + `/new` — es que la
conversación nueva ya sabe qué se hizo y en qué quedó, así que responder se
siente como seguir la misma charla y no como explicarle todo de nuevo a un
agente que no vio nada.

## 2. Por qué NO es "reanudar la sesión" (y por qué eso está bien)

La sesión que dispara el aviso corre en tu carpeta real, con permisos y
cambios sin guardar que le pertenecen solo a ella. Si "continuar" reanudara
esa sesión literal con permiso de escribir, se rompería la regla que T2
dejó firme a propósito: el bot nunca toca tu árbol de trabajo.

Al crear una copia con rama (worktree), este T4 **no es un caso especial**:
es una conversación T2 más, solo que la origina un aviso en vez de un
`/new` manual. Hereda sus reglas de permisos, aislamiento y comandos
(`/write`, `/diff`, `/commit`, `/test`, `/push`, `/merge`) sin tocarlas.

## 3. Los dos costos, y por qué van separados

Tratar "generar el traspaso" y "crear la copia" como un solo paso es lo que
hace cara la idea si el aviso nunca se continúa. Van separados:

### 3.1 El traspaso de contexto (barato — no es una llamada nueva)

El aviso que ya se manda por Telegram ("terminé X, hice Y") **ya es un
resumen** de lo que pasó; esa llamada ocurre de todos modos, se continúe o
no. En vez de una llamada aparte para "decidir cómo continuar", la MISMA
llamada que redacta el aviso agrega 3-4 líneas de traspaso: qué se tocó, en
qué quedó, próximo paso sugerido. Costo marginal, no una llamada nueva.

Esas 3-4 líneas se guardan junto con el aviso (proyecto, rama/commit de
origen, timestamp) — nada de git todavía.

### 3.2 La copia con rama (gratis en tokens, pero perezosa)

Crear la rama y el worktree no necesita LLM, solo es trabajo de git — pero
sigue siendo trabajo que queda huérfano si nadie lo usa. Se crea **solo
cuando llega el comando de continuar**, nunca al momento del aviso. Así, un
aviso que nadie retoma no dejó ninguna rama ni carpeta sueltas — solo texto
barato que de todas formas se iba a mandar.

## 4. Flujo propuesto

1. Termina una tarea con "mándamelo por telegram" (T0). La misma llamada que
   redacta el aviso también redacta el traspaso corto (§3.1).
2. El aviso se manda con un ID corto y una línea al final:
   `Para seguir aquí: /pickup 7f3a`
3. Si el usuario nunca manda ese comando: no pasó nada más. Sin rama, sin
   worktree, sin costo extra.
4. Si lo manda: el daemon (que ya tiene que estar corriendo — ver §6) crea
   la rama + worktree como en T2, copia `CLAUDE.md`, inyecta el traspaso
   como primer contexto de la conversación nueva, y la deja activa para ese
   chat. Responde confirmando con el traspaso a la vista, listo para que el
   usuario mande su siguiente mensaje.

## 5. Por qué hace falta un ID corto (no basta "el último aviso")

Si se mandan dos avisos seguidos (dos tareas distintas terminando), "sigue
aquí" a secas es ambiguo: no se sabe a cuál de los dos te refieres. Cada
aviso necesita un identificador corto propio (ej. `/pickup 7f3a`), no un
`/continue` genérico que dependa de asumir "el último".

## 6. Dependencia con T1: el daemon tiene que estar corriendo

T0 hoy no necesita nada escuchando — solo manda el POST y termina. Para que
`/pickup <id>` funcione, algo tiene que estar escuchando Telegram: eso es
el daemon de T1. **T4 no puede ser standalone**; asume que el puente
completo ya está encendido. Es un cambio de expectativa respecto a T0 (que
hoy es "cero infraestructura") y debe quedar explícito en el ADR cuando se
formalice.

## 7. Lo que se pierde y hay que dejar dicho, no asumido

- **Los cambios sin guardar del árbol real no viajan a la rama nueva** — la
  rama nace del último commit. El traspaso de §3.1 debería mencionar si
  había cambios sueltos en la sesión original, para que no se pierdan sin
  que el usuario se entere, aunque no los cargue físicamente. Llevarlos de
  verdad a la rama nueva (parche/stash) queda fuera de este RFD.
- **Ofertas de "pickup" sin usar se acumulan** si nadie las limpia. Necesita
  una expiración (ej. las de más de N días dejan de ser válidas y el ID se
  reporta como vencido) — mismo espíritu que la reconciliación de
  worktrees huérfanos de T2.

## 8. Qué NO es esta idea

- No reemplaza `/p` + `/new` para arrancar trabajo nuevo sin partir de un
  aviso — sigue siendo el camino normal.
- No es el paralelismo de T5 (varias conversaciones en vuelo a la vez): T4
  crea UNA conversación nueva por aviso retomado; seguir usándola en
  paralelo con otras cae bajo las reglas (o falta de ellas) de T5.

## 9. Prerrequisitos antes de diseñarla en serio

- [ ] T2 auditado y estable (esta idea es, estructuralmente, "otra
      conversación T2" — no tiene sentido construirla sobre una base sin
      auditar).
- [ ] Daemon corriendo de forma confiable (T3 base: autoarranque), porque
      T4 depende de que siempre esté escuchando.

## 10. Preguntas abiertas para cuando se diseñe en serio

1. ¿Cuánto vive un ID de "pickup" antes de expirar?
2. ¿El traspaso corto se le muestra al usuario dentro del aviso mismo, o
   solo al confirmar el `/pickup`?
3. ¿`/pickup` puede fallar si la rama de origen ya no existe (se hizo
   `/done` o `/merge` de esa conversación mientras tanto)? ¿Qué se reporta?

## 11. Debug 2026-08-01 — "mándamelo" creaba archivos en vez de entregarlos

Encontrado al usar el puente en esta misma sesión: al pedir "mándame un
resumen en un md", el agente escribía el archivo en `docs/` del repo (vía
`Write`) en vez de responder con el contenido. El usuario nunca lo veía —
el daemon no vigila el disco, solo entrega la respuesta de texto.

**No es un bug de código.** Revisado `tg_daemon.py` / `notify_telegram.py`:
`deliver_text()` ya es la política de entrega completa de T0 y T1 — manda
la respuesta como mensaje si son ≤4096 caracteres, o genera un `.md` y lo
adjunta con `sendDocument` automáticamente si es más larga. **No depende de
ninguna herramienta ni de modo lectura/escritura**: solo depende de qué
texto ponga el agente en su respuesta. Es exactamente el mecanismo que este
RFD necesita para el traspaso (§3) y para confirmar un `/pickup` — ya existe
y no hay que construir nada nuevo para "entregar contenido largo".

**La causa era de criterio, no de infraestructura**: el agente interpretaba
"mándamelo" como "crear el archivo pedido" (patrón normal de una sesión de
escritorio) en vez de "responder con el contenido" (lo único que se entrega
por este canal). Las Memory Rules del CLAUDE.md de este proyecto prohíben
escribir en el vault, pero no dicen nada sobre crear archivos sueltos en
`docs/` cuando lo pedido es que se entregue por chat — ese hueco es la
causa de fondo.

**Fix propuesto (no aplicable desde este worktree — CLAUDE.md real vive en
el árbol del usuario, fuera de alcance):**

> Si el usuario pide que le mandes/envíes algo (resumen, reporte, archivo),
> respóndelo directo en el chat — el daemon lo entrega solo (mensaje o
> adjunto `.md` si es largo). No crear archivos en el repo salvo que pida
> explícitamente guardarlo/documentarlo.

Relevante para T4 en concreto: cuando se implemente, la confirmación de
`/pickup` y el traspaso mismo deben construirse como texto de respuesta
normal (dejar que `deliver_text()` lo entregue), no como archivo escrito en
el worktree nuevo — sería el mismo bug otra vez, ahora dentro de T4.

---

*Renumeración 2026-08-01: lo que antes se mencionaba de forma informal como
"T4" (desarrollo paralelo multi-proyecto) pasó a ser T5 —
`03-RFD-T5-DESARROLLO-PARALELO.md` (renombrado físicamente el 2026-08-01,
junto con este RFD, que pasó de `05-` a `06-` para no chocar con el T3).
requiere `git mv`, fuera del alcance de bash permitido en este modo).*
