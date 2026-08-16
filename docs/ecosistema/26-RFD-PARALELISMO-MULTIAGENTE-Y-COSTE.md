---
title: RFD 26 — Paralelismo, multiagente y coste: dónde está de verdad el cuello
tags: [rfd, paralelismo, multiagente, coste, worktree, hooks, xdist]
created: 2026-08-16
updated: 2026-08-16
status: parcialmente-arbitrado
type: rfd
project: atloos
decisiones: [D15, D16, D17, D18, D19]
arbitradas: [D15, D16, D19]
suspendidas: [D18]
abiertas: [D17]
---

# RFD 26 — El cuello no es el que parece, y la palanca no es la que se usa

Tres peticiones tuyas, una conclusión común:

> «el orquestador basta con un modelo como sonnet · se puede usar un hook para
> decidir qué subagente mandar · usar paralelismo con múltiples hilos para no
> sobrecargar todo a un núcleo · la parte de la RAM con los worktrees»

**Las cuatro son viables y tres están mal dimensionadas por una razón común: se
está optimizando el reparto de agentes cuando el desperdicio está en la
ejecución.** Y hay un hallazgo que probablemente explica solo el ×2,05 que
mediste.

---

## 0 · El hallazgo que va primero, porque puede ser gratis

**`pytest -n auto` ignora `taskset`.** Verificado en laboratorio:

```
$ pytest -n auto tests                → created: 2/2 workers
$ taskset -c 0 pytest -n auto tests   → created: 2/2 workers   ← NO bajó a 1
$ taskset -c 0 python -c "psutil.cpu_count(logical=False)" → 2
$ taskset -c 0 python -c "len(os.sched_getaffinity(0))"    → 1
```

La causa está en el código de `xdist/plugin.py`: consulta **psutil primero**, y
`psutil.cpu_count()` **no respeta la afinidad**. Solo cae a `sched_getaffinity`
si psutil no está instalado.

> **Si el `pytest.ini` del proyecto lleva `-n auto` en `addopts`, cinco frentes
> lanzaron 5 × 8 = 40 procesos de test en 8 núcleos.** Sobresuscripción de ×5.
> Eso no es «contención por paralelizar»: es una fuga de configuración.

**Primer comando a correr, y cuesta diez segundos:**

```bash
grep -rn "addopts\|numprocesses\|-n auto" pyproject.toml pytest.ini setup.cfg tox.ini
```

Si aparece, **el ×2,05 tiene una explicación más barata que cualquier rediseño**,
y la palanca correcta es la variable —que sí se respeta incluso con `-n auto`—:

```bash
export PYTEST_XDIST_AUTO_NUM_WORKERS=2
```

⚠ Es una hipótesis con fundamento, **no un diagnóstico**: no tengo el
`pytest.ini` de ese repo. Pero es lo primero que hay que mirar y **descarta o
confirma medio RFD**.

---

## 1 · El paralelismo de CPU: la palanca que no se está usando

Tu suite son **4756 tests, 6-7 min limpia**. Hoy corre **en un solo núcleo por
frente**. Con 8 núcleos físicos, eso deja siete parados mientras el gate bloquea
el árbol.

### 1.1 Los modos, con su definición literal

`-n` es un atajo de `--dist=load --tx=NUM*popen`. **Son procesos, no hilos** —
sin GIL compartido, pero tampoco memoria compartida.

| Valor | Qué hace | En tu 8845HS |
|---|---|---|
| `-n auto` | *«detect **physical** CPU count»* | 8 |
| `-n logical` | *«detect **logical** CPU count (requires psutil)»* | 16 |
| `-n <N>` | N explícito | — |

**Y el modo de reparto importa tanto como el número.** Con `load` (el que trae
`-n` por defecto) una fixture de módulo cara se construye **en cada worker que
reciba un test de ese módulo**. Con `--dist loadfile`, *«tests are grouped by
their containing file»* y el archivo entero va a **un solo** worker: la fixture
se construye **una vez**.

> **Recomendación: `--dist loadfile` en `addopts`, y `-n` NUNCA en `addopts`** —
> que lo elija quien invoca, porque el número correcto depende de cuántos frentes
> haya vivos.

### 1.2 El reparto: 3 frentes × `-n 2` gana a serializar

