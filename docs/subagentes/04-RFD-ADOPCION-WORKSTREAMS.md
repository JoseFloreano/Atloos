# RFD — Adopción de workstreams paralelos con subagentes

> **Estado:** PROPUESTA — no aprobada, nada instalado.
> **Fecha:** 2026-08-01 · **v3** (mismo día): las 3 preguntas abiertas
> resueltas (piloto = AlphaDogs); **C1 invertido** en v2 (worktree manual, no
> el flag nativo, porque la ruta nativa no es configurable); **C7 añadido** en
> v3 (el anti-drift del vault con N frentes sobre el mismo proyecto).
> W0 queda cerrado salvo declarar el comando de test.
> **Contexto:** `00`–`03` de esta subserie · RFD 02 §4/C4 del puente Telegram ·
> doc 12 (concurrencia) · doc 13 §2 (plugin agent-teams) · R2 de la auditoría.
> **Método:** evaluación de la investigación 00–03; formato de RFD del repo
> (problema → objetivos → casos de diseño → alcance → criterios de éxito).

---

## 1. Problema

La investigación 00–03 dejó claro **qué existe**, pero no **qué hacemos**.
Y el riesgo de no decidir es concreto: cuatro capas de mecanismo disponibles
(nativo, Superpowers, plugin externo, RFD 02) invitan a montar infraestructura
antes de tener un caso de uso que la pague. Sería el anti-patrón que el propio
doc 02 de la serie de memoria describe — sofisticación por delante de la
necesidad.

La pregunta que este RFD responde: **¿cuál es la ruta mínima desde "hoy no
tengo nada" hasta "trabajo con varios frentes en paralelo y mergeo con
criterio", sin construir de más?**

## 2. Evaluación de lo investigado

Tres juicios que ordenan la decisión:

**E1. El mecanismo es un problema resuelto; el criterio de integración no.**
Aislar frentes ya se hace con un flag (`claude --worktree`). Lo que ninguna
capa externa trae es *cuándo se puede mergear esto a `main`* con nuestras
reglas. Toda la inversión propia debe ir ahí, no al aislamiento.

