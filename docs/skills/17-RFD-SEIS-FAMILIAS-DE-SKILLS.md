# RFD — Seis familias de skills: investigar, adaptar, importar, crear

> **Estado:** BORRADOR EN CURSO — **§1 y §2 escritas**, el resto pendiente.
> Se redacta sección por sección, con revisión del usuario entre cada una.
> **Fecha:** 2026-08-08 · **Autor:** Opus (laptop, con el inventario delante)
> **Origen:** propuesta del usuario — 6 familias: (1) ML/DL/datasets,
> (2) presentaciones de negocio en HTML, (3) diseñador de proyectos (RF/RNF/RN),
> (4) revisión de la familia de bases de datos, (5) mantenimiento,
> (6) memoria/RAG/embeddings.
> **Contexto:** `bd-y-nube/05-CATALOGO-Y-PLAN-DE-IMPLEMENTACION.md` (el catálogo
> anterior, y la lección) · `bd-y-nube/06-AUDITORIA-ADVERSARIAL-SKILLS.md` ·
> `skill-forge` (la skill que fabrica skills) ·
> `ADR-20260803-skills-fuente-unica`.

---

## 1. Problema

Hay seis huecos reales en el catálogo, y la evidencia de que son huecos está en
el §2. Pero **ese no es el problema difícil de este RFD**.

El problema difícil es que **ya escribimos un catálogo de skills y se pudrió**.
`bd-y-nube/05` (subserie cerrada el 2026-08-02) propuso **17 piezas** en cuatro
fases —S0 núcleo, S1 importaciones, S2 garantías, S3 MCPs—. Hoy, seis días
después:

| Fase | Propuesto | Construido |
|---|---|---|
| S0 · núcleo `shared/` | 5 | **5** ✅ |
| S1 · importaciones (`dbt-workflow`, `terraform-safe-apply`, `warehouse-query-optimize`…) | 6 | **0** |
| S2 · garantías (4 hooks: `validate-migration-review`, `block-terraform-apply-without-plan`, `tf-fmt-validate`, `sql-lint`) | 4 | **0** |
| S3 · dependientes de MCP (`db-explorer`, `lineage-check`…) | 2+ | **0** |
| `cowork/` (`data-doc-writer`, `cloud-architecture-review`) | 2 | **0** |

**5 de 17.** Y lo que no se construyó no quedó como deuda visible: quedó como
**referencias colgantes dentro de skills vivas**, que es peor que no haberlas
escrito.

```
setup/skills/shared/sql-conventions/SKILL.md:11   → warehouse-query-optimize   (nunca existió)
setup/skills/shared/skill-forge/SKILL.md:9        → cowork-plugin              (nunca existió)
```

La primera al menos se cubre con *"si está instalada"*. **La segunda no**:
`skill-forge` manda usar `cowork-plugin` en indicativo, sin hedge, y esa skill
no existe en el repo, ni en `~/.claude/skills/`, ni en el marketplace instalado.
Un agente que la obedezca literalmente se queda sin salida — **es la misma clase
del fallo de `notify-telegram` del 08-07**: una instrucción que nombra algo
inalcanzable. El arnés `test-skill-paths.py` no la caza porque solo mira rutas
de ficheros, no nombres de skills.

De ahí las dos preguntas que este RFD tiene que contestar, en este orden:

**P1 — ¿Qué se construye?** Las seis familias, acotadas: cuáles son skill
propia, cuáles se importan y adaptan, cuáles ya están cubiertas por otra cosa y
**cuáles hay que rechazar**. Un catálogo que lo acepta todo no es un catálogo.

**P2 — ¿Qué impide que este catálogo se pudra como el anterior?** Porque la
diferencia entre S0 y S1 no fue de dificultad: fue que **S0 se hizo en la misma
sesión que se escribió y S1 quedó para "después"**. Este RFD no puede proponer
17 piezas más sin decir qué pasa con las que no se construyan.

