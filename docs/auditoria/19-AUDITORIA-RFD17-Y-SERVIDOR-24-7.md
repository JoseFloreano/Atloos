# Auditoría del RFD 17 + los conflictos del servidor 24/7

> **Fecha:** 2026-08-09 · **Autor:** Cowork (auditor externo, nube).
> **Alcance:** (A) auditoría externa de `skills/17-RFD-SEIS-FAMILIAS-DE-SKILLS.md`
> —borrador completo, sin implementar— y (B) los conflictos entre el servidor
> 24/7 (`ADR-20260801-os-servidor-24-7`, `telegram/01`), el bucle `/goal`+`/loop`
> del RFD 18 y las guardias del §4.5 del RFD 17, con soluciones.
> **Método:** medición propia sobre el disco en `cc2ac79`; el check que el RFD 17
> propone lo **implementé y corrí** antes de auditarlo; documentación oficial de
> Claude Code como fuente para lo que existe hoy.
> **Base:** `cc2ac79`. Nada de esto está implementado y no cosecho nada.

> **Actualización 2026-08-09, mismo día**: **HEAD es ahora `c3a21b1`**
> (`acdfa67` arregló el parser del W3, `9b6b664` añadió el arnés de copias
> desplegadas, `c3a21b1` cosechó los RFD 04, 10 y 12). **Re-medí la Parte A
> contra el HEAD nuevo: los cuatro hallazgos siguen en pie sin un solo cambio**
> — la tabla de A.2 da los mismos nueve números, `validate-migration-review`
> sigue colgando en las dos skills, y `test-skill-catalog.py` sigue sin existir
> (`setup/scripts/tests/` tiene cuatro arneses, ninguno es ése). Los puntos 1 y
> 2 del anexo quedan **cumplidos**.

---

# Parte A — Auditoría del RFD 17

## A.0 Veredicto

**APROBABLE en su arquitectura, con cuatro hallazgos importantes que hay que
cerrar antes de F0.** El diagnóstico del §1 —*se construyó lo que cabía en la
sesión y el resto se pudrió*— es correcto y está medido (5 de 17). R1 (la
familia como unidad de entrega), R3 (caducidad a 60 días) y R4 (el eslabón de
arriba se entrega solo) son buen diseño y no tengo objeciones.

Lo que no se sostiene es **R2**, que es justo la pieza que el RFD declara
bloqueante. Y no por la idea —el arnés hace falta— sino por la especificación:
la corrí y **falla en las dos direcciones a la vez**.

Además, la parte medida del §4.4 **caducó el mismo día en que se escribió**.

## A.1 Lo que verifiqué y se sostiene

| Afirmación del RFD | Mi comprobación | |
|---|---|---|
| 5 de 17 piezas del catálogo `bd-y-nube` construidas | Consistente con el repo: las 5 de S0 existen, ninguna de S1/S2/S3 | [R] |
| `sql-conventions:11` cita `warehouse-query-optimize` **con hedge** | Cierto: *"…usa `warehouse-query-optimize` **si está instalada**"* | [R] |
| Ninguna de las 5 de bases de datos admite una frase más | Cierto: 468–499 sobre 500, y **tres sin `references/`** | [R] |
| La saturación correlaciona con madurez, no con la familia 4 | Cierto y más fuerte de lo que dice — ver A.2 | [R] |
| Superpowers no toca ninguna de las seis familias | No verificado desde aquí (no tengo su carpeta montada) | [AR] |
| 31 skills instaladas en la laptop | No verificable por el bridge (solo monta el repo y el vault) | — |
| CUJBench 19,7% · OpenRCA 3,9–12,5% · self-healing IaC 96,8% | Citados con fuente, **no replicados por mí** | [AR] |

## A.2 · H1 — IMPORTANTE: la tabla de saturación ya estaba desfasada al publicarse

El §4.4 mide ocho skills «≥475 palabras» y concluye «8 de 33 — el 24% del
catálogo». Recontado hoy con el mismo método (cuerpo sin frontmatter, CR
quitados), sobre `cc2ac79`:

