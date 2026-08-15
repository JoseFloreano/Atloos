# Agradecimientos

Atloos no se inventó casi nada. Es un montaje de piezas ajenas con unas cuantas
reglas propias encima, y casi todas las reglas propias salieron de romperse la
cara contra algo que otro construyó primero.

Esta lista es **lo que cambió el setup**, no todo lo que se miró. Un
agradecimiento que nombra treinta repos que solo hojeamos no agradece nada.

---

## Lo que sostiene el día a día

**[Superpowers](https://github.com/obra/superpowers) — Jesse Vincent ([@obra](https://github.com/obra))** · MIT

La pieza más grande y la que más se usa. `brainstorming`,
`subagent-driven-development`, `writing-plans`, `test-driven-development`,
`systematic-debugging`, `dispatching-parallel-agents`, `executing-plans`,
`condition-based-waiting` — todas aparecen en los reportes de campo, disparadas
de verdad, en sesiones de nueve horas.

Y no es solo el código: **es la metodología**. `workstream-dispatch` se declara
a sí misma *«capa DELGADA sobre `subagent-driven-development`»*, y lo dice con
razón. Cuando las dos discreparon en un número, el hallazgo fue nuestro; el
esqueleto sobre el que discreparon era suyo. La regla de este repo de **mutar en
vez de opinar** —comprobar que un check muerde antes de creerle— viene de ahí.

También [superpowers-skills](https://github.com/obra/superpowers-skills), donde
vive la versión editable por la comunidad.

**[Claude Code](https://code.claude.com) y [Cowork](https://claude.com) — Anthropic**

La plataforma entera: skills, hooks, subagentes, `/goal`, `/loop`, worktrees,
Agent Teams. Los hooks de `PreToolUse` y `Stop` son el mecanismo sobre el que se
apoya la tesis central del repo —**la convención escrita no muerde; el arnés
sí**—, y sin ellos este setup sería un montón de documentos pidiendo por favor.

La **[especificación de Agent Skills](https://agentskills.io)** merece mención
aparte: su límite de 1024 caracteres en `description` nos bloqueó una subida, y
perseguir ese fallo produjo el check que hoy lo caza y una lección que ya vamos
por la tercera vez aprendiendo — *medimos lo que se nos ocurrió medir*.

**[Obsidian](https://obsidian.md)** y **[obsidian-git](https://github.com/Vinzent03/obsidian-git) — [@Vinzent03](https://github.com/Vinzent03)**

El vault es la memoria durable del setup, y `obsidian-git` es lo que la
sincroniza entre laptops sin que nadie se acuerde de hacerlo.

---

## Lo que nos enseñó algo, aunque doliera

**[Graphify](https://github.com/Graphify-Labs/graphify) — Graphify-Labs**

Grafo consultable del código, con parseo determinista y sin base vectorial. Nos
dio dos cosas y las dos valen:

1. **La herramienta**, que responde en menos de dos segundos lo que un `grep`
   tarda diez búsquedas en aproximar.
2. **Tres jornadas de campo con `graphify: no-usado`**, que fue el fallo más
   instructivo del proyecto. Perseguirlo produjo la frase que hoy es la regla 1
   de `skill-forge` — *«la instrucción no dice cuándo, solo dice qué»* — y el
   corolario que la acompaña: **un disparador que exige que el agente se
   autodiagnostique el tipo de pregunta no se dispara nunca**.

Y a la cuarta jornada se usó. Gracias por aguantar la investigación.

**[web-interface-guidelines](https://github.com/vercel-labs/web-interface-guidelines)
y [agent-skills](https://github.com/vercel-labs/agent-skills) — Vercel Labs** · MIT

De aquí salió `web-design-guidelines`, **la única skill externa adoptada** de las
tres que se evaluaron, y el estreno de nuestro protocolo de importación de seis
pasos. Su procedencia —repo, commit, fecha, licencia, adaptación— está escrita
dentro de la propia skill, que es como creemos que debe hacerse.

Y nos dejó de regalo un hallazgo incómodo sobre nosotros mismos: el original son
~176 palabras cuya sustancia entera vive tras una URL. **Aceptamos a propósito la
enfermedad que este repo persigue con tres arneses**, y lo dejamos declarado en
voz alta en vez de fingir que no pasaba.

**[anthropics/skills](https://github.com/anthropics/skills) — Anthropic**

`frontend-design` y `mcp-builder` se evaluaron y **no se adoptaron**, las dos por
buenas razones: una ya existe como plugin oficial, la otra solapa con
`mcp-server`. Una no-adopción razonada es una decisión de arquitectura, y esa
decisión no habría existido sin poder leer el código.

**[Graphiti](https://github.com/getzep/graphiti) — Zep**

Memoria de grafo temporal para agentes. Se investigó a fondo y **está pospuesto
como decisión cerrada**, no como pendiente. La investigación no se tira: definió
lo que el vault tiene que hacer y lo que no, y por qué la memoria durable de este
setup es de ficheros y no de base de datos.

**[ponytail](https://github.com/DietrichGebert/ponytail) — [@DietrichGebert](https://github.com/DietrichGebert)** · MIT

Evaluado el 2026-08-14. **No adoptado como plugin**, y aun así nos dio la
formulación más limpia de algo que ya teníamos disperso: **una escalera de
decisión que empieza en «¿esto necesita existir?»**. Es la misma forma que el
*«tu mejor respuesta es no es ML»* de `ml-problem-framing`, el *«el patrón más
simple que funcione»* de `agentic-system-design` y la fase 0 de
`requirements-designer`. Verlo nombrado para el código, que es donde nos
faltaba, valió la lectura.

---

## Los catálogos que nos ahorraron descubrir lo obvio

Antes de escribir una skill propia, la pregunta es siempre si ya existe. Estos
repos fueron el mapa para contestarla — y varias veces la respuesta fue **«sí,
ya existe y es mejor que lo que ibas a escribir»**, que es exactamente para lo
que sirve un catálogo:

[wshobson/agents](https://github.com/wshobson/agents) ·
[affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) ·
[travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) ·
[trailofbits/skills](https://github.com/trailofbits/skills) ·
[terramate-io/agent-skills](https://github.com/terramate-io/agent-skills) ·
[alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) ·
[lgbarn/devops-skills](https://github.com/lgbarn/devops-skills) ·
[TensorBlock/awesome-mcp-servers](https://github.com/TensorBlock/awesome-mcp-servers)

---

## El trabajo publicado del que salen las reglas

Varias skills de este repo no son opinión nuestra: son literatura resumida. Sin
estas fuentes, `ml-tabular-workflow` y `ml-problem-framing` serían intuiciones
con formato bonito.

**Fuga de datos y evaluación**
- **Kaufman, Rosset & Perlich** — *Leakage in Data Mining* (KDD 2011). El test
  del *«no time machine»*, que caza la mayoría de los casos y es gratis.
- **Kapoor & Narayanan** — *Leakage and the reproducibility crisis in
  machine-learning-based science* (Patterns, 2023). Fuga documentada en **294
  papers de 17 disciplinas**, con la taxonomía L1/L2/L3 y las *model info sheets*.
- **Davis & Goadrich** (ICML 2006) y **Saito & Rehmsmeier** (PLOS ONE 2015). Por
  ellos este repo prohíbe decir *«ROC-AUC miente»* sin explicar el mecanismo.
- **Marcos López de Prado** — *Advances in Financial Machine Learning*, cap. 7.
  *Purging* y *embargo*, que aplican mucho más allá de las finanzas.

**Cuándo NO hacer machine learning**
- **Martin Zinkevich** — *Rules of Machine Learning* (Google). Las reglas #1, #3
  y #4, que juntas dicen que ML se justifica cuando la heurística se volvió
  inmantenible, no cuando sería interesante.
- **Sculley et al.** — *Hidden Technical Debt in Machine Learning Systems*
  (NeurIPS 2015). CACE, dependencias ocultas, código glue.
- **Grinsztajn, Oyallon & Varoquaux** (NeurIPS 2022) y **Dacrema et al.**
  (RecSys 2019), este último por recordarnos que **6 de 7 métodos neuronales
  fueron superados por heurísticas simples**.
- **Mitchell et al.** — *Model Cards* (FAT\* 2019) y **Gebru et al.** —
  *Datasheets for Datasets* (CACM 2021).
- **[scikit-learn](https://scikit-learn.org)**, cuya documentación es la mitad de
  lo que sabemos de umbrales y validación cruzada.

**Requisitos y calidad**
- **Alistair Mavin** y el equipo de Rolls-Royce — **EARS**, las seis plantillas.
- **Suzanne y James Robertson** — **Volere** y el *fit criterion*.
- **Tom Gilb** — **Planguage**, y la idea de que un requisito sin número no es un
  requisito.
- **ISO/IEC 25010:2023** e **ISO/IEC/IEEE 29148:2018**.
- **MADR** — el vocabulario de estados de los ADR.
- **OWASP** — el Top 10, que gobierna `web-security-review`.

---

## Y a quien prueba el setup y escribe lo que falló

La carpeta `feedback/` existe porque **el reporte de un agente sobre su propio
trabajo no es evidencia**. Cada reporte de campo que ha entrado ahí destapó algo
que ninguna auditoría interna había visto: el gate que corría cuatro veces sin
correr, el hook que sellaba un grafo viejo como fresco, la skill que existía y
no cargaba porque su disparador no nombraba un momento.

**Escribir lo que salió mal, con el comando al lado, es la contribución más
valiosa que recibe este repo.** Gracias.

---

<sub>Si algo tuyo está aquí mal atribuido, mal licenciado o no debería estar,
abre un issue y se corrige. Si algo tuyo debería estar y falta, también.</sub>
