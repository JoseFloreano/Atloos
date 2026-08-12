---
title: Auditoría externa del sprint 2 — fase 0, canal del disparador, gate del push y familia 1
tags: [auditoria, sprint2, merge-gate, graphify, feedback, ml]
created: 2026-08-12
updated: 2026-08-12
status: done
type: auditoria
project: atloos
rama_auditada: sprint2/fase0-canal-gate-familia1
commit: 3f698770310038da60607bd8e93edaa04da9dcb3
base: 9d2827b381787441f8c3878ffe803e75ecc4ba1e
agente: Cowork (auditor externo, nube)
---

# Auditoría 22 — el sprint 2

**Veredicto: NO integrar todavía.** Tres bloqueantes, los tres baratos, y uno de
ellos convierte el gate en su propio obstáculo. El trabajo de fondo es bueno —
mejor que el del sprint 1— y esto no lo cambia: son tres arreglos de pocas
líneas, no un rediseño.

## Cómo se verificó

Clon fresco de la rama en un laboratorio aparte (`/tmp/audit-s2`, HEAD
`3f69877`, árbol limpio), más un `git worktree` para el caso decisivo y un
segundo worktree en `9d2827b` para separar lo heredado de lo nuevo. Todas las
suites corridas por mí. Tres mutaciones al código del guard y una al arnés.
Sonda propia de 33 casos contra el guard del push. El repo real quedó intacto:
misma rama, mismo sha, sin `.lock`.

> **Dos veces estuve a punto de firmar un exit code falso.** `python x.py | tail`
> y luego `echo $?` devuelve el estado de `tail`, no el de Python — la misma
> trampa que ya me mordió con `head` en la auditoría del RFD 11. La primera vez
> me habría hecho declarar verde un arnés que está rojo. Se declara.

**Lo que el árbol de trabajo del repo real dice y no es**: `git status` marca 117
ficheros modificados. `git diff --ignore-cr-at-eol` sale **vacío**: son finales
de línea, no contenido. El «árbol limpio» del reporte es cierto en sustancia.

---

## Bloqueantes

### B1 · El arnés nuevo de deriva se pone ROJO en cualquier worktree y en cualquier clon — y el gate corre en un worktree

`test-claude-md-drift.py` ahora lee sus objetivos de
`setup/telegram-bridge/projects.json`. Ese fichero está en `.gitignore`
(línea 26). `CLAUDE.md` también (línea 15, y por buen motivo: es artefacto de
instancia).

Un `git worktree` nuevo no tiene ninguno de los dos. Medido:

```
$ git worktree add /tmp/wt-audit HEAD
$ python3 setup/scripts/tests/test-claude-md-drift.py
  [AUTOPRUEBA] OK — la línea vieja de Graphify produce hallazgo
  [DERIVA] no existe projects.json: no hay lista de CLAUDE.md vivos que auditar
  [DERIVA] no existe: /tmp/wt-audit/CLAUDE.md
EXIT EN WORKTREE = 1
```

Idéntico en un clon fresco. Y `gate-test.py` corre la suite en
`git rev-parse --show-toplevel`, que **dentro de un worktree es el worktree**.
El paso 2 de `workstream-merge-gate` manda producir la evidencia con ese helper,
y solo con exit 0 se escribe `gate-verde.json`.

> **Consecuencia:** integrada tal cual, esta rama impide producir un verde en el
> entorno donde el gate lo produce. La compuerta se cierra sobre sí misma.

Y es la categoría exacta que el reporte de campo del 08-11 ya había nombrado
—*«el worktree de integración falla por motivos que no son el código»*— y que yo
mismo enruté a pendientes. El sprint añadió un caso nuevo de ella.

Por qué el reporte no lo vio: **el checkout principal sí tiene los dos ficheros**
(están en disco, solo que sin versionar). El 14/14 se midió ahí. Es la ley del
laboratorio: el estado del laboratorio también es estado.

**Fix (pocas líneas):** la ausencia de `projects.json` y la de `CLAUDE.md` son
**condiciones de entorno, no deriva**. Deben salir como `[SKIP]` con su motivo
—igual que ya se hace con los proyectos declarados que no están en esta máquina—
y no como hallazgo. La deriva es que la copia desplegada **exista** y vaya
atrasada. Con su caso de arnés, que hoy no existe: correr el arnés en un
worktree y exigir exit 0.