Con `T₁ = 400 s`, `p = 0,95` y arranque `c = 2 s/worker` —**valores de trabajo,
mide los tuyos**—:

| | **A: 3 frentes × `-n 2`, a la vez** | **B: serializado, `-n 6` por turnos** |
|---|---|---|
| Workers simultáneos | 6 | 6 |
| Núcleos libres para los agentes + SO | 2 | 2 |
| Wall del **último** frente | **214 s** | 286 s |
| Throughput de las 3 suites | **214 s** | 286 s |
| Complejidad | ninguna | hace falta un lock global |

**Gana A en las dos métricas.** Y `-n 8` serializado es peor todavía (250 s
totales) porque durante 84 s los ocho núcleos están al 100 % y **los agentes se
ahogan** — que es justo cuando tu prueba de latencia falla por carga.

**Presupuesto para 8 núcleos:** 3 frentes × 2 workers = 6, y **2 reservados**
para los agentes de Node y el sistema. `-n 8` solo cuando corres solo.

### 1.3 El fallo «por carga, no por código» tiene solución estándar

Y la respalda la herramienta de referencia. `pytest_benchmark/session.py`,
literal:

```python
if xdist_active and not self.skip and not self.disabled:
    self.logger.warning(
        'Benchmarks are automatically disabled because xdist plugin is active. '
        'Benchmarks cannot be performed reliably in a parallelized environment.')
    self.disabled = True
```

Y en su CHANGELOG: *«auto disables benchmarks if xdist is enabled **by
design**»*.

> **El autor del plugin de benchmarking decidió que medir rendimiento bajo
> paralelismo no tiene sentido.** Tu instinto de serializarlos está respaldado
> por la herramienta, no es una concesión.

**El patrón, en cuatro piezas:**

1. Marcador `perf` registrado en `pyproject.toml`.
2. Dos pasadas: `-n 2 -m "not perf"` en paralelo, y `-n 0 -m perf` serializada.
3. **`flock` global entre worktrees**, para que dos frentes no midan latencia a
   la vez.
4. **Red de seguridad en `conftest.py`**: si detecta xdist, **salta** los `perf`
   en vez de dejarlos fallar. Exactamente lo que hace pytest-benchmark.

Y para las aserciones: **`time.process_time()` en vez de `time.perf_counter()`**
mide CPU del proceso, no reloj de pared — **inmune a la contención del
scheduler**. Es la mitigación si algún día no puedes serializar.

### 1.4 Acotar de verdad: Linux puede, Windows no

| Mecanismo | Semántica | ¿Sirve? |
|---|---|---|
| **`CPUQuota=200%`** (systemd) | *«never get more than 20% CPU time on one CPU»* → `200%` = 2 núcleos | ✅ **el correcto** |
| `CPUWeight=` | peso relativo 1-10000, sin techo | ✅ mejor si la máquina suele estar libre |
| `AllowedCPUs=` | fija a núcleos concretos | para reproducir perf, no para limitar |
| `taskset` | afinidad | ❌ **y no reduce `-n auto`** (§0) |

```bash
systemd-run --user --scope -p CPUQuota=200% -p MemoryHigh=3G -p MemoryMax=4G \
  -- pytest -n 2 --dist loadfile -m "not perf" -q
```

**En Windows no hay equivalente.** `Start-Process -Affinity` **no existe**;
`cmd /c start /affinity` es afinidad, no cuota; el único techo real son los **Job
Objects**, que no tienen CLI y exigen P/Invoke.

> **Esto es un argumento nuevo y concreto para el mini PC**, distinto de los que
> ya teníamos: *el control de recursos por frente solo existe en Linux*. En la
> Legion la alternativa es WSL 2 con `.wslconfig` (`processors=`, `memory=`),
> que acota el conjunto pero no cada frente.

---

## 2 · Los worktrees: el coste no es el que crees

**No duplican el historial.** Documentación de git: *«sharing everything except
per-worktree files such as `HEAD`, `index`»*. Medido en laboratorio:

```
$ du -sh .git/worktrees/*      →  52K cada uno
$ du -sh .git/objects          →  768K antes y después de 3 worktrees (idéntico)
```

El `index` cuesta **~80 B por fichero versionado**. Para 10 000 ficheros, 800 KB
por worktree. **Ruido.**

