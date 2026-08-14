# Hooks — Enforcement determinista (auditoría R2)

El aislamiento de memoria por proyecto NO puede depender solo de instrucciones
en CLAUDE.md (compliance probabilística que se degrada en sesiones largas).
Estos hooks lo convierten en garantía: la llamada inválida se **bloquea antes
de ejecutarse** y Claude recibe el motivo para autocorregirse.

> Solo aplica a **Claude Code** (los hooks de sesión no corren sobre tu disco
> en Cowork). En Cowork la mitigación equivalente es montar por proyecto solo
> `10-Projects/<proyecto>/` + `brain/`, no el vault completo.

## Hooks incluidos

| Hook | Evento | Qué garantiza |
|------|--------|---------------|
| `validate-graphiti-group-id.py` | PreToolUse sobre `mcp__graphiti*` | Ningún `add_episode` sin `group_id` válido; ninguna búsqueda sin `group_ids`. Bloquea `main`, vacío y placeholders |
| `mark-code-dirty.py` | PostToolUse sobre `Write\|Edit\|MultiEdit` | Marca flag cuando la sesión edita CÓDIGO **de este proyecto** — insumo del siguiente. No cuentan: los `.md`, ni nada fuera de `CLAUDE_PROJECT_DIR` (scratchpad, otras working dirs, otro repo). Esa segunda condición faltaba y provocaba falsos positivos en los 3 hooks anti-drift: un `commit-msg.txt` temporal sellaba el flag y el hook Stop exigía actualizar un vault que ya estaba al día |
| `check-vault-updated.py` | Stop | Anti-drift del vault: si hubo código editado y `_PROJECT.md` no se actualizó después, bloquea el cierre (exit 2) pidiendo SOLO pendientes/estado. **Una vez por sesión**, respeta `stop_hook_active`, silencio total en proyectos sin onboarding. Sale en silencio si `CLAUDE_TG_BOT=1` (sesiones del daemon de Telegram: no hay humano para cerrar el vault y bloquear colgaría la respuesta del bot — ADR puente-telegram §7). El cierre completo es de la skill `session-close` |
| `merge-gate-guard.py` | PreToolUse sobre `Bash` | **W3 del RFD 04.** Bloquea (exit 2) todo `git merge` cuyo **destino efectivo** sea `main`/`master` sin evidencia determinista de verde: un `.claude/gate-verde.json` cuyo `sha` sea el HEAD actual de la rama que se integra — la evidencia la escribe `scripts/gate-test.py` y solo con exit 0 de la suite. **Por qué existe**: en la prueba deliberada del 2026-08-07 el `workstream-merge-gate` salió 2/4 y la causa medida no fue que la skill fallara, sino que **no llegó a correr** (ganó `superpowers:finishing-a-development-branch`, sin confirmación humana ni squash) — se colaron 2 merges a `main` sin OK. Una convención escrita vuelve a fallar; un arnés, no. **Destino EFECTIVO, no rama actual**: los dos merges venían como `git checkout main && git merge x`, así que mirar el HEAD del momento dejaría pasar justo el caso que lo motivó. Fuera de las ramas protegidas no interviene, y no suplanta a la skill: no juzga la calidad del verde, ni el worktree, ni pide la confirmación (un hook no puede preguntar) |
| `goal-evidence-guard.py` | Stop | **Capa 1 del contrato de `/goal`.** El evaluador de `/goal` **no ejecuta herramientas**: juzga solo lo que apareció en la conversación, así que cierra metas leyendo el reporte, no el artefacto — la ley 1 rota por diseño, y corriendo sola. Este hook lee la meta forjada por `goal-forge` en `.claude/goal.json` y, si nombra un artefacto, comprueba contra el DISCO tres cosas, en orden: que **existe**, que **no declara rojo** si trae campo de veredicto (`exit_code`, `ok`, `fallos`…) y que es **fresco** (contrato sha↔HEAD del `merge-gate-guard`, movido de `PreToolUse` a `Stop`). Lo del veredicto es H1 de `auditoria/21`: con `gate-verde.json` existir ES el veredicto —solo se escribe en exit 0—, pero nada obligaba a esa semántica y un artefacto escrito también en rojo cerraba la meta con la suite rota. Lo que el fichero **no** declara, el hook no lo inventa. **La meta es de su sesión**: el guard sella `goal.json` con el `session_id` del primer turno que la ve y borra la de otra sesión, porque `/goal` muere con la sesión y el fichero no — H2 del mismo documento. **Fail-open** sin `goal.json` o con meta que no nombra artefacto: un guard que bloquea cierres legítimos se desactiva en dos semanas. **Cláusula de corte propia**: tras 3 bloqueos sale abierto diciendo que la condición está mal forjada — un bloqueo infinito es otro fallo, no una defensa. La capa 2 (`type: "agent"`, que sí lee disco) queda **nombrada, no construida**: es experimental por declaración de Anthropic |
| `memory-flush.py` | PreCompact (`manual` y `auto`) | Anti-drift en la compactación (R5 del `ecosistema/16`): con el mismo flag, si el vault sigue desfasado **pausa la compactación una vez** y pide volcar pendientes/decisiones antes de que el contexto se resuma. Sin flag → silencio. PreCompact **no admite `additionalContext`**: su único canal hacia Claude es exit 2, que en este evento significa "blocks compaction" — de ahí la pausa. Marca `precompact_flushed` para no repetirla (una auto-compactación bloqueada en bucle ahogaría la sesión) |

