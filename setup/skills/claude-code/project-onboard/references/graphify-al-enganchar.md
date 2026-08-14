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
cp setup/hooks/git-post-commit-graph-report.sh <repo>/.git/hooks/post-commit
chmod +x <repo>/.git/hooks/post-commit
```

⚠ Escribe `codebase-map-snapshot.md`, **nunca el `codebase-map.md` curado**
(RFD 10 C2).

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
