---
title: RFD 25 — Dos coordinadores en dos frentes, y el gate que tendrían que compartir
tags: [rfd, multiagente, agent-teams, gate, worktree, servidor]
created: 2026-08-14
updated: 2026-08-14
status: abierto
type: rfd
project: atloos
decisiones: [D12, D13, D14]
---

# RFD 25 — Dos coordinadores, y la pieza que de verdad falta

**La petición, literal, del reporte del 2026-08-13:**

> «Sí, una skill para poder usar 2 agentes de Claude Code y trabajar en 2
> frentes a la vez, cada uno orquestando subagentes.»

**Tesis de este documento, en tres frases:**

1. **Lo que pides ya existe**, en dos formas nativas y distintas, y una de las
   dos **no funciona en tu máquina de hoy**.
2. **Ninguna de las dos resuelve tu problema**, porque el cuello no son los
   agentes: es que **el gate corre sobre el árbol de trabajo, que es único**.
3. **La pieza que falta cabe en una línea de código y no la ha pedido nadie**:
   que la evidencia de verde se direccione **por contenido**, no por rama.

---

## 1 · Las tres formas de correr varios agentes, y cuál es cuál

| | Subagentes | **Agent Teams** | **Mensajería entre sesiones** |
|---|---|---|---|
| Qué es | trabajadores dentro de TU sesión | varias sesiones Claude Code coordinadas, con un *lead* | tus sesiones independientes se pasan texto |
| Se hablan entre sí | **no**, solo reportan al principal | **sí**, buzón directo | **sí**, texto plano |
| Lista de tareas | la lleva el principal | **compartida**, con bloqueo de fichero al reclamar | ninguna |
| Quién manda | tú | el *lead*, fijo de por vida | nadie |
| Estado | estable, es lo que usas hoy | **experimental**, apagado por defecto | estable |
| **En tu Windows** | sí | sí | ❌ **NO** |

**Hoy usas la primera.** Un coordinador y hasta 3 subagentes, que es el techo
que tú mismo mediste.

### Lo que responde a tu petición al pie de la letra: Agent Teams

Se enciende con `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` en `settings.json`.
Desde la v2.1.178 no hay paso de creación: describes el equipo y el *lead* lo
levanta. Tú tienes **2.1.231**, así que te sobra versión.

Y sí hace exactamente lo que pediste: **un compañero de equipo puede lanzar sus
propios subagentes.** Lo que no puede es lanzar *compañeros* — no hay equipos
anidados, y el *lead* es uno solo y no se puede traspasar. O sea:

> **«Dos agentes, cada uno orquestando subagentes» = un lead + un compañero,
> cada uno con sus subagentes.** Existe hoy. Con una pega: los subagentes de un
> compañero **corren en primer plano**, no en segundo.

### Lo que responde mejor a tu modelo mental: mensajería entre sesiones

Dos sesiones tuyas de verdad independientes, cada una con su terminal, que se
mandan avisos: *«acabé la migración, ya puedes rebasar»*. Sin lead, sin
jerarquía. `/list-agents` (o `/peers`) las lista, `SendMessage` las escribe.

⚠ **Y aquí está el hallazgo que reordena todo el documento:**

> **La mensajería entre sesiones no existe en Windows nativo.** Solo macOS y
> Linux —WSL 2 cuenta como Linux—. Tu máquina de hoy es Windows 11.

**No es una limitación de diseño nuestro: es de la plataforma.** Y significa
que la forma más limpia de lo que pides **llega con el mini PC**, no antes.

---

## 2 · El cuello no son los agentes

Lo diagnosticó el propio agente en el reporte, y es correcto:

> Los gates son serializados por diseño —`workstream-merge-gate` §4, *«un solo
> agente corre la suite y mergea»*—, así que **mientras el árbol estaba ocupado,
> todo lo demás esperaba**.

Medido esa jornada: **~10 gates, de 228 s a 615 s**, cerca de **una hora de
reloj** con el árbol bloqueado en varios. Y el humano lo dijo antes que nadie:
*«me estorbó que los gates tarden tanto, la RAM, trabajar con distinto worktree
tiene esa desventaja»*.

**Poner dos coordinadores sobre ese diseño no parte la cola en dos: la duplica
delante del mismo cuello.** Y hay algo peor, documentado:

> Los compañeros de un Agent Team **no tienen worktree propio**. La
> documentación oficial lo dice sin rodeos: *«dos compañeros editando el mismo
> fichero produce sobrescrituras; reparte el trabajo para que cada uno sea dueño
> de ficheros distintos»*.