| Skill | RFD 17 (08-08) | **Hoy** | Δ | `references/` |
|---|---:|---:|---:|:---:|
| `pipeline-designer` | 499 | 499 | — | 1 |
| `vault-drift-audit` | **500** | **499** | −1 | 1 |
| `workstream-merge-gate` | **484** | **497** | **+13** | **0** |
| `data-quality-gates` | 497 | 497 | — | **0** |
| `design-doc-harvest` | 495 | 495 | — | 1 |
| **`claude-code/project-resume`** | **ausente** | **494** | **nueva** | **0** |
| `session-close` | **488** | **491** | +3 | 2 |
| `migration-auditor` | 488 | 488 | — | 1 |
| `schema-designer` | 475 | 475 | — | **0** |

**Son 9 de 34, no 8 de 33.** Y las tres celdas que se movieron se movieron por
la implementación del RFD 11 y del trigger del gate, **del mismo 08-08**:
`762be75` engordó `workstream-merge-gate` 13 palabras y `543aa5f` metió a
`claude-code/project-resume` en la lista por primera vez.

No es un error de cálculo: es que **la tabla no dice contra qué commit se midió**,
así que envejece sin avisar. Es la ley 2 de la casa —*el brief no conoce el
presente*— aplicada al propio RFD.

Y la dirección importa: **la saturación es peor, no mejor**, de lo que el
documento afirma. Refuerza su tesis y a la vez invalida sus cifras.

**Fix mínimo:** que la tabla lleve `medido en <sha> · <fecha>`, igual que
`Estado del repo:` en `_PROJECT.md`. Y que la genere el arnés, no una persona —
una tabla de números a mano vuelve a caducar el martes siguiente.

## A.3 · H2 — IMPORTANTE: el check 1 de R2 no funciona, y es el bloqueante

R2 especifica: *"toda skill nombrada dentro de un `SKILL.md` debe existir en
`setup/skills/`; si no existe, es hallazgo, salvo que venga marcada como
opcional"*. El criterio de aceptación 1 lo declara **bloqueante**.

**Lo implementé tal cual y lo corrí sobre las 32 skills.** Resultado:

```
Dispararían como HALLAZGO (sin hedge): 26
```

De esos 26, la inmensa mayoría **no son referencias colgantes**:

| Lo que caza | Ejemplos | ¿Es una skill que falta? |
|---|---|---|
| Skills de **Superpowers** | `systematic-debugging` (6×), `subagent-driven-development`, `condition-based-waiting`, `writing-skills`, `sdd-workspace`, `task-brief` | No — existen, en otro namespace |
| Skills **bundled** de Anthropic | `skill-creator` (2×) | No — existe; **la tengo delante ahora mismo** [R] |
| **Scripts** del propio repo | `sync-skills` (6×) | No — es un `.ps1` |
| **Hooks** del propio repo | `merge-gate-guard` (2×) | No — es un `.py` |
| Un **MCP** | `graphiti-memory` (5×, 4 con hedge) | No |
| Una **cita bibliográfica** | `api-design-principles` (de wshobson) | No — es trabajo ajeno citado |
| Un **literal de JWT** | `alg:none` | No, evidentemente |

Y en la otra dirección: **no caza el caso que motivó el arnés.** La referencia
de `skill-forge` a `cowork-plugin` está escrita **sin backticks**, en prosa
corrida. Una implementación que busque nombres marcados la deja pasar; una que
busque texto plano se llena de basura. **El check falla en las dos direcciones a
la vez, y es el que bloquea la entrega de cada familia.**

**Fix mínimo, y es barato:** el nombre por sí solo no es identificador. Hace
falta **namespace explícito** en el cuerpo de las skills:

- `superpowers:systematic-debugging` — ya se usa así en `workstream-merge-gate:12`,
  así que la convención existe y solo hay que generalizarla.
- `bundled:skill-creator` / `cowork:cowork-plugin` para lo que trae la
  plataforma.
- Sin prefijo = skill propia, y **esa** sí tiene que existir en `setup/skills/`.

Con eso el check pasa de heurística a comprobación exacta, y de paso obliga a
que las skills digan de dónde sale cada cosa que mandan usar — que es
información útil por sí sola.

## A.4 · H3 — IMPORTANTE: `cowork-plugin` sí existe

El §1 afirma que `cowork-plugin` *"no existe en el repo, ni en `~/.claude/skills/`,
ni en el marketplace instalado"* y lo usa como el ejemplo urgente.

**Existe como skill bundled de Cowork.** Evidencia de primera mano: está en la
lista de skills disponibles de esta misma sesión, con su descripción —*"Create a
new Cowork plugin from scratch, or customize an installed plugin…"*—. [R]