> **Un worktree consume 0 bytes de RAM.** Es un directorio. La RAM la gastan los
> procesos que lanzas dentro. Todo el coste real es **la copia del checkout**.

### 2.1 Lo caro son tus 188,6 MB que git no versiona

3 worktrees × (179 MB de BD + 9,6 MB de CSV) = **565,8 MB duplicados**.
Compartidos por enlace: **188,6 MB**. Ahorro de **377 MB de disco** — y, lo que
importa más, **el kernel cachea el fichero una sola vez** en vez de tres.

| Técnica | Riesgo |
|---|---|
| **Symlink** (solo lectura) | ✅ recomendado si los datos no se escriben |
| **`cp --reflink=auto`** (Btrfs/XFS) | ✅✅ lo mejor si hay escritura: coste 0 al copiar, divergen al escribir |
| Hard link | ⚠️ **el más traicionero**: si el proceso hace *write-to-temp + rename*, el enlace se rompe **en silencio** y el frente diverge sin avisar |
| Symlink de `.venv` | ⚠️ un `pip install` en un frente **rompe a los otros**. `.venv` propio por frente |
| `git clone --shared` | ❌ *«possibly dangerous… the cloned repository will become corrupt»* |

**Y un detalle operativo que ahorra media hora**: en un worktree `.git` es un
**fichero**, así que `echo x >> .git/info/exclude` falla con `Not a directory`.
La ruta buena la da git y **resuelve al directorio común**, así que excluyes una
vez para todos:

```bash
printf 'data.db\ndata.csv\n' >> "$(git rev-parse --git-path info/exclude)"
```

En Windows, usa **`mklink /J`** (junction): es la única forma que **no** exige
modo desarrollador ni elevación.

---

## 3 · El orquestador barato y el hook que enruta: las dos se pueden

### 3.1 Sonnet de orquestador: documentado y sin límite — ⏸ **D18 SUSPENDIDA**

> **No se implementa nada de este apartado.** **[H]** *«lo de sonnet suspéndelo
> de momento, luego lo checamos»* (2026-08-16). Queda escrito para cuando se
> retome; **suspendida no es rechazada**, y la investigación no se repite.

El modelo de un subagente se fija en el frontmatter de su definición
(`.claude/agents/<name>.md`), y admite `sonnet`, `opus`, `haiku`, `fable`, un ID
completo, o `inherit`. **Por defecto hereda el del principal.** La documentación
del SDK trae el patrón exacto que pides, invertido:

```python
model="opus" if is_strict else "sonnet",   # barato por defecto, caro por excepción
```

> **No hay ninguna limitación documentada** para un orquestador en Sonnet que
> despache subagentes en modelos distintos. Y encaja con la regla que el sprint 6
> ya instaló —barato por defecto, el caro justifica—, **que hasta ahora solo
> podía cumplirse a mano.**

⚠ **El matiz que hay que medir antes de celebrarlo:** el coordinador es quien
lleva el contexto largo, y **el 73-83 % de tu gasto está por encima de 150k**.
Bajarlo a Sonnet reduce el precio por token del tramo más caro — pero es también
**quien escribe los briefs**, y nueve frentes de nueve refutaron una premisa del
brief. **Un orquestador peor escribe briefs peores, y el coste del brief malo lo
pagan los subagentes caros.** Esto se prueba una jornada y se mide; no se decide
leyendo una tabla de precios.

### 3.2 El hook que decide qué subagente: **existe y puede reescribir la orden**

Éste es el hallazgo que hace viable lo que pediste.

- La herramienta se llama **`Agent`** (se llamaba `Task` hasta la v2.1.63). Ése
  es el nombre para el matcher.
