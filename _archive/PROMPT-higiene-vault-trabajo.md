# Prompt — Reestructurar el vault del trabajo (local) con el patrón del RFD 09

> **Qué es esto:** un prompt para pasárselo a un agente (Claude Code) que tenga
> a mano el repo `ClaudeSetup`. Adapta al vault del trabajo — **local, sin
> OneDrive** — la higiene de contexto que se implementó en el vault personal el
> 2026-08-01.
>
> **Cómo usarlo:** abre una sesión en el vault del trabajo (o en el repo que lo
> acompañe), pega todo lo que hay bajo la línea, y sustituye los `<...>`.
>
> **Por qué está archivado aquí:** es un derivado del RFD 09, no parte del
> setup. Vive en `_archive/` para no contaminar `docs/`.

---

Vas a reestructurar un vault de Obsidian **del trabajo** aplicando un patrón de
higiene de contexto que ya se implementó y auditó en otro vault. No es una
migración mecánica: el vault de origen vive en OneDrive y varias de sus
decisiones existen **por eso**. El del trabajo es completamente local, así que
parte de lo que verás no aplica, y hay cosas que allí eran caras y aquí son
gratis.

## Lo que tienes a mano

El repo `ClaudeSetup` en `<RUTA-AL-REPO>`. Léelo en este orden y no más:

1. `docs/arquitectura-memoria/09-RFD-HIGIENE-VAULT.md` — el diseño y, sobre todo,
   **por qué** cada decisión. Presta atención a §3.0 (las tres capas), §4
   (alternativas rechazadas, con sus umbrales) y §8 (riesgos).
2. `setup/scripts/adr-index.py` — el generador del índice. Es el único código.
3. `setup/skills/shared/{adr-writer,session-close,design-doc-harvest}/SKILL.md` y
   `setup/skills/claude-code/project-resume/SKILL.md` — cómo se cablearon las
   convenciones al flujo de trabajo.

El vault del trabajo está en `<RUTA-AL-VAULT>`.

## El problema que resuelve, en una frase

Una sesión de Claude Code leía ~36 KB del vault al arrancar, y el 39% de su
archivo principal era historial acumulado que nadie volvía a leer. El resultado
tras la reestructuración: 7 861 B de suelo (13-16 KB reales), `_PROJECT.md` de
188 a 106 líneas, y ninguna nota perdida.

**No copies esos números.** Mide los del vault del trabajo: son tu línea base y
tu criterio de éxito.

## Lo que SÍ transfiere (el patrón)

- **Tres capas con caducidad distinta.** Durable (decisiones, convenciones,
  bugs con causa raíz) · episódico (qué pasó en una sesión) · andamiaje (specs,
  planes, RFDs). Cada capa tiene un destino y **un final**. Todo lo demás del
  diseño se deriva de esta tabla.
- **El archivo de estado describe el presente, no la historia.** Esqueleto fijo,
  tope de líneas, y el historial rota a `sessions/`. Prohibido acumular
  secciones tipo "Hecho".
- **Un índice generado se lee al arrancar, en vez de los documentos enteros.**
  Una línea por decisión con un `summary` de una frase; el documento completo se
  abre solo cuando la tarea lo toca. Es recuperación just-in-time.
- **Frontmatter uniforme y legible por máquina.** Un solo vocabulario de
  `status`. Si una auditoría busca `status: accepted`, un documento en otro
  idioma o con otra clave es invisible para ella.
- **Ciclo de vida del andamiaje**, con una regla que se descubrió a base de
  fallos: **redirigir las referencias entrantes ANTES de borrar**. "Git conserva
  la historia" es cierto para el contenido y falso para los enlaces que apuntan
  al archivo.
- **Enforcement blando y su razón.** El tope es convención: la skill de cierre
  avisa, la auditoría periódica reporta reincidencia. No un hook. Un aviso que
  salta cuando no toca entrena a ignorarlo.

## Lo que NO transfiere (y por qué) — léelo antes de copiar nada

| Del vault personal | En el del trabajo |
|---|---|
| `.git` fuera del vault con `--separate-git-dir` | **Innecesario.** Ese truco existe porque OneDrive corrompe `.git` al sincronizar. En local, un repo git normal dentro del vault está bien. |
| "Los mtime no son fiables, usa la fecha del frontmatter" | **Aquí los mtime SÍ son fiables.** Puedes usarlos. Aun así, la fecha del frontmatter sigue siendo más portable y sobrevive a copias; decide tú, pero deja escrito el porqué. |
| Ruta absoluta al script anclada en `$HOME/OneDrive/...` | **Hay que reapuntarla** a donde viva `ClaudeSetup` en esta máquina. Si no, el índice no se genera nunca y todo el esquema queda inerte — este fallo exacto llegó hasta la revisión final allí. |
| Mirror de skills + `sync-skills.ps1` + zip manual para Cowork | Solo si el equipo del trabajo usa el mismo montaje. Si no, ignóralo entero. |
| Manifest escrito con BOM UTF-8 | Detalle de la sincronización multi-laptop. Probablemente irrelevante. |
| Los hooks anti-drift | Ya soportan vault local: buscan `$HOME/DevSetup/ObsidianVault/10-Projects/<proyecto>/_PROJECT.md` sin necesidad de OneDrive (ver `find_vault_project` en `setup/hooks/check-vault-updated.py`). Instalarlos es **opcional** y va aparte de esta reestructuración. |