O sea: la instrucción de `skill-forge` —*"Para plugins completos de Cowork usa
`cowork-plugin`"*— **resuelve exactamente en la superficie donde manda usarla**
(Cowork) y cuelga solo en Claude Code CLI, donde nadie construye plugins de
Cowork de todos modos.

No es una nimiedad de catálogo. Cambia el fix:

- El RFD trata el caso como *referencia inalcanzable* y el remedio implícito es
  borrarla o hedgearla.
- Lo correcto es **marcar la superficie**: *"en Cowork, usa `cowork:cowork-plugin`"*.
  Borrarla perdería una instrucción **correcta**.

Y sube el listón de R2: el arnés no puede ser *"existe o no existe"*, tiene que
ser *"existe **en la superficie donde se manda usar**"*. `setup/skills/` ya está
partido en `shared/`, `claude-code/` y `cowork/`, así que la información
necesaria ya está en el árbol.

**Mea culpa preventiva:** que yo tenga esa skill delante no prueba que la tenga
todo Cowork —depende de la organización y de los plugins instalados—. Lo que sí
queda refutado es la afirmación categórica de que no existe en ningún sitio.

## A.5 · H4 — IMPORTANTE: hay dos referencias colgantes más, y son peores

El §1 lista dos. Hay al menos **una tercera, citada dos veces**, y de una clase
más grave:

```
setup/skills/shared/migration-auditor/SKILL.md:61
   "…la garantía dura es el hook `validate-migration-review` (Fase S2)"
setup/skills/shared/sql-conventions/SKILL.md:76
   "…instrucción, no garantía: el hook `validate-migration-review` (Fase S2)"
```

`validate-migration-review` es uno de los cuatro hooks de S2 que **nunca se
construyeron**, y que el §4.4 manda **borrar del catálogo**. Verificado: no hay
tal fichero en `setup/hooks/`. [R]

Por qué es peor que las otras dos: no dice *"usa X"*, dice **"la garantía dura
es X"**. Una skill afirmando que existe una garantía de máquina que no existe es
peor que una que manda a una skill ausente — y es, palabra por palabra, la
enfermedad que este proyecto nombró el 08-07 con `notify-telegram`.

Y el conflicto directo con el propio RFD: **la poda del §4.4 borraría los 4
hooks de S2 del catálogo dejando estas dos citas vivas dentro de skills
maduras.** Sería repetir el mecanismo exacto que produjo el problema del §1:
quitar del catálogo sin redirigir lo que entra.

**Fix mínimo:** la poda no es `borrar del catálogo`; es
`borrar + grep de referencias entrantes + redirigir o hedgear + grep final = 0`.
Que es, literalmente, el ritual de cosecha que ya tienen escrito para los RFD.
Aplicar el mismo a las skills.

## A.6 · Hallazgos menores

**M1 — "los cuatro hooks de Claude Code son todos de sesión".** La lista del
§4.5 es la de los cuatro que *Atloos usa*, presentada como el conjunto que
*existe*. Hay más eventos (`SessionStart`, `UserPromptSubmit`, `SubagentStop`,
`PostToolBatch`, `Notification`…). Y la conclusión que cuelga de esa premisa
—*"lo único 24/7 que este setup tiene es el daemon y el plan del mini-PC"*— **ya
no es cierta**: hoy existen Routines de nube y tareas programadas de escritorio.
Es el eje de la Parte B.

**M2 — el conteo.** Son **34** `SKILL.md` bajo `setup/skills/` (21 `shared` + 10
`claude-code` + 2 `cowork` + 1 `_template`), o **32** skills reales sin plantilla
ni contar la plantilla como catálogo. El RFD dice 33. Diferencia menor, pero el
denominador del "24%" sale de ahí.

**M3 — `workstream-merge-gate` está en 497 con cero `references/`.** El criterio
4 del §8 dice que *toda skill que se edite sale ≤450 y con `references/`*. El
trabajo del bucle (RFD 18) va a tocar esa skill. **Son ~50 palabras a extraer y
una carpeta que crear antes de poder añadir una sola línea.** Presupuestarlo, no
descubrirlo a medio camino — que es la propia advertencia del §4.4 aplicada a
sí misma.

## A.7 · Lo que NO pude verificar