- Un hook `PreToolUse` **puede modificar la entrada antes de ejecutar**, no solo
  permitir o bloquear. El esquema de salida documentado:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": { }
  }
}
```

> **`updatedInput` es la pieza.** Un hook determinista puede leer la petición de
> despacho y **reescribir el tipo de subagente y el modelo** antes de que
> arranque: lectura → barato, auditoría → medio, código → el que toque. Es el W3
> aplicado al despacho: **no una regla escrita en una skill que el coordinador
> puede olvidar, sino un cable.**

⚠ **Límite honesto: qué campos concretos de `tool_input` de `Agent` se pueden
reescribir NO está documentado.** Que `updatedInput` existe, sí; que acepte
`subagent_type` y `model`, hay que **probarlo con un canario** antes de diseñar
nada encima. Es exactamente la ley de la casa: *toda frontera de permisos se
prueba con canario, no leyendo flags*.

### 3.3 Y hay dos hooks más que no estábamos usando

| Hook | Recibe | `exit 2` |
|---|---|---|
| `SubagentStart` | `agent_type` | **no bloquea** — solo enseña stderr |
| `SubagentStop` | `agent_type` + `last_assistant_message` | **BLOQUEA: impide que el subagente pare** |

> **`SubagentStop` con exit 2 es un gate por frente.** Un subagente no puede
> declararse terminado sin cumplir el contrato — el criterio de salida deja de
> ser una frase en el brief y pasa a ser una condición verificada. Es la misma
> forma que `TaskCompleted` que apunté en el RFD 25, pero **sin necesitar Agent
> Teams**.

### 3.4 El número que nadie ha tocado — y por qué **no** hay que clavarlo

**`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` vale 20 por defecto.**
(`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` vale 3; ahí el defecto ya es razonable.)

Mi voto original era ponerlo a 3. **Arbitrado en contra**, y la razón del humano
convierte esto en otra cosa:

> **[H]** *«lo de MAX_SUB_AGENTS, no lo veo tan bien, lo que quiero es ir
> logrando ir aumentando la capacidad de subagentes»* — 2026-08-16

**Y revisándolo con eso delante, tenía razón y mi voto estaba mal fundado.**
El techo de 3 descansa sobre **una sola medición**: 677 s con 5 frentes contra
~330 s, ×2,05. Y esa medición está **confundida por el §0 de este mismo
documento**: si el `addopts` del proyecto lleva `-n auto`, esos 5 frentes
lanzaron **40 procesos de test en 8 núcleos**. El ×2,05 puede no ser el techo del
harness, sino el precio de una fuga de configuración.

> **Clavar 3 habría congelado en una variable de entorno un número que sale de un
> experimento contaminado.** Es el mismo error que persigo desde el sprint 3, con
> el signo cambiado: no un número que nadie mide, sino **una medición sin repetir
> ascendida a límite**.

Lo que sí hace falta es que el número **exista, tenga fecha, máquina y
procedimiento, y pueda subir**. Las tres palancas que lo suben ya están en este
RFD y ninguna necesita el cap:

| Palanca | Dónde | Qué libera |
|---|---|---|
| Presupuesto de núcleos por frente | §0 y §1.2 | quita la sobresuscripción ×5 |
| Worktrees: **0 B de RAM**, `.git/objects` compartido | §2 | la RAM no es el techo |
| `CPUQuota` por frente | §1.4 | acota de verdad — **solo Linux**, o sea la SER8 |

Y la cuarta está fuera de este apartado: **cada frente cuesta contexto**, y §4.5
es lo que lo abarata. Higiene de salida y capacidad de subagentes **son el mismo
problema visto por los dos extremos**.

---

## 4 · Headroom: **no adoptar**, y las razones son medibles

Lo pediste como ahorro de tokens. Lo investigué a fondo — el repo es real,
activo (último commit de ayer), Apache-2.0, con 762 ficheros de test propios y un
`LIMITATIONS.md` **más honesto que su README**. Y aun así, para tu caso, no.

### 4.1 El ahorro no está donde está tu gasto — medido sobre tus cargas

| Tu carga | Compresión |
|---|---:|
| **`git log --stat` (800 commits)** | **0,0 %** |
| **`Read` de un `.py`** | **0,0 %** (`router:excluded:tool`) |
| grep / rg | 49,4 % |
| **pytest (275 KB)** | 99,1 % |
| JSON repetitivo de campos cortos | 61,3 % |
| JSON con campos de texto largo | 2,2 % |

Y su propio `LIMITATIONS.md` sobre el código:

> *«If the most recent user message contains keywords like "analyze", "review",
> "explain", "fix", "debug", "optimize", "error", "bug" — **ALL code in the
> conversation is protected**.»*

**Es decir: en una sesión de depuración —las tuyas— el código no se comprime por
diseño.** Tu gasto está en contexto acumulado, código y logs de git. Los tres
miden 0 %.

### 4.2 El «20 % para agentes de código» no tiene metodología

La cifra aparece **solo** en el tagline del README y en la descripción de GitHub.
Cero apariciones en código, benchmarks o resultados. Y la tabla «Proof» la genera
`benchmarks/real_world_agent_benchmark.py`, cuyo docstring dice *«This is NOT
synthetic data»* mientras el código son plantillas con `random.choice` **sin
seed** — **irreproducible por construcción**. El harness de accuracy que sí es
serio (envuelve lm-eval) está medido sobre **gpt-4o-mini**, no sobre Claude, y
**ninguna de sus tareas es de código**.

### 4.3 El riesgo dominante es el prompt cache, y es tu topología exacta

De su propio CHANGELOG, describiendo Claude Code con subagentes paralelos:

> *«the forwarded prefix is byte-unstable on nearly every turn and the provider
> prompt cache is re-written instead of read — reported as **~4.4x
> cache-creation inflation and a 2.5–3x net cost increase under Claude Code**.»*

Ese arreglo se liberó. Pero el issue **#2438** —*«Proxy defeats Anthropic prompt
caching… measured 2-7x cost increase»*— se abrió **después** del arreglo y se
cerró **hace dos días**.

> Con el **73-83 % de tu gasto por encima de 150k**, tu factura la domina el
> *cache read*. Si el proxy desestabiliza el prefijo, **el sobrecoste se come
> cualquier ahorro por compresión**, y lo dicen ellos.

### 4.4 Y rompe la regla de la fuente única

`headroom wrap claude` escribe `ANTHROPIC_BASE_URL` en el
**`.claude/settings.local.json` de tu repo**, instala un hook `SessionStart` en
`~/.claude/settings.json`, y registra **Serena como MCP de usuario** — que su
propio README admite que *«stays available in your other projects»*. Es el mismo
segundo canal fuera del repo que ya descartó `npx skills add`, y lo prohíbe el
`ADR-20260803-skills-fuente-unica`.

### 4.5 Lo que sí atacaría el mismo problema, gratis

**Higiene de salida de herramienta.** Cero riesgo, cero latencia, cero
dependencia, y ataca exactamente donde el proxy mide 0 %:

- `pytest -q --tb=line` en vez de la traza completa
- `git log --oneline -n 50` en vez de `--stat` de 800 commits
- `jq` para recortar el JSON **antes** de que lo lea el agente
- y lo que ya tienes: **subagentes**, que son compresión con pérdida cuyo
  «retrieve» es volver a preguntar

Y una alternativa nativa que merece su propia investigación: el **context editing
de Anthropic** (`clear_tool_uses_20250919`), que borra tool results viejos
*server-side* y **sin proxy** — aunque también invalida el prefijo del caché, y
por eso trae `clear_at_least`, que existe justo para decidir si compensa.

---

## 5 · Decisiones — cuatro arbitradas el 2026-08-16, una abierta

El humano respondió: **[H]** *«Me parece bien, lo de sonnet suspéndelo de
momento, luego lo checamos. Lo que sí lo de MAX_SUB_AGENTS, no lo veo tan bien,
lo que quiero es ir logrando ir aumentando la capacidad de subagentes. Alta
prioridad en la higiene de los logs.»*

| | Decisión | Estado | Sale a |
|---|---|---|---|
| **D15** | Medir el `-n auto` antes de nada | ✅ **aceptada** | sprint 8 · S3 |
| **D16** | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=3` | ❌ **rechazada** | sprint 8 · S4, invertida |
| **D17** | Canario del hook de enrutado | ⬜ **sin arbitrar** | — |
| **D18** | Orquestador en Sonnet | ⏸ **suspendida** | — |
| **D19** | Headroom | ❌ **no adoptar** | §4 queda como el porqué |

