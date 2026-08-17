---
title: Inventario de portabilidad a Linux — por clases, con la columna que importa
fecha: 2026-08-17
sprint: 11
tipo: inventario
estado: medido
maquinas: [Legion (Windows 11), floreano-server (Ubuntu 24.04)]
---

# 28 · Inventario de portabilidad — el diagnóstico antes que el arreglo

**Medido, no recordado.** Todo lo de aquí sale de correr comandos en las dos
máquinas el 2026-08-16/17: la Legion (Windows 11, Git Bash, Python 3.12.10) y
`floreano-server` (Ubuntu 24.04, Linux 6.8.0-137, Python 3.12.3, 16 núcleos,
50,8 GiB de RAM visibles).

**La columna que vale es la última.** No todo lo que menciona Windows está roto,
y confundir «menciona Windows» con «no funciona en Linux» infla el trabajo.
El resultado más útil de este inventario es justamente **cuánto de lo que
parecía roto no lo estaba**.

---

## Resumen: qué rompía de verdad

| Clase | Sitios mirados | **Rompen** | Cosméticos / correctos |
|---|---:|---:|---|
| 1 · Instaladores | 9 scripts | **2** | 7 |
| 2 · Invocación de Python | ~90 sitios | **~45** | el resto, prosa o etiquetado |
| 3 · Rutas y variables | 28 sitios | **0** | 28 |
| 4 · Permisos y allowlists | 4 sitios | **2** | 2 |

> **El titular:** la clase 3 —la que parecía la más gorda, con `%LOCALAPPDATA%`
> por todas partes— **no rompía nada**. Y la clase 4, que parecía cosmética,
> esconde los dos fallos más graves del repo, porque **fallan abiertos y en
> silencio**.

---

## Clase 1 · Instaladores

`sync-hooks` era **el único par asimétrico del repo**. Todo lo demás ya tenía
sus dos versiones.

| Fichero | Línea | ¿Rompe en Linux? | Detalle |
|---|---|---|---|
| `setup/sync-hooks.ps1` | — | **ROMPÍA** | Único instalador de hooks, y solo en PowerShell. **En la SER8 no existía `~/.claude/hooks/`**: verificado el 16-08 antes de tocar nada. Cero hooks, `settings.json` con solo `{"theme": "dark-ansi"}` |
| `setup/setup-new-machine.sh` | 237-241 | **ROMPÍA** | Llamaba a `sync-skills.sh` y **a ningún hook**. Una máquina Linux salía del bootstrap con las skills puestas y sin capa 3 |
| `setup/sync-skills.{sh,ps1}` | — | no | Par completo |
| `setup/backup-graph.{sh,ps1}` | — | no | Par completo |
| `setup/restore-graph.{sh,ps1}` | — | no | Par completo |
| `setup/setup-new-machine.{sh,ps1}` | — | no | Par completo |
| `setup/hooks/git-post-commit-graph-report.sh` | 113 | no | Normaliza los backslashes de `%LOCALAPPDATA%` con `tr` **a propósito**. Es código que ya pensó en esto |

**Consecuencia literal, y es la frase que justifica el sprint:** el servidor que
va a correr sin vigilancia humana era el único sin `merge-gate-guard`,
`goal-evidence-guard`, `check-vault-updated`, `memory-flush` ni
`mark-code-dirty`. No es una carencia de portabilidad — es que el gate no
existía en la máquina donde más falta hace.

*(Cerrado en S2: `setup/sync-hooks.sh` + `setup/scripts/wire-hooks.py`, con la
lista en `setup/hooks/hooks-map.json` como fuente única y
`test-sync-hooks-paridad.py` vigilando que los dos envoltorios registren lo
mismo. Demostrado en la SER8: merge a protegida sin evidencia → exit 2.)*

---

## Clase 2 · Invocación de Python

**Tu estimación se queda corta: no son ~10 ficheros, son ~45 sitios en 44
ficheros.** Y lo importante no es el número, es que **la salida obvia también
estaba rota**:

| | `py` | `python3` | `python` |
|---|---|---|---|
| **Windows** | Python 3.12.10 **real** | **existe y MIENTE** — alias de la Store: «Python was not found» | igual, miente |
| **SER8** | **no existe** | Python 3.12.3 real | Python 3.12.3 real |

