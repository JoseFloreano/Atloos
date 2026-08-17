# El comando de test declarado — sin él no hay verde posible

## Dónde se declara

En `.claude/settings.json` del proyecto, bajo `env.GATE_TEST_CMD`. El fichero
está **versionado**, así que viaja entre máquinas y se ve en el diff — que es
justo lo que no pasaba cuando el comando vivía en la cabeza de quien mergeaba.

```json
{ "env": { "GATE_TEST_CMD": "py setup/scripts/run-tests.py" } }
```

## La forma: argv, no shell

Debe ser **un ejecutable con sus argumentos**, y nada más. **Sin `&&`, sin
pipes, sin redirecciones, sin `;`.**

El motivo es concreto: el `/test` del puente Telegram corre el comando como
`argv` sin pasar por un shell, así que un `&&` no encadena nada — se le entrega
al primer ejecutable como si fuera un argumento más, y falla de una forma que no
se parece a un test roto. Si necesitas encadenar, el sitio correcto es un script
del repo (como `run-tests.py`), que además queda versionado y auditable.

## ⚠ Y tiene que VIAJAR: el caso del worktree

Esta sección faltaba entera, y su ausencia costó una jornada. El sprint 3 decidió
*«se aprovisiona el worktree; el gate corre donde trabaja el frente»* — pero este
fichero **no mencionaba la palabra worktree ni una sola vez**, así que la orden se
contradecía consigo misma: mandaba correr el gate en un sitio donde el comando
declarado no arrancaba.

En campo el comando era `backend\.venv\Scripts\python.exe …`, y **`.venv` no está
en git**. En el checkout principal funciona; en un worktree recién creado no
existe ese intérprete y el gate no puede ni empezar.

> **Un intérprete relativo a un `.venv` que no viaja no es un comando declarado:
> es un comando que solo funciona en una máquina y en un directorio.**

### Cómo se declara uno que sí viaje

Por orden de preferencia:

1. **El intérprete que ya está corriendo.** Un `pytest -q` o un
   `<lanzador> setup/scripts/run-tests.py` [repo] usa el intérprete del `PATH`,
   que existe en cualquier árbol. Es la forma que este repo usa, y por eso su
   gate corre en cualquier worktree.

   > ⚠ **El lanzador escrito es una semilla, no un requisito** (sprint 11). Este
   > repo declara `py setup/scripts/run-tests.py` [repo] (Windows: ese lanzador
   > no existe en Linux) — pero `gate-test.py` cambia el primer token por el que
   > lo está ejecutando antes de lanzarlo, así que el MISMO comando versionado
   > corre en Windows y en Linux. Solo se toca el primer token y solo si es un
   > lanzador conocido (`py`, `python3`, `python`): un `pytest -q` o un
   > `npm test` pasan intactos. Por eso el literal no se cambió — cambiarlo a
   > `setup/scripts/py …` habría roto Windows, donde `shell=True` es cmd.exe y
   > no sabe lanzar un script de bash.

2. **Un script del repo que se aprovisione solo.** Si hace falta un entorno,
   que lo cree el propio script —el `-m venv .venv && pip install -r req.txt`
   de siempre, con `py` en Windows y `python3` en Linux— antes de correr la
   suite. Versionado, auditable, y el mismo en los dos árboles.
3. **Nunca una ruta absoluta ni relativa a algo no versionado.** `.venv/`,
   `node_modules/`, un dataset, una `db/*.sqlite`: si no está en git, no puede
   estar en el comando.

### Cuando el proyecto NO puede

Hay proyectos que de verdad necesitan un entorno pesado. Entonces:

- **El manifiesto de lo que git no versiona es parte del despacho**, con ruta,
  tamaño y cómo obtenerlo — bloque 2 de `shared:workstream-dispatch`, que ya lo
  exige. El frente aprovisiona su worktree ANTES de la primera corrida.
- **Y se dice en el `## Comando de test`**, en una línea al lado del bloque:
  *«requiere `.venv`; créalo con `<comando>` antes de gatear»*. Un requisito
  escrito se cumple; uno implícito se paga tres veces, que es lo que pasó.

⚠ **Lo que NO es la salida: copiar la evidencia entre árboles.** El campo lo
rechazó y tenía razón — copiar un `gate-verde.json` de un árbol a otro es
fabricar el verde a mano, que es exactamente lo que la compuerta existe para
impedir. **No hace falta**: desde el 2026-08-14 la evidencia vive en el
directorio git **común** (`git rev-parse --git-common-dir`), así que un verde
producido en un worktree lo ve quien integra desde el principal, sin copiar nada
y sin relajar nada — sigue llevando `branch` y `sha`, y un verde de otra rama
sigue sin valer.

## Manda sobre `projects.json`

El comando lo declara **el repo**, no el registro del puente. Un proyecto sabe
cómo se prueba a sí mismo; el daemon solo lo ejecuta. Si `projects.json` trae
otra cosa, gana lo que dice el repo.

## Si no hay comando declarado

**No hay verde posible y no se mergea.** No es un tecnicismo: sin comando no
existe la evidencia que el hook `merge-gate-guard` exige, así que el bloqueo es
automático.

Dos salidas legítimas, y ninguna es saltarse el gate:

1. **Redefinir el verde** para ese proyecto. No todo repo tiene tests: un build
   que compila, un linter en cero, un script de humo. Lo que sea, declarado en
   `GATE_TEST_CMD`, es infinitamente mejor que una afirmación.
2. **Reconocer que el patrón no aplica aquí** y decirlo por escrito. Un repo de
   notas no necesita un gate de merge. Lo que no vale es fingir que lo tiene.

## Por qué esto es un requisito y no un consejo

El 2026-08-09 el gate solo pasó **encadenando los arneses a mano con `--cmd`**,
porque este repo no tenía comando declarado. Todo merge futuro chocaba con el
mismo muro, y la única forma de pasarlo era un paso manual distinto cada vez —
es decir, no reproducible, es decir, no era evidencia.
