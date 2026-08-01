# Chequeos del audit — detalle operativo

Comandos y umbrales. El cuerpo de la skill solo dice QUÉ mirar; aquí está el CÓMO.

Estos chequeos corren `adr-index.py`, que vive en el repo ClaudeSetup — hacen
falta ese repo conectado a la sesión de Cowork para poder correrlos. Donde no
esté conectado, el audit pide al usuario correrlo y reportar el resultado
(igual que el cuerpo de la skill ya hace con los comandos de git en su paso 2).

## Índice de ADRs desfasado

```bash
py "$HOME/OneDrive/Documentos/Mis_Documentos/Proyectos/Coding/Python/Otros/ClaudeSetup/setup/scripts/adr-index.py" "<vault>/10-Projects/<proyecto>/ADRs" --check
```

El script vive en el repo ClaudeSetup; la ruta absoluta es estable entre
laptops porque el repo viaja en OneDrive.

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

## Frontmatter de ADRs

```bash
grep -L "^status:" <vault>/10-Projects/<proyecto>/ADRs/ADR-*.md
```

Cualquier archivo listado es invisible para el chequeo de ADRs contradictorios.
