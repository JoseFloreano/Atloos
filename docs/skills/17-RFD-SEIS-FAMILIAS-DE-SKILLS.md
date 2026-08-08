# RFD — Seis familias de skills: investigar, adaptar, importar, crear

> **Estado:** **BORRADOR COMPLETO (2026-08-08)** — las 10 secciones escritas.
> Pendiente de **auditoría externa** y del **arbitraje de D1–D3 (§10)**.
> Aprobarlo NO es aprobar seis familias: es aprobar F0 y **una** de ellas.
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

⚠ **Y no es una enfermedad de la familia 4.** Al medir las 33 skills del repo
buscando el umbral de saturación (≥475 palabras), salieron **ocho — el 24% del
catálogo**:

| Skill | Palabras | `references/` |
|---|---:|:---:|
| `vault-drift-audit` | **500** | 1 |
| `pipeline-designer` | 499 | 1 |
| `data-quality-gates` | 497 | **0** |
| `design-doc-harvest` | 495 | 1 |
| `session-close` · `migration-auditor` | 488 | 2 · 1 |
| `workstream-merge-gate` | 484 | **0** |
| `schema-designer` | 475 | **0** |

Tres de ellas —`design-doc-harvest`, `session-close`, `workstream-merge-gate`—
no tienen nada que ver con bases de datos, y son de **las más usadas del
sistema**. El patrón real es otro: **la saturación correlaciona con la
madurez**. Una skill que se ha corregido cinco veces ha crecido cinco veces, y
el tope no avisa hasta que ya no cabes. Eso no es un parche de la familia 4:
es una señal que falta en todo el catálogo, y se diseña en §6.

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

## 5. Importar, crear, o robar el patrón

El protocolo de importación **ya existe** y es bueno: `bd-y-nube/05` §2, seis
pasos (clonar fuera, leer todo antes de instalar, copiar solo lo que se usa,
adaptar dialecto y rutas, registrar procedencia con commit y fecha, verificar el
trigger con una petición real). No hay que reescribirlo.

Lo que le falta es lo de arriba otra vez: **dice CÓMO importar, no CUÁNDO**. Y
la evidencia de que ese hueco cuesta está medida: de las **6 importaciones**
planificadas en S1, se hicieron **0**. El protocolo es correcto y también es
caro —leer una colección entera antes de instalar nada son horas— y sin un
criterio que diga si vale la pena, "importar" se pospone indefinidamente.

Pero hay un tercer camino que este repo **ya usó con éxito** y nunca nombró como
método: `ecosistema/16-AHORRO-TOKENS-ROBADO-DE-HERMES-OPENCLAW.md`. Ahí no se
importó nada: se leyó lo ajeno, se extrajo el patrón y se escribió lo propio.
Frente a 0 importaciones, ese camino sí produjo resultados.

| Modo | Cuándo | Coste | Qué se registra |
|---|---|---|---|
| **Crear** | el valor es una **decisión tuya**: convenciones, criterio, el eslabón que acota el problema | medio | nada externo |
| **Robar el patrón** | el conocimiento es público y bueno, pero el envoltorio ajeno no encaja (dialecto, rutas, idioma del trigger) | **bajo** | la fuente en el cuerpo, como en `ecosistema/16` |
| **Importar** | la pieza vale por su **exhaustividad verificable** y reescribirla perdería cobertura (checklists largos, taxonomías) | **alto** — protocolo completo de 6 pasos | procedencia: repo, commit, fecha |

> Regla práctica: **si vas a reescribir más de la mitad, no estás importando —
> estás robando el patrón.** Y entonces el protocolo de 6 pasos no aplica: basta
> con leer la fuente y citarla.

Aplicado a las seis familias:

| Familia | Modo | Por qué |
|---|---|---|
| 1 · ML | `ml-problem-framing` **crear** · `ml-tabular-workflow` **robar** | el framing es juicio propio; fugas de datos, split temporal y baselines son conocimiento público y asentado |
| 2 · Presentaciones | **crear** | la narrativa de negocio es criterio; y las restricciones de `Artifact` (CSP, sin CDN, tema doble) son nuestras, no de nadie |
| 3 · Requisitos | **robar** el vocabulario, **crear** el traspaso | RF/RNF/RN es estándar de ingeniería; lo que no existe fuera es el handoff nominal a `schema-designer`/`api-design` |
| 4 · Bases de datos | **ni una cosa ni otra: podar** | y `pii-guard` decide su modo cuando le toque, no antes |
| 5 · Mantenimiento | **crear**, con **investigación** previa en las guardias | no hay nada que importar: lo que existe son productos SaaS, no skills |
| 6 · RAG | **robar** fuerte | es la familia con más conocimiento público bueno y menos opinión propia |

