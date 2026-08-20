# 40 — Alta de AlphaDogs en el puente (SER8), con su corpus

**Fecha:** 2026-08-19 · **Estado:** BLOQUEADA, con los bloqueos medidos.
**Encargo:** la parte que no es nuestra va al Claude Code de AlphaDogs (§4).

> Qué se pidió: dar de alta `alphadogs` en el daemon **de la SER8** (el 24/7, el
> que contesta al móvil) **con su corpus** — el del Bibliotecario, no el
> briefing del vault (confirmado por el humano, 08-19).

---

## 1 · Lo que ya está, y no sirve todavía

- `alphadogs` **ya figura en el `projects.json` de la Legion**, con la ruta de
  Windows y **sin `test`**. Ese fichero es **por-máquina y está gitignorado**:
  no viaja. La SER8 tiene el suyo y ahí `alphadogs` no existe.
- La carpeta del vault **existe y está viva**: `10-Projects/alphadogs/` con
  `_PROJECT.md`, `ADRs/`, `bugs/`, `convenciones.md`, `sessions/`. El vault de
  la SER8 es un clon git normal, así que eso **sí llega solo**.
- El `CLAUDE.md` del repo declara `## Active Project: alphadogs` — la clave de
  `projects.json`, la carpeta del vault y el nombre que usa el hook del snapshot
  **casan**. Una cosa menos.

## 2 · Los cinco bloqueos, medidos

**B1 · El repo no está clonado en la SER8** (confirmado por el humano). Es un
repo **privado y ajeno** (`amillanlopez/AlphaDogs`, con más colaboradores). Una
caja headless no trae helper ni `gh`: la salida correcta es **clave SSH por
máquina**, revocable sola — no `credential.helper store`, que deja el token en
claro (misma lección que el alta de la SER8, README §382).

**B2 · El comando de test no puede funcionar en Linux, en ninguna de sus dos
formas.** AlphaDogs declara en `.claude/settings.json` (versionado, y el repo
**gana** sobre `projects.json`):

```
GATE_TEST_CMD = "C:/Users/jlflo/Documents/venvs/alphadogs/Scripts/python.exe -m pytest -q backend/tests"
```

- Tal cual: el primer token **no** está en `testcmd.LANZADORES` (`py`,
  `python3`, `python`), así que pasa intacto → `FileNotFoundError` en la SER8.
- Cambiarlo a `python3 -m pytest ...`: **peor**, porque entonces `testcmd.argv`
  **sí** lo sustituye — por `sys.executable`, que es el intérprete del venv **del
  puente** (`~/.local/share/claude-telegram/venv`). Ese venv no tiene
  `fastapi`, `sqlalchemy` ni `fastembed` → `ModuleNotFoundError`.

  > No es un fallo del resolutor: hace exactamente lo que dice
  > (`setup/telegram-bridge/testcmd.py`, función `argv`). Es que **un repo con
  > venv propio necesita un runner propio**, que es justo lo que esta casa
  > resolvió para sí con `setup/scripts/py setup/scripts/run-tests.py`.

  Sin comando válido, `/test` avisa y **`/merge` queda bloqueado por diseño** —
  justo en la máquina 24/7, que es donde vive el bot.

**B3 · El runner de AlphaDogs no está en la lista blanca.** `WRITE_TOOLS`
(`setup/telegram-bridge/tg_daemon.py:127`) nombra suites genéricas y **las dos
formas del runner de esta casa**. La lista **es blanca: lo que no está, no
corre**, y al otro lado del móvil no hay humano que apruebe un prompt — la
invocación se cuelga. El README lo deja dicho: *«Si enganchas otro proyecto cuyo
runner no sea `pytest` ni `npm test`, esto hay que repetirlo para él»*. La
entrada debe ser **estrecha** (el path exacto del runner, nunca `Bash(py:*)`), y
la vigila `setup/telegram-bridge/tests/test-perfil-bot.py`, que resuelve la
declaración con el **mismo** `testcmd.resolver` que usa `/test`. **Depende de
B2**: sin runner decidido no hay string que meter.

