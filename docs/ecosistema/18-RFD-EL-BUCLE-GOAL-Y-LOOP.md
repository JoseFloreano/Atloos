# RFD — El bucle: `/goal` y `/loop` como motor del setup

> **Estado:** 🔴 **Propuesta — pide decisión.** Cuatro decisiones abiertas
> (D1–D4) para arbitrar.
> **Fecha:** 2026-08-09 · **Autor:** Cowork (auditor externo, nube).
> **Origen:** `docs/tmp/skills y plugins.md` (11 piezas) y
> `5-Skills-de-Claude-Code — Isa Muñuzuri.pdf` (5 skills), entregados el 08-09.
> **Método:** documentación oficial de Claude Code como fuente primaria
> (`code.claude.com/docs`), tres agentes de investigación en paralelo para el
> catálogo externo, y evidencia de primera mano del entorno de esta sesión.
> **Contexto:** `subagentes/04` (workstreams) · `auditoria/11` (del caso a la
> clase) · `ecosistema/16` (ahorro de tokens) · `ADR-20260801-higiene-vault` ·
> `ADR-20260801-os-servidor-24-7` (⚠ este RFD lo toca).

> **Actualización 2026-08-09, mismo día**: escrito contra `cc2ac79`; **HEAD es
> ahora `c3a21b1`**. Mientras se redactaba, el Opus cerró el parser del W3
> (`acdfa67`, arnés 11→**23 casos**) y **cosechó los RFD 04, 10 y 12**
> (`c3a21b1`), que ya no existen en el repo: sus decisiones viven en ADRs.
> Las citas a `subagentes/04` de este documento hay que leerlas contra su ADR.
> El paso 0 del §15 queda **cumplido**.

---

## 0. El resumen de una página

`/goal` y `/loop` **no son skills de terceros ni comandos que uno se escribe**:
son piezas nativas de Claude Code, documentadas por Anthropic, y el blog más
citado sobre ellas **se equivoca** al decir que se implementan como
`.claude/commands/goal.md`. Verificado en la fuente.

Y son exactamente lo que el nombre del proyecto prometía. **Atlas + loop**: el
atlas es el mapa durable (vault, ADRs, `codebase-map`), el loop es el motor que
trabaja contra él. Este RFD dice cómo se ensamblan.

Pero traen una colisión de frente con la ley 1 de la casa, y es el hallazgo
central de este documento:

> **El evaluador de `/goal` no ejecuta herramientas.** Solo juzga lo que ya
> apareció en la conversación. Es decir: **cierra objetivos leyendo el reporte,
> no el artefacto** — justo lo que este setup existe para impedir.

La buena noticia es que la propia plataforma trae el antídoto (`hooks` de tipo
`agent`, que sí leen ficheros y corren comandos), y este setup ya tiene la
mitad del trabajo hecho: `gate-test.py` es, literalmente, un productor de
evidencia de máquina. Lo que falta es el pegamento, y es poco.

**Recomendación en una línea:** adoptar `/goal` y `/loop`, pero **envueltos**
en un contrato de evidencia propio; adoptar 3 skills externas de las 16 piezas
revisadas; descartar el resto; y **revisar el ADR de la mini PC antes de
comprar nada**, porque las Routines de nube cubren buena parte de su motivo.

---

# Parte I — El inventario, auditado

## 1. Hallazgo de seguridad, primero

El fichero `skills y plugins.md` contiene una URL de `skilltree.altari.ai` con
un **`mcp_token` JWT personal incrustado en el query string**, con `exp` a
~mayo de 2027. **No la abrí**, deliberadamente: abrirla desde aquí habría
quemado el token contra una IP que no es la tuya.

- Estado hoy: `docs/tmp/` **sí está en `.gitignore`** → no viaja a GitHub. [R]
- Pero esa regla **no está commiteada**: `git show HEAD:.gitignore` no la
  contiene. [R] En la otra laptop, esa carpeta **no está ignorada**. Si el
  fichero llega allí por OneDrive y alguien hace `git add -A`, el token se
  publica.
