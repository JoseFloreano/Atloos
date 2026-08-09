# Chequeos del audit — detalle operativo

Comandos y umbrales. El cuerpo de la skill solo dice QUÉ mirar; aquí está el CÓMO.

Estos chequeos corren `adr-index.py` desde **`~/.claude/scripts/`**, donde lo
instala `sync-skills`: misma ruta en toda máquina y **sin depender de dónde esté
clonado el repo**. En Cowork esa ruta **no existe** —no es una máquina tuya—, así
que ahí el audit pide al usuario correrlo y reportar el resultado, igual que hace
con los comandos de git en su paso 2.

## Índice de ADRs desfasado

```bash
py "$HOME/.claude/scripts/adr-index.py" "<vault>/10-Projects/<proyecto>/ADRs" --check
```

`sync-skills` instala el script ahí: misma ruta en toda máquina, con OneDrive o
sin él.

> ⚠️ **Esta skill es de Cowork, donde `~/.claude/scripts/` NO existe** — no es
> una máquina tuya. Ahí este check **no se puede ejecutar**: repórtalo como
> "índice no verificado (requiere laptop)" en vez de darlo por bueno. Un check
> que no corrió no es un check que pasó.

Exit 2 = el índice no refleja los ADRs de la carpeta (alguien escribió uno a
mano). Se arregla corriendo el mismo comando sin `--check`.
Exit 1 con carpeta sin `ADR-*.md` = proyecto joven sin ADRs todavía — el audit
reporta "sin ADRs aún", no un error.

## Tope de `_PROJECT.md`

```bash
wc -l < "<vault>/10-Projects/<proyecto>/_PROJECT.md"
```

- \> 120 líneas: proponer qué rotar a `sessions/`.
- \> 150 líneas: reincidencia — el ritual de cierre no se está aplicando en esa
  laptop; revisar por qué antes de proponer nada más.
- Cualquier sección `## Hecho`: es historial en el sitio equivocado, siempre.

## Notas de sesión cosechadas

Una nota con `harvested: true` en el frontmatter y más de ~30 días de antigüedad
—medida desde la fecha en el frontmatter (`created`/`date`), **no** el mtime
del archivo: este vault vive en OneDrive y los mtimes no son confiables (las
notas migradas comparten todas el mismo timestamp de sync)— es candidata a
`10-Projects/<proyecto>/_archive/`. **Proponer, nunca mover sin aprobación**:
el usuario decide qué deja de estar a la vista.

## Ciclo de vida de los ADRs — todos los estados, no solo `accepted`

El vocabulario es el de MADR: `proposed | accepted | rejected | superseded-by: …`.
Un ADR **nace `proposed`** y eso es correcto: refleja la verdad. Lo que la
auditoría vigila es que no se quede ahí para siempre.

```bash
grep -H "^status:" <vault>/10-Projects/<proyecto>/ADRs/ADR-*.md
grep -L "^status:" <vault>/10-Projects/<proyecto>/ADRs/ADR-*.md   # sin estado
```

| Señal | Hallazgo |
|---|---|
| `proposed` con **más de 14 días** | **Decisión en el limbo.** Reportar: hay que aprobarla o rechazarla. Un `proposed` eterno es una decisión que nadie tomó y que el equipo cree tomada. |
| `accepted` contradicho por otro ADR sin `superseded-by:` | El registro durable se contradice consigo mismo. |
| Sin `status:` | Invisible para todos los chequeos anteriores. |
| `rejected` o `superseded-by:` | Nada que hacer: el ciclo se cerró bien. |

La fecha para el umbral de 14 días sale del `date:` del frontmatter, no del
mtime (el vault se sincroniza por OneDrive y los mtime no son fiables).

**Por qué así y no forzando `accepted` al nacer:** falsear el estado para que
la auditoría lo vea sería mentirle al registro. La auditoría cubre el ciclo
completo; el estado dice la verdad.

---

## Backlog `pendientes.md` — los 4 checks (RFD 12 §2.3)

Solo aplican a proyectos que tengan `10-Projects/<proyecto>/pendientes.md`, o
que deberían tenerlo. Sin este bloque, el backlog es un punto ciego: un archivo
que nadie audita se convierte en el cementerio que el ADR de higiene mató.

| Check | Cómo se mira | Hallazgo |
|---|---|---|
| **Zombi** | Ítem del backlog con `(alta: YYYY-MM-DD)` de **más de 30 días** y sin tocar | Proponer **borrar o re-priorizar**. Mismo espíritu que el `proposed` estancado: un pendiente que lleva un mes sin moverse casi nunca es un pendiente, es un deseo |
| **Divergencia** | El mismo título aparece en `_PROJECT.md` **y** en `pendientes.md`; **o** la N de `Backlog: N ítems → [[pendientes]]` ≠ el conteo real | Las dos listas se están separando. **La N desfasada es el síntoma más temprano** y el más barato de detectar |
| **Disolver** | Existe `pendientes.md` y el total (activos + backlog) es **≤8** | El backlog ya no se gana su existencia: proponer reabsorber y borrar el archivo |
| **Crear** | `_PROJECT.md` tiene **más de 12** checkboxes de primer nivel y **no** hay `pendientes.md` | La sección va camino de romper el tope: proponer la válvula |

