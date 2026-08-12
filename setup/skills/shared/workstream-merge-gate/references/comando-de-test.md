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