- Además, la regla se añadió **mientras yo auditaba** (el `.gitignore` cambió
  de `239ab09` a `eba986a` entre dos lecturas mías). Lo digo porque es la
  trampa 5 del handoff ocurriendo en vivo.

**Acción mínima:** commitear la línea `docs/tmp/` y **revocar ese token** en
altari.ai. Un token en un fichero dentro de un repo git es un incidente aunque
hoy esté ignorado: los `.gitignore` no son retroactivos y las carpetas
compartidas viajan.

## 2. Veredictos del catálogo

| Pieza | Qué es | Madurez | Veredicto |
|---|---|---|---|
| **`/goal`** | Nativo de Claude Code (v2.1.139+) | Anthropic, documentado | ⭐ **ADOPTAR envuelto** — Parte II |
| **`/loop`** | Skill bundled nativa | Anthropic, documentado | ⭐ **ADOPTAR envuelto** — Parte II |
| `web-design-guidelines` | Vercel; audita UI contra 100+ reglas vivas | Vercel, MIT, 526K instalaciones | ✅ **Adoptar** — cubre un hueco real |
| `frontend-design` | Anthropic; fuerza dirección estética deliberada | Anthropic, Apache-2.0, 753K instalaciones | ✅ **Adoptar** (⚠ comando del PDF equivocado, §3) |
| `mcp-builder` | Anthropic; 4 fases + evals para construir MCPs | Anthropic, Apache-2.0 | ✅ **Adoptar** — encaja con `agentic-system-design` |
| Playwright MCP | Microsoft; navegador real por árbol de accesibilidad | Microsoft, Apache-2.0, 6.7M desc/sem | 🟡 **Adoptar acotado** — verificación e2e de subagentes |
| `agent-browser` | Vercel; navegador en Rust vía CDP | Vercel, Apache-2.0 | 🟡 **Uno u otro, no los dos** (D3) |
| Context7 | Upstash; docs de librerías al día | Upstash, MIT (solo cliente) | 🟡 **Con cautela** — servicio hospedado, sin self-host |
| Claude Code Setup (oficial) | 1 skill que **recomienda** automatizaciones | Anthropic, Apache-2.0 | 🔵 **Robar la forma** — `SKILL.md` fino + `references/` categorizadas |
| Claude Mem | Memoria persistente: 5 hooks + daemon HTTP + SQLite/Chroma | Individuo, Apache-2.0, CI real | 🔵 **Robar una idea** — los tags que preservan lo escrito a mano |
| Headroom | Compresor de contexto en Rust | Individuo→startup, Apache-2.0, CI+Codecov | 🔵 **Robar la idea** — no el stack |
| Task Observer | Una skill que "observa" y propone mejoras a otras skills | Individuo, CC-BY-4.0, **0 tests** | ❌ **Descartar** — §4 |
| Agent-Reach | Lectura de 17 plataformas (Twitter, Reddit, YouTube…) | 20.8K★, MIT, **tests reales** | ❌ **Fuera de alcance hoy** |
| OmniRoute | Gateway/proxy de 290+ proveedores LLM | 42K★, MIT | 🚨 **Descartar** — §5 |
| `find-skills` | Meta-instalador que busca e instala skills sola | Vercel, MIT | ❌ **NO instalar** — §6 |
| SkillTree (altari.ai) | Catálogo hospedado | — | ❌ Descartar; **revocar el token** |

### 3. Tres comandos del PDF están mal — los corregidos

El PDF es divulgativo y bienintencionado, pero dos de sus cinco comandos no
apuntan donde dicen. Verificado contra `skills.sh`:

| Skill | Comando del PDF | Correcto |
|---|---|---|
| `frontend-design` | `…/anthropics/claude-code --skill frontend-design` | `…/anthropics/skills --skill frontend-design` |
| `agent-browser` | `…/vercel-labs/agent-browser` (sin `--skill`) | `…/vercel-labs/agent-browser --skill agent-browser` |
| `web-design-guidelines` | (solo dio el repo) | `…/vercel-labs/agent-skills --skill web-design-guidelines` |