## 6. Anti-podredumbre — la respuesta a P2

El diagnóstico está en el §1 y es incómodo de lo simple que es:

> **Se construyó lo que cabía en la sesión que escribió el catálogo. Todo lo
> demás quedó "para después", y "después" nunca llegó.**

No fue falta de disciplina ni de tiempo: fue que **el catálogo era la unidad de
aprobación**, y aprobar 17 piezas de golpe hace que las 12 no construidas se
sientan igual de vivas que las 5 construidas — hasta que alguien las cita.

### R1 · La familia es la unidad de entrega, no el catálogo

**Este RFD no se aprueba entero.** Se aprueba **una familia**, se construye
completa —skills, `references/`, prueba de trigger real— y solo entonces se abre
la siguiente. Las otras cinco quedan como **propuesta fechada**, no como
compromiso.

Es el mismo principio del RFD 12 con el backlog: un pendiente que nadie va a
tocar este mes no se lista como activo, se manda al backlog y se dice que está
ahí. Cambiar de sitio no es perderlo; **fingir que está vivo, sí**.

### R2 · Ninguna skill viva puede nombrar una que no existe

Es el fallo concreto que se encontró en §1 y es de la misma clase que
`notify-telegram`: **una instrucción que apunta a algo inalcanzable**. El arnés
`test-skill-paths.py` no lo caza porque solo mira rutas de fichero.

**Arnés nuevo — `test-skill-catalog.py`**, hermano del de rutas:

1. **Referencia colgante.** Toda skill nombrada dentro de un `SKILL.md` debe
   existir en `setup/skills/`. Si no existe, es hallazgo — **salvo que la
   mención venga marcada como opcional** (*"si está instalada"*), que es una
   excepción declarada y greppable, igual que el `[repo]` de ayer.
2. **Saturación del cuerpo.** Cuerpo (sin frontmatter) **≥ 475 palabras** →
   aviso de saturación, con el detalle de si tiene `references/` o no.

El segundo check es la respuesta al §4.4, y nace con señal verdadera: hoy
dispararía en **8 skills — el 24% del catálogo** (§4.4), tres de ellas fuera de
la familia de bases de datos. No es un check decorativo esperando su primer caso.

⚠ **Y aquí aplica lo que acabamos de aprender en el RFD 11**: un aviso que nadie
atiende es F16 otra vez. Así que la saturación **no es solo un aviso**: entra en
`vault-drift-audit` con la misma disciplina de escalada que D1(b) —la primera
vez propone, a partir de la segunda lo dice con los días acumulados—. Un umbral
sin escalada ya sabemos en qué se convierte.

### R3 · El catálogo caduca, y se reusa el mecanismo que ya existe

No hace falta inventar nada: `vault-drift-audit` ya declara **en el limbo** un
ADR `proposed` con más de 14 días, y **zombi** un ítem de backlog con más de 30.
La misma regla vale aquí.

> Una familia propuesta y no construida en **60 días** se **borra del catálogo o
> se re-justifica por escrito**. No se queda "pendiente".

Sesenta y no treinta porque una familia es más cara que un pendiente. Lo que
importa no es el número: es que **la propuesta tenga fecha de caducidad**, que es
justo lo que le faltó a `bd-y-nube/05`.

### R4 · El eslabón de arriba se entrega solo

Es el O1 visto como defensa, y es la parte más barata de todo el RFD: la pieza
que acota el problema (`ml-problem-framing`, el documento de requisitos, el
triage de mantenimiento) **vale por sí sola aunque la de ejecución no se
construya nunca**.

Ese es el seguro real contra la podredumbre. Si de la familia 1 solo llega a
existir `ml-problem-framing`, el resultado no es media familia: es una skill útil
que además dirá, con casos reales, si la otra hacía falta.

---

## 7. Orden

Por R1 se aprueba **una familia**, no el catálogo. Pero hay algo que va antes de
la primera, y no es una familia.

### F0 · Higiene del catálogo — antes de añadir nada

Media jornada, y es el seguro de todo lo demás:

1. Cerrar las dos referencias colgantes (`skill-forge:9` primero: manda en
   indicativo hacia `cowork-plugin`, que no existe).