### Quinto check: el umbral avisado sin acción (RFD 11 C3)

Distinto origen que los 4 de arriba, misma familia. Bajo la línea del backlog
(o al final de `## Pendientes`), `session-close` deja constancia de cada aviso:

```
Backlog: 6 ítems → [[pendientes]]
<!-- umbral avisado: 2026-08-05, 2026-08-07, 2026-08-08 -->
```

```bash
grep -o "umbral avisado:[^-]*-->" "<vault>/10-Projects/<proyecto>/_PROJECT.md"
```

**Cuenta las fechas. 3 o más → hallazgo**: *"umbral avisado N veces sin
acción"*, con los días desde la primera. No es un aviso más: es la prueba de
que avisar no está funcionando y hay que decidir —crear el backlog, disolverlo
o cambiar el umbral—. Menos de 3, silencio: la reincidencia empieza a contar a
la tercera, no a la segunda.

Si el comentario existe pero el umbral **ya no está cruzado**, el hallazgo es
otro: `session-close` debió borrar la línea y no lo hizo.

**La fecha del zombi sale del `(alta:)` del ítem, no del mtime** — el vault se
sincroniza por OneDrive y los mtime no son fiables (mismo motivo que en los
ADRs). Un ítem sin `alta:` es en sí un hallazgo menor: no se puede auditar.

**Se cuentan checkboxes de primer nivel** (`- [ ]` al margen izquierdo). Los
sub-ítems indentados son detalle de su padre.

⚠ **Cómo comparar títulos en el check de duplicados** — se aprendió fallando en
la prueba sembrada del 2026-08-05:

- Compara el **título completo**, no un prefijo. Truncar en el primer paréntesis
  dejaba `"T4"`, que casa con cualquier cosa.
- Busca **solo dentro de la sección `## Pendientes`** de `_PROJECT.md`, no en el
  archivo entero: *Estado actual* menciona features por su nombre («T4 validado
  como diseño») y eso no es un pendiente duplicado.

Un check que grita en falso se ignora a las dos semanas, y entonces da igual que
existiera. Prefiere no reportar a reportar ruido.

Como todo en esta skill: **reporta y propone, no apliques**. Mover pendientes es
escritura, y el único escritor del backlog es `session-close` o el coordinador.

---

## Refutación a medias (RFD 11 C4)

Un hecho refutado se marca donde nació **y donde se propagó**. Si solo se marcó
en un sitio, el vault se contradice consigo mismo — que es exactamente el caso
Graphiti, corregido a mano en tres sitios.

```bash
grep -rn "REFUTADO" "<vault>/10-Projects/<proyecto>/"
```

Por cada refutación encontrada, comprueba que el hecho original esté marcado
(`~~tachado~~` + enlace) **en todos** los sitios donde aparezca:
`_PROJECT.md`, `ADRs/_INDEX.md`, `pendientes.md`, otras notas de `sessions/`.

| Señal | Hallazgo |
|---|---|
| `REFUTADO` en una nota, pero el hecho sigue **sin tachar** en `_PROJECT.md` o en un índice | **Divergencia**: el arranque seguirá sirviendo el hecho falso como bueno |
| Línea tachada **sin enlace** a la refutación | Se sabe que es falso pero no por qué — el error deja de enseñar |
| `REFUTADO` **sin** "Medido en:" | Es una opinión con formato de medición. Reportar |

Buscar la cadena `REFUTADO` es barato y no tiene falsos positivos plausibles:
nadie la escribe por accidente.

---

## Rutas inalcanzables en las skills

```bash
py setup/scripts/tests/test-skill-paths.py   # [repo] · 0 = limpio · 1 = hallazgos
```

⚠ **En Cowork no se puede correr** (no hay repo conectado ni intérprete): igual
que el `--check` del índice, repórtalo como **"no verificado (requiere laptop)"**
en vez de darlo por bueno. Un check que no corrió no es un check que pasó.

Caza la enfermedad que produjo el fallo del 2026-08-07: **una skill corre desde
el cwd de CUALQUIER proyecto**, así que todo lo que mande ejecutar necesita una
ruta **estable por máquina** (`~/.claude/scripts/`, que puebla `sync-skills`) —
no la ruta del repo, y no *"búscalo en Atloos"*.

Ese día `notify-telegram` mandó ejecutar un script "del repo Atloos" desde
`alphadogs`, en la misma máquina y con el puente configurado. No hay relación de
rutas entre los dos árboles: el agente no podía encontrarlo.

**Por qué un arnés y no un grep**: el barrido del 08-03 buscó rutas
*hardcodeadas* —el síntoma— y esta skill tenía una ruta *vaga*. Misma
enfermedad, otro síntoma, y sobrevivió al grep.