- Las **44 skills de Superpowers** y su no-solape con las seis familias: no
  tengo esa carpeta montada.
- Las **31 instaladas** en la laptop: el bridge solo monta el repo y el vault.
- Los **números de CUJBench, OpenRCA y self-healing IaC**: están citados con
  enlace, no los repliqué. Son [AR] y el RFD los usa para decidir el alcance de
  N2, así que conviene que alguien los mire antes de construir la guardia.
- **Si D2 se resolvió bien**: la revisión del §4.5 tras la respuesta del usuario
  me parece el mejor razonamiento del documento —*la autonomía es segura donde
  existe un estado correcto declarado*—, pero es un juicio, no una verificación.

---

# Parte B — El servidor 24/7: conflictos y soluciones

## B.0 El resumen

El ADR de la mini PC sigue en **`proposed`** y se escribió el 01-08, cuando
*"lo único 24/7"* era el daemon. Desde entonces han aparecido dos capas nuevas
—Routines de nube y tareas programadas de escritorio— y un motor nuevo
—`/goal` y `/loop`—. **Ninguna de las tres invalida la mini PC, pero las tres
cambian qué debería correr en ella.**

Diez conflictos. Ocho tienen solución barata; dos son decisiones.

## C1 · N0 necesita fierro; N1 y N2, no

Los tres niveles de guardia del §4.5 no tienen el mismo requisito de hardware, y
el RFD los trata como un bloque que vive en la mini PC:

| Nivel | Qué necesita | ¿Lo puede hacer la nube? |
|---|---|---|
| **N0** · el proceso se cayó, no responde | `systemd` en la máquina donde corre el proceso | **No.** No se reinicia un daemon desde la nube |
| **N1** · diff contra estado declarado | leer el estado declarado y compararlo | **Sí, si el estado vive en git** |
| **N2** · diagnóstico abierto | contexto y herramientas | **Sí** (y su salida es un reporte, no una acción) |

**Solución:** repartir. N0 se queda en la máquina y **no lleva IA** (es un
fichero de unidad). N1 puede correr en los dos sitios, y **debe correr en los
dos**, por C2. N2 va donde haya contexto, que hoy es la laptop o la nube.

Consecuencia para la compra: **la mini PC ya no se justifica por la guardia**
—N1 y N2 no la necesitan— sino por lo que de verdad solo se puede hacer con
fierro propio: el daemon de Telegram con latencia de segundos, los tests y
builds locales, y el minuto de granularidad.

## C2 · ¿Quién vigila al vigilante?

El §4.5 lo dice bien: *"un cron que deja de correr es la ausencia de algo bueno:
no hay error que capturar"*, y pide un **latido**. Pero un latido que emite y
comprueba la misma máquina no prueba nada — es la primera ley de la casa al
nivel de sistema: **el auto-reporte no es evidencia**.

Si la guardia vive en la mini PC y la mini PC se cae, no hay quien avise.

**Solución — vigilancia cruzada, y el latido es un commit:**

1. La mini PC empuja un latido a un remoto que la nube sí ve. **El vault ya
   tiene remoto propio en GitHub** (`ADR-20260726-vault-git-fuera-de-onedrive`),
   así que el medio existe: un fichero `latido.json` con `ts` y `sha`, commiteado
   por el daemon.
2. Una **Routine de nube** corre cada hora, clona, mira la edad del latido y
   avisa si pasó el umbral. No necesita ver la mini PC ni red privada.
3. La mini PC, a su vez, comprueba lo que la nube no puede: procesos, memoria,
   disco.

Ninguna de las dos se avala a sí misma, y ninguna necesita alcanzar a la otra
por red — se hablan por el repo. Es barato y usa lo que ya está montado.

## C3 · Sesiones largas contra la estrategia anti-fugas

**Conflicto directo, y es el que más me llamó la atención.**

`telegram/01` dice que la estabilidad de un daemon 24/7 la dan **sesiones cortas
con `--resume`**, `MemoryMax=` y margen de RAM, porque los memory leaks de
Claude Code son la falla #1 documentada del patrón (sesiones a 10+ GB).

`/goal` y `/loop` son exactamente lo contrario: mecanismos para **alargar** la
sesión, turno tras turno, durante horas.

Poner el bucle en la mini PC sin más es maximizar la exposición al fallo #1.