Requiere Python 3 en el PATH (`python3` en macOS/Linux, `python` en Windows).

## Hook de git (aparte — no es hook de Claude Code)

| Hook | Evento | Qué garantiza |
|------|--------|---------------|
| `git-post-commit-graph-report.sh` | git `post-commit` (por repo) | El `codebase-map-snapshot.md` del vault se regenera con Graphify en cada commit que toque código (commits solo de docs no disparan). **Escribe el snapshot, NUNCA el `codebase-map.md` curado** (RFD 10 C2). `session-close` no regenera: verifica que el hook esté instalado y la edad del snapshot |

Instalación por repo (solo donde corre Graphify):

```bash
cp setup/hooks/git-post-commit-graph-report.sh <repo>/.git/hooks/post-commit
chmod +x <repo>/.git/hooks/post-commit
```

Nota de migración: versiones previas copiaban `graph-report.md`; el nombre
canónico HUMANO es `codebase-map.md` — curado, lo escribe una persona; el
generado por el hook es `codebase-map-snapshot.md` (el snippet de memoria lee el curado y
`project-resume`). El hook borra el nombre viejo automáticamente.

## Instalación

### La forma fácil (Windows) — `sync-hooks.ps1`

```powershell
.\sync-hooks.ps1
```

Copia los `.py` a `~/.claude/hooks/` (y a cada `~/.claude-*/hooks/` en multi-cuenta)
y **cablea `settings.json` de forma idempotente** (con backup). Elige `py` como
intérprete automáticamente (en Windows `python` suele ser el stub del Store). El
bootstrap `setup-new-machine.ps1` ya lo invoca. Corre este script tras editar
cualquier hook — no hay sync automático como el de las skills.

### Manual (para entender el cableado, o en macOS/Linux)

1. Copia el script a tu config de Claude Code (y a tu repo de dotfiles):

   ```bash
   mkdir -p ~/.claude/hooks && cp validate-graphiti-group-id.py ~/.claude/hooks/
   ```