O sea: **Agent Teams reproduce dentro del equipo el problema que
`workstream-dispatch` ya resolvió fuera** —propiedad por fichero—, y **no
resuelve el del gate en absoluto**. La partición por propiedad de fichero
nuestra aguantó 11 frentes con cero conflictos; eso es lo que hay que llevarse,
no tirar.

---

## 3 · La pieza que falta: evidencia direccionable por contenido

Hoy `gate-verde.json` guarda `{branch, sha, ts, cmd}`. **La evidencia está atada
a una rama y a un commit**, así que solo vale para quien esté parado ahí.

Pero lo que la suite verifica **no es la rama: es el árbol**. Y git ya sabe
nombrar un árbol:

```
git rev-parse HEAD^{tree}
```

> **Propuesta P1 — la evidencia lleva el hash del árbol.** Si `gate-verde.json`
> guarda también `tree`, entonces **cualquier agente, en cualquier worktree, en
> cualquier máquina, con ese mismo árbol, está cubierto por ese verde** — y sin
> cambiar una coma del contrato: sigue siendo *«el verde cubre el árbol que
> viaja»*, dicho con más precisión.

**No es una idea nueva en este repo: es la que ya está a medias.** El
`merge-gate-guard` **ya compara el árbol** para no bloquear en falso un
`--squash`, donde el commit es nuevo y el contenido el mismo. La mitad del
razonamiento está escrita; falta llevarla al artefacto.

**Lo que se desbloquea, y no es poco:**

- **Dos agentes comparten un verde** sin correr la suite dos veces. Con ~10
  gates de 228-615 s por jornada, es la mayor devolución de reloj disponible.
- **El worktree deja de invalidar la evidencia.** Hoy, un frente que reconstruye
  el mismo árbol en su worktree tiene que volver a gatear.
- **Resuelve de paso «¿esta rama está integrada?»** — el problema con squash que
  casi te cuesta 29 commits. Con squash el sha cambia y el árbol no; **GitHub
  decía `0 ahead` a cuatro ramas con trabajo real** precisamente porque miraba
  commits. El árbol es la respuesta correcta a esa pregunta.

⚠ **Y el límite honesto**: un árbol idéntico **no garantiza un entorno
idéntico**. Es justo el fallo del worktree que finge verde —mismo árbol, sin el
CSV de 9,6 MB, y la suite salta ~115 tests de más—. Así que la evidencia por
árbol **tiene que llevar además la firma del entorno**: el conteo de tests y de
skips de esa corrida. Eso ya existe a medias en el criterio del reloj (*«la
duración es el detector, el conteo es el diagnóstico»*) y aquí se vuelve
obligatorio, no opcional.

---

## 4 · El punto de aplicación determinista que ya existe y no usamos

Toda la filosofía de este repo es **W3: la convención escrita no muerde, el hook
sí**. Y Agent Teams trae tres hooks que encajan exactamente con eso:

| Hook | Cuándo | Qué hace con `exit 2` |
|---|---|---|
| **`TaskCompleted`** | al marcar una tarea como hecha | **impide completarla** y devuelve el motivo |
| `TaskCreated` | al crear una tarea | impide crearla |
| `TeammateIdle` | cuando un compañero va a quedarse quieto | **lo mantiene trabajando** |

> **Propuesta P2 — el gate como `TaskCompleted`.** Una tarea no se puede marcar
> hecha sin evidencia verde para su árbol. **Es el W3 aplicado al equipo**, y es
> más fuerte que la skill: la skill puede no invocarse —pasó, es el caso de los
> dos merges del 2026-08-07—; un hook no.

Y `TeammateIdle` contesta, gratis, la otra petición del reporte: *«un comando
para ver el estado de todos los subagentes y su avance»*. La asimetría que te
escocía —**tú a ciegas, el agente viendo**— la rompe el panel de compañeros:
flechas para elegir, Enter para abrir su transcripción y **hablarle
directamente**, sin pasar por el lead. Eso es exactamente lo que pediste en el
§8 del reporte, y ya existe.

---

## 5 · Lo que este documento NO recomienda

**No adoptar Agent Teams como modo por defecto**, y las razones son tuyas, no mías:

1. **Es experimental y apagado por defecto**, con límites documentados que te
   morderían: **no sobrevive a `/resume`** —y tu sesión del 13 se compactó y duró
   9 horas—, el estado de las tareas **se queda atrás** y bloquea dependientes, y
   el apagado es lento.