> Sin P2, este documento es el catálogo de `bd-y-nube` otra vez, con seis temas
> nuevos y la misma vida útil.

## 2. Mapa del terreno — qué existe hoy, verificado

**33 skills en el repo** (`21 shared` + `10 claude-code` + `2 cowork`), de las
que **31 están instaladas** en esta laptop; las de `cowork/` viven en la nube.
Superpowers aporta **44 skills más**, todas de **proceso** (brainstorming, TDD,
systematic-debugging, writing-plans, frontend-design…) — y **no toca ninguna de
las seis familias**, así que aquí no hay riesgo de duplicar su territorio. La
regla de W2 sigue en pie: nuestras piezas van **encima**, no dentro.

Cobertura, familia por familia:

| # | Familia | Cobertura hoy | Lo más cercano que existe | Veredicto preliminar |
|---|---|---|---|---|
| **1** | ML · clasificación, RNN/DL, predicción, limpieza de datasets | **Nula** | `data-quality-gates` valida datos *en tránsito*, no *para entrenar*; `model-benchmark` compara **LLMs de proveedor**, no modelos entrenados por ti | Hueco real y **grande** — la familia más ancha de las seis |
| **2** | Presentaciones de negocio en HTML | **Nula** | Superpowers `frontend-design` (interfaces, no mazos); el canal de entrega ya existe: la herramienta `Artifact` publica HTML autocontenido | Hueco real, **el más acotado** y con entrega ya resuelta |
| **3** | Diseñador de proyectos (RF, RNF, RN) | **Nula aguas arriba** | `brainstorming` idea; `writing-plans` planifica la implementación; `api-design`/`schema-designer` diseñan **después** de saber los requisitos | Hueco real y **estructural**: falta justo el eslabón entre idear y diseñar |
| **4** | Bases de datos | **Parcial: 5 de 17** | Las 5 de S0, todas ≥546 palabras y **0–1 `references/`** | No es "crear más": es **auditar las 5 vivas** y decidir qué queda del catálogo muerto |
| **5** | Mantenimiento | **Dispersa, sin nombre** | `dependency-audit`, `migration-auditor`, `flaky-test-hunter`, `secrets-scan`, `vault-drift-audit`, `token-audit` — seis piezas que nadie llama "mantenimiento" ni coordina | **La familia menos definida**: hay que decidir qué significa antes de construir |
| **6** | Memoria / RAG / embeddings | **Confusión de dos cosas** | Tenemos un **sistema de memoria propio** (vault + Graphiti + `memory-keeper` + `context-engineering`) y **cero skills para construir RAG dentro de un producto** | Hueco real, pero **solo si se separa** "mi memoria" de "el RAG que le construyo a un cliente" |

Tres cosas que el mapa deja claras antes de diseñar nada:

- **La familia 4 no es como las otras cinco.** Las demás piden crear; esta pide
  **revisar y podar**. Meterlas en el mismo saco haría que el trabajo barato
  (auditar 5 skills que ya existen) quedara sepultado bajo el caro (inventar una
  familia de ML entera).
- **La familia 6 tiene una trampa de nombre.** "Manejo de memoria" describe dos
  problemas sin relación: cómo recuerda *este setup* (resuelto, con ADRs y RFDs
  propios) y cómo se le construye RAG a *un producto* (sin nada). Si el RFD no
  las separa en §3, la skill nacerá disparándose en el contexto equivocado.
- **La familia 5 todavía no es una familia.** Es un adjetivo. Seis skills
  existentes ya hacen mantenimiento sin llamarse así; hasta saber qué falta de
  verdad, "mantenimiento" es un nombre buscando contenido — y ese es
  exactamente el molde del que salen las skills que nunca se disparan.

## 3. Objetivos

Las respuestas del usuario (2026-08-08) destaparon un patrón que atraviesa la
mitad de las familias y que ninguna de ellas nombraba:

> **Lo que falta casi nunca es la ejecución. Es el eslabón de ARRIBA: la pieza
> que acota el problema antes de resolverlo.**

- Familia 1: *"que haya una que acote el problema a ML o DL"* — antes de
  entrenar, decidir **si esto es ML siquiera**.
- Familia 3: requisitos (RF/RNF/RN) es literalmente el eslabón entre idear
  (`brainstorming`) y diseñar (`api-design`, `schema-designer`).
- Familia 5: seis skills ya hacen mantenimiento; lo que no existe es **quién
  decide qué mantener y cuándo**.

Es coherente con lo que ya sabemos: `schema-designer` nació con la regla
*ERD antes de DDL* y `api-design` con *contrato primero*. Las skills de este
setup que funcionan son las que ponen una decisión antes de la ejecución.

**O1 · El eslabón de arriba primero.** Donde una familia tenga fase de acotar y
fase de ejecutar, **la de acotar se construye antes**. Es la más barata, la que
más errores evita y la que decide si la otra hace falta.

**O2 · Alcance escrito y caso real.** Ninguna familia entra al catálogo sin
decir dónde termina y sin un caso concreto de los proyectos vivos —
`recomendador-cobranza`, `AlphaDogs`, `RecetIA`— donde se habría disparado.

**O3 · "Mi setup" y "el producto del cliente" no son lo mismo.** La familia 6 se
acota a **RAG de producto**; la memoria del setup ya está resuelta y **no se
toca** (decisión del usuario).

**O4 · La familia 4 se poda, no se amplía.** El catálogo muerto de `bd-y-nube`
se cierra explícitamente: lo que no se va a construir se **borra del catálogo y
de las referencias**, no se deja "pendiente".

**O5 · Nada se propone sin destino.** Toda pieza sale con fase asignada, y
**ninguna skill viva puede nombrar una skill que no existe** sin marcarla como
opcional. Es P2 del §1 y se diseña en §6.

**O6 · Cero regresiones.** Cuerpos ≤500 palabras, `references/` para el detalle,
las skills de Superpowers no se tocan, y `sync-skills` sigue verde.

## 4. Acotación, familia por familia

### 4.1 · ML — dos piezas, y el DL se aplaza a propósito

Decisión del usuario: **tabular end-to-end, más una pieza que acote el problema
a ML o DL**. Eso son dos skills con contratos distintos, no una grande.

| | `ml-problem-framing` (el eslabón de arriba) | `ml-tabular-workflow` (la ejecución) |
|---|---|---|
| Contesta | ¿esto es ML? ¿clásico o DL? ¿qué se predice y con qué dato disponible **en el momento de predecir**? ¿cuál es la métrica **de negocio**? ¿cómo se ve el fracaso? | limpieza → split → features → modelo → evaluación honesta → entrega |
| Su mejor respuesta | **"no es ML: es una regla, un SQL o un umbral"** — y ahorra el proyecto entero | un baseline superado con números, o la constancia de que no se superó |
| Se dispara | "quiero predecir X", "un modelo para Y", "clasificar Z" | después de la anterior, o cuando ya hay dataset y objetivo claros |

Lo que `ml-tabular-workflow` debe blindar, porque es donde de verdad se pierde
el tiempo y ninguna de nuestras skills lo cubre:

- **Fuga de datos** — la clase de bug más cara del ML y la más silenciosa:
  produce métricas excelentes y un modelo inútil. Incluye el caso que más muerde
  en datos de negocio: **split temporal, no aleatorio**, cuando la predicción es
  sobre el futuro.
- **Baseline obligatorio antes del modelo.** Sin él, "85% de accuracy" no
  significa nada — puede ser peor que responder siempre la clase mayoritaria.
- **La métrica del negocio, no `accuracy`.** Con desbalance (cobranza, fraude,
  churn) `accuracy` miente por construcción.
- **Qué se entrega**: no un notebook, sino modelo + preprocesamiento
  reproducible + la evaluación con su método escrito.