**B4 · El corpus no viaja por git y no cabe en un `scp` inocente.** El área de
ingesta local pesa **4,1 GB** (`rag_out_full_prod/`, con `chunks.jsonl` y sus
variantes) más 121 MB de `rag_out_latam/`, y las dos están **gitignoradas**
(`.gitignore:24`, patrón `rag_out*/`). Pero el corpus **vivo** no son esos
ficheros: son **286 436 chunks / 1 234 docs en PostgreSQL con pgvector**
(`halfvec`, `unaccent`, reranker ONNX local). Levantarlo en la SER8 no es copiar
una carpeta: es Postgres + extensiones + restore o re-ingesta + los modelos de
embedding.

> **Y hay una salida más barata que nadie ha evaluado**: el Bibliotecario v1
> **ya está desplegado y sirviendo**. Si esa instancia es alcanzable desde la
> SER8, *apuntar* vale más que *duplicar* 4 GB. Es la pregunta P4 del encargo.

**B5 · El alta abre una lectura de secretos que hoy nadie tapa.**
`secret_denies` (`setup/telegram-bridge/tg_daemon.py:179`) deniega por **ruta
absoluta** los `.env` del puente, `~/.ssh`, `~/.aws`, `~/.gnupg` y
`~/.config/gh` — y su propio docstring avisa de que **los globs no funcionan**
(`Read(**/.env)` dejó pasar la lectura, medido el 2026-08-01) y de que **la
lectura no tiene frontera de directorio en ningún modo**. El `backend/.env`
**del proyecto** no está en esa lista.

Con AlphaDogs dado de alta, el bot puede leer por ruta absoluta el `.env` que
guarda la clave de Anthropic, las credenciales de la BD de Azure y el secreto de
sesión del panel admin. La escritura sí está acotada (worktree + `acceptEdits` +
deny explícito sobre el repo real, `tg_daemon.py:1341`); **la lectura no**.

> No es un fallo nuevo: es un residual conocido que **este alta convierte en
> exposición concreta**, porque hasta hoy ningún proyecto enganchado guardaba
> credenciales de producción.

> ✅ **ARREGLADO el 2026-08-19**, rama `fix/deny-env-de-proyectos` (§3.1).

## 3 · Lo que sí se puede hacer sin desbloquear nada

1. ✅ **B5, hecho.** `project_env_denies()` recorre los `path` de
   `projects.json` y emite `<dir><sep>.env**` por la raíz y por cada directorio
   con ficheros de entorno; `main()` carga los proyectos **antes** de calcular
   el deny (calculado antes, la lista llegaba vacía). Arnés
   `tests/test-deny-env-de-proyectos.py`: **12 casos**, las dos plataformas y
   cuatro mutaciones — el separador ya mordió una vez (auditoría 31, H1). Suite
   **38/38 verde**. Medido sobre los 4 proyectos de esta máquina, uno con 4,1 GB
   de corpus: **0,01 s y 9 reglas**, incluidas `frontend/.env` de AlphaDogs y
   `appweb/.env` de TT1, que nadie había nombrado.

   **La forma de la regla fue la decisión**: prefijo + `**` es la única
   verificada en campo, así que un `.env.prod` creado después del arranque queda
   cubierto sin reiniciar. Residual que queda: más hondo que `ENV_MAX_DEPTH` (3),
   o en un directorio nuevo, no se cubre hasta el siguiente arranque.
2. El **`codebase-map.md` curado** de `10-Projects/alphadogs/` — hoy **no
   existe**, ni él ni el snapshot, así que el briefing que inyecta el daemon
   (`vaultio.py:126`, `tg_daemon.py:1566`) le daría al bot solo el `_PROJECT.md`
   y la línea *«snapshot ausente»*. Lo escribe quien conoce ese codebase (P6).
3. El **hook del snapshot**, que tiene un choque real (✅ la receta ya lo dice:
   `graphify-al-enganchar.md` mandaba copiar encima **sin avisar de que ahí ya
   vive otro** — corregido el 08-19, con la tabla de qué hace cada uno): el
   `.git/hooks/post-commit` de AlphaDogs lo ocupa **graphify**, y el nuestro
   (`setup/hooks/git-post-commit-graph-report.sh`) se instala en ese mismo
   fichero. El nuestro **también** reconstruye con graphify (`graphify update .
   --no-cluster` + `cluster-only`), pero **en primer plano** (~5,6 s por commit),
   mientras que el de graphify lanza la reconstrucción **desacoplada**. Sustituir
   uno por otro cambia el coste de cada commit de AlphaDogs: **es decisión del
   dueño del repo**, no nuestra.