2. **El coste escala lineal con los compañeros.** Tu última sesión: **$361,77**,
   100 % con subagentes, 79 % en sesiones de 8 h o más. **Duplicar
   coordinadores duplica el contexto que se paga**, y todavía no has ejercido ni
   una vez la regla de modelo barato por frente que entró en el sprint 3.
3. **Tu cuello medido es CPU, no agentes.** Con 5 frentes la suite pasó de
   ~330 s a **677 s (×2,05)** por contención, en 8 núcleos. **Dos coordinadores
   con sus subagentes empeoran eso**, no lo mejoran, y el mini PC lleva el mismo
   procesador.
4. **La evidencia externa va en contra.** Sobre 7 frameworks y 200+ trazas:
   **36,94 % de los fallos son desalineación entre agentes** — una clase que
   **no existe si no hay dos agentes**. Y en tu propia jornada, **nueve frentes
   de nueve refutaron una premisa del brief**: *«el desfase no vino del modelo ni
   del código: vino del traspaso»*. **Más agentes = más traspasos.**

> **El orden correcto es al revés del que pide la intuición: primero se hace el
> gate compartible, y solo entonces tiene sentido un segundo coordinador.**
> Con el gate serializado, el segundo coordinador es un segundo cliente para la
> misma cola.

---

## 6 · Propuesta, en tres fases y por orden de retorno

**Fase 1 — el gate direccionable por contenido (P1).** No necesita Agent Teams,
no necesita el servidor, y devuelve reloj desde el primer día. `gate-verde.json`
gana `tree` y la firma del entorno (tests corridos, skips); el guard acepta la
evidencia cuyo árbol coincida. **Es la única fase que recomiendo hacer ya.**

**Fase 2 — el gate como hook de tarea (P2).** Solo tiene sentido con Agent Teams
encendido. Prueba deliberada obligatoria, del estilo de la del 2026-08-07:
montar el equipo, intentar cerrar una tarea sin verde, y **comprobar que no
deja**.

**Fase 3 — dos coordinadores de verdad.** Con mensajería entre sesiones, que
**exige Linux**. Es decir: **en el SER8**, no en la Legion. Y con propiedad de
ficheros disjunta, que es lo único de `workstream-dispatch` que ya está probado
a 11 frentes.

---

## 7 · Decisiones que necesito que arbitres

**D12 · ¿Se hace la fase 1 ahora?** Mi voto: **sí**, y sola. Es la que devuelve
más reloj por línea de código, no depende de nada experimental, y arregla de
paso el problema de «¿esta rama está integrada?».

**D13 · ¿Encendemos Agent Teams para probar, o esperamos a que salga de
experimental?** Mi voto: **probarlo una jornada, en un proyecto que no sea
crítico, y con la prueba deliberada del gate como objetivo**, no para producir.
Encenderlo no cuesta nada; usarlo para trabajo real hoy sí.

**D14 · ¿La fase 3 espera al SER8?** Mi voto: **sí, y no hay alternativa** —la
mensajería entre sesiones no existe en Windows nativo. La única vía de acortarlo
sería WSL 2, que cuenta como Linux; **eso es decisión tuya y tiene su propio
coste**, porque partiría tu entorno de trabajo en dos.

---

## 8 · Lo que no pude comprobar

- **No he encendido Agent Teams ni corrido un equipo.** Todo el §1 y el §4 salen
  de la documentación oficial de la v2.1.178+ y entran como **[AR]** hasta que
  alguien monte uno. La prueba deliberada de D13 es justo para eso.
- **No he medido el ahorro de la fase 1.** El número —cuántos de los ~10 gates
  de una jornada habrían reutilizado un verde ajeno— **solo lo da el campo**, y
  se puede instrumentar barato: contar cuántas veces se gatea un árbol ya
  gateado.
- **El límite de 3 frentes con dos coordinadores no está medido.** Con uno son
  3; con dos no son 6 —el ×2,05 fue por CPU— pero **no sé cuántos son**, y
  suponerlo sería inventarlo.

---

## Fuentes

- [Agent Teams — orquestar equipos de sesiones de Claude Code](https://code.claude.com/docs/en/agent-teams)
- [Mensajería entre sesiones — disponibilidad, límites y `/list-agents`](https://code.claude.com/docs/en/cross-session-messaging)
- [Subagentes](https://code.claude.com/docs/en/sub-agents) · [Worktrees](https://code.claude.com/docs/en/worktrees)
- Reporte de campo 2026-08-13 (`feedback/`, §4, §7 y §8) — los números de gates,
  coste, contención y el «nueve de nueve refutaron».
- `workstream-merge-gate` §4 y `references/criterio-del-reloj.md` — la
  serialización y el conteo como diagnóstico.
