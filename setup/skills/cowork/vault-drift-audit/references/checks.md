# Chequeos del audit — detalle operativo

Comandos y umbrales. El cuerpo de la skill solo dice QUÉ mirar; aquí está el CÓMO.

## Índice de ADRs desfasado

```bash
py setup/scripts/adr-index.py "<vault>/10-Projects/<proyecto>/ADRs" --check
```

Exit 2 = el índice no refleja los ADRs de la carpeta (alguien escribió uno a
mano). Se arregla corriendo el mismo comando sin `--check`.

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
es candidata a `10-Projects/<proyecto>/_archive/`. **Proponer, nunca mover sin
aprobación**: el usuario decide qué deja de estar a la vista.

## Frontmatter de ADRs

```bash
grep -L "^status:" <vault>/10-Projects/<proyecto>/ADRs/ADR-*.md
```

Cualquier archivo listado es invisible para el chequeo de ADRs contradictorios.