El caso de `frontend-design` importa más de lo que parece: `anthropics/claude-code`
es el repo de la CLI y está bajo **licencia comercial propietaria**, no Apache.
Sí contiene una copia anidada de la skill, pero no en la ruta que el instalador
escanea. El repo correcto es `anthropics/skills`.

### 4. Task Observer — por qué se descarta, y qué se le roba

Se llama "one skill to rule them all" y suena a mecanismo de gobierno. No lo es:
sus "hooks" y "checkpoints" **no son hooks del sistema** — son frases en
lenguaje natural dentro de un `SKILL.md` que el modelo puede seguir o no. Ni
siquiera su propia activación está garantizada: pide que le añadas una línea a
tu `CLAUDE.md` para que cargue. Cero tests, cero CI funcional.

Es, punto por punto, **la clase de fallo que el RFD 11 acaba de nombrar**:
la convención escrita que vuelve porque no tiene arnés. Adoptarla justo después
de auditar ese RFD sería incoherente.

Lo que sí vale robarle: la idea de un **fichero de principios transversales**
que se comprueba al crear o editar cualquier skill. Pero implementado como
comprueba esta casa — un caso en `test-skill-paths.py`, no una promesa.

### 5. OmniRoute — descartar, y no es por gusto

Su versión npm 3.8.5 fue bloqueada por Socket.dev con hallazgos de malware
potencial: instalación de **certificados raíz en el almacén de confianza del
SO**, manipulación de DNS/hosts, servidor MITM embebido y capacidad de extraer
credenciales de keychains. El mantenedor **reconoció 2 de los 6 hallazgos como
vulnerabilidades reales** (fuga de credenciales en Cloud Sync, parcheada en
3.8.6). No hace falta decidir si fue malicioso o descuidado: es un proxy de un
solo mantenedor por el que pasarían todas tus llamadas y todas tus claves.

Y es **ortogonal al problema**: enruta proveedores, no gestiona memoria.

### 6. `find-skills` — el que rompe el contrato

Merece párrafo propio porque es el que un lector del PDF instalaría primero.

`find-skills` enseña al modelo a buscar en el catálogo y **ejecutar solo**
`npx skills add <repo@skill> -g -y`. El `-y` salta toda confirmación; el `-g`
instala global. El destino no es tu repo: escribe en `~/.agents/skills/` con un
symlink a `~/.claude/skills/` — mecanismo con **bug abierto y confirmado**
(`vercel-labs/skills#851`: el symlink a veces no se crea y la skill queda
invisible). No documenta ninguna comprobación de duplicados.

Es decir: **un segundo canal de skills, fuera del repo, sin dedup contra las 34
que ya tienes, instalando sin preguntar.** El
`ADR-20260803-skills-fuente-unica` existe precisamente porque tener dos fuentes
de verdad ya les costó una vez. Instalar `find-skills` es reabrir esa herida por
la puerta de atrás.

Lo aprovechable es el catálogo (`skills.sh`) como **fuente de consulta manual**,
y la idea de una skill que *proponga* — nunca que instale.

---

# Parte II — `/goal` y `/loop`: qué son de verdad

## 7. La mecánica, desde la fuente

Todo lo de esta sección sale de `code.claude.com/docs/en/goal` y
`…/scheduled-tasks`, no de blogs. **Corrección importante**: el artículo más
citado sobre estos comandos afirma que son slash commands personalizados que
uno escribe en `.claude/commands/goal.md`. Es falso. Son nativos.

### 7.1 `/goal` — la brújula

```text
/goal all tests in test/auth pass and the lint step is clean
/goal                 # estado: condición, duración, turnos, gasto, última razón
/goal clear           # también: stop, off, reset, none, cancel
```

- Requiere **v2.1.139+**. **Una meta activa por sesión**; una nueva reemplaza a
  la anterior. La condición admite hasta **4.000 caracteres**.
- Ponerla **arranca un turno inmediatamente**, con la condición como directiva.
- Tras **cada turno**, un modelo pequeño y rápido (Haiku por defecto) responde
  sí/no y **da una razón corta**. Si es "no", esa razón **se le pasa a Claude
  como guía del turno siguiente**. Si es "sí", la meta se limpia sola.