La casilla del medio es la trampa: en Windows `command -v python3` **dice que
sí**. Un resolutor que se fíe de que el comando exista elige el stub. *«El
comando existe» no es evidencia de que ejecute* — y ese es el patrón que esta
casa persigue en los checks, apareciendo aquí en el `PATH`.

| Zona | Sitios | ¿Rompe en Linux? | Qué se hizo |
|---|---:|---|---|
| `setup/skills/**` (órdenes que el agente EJECUTA) | 13 ficheros | **ROMPÍA** | → `setup/scripts/py` \| `"$HOME/.claude/scripts/py"` |
| Docstrings `Uso:` de los 22 arneses | 25 ficheros | **ROMPÍA** (se copian y pegan) | → `setup/scripts/py` |
| `README.md`, `docs/**`, `feedback/**` | 6 ficheros | **ROMPÍA** | → `setup/scripts/py` |
| `setup/hooks/README.md` | 5 líneas | no | Bloque ` ```powershell ` **etiquetado**: correcto. Se le añadió el bloque `bash` equivalente |
| `setup/hooks/merge-gate-guard.py` | 532, 678 | **ROMPÍA, y de la peor forma** | El gate bloqueaba con exit 2 y **acto seguido mandaba correr `py …`, que en Linux no existe**. Un bloqueo cuyo remedio no se puede seguir es medio bloqueo. → `LANZADOR = "py" if os.name == "nt" else "python3"` |
| `.claude/settings.json` → `GATE_TEST_CMD` | 3 | **ROMPÍA** | **No se cambió el literal**: corre con `shell=True`, que en Windows es cmd.exe y no sabe lanzar un script de bash. Se arregló en `gate-test.py`, que cambia el primer token por el intérprete que ya lo ejecuta |
| `setup/telegram-bridge/**` | 26 | **ROMPE — SIN ARREGLAR** | Fuera de alcance por orden explícita («no toques el daemon»). Ver deuda abajo |
| Fixtures de laboratorio (`test-skill-paths`, `test-testcmd`, …) | 8 | no | Son datos que deben disparar el detector; reescribirlos lo apagaba |

### La decisión, y por qué resuelve los dos lados

**No hay un literal portable, así que la respuesta es resolver, no elegir.**

| Dónde | Forma |
|---|---|
| Dentro de este repo | `setup/scripts/py <script>` |
| Desde cualquier otro proyecto (skills) | `"$HOME/.claude/scripts/py" <script>` |
| Dentro de un `.py` que ya corre | `sys.executable` (ya lo hacía `run-tests.py:58`) |
| Un hook, que no puede pagar un subproceso | `"py" if os.name == "nt" else "python3"` |
| `GATE_TEST_CMD` | lanzador cualquiera; `gate-test.py` lo normaliza |

`setup/scripts/py` **ejecuta** cada candidato (`-c 'print("ok")'`) antes de
elegirlo. Es lo único que distingue el lanzador real del stub que miente.
Verificado en las dos: elige `py` en la Legion y `python3` en la SER8.

Que no vuelva: `setup/scripts/tests/test-comandos-portables.py`, con su mutación
(un `py …` a secas se caza; el resolutor no se señala; un par etiquetado por
plataforma se respeta; y una etiqueta a 5 líneas **no** exime, para que nombrar
«Windows» una vez arriba no silencie el fichero entero).

---

## Clase 3 · Rutas y variables — **la sorpresa: no rompe nada**

Esta es la clase que el encargo daba por rota y **no lo está**. Los tres
`%LOCALAPPDATA%` no gobiernan una raíz: gobiernan **tres distintas**, y las tres
tienen fallback de Unix escrito a mano.

| Fichero | Línea | Qué gobierna | ¿Rompe en Linux? |
|---|---|---|---|
| `setup/telegram-bridge/gitops.py` | 38 | Raíz de **worktrees** | **No.** `or os.path.join("~", ".local", "share")` |
| `setup/telegram-bridge/notify_telegram.py` | 59 | Ruta del **`.env`** | **No.** Segunda opción `~/.config/claude-telegram/.env`, comentada `# Unix` |
| `setup/telegram-bridge/tg_daemon.py` | 156 | Dir del **perfil bot** | **No.** `or Path.home()`. Queda en `~/claude-tg-profile` (sin punto, no-XDG): cosmético |
| `setup/*.ps1` (6 sitios) | varias | `$env:USERPROFILE`, `$env:LOCALAPPDATA` | **No.** Son los scripts de Windows; su gemelo `.sh` existe |
| `git-post-commit-graph-report.sh` | 113, 122 | `LOCALAPPDATA`, `OneDrive`, `USERPROFILE` | **No.** Normaliza y encadena fallbacks |
| `test-graph-report-hook.py` | 128 | Limpia el env del laboratorio | **No.** Correcto |
| Menciones `C:\…` en comentarios y docstrings | 8 | — | **No.** Explican un caso de Windows |

> **Lo que este hallazgo enseña:** el código del puente ya estaba escrito
> pensando en Unix. Lo que no estaba pensado era **el separador**, que es la
> clase 4.

---

## Clase 4 · Permisos y allowlists — **los dos fallos graves**

Aquí está lo peor del inventario, y no se ve mirando variables de entorno: se ve
mirando **cómo se construye la cadena**.

| Fichero | Línea | ¿Rompe en Linux? | Por qué importa |
|---|---|---|---|
| `setup/telegram-bridge/tg_daemon.py` | **111** | **ROMPE, EN SILENCIO** | `reglas.append(f"Read({d}\\**)")` — separador `\` **hardcodeado**. En Linux `d` es `/home/floreano/.ssh` y la regla sale `Read(/home/floreano/.ssh\**)`, que **no casa con nada**. Son las denegaciones de **secretos** (`.ssh`, `.aws`, `.gnupg`, `.config/gh`, los `.env`). No fallan cerrado: **fallan abiertas** |
| `setup/telegram-bridge/tg_daemon.py` | **1229** | **ROMPE, EN SILENCIO** | `deny += f",Write({repo_path}\\**),Edit({repo_path}\\**)"` — misma causa. Es la **segunda barrera del aislamiento de T2**, la que impide que un frente en modo escritura toque el árbol del usuario. En Linux se evapora |
| `.claude/settings.json` | 51 | no | `Bash(py "C:/…/scratchpad/merge_hooks.py")` — ruta absoluta de un **scratchpad muerto** de una sesión del 08-14. Basura, no rotura: hoy no concede nada porque el fichero ya no existe. **Debe borrarse** |
| `setup/telegram-bridge/tg_daemon.py` | 100-108 | no | El comentario que **ya documenta** que los glob no funcionan y que por eso se calculan rutas absolutas. El razonamiento es correcto; lo que no se pensó fue el separador |

> ⚠ **Estos dos NO se han arreglado**, por la orden explícita de no tocar el
> daemon en este sprint. Quedan aquí escritos, con fichero y línea, y repetidos
> en el mapa de S4. **Son el hallazgo que hay que atender primero cuando el
> puente se lleve a la SER8** — porque el modo escritura del bot en Linux hoy
> corre con una barrera menos y sin decirlo.

---

## Lo que queda pendiente, y de quién es

| Pendiente | Dónde | Por qué no aquí |
|---|---|---|
| Separadores `\` en las allowlists | `tg_daemon.py:111, 1229` | Prohibido tocar el daemon este sprint |
| `py` en el puente (26 sitios) | `setup/telegram-bridge/**`, `projects.example.json:7` | Ídem. Incluye `"test": "py -m pytest -q"`, que en Linux no corre |
| Entrada muerta de allowlist | `.claude/settings.json:51` | S1 es diagnóstico; borrar es un cambio |
| `test-suelo-python.py` no puede dar verde en la SER8 | — | No hay Python 3.10 en Ubuntu 24.04. Ver «fallos del entorno» del reporte |

---

## Cómo se reproduce este inventario

```bash
setup/scripts/py setup/scripts/tests/test-comandos-portables.py   # clase 2, y falla si vuelve
setup/scripts/py setup/scripts/tests/test-sync-hooks-paridad.py   # clase 1
git grep -n -E 'LOCALAPPDATA|APPDATA|USERPROFILE' -- '*.py' '*.sh' '*.ps1'   # clase 3
git grep -n -E '(Read|Bash|Edit|Write)\([^)]*\\\\\*\*' -- '*.py'             # clase 4
```

Las clases 1 y 2 tienen arnés, así que se vigilan solas. Las clases 3 y 4 **no**:
se miran con `git grep` y a mano. Que la 4 no tenga arnés es exactamente por qué
sus dos fallos llevaban ahí desde que se escribió el daemon.