**El DL/RNN se aplaza explícitamente**, y esto es una decisión, no un olvido:
es la pieza más cara de las seis familias y la que menos veces se dispararía.
`ml-problem-framing` **decide cuándo hace falta**; el día que su respuesta sea
"aquí sí hace falta DL" en un caso real, ese caso es el disparador para
construirla. Hasta entonces, proponerla sería fabricar la S1 de este RFD.

### 4.2 · Presentaciones de negocio — una skill, dos formatos

Decisión del usuario: **una sola skill que decide el formato**. El criterio de
decisión es limpio y no necesita preguntar dos veces:

> **¿Habrá alguien exponiendo?** Sí → mazo navegable. No → informe de una
> página que se defiende solo.

Lo que comparten —y es el 80% del valor— es la **narrativa**:
problema → evidencia → propuesta → números → **el pedido**. La entrega ya está
resuelta: la herramienta `Artifact` publica HTML autocontenido, y sus
restricciones (CSP estricta, sin CDN, sin fuentes remotas, tema claro/oscuro)
son requisitos que la skill debe conocer de antemano en lugar de descubrirlos
fallando.

⚠ **El riesgo propio de esta familia es el relleno.** Una skill de
presentaciones tiende a producir diapositivas bonitas sin contenido. Dos
antídotos que van en el cuerpo, no en un reference:

- **Sin el pedido explícito no hay presentación.** Si no se sabe qué se le pide
  a quien escucha (aprobar, financiar, decidir entre A y B), la skill lo
  pregunta antes de generar nada.
- **Cada afirmación de negocio lleva su número o se cae.** Y el número lleva de
  dónde salió.

### 4.3 · Diseñador de proyectos — el eslabón que falta aguas arriba

Hoy hay un salto: `brainstorming` idea, `writing-plans` planifica la
**implementación**, y `api-design`/`schema-designer` diseñan **suponiendo que
los requisitos ya se conocen**. Nadie los produce. Es el hueco más estructural
de las seis familias.

Entrega un documento de requisitos con las tres capas separadas, porque
mezclarlas es el fallo clásico:

| | Qué es | La prueba de que está bien escrito |
|---|---|---|
| **RF** · funcionales | qué hace el sistema | numerado y verificable: se puede escribir un test |
| **RNF** · no funcionales | con qué calidad | **tiene número y unidad** — "p95 < 300 ms con 500 usuarios", nunca "rápido" |
| **RN** · reglas de negocio | qué es cierto en el dominio, independientemente del software | sobrevive a un cambio de tecnología |

Dos cosas que lo separan de una plantilla genérica de requisitos:

- **Traspaso explícito.** Termina nombrando qué RF/RN van a `schema-designer`
  (entidades y su grano) y cuáles a `api-design` (superficie y contrato). Sin
  eso el documento se archiva y nadie lo usa — que es el destino habitual de los
  documentos de requisitos.
- **Alcance negativo.** Una sección de **qué NO hace** el proyecto, con la misma
  numeración. Es lo que impide la discusión de la semana 6.

### 4.4 · Bases de datos — la familia está saturada, y eso manda

Medición del cuerpo de las cinco (sin frontmatter), contra el tope de 500:

| Skill | Palabras | `references/` |
|---|---:|:---:|
| `pipeline-designer` | **499** | 1 |
| `data-quality-gates` | **497** | **0** |
| `migration-auditor` | 488 | 1 |
| `schema-designer` | 475 | **0** |
| `sql-conventions` | 468 | **0** |

**Ninguna incumple, y ninguna admite una frase más.** Media 485; la más holgada
tiene 32 palabras de margen. Y **tres de cinco no tienen `references/`**, así
que ni siquiera hay dónde mover el detalle: hay que crear la carpeta primero.