**Solución, y sale gratis:** `/goal` **sobrevive al reinicio**. La documentación
es explícita: *"una meta que seguía activa cuando la sesión terminó se restaura
al reanudar con `--resume` o `--continue`"* — la condición viaja; el contador de
turnos, el cronómetro y el gasto se reinician.

Eso convierte el conflicto en un diseño:

> **`MemoryMax=` mata, systemd reanuda con `--resume`, y la condición de la meta
> es el contrato de recuperación.**

La unidad de trabajo deja de ser la sesión (frágil, con fuga) y pasa a ser la
**meta** (durable, verificable). El leak se vuelve un incidente de N0 en vez de
una pérdida de trabajo. Es la mejor razón que he visto para adoptar `/goal` en
un servidor, y no aparece en ningún blog.

⚠ Con un requisito: el reinicio **reinicia el contador de turnos**, así que la
cláusula de corte (`o para a los 20 turnos`) **deja de acotar** tras un kill. Un
bucle con fugas podría reiniciarse indefinidamente. Hace falta un tope externo:
`StartLimitBurst` de systemd, que ya está en el ADR, y un contador persistido
fuera de la sesión.

## C4 · `/loop` no sirve como guardia

Por si alguien lo alcanza: `/loop` **caduca a los 7 días**, **muere con la
sesión** y **necesita la sesión abierta**. Es para vigilar algo durante una
jornada, no para una guardia.

**Solución:** en el servidor, lo recurrente lo dispara `systemd` (timers) o una
tarea de escritorio; `/loop` se queda en la laptop, para trabajo asistido.

## C5 · El anti-drift del vault está apagado justo donde nadie mira

`check-vault-updated.py` **sale en silencio si `CLAUDE_TG_BOT=1`** — decisión
correcta y documentada (§7 del ADR del puente: no hay humano para cerrar el
vault y bloquear colgaría la respuesta del bot).

Pero la consecuencia, sumada al hallazgo D2 del RFD 18 (dispara una vez por
sesión), es que **en el servidor el anti-drift no dispara nunca**. Y el servidor
es, por definición, donde nadie está leyendo.

Hay un control compensatorio y hay que decirlo: **el daemon escribe la nota de
sesión** (`vaultio.write_session_note`, `ADR-20260801-bot-memoria-y-perfil`), y
lo hace el código, no el LLM. Pero **solo en `/done`**. Trabajo iniciado por un
timer o una Routine, sin `/done`, no deja rastro en el vault.

**Solución:** el registro en el servidor no puede depender de un hook de sesión
ni de un comando del usuario. Que lo escriba el **mismo mecanismo que dispara el
trabajo**: si el trabajo lo lanza una unidad de systemd, esa unidad escribe el
apunte al terminar, con el exit code y el sha. Determinista, sin LLM, y encaja
con la doctrina ya establecida de que el vault lo toca el daemon.

## C6 · `/goal` desnudo en un servidor es peor que en la laptop

El hallazgo central del RFD 18: el evaluador de `/goal` **no ejecuta
herramientas**, así que cierra metas leyendo lo que Claude dijo.

En la laptop hay un humano que puede oler el reporte falso. **En un servidor
24/7 no lo lee nadie.** Con auto mode, un bucle puede cerrar una meta sobre una
afirmación y seguir a la siguiente durante toda la noche.

**Solución:** `goal-evidence-guard` (P2 del RFD 18) pasa de *recomendable* a
**precondición de instalar el bucle en el servidor**. Y en el servidor debe ser
la capa `command` determinista, no la `agent` experimental.

## C7 · Gasto sin techo

La sesión interactiva tiene dos frenos accidentales: `/loop` caduca a los 7 días
y las Routines tienen tope diario de runs. **Un bucle lanzado por systemd en una
máquina que nunca se apaga no tiene ninguno de los dos.**

El criterio 4 del RFD 18 pide medir el coste del bucle contra el trabajo a mano.
Antes de eso, en el servidor hace falta un **techo**, no una medición:
presupuesto por ventana, y el bucle se detiene al alcanzarlo. Es la salvaguarda
2 del propio §4.5 (*enfriamiento y tope de acciones*) aplicada a tokens en vez de
a acciones — el RFD ya tiene el principio escrito, solo no lo aplicó al gasto.

## C8 · La nube no alcanza la mini PC

Las Routines corren en infraestructura de Anthropic con clon fresco del repo: no
ven ficheros locales y no entran a tu red. Tailscale no cambia eso.