**D15 — aceptada.** Un `grep` de diez segundos que puede explicar el ×2,05 y
dejar medio RFD sin objeto. Entra en el sprint 8 con la orden de **reportar lo
que salga, aunque sea nada**: un «no está» también cierra la hipótesis.

**D16 — rechazada, y el motivo cambia el diseño, no solo la respuesta.** No se
pone el cap. La dirección es la contraria: **subir la capacidad**. Lo que entra
en su lugar (§3.4) es el número **con fecha, máquina y procedimiento
repetible**, para que suba cuando la medición lo permita — empezando por quitarle
al experimento la contaminación del §0, y con la SER8 como el sitio donde
`CPUQuota` por fin existe. **Que nadie lo re-proponga**: la razón está citada
arriba.

**D17 — sigue sin arbitrar, y es la única.** Comprobar si `updatedInput` acepta
`subagent_type` y `model` en la herramienta `Agent`. Si acepta, el enrutado
determinista es un proyecto real; si no, es una idea muerta y lo sabemos en una
tarde. **No la doy por aceptada con el «me parece bien»**: no la mencionó, y un
canario que toca el despacho de subagentes necesita firma explícita.

**D18 — suspendida, no rechazada.** *«luego lo checamos.»* El §3.1 queda como
está para cuando se retome: la hipótesis del ahorro es sólida y la del brief peor
también, y el brief malo lo pagan los subagentes caros. **No entra en el sprint
8** y no se toca la configuración de modelo de nada.