## 4 · Encargo para el Claude Code de AlphaDogs

Contexto que necesita saber de nuestro lado, y que no puede adivinar:

- El bot corre `/test` **como argv, SIN shell**: nada de `&&`, `||`, `|`, `;`.
- La lista de herramientas **es blanca**; lo que no esté declarado, no corre, y
  no hay humano que apruebe un permiso al otro lado.
- El agente trabaja en un **worktree**, no en el repo real, y tiene **denegado**
  escribir en el repo real. `git commit`, `push` y `merge` los ejecuta el
  daemon, nunca el agente.
- Sin comando de test válido, **`/merge` queda bloqueado**: no hay verde posible.

**P1 · Runner portable.** ¿Cuál es el comando de test de AlphaDogs que funciona
en Ubuntu Server 24.04 LTS headless resolviendo **su propio venv por máquina**? Lo que aquí
funcionó fue un resolutor en el repo (`scripts/py`) invocado como un solo
ejecutable con argumentos. Hace falta **el string exacto** que quedará en
`GATE_TEST_CMD`, para poder meterlo estrecho en la lista blanca.

**P2 · Verde sin base de datos.** De los **2 071** tests, ¿cuántos pasan sin
Postgres, sin Azure y sin red? Si el verde exige BD viva, el alta arrastra
Postgres + pgvector a la SER8 **solo para poder mergear**. Si hay un subconjunto
honesto que corre en seco, decid **cuál** y si ese es el verde que debe exigir
`/merge` — un verde que no ejerce nada ya nos costó caro (`compileall` en
atloos).

**P3 · Qué es «el corpus», en términos de despliegue.** Esquema y tablas
(`rag.chunks`...), versiones de extensión (pgvector/`halfvec`, `unaccent`),
modelo de embedding y dimensiones, **tamaño real en disco** del dump, y qué
modelos hay que descargar (fastembed E5-large, reranker ONNX) con su peso.

**P4 · ¿Duplicar o apuntar?** El Bibliotecario v1 ya está desplegado y
sirviendo. ¿Es alcanzable esa instancia desde otra máquina, o está atada a su
VM? Y la BD de farma en Azure (read-only): ¿acepta una IP nueva o está detrás de
firewall por IP? **Si se puede apuntar, la SER8 no necesita los 4 GB.**

**P5 · Secretos en la SER8.** Qué claves mínimas necesita `backend/.env` para
que el subconjunto de P2 pase, y cuáles **no** deben existir en esa máquina.

**P6 · `codebase-map.md` curado** para `10-Projects/alphadogs/`: ~2 000
caracteres útiles (es el presupuesto que lee `vaultio.MAP_BUDGET`), orientado a
*por dónde se entra al código*, con `updated:` en el frontmatter — el briefing
antepone esa fecha para que el bot pueda pesar la edad de lo que lee.

**P7 · El `post-commit`.** ¿Aceptáis cambiar el hook de graphify por el nuestro
(§3.3), sabiendo que pasa a ser síncrono (~5,6 s/commit) y que a cambio el vault
mantiene el snapshot fresco? Si no, decidlo y el briefing se queda sin snapshot
a propósito, no por olvido.

---

## 5 · Orden de ejecución cuando lleguen las respuestas

1. P1 → fijar `GATE_TEST_CMD` en el repo de AlphaDogs (versionado).
2. P1 → entrada estrecha en `WRITE_TOOLS` + verde de `tests/test-perfil-bot.py`.
3. B5 → deny de los `.env` de los proyectos, con arnés de las dos plataformas.
4. B1 → clave SSH de la SER8 + clon.
5. P2/P3/P4 → decidir **apuntar** o **duplicar**; solo entonces Postgres.
6. `projects.json` **de la SER8**: la entrada `alphadogs` con su ruta Linux.
7. P6/P7 → `codebase-map.md` y el hook del snapshot.
8. Prueba real: `/p alphadogs` → `/test` → verde → `/merge` con OK humano.