Eso reordena la familia 4 por completo. **Mejorar estas skills no es editar
texto: es refactorizarlas.** Cualquier "le añadimos X" empieza por extraer
material a `references/`. Es trabajo real y hay que presupuestarlo, no
descubrirlo a medio camino.

⚠ Es exactamente el hallazgo **M2** que el auditor encontró en
`vault-drift-audit` (500/500 exactas) hace dos días. Dos hallazgos iguales en
sitios distintos dejan de ser casualidad: **el tope de 500 se está tocando en
todo el catálogo maduro** y no hay ninguna señal que avise antes de chocar. Eso
merece su propia respuesta en §6, no un parche aquí.

**La poda.** De las 12 piezas del catálogo de `bd-y-nube` que nunca se
construyeron, el criterio para cerrarlas es la **dependencia**:

- **Se borran del catálogo** las que exigen una herramienta o un MCP que no está
  en uso: `dbt-workflow`, `terraform-safe-apply`, `spark-optimizer`,
  `warehouse-query-optimize`, `warehouse-cost-review`, `lineage-check`,
  `db-explorer`, `cloud-cost-tagger` y los 4 hooks de S2. Ninguna se dispararía
  hoy; mantenerlas listadas es lo que produjo las referencias colgantes.
- **Sobreviven como candidatas** las de metodología pura, que funcionan con lo
  que ya hay: `pii-guard` (datos personales en cobranza y recetas: aplica hoy) y
  `data-doc-writer` (diccionario de datos y ERD como entregable — y se apoya en
  la familia 2).

**Y se cierran las dos referencias colgantes** de §1: `sql-conventions:11` y
`skill-forge:9`. La primera se borra; la segunda es la urgente, porque manda en
indicativo hacia una skill inexistente.

### 4.5 · Mantenimiento — es un plugin, y las guardias piden cautela

Decisión del usuario: los **tres frentes** (código heredado, el propio setup,
sistemas en producción) y *"casi casi un plugin"*. El inventario lo confirma:
`dependency-audit`, `migration-auditor`, `flaky-test-hunter`, `secrets-scan`,
`token-audit` y `vault-drift-audit` ya hacen mantenimiento **sin coordinarse**.
No falta capacidad; falta **quién decide qué mantener, cuándo, y con qué
resultado** — el eslabón de arriba del O1.

Los tres frentes, con lo que ya existe debajo:

| Frente | Qué aporta de nuevo | Sobre qué se monta |
|---|---|---|
| **Código heredado** | entrar a un repo que no escribiste: mapa, red de tests **antes** de tocar, refactor por pasos reversibles, retirada de código muerto | `dependency-audit`, `flaky-test-hunter`, `git-bisect-assist`, Superpowers `systematic-debugging` |
| **El propio setup** | una rutina periódica que corra los arneses y reporte **junto**, en vez de seis invocaciones que nadie recuerda | los 6 de arriba + `test-sync-guard` + `test-skill-paths` |
| **Producción** | runbooks, incidentes, postmortem | `deploy-planner` llega hasta el despliegue y **para ahí** |

#### Las guardias: qué encontré, y por qué el diseño cambia

**El hueco técnico es real y concreto.** Los cuatro hooks de Claude Code son
**todos de sesión** (PreToolUse, PostToolUse, Stop, PreCompact): ninguno puede
dispararse cuando *no hay sesión*, que es exactamente el caso de una guardia. Lo
único 24/7 que este setup ya tiene es el **daemon de Telegram** y el plan del
**mini-PC** (`telegram/01`). Ahí es donde una guardia viviría, y el canal de
salida ya está instalado: `~/.claude/scripts/notify_telegram.py`.

**El motor existe y es maduro.** El modo headless (`claude -p`) con
`--allowedTools`, `--max-turns` y `--output-format json` está pensado para
justo esto: disparo por evento, herramientas restringidas, salida estructurada
que un script parsea antes de actuar.

**La industria ya convergió, y en una sola frase:**

> **Investigar autónomo. Remediar supervisado.**

