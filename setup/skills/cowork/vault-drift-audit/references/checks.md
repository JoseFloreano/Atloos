# Chequeos del audit — detalle operativo

Comandos y umbrales. El cuerpo de la skill solo dice QUÉ mirar; aquí está el CÓMO.

Estos chequeos corren `adr-index.py`, que vive en el repo ClaudeSetup — hacen
falta ese repo conectado a la sesión de Cowork para poder correrlos. Donde no
esté conectado, el audit pide al usuario correrlo y reportar el resultado
(igual que el cuerpo de la skill ya hace con los comandos de git en su paso 2).

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