### B2 · `git push origin HEAD` se escapa — probado hasta el final

Sonda de 33 casos. **31 bloquean bien. Dos no.** El primero no es una
ofuscación: es el idioma de todos los días.

Y no me quedé en el exit code. Repo real, `main`, un commit sin publicar, sin
evidencia:

```
origin/main ANTES  : 935b6b1df439
$ git push origin HEAD          ← el hook devuelve 0, no interviene
origin/main DESPUÉS: b5f0a59e6f70
mensaje que aterrizó: "NUEVO SIN GATEAR"
```

**El commit sin gatear aterrizó en `origin/main`.** Es el incidente del 08-11
otra vez, con otro tecleo.

La causa está a la vista en `destinos_de_push()`: el destino se resuelve como el
literal del refspec, y `HEAD` no está en `PROTEGIDAS`. Lo mismo con `@` y con
`head`. El arnés prueba `push origin HEAD:main` (caso 32) — pensaron en `HEAD`
**con dos puntos** y no en `HEAD` a secas.

**Fix:** resolver `HEAD`, `@` y `head` a la rama actual antes de comparar. La
función ya recibe `rama_actual`; es la misma línea que ya resuelve el push sin
refspec.

### B3 · La plantilla de feedback trae la sección 9 rellena, y pasa el check que S5 construyó

El check de la sección 9 es correcto: bloquea `pendiente`, `TODO`, `<algo>` y
menos de 60 caracteres útiles. Pero `_PLANTILLA.md` la entrega así:

```
- [H] Leído y corregido por: alias-real · 2026-08-11
- [H] Cambios que pedí sobre el borrador del agente: describe cuáles, o escribe
  que no pediste ninguno y por qué te parece fiel.
```

Nombre plausible, fecha real, longitud suficiente. **Pasa.** Copié la plantilla,
edité solo `tarea` y la sección 4, no toqué la 9:

```
[OK   ] 2026-08-12-tester-perezoso.md
1 reporte(s) · 0 fallo(s)     EXIT REAL = 0
```

Es el mismo agujero que S5 vino a cerrar, **y ahora es peor**: antes un reporte
sin confirmar decía `<pendiente>` y se veía; ahora afirma una confirmación
humana con nombre y fecha que nadie escribió.

**Fix (una línea):** `- [H] Leído y corregido por: <alias> · <AAAA-MM-DD>`. El
patrón `<[^>\n]{1,40}>` que ya está escrito lo caza solo.

---

## Hallazgos no bloqueantes

### H4 · `test-goal-evidence-guard.py` está ROJO en `main`, y no es transitorio

La mea culpa 5 dice que el rojo *«lo era [transitorio] — da 0 en solitario»*. No
lo da. En clon limpio, dos veces seguidas, **exit 1 · 26/28**, y lo mismo en
`9d2827b` — es decir, **en `main`, pushado desde el 11 a las 08:16**. La rama no
lo rompió: lo heredó.

Los dos casos que caen son los únicos de su grupo que esperan `0`:

```
[FALLA] F · artefacto que declara VERDE: pasa  (exit 2, esperado 0)
[FALLA] F · JSON sin campo de veredicto: no se lo inventa, pasa  (exit 2, esperado 0)
```

Su hermano —`artefacto sin sha POSTERIOR a la meta`— lleva `time.sleep(0.05)`
entre forjar la meta y escribir la evidencia. **Estos dos no.** El guard exige
que el artefacto sea posterior a la meta; sin la pausa, ambos caen en el mismo
tick y «posterior» falla. Los tres casos ROJO del grupo pasan igualmente porque
un bloqueo falso también es un bloqueo.

Puesto el mismo sleep: **28/28, exit 0.** Es una carrera del arnés, no un fallo
del hook, y es determinista en este sistema de ficheros — no ruido. Lo que
convierte «lo comprobé después» en un problema no es el orden: es que la
comprobación tampoco lo desmintió.

### H5 · El canal de S2 está construido y vacío

`projects.json` en la máquina real declara **un solo proyecto: `atloos`**. El
mecanismo —leer los objetivos del registro que ya existe en vez de escribir una
segunda lista— es la decisión correcta y está bien argumentada. Pero hoy audita
exactamente el mismo objetivo que antes del sprint: este repo.

