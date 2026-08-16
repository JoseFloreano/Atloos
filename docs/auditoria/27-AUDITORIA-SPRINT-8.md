---
title: Auditoría del sprint 8 — la higiene se sostiene, el techo se quedó sin explicación, y el CRLF espera en la SER8
tags: [auditoria, sprint8, higiene, paralelismo, crlf, gitattributes]
created: 2026-08-16
updated: 2026-08-16
status: cerrada
type: auditoria
project: atloos
base: e2ec4d5
---

# Auditoría del sprint 8

**Veredicto: aceptado.** Cuatro entregas hechas, ninguna fingida, y **lo mejor
del sprint no se lo pedí**: `medir-el-techo.md` y la retractación escrita en
`gobierno-vs-sdd.md`. Cero bloqueantes. Siete hallazgos, y **cuatro de los siete
son míos**.

> Todo lo marcado **[R]** lo repliqué desde el puente sobre `e2ec4d5`. **[AR]**
> es autorreportado y no lo pude tocar. **[H]** lo dijo el humano.

---

## 1 · Lo que repliqué y está bien

**Base y ramas [R].** `main` sigue en `1dd8710` sin tocar. `sprint8/higiene-y-capacidad`
en `e2ec4d5`, dos commits sobre `b9a9d98`. Partió, no integró, y lo dijo. Correcto:
el gate exige verde posterior y OK humano, y no los tenía.

**S2 · el `<persona>` [R].** Un diff de **una línea**. La description resuelta
mide **911 caracteres** —los conté yo, no leí su número—, las **seis frases
gatillo están las seis** sobre disco, y ningún frontmatter de las 39 lleva
angulares.

**S2 · el check 5, contra mis mutaciones, no las suyas [R].** Le pasé siete que
él no escribió:

| # | Mutación | Esperado | Resultado |
|---|---|---|---|
| 1 | `<algo>` en la **primera** línea de la description | caza | **exit 1** ✅ |
| 2 | `<algo>` en la **última** línea (cola del escalar) | caza | **exit 1** ✅ |
| 3 | etiqueta de **cierre** `</b>` | caza | **exit 1** ✅ |
| 4 | **angular partido por el salto**: `<perso` + `na>` | caza | **exit 1** ✅ |
| 5 | `a < b` (el límite **declarado**) | no caza | exit 0 ✅ |
| 6 | angular en el **cuerpo** | no caza | exit 0 ✅ |
| 7 | angular en el campo **`name`** | — | **exit 1** ✅ |

**La 4 es la que importa.** Es la quinta aparición de la familia «el check mide
por línea» —que mordió en los sprints 1, 3, 6 y 6— y esta vez **no muerde**,
porque el check mide el valor **resuelto** del escalar plegado y no el texto
crudo. Es la lección del sprint 7 aplicada **antes** de que costara algo.

**S3 · la hipótesis del `-n auto` está muerta, y la maté yo también [R].** No hay
`pyproject.toml`, `pytest.ini`, `setup.cfg` ni `tox.ini`. `grep` de `addopts` /
`numprocesses` / `-n auto` sobre todo el repo: **cero**. `run-tests.py` corre
cada arnés con `subprocess.run` dentro de un `for` — **serial**, sin paralelismo
de ninguna clase.

**Las cifras de higiene, dos al azar [R].** `git log --stat` me da **225 578 B**
contra sus 222 314 (midió con dos commits menos) y `--oneline -n 50` me da
**4 269 B** contra sus 4 267. El −98,1 % se sostiene.

**`no-perdida.py` [R].** Exit **0** en las cinco skills, con `--base b9a9d98`,
corrido por mí.

**Worktrees [R].** Nueve registrados, como dice.

---

## 2 · H1 · La suite no es 18/18 desde donde yo miro — y el motivo espera en la SER8

**[R]** Desde el puente, `run-tests.py` da **17/18**.
`test-graph-report-hook.py` cae con **4 casos**, todos con `exit 2; llamadas: ''`.

La causa, reproducida a pelo:

```
$ bash setup/hooks/git-post-commit-graph-report.sh
setup/hooks/git-post-commit-graph-report.sh: line 34: $'\r': command not found
setup/hooks/git-post-commit-graph-report.sh: line 37: syntax error near unexpected token `|'
exit=2
```

**El `.sh` llega al árbol de trabajo con CRLF.** Y aquí va la parte que evita
que esto se convierta en un falso hallazgo: **los blobs están limpios** — conté
los `\r` dentro de `git cat-file blob` de los cinco `.sh` y de ocho `.py` de
`setup/hooks/`: **cero en todos**. Así que **no es un defecto del repo, es del
árbol de trabajo**, y su 18/18 en Windows es creíble.

> **Pero el repo no tiene `.gitattributes`.** Ninguno. La protección es hoy la
> variable `core.autocrlf` de cada máquina, y eso es una decisión que no está
> escrita en ningún sitio del proyecto.

**Y ahí está lo que importa, porque es la semana que viene:** la SER8 va a
correr **Ubuntu**. Si el repo llega a esa máquina por **`git clone`**, no pasa
nada. Si llega por **la carpeta de OneDrive** —que es como viaja hoy entre tus
dos laptops—, entonces `setup-new-machine.sh`, `sync-skills.sh` y el hook
`post-commit` aterrizan con CRLF y mueren con **el error que acabo de
reproducir**, en el primer minuto de la instalación.

**Y el hueco es mío:** repasé mi propio manual (`docs/telegram/23`) y **no dice
en ninguna parte cómo llega el repo a la mini PC**. Ni `git clone`, ni OneDrive,
ni rclone. Cero apariciones. Escribí 34 KB de manual y me salté el paso que
decide si los scripts arrancan.

**Lo barato, y va antes que la SER8:** un `.gitattributes` con `* text=auto` y
`*.sh text eol=lf`.

---

## 3 · H2 · Tú y yo no vemos el mismo repositorio

**[R]** Desde el puente, ahora mismo:

```
git config core.autocrlf              → (vacío, sin definir)
git diff --name-only --ignore-cr-at-eol | wc -l   → 162
git diff --numstat   --ignore-cr-at-eol | wc -l   → 0
git status --short | wc -l                        → 162
```

En Windows, con `core.autocrlf=true`, el árbol sale limpio. **Su frase «aquí no
se reproduce» y mi «159 contra 0» son las dos verdad**, cada una en su lado del
mismo repositorio.

> Esto no es una curiosidad: es que **ningún juicio sobre «qué cambió» es
> portable entre el implementador y el auditor** hasta que haya
> `.gitattributes`. Es la prima hermana del problema de bytes rancios de
> OneDrive, y se arregla con la misma línea que H1.

⚠ Y un aviso operativo de mi propia sesión: un `git status` desde el puente dejó
un **`.git/index.lock`** que la VM no puede borrar (`Operation not permitted`).
**Lo moví a `_to_delete/`**. Si alguna vez ves un git bloqueado sin motivo,
mira ahí primero.

---

## 4 · H3 · El presupuesto de núcleos está dimensionado para una máquina que no existe

**[R]** En el mismo commit conviven:

- `references/medir-el-techo.md:18` — *«`FLOREANO_LEGION` (Intel Core Ultra 9
  275HX) tiene **24** núcleos»*
- `references/plantilla-despacho.md:255` — *«| 3, **en 8 núcleos** | `-n 2` |
  3 × 2 = 6, y 2 reservados |»*, y *«| 1, en solitario | **`-n 8`** |»*

**Es justo decir que no es falso**: la fila está condicionada («en 8 núcleos») y
diecinueve líneas más abajo el propio fichero declara que *«en Atloos esto no
aplica hoy»*. Pero **es una tabla rancia de nacimiento**: en la máquina real la
fila que aplica no existe, y quien corriera en solitario con `-n 8` dejaría
**16 núcleos parados**.

**Y la causa raíz es mía**: el encargo ordenó literalmente *«`-n 2` por frente
con 3 frentes en 8 núcleos»*. Escribí el número; él lo escribió donde le dije.

**Lo que corrige la clase, no la instancia:** que la fila sea una **fórmula** y
no una tabla con un número clavado — `workers por frente = (núcleos − 2) ÷
frentes vivos`, con `os.cpu_count()` como entrada. Así la misma frase vale para
24, para los 8 de la SER8 y para la siguiente máquina.

---

## 5 · H4 · `450` es un número que nadie mide — **sexta vez**

**[R]** El reporte da cinco presupuestos como «449/450», «442/450», «446/450».
Ese **450 no existe en el arnés**: `test-skill-catalog.py` define
`SATURACION = 475` (aviso) y `TOPE_DURO = 500` (bloquea). El 450 solo vive en un
docstring: *«una skill nueva nace en ≤450»*.

Una skill a **460** pasa en silencio mientras el contrato dice que no debería
existir. El riesgo está **acotado** —el 475 deja margen—, pero la forma es
exactamente la que ese fichero persigue en los demás.

> Quinta vez conté yo en la poda del tablero (500 palabras, techo de
> `_PROJECT.md`, 1024 caracteres, umbrales 8/12). **Esta es la sexta, y está
> dentro del arnés que vigila a las otras.**

**Y una que hay que apuntar antes de que muerda [R]:** `shared/schema-designer`
está en **475 palabras con 0 `references/`** — la única de las 39 sobre el umbral
de aviso, y no la tocó este sprint. Es la próxima en cruzar el 500.

---

## 6 · H5 · La única vía de despliegue siempre-activa es la que no deja rastro

Él escribió la línea de higiene en los `CLAUDE.md` de **AlphaDogs** y **TT1**.
Lo decidió, lo declaró y ofreció revertirlo — eso está bien hecho. El hallazgo
es **estructural**, no de conducta:

**[R]** Corrí `test-claude-md-drift.py` desde el puente y **saltó los tres
destinos**, incluido el de `atloos`:

```
[SKIP] alphadogs: declarado en projects.json pero no está en esta máquina
[SKIP] atloos:    declarado en projects.json pero no está en esta máquina
[SKIP] tt1-revisor-chatbot: … — multi-laptop, no deriva
[OK] los gemelos coinciden y 1 CLAUDE.md al día
```

Suma tres cosas: los `CLAUDE.md` están **gitignorados**, viven **fuera de este
repo**, y el check **salta lo que no está en la máquina**. Resultado: **~95
tokens por sesión entraron en dos proyectos ajenos y no hay forma de auditarlo
desde ninguna otra máquina.** El vehículo funciona; lo que no existe es el
recibo.

**Es tuya la decisión [H]**, y es lo que hay que firmar: ¿esa línea se queda en
AlphaDogs y TT1? Revertirla cuesta quitar una línea de los dos gemelos y de los
tres destinos.

---

## 7 · H6 · El ×2,05 se quedó sin ninguna explicación, y tenía dos

Antes de este sprint, el repo daba **dos causas distintas** para el mismo número:
`gobierno-vs-sdd.md` decía **CPU**, `protocolo-escalacion.md` decía **RAM**.
Ninguna de las dos estaba medida.

Y ahora las dos están peor: **5 frentes sobre 24 núcleos, con la suite corriendo
como subprocesos seriales, no puede saturar la CPU**. La hipótesis de la fuga de
`-n auto` está descartada [R]. Queda un número —×2,05— **medido una vez, hace
cinco días, en una máquina que no consta, con dos explicaciones incompatibles y
ninguna sostenida**, y ese número es **el único techo que tenemos**.

`medir-el-techo.md` dice esto mismo con todas sus letras y sin adornarlo. Es la
pieza mejor escrita del sprint y no la pedí.

---

## 8 · Mea culpa — cuatro, y una es de esta misma auditoría

**1 · La premisa de S4 era mía y era falsa.** Escribí *«esa medición está
contaminada por el §0»* como si estuviera establecido. Era una hipótesis. Peor:
la metí en el **texto plantilla** que él debía copiar en cinco sitios —*«Revisar
al cambiar de máquina o al quitar el `-n auto`»`*— cuando aquí no hay `-n auto`
que quitar. **Si hubiera implementado por obediencia, habría escrito ficción en
cinco ficheros.** Lo único que lo evitó es que el mismo encargo ordenaba medir
antes (S3 → S4). Su queja es correcta y la acepto entera.