Es el patrón idéntico en todos los proveedores; el Azure SRE Agent llegó a GA en
marzo de 2026 con 35.000 incidentes mitigados. Y es —literalmente— la regla que
este proyecto ya escribió por su cuenta en `vault-drift-audit`: *reporta y
propone, no apliques*. Que dos caminos independientes lleguen a la misma norma
es la mejor señal de que la norma es correcta.

**Pero los números de los vendors y los de la academia no se parecen.** Y esto
es lo que de verdad decide el alcance:

| Fuente | Qué mide | Resultado |
|---|---|---|
| Vendors (2026) | MTTR, incidentes Tier-1 | −70% MTTR, "90% de acierto" |
| **CUJBench** | diagnóstico de fallo extremo a extremo, 6 modelos frontera | **19,7% de acierto**, techo **52%** |
| **OpenRCA** | RCA *perfecta*, 5 modelos frontera | **3,9% – 12,5%** |

La diferencia no es que unos mientan: miden cosas distintas —"mitigado" no es
"causa raíz correcta"—. Pero **una guardia que se diseñe con el número del
vendor y rinda como el de la academia es una que despierta a su dueño de
madrugada para nada.**

**Tres hallazgos que son instrucciones de diseño directas:**

1. **Más herramientas empeoraron el resultado.** En CUJBench los agentes *solo
   con navegador* superaron a los de toolset completo: el acceso ampliado a
   evidencia produjo **exploración difusa, no mejor síntesis**. El fallo
   dominante no fue no encontrar la evidencia decisiva —la encontraban— sino
   **atribuirla mal**. → La guardia arranca con el **mínimo** de herramientas y
   solo se le añaden con un caso que lo justifique. Es lo contrario del instinto.