**`ProgramadoMaxi2`, el proyecto que falló graphify tres jornadas de tres, no
está en la lista.** Su `CLAUDE.md` sigue con la línea vieja y nada lo mirará.

La mitad buena de S2 sí es real y sí viaja: el disparador entró en
`memory-snippet.md` **y en su gemelo** `memory-instructions.md`, nombra un
momento (*«antes de tu primer `grep` de exploración»*) y ordena borrar la línea
vieja. Eso llega solo en cada onboarding nuevo.

**Acción, y no es código:** dar de alta los proyectos vivos en `projects.json`.
Sin eso, S2 es un canal correcto sin nada que transportar.

### H6 · Un paréntesis se salta el gate — preexistente, y no está declarado

```
rc=0  '(git push origin main)'
rc=0  '{ git push origin main; }'
rc=0  '(git merge feat/x)'
rc=0  '{ git merge feat/x; }'
rc=0  'if true; then git push origin main; fi'
rc=0  "bash -c 'git push origin main'"
```

Afecta también a `git merge`, así que **no es del sprint 2**: llevaba ahí desde
el W3. Lo nuevo es que ahora el hook declara sus límites en un bloque
—`LÍMITE DECLARADO: git push --delete`— y ese bloque **omite este**, lo que hace
que la cobertura se lea más ancha de lo que es.

`bash -c`, `if` y `for` son el límite honesto de cualquier parser de texto y
basta con decirlo. `( … )` y `{ …; }` son **un carácter de envoltorio** y sí se
pueden pelar. Recomiendo pelar los dos y ampliar el bloque de límites con el
resto.

### H7 · El «tope duro 500» no lo hace cumplir nadie

Está escrito en `test-skill-catalog.py`… dentro de la cadena de texto de una
tabla markdown generada. El único `return 1` del arnés depende de las
referencias colgantes. **Ningún check bloquea por palabras: ni 450, ni 475, ni
500.** Y siete skills viven entre 491 y 499:

`pipeline-designer` 499 · `vault-drift-audit` 499 · `data-quality-gates` 497 ·
`goal-forge` 495 · `design-doc-harvest` 495 · `project-resume` 494 ·
`session-close` 491.

Es la ley 1 aplicada al propio catálogo: la convención escrita no muerde. Va a
pendientes, no a este sprint.

### H8 · El motivo declarado para no vendorizar ya no aplica

`web-design-guidelines` acepta a conciencia depender de una URL, y da la razón:
*«la alternativa era vendorizar un documento de otro repo cuya licencia no hemos
verificado»*. La verifiqué: **`vercel-labs/web-interface-guidelines` es MIT**, el
`command.md` existe en `main`, y `vercel-labs/agent-skills` también es MIT y sí
contiene la skill. El bloqueo declarado está levantado; vendorizar con
atribución es una opción legal disponible, y cerraría justo la enfermedad que la
skill declara estar aceptando.

No pude verificar el commit `7c180d9…` (GitHub devolvió 403 a la API). Queda
**sin comprobar**, no desmentido.

### H9 · «Auditoría 21» ya no es un misterio, pero sigue colgando

El documento **existe**: commit `0c8064c`, rama `tg/20260811-…`, **sin mergear a
`main`**. Las cuatro referencias en código de `main` apuntan a algo que no está
en `main`. No era del sprint; sigue abierto.

### H10 · `test-gate-test.py` no puede correr fuera de Windows

3/9 en Linux, y las seis caídas dicen `/bin/sh: 1: py: not found`. Sus fixtures
declaran comandos con el lanzador `py`. Ahora es cosmético; **deja de serlo el
día que el mini PC 24/7 sea Linux**, que es la decisión D5/D8 ya tomada en
principio. A pendientes, con la compra.

---

## Lo que está bien, con evidencia

- **El arnés del push muerde.** 44/44 replicado. Y lo mutá: `revisa_push` que
  nunca bloquea → **35/44**; quitar `push` de la lista de verbos → **36/44**. No
  es decorativo.
- **La autoprueba del arnés de deriva funciona** — fabrica un `CLAUDE.md` con la
  línea vieja y exige el hallazgo, en cada corrida. Es la costumbre correcta y
  además es la que sobrevive a B1.