**2 · Los «8 núcleos» son míos, y son de otra máquina.** El RFD 26 construyó
todo el §1 sobre el 8845HS —**la SER8, que ni siquiera está montada**— y luego
aplicó ese presupuesto al portátil donde se hizo la medición, que tiene **24**.
Está en cuatro sitios del RFD 26 y en el `25:185`. **Erratas, y hay que
escribirlas** (§9).

**3 · La contradicción `=6` contra `=3` es mía [R].**
`docs/telegram/20-DIMENSIONADO…:178` pone
`Environment=CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=6`; `docs/telegram/23-MANUAL…:748`
pone `=3`. Dos manuales míos, del mismo servidor, con el mismo ajuste y números
distintos. Él lo encontró y **no lo tocó, porque no era su encargo**. Correcto.

**4 · Mi encargo se contradecía en `skill-forge`.** «Gana la regla en la misma
frase» (eso es el cuerpo) contra «no escribas en el cuerpo de `skill-forge`».
Escribí *«entra extrayendo»*, que es la salida — pero la resolución iba en una
frase distinta de la orden, y eso lo tuvo que reconstruir él. Hit justo.

**5 · Volví a leer `$?` después de una tubería, en esta auditoría.** `python $t
2>&1 | head -8; echo "exit=$?"` me devolvió el exit de `head`, no el de Python.
**Cuarta vez este mes**, y esta vez mientras auditaba un sprint cuya entrega
principal contiene la regla de no hacerlo. Lo vi porque el 0 no cuadraba con un
traceback en pantalla.

