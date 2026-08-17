# El techo de frentes — cómo se re-mide, y qué invalida el resultado

El número de frentes simultáneos **no es un principio, es un dato con fecha**.
Este documento existe para que caduque bien: dice de dónde sale el que está
escrito, cómo sacar uno nuevo y **qué hace inválida la medición**.

## De dónde sale el 3 que hay escrito hoy

| | |
|---|---|
| Medición | 5 frentes: la suite pasó de ~330 s a **677 s** (**×2,05**), y una prueba de latencia falló por carga |
| Cuándo | **2026-08-10**, en campo — **una sola vez, sin repetir** |
| **De qué suite** | **NO la de Atloos.** Es la del proyecto de esa jornada — el MVP de avisos por corte para cobranza — y **su nombre no está en el reporte**: solo la tarea |
| **Máquina** | **`ProgramadoMaxi2`, Windows 11 Pro** (campo `maquina:` de la cabecera). **Lo que NO consta es su tamaño**: ni núcleos ni RAM, en ninguno de los dos reportes |
| Calidad del dato | **partida.** El **pico de 677 s es `[AR]`**, autorreportado por el propio agente que corrió los 5 frentes; el **suelo de ~330 s es `[R]`**, replicado — el gate lo usó ese día para cazar dos verdes falsos, de 117 s y 146 s |
| Qué se dedujo | «máximo 3 frentes», aplicado a **todos** los proyectos y a **todas** las máquinas |

> **Denominador replicado, numerador autorreportado.** Es la descripción más
> exacta que se puede dar del único techo que gobierna los despachos, y merece
> decirse así en vez de redondear a «medido» o a «sin medir».

⚠ **`ProgramadoMaxi2` es una MÁQUINA, no un proyecto.** Lo dice el campo
`maquina:` de los dos reportes, lo dice el contrato de nombres de fichero
(`AAAA-MM-DD-<alias-maquina>-<slug-tarea>`) y lo confirma que no está en
`projects.json`. Es la **tercera pasada** de esta confusión —la auditoría 22 la
llama «el proyecto» y el sprint 8 etiquetó la suite con su nombre—, y por eso
va escrito aquí en vez de arreglado en silencio.

⚠ **La suite de esos ~330 s no está identificada con certeza.** El reporte del
día siguiente (08-11, misma máquina) dice `3960 passed, 83 skipped, 4 xfailed`
en **416,99 s**, y es *razonable* que sea la misma suite un día después. **Eso
es una inferencia, no una medición**: los dos números vienen de reportes
distintos y nadie los corrió juntos. Se escribe como inferencia a propósito —
encadenar dos datos plausibles y llamarlo medido es cómo el ×2,05 llegó hasta
aquí.

**Y ahí están sus tres grietas, las tres verificadas el 2026-08-16:**

1. **La medición no es de este repo ni de esta máquina.** El ×2,05 se midió en
   `ProgramadoMaxi2` sobre la suite de otro proyecto — probablemente pytest con
   ~3 960 tests, por la inferencia de arriba. La de Atloos son 18 arneses
   seriales que hoy tardan **43 s**. Un techo deducido allí y escrito aquí **no
   es el mismo número**, y hasta el sprint 9 nada lo decía.
2. **Los 8 núcleos no son de nadie.** No salen del reporte —que no anota tamaño
   de máquina— sino del dimensionado de la **SER8**, que ni está montada.
   `FLOREANO_LEGION` (Intel Core Ultra 9 275HX) tiene **24**, y de
   `ProgramadoMaxi2` no sabemos nada. El presupuesto «3 × 2 workers + 2
   reservados = 8» se escribió contra un tamaño que no era el de ninguna de las
   dos máquinas implicadas.
3. **La contaminación por `-n auto` sigue SIN COMPROBAR — y es la hipótesis
   viva.** ⚠ Aquí se cometió el error que este documento existe para evitar: el
   sprint 8 grepeó `addopts` en **Atloos** —donde no hay pytest— y declaró la
   hipótesis cerrada. **Se grepeó el repo equivocado.** El que hay que mirar es
   **ProgramadoMaxi2**, que sí usa pytest, y **no está en esta laptop**. Con
   `-n auto` y 24 núcleos, 5 frentes son hasta **120 procesos de test**: la fuga
   explicaría el ×2,05 de sobra. Nadie lo ha mirado todavía.

> El 3 no está refutado ni confirmado. Está **sin anclar**: una medición
> autorreportada, no repetida, **de otro proyecto**, en una máquina que no
> consta, con su explicación más probable aún sin comprobar. Eso no es un techo
> — es el último número que alguien apuntó.

**Lo primero que hay que hacer, y cuesta diez segundos en la máquina correcta:**

```
grep -rn "addopts\|numprocesses\|-n auto" \
     <raiz-de-ProgramadoMaxi2>/{pyproject.toml,pytest.ini,setup.cfg,tox.ini}
```

## Lo que este documento afirmó antes, y por qué dejó de afirmarlo

Un fichero sobre números que sobreviven a su evidencia necesita su propio
registro de retractaciones. Las que hubo que **retirar** van aquí en vez de
borradas, porque es más **útil**: una afirmación retirada dice qué se creía y
por qué dejó de creerse; una ausencia no dice nada. Y varias no **estaban**
mal por descuido de redacción — **estaban** mal por no ir a mirar, que es peor
y se corrige distinto: hay que **anotar** cada una con su causa.