- **Los presupuestos de la tabla del reporte son exactos**, medidos por mí con
  el método del propio arnés: `requirements-designer` 449 · `merge-gate` 449 ·
  `dispatch` 450 · `project-onboard` 440 · `ml-problem-framing` 445 ·
  `ml-tabular-workflow` 448 · `web-design-guidelines` 428. La mea culpa 4 (452 y
  454 entregados) describe un proceso que falló y un resultado que se corrigió.
  38 SKILL.md en el repo, 36 desplegables a Claude Code — las 2 de diferencia
  son las de superficie `cowork`. El manifest cuadra.
- **`workstream-merge-gate` salió de la lista de saturación**: 536 → 449, con 3
  `references/` nuevos. Verificado.
- **El contenido de la familia 1 es correcto contra las fuentes.** Kaufman
  (KDD 2011) y su *no time machine*, Kapoor & Narayanan (*Patterns* 2023, 294
  papers / 17 disciplinas), L1-L2-L3, *model info sheets*, purging y embargo con
  López de Prado cap. 7, `TimeSeriesSplit(gap=)`, el target encoding
  out-of-fold, Rules of ML #1/#3/#4 y Sculley et al. 2015. **No encontré ni un
  dato mal citado.** Y la salida «no es ML» está puesta como la que más veces
  acierta, no como la de emergencia.
- **S4 entregó los cuatro puntos medidos**: la firma del fallo en el bloque 2
  —con el reverso de lista cerrada, que es lo que impide que la firma se vuelva
  excusa—, el bloque 8 de destino de la rama, la desambiguación contra SDD con
  el ×2,05 escrito, y el árbitro cuando discrepan.
- **El criterio del reloj está bien afilado**: suelo, ⅔ como regla práctica, y
  la frase que lo salva —*«la duración es el detector, el conteo es el
  diagnóstico»*—. Y el reverso, que no se vuelva techo.
- **La corrección al encargo es justa en las dos.** `merge-gate` estaba en 536,
  no en 497: mi cifra venía del vault y el vault estaba al día — el error era
  mío en el prompt. Y el criterio del reloj sí existía como frase; afilarlo, no
  crearlo, es la descripción correcta.
- **La procedencia de la externa es el estándar que quiero para todas**: origen,
  commit, licencia, fecha, adaptación declarada y el límite dicho en voz alta.

---

## Qué hacer, en orden

1. **B1** — `[SKIP]` en vez de hallazgo cuando faltan `projects.json` o
   `CLAUDE.md`, con caso de arnés corrido **desde un worktree**.
2. **B2** — resolver `HEAD`/`@`/`head` a la rama actual, con los tres casos en
   el arnés.
3. **B3** — devolver los marcadores `<…>` a la sección 9 de la plantilla.
4. **H4** — el `time.sleep(0.05)` en los dos casos del grupo F. Sale de este
   sprint: arregla un rojo que está en `main`.
5. **H5** — alta de los proyectos vivos en `projects.json`. No es código.
6. **H6** — pelar `( )` y `{ }`, y ampliar el bloque de límites declarados.

Con 1, 2 y 3 la rama es integrable. 4 y 5 se pueden hacer en el mismo empujón
porque son de una línea cada uno; 6 puede esperar si el presupuesto aprieta.

**A pendientes:** H7 (el tope sin arnés), H9 (auditoría 21 sin mergear), H10
(el arnés atado a Windows, con la compra del mini PC).

---

## Lo que no pude comprobar

- **Las cinco sesiones ciegas de disparo.** El laboratorio no tiene red ni
  Claude Code, así que los `claude -p` del reporte entran como **[AR]**. Lo que
  sí verifiqué es lo estático: la `description` de `requirements-designer`
  contiene ahora *«desarrolla el MVP de X»* y *«haz X para \<persona\>»*, que
  cubren literalmente la frase que en campo no disparó, y el reparto contra
  `superpowers:brainstorming` está escrito en los dos sentidos.
- **El commit `7c180d9…` de Vercel** — 403 de la API. Sin comprobar.
- **Si el rojo de H4 también se da en Windows.** Es una carrera de resolución de
  reloj y sistema de ficheros; en Linux es determinista. Que allí saliera verde
  no lo desmiente: lo convierte en flaky, que es peor que rojo.