2. Construir `test-skill-catalog.py` (§6 R2) y dejarlo en verde.
3. Podar el catálogo de `bd-y-nube`: **borrar** las 12 piezas descartadas del
   §4.4, con una nota de por qué. No marcarlas "pendiente".

**Por qué primero y no después:** añadir seis familias a un catálogo que ya no
sabe distinguir lo construido de lo propuesto es multiplicar el problema del §1.
Con F0 hecho, cada familia nueva nace vigilada.

### Después: una familia, completa

**Recomendación — familia 3 (requisitos).** Es creación pura sin dependencias,
se enchufa a una cadena que ya funciona (`schema-designer`, `api-design` la
están esperando sin saberlo), y **aplica a cualquier proyecto futuro
independientemente del dominio**. Es la que más veces se disparará.

La familia 1 le disputa el sitio con un argumento legítimo: si hay una decisión
de ML inminente en un proyecto vivo, `ml-problem-framing` gana la cola, porque
su valor es evitar el proyecto equivocado y eso caduca. **Lo decide el usuario**
(§10 D1).

El resto queda como **propuesta fechada**, sujeta a la caducidad de R3.

## 8. Criterios de aceptación

Aplican a **cada familia**, no al RFD entero. Medibles, no opinables:

1. **Cero referencias colgantes.** `test-skill-catalog.py` da 0 en su check 1.
   Es bloqueante.
2. **Trigger probado con una petición real**, y la petición literal escrita en
   el commit — paso 6 del protocolo de `bd-y-nube/05` §2, que hasta hoy nunca
   se ejerció por no haber importado nada.
3. **Cuerpo ≤450 palabras** en toda skill nueva. **No 500**: el §4.4 demuestra
   que las skills maduran creciendo, y una que nace en 495 no tiene dónde
   corregirse. El margen es deliberado.
4. **Toda skill que se EDITE en la fase sale ≤450 y con `references/`** si tenía
   detalle que mover. Mismo criterio que el 5 del RFD 10: lo que se toca, se deja
   cumpliendo.
5. **Los tres arneses verdes**: `test-skill-catalog` 0, `test-skill-paths` 0,
   `test-sync-guard` 11/11. Y `sync-skills` corre sin huérfanas.
6. **El catálogo queda al día en el mismo commit**: lo construido se marca
   construido; lo descartado se **borra**, no se aparca.
7. **Cero cambios en Superpowers.** `git diff` sobre su carpeta, vacío.

## 9. Lo que NO se hace

- **DL / RNN** (§4.1). Aplazado con disparador escrito: el primer caso real en
  que `ml-problem-framing` responda "aquí sí hace falta DL".
- **Remediación autónoma en las guardias** (§4.5). Los números no la sostienen.
  Se gana con un runbook concreto tras verlo resolverse a mano varias veces.
- **La memoria del propio setup** (§4.6). Decisión del usuario: la familia 6 es
  RAG de producto y nada más. `memory-keeper` y `context-engineering` no se tocan.
- **Las 12 piezas podadas** de `bd-y-nube` y **los 4 hooks de S2**. No quedan
  "pendientes": se borran del catálogo.
- **Las skills de Superpowers.** Regla de W2, otra vez: nuestras piezas van
  encima, no dentro.
- **Aprobar las seis familias de golpe.** Es exactamente lo que hizo
  `bd-y-nube/05`, y es la causa del §1.

## 10. Decisiones abiertas

| | Decisión | Recomendación |
|---|---|---|
| **D1** | ¿Qué va primero tras F0: familia 3 (requisitos) o familia 1 (`ml-problem-framing`)? | **La 3**, salvo que haya una decisión de ML inminente — ese valor caduca y el de los requisitos no |
| **D2** | **¿Qué vigila la guardia?** Bloquea §4.5 entero: sin respuesta es una solución buscando problema | Acotarla a lo propio: daemon de Telegram, backups del vault y los `sync`. Pequeña, útil y verificable |
| **D3** | ¿El tope de las skills nuevas baja a **450** (criterio 3)? | **Sí.** 8 de 33 skills están a ≤25 palabras del techo por haber nacido cerca de él |

---

*RFD 17 de la subserie `skills/`. **Borrador completo, pendiente de auditoría
externa y del arbitraje de D1–D3.** Aprobarlo NO es aprobar seis familias: es
aprobar F0 y **una** de ellas (R1). Nada de esto está implementado.*