| Se afirmaba | Dónde | Qué pasó |
|---|---|---|
| «los límites numéricos están **medidos en esta máquina**» | `gobierno-vs-sdd.md`, hasta el sprint 8 | Falso. La medición es de otra máquina. |
| «la **máquina** no consta / sin máquina **anotada**» | aquí y en tres sitios más, sprint 8 | **Falso, y por no leer.** El campo `maquina:` de la cabecera del reporte dice `ProgramadoMaxi2` desde el primer día; se leyó el cuerpo y no el frontmatter. Lo que no consta es el **tamaño**. |
| «la suite de **ProgramadoMaxi2**» | aquí, sprint 8 | Etiquetaba la suite con un nombre de **máquina**. El proyecto de esa jornada era el MVP de avisos por corte, y su nombre no está en el reporte. |
| «nadie lo **comprobó**» sobre los 8 núcleos | aquí, sprint 8 | Cierto pero incompleto: los 8 no salían de nadie, salían del dimensionado de la SER8. |
| «se **construyó** encima un presupuesto para 8 núcleos» | aquí, sprint 8 | Se mantiene, con la corrección de arriba. |
| «`os.cpu_count()` y `psutil` **coinciden** en 24» | aquí, sprint 8 | **Se mantiene**: replicado el 2026-08-16. |

⚠ **`ProgramadoMaxi2` es una máquina, y esta es la tercera vez que se confunde
con un proyecto** (la auditoría 22, el sprint 8, y por poco el 9). El contrato
de nombres es `AAAA-MM-DD-<alias-maquina>-<slug-tarea>`: lo que va después de la
fecha **es la máquina**. Los reportes de campo viven en `Downloads/`, no en el
repo, así que nadie los ve por accidente — hay que ir a buscarlos, y hay que
leerles la cabecera.

**Y la causa raíz ya está arreglada donde tocaba**: el formato de feedback pide
`nucleos` y `ram_gb` desde la v3 (2026-08-16), y `valida-reporte.py` los exige
como número. Sin eso, el próximo tiempo medido volvería a viajar sin poder
atribuirse — que es exactamente lo que se **replicó** aquí cuatro sprints
seguidos.

## El procedimiento, cuando se re-mida

Una corrida por escenario, y los escenarios en este orden (el barato primero):

1. **Línea base de un frente, en solitario.** Dos corridas, y se anota la
   dispersión — si las dos difieren más de un 15 %, la máquina no está quieta y
   lo demás no vale.
2. **3 frentes a la vez**, cada uno en su worktree, con su presupuesto de
   núcleos declarado (bloque 5 de `plantilla-despacho.md`).
3. **5 frentes**, igual.

De cada escenario se anota: **wall de la suite más lenta**, exit code de cada
una, núcleos de la máquina y carga en reposo antes de empezar.

```bash
# el instrumento, sin tubería (higiene-de-salida.md)
"$HOME/.claude/scripts/py" -c "import os,psutil; print(os.cpu_count(), psutil.cpu_percent(interval=1))"
inicio=$(date +%s); setup/scripts/py setup/scripts/run-tests.py > /tmp/f1.txt 2>&1; echo "exit=$?"   # [repo]
echo "wall=$(( $(date +%s) - inicio ))s"; tail -1 /tmp/f1.txt
```

**Línea base ya medida** (2026-08-15, `FLOREANO_LEGION`, 24 núcleos, CPU al
7,7 % en reposo, un frente en solitario): **43 s y 48 s**, 18/18, exit 0. Ese es
el número contra el que se compara cualquier escenario futuro.

## ⚠ Qué INVALIDA el resultado

Si cualquiera de estas es cierta durante la medición, **el número no se escribe
en ningún sitio** — se repite la corrida:

- **`-n auto` sin presupuesto** en cualquiera de los frentes. `auto` cuenta los
  núcleos del **host**, no los del frente, así que N frentes se multiplican por
  los núcleos enteros. Y no se acota con `taskset`: xdist pregunta a psutil, que
  ignora la afinidad (`plantilla-despacho.md`, bloque 5).
- **Otra carga en la máquina**: otra sesión de agente, un build, una indexación
  de OneDrive, un backup. Se mide `psutil.cpu_percent()` en reposo **antes** y
  se anota; por encima del 15 % no se mide.
- **Throttling térmico.** En un portátil una corrida larga baja de frecuencia
  sola, así que el escenario de 5 frentes castiga por calor, no por contención.
  Si las corridas van de menos a más largas, el sesgo va todo en la misma
  dirección — alterna el orden.
- **Núcleos distintos de los del número escrito.** Cambiar de laptop invalida el
  techo entero: es multi-laptop, y la Legion y la SER8 no son la misma máquina.
- **Runner distinto.** El día que este repo adopte pytest + xdist, la línea base
  de 43 s deja de ser comparable con nada de aquí.

## Dónde tiene sentido medir de verdad

El escenario de 3 y 5 frentes **no se corrió el 2026-08-15**: cuesta más de 20
minutos de máquina ocupada y el sitio donde importa es la **SER8**, porque es
donde `CPUQuota` por frente existe. Windows no tiene equivalente utilizable —
Job Objects necesita P/Invoke y `Start-Process` no acepta afinidad—, así que
aquí el reparto es una convención, no un límite que la máquina imponga.

Hasta que se re-mida, el 3 se trata como **conservador y provisional**, no como
el techo del harness. Y la dirección declarada por el humano es **subir**,
así que la pregunta que la medición tiene que contestar no es «¿aguanta 3?»
sino **«¿dónde empieza a doler de verdad?»**.