---

## 9 · Erratas que tengo que escribir yo

| Dónde | Qué dice | Qué es verdad |
|---|---|---|
| RFD 26 §1.1, §1.2, §0, §3.4 | «8 núcleos» como la máquina de la medición | la medición se hizo en `FLOREANO_LEGION`, **24 núcleos**; los 8 son de la SER8, sin montar |
| RFD 26 §0 y §3.4 | el ×2,05 «puede ser» una fuga de `-n auto` | **descartado y medido**: no hay pytest en este repo |
| RFD 25:185 | «×2,05 por contención, en 8 núcleos» | misma errata |
| `docs/telegram/20:178` vs `23:748` | `=6` contra `=3` | uno de los dos sobra; **sin arbitrar** |

**No los edito ahora mismo**, y digo por qué: los RFD 25 y 26 ya están
**commiteados en su rama** (`e7ca5f5`), y tocarlos desde aquí le dejaría cambios
sin explicar en su árbol — que es exactamente la ley 3 que ya rompí una vez con
`AGRADECIMIENTOS.md`. Van en el siguiente encargo, o los aplico en cuanto la
rama esté integrada.

---

## 10 · Lo que queda en el tablero después de esto

1. **`.gitattributes`** — `* text=auto`, `*.sh text eol=lf`. Barato y **va antes
   de la SER8**.
2. **Cómo llega el repo a la mini PC** — falta en mi manual. `git clone`, no
   sincronizar la carpeta.
3. **La fórmula de núcleos** en vez de la tabla de 8.
4. **El 450 sin arnés**, y `schema-designer` en 475 con 0 `references/`.
5. **¿Se queda la línea de higiene en AlphaDogs y TT1?** — tu firma.
6. **`=6` contra `=3`** en los dos manuales del servidor — tu firma.
7. **El ×2,05 sin explicación.** Ya no es una deuda de medición: es una deuda de
   **saber si el techo existe**.
8. **Dos ramas sin integrar** (`sprint7` y `sprint8`), y `main` en `1dd8710`.

---

---

## 11 · Las dos firmas que me devolvió el humano

**[H]** *«2. ¿Se queda la línea de higiene en AlphaDogs y TT1? Sigue siendo tu
firma. 3. =6 contra =3 en los dos manuales del SER8. Tu firma. duda en la 2 si
no? hay que meter la higiene de los logs»* — 2026-08-16.

Las firmo yo, con el motivo escrito para que no se re-discutan.

### Firma 1 · La línea de higiene **SE QUEDA** en AlphaDogs y TT1

Y la objeción de coste **no sobrevive a medirla**. Conté el snippet [R]:

| | Caracteres | ≈ tokens (car ÷ 3,0–3,8) |
|---|---:|---:|
| Lo que entra en cada `CLAUDE.md` | **3 253** | **856 – 1 084** |
| …de eso, la línea de higiene | 474 | 125 – 158 |
| **Presupuesto que el propio fichero declara** | — | **~300** |