**Solución:** ya está en C2 — el medio compartido es git. Todo lo que la nube
deba saber de la máquina tiene que estar commiteado. Y su corolario: **lo que no
esté en git es invisible para la capa de nube**, así que decidir qué se
commitea es decidir qué se puede vigilar desde fuera.

## C9 · Permisos: auto mode sin humano

El §4.5 acierta en que el mínimo privilegio es el control de mayor palanca.
Sumando: `/goal` **no cambia permisos** por sí solo y para correr desatendido
pide auto mode; las Routines corren **sin prompts de permiso** por diseño.

**Solución:** reusar lo que ya existe en vez de inventar — el perfil recortado
del bot (15 de 34 skills) y el **deny de secretos por ruta absoluta** (con la
trampa ya documentada: *los globs no funcionan*). El servidor necesita su propio
perfil, más estrecho que el de la laptop, y **probado con canario**, no leyendo
flags.

## C10 · N1 y `goal-evidence-guard` son la misma primitiva

Vale la pena verlo antes de construir dos veces:

| | Qué declara | Qué compara | Qué hace si difiere |
|---|---|---|---|
| Guard del `sync-skills` | manifest de skills | conjuntos de nombres | grita |
| `merge-gate-guard` (W3) | `gate-verde.json` con sha | sha ↔ HEAD | bloquea |
| `goal-evidence-guard` (RFD 18) | artefacto nombrado en la condición | existe y es fresco | no deja cerrar |
| **Guardia N1** (RFD 17) | hooks, `.env`, skills, latido | estado declarado ↔ disco | restaura |

Es **una sola primitiva** —*declarar, diferir, actuar*— en cuatro escalas.
Merece un módulo compartido y un solo arnés, no cuatro implementaciones que
divergen. Es, además, el mejor argumento de que la arquitectura del setup es
coherente: llegó a la misma forma cuatro veces por caminos distintos.

## B.1 · La arquitectura que sale de los diez conflictos

Tres anillos, cada uno con lo que solo él puede hacer:

| Anillo | Dónde | Qué le toca | Por qué solo él |
|---|---|---|---|
| **Reflejos** | mini PC · `systemd` | reiniciar, watchdog, tope de reintentos, timers | Nada remoto reinicia un proceso local |
| **Contrato** | mini PC **y** nube | N1: diff contra estado declarado; latido cruzado | Debe estar en los dos o nadie vigila al vigilante |
| **Juicio** | laptop o nube | N2, diseño, `/goal` con humano cerca | Es donde los números dicen que la máquina falla |

Y la regla que los une, que es la misma del RFD 18 en otra escala:

> **Cuanto menos humano hay mirando, más determinista tiene que ser la
> comprobación.** En la laptop puedes permitirte un evaluador que lea el
> transcript. En el servidor, no.

## B.2 · Entonces, ¿se compra la mini PC?

El ADR está en `proposed` y `vault-drift-audit` ya lo declararía **en el limbo**
(ADR `proposed` con más de 14 días — y lleva ocho días de sobra). Así que la
decisión toca de todas formas.

Lo que **sigue justificando el fierro**, después de restar lo que la nube cubre:

- El **daemon de Telegram**: es la razón original, es tuyo por decisión, y la
  nube no lo cubre (Routines no hacen mensajería con latencia de segundos).
- **N0**, que no se puede delegar.
- **Tests y builds locales** de los frentes paralelos: son CPU real, y las
  Routines clonan pero no son tu entorno.
- **Granularidad de un minuto**; las Routines tienen mínimo de una hora.
- **Acceso al vault local** sin pasar por GitHub.

Lo que **ya no lo justifica**, y estaba en el motivo original:

- Ser *"lo único 24/7"*. Ya no lo es.
- La guardia entera: dos de sus tres niveles no la necesitan.
- Correr Graphiti en Docker: **está pospuesto por ADR** desde el 08-08, y era
  parte del dimensionamiento de RAM del `telegram/01`.

Ese último punto cambia los números de la compra: el presupuesto de RAM del
`telegram/01` incluye *"Docker + FalkorDB/Redis + Postgres idle"* en el renglón
de 1,5-2 GB. Con Graphiti pospuesto, **ese renglón se encoge**, y el pico
realista baja del rango 11-18 GB declarado. **32 GB sigue siendo la
recomendación sensata por los leaks**, pero la opción de 16 GB deja de ser
descartable de plano, y eso mueve el precio de forma no trivial.

