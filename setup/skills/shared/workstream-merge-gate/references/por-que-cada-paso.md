# Por qué cada paso — las cicatrices, una por una

Ningún paso del gate es una buena práctica genérica. Cada uno está porque algo
concreto se coló. Esto es el registro, para que quitar un paso cueste lo que
debe costar.

## Paso 1 · el artefacto, no el reporte

**Dos fallos en un solo día**, ambos con el subagente reportando éxito:

- Uno **reportó un fichero que nunca escribió**. El reporte era coherente,
  detallado y falso.
- Otro reportó **23 arreglos y la suite en verde**, y **nunca commiteó**. El
  trabajo existía en su worktree y desapareció con él.

Ninguno mintió a propósito: un agente que termina su turno cree que terminó. Por
eso la comprobación es de máquina —hash, existencia del fichero, worktree
limpio— y no una pregunta.

> **El reporte no es el artefacto**, igual que el código de salida no es el
> estado. Son la misma ley aplicada a dos capas.

## Paso 2 · verde posterior al último commit

El orden importa y es contraintuitivo: un verde de hace veinte minutos parece
suficiente y no lo es, porque entre medias hubo commits. Lo que valida la suite
es **un árbol concreto**, no una rama.

Y **tests que el implementador no escribió ni editó en esa tarea**. Si los tocó,
antes de aceptar el verde van los 3 criterios del revisor
(`workstream-dispatch/references/revisor.md` §3):

1. ¿el test fijaba el borde exacto de lo que se cambió?
2. ¿perdió poder de discriminación (pasa ahora con más cosas que antes)?
3. ¿tocó dato de prueba o tocó lógica?

Un test relajado para que pase produce un verde perfectamente válido y
perfectamente inútil.

## Paso 4 · integración serializada

Paralelizar la *implementación* es barato; paralelizar la *validación* no. Con
varios agentes mergeando, el árbol que uno probó no es el que el otro integra, y
la suite de integración mide un estado que ya no existe.

**Paraleliza lo que quieras, pero la validación pasa por un cuello único.** Y
ese cuello mide también el coste: con 5 frentes en vez de 3, la suite pasó de
~330 s a **677 s (×2,05)**, se dijo que por contención de CPU — medido **una
vez**, el 2026-08-10, en OTRA máquina (`ProgramadoMaxi2`, que sí quedó
**anotada** en el reporte; su tamaño, no) y sin repetir, así que la causa es
la hipótesis de entonces y no un hecho. El número y su caducidad los gobierna
`workstream-dispatch`, en **su** `references/medir-el-techo.md` — no en esta
skill; aquí solo importa que paralelizar la validación se paga.

## Paso 5 · squash

El histórico de commits de un subagente es un diario de trabajo, no una
narración útil de qué cambió. El squash convierte el frente en una unidad
revertible con un mensaje que alguien puede leer en seis meses.

⚠ **Deuda conocida**: encadenar squashes sobre ramas hijas puede **resucitar
ficheros borrados**, y el gate manda squash. Está identificado y sin
procedimiento decidido — no lo parchees sobre la marcha.

## Paso 6 · confirmación humana

Es el paso que ninguna máquina puede poner: el hook `merge-gate-guard` bloquea
lo verificable, pero no puede preguntar. En la prueba deliberada del 2026-08-07,
`superpowers:finishing-a-development-branch` ganó el enrutado en 3 de 4
escenarios y **se colaron 2 merges a `main` sin OK humano**. Esa es la razón de
que esta skill exista en vez de usar aquella.

## Paso 7 · limpieza

Sin este paso se llega a **92 ramas remotas**, y bajarlas a 17 se comió una parte
de una sesión sin producir nada. El diagnóstico correcto no fue «paralelizamos de
más», sino **no haber decidido el destino de la rama al despacharla** — por eso
`workstream-dispatch` lo pide ahora en el propio despacho.

Detalle operativo: **tras un squash, `git branch -d` no reconoce la rama como
integrada**, porque sus commits no son ancestros de `main`. Hace falta `-D`, y
conviene saberlo antes de asustarse.
