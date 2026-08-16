# El techo de frentes — cómo se re-mide, y qué invalida el resultado

El número de frentes simultáneos **no es un principio, es un dato con fecha**.
Este documento existe para que caduque bien: dice de dónde sale el que está
escrito, cómo sacar uno nuevo y **qué hace inválida la medición**.

## De dónde sale el 3 que hay escrito hoy

| | |
|---|---|
| Medición | 5 frentes: la suite pasó de ~330 s a **677 s** (**×2,05**), y una prueba de latencia falló por carga |
| Cuándo | **2026-08-10**, en campo — **una sola vez, sin repetir** |
| **De qué suite** | **NO la de Atloos.** Es la de **ProgramadoMaxi2** (`Downloads/2026-08-10-programadomaxi2-…`): pytest, ~3 960 tests, 416,99 s al cierre |
| Máquina | **no consta en el registro**. El razonamiento que se construyó encima supone **8 núcleos** |
| Calidad del dato | **`[AR]` — autorreportado.** Lo reportó el propio agente que corrió los 5 frentes; nadie lo replicó |
| Qué se dedujo | «máximo 3 frentes», aplicado a **todos** los proyectos |

**Y ahí están sus tres grietas, las tres verificadas el 2026-08-16:**

1. **La medición no es de este repo.** El ×2,05 mide una suite de pytest con
   ~3 960 tests en otro proyecto. La suite de Atloos son 18 arneses seriales que
   hoy tardan **43 s**. Un techo deducido allí y escrito aquí **no es el mismo
   número**, y hasta ahora nada lo decía.
2. **Los 8 núcleos no son los de esta máquina.** `FLOREANO_LEGION` (Intel Core
   Ultra 9 275HX) tiene **24** — `os.cpu_count()` y `psutil.cpu_count()`
   coinciden. El presupuesto «3 × 2 workers + 2 reservados = 8» se escribió
   contra un tamaño de máquina que aquí no existe, y nadie lo comprobó.
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

⚠ Y una frase que había que retirar: `gobierno-vs-sdd.md` afirmaba que los
límites numéricos estaban **medidos en esta máquina**. No lo estaban — ni consta
cuál era la máquina, ni el tamaño supuesto coincide con el de esta. Queda
escrito aquí en vez de borrado, porque una afirmación retirada es más útil que
una ausencia: dice qué se creía y por qué dejó de creerse.

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
py -c "import os,psutil; print(os.cpu_count(), psutil.cpu_percent(interval=1))"
inicio=$(date +%s); py setup/scripts/run-tests.py > /tmp/f1.txt 2>&1; echo "exit=$?"   # [repo]
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