## B.3 · Decisiones abiertas

### D5 · ¿Cuándo se compra la mini PC?

| | Opción | A favor | En contra |
|---|---|---|---|
| **(a)** ⭐ | **Aplazar hasta después del bucle**, y montar mientras tanto el anillo *contrato* con una Routine + una tarea de escritorio | Cero gasto; prueba el diseño de C2 con la laptop haciendo de "servidor"; el ADR se re-justifica con uso medido | El daemon sigue dependiendo de que la Legion esté encendida |
| **(b)** | Comprar ya, según `telegram/01` | Desbloquea T4/T5 y el 24/7 real | Se compra dimensionado para un Docker que está pospuesto |
| **(c)** | No comprar: todo a la nube | Sin fierro que mantener | Pierde N0, el minuto de granularidad y el daemon; **no es viable** |

**Mi voto: (a).** No por ahorrar: porque el latido cruzado de C2 **se puede
probar sin mini PC** —la laptop emite, la Routine vigila— y esa prueba es la que
dice si el diseño de guardia sirve. Comprar antes de esa prueba es comprar para
un diseño no verificado. Y el ADR pasaría de `proposed` a `accepted` con un
motivo medido, que es lo que hoy le falta.

### D6 · ¿Qué namespace usan las referencias entre skills? (de H2/H3)

| | Opción |
|---|---|
| **(a)** ⭐ | Prefijo obligatorio: `superpowers:`, `bundled:`, `cowork:`; sin prefijo = propia y debe existir |
| **(b)** | Lista blanca de nombres externos en un fichero del arnés |
| **(c)** | Solo hedge textual (*"si está instalada"*), como hoy |

**Mi voto: (a).** (b) es un segundo catálogo que se desincroniza —el problema
del §1 otra vez—, y (c) es lo que ya falló. (a) además hace el arnés exacto en
lugar de heurístico, y la convención ya existe en `workstream-merge-gate:12`.

### D7 · ¿F0 antes o después del bucle?

El usuario dijo que las familias van **después** del bucle. Pero **F0 no es una
familia**: es higiene del catálogo, media jornada, y el bucle **añade skills
nuevas** (`goal-forge`) al mismo catálogo que hoy no distingue lo construido de
lo propuesto.

| | Opción |
|---|---|
| **(a)** ⭐ | **F0 antes del bucle.** Media jornada; `goal-forge` nace vigilada |
| **(b)** | Bucle primero, F0 después, y `goal-forge` se audita retroactivamente |

**Mi voto: (a)**, con una condición: F0 no arranca hasta cerrar H2 y H3, porque
su punto 2 es construir el arnés — y construirlo con la especificación actual es
construir un bloqueante que da 26 falsos positivos.

---

## Anexo · Orden consolidado

Uniendo este documento con el RFD 18 y lo que quedó abierto del 08-09:

1. ~~**Cerrar el parser del W3**~~ ✅ **HECHO** (`acdfa67`): mis 8 sondas dan
   **10/10** y el arnés pasa de 11 a **23 casos**. Re-verificado por mí.
2. ~~**Cosechar 10 y 12**, y el 04~~ ✅ **HECHO** (`c3a21b1`): los tres a ADR y
   borrados del repo.
3. **Seguridad**: revocar el token de altari.ai, commitear `docs/tmp/`.
4. **Arbitrar D1–D7.**
5. **F0 corregido** (H2 + H3 + H4 antes de escribir el arnés).
6. **El bucle**: `goal-forge`, `goal-evidence-guard`, `loop.md`.
7. **El anillo *contrato* sin fierro**: latido cruzado laptop ↔ Routine. Es la
   prueba de D5.
8. **Decisión de compra** con la prueba del 7 en la mano.
9. **Una familia**, la que diga D1 del RFD 17.

## Sesgo declarado

Vengo de encontrar ocho fallos en el parser del W3 esta misma jornada, y de
proponer otra compuerta en el RFD 18. Es previsible que vea compuertas por todos
lados; el lector debería atacar sobre todo C6 y C10 —¿de verdad hacen falta
cuatro guards, o uno bien puesto?— y B.2, donde estoy recomendando **no** gastar
y eso también es una postura cómoda para quien no paga.
