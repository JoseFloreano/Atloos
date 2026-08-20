# Graphify al enganchar un repo — qué instalar y qué borrar

Detalle del paso 7. Graphify es **externo**: este setup no lo gestiona. Lo que
sigue son cosas aprendidas en campo que su documentación no dice.

## Antes de correr `graphify claude install`, los cuatro avisos

Están enteros en `setup/hooks/README.md` (sección «Graphify»). En corto:

1. **Registra hooks `PreToolUse` que no documenta**, además de la sección del
   `CLAUDE.md`. Inyectan una instrucción imperativa en **cada búsqueda de cada
   sesión** del repo. Con agentes en paralelo eso es desviarles el método a
   media tarea: **con agentes en paralelo, instala SOLO la sección.**
2. **Es una primera pasada con omisiones garantizadas**, no una respuesta:
   5 de 9 sitios en 1,7 s sobre la pregunta más cara de la jornada, **con los 2
   decisivos fuera**, y 49 de 65 `loc=` apuntando a `L1` (el fichero, no la
   línea). Confirma siempre con `Read`.
3. **Su reconstrucción cuesta**: son **dos** hooks de git
   (`.git/hooks/post-checkout` y `.git/hooks/post-commit`), compiten por RAM con
   la suite y con los frentes. En una jornada con gates, quita el de checkout.
4. **Coste de reputación**: el hook tarda **5,6 s** y la consulta **0,5 s**. Lo
   lento no es lo que se evita, pero la resistencia se transfiere igual.

El hook nuestro, que mantiene el snapshot del vault fresco:

```bash
# MIRA PRIMERO si ya hay uno. `graphify hook install` deja el SUYO justo ahí.
cat <repo>/.git/hooks/post-commit 2>/dev/null | head -5
cp setup/hooks/git-post-commit-graph-report.sh <repo>/.git/hooks/post-commit
chmod +x <repo>/.git/hooks/post-commit
```

⚠ **Ese `cp` pisa un hook ajeno, y `graphify hook install` pone el suyo en ese
mismo fichero** (aviso 3 de arriba: son dos hooks de git, y uno vive en
`.git/hooks/post-commit`). Git admite **uno solo** por repo, así que copiar a
ciegas **borra en silencio** la reconstrucción automática del grafo — y no se
nota hasta que alguien pregunta por código reciente y el grafo responde por
símbolos viejos. Encontrado en `alphadogs` el 2026-08-19, con el hook de
graphify vivo y esta receta mandando pisarlo.

Los dos hacen lo mismo y no igual, y por eso la elección es real:

|  | hook de graphify | el nuestro |
|---|---|---|
| Reconstruye el grafo | sí, **desacoplado** (el commit vuelve enseguida) | sí, **en primer plano** (~5,6 s por commit) |
| Mantiene `codebase-map-snapshot.md` en el vault | **no** | sí |
| Si la reconstrucción falla | lo deja en su log | **no re-sella**: avisa de que el grafo es viejo |

Si el repo es ajeno o hace muchos commits, **pregunta a su dueño antes**: le
estás cambiando el coste de cada commit. Si decide quedarse con el de graphify,
el briefing del bot se queda sin snapshot **a propósito** — que es distinto de
por olvido, y así hay que decirlo en su `_PROJECT.md`.

⚠ Escribe `codebase-map-snapshot.md`, **nunca el `codebase-map.md` curado**
(RFD 10 C2).

## Dos banderas que no hacen lo que su nombre sugiere

Medido en campo el 2026-08-01 y reconfirmado el 08-16. **No está en su
documentación**, y las dos fallan en silencio: no dan error, hacen otra cosa.

1. **`graphify update` sin `--force` puede NO sobrescribir.** Si la
   reconstrucción sale con **menos nodos** que el grafo que ya hay, se planta y
   deja el viejo. La intención es no destruir un grafo bueno con una pasada
   mala; el efecto práctico es que **borrar código y reindexar te deja el grafo
   de antes**, respondiendo por símbolos que ya no existen. Y el comando termina
   sin quejarse, así que la única señal es el conteo. Después de una poda,
   `--force`.

2. **`--code-only` es bandera de `graphify extract`, no de la invocación por
   defecto.** Ponerla donde no va no la aplica: el comando corre igualmente,
   indexando todo, y tú te quedas creyendo que acotaste el alcance.

> El patrón de las dos es el mismo, y es el que hace que valga la pena
> escribirlas: **una bandera que se ignora sin avisar es peor que una que
> falla.** El conteo de nodos es lo único que las delata — mira siempre el
> `N/N archivos, N nodos` que imprime.

## Y lo que hay que BORRAR: la línea vieja

`graphify claude install` deja en el `CLAUDE.md` su propia línea:

> *"For codebase questions, first run `graphify query` to explore."*

**Bórrala.** Dice QUÉ y no dice CUÁNDO, y por eso no se dispara: `graphify:
no-usado` en **4 jornadas de 4** con la herramienta instalada y al día. La
instrucción que la sustituye —la que nombra un momento reconocible, *«antes de
tu primer `grep` de exploración en una sesión»*— **ya viaja en el snippet del
paso 5**, así que un proyecto recién enganchado la tiene sin que nadie haga
nada.

Por eso este paso ya **no es la vía** por la que llega el disparador: es solo el
**parche** para un repo que ya arrastra la línea vieja. Dejarla en pie mantiene
viva la mala instrucción, que es la que el agente lee de verdad.

Lo comprueba `test-claude-md-drift.py`, que la caza **por su nombre** para que
el hallazgo diga qué borrar y no solo qué añadir.