> **El snippet va a ~3× de su propio presupuesto declarado, y ya iba a ~2,5×
> antes de que la higiene entrara.** Quitar la línea recorta el **14 %** de un
> bloque que se pasa por 600 tokens. Sería cortar por donde no está el problema.

Tres razones, en orden:

1. **Es lo que pediste.** *«Alta prioridad en la higiene de los logs»*, y el
   argumento de S1 se sostiene: una regla que solo se lee al despachar no
   gobierna a la sesión que no despacha. Fuera de AlphaDogs y TT1, la higiene
   viviría solo en el meta-repo — que es el proyecto donde menos falta hace.
2. **El coste real es 125-158 tokens**, no los ~95 del reporte, y aun así es la
   parte más barata del bloque.
3. **El ×2,05 murió, la higiene no.** De las cuatro palancas del RFD 26 para
   subir la capacidad de subagentes, esta es la única que quedó **medida** —
   −91 % a −99 % de bytes, con cifras de este repo.

⚠ **Pero se queda con dos condiciones**, porque conservarla sin ellas repite el
hallazgo que la rodea:

- **El snippet se mide y su presupuesto se ajusta.** O el «~300» pasa a ser el
  número real, o el snippet se recorta hasta él. **Séptima vez el mismo patrón**
  —un número escrito que nadie mide— y es el de mayor radio: gobierna lo que se
  inyecta en **cada sesión de cada proyecto**.
- **El despliegue deja recibo.** Un **sello de versión** en el snippet, visible
  en el `CLAUDE.md` desplegado, para que cualquier máquina conteste con un
  `grep` qué versión lleva. Hoy `test-claude-md-drift.py` **salta** los tres
  destinos que no están en la máquina y firma *«1 CLAUDE.md al día»* [R]. Con
  sello, el `[SKIP]` sigue existiendo —no se puede auditar un fichero que no
  está— pero deja de ser silencioso.

### Firma 2 · Ni `=6` ni `=3` — **fuera de los dos manuales**

1. **Es el cap que arbitraste en contra.** `Environment=CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=6`
   dentro de una unit de systemd es exactamente D16, escondido en el sitio que
   nadie relee. *«Quiero ir aumentando la capacidad de subagentes»* no es
   compatible con clavarlo en el arranque del servidor.
2. **Los dos números descienden del ×2,05**, que se quedó sin explicación (§7).
   Y **ninguno se midió en la SER8**, que no está montada. Escribir cualquiera
   de los dos es inventar un número para una máquina que nadie ha arrancado.
3. **Lo que va en su lugar**, y es más seguro que un cap:
   - **Nada puesto** → el defecto (20), y un **paso de instalación** que mide el
     RSS de la primera corrida real y solo entonces escribe un valor **con fecha
     y máquina**, igual que `medir-el-techo.md`.
   - **La barrera de verdad en un servidor de 24 GB headless es la RAM**, y
     Linux ya tiene el mecanismo correcto: `MemoryMax=` / `MemoryHigh=` en la
     propia unit (RFD 26 §1.4). Falla cerrado contra el OOM **sin poner techo a
     la ambición**, que es justo la distinción que pediste.

---

## 12 · Rectificación — el implementador tiene razón en H6, y la fuente primaria dice más que los dos

Pedí acceso a `Downloads/` y leí los dos reportes. **Su refutación se sostiene y
mi H6 estaba mal razonado.**

### Lo que concedo entero

**H6 era un razonamiento correcto aplicado al runner equivocado.** Escribí que
«5 frentes sobre 24 núcleos con subprocesos seriales no pueden saturar la CPU».
Cierto de `run-tests.py`, **irrelevante** para una suite de pytest en otro
proyecto. Declaré muerta una explicación mirando la máquina de al lado.

**Y la errata del §9 es peor que el error que corregía.** Escribí *«la medición
se hizo en `FLOREANO_LEGION`, 24 núcleos»* sin ninguna fuente. Cambiar un dato
sin respaldo por otro sin respaldo no es corregir: es mover la ficción.

