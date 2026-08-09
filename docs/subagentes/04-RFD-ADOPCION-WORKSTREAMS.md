# RFD — Adopción de workstreams paralelos con subagentes

> **Estado:** **W1 ✓ de facto · W2 EJECUTADA · W3 no disparado.**
> Pendiente de auditoría externa: hasta que cierre, el RFD **no se cosecha**.
> **Fecha:** 2026-08-05 · **v4** — W1 ocurrió de facto el **2026-08-04**: una
> jornada con **22 despachos** sobre dos planes y **8 ramas fusionadas sin un
> solo conflicto de código**, usando el SDD interno de Superpowers. No se
> planificó como piloto; dejó evidencia escrita
> (`subagentes/05-LIMITACIONES-OBSERVADAS.md`). W2 se ejecutó a partir de esa
> evidencia: `workstream-dispatch` y `workstream-merge-gate` en
> `setup/skills/shared/`.
> **v3** (2026-08-01): 3 preguntas resueltas (piloto = AlphaDogs); **C1
> invertido** en v2 (worktree manual, no el flag nativo); **C7 añadido**.
> **Contexto:** `00`–`03` de esta subserie · **`05-LIMITACIONES-OBSERVADAS.md`**
> (evidencia empírica, 22 despachos) · **`06-INVESTIGACION-EXTERNA-MULTIAGENTE.md`**
> (investigación externa; sus ①–⑩ están integrados en las skills) ·
> `ADR-20260801-puente-telegram` (worktree + gate de merge) ·
> doc 12 (concurrencia) · doc 13 §2 (plugin agent-teams) · R2 de la auditoría.
> **Método:** evaluación de la investigación 00–03; formato de RFD del repo
> (problema → objetivos → casos de diseño → alcance → criterios de éxito).

---

## 1. Problema

La investigación 00–03 dejó claro **qué existe**, pero no **qué hacemos**.
Y el riesgo de no decidir es concreto: cuatro capas de mecanismo disponibles
(nativo, Superpowers, plugin externo, `ADR-20260801-puente-telegram`) invitan a montar infraestructura
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
largas — que es cuando más se usa este patrón. El `ADR-20260801-puente-telegram` lo resolvió sacando
los git ops del agente y poniéndolos en el daemon; en una sesión normal de
Claude Code no hay daemon, así que la garantía tiene que venir de otro lado.

**E3. Este repo es mal candidato para el piloto.** `Atloos` es docs +
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
orquestador propio desde cero (E1); y aplicar esto al repo `Atloos` como
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

### C1. Unidad de aislamiento: worktree manual del `ADR-20260801-puente-telegram`, NO el flag nativo

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
sincronizada — exactamente lo que H8/A1 prohíben y lo que el `ADR-20260801-puente-telegram` evitó a
propósito.

**Decisión:** worktrees creados a mano fuera de OneDrive
(`%LOCALAPPDATA%\...`), reutilizando el patrón del `ADR-20260801-puente-telegram` (worktree por conversación). No es un rodeo:
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

> **Actualización (2026-08-05).** El coordinador-agente **ya existe de facto**:
> es el `subagent-driven-development` interno de Superpowers, que fue lo que
> movió los 22 despachos del 08-04 sin que nadie lo decidiera como fase. Lo que
> W2 añade NO es un orquestador propio —eso sería reconstruir lo que ya
> funciona— sino una **capa encima**: `workstream-dispatch`, con lo que SDD no
> trae y la evidencia exigió (estado del mundo generado, ownership por archivo,
> presupuesto con número, predicción, y escalación por categoría con juez).
> El plugin de wshobson **sigue sin instalarse**: sus tres mecanismos útiles
> (file-ownership, contratos de interfaz, gate de partición) se adoptaron como
> texto en la skill, sin traer su runtime (doc 06 §1.3).

### C3. Criterio de merge (contenido del gate)

Heredado de C4 del `ADR-20260801-puente-telegram`, con una diferencia: allá el botón caduca a 5 min
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

⚠ Excepción heredada del `ADR-20260801-puente-telegram` (worktree por conversación): si el worktree se crea en una ruta donde
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
| **W1** | ✅ **Ocurrida de facto el 2026-08-04**: 22 despachos, 2 planes, 8 ramas fusionadas, 0 conflictos de código. No fue el piloto planificado (no fue AlphaDogs ni 2 frentes acordados), pero produjo la evidencia que W2 necesitaba — `05-LIMITACIONES-OBSERVADAS.md`. | 1 jornada real |
| **W2** | ✅ **Ejecutada el 2026-08-05**: `workstream-dispatch` (+3 references) y `workstream-merge-gate` en `setup/skills/shared/`, destiladas del §3 del doc 05 y enriquecidas con los ①–⑩ del doc 06. **Sin ADR todavía**: la cosecha está gateada a la auditoría externa. | ½ día |
| **W3** | ⛔ **NO disparado.** Su disparador es "el criterio de merge se saltó en la práctica", y no es lo que muestra la evidencia: los fallos del 08-04 fueron de **traspaso** (brief con premisa falsa, reporte sin artefacto, deriva entre paralelos), no del criterio de integración. Un hook que bloquea `git merge` no habría evitado ninguno. Sigue gateado a su disparador original. | — |