- Sobrevive a `--resume` / `--continue`; el contador de turnos, el cronómetro y
  el gasto se reinician.
- Funciona headless: `claude -p "/goal …"` corre el bucle entero en una
  invocación. Con salida de texto por defecto **no imprime nada hasta cumplir**
  — usar `--output-format stream-json --verbose` o parece colgado.
- **No cambia permisos.** Para que los turnos corran desatendidos hay que
  emparejarlo con auto mode.
- **Es un envoltorio sobre un Stop hook de tipo `prompt` con alcance de
  sesión.** Por eso exige workspace de confianza y **no está disponible con
  `disableAllHooks` ni con `allowManagedHooksOnly`**.

Y el dato que gobierna todo lo demás:

> **El evaluador no llama a herramientas.** Solo puede juzgar lo que Claude ya
> volcó en la conversación.

### 7.2 `/loop` — el motor

```text
/loop 5m check if the deployment finished     # intervalo fijo → cron
/loop check whether CI passed                 # sin intervalo → Claude elige (1 min–1 h)
/loop                                         # prompt de mantenimiento, o tu loop.md
/loop 20m /review-pr 1234                     # una skill como prompt
```

- Es una **skill bundled**, no un comando escrito a mano.
- Sin intervalo, Claude elige el retardo **tras cada iteración** y dice cuál y
  por qué. En este modo puede terminar el bucle solo llamando a
  `ScheduleWakeup` con `stop: true`. *(Evidencia de primera mano: esta sesión
  tiene esa herramienta y su contrato exactamente así.)*
- **`loop.md` sustituye el prompt de mantenimiento**: `.claude/loop.md` (gana)
  o `~/.claude/loop.md`. Se relee **en cada iteración**, así que se puede
  afinar con el bucle corriendo. Tope 25.000 bytes.
- **Caduca a los 7 días**, sin excepción. `Esc` lo para. Es de sesión: si
  cierras la sesión, muere (salvo que la mandes a background).
- Puede ejecutar skills, pero **solo las que Claude puede auto-invocar**. Las
  marcadas `disable-model-invocation: true` llegan como texto plano.
  **Verificado: ninguna de tus 34 skills lleva esa marca** → todas son
  invocables desde un `/loop`. [R]
- Jitter determinista, máximo 50 tareas por sesión, `CLAUDE_CODE_DISABLE_CRON=1`
  lo apaga todo.

### 7.3 Las tres formas de mantener viva una sesión

| Enfoque | El siguiente turno arranca cuando | Para cuando |
|---|---|---|
| `/goal` | Termina el turno anterior | Un modelo confirma que la condición se cumple |
| `/loop` | Pasa un intervalo | Tú lo paras, o Claude decide que acabó |
| Stop hook propio | Termina el turno anterior | Lo decide **tu script** |

La tercera fila es la tuya: `check-vault-updated.py` ya vive ahí.

### 7.4 Las tres formas de programar trabajo

| | Routines (nube) | Tarea de escritorio | `/loop` |
|---|---|---|---|
| Corre en | Nube de Anthropic | Tu máquina | Tu máquina |
| ¿Máquina encendida? | **No** | Sí | Sí |
| ¿Sesión abierta? | **No** | No | **Sí** |
| Ficheros locales | No (clon fresco) | **Sí** | **Sí** |
| Intervalo mínimo | 1 hora | 1 minuto | 1 minuto |
| Permisos | Autónomo, sin prompts | Configurable | Hereda de la sesión |

---

# Parte III — La colisión con la ley 1

## 8. El problema, dicho sin rodeos

La primera ley de esta casa dice: **el código de salida no es el estado; el
reporte no es el artefacto.** Todo el setup está construido sobre ella: el
`merge-gate-guard` no cree a la skill, `gate-test.py` no cree al agente, y la
auditoría de ayer no creyó al implementador.