2. **El fallo que no produce error.** *"Un cron que deja de correr es la
   ausencia de algo bueno: no hay error que capturar, no hay alerta que
   dispare"*. Es palabra por palabra nuestra primera ley —**el exit code no es
   el estado**— y la razón de que el guard del sync compare **conjuntos y no
   conteos**. → Una guardia necesita **latido** (dead man's switch), no solo
   alertas. Sin eso vigila lo ruidoso e ignora lo mudo, que es lo caro.
3. **La fatiga de alertas mata la guardia antes que cualquier bug.** El
   promedio es ~50 alertas por semana de las que **2–5% requieren intervención**.
   Nuestro propio arnés ya lleva escrita la consecuencia: *"un arnés que grita
   en falso se ignora a las dos semanas"*. → El criterio de aceptación de una
   guardia **no es cuántos problemas detecta, sino cuántas veces avisó en balde**.

**Y los guardrails coinciden con la filosofía de nuestros hooks.** El control de
mayor palanca es el **mínimo privilegio**, porque acota el radio de todo lo
demás; las acciones se clasifican (solo-lectura · modificación de bajo riesgo ·
alto riesgo · destructiva); y el enforcement va en la **capa de ejecución, de
forma determinista**, sin confiar en la configuración del agente. Es la misma
tesis del `hooks/README.md`: *la compliance probabilística se degrada; el hook
la convierte en garantía*.

#### Veredicto sobre las guardias

**Construible hoy — guardia de latido y triage, solo-lectura.** Vigila que lo
que debe correr corra (el daemon, los backups, el sync), y cuando algo falla
**investiga y reporta por Telegram con su evidencia**. No toca nada. Se monta
sobre piezas que ya existen: mini-PC, daemon, `notify_telegram.py`, headless.

**No construible todavía — remediación autónoma.** Los números no la sostienen,
y el camino honesto es el que la propia industria usa: elegir **un** runbook de
alta frecuencia y bajo riesgo, y automatizarlo **solo después** de haberlo visto
resolverse a mano varias veces. Sin ese historial, es adivinar.

⚠ **La pregunta que decide si esta pieza se construye o no:** *¿qué vigila?*
Hoy no hay nada en producción con guardia. Si la respuesta es "el daemon de
Telegram y los backups del vault", es una guardia pequeña y perfectamente útil.
Si es "los servidores de un cliente", es otro proyecto. **Mientras no haya
respuesta, esto es una solución buscando su problema** — y ese es el molde del
que salieron las 12 skills muertas del §4.4.

### 4.6 · RAG de producto — evaluar antes que elegir

Acotada por el usuario a **construirle recuperación a un producto**; la memoria
de este setup ya está resuelta y **no se toca**.

**La frontera hay que escribirla en las dos descriptions**, o competirán por el
trigger: `context-engineering` diseña el contexto de **mi** agente (qué entra a
la ventana, compaction, subagents); esta construye recuperación **dentro del
producto que entrego**. Se parecen lo bastante como para pisarse.

El eslabón de arriba aparece aquí también, y es el que más dinero ahorra:
**¿hace falta RAG?** Con pocos documentos, meterlos enteros en el contexto gana;
si la pregunta es estructurada, un SQL gana; si es exacta, un `grep` gana. RAG
es la respuesta cuando el corpus no cabe y la pregunta es semántica.

Y la inversión del orden habitual, que es donde esta skill se gana el sitio:

> **Se empieza por la evaluación, no por la base vectorial.** El error típico es
> elegir vector store primero y descubrir seis semanas después que no hay forma
> de saber si recupera bien.

Eso significa, en este orden: un set de preguntas de oro con su respuesta →
métrica de recuperación (`recall@k`) → **entonces** chunking, embeddings,
híbrido léxico+denso y reranking, cada uno medido contra el set. Es el mismo
patrón que `ml-tabular-workflow` con su baseline, y por el mismo motivo: sin
número de partida, cualquier cambio parece una mejora.

---

**Fuentes de §4.5** — [CUJBench (arXiv)](https://arxiv.org/html/2604.23455v2) ·
[Benchmark multi-dataset de diagnóstico en microservicios (arXiv)](https://arxiv.org/html/2606.29193v1) ·
[Stalled, Biased, and Confused: fallos de razonamiento en RCA (ACM)](https://dl.acm.org/doi/10.1145/3793655.3793732) ·
[Exploring LLM-based Agents for RCA (arXiv)](https://arxiv.org/html/2403.04123v1) ·
[Defense in depth for autonomous AI agents (Microsoft)](https://www.microsoft.com/en-us/security/blog/2026/05/14/defense-in-depth-autonomous-ai-agents/) ·
[AI agent guardrails: defense in depth](https://blog.traversaal.ai/ai-agent-guardrails-defense-in-depth-architecture-guide/) ·
[Top AI SRE tools 2026](https://neubird.ai/blog/top-ai-sre-tools) ·
[AI SRE en gestión de incidentes (Augment Code)](https://www.augmentcode.com/guides/ai-sre-incident-management) ·
[Alert fatigue y on-call con IA (OneUptime)](https://oneuptime.com/blog/post/2026-03-05-alert-fatigue-ai-on-call/view) ·
[Reducción de fatiga de alertas con agentes (IBM)](https://www.ibm.com/think/insights/alert-fatigue-reduction-with-ai-agents) ·
[Self-host Healthchecks: dead man's switch para cron](https://blog.elest.io/self-host-healthchecks-know-the-instant-a-cron-job-dies/) ·
[Claude Code en CI/CD y automatización headless](https://hidekazu-konishi.com/entry/claude_code_cicd_and_headless_automation.html) ·
[Claude Code headless mode (guía)](https://amux.io/guides/claude-code-headless/)

---

> **Secciones pendientes:** §5 importar-vs-crear · §6 la respuesta a P2
> (anti-podredumbre) — que ahora debe cubrir también **la saturación del tope
> de 500** detectada en §4.4 · §7 orden y fases · §8 criterios de aceptación ·
> §9 lo que NO se hace.