2. Fusiona esto en `~/.claude/settings.json` (ajusta `python3`→`python`/`py` en
   Windows y `~` a tu ruta absoluta si tu shell no la expande):

   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "mcp__graphiti",
           "hooks": [
             { "type": "command",
               "command": "python3 ~/.claude/hooks/validate-graphiti-group-id.py" }
           ]
         }
       ],
       "PostToolUse": [
         {
           "matcher": "Write|Edit|MultiEdit",
           "hooks": [
             { "type": "command",
               "command": "python3 ~/.claude/hooks/mark-code-dirty.py" }
           ]
         }
       ],
       "Stop": [
         {
           "hooks": [
             { "type": "command",
               "command": "python3 ~/.claude/hooks/check-vault-updated.py" }
           ]
         }
       ],
       "PreCompact": [
         {
           "hooks": [
             { "type": "command",
               "command": "python3 ~/.claude/hooks/memory-flush.py" }
           ]
         }
       ]
     }
   }
   ```

3. Verifica en una sesión nueva:
   - Graphiti: pide guardar un episodio **sin** group_id — debe bloquearse.
   - Anti-drift: en un proyecto enganchado, pide un cambio de código trivial y
     deja que termine — al final debe pedir actualizar pendientes (y callarse
     en cuanto cumplas; si lo ignoras, insiste 3 veces y abre).
   - Memory flush: en esa misma sesión (con el flag ya puesto), corre `/compact`
     — debe pausarse una vez con el recordatorio; el segundo `/compact` pasa. En
     una sesión que solo tocó `.md`, `/compact` no dice nada.

> Añade `.claude/vault-dirty.json` al `.gitignore` de tus proyectos (es estado
> de sesión local, no se versiona).

## Pruebas

Arneses de contrato en `tests/` (solo stdlib; usan proyecto temporal + vault
falso, nunca tocan el vault real). `sync-hooks.ps1` no los copia: solo instala
los `.py` de la raíz de `hooks/`.

```powershell
py setup\hooks\tests\test-mark-code-dirty.py       # 15 casos
py setup\hooks\tests\test-check-vault-updated.py   # 28 casos (el re-armado D2)
py setup\hooks\tests\test-memory-flush.py          # 11 casos
py setup\hooks\tests\test-merge-gate-guard.py      # 23 casos (repos git reales)
py setup\hooks\tests\test-goal-evidence-guard.py   # 28 casos (incluye el canario)
```

Córrelos ante **cualquier** cambio en el sistema anti-drift: los tres hooks
comparten el flag `.claude/vault-dirty.json`, así que un cambio en uno puede
romper a los otros dos. Ojo al probar a mano en PowerShell: canalizar el payload
JSON con `|` a `py` no siempre entrega bien stdin y el hook parece "no hacer
nada" (fail-open); usa los arneses o bash.

## Diseño

- **Fail-open** ante entrada ilegible: si el JSON del hook no parsea, no
  bloquea (un bug del hook no debe tumbar el resto de herramientas).
- **Fail-closed en `merge-gate-guard`** ante un merge a rama protegida que no se
  puede verificar (rama sin nombrar, evidencia ilegible): ahí la duda se
  resuelve parando — es el sentido de una compuerta. Fuera de `main`, ni se
  entera.
- **Fail-closed** ante group_id ausente/prohibido: exit 2 + mensaje accionable.
- El multi-cuenta hereda el hook si copias `hooks/` + settings a cada
  `CLAUDE_CONFIG_DIR` (el sync de dotfiles ya contempla `settings.json`).

## Dos hooks en `Stop`: cómo conviven (y la deuda que queda)

Desde el 2026-08-09 hay **dos**: `check-vault-updated.py` y
`goal-evidence-guard.py`. Los dos corren, en el orden del `$HookMap` de
`sync-hooks.ps1` (el cableado **apende**, así que el del vault va primero).
Miden cosas distintas y ninguno lee el estado del otro, así que no se estorban.
Medido en `tests/test-goal-evidence-guard.py` §E.

**Hubo un efecto real, medido y ya arreglado (D2·b, 2026-08-10).** Antes,
`check-vault-updated` respetaba `stop_hook_active` y solo exigía **una vez por
sesión**: si el guard bloqueaba primero, el turno siguiente llegaba con el flag
puesto y **el anti-drift se callaba el resto del bucle** — justo en el escenario
que más lo necesita, horas de trabajo autónomo sin humano mirando. Estaba medido
en el caso E.3, que hoy fija lo contrario.

Los dos hooks comparten ahora el mismo criterio, que es el que ya tenía el
guard: **no se respeta `stop_hook_active`** (la pregunta tiene respuesta distinta
en cada vuelta) y **cada uno se acota con su propia cláusula de corte de 3
bloqueos**. Ninguno lee el estado del otro.

### El disparador del anti-drift, en una tabla

| | Antes | Ahora |
|---|---|---|
| Primer aviso | primer Stop con código sin registrar | igual |
| Insistencia | ninguna: una vez y mudo | hasta **3 avisos**, luego sale abierto |
| Vuelve | nunca en esa sesión | cuando se acumulan **N ediciones** más sin registrar |
| N | — | `VAULT_DRIFT_EVERY`, default **10** |
| `stop_hook_active` | lo enmudecía | se ignora |

`VAULT_DRIFT_EVERY=0` es la escotilla al comportamiento viejo (una tanda y no
vuelve). Un valor inválido cae al default: un número mal escrito no puede
apagar el anti-drift en silencio. La cuenta la lleva `mark-code-dirty` en la
clave `edits` del flag, y **muere con el flag** en cuanto el vault se actualiza
— mide el tamaño de la deuda, no la duración de la sesión.

Contrato completo en `tests/test-check-vault-updated.py` (§B el re-armado, §C
la convivencia).

## `/loop`: lo que hay que saber antes de confiarle nada

Verificado contra `code.claude.com/docs`, no contra blogs. El artículo más
citado sobre `/goal` y `/loop` **se equivoca**: dice que se implementan como
`.claude/commands/goal.md`. Son **nativos** — `/goal` es un comando y `/loop`
una skill bundled.

**Lo que descalifica a `/loop` como guardia**, y son tres cosas a la vez:

- **Caduca a los 7 días**, sin excepción.
- **Muere con la sesión** (salvo que se mande a background).
- **Necesita la sesión abierta.** No es un cron.

Para trabajo durable, las opciones son **Routines** (nube, sin máquina
encendida, mínimo 1 hora, no ve ficheros locales) o **tareas de escritorio**
(máquina encendida, sin sesión abierta, sí ve ficheros locales, 1 minuto).

**Lo demás, útil:**

- **Sin intervalo, Claude elige el retardo** (1 min – 1 h) tras cada iteración,
  y dice cuál y por qué. En ese modo **puede terminar el bucle solo**, llamando
  a `ScheduleWakeup` con `stop: true`.
- **`loop.md` sustituye el prompt de mantenimiento**: `.claude/loop.md` (gana)
  o `~/.claude/loop.md`. **Se relee en cada iteración** → se afina en caliente,
  con el bucle corriendo. Tope **25.000 bytes**. El de este proyecto está en
  `.claude/loop.md` y va por ~3 KB.
- **Puede ejecutar skills como prompt** (`/loop 20m /vault-drift-audit`), pero
  solo las **auto-invocables**. Verificado: **ninguna de nuestras skills lleva
  `disable-model-invocation`**, así que todas valen.
- **Máximo 50 tareas por sesión.** `Esc` lo para.
  **`CLAUDE_CODE_DISABLE_CRON=1` lo apaga todo.**

**Dependencias de versión**, que conviene comprobar en `setup-new-machine`:
`/goal` pide **v2.1.139+**; el `stop: true` de `ScheduleWakeup`, **v2.1.202+**;
el filtro de skills auto-invocables en disparos programados, **v2.1.196+**.

## Graphify: cuatro cosas que conviene saber antes (RFD 10 C8)

La herramienta es **externa** — este sync no la gestiona, y está bien así. Pero
cuatro cosas se aprendieron usándola en campo y no están en su documentación:

1. **`graphify claude install` registra `PreToolUse` en `.claude/settings.json`**,
   además de la sección del `CLAUDE.md` que sí documenta. Esos hooks **inyectan
   una instrucción imperativa en cada búsqueda de cada sesión** del repo
   (*"MUST run graphify query before grepping"*). Con agentes en paralelo eso es
   desviarles el método a media tarea: con 7 worktrees vivos se quitaron y se
   dejó solo la sección del `CLAUDE.md`, que es inerte. **Con agentes en
   paralelo, instala SOLO la sección.**
2. **Tiene un disparador, no una franja horaria.** La instrucción es:

   > **Antes de tu primer `grep` de exploración en una sesión, corre
   > `graphify query`. Su salida es la LISTA DE CANDIDATOS, no la respuesta:
   > confírmala con `Read` y da por hecho que le faltan sitios.**

   Decir "úsalo pronto" no nombra un momento, y se incumplió **2 jornadas de 2**
   con la herramienta al día. `grep` sí es un momento reconocible.

   **La expectativa va calibrada con números, no con adjetivos**: sobre la
   pregunta más cara de la jornada devolvió **5 de 9 sitios en 1,7 s** (contra
   ~40 min a mano) pero **omitió los dos decisivos**, y **49 de 65 `loc=` eran
   `L1`** — señala el fichero, no la línea. Es una **primera pasada con
   omisiones garantizadas**. Y **no esperes respuestas semánticas**: *"¿quién
   NECESITA este dato y quién solo lo transporta?"* no lo contesta un grafo AST,
   porque un conteo de ocurrencias no mide dependencia.
3. **Su hook reconstruye en cada cambio de rama** — en una jornada se disparó
   unas seis veces, compitiendo por RAM con tres subagentes. **Cuenta en el
   presupuesto de máquina** del bloque 5 del despacho.

   **Y tiene coste de reputación, que es el que de verdad se paga.** En campo se
   reportó que *"los hooks de graphify tardaban mucho"* — y esa impresión se
   transfiere entera al comando de consulta, que es otra cosa y no cuesta lo
   mismo. Medido en una copia aislada de este repo (334 ficheros, 3,1 MB →
   2.475 nodos): el hook (`graphify update`) **5,6 s**, en cada commit que toque
   código; la consulta (`graphify query`) **0,5 s**, once veces menos. Este repo
   es de docs, así que en uno de código el hook cuesta **más**, no menos.
   **Lo lento no es lo que se evita**, pero la resistencia se acumula igual: al
   pedir que se invoque a mano, da el número de la consulta — si no lo das, el
   usuario descuenta el del hook.
4. **Son DOS hooks de git, no uno** — este README decía "su hook" en singular y
   por eso el coste se contaba a la mitad. Enumerados en un repo enganchado
   (`ls .git/hooks/`, AlphaDogs, 2026-08-13):

   | Hook | Bytes | Marcador | Cuándo dispara |
   |---|---:|---|---|
   | `post-checkout` | 8593 | `# graphify-checkout-hook-start` | cada cambio de rama |
   | `post-commit` | 9186 | `# graphify-hook-start` | cada commit |

   Los dos los pone `graphify hook install` (lo dicen ellos mismos, en su
   cabecera). Eso explica los **dos prefijos distintos** que el campo vio en un
   solo comando —`git checkout -b` + `git merge --squash` disparó
   `[graphify] Branch switched…` **y** `[graphify hook] launching background
   rebuild`—: dos reconstrucciones en paralelo, en un comando que ya tardó
   **4 m 54 s**, compitiendo por la RAM que el humano nombró como fricción nº 1.

   **Recomendación operativa: en una sesión con gates, quita el `post-checkout`.**
   No hace falta un flag; el fichero no está versionado y basta apartarlo:

   ```bash
   mv .git/hooks/post-checkout .git/hooks/post-checkout.off   # quitar
   mv .git/hooks/post-checkout.off .git/hooks/post-checkout   # devolver
   ```

   ⚠ **Lo que se pierde, dicho con precisión**: el mapa deja de regenerarse *al
   cambiar de rama*, así que tras un `checkout` queda **desfasado hasta el
   siguiente commit**, que es cuando `post-commit` lo rehace. En una jornada de
   frentes eso es exactamente lo que quieres —el mapa de una rama a medio
   construir no vale— y a cambio te ahorras una reconstrucción por cada salto.
   Si tu trabajo es *leer* código saltando de rama sin commitear, déjalo puesto.