**E2. El eslabón débil es el enforcement, no la documentación.** El repo ya
aprendió esta lección (R2 de la auditoría: "las instrucciones son
probabilísticas; los hooks son garantía"). Una skill que dice "no mergees sin
test verde" es exactamente el tipo de instrucción que se degrada en sesiones
largas — que es cuando más se usa este patrón. El RFD 02 lo resolvió sacando
los git ops del agente y poniéndolos en el daemon; en una sesión normal de
Claude Code no hay daemon, así que la garantía tiene que venir de otro lado.

**E3. Este repo es mal candidato para el piloto.** `ClaudeSetup` es docs +
scripts: no tiene módulos independientes que se presten a ownership por
archivo, ni suite de tests que dé el verde del gate. Pilotar aquí mediría el
mecanismo pero no el valor. El caso real vive en los proyectos de aplicación
(AlphaDogs, RecetIA).

## 3. Objetivos

**O1.** Poder trabajar 2-3 frentes independientes en paralelo, cada uno en su
rama y su worktree, sin que se pisen archivos.

**O2.** Que la integración a `main` tenga un criterio explícito y verificable
— no "el agente dijo que estaba listo".

**O3.** Que cada frente herede las Memory Rules de su proyecto (aislamiento de
`group_id` y vault), sin importar quién lo lanzó.

**O4.** Coste conocido antes de escalar: saber qué cuesta un frente antes de
abrir seis.

**No objetivos:** multi-agente sobre el mismo archivo (prohibido por doc 12,
no cambia); Agent Teams como default para trabajo cotidiano de 1-2 frentes;
orquestador propio desde cero (E1); y aplicar esto al repo `ClaudeSetup` como
caso principal (E3).

## 4. Caso central: dónde vive el gate de merge

Es la decisión que define el resto. Tres opciones:

| | **A. Solo skill** | **B. Skill + hook** *(elegida, por fases)* | **C. Solo hook** |
|---|---|---|---|
| Cómo | `workstream-merge-gate` describe el criterio; el agente lo sigue | La skill trae el criterio y el flujo; un hook `PreToolUse` bloquea `git merge` hacia rama protegida sin evidencia de verde | Hook que bloquea y ya; sin skill |
| Garantía | Probabilística (R2) | Determinista donde importa | Determinista pero ciega |
| Puede explicar el "por qué" | Sí | Sí | No — solo bloquea |
| Costo de construir | Bajo | Medio (skill ya + hook después) | Medio |
| Falla si el agente ignora la instrucción | **Sí** | No | No |

**Elegida: B, en dos tiempos.** Primero la skill (barata, útil de inmediato,
y sirve de especificación de lo que el hook tendrá que verificar); el hook
**solo cuando el piloto demuestre que el criterio se salta en la práctica**.
Escribir el hook antes sería adivinar qué hay que bloquear — y un hook mal
calibrado que bloquea merges legítimos se desactiva a la semana.

C se descarta por lo mismo que el `auditoria/09` descartó "hook sin skill" en otros
frentes: un bloqueo sin explicación no enseña el flujo correcto, solo
frustra. A se descarta por E2.

**Consecuencia aceptada:** entre W1 y W3 el criterio es probabilístico. Es
tolerable porque en esa ventana el humano sigue en el loop de cada merge
(§5, C2).

## 5. Casos de diseño

### C1. Unidad de aislamiento: worktree manual del RFD 02, NO el flag nativo

*(Decidido tras verificar la pregunta 2 del §9 — 2026-08-01. Esta decisión se
invirtió respecto al primer borrador de este RFD.)*

**Hallazgo bloqueante:** la ruta del worktree nativo **no es configurable
hoy**. Claude Code la fija en `.claude/worktrees/<nombre>/` bajo la raíz del
repo, y hay al menos tres feature requests abiertas pidiendo justo esto
(`worktreeDir` #28242, `worktreeRoot` #57738, `claudeDirectory` #33131) — es
decir, reconocido como limitación y sin implementar.

**Por qué importa aquí:** *todos* los repos del caso de uso viven dentro de
OneDrive (`OneDrive\Documentos\...\Proyectos\`), igual que este. Usar el flag
nativo metería un checkout completo por frente dentro de la carpeta
sincronizada — exactamente lo que H8/A1 prohíben y lo que el RFD 02 evitó a
propósito.

**Decisión:** worktrees creados a mano fuera de OneDrive
(`%LOCALAPPDATA%\...`), reutilizando el patrón del RFD 02 §4. No es un rodeo:
ese patrón **ya está escrito, probado y corriendo** — este mismo RFD se está
redactando dentro de uno de esos worktrees. `EnterWorktree`/`ExitWorktree`
siguen sirviendo para *moverse* entre worktrees ya creados; lo que no se usa
es la creación automática con su ruta impuesta.

**Revisar si:** se implementa `worktreeDir`/`worktreeRoot` (entonces el flag
nativo vuelve a ser la opción simple), o si algún repo futuro nace fuera de
OneDrive.

### C2. Quién orquesta

Por fases, y a propósito:

- **W0–W1: el humano.** Abre las sesiones, reparte los frentes, decide el
  orden de merge. El agente no coordina nada. Así se mide el valor del patrón
  sin añadir la variable "¿el orquestador lo hizo bien?".
- **W2+: un agente coordinador**, solo si W1 demostró que repartir a mano se
  vuelve el cuello de botella. Ahí entran `subagent-driven-development` y, si
  hace falta descomposición con ownership explícito, el plugin de wshobson.

### C3. Criterio de merge (contenido del gate)

Heredado de C4 del RFD 02, con una diferencia: allá el botón caduca a 5 min
porque la UI es Telegram; aquí la confirmación es conversacional.

1. Verificación verde (tests/lint del proyecto) **después del último commit**
   del frente. Sin comando de test declarado → no hay verde posible → no se
   mergea.
2. Un frente a la vez, en orden explícito.
3. Squash por defecto.
4. Confirmación humana explícita si el destino es la rama protegida.
5. Limpieza tras integrar (worktree + rama local mergeada).

### C4. Memoria por frente (O3)

En W0–W1 no hace falta skill nueva: cada sesión carga el `CLAUDE.md` de su
worktree por sí sola. `workstream-memory-briefing` (doc 03 §2.2) **solo se
escribe si se llega a W2** con subagentes lanzados programáticamente — antes
de eso sería una skill sin usuario.

⚠ Excepción heredada del RFD 02 §4: si el worktree se crea en una ruta donde
`CLAUDE.md` no viaja (está gitignorado como artefacto de instancia), el frente
nace **sin Memory Rules**. Verificar esto en W1 es criterio de éxito (§7.3).

### C5. Presupuesto y número de frentes (O4)

- Tope duro inicial: **3 frentes simultáneos**. Las fuentes coinciden en que
  pasar de ~5 necesita justificación; 3 es margen conservador para empezar.
- Medir con `ccusage`/`token-audit` el costo real de W1 y contrastarlo con la
  estimación del doc 02 §5 (~$13/día por agente activo, cifra de terceros sin
  réplica — H10). Si el real difiere en más de 2×, el número de frentes se
  revisa antes de W2.

### C6. Qué NO se instala en ninguna fase (salvo disparador explícito)

- Agent Teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`): solo si en W2 los
  frentes necesitan hablar entre sí durante la ejecución, no solo al final.
- Plugin `agent-teams` de wshobson: solo con el protocolo de importación
  completo (`skills/10` §2), y solo si la descomposición manual duele.

### C7. El hook anti-drift con N frentes sobre el MISMO proyecto *(nuevo, v3)*

Consecuencia de elegir un repo **enganchado al vault** (AlphaDogs lo está):
los hooks de anti-drift aplican a cada frente. Con 2-3 worktrees del mismo
proyecto editando código a la vez, cada sesión:

1. marca su propio `.claude/vault-dirty.json` (`mark-code-dirty.py` — es por
   `CLAUDE_PROJECT_DIR`, así que cada worktree tiene el suyo: **no hay
   contención en el flag**), y
2. al cerrar, `check-vault-updated.py` le exigirá actualizar el vault.

Si los tres frentes intentaran actualizar `_PROJECT.md`, se pisarían — es
exactamente el escenario que el doc 12 §P2/P3 describe. **La salida ya existe
y no hay que construir nada**: el hook se da por satisfecho con una nota
propia en `10-Projects/<proyecto>/sessions/<fecha>-<tarea>.md`, y
`session-close` consolida después.

**Implicación operativa para W1:** cada frente escribe su nota de sesión, no
`_PROJECT.md`. El coordinador (o el humano, en W1) consolida al final, tras
el merge. Este piloto es de paso **la primera prueba real de la vía
multi-agente del hook**, que hasta ahora solo existía en el código y en el
doc — un beneficio colateral de haber elegido un proyecto del vault.

## 6. Fases

| Fase | Contenido | Esfuerzo |
|---|---|---|
| **W0** | ~~Verificar C1~~ (§9.2) y ~~elegir repo piloto~~ (§9.1: AlphaDogs). Queda: declarar su comando de test y elegir los 2 frentes. | ~15 min |
| **W1** | Piloto manual: 2 frentes reales en el proyecto elegido, sin instalar nada. Gate de merge aplicado **a mano**. Medir costo. | 1 sesión real |
| **W2** | Solo si W1 salió bien: escribir `workstream-merge-gate` (`shared/`) destilando lo que se hizo a mano. ADR si cambia el flujo de git del proyecto. | ½ día |
| **W3** | Solo si el criterio se saltó en la práctica: hook de enforcement (§4, opción B). `workstream-memory-briefing` solo si se llegó a orquestación programática. | ½ día |

Cada fase es un gate: si W1 no aporta valor medible, no hay W2 — y la
investigación 00–03 queda como registro de por qué no.

## 7. Criterios de éxito

1. **W0:** repo piloto elegido con comando de test declarado, y sus worktrees
   resuelven fuera de OneDrive (C1).
2. **W1 (aislamiento):** un archivo modificado y sin commitear en un frente
   queda byte-idéntico tras trabajar en el otro (hash antes/después) — mismo
   criterio que usó el RFD 02 §8.2.
3. **W1 (memoria):** cada frente ve las Memory Rules de su proyecto
   (comprobable pidiéndole que las cite).
4. **W1 (valor):** el trabajo en paralelo terminó antes que la estimación
   secuencial, o la diferencia fue lo bastante clara para justificar W2. Si
   no, se documenta y se para.
5. **W1 (costo):** hay una cifra propia de `ccusage` para comparar con la
   estimación de terceros.
6. **W1 (anti-drift, C7):** cada frente cierra con su nota en `sessions/` sin
   pelearse por `_PROJECT.md`, y el hook Stop queda satisfecho en los dos.
7. **W2:** el gate rechaza un merge sin verde en una prueba deliberada.
8. **W3 (si llega):** el hook bloquea `git merge` hacia `main` sin evidencia
   de verde, y no bloquea un merge legítimo.

## 8. Riesgos de esta propuesta

- **Que W1 nunca ocurra.** Es el riesgo más probable: el patrón es
  interesante en abstracto y el caso de uso real puede no aparecer en meses.
  Mitigación honesta: si a los ~2 meses no hubo W1, esta subserie se marca
  como investigación archivada, no como pendiente vivo.
- **Sobre-ingeniería por entusiasmo:** saltarse W1 e ir directo a escribir las
  dos skills. El gate de fases existe justo para eso.
- **Que el gate sea inaplicable** en proyectos sin suite de tests — en cuyo
  caso el criterio de verde hay que redefinirlo (¿build? ¿lint?) o el patrón
  no aplica a ese repo.

## 9. Preguntas — todas resueltas (2026-08-01)

1. ~~¿En qué repo se hace el piloto?~~ **RESUELTA (usuario, 2026-08-01):
   AlphaDogs**, que además ya está enganchado al vault con su propia carpeta
   en `10-Projects/`. Cumple los dos criterios: suite de pytest amplia
   (`tests/memory`, `tests/content`, `tests/core`, `tests/agents`…) que da un
   verde real al gate, y fronteras de módulo claras para repartir frentes sin
   solape. Consecuencia de estar en el vault: aplica C7.
2. ~~¿La ruta de `.claude/worktrees/` es configurable?~~ **RESUELTA
   (2026-08-01): NO.** Hardcodeada bajo la raíz del repo; feature requests
   abiertas sin implementar. Consecuencia: C1 invertido — se usa el worktree
   manual del RFD 02, no el flag nativo. Ver C1.
3. ~~¿"Rama protegida" es siempre `main`?~~ **RESUELTA (usuario,
   2026-08-01): sí, siempre `main`.** Simplifica el hook de W3: no necesita
   configuración por repo, la rama destino es constante.

---

*RFD 04 de la subserie `subagentes/`. Promoverlo a decisión = ejecutar W0 y
responder las tres preguntas del §9; registrar con `adr-writer` si se adopta.*