**Los dos matices, replicados y concedidos [R]:** en `_to_delete/` había ya
**siete** locks del 7-9 de agosto —no los vi porque empiezan por punto y `ls -1`
los oculta—, así que el mío es el octavo y no un incidente. Y el **450 sí está
documentado** en `skill-forge/SKILL.md:28` (*«≤450, duro 500»*): es convención
escrita, no contrato incumplido. H4 se reduce a lo que él dice — **falta que
muerda**, entre 451 y 474 nadie avisa.

### Lo que la fuente primaria dice, y que él tampoco leyó [R]

Leí las dos cabeceras completas, no solo el cuerpo:

```yaml
# 2026-08-10-programadomaxi2-mvp-avisos-por-corte.md
maquina: ProgramadoMaxi2
so: Windows 11 Pro
tarea: Desarrollar el MVP de avisos por corte para el subdirector de cobranza
```

**1 · `ProgramadoMaxi2` es la MÁQUINA, no el proyecto.** Lo dice el campo
`maquina:` de los dos reportes, y lo dice **mi propio contrato de nombres**:
`feedback/PROMPT.md:126` fija `AAAA-MM-DD-<alias-maquina>-<slug-tarea>.md`, y el
fichero se llama `2026-08-10` + `programadomaxi2` + `mvp-avisos-por-corte`. No
está en `projects.json` (`atloos`, `alphadogs`, `tt1-revisor-chatbot`).

> Así que las **dos** filas nuevas de `medir-el-techo.md` están mal: *«De qué
> suite: la de ProgramadoMaxi2»* etiqueta la suite con un nombre de máquina, y
> *«Máquina: no consta»* es falso — **la máquina sí consta; lo que no consta es
> su tamaño**. Ni núcleos ni RAM, en ninguno de los dos reportes.
>
> ⚠ Y es una confusión con antecedentes: **mi auditoría 22 la llama «el
> proyecto»** (línea 174), y él ya me corrigió esa misma categoría una vez.
> Tercera pasada por el mismo error, en las dos direcciones.

**2 · El `3 960 passed / 416,99 s` es del reporte del día SIGUIENTE.** Está en el
del 08-11; el ×2,05 es del 08-10. Identificar las dos suites es una **inferencia
razonable, no una medición** — y decirlo importa justo aquí.

**3 · El ×2,05 es un cociente de dos clases de evidencia distintas.** El 677 s
está marcado `[AR]`. Pero el **suelo de ~330 s está marcado `[R]`**, en otro
punto del mismo reporte: *«El gate cazó dos verdes falsos por el reloj: 117 s y
146 s contra un suelo de ~330 s»*. **Denominador replicado, numerador
autorreportado.** El único techo que gobierna todos los despachos es una razón
entre un hecho y un dicho.

### Y la causa raíz es mía, y no es el grep

El formato de feedback lo diseñé yo. Tiene un campo `maquina:` y una sección
titulada **«2. Evidencia de máquina»**… que pide `claude --version`, el sha de
git, `git status --porcelain | wc -l` y el sha del setup. **No pide núcleos. No
pide RAM. No pide de qué suite es un tiempo.**

> **Una sección llamada «evidencia de máquina» que no recoge ni una sola
> propiedad de la máquina.** Por eso un número pudo cruzar cuatro sprints y ocho
> ficheros sin que nadie pudiera atribuirlo. El grep al repo equivocado es el
> síntoma; esto es la causa.

**Lo que hay que arreglar**, y va al sprint 9: la sección 2 gana tres líneas
(`os.cpu_count()`, RAM, alias de máquina ya está) y **la regla de que cualquier
cifra de tiempo nombre la suite de la que sale**.

### Su frase final, que me quedo

> *«`medir-el-techo.md` era la pieza que él más elogió, y era la que llevaba
> dentro el error más grave. Que un documento esté bien escrito sobre lo que no
> sabe no lo protege de estar anclado al dato equivocado.»*

Tiene razón, y añade la lección que me toca: **elogié la honestidad de la forma
y no comprobé la procedencia del dato.** Es exactamente el fallo que persigo en
los demás — el reporte no es el artefacto — cometido sobre un documento que me
gustó.

---

**Escrito por el auditor externo desde el puente, sobre `e2ec4d5`.** Este
fichero es nuevo en `docs/auditoria/` y **no está commiteado** — lo digo aquí
porque la última vez que dejé un fichero sin avisar, el implementador lo
reportó como un escritor desconocido tres reportes seguidos.