**D19 — no adoptar.** Las razones del §4 quedan escritas para que no se
re-proponga en dos meses. Lo que sí sale, y **con prioridad alta por orden
expresa**, es la higiene de salida del §4.5 — sprint 8 · S1.

---

## 6 · Lo que no pude comprobar

- **El `pytest.ini` del repo del copiloto no lo tengo.** Todo el §0 es una
  hipótesis fundada, no un diagnóstico. **Es lo primero que hay que medir.**
- **Los números de Amdahl del §1.2 son de trabajo**, no tuyos. `p` y `c` se miden
  con dos corridas de `hyperfine` y cambian el reparto óptimo.
- **Ni la ganancia real del SMT** en tu 8845HS: si `-n 16` no baja al menos ~20 %
  frente a `-n 8`, `-n logical` solo compra calor.
- **Qué campos de `tool_input` acepta `updatedInput`** — no documentado, por eso
  D17 es un canario y no un diseño.
- **El RSS real de un agente y de tu suite.** No hay dato público fiable de lo
  primero; cualquier cifra sin medir es inventada. El techo del heap de V8 lo da
  `node -e "console.log(require('v8').getHeapStatistics().heap_size_limit)"` en
  tu máquina.

## Fuentes

- [pytest-xdist — modos de distribución](https://pytest-xdist.readthedocs.io/en/stable/distribution.html) · [cómo funciona](https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html) · [fixtures de sesión con FileLock](https://pytest-xdist.readthedocs.io/en/stable/how-to.html) · [limitaciones conocidas](https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html)
- [pytest-benchmark — FAQ y aislamiento](https://pytest-benchmark.readthedocs.io/en/latest/faq.html) · [CHANGELOG: se desactiva bajo xdist por diseño](https://github.com/ionelmc/pytest-benchmark/blob/master/CHANGELOG.rst)
- [git-worktree — qué comparte y qué no](https://git-scm.com/docs/git-worktree) · [git-clone — avisos de `--shared` y `--reference`](https://git-scm.com/docs/git-clone)
- [systemd.resource-control — `CPUQuota`, `CPUWeight`, `MemoryHigh`](https://man7.org/linux/man-pages/man5/systemd.resource-control.5.html) · [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html) · [taskset(1)](https://man7.org/linux/man-pages/man1/taskset.1.html)
- [Job Objects de Windows](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects) · [`mklink`](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/mklink) · [`.wslconfig`](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)
- [Claude Code — subagentes: frontmatter, modelo, concurrencia](https://code.claude.com/docs/en/sub-agents) · [hooks: `updatedInput`, `SubagentStart`/`SubagentStop`](https://code.claude.com/docs/en/hooks) · [SDK de subagentes](https://code.claude.com/docs/en/agent-sdk/subagents)
- [headroomlabs-ai/headroom](https://github.com/headroomlabs-ai/headroom) · [issue #2438 — el proxy derrota el caché, 2-7×](https://github.com/headroomlabs-ai/headroom/issues/2438) · [issue #2509](https://github.com/headroomlabs-ai/headroom/issues/2509) · [issue #2462](https://github.com/headroomlabs-ai/headroom/issues/2462)
- [Context editing de Anthropic](https://platform.claude.com/docs/en/build-with-claude/context-editing) · [AMD Ryzen 7 8845HS](https://www.amd.com/en/products/processors/laptop/ryzen/8000-series/amd-ryzen-7-8845hs.html) · [SQLite: bloqueo y concurrencia](https://www.sqlite.org/lockingv3.html)