Y una advertencia estructural: **no asumas que el vault del trabajo usa PARA ni
`10-Projects/`.** Puede estar organizado de otra forma, o no estarlo. El patrón
es el de las tres capas; la carpetería es lo de menos y se adapta a lo que ya
haya.

## Reglas duras

1. **Es material de trabajo.** No lo publiques, no lo mandes a ningún servicio
   externo, no lo copies al repo personal ni a ningún artefacto compartido. Si
   algo parece confidencial (clientes, credenciales, datos de personas), no lo
   muevas de sitio sin preguntar.
2. **Nada se borra. El contenido se mueve.** Un bloque solo desaparece de su
   origen cuando has **verificado** que llegó a su destino.
3. **Verifica antes de reescribir, nunca después.** Si reescribes primero y la
   verificación falla, el contenido ya no está.
4. **Punto de retorno primero.** Si el vault tiene git, commit antes de tocar
   nada y anota el sha. Si no lo tiene, haz una copia de la carpeta y dilo.
5. **Interpretación**: si el RFD y lo que ves en el vault del trabajo se
   contradicen, gana el vault del trabajo. El RFD describe otro sitio.

## Cómo proceder

### Fase 1 — Diagnóstico (solo lectura, no cambies nada)

Mide antes de opinar. Nada de estimaciones:

- ¿Qué lee una sesión al arrancar en este vault, y cuánto pesa en bytes?
- ¿Qué proporción del archivo de estado principal es historial acumulado frente
  a estado presente?
- ¿Cuántas notas hay por tipo, y a qué ritmo crecen (mira las fechas)?
- ¿Hay frontmatter? ¿Es uniforme? ¿Algo lo lee — una consulta de Dataview, una
  skill, un script?
- ¿Qué documentos se contradicen entre sí? Dos fuentes de verdad divergiendo es
  el síntoma que más duele y el más fácil de pasar por alto.

### Fase 2 — Propuesta (y para aquí)

Presenta: la línea base medida, qué partes del patrón aplican a **este** vault y
cuáles descartas con su motivo, el destino de cada tipo de nota, y qué se
rompería (consultas de Dataview, enlaces, automatismos del equipo).

**Espera aprobación explícita antes de tocar el vault.** Si algo es ambiguo,
pregunta en vez de elegir por tu cuenta.

### Fase 3 — Ejecución

En este orden, que es una propiedad de seguridad y no una preferencia:

1. Punto de retorno.
2. Mueve el historial a su destino, **verbatim**, conservando la fecha real del
   trabajo (no la de hoy) en el nombre y en el frontmatter.
3. **Verifica que cada bloque llegó** — busca por contenido una frase
   característica de cada uno. Si alguna búsqueda vuelve vacía, **para**.
4. Solo entonces, reescribe el archivo de estado con el esqueleto nuevo.
   Conserva lo vivo: pendientes, convenciones, enlaces. Eso no es historial.
5. Unifica el frontmatter y genera el índice.
6. Comprueba idempotencia: genera dos veces y compara por hash. Si difiere, algo
   variable se está colando (una marca de tiempo, un contador, el orden del
   sistema de archivos) y romperá cualquier verificación futura.

### Fase 4 — Verificación

Mide otra vez el arranque y compáralo con la línea base. Después, la prueba que
ningún comando sustituye: **arranca una sesión nueva y comprueba si te deja al
día sin echar nada de menos.** Si acabas abriendo tres documentos a mano, los
`summary` del índice son malos — mejóralos, no vuelvas a leerlo todo.

## Errores que ya se cometieron allí — no los repitas

Salieron todos en la implementación del vault personal, y ninguno era obvio:

- **El script invocado con ruta relativa** funcionaba en su repo y fallaba en
  todos los demás proyectos. El esquema quedaba inerte sin que nadie se enterara.
- **Un parser que quitaba comentarios inline** truncaba en silencio cualquier
  resumen que contuviera `#`. Y el resumen es la interfaz entera de una decisión
  cuando el documento ya no se abre.
- **Un archivo guardado con BOM** perdía su frontmatter completo al leerlo con
  `utf-8` en vez de `utf-8-sig`.
- **Una marca (`harvested`) que una auditoría leía y que nadie escribía**: la
  regla de archivado no podía dispararse jamás. Si defines un estado, define
  quién lo escribe.
- **Un chequeo colocado después del paso de despedida**, es decir, un chequeo que
  nunca corre.
- **Reescribir antes de verificar.** No pasó, precisamente porque el orden estaba
  fijado de antemano. Mantenlo.

## Lo que se decidió NO hacer, con su umbral

Subcarpetas temáticas dentro de la carpeta de decisiones: **rechazado**. Para un
agente que resuelve por glob y grep, la carpeta no añade señal — añade un
problema de clasificación (¿este documento va en `a/`, en `b/` o en `c/`?), y
cada colocación dudosa es un fallo de recuperación futuro. El beneficio real, que
es humano, lo da el índice generado más barato. **Reabrir el debate a ~25-30
documentos en un mismo proyecto, o si aparece un segundo eje de verdad.**

Si en el vault del trabajo ya hay muchas más notas por proyecto que en el
personal, ese umbral puede estar ya superado el primer día: compruébalo en la
Fase 1 en vez de heredar la conclusión.

## Entregable

- El vault reestructurado, con su punto de retorno anotado.
- Un documento corto en el propio vault que registre **qué se decidió y por qué**
  para este vault en concreto, incluido lo que descartaste del patrón original.
  Quien llegue dentro de seis meses necesita el porqué, no el qué.
- La comparación medida: antes y después, con los comandos que la produjeron.