Cada fase es un gate: si W1 no aporta valor medible, no hay W2 — y la
investigación 00–03 queda como registro de por qué no.

> **Lección sobre los gates mismos (2026-08-05):** W1 no ocurrió como se
> planeó — ocurrió sola, en otro repo y sin declararse. El gate funcionó igual
> porque lo que exigía era **evidencia**, no ceremonia. Un gate que hubiera
> exigido "ejecutar el piloto tal como está escrito" habría declarado W1
> pendiente teniendo 22 despachos documentados encima de la mesa.

## 7. Criterios de éxito

Estado al 2026-08-05. **Solo se marca lo que tiene artefacto**; lo demás queda
abierto y dicho, porque W1 ocurrió sin instrumentarse como piloto.

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | **W0:** repo piloto con comando de test declarado, worktrees fuera de OneDrive | ⚠️ parcial | Los worktrees resuelven fuera de OneDrive (C1, ya en uso). El piloto NO fue AlphaDogs |
| 2 | **W1 aislamiento** | ✅ **CUMPLIDO** | **8 ramas fusionadas sin un solo conflicto de código** (doc 05 §2). Lo que sí colisionó fue lo *compartido*: `.git`, la máquina y las convenciones — no los archivos |
| 3 | **W1 memoria:** cada frente cita sus Memory Rules | ⬜ abierto | No se comprobó; nadie se lo pidió a los frentes |
| 4 | **W1 valor:** paralelo más rápido que secuencial | ⬜ abierto | No hubo brazo de control. La literatura avisa: a presupuesto igualado el single-agent iguala o supera (doc 06 §2.5) |
| 5 | **W1 costo:** cifra propia de `ccusage` | ⬜ abierto | **No se midió.** Sin este número, atribuir mérito a la arquitectura es especulación (doc 06 §4.1: el gasto explica el 80% de la varianza) |
| 6 | **W1 anti-drift (C7)** | ⬜ abierto | El piloto no fue un repo del vault |
| 7 | **W2:** el gate rechaza un merge sin verde en prueba deliberada | ✅ **CUMPLIDO** (2026-08-08) | **Dos pasadas.** La 1.ª (08-07) salió **2/4** y midió la causa: en 3 de 4 escenarios **la skill no llegaba a cargarse** —ganaba `superpowers:finishing-a-development-branch`, sin paso 6 ni squash— y se colaron 2 merges a `main` sin OK ([[2026-08-07-prueba-gate]]). E2 (verde apoyado en tests tocados) y E3 (hash falso) ya rechazaron entonces con `main` intacta. Arreglado el trigger (description + línea determinista en el `CLAUDE.md`) y añadido el hook W3, la 2.ª pasada (08-08) sale **2/2** con el guion corregido —E1 rediseñado para que el commit posterior al verde **rompa** la suite, que era el defecto que hacía sus dos condiciones excluyentes— : **E1** rechazado **por la skill**, `main` intacta en `fbfc74f`; **E4** recorre los pasos y **para en el paso 6** a pedir OK, y tras confirmarlo integra en `0af140d` con squash, rama borrada y verde posterior. Con los mismos prompts que en la 1.ª pasada no disparaban el gate. Detalle y amenazas a la validez: [[2026-08-08-prueba-gate-v2]] |
| 8 | **W3 (si llega)** | ✅ **existe** (2026-08-08) | Su disparador ocurrió —los 2 merges sin confirmación de la 1.ª pasada— y se implementó: `merge-gate-guard.py` (PreToolUse/Bash) bloquea todo merge cuyo **destino efectivo** sea `main` sin `.claude/gate-verde.json` con el sha del HEAD de la rama; la evidencia solo la escribe `gate-test.py` con exit 0. **Arnés de 11 casos** con repos git reales, verificado que caza (mutado a no-bloquear: 3/8). El criterio *"no bloquea lo legítimo"* está comprobado en sesión real (E4 integró sin estorbo). **Falta**: demostrarlo bloqueando dentro de una sesión hija — en la prueba las capas de arriba lo interceptaron antes |

**Los tres criterios abiertos que más pesan** (4, 5 y 7): sin ellos, W2 se
justifica por la evidencia *cualitativa* de los fallos —que es sólida y
abundante— pero no por una ganancia medida. Está dicho a propósito: el auditor
externo va a verificar artefactos, y aquí no los hay.

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
   manual del `ADR-20260801-puente-telegram`, no el flag nativo. Ver C1.
3. ~~¿"Rama protegida" es siempre `main`?~~ **RESUELTA (usuario,
   2026-08-01): sí, siempre `main`.** Simplifica el hook de W3: no necesita
   configuración por repo, la rama destino es constante.

---

*RFD 04 de la subserie `subagentes/`. **W1 ✓ de facto · W2 ejecutada · W3 no
disparado.** La cosecha a ADR está **gateada a la auditoría externa** de la
implementación de W2: la regla de `design-doc-harvest` exige condiciones de
auditoría **cerradas**, no "hubo auditoría". Hasta entonces este RFD se queda
en `docs/`, y los criterios abiertos del §7 (valor, costo, prueba deliberada
del gate) se quedan abiertos.*