`/goal`, tal como viene, hace justo lo contrario: su evaluador lee la
transcripción. Si el turno dice *"corrí los tests y pasaron"*, el evaluador lo
lee, lo cree y **cierra la meta**. No hay ningún punto en el que se mire el
disco.

Esto no es un bug de Anthropic — la documentación lo dice con todas las letras y
recomienda escribir la condición *"como algo que la propia salida de Claude
pueda demostrar"*. Es un contrato razonable para el caso general. Lo que pasa es
que **el caso general no es este proyecto**.

Un bucle autónomo amplifica lo que se le dé. Si le das un evaluador que cree
reportes, has construido una máquina de acumular reportes falsos, corriendo sola
mientras duermes. Es la peor combinación posible de las dos propiedades que este
setup más aprecia.

## 9. El antídoto ya está en la plataforma

Los hooks admiten tres tipos, y el tercero cambia el juego:

| Tipo | Qué hace | Ve el disco |
|---|---|---|
| `command` | Corre un script (lo que tú ya usas) | Sí |
| `prompt` | Una llamada a un modelo, decide sí/no + razón | **No** |
| `agent` ⚠ experimental | **Lanza un subagente con herramientas**: lee ficheros, corre comandos, hasta 50 turnos | **Sí** |

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ {
        "type": "agent",
        "prompt": "Verify that all unit tests pass. Run the test suite and check the results. $ARGUMENTS",
        "timeout": 120
      } ] }
    ]
  }
}
```

Con eso, la pregunta *"¿está hecho?"* deja de contestarse leyendo la
conversación y pasa a contestarse **corriendo la suite**. Es el `merge-gate` otra
vez, pero aplicado al cierre de turno en vez de al merge.

Cautela honesta: **es experimental** y la propia documentación recomienda hooks
de comando para producción. Por eso la propuesta de abajo no depende de él —
lo usa como capa 2, con la capa 1 en un `command` determinista.

## 10. El segundo choque: tu Stop hook ya vive ahí

`check-vault-updated.py` es un `Stop` hook que bloquea el cierre **una vez por
sesión**. Con `/goal` o `/loop`, una sesión deja de ser "media hora y cierro" y
pasa a ser 40 turnos durante seis horas.

Consecuencia concreta: **el anti-drift dispara pronto, se marca como hecho, y se
calla el resto del bucle** — es decir, se apaga exactamente en el escenario que
más lo necesita: horas de trabajo autónomo sin humano mirando. No es hipotético:
es la lectura directa de su contrato ("una vez por sesión, respeta
`stop_hook_active`") contra el nuevo modo de uso.

**Fix mínimo:** que la condición de disparo deje de ser "una vez por sesión" y
pase a ser "una vez por cada N ediciones de código sin registrar" o "una vez
cada N turnos con el flag puesto". Con su caso en el arnés, que para eso están
los 12 que ya tiene.

Detalle menor pero real: cambiar `ANTHROPIC_DEFAULT_HAIKU_MODEL` para afinar el
evaluador de `/goal` **también cambia el modelo de todo lo que use el modelo
pequeño** (resúmenes de conversación, funcionalidad de fondo). No es una perilla
local.

---

# Parte IV — El diseño: Atlas + loop

## 11. La tesis

> **Atlas** es el mapa durable: el vault, los ADRs, `_PROJECT.md`,
> `codebase-map`. **Loop** es el motor que trabaja contra él.
> Y la ley que los une: **un bucle solo converge si el mapa es verdadero.**

Esto no es poesía de naming. Es la razón por la que el C4 del RFD 11 —la
refutación de hechos falsos— deja de ser higiene y pasa a ser **precondición de
la autonomía**. Un vault que no puede retractarse es tolerable cuando un humano
lee cada turno. En un bucle de 40 turnos, es un multiplicador de error.

De ahí sale el orden correcto de adopción: **primero el mapa, después el motor.**

## 12. Las cuatro piezas que faltan

### P1 · `goal-forge` — la skill que escribe condiciones que no se pueden fingir

La skill más valiosa de todo este documento, y no existe en ningún catálogo:
convierte un objetivo difuso en una condición de `/goal` **verificable por
máquina**, en el idioma de evidencia de la casa.

Contrato que impondría:

1. **Un solo estado final medible** — un exit code, un conteo, una cola vacía.
2. **El comando que lo prueba**, nombrado en la condición: *"`py
   setup/hooks/tests/test-merge-gate-guard.py` imprime `N/N casos OK`"*.
3. **Las restricciones que importan** — qué no debe cambiar por el camino.
4. **Una cláusula de corte**: `o para a los 20 turnos`. La documentación lo
   soporta explícitamente y sin ella el bucle no tiene fondo.
5. **Rechaza** condiciones que solo puede satisfacer una afirmación. *"El código
   queda limpio"* no es condición; *"`ruff check .` sale 0"* sí.

El chiste es que esto ya existe a medias: es el **bloque 6 (predicción
obligatoria)** y el **bloque 7 (contrato de reporte)** de `plantilla-despacho.md`,
que ya te obligan a decir qué esperas y cómo se comprueba. `goal-forge` es esa
disciplina, comprimida a 4.000 caracteres y puesta donde el evaluador la lee.

### P2 · `goal-evidence-guard` — el Stop hook que sí mira el disco

Dos capas, como el gate:

- **Capa 1, `command`** (determinista, producción): si la condición nombra un
  artefacto (`gate-verde.json`, un fichero, un exit code registrado), comprueba
  que **existe y es fresco**. Reutiliza el patrón de `merge-gate-guard`: el sha
  del HEAD contra el sha de la evidencia. Ya está escrito, solo cambia el
  evento.
- **Capa 2, `agent`** (opt-in, experimental): para condiciones que no se pueden
  reducir a un fichero, lanza un subagente que corre la comprobación.

Y el corolario de la casa aplicado aquí: **esta frontera se prueba con canario**.
Una condición deliberadamente falsa ("los tests pasan", con la suite roja) que
el evaluador de `/goal` cerraría y el guard debe rechazar. Sin esa prueba,
P2 es una convención escrita — y ya sabemos cómo acaban.

### P3 · `loop.md` de la casa

El `.claude/loop.md` del proyecto sustituye el prompt de mantenimiento genérico
por el ciclo propio. Borrador:

```markdown
Lee `10-Projects/atloos/_PROJECT.md` y toma el primer pendiente activo.
Trabaja UNA unidad de él. Antes de reportarlo hecho, corre su arnés y pega la
salida. Si no hay arnés, dilo y no lo des por hecho.
Registra en el vault lo que cambió (pendientes/estado, 2-5 líneas).
Si el pendiente está bloqueado por una decisión del usuario, párate y dilo:
no elijas por él.
No cosechar, no mergear a main, no tocar otros proyectos del vault.
```

Se relee en cada iteración, así que se afina en caliente. Y el tope de 25 KB da
margen de sobra.

### P4 · El contrato de meta dentro de `workstream-dispatch`

Hoy la plantilla de despacho tiene 7 bloques. La condición de `/goal` es el
cierre natural del bloque 7: **el criterio de salida del subagente y la
condición de la meta son el mismo objeto**, escrito una vez. Un frente
despachado con una condición bien forjada puede correr en `/goal` sin humano
hasta que su propia evidencia diga que acabó.

Ahí es donde el setup se vuelve otra cosa: `workstream-dispatch` define la
tarea, `goal-forge` la vuelve verificable, `/goal` la persigue, el guard la
cierra contra el disco, `workstream-merge-gate` + W3 la integran, y
`session-close` la registra. **Es el ciclo completo, y cinco de esas seis piezas
ya existen.**

## 13. Qué capa usar para qué

| Necesidad | Herramienta | Por qué |
|---|---|---|
| Terminar un trabajo con final verificable | `/goal` + P1 + P2 | Para solo cuando la evidencia existe |
| Vigilar algo que cambia solo (CI, PR, build) | `/loop` sin intervalo | Claude ajusta el ritmo; o mejor, `Monitor` |
| Mantenimiento recurrente en la laptop | `/loop` con `loop.md` | Ficheros locales, 1 min de granularidad |
| Que corra con la laptop cerrada | **Routines** | Nube, 1 h mínimo, clon fresco |
| Auditoría nocturna del vault | Tarea de escritorio | Necesita el vault local, que Routines no ve |

## 14. ⚠ Esto toca el ADR de la mini PC

`ADR-20260801-os-servidor-24-7` (Debian 13 headless para el servidor 24/7 del
puente Telegram) sigue en estado **`proposed`**. Antes de comprar o configurar
hardware, conviene mirar que **las Routines cubren buena parte de su motivo**:
corren en la nube, sin máquina encendida, con triggers de horario, de API (POST
con bearer token) y de eventos de GitHub.

Lo que **no** cubren, y por eso no es un reemplazo automático:

- **No ven ficheros locales** — clonan el repo. Tu vault vive en OneDrive, no en
  GitHub… salvo que ya tiene remoto propio en GitHub
  (`ADR-20260726-vault-git-fuera-de-onedrive`). Eso lo pone al alcance.
- **Mínimo 1 hora**, contra el minuto que da el daemon.
- **Sin Telegram**: el puente es tuyo y la mensajería es su razón de ser.
- Requieren login de claude.ai y tienen tope diario de runs.

No propongo revocar nada. Propongo que **el ADR se relea antes de gastar**, y
eso es D4.

---

# Parte V — Qué NO hacer

- **No instalar `find-skills`.** Rompe la fuente única (`ADR-20260803`) e
  instala con `-y -g` sin dedup.
- **No poner `/goal` a correr con auto mode sin P2.** Es un bucle autónomo con
  un evaluador que cree reportes: la peor combinación posible aquí.
- **No meter dos navegadores.** Playwright MCP y `agent-browser` resuelven lo
  mismo; elegir uno (D3).
- **No depender del hook `agent` para producción.** Es experimental por
  declaración propia de Anthropic.
- **No confiar en `/loop` para nada durable.** Caduca a los 7 días y muere con
  la sesión. Lo durable son Routines o tareas de escritorio.
- **No tocar el `ANTHROPIC_DEFAULT_HAIKU_MODEL`** creyendo que solo afecta a
  `/goal`.
- **No re-litigar Graphiti.** Nada de este documento lo toca.

---

# Parte VI — Decisiones abiertas

## D1 · ¿`/goal` envuelto o `/goal` desnudo?

| | Opción | Coste | Riesgo |
|---|---|---|---|
| **(a)** | Adoptar `/goal` tal cual y confiar en condiciones bien escritas | ~0 | El evaluador cierra metas leyendo reportes. Es la ley 1 rota por diseño |
| **(b)** ⭐ | Adoptar `/goal` + `goal-forge` + `goal-evidence-guard` (capa `command`), con canario | 1 skill + 1 hook + arnés | El guard puede bloquear metas legítimas si la condición no nombra artefacto — mitigable con fail-open fuera de las condiciones que sí lo nombran |
| **(c)** | No adoptar `/goal`; quedarse con Stop hooks propios | ~0 | Se pierde el evaluador por turno y la cláusula de corte, que son buenos |

**Mi voto: (b).** Es el mismo patrón que ya funcionó con el merge gate, y la
pieza cara (`gate-test.py`, el contrato sha↔HEAD) ya está escrita.

## D2 · ¿Qué dispara el anti-drift en sesiones largas?

| | Opción |
|---|---|
| **(a)** | Dejarlo como está (una vez por sesión) y asumir el hueco |
| **(b)** ⭐ | Cada N ediciones de código sin registrar (N configurable, arranque en 10) |
| **(c)** | Cada N turnos con el flag puesto |

**Mi voto: (b)** — mide la causa (código sin registrar), no el síntoma (turnos).
Es la lección del RFD 11 C1: el disparador tiene que ser un momento reconocible.

## D3 · ¿Qué navegador?

| | Opción | A favor | En contra |
|---|---|---|---|
| **(a)** ⭐ | Playwright MCP | Microsoft, 6.7M desc/sem, 3 issues abiertos, multi-navegador | *"Playwright MCP is not a security boundary"* — cita textual de su README |
| **(b)** | `agent-browser` | Vercel, en Rust, muy eficiente en tokens (el PDF dice 10× menos) | Superficie nueva; el ahorro de tokens es [AR], no medido por nosotros |
| **(c)** | Ninguno por ahora | Cero superficie | Sin verificación visual para los frentes de frontend |

**Mi voto: (a)**, con allowlist de dominios y **jamás con un perfil logueado
real**. Ambos proyectos renuncian explícitamente a ser frontera de seguridad;
esa frontera la pones tú.

## D4 · ¿Se relee el ADR de la mini PC antes de gastar?

Sí / No. Es barato: media hora de comparación contra Routines. Si la respuesta
es que la mini PC sigue justificada, el ADR pasa de `proposed` a `accepted` con
un motivo medido en vez de por inercia — que es una mejora aunque no cambie
nada.

---

## 15. Orden de trabajo propuesto

**Primero el mapa, después el motor.** Nada de esto arranca hasta cerrar lo que
ya está en vuelo.

0. ~~Cerrar el parser del W3 y la cosecha triple.~~ ✅ **HECHO el 08-09**
   (`acdfa67` + `c3a21b1`). Verificado por mí: mis 8 sondas dan **10/10** contra
   el parser nuevo y el arnés pasa de 11 a **23 casos**.
1. **Seguridad**: revocar el token de altari.ai y commitear `docs/tmp/`.
2. **D1–D4 arbitradas.**
3. `goal-forge` + `goal-evidence-guard` con su arnés y su canario.
4. `loop.md` del proyecto, afinado en caliente durante una semana real.
5. `workstream-dispatch` gana el bloque de condición de meta.
6. Adoptar `web-design-guidelines`, `frontend-design` y `mcp-builder`.
7. Navegador, según D3.

## 16. Criterios de éxito

Medibles, no adjetivos. Ninguno se cierra con evidencia sustituta.

1. **El canario del guard**: una meta con condición falsa ("los tests pasan",
   suite en rojo) **no se cierra**. `/goal` desnudo la cerraría; con P2 no.
2. **Una jornada real** en `/loop` con `loop.md`, con el vault al día al final
   sin intervención — y el número de veces que el anti-drift disparó, contado.
3. **Un frente despachado con condición de meta** que corre en `/goal` hasta su
   propia evidencia, sin humano en el medio, y con `main` intacta.
4. **Coste medido**: gasto de tokens del bucle contra el de la misma tarea a
   mano. Sin este número, "el bucle nos hace más rápidos" es especulación —
   la misma trampa del criterio 5 del RFD 04.

---

## 17. Riesgos de esta propuesta

- **El hook `agent` es experimental** y puede cambiar bajo nosotros. Por eso la
  capa 1 es determinista y la 2 es opt-in.
- **La autonomía multiplica el error del mapa.** Si el vault sirve un hecho
  falso, un bucle lo propaga 40 veces. Mitigación: C4 del RFD 11 ya está
  implementado; el check de refutación a medias ya existe en `checks.md`.
- **Bucle que gasta sin converger.** Mitigación: cláusula de corte obligatoria
  en toda condición (`o para a los 20 turnos`), impuesta por `goal-forge`.
- **Dependencia de versión**: `/goal` pide v2.1.139+, el `stop: true` de
  `ScheduleWakeup` pide v2.1.202+, y el filtro de skills auto-invocables en
  fires programados, v2.1.196+. Conviene fijar una versión mínima en el README
  y comprobarla en `setup-new-machine`.
- **Sesgo del autor, declarado**: acabo de auditar el W3 y encontré ocho fallos
  en su parser. Es probable que eso me incline a proponer "otra compuerta" como
  solución a todo. El lector debería atacar precisamente el punto 9: ¿de verdad
  hace falta un guard, o basta con escribir condiciones que nombren artefactos?
  No tengo evidencia de campo para cerrarlo — solo el precedente del merge gate,
  donde la convención escrita falló y el arnés no.
