# El backlog `pendientes.md` — umbrales y mecánica

Detalle del paso 7 de `session-close`. Diseño: RFD 12
(`docs/arquitectura-memoria/12-RFD-BACKLOG-DE-PENDIENTES.md`), enmienda a
`ADR-20260801-higiene-vault`.

**Qué defiende esto.** El tope de 120 líneas de `_PROJECT.md` existe para
forzar curación. Sin válvula, un proyecto sano con más pendientes legítimos de
los que caben acaba en uno de dos fallos: se borran pendientes reales para
caber (pérdida), o se estira el tope (muere el mecanismo). **El backlog no
relaja el tope: lo hace sostenible.**

---

## Los umbrales, con histéresis

| Situación | Acción |
|---|---|
| `## Pendientes` de `_PROJECT.md` pasa de **12 ítems**, o el archivo rompe las 120 líneas por culpa de pendientes | **Proponer CREAR** el backlog |
| Existe `pendientes.md` y el total (activos + backlog) cae a **≤8** | **Proponer DISOLVER**: reabsorber y borrar el archivo |
| Total entre **8 y 12** | **Nada.** La banda muerta es deliberada: evita crear y disolver el mismo archivo cada semana |

Se cuentan **checkboxes de primer nivel** (`- [ ]` al margen). Los sub-ítems
indentados son detalle de su padre, no pendientes.

## Al crear

1. Copia `templates/pendientes.md` a `10-Projects/<proyecto>/pendientes.md` y
   rellena el frontmatter (`project:`, `updated:`).
2. **Deja en `_PROJECT.md` solo los 5–7 activos**: lo que de verdad se
   trabajará próximo. Si dudas cuáles son, **pregúntale al usuario** — es su
   lista de prioridades, no la tuya.
3. Mueve el resto. **Cada ítem conserva o gana su fecha de alta**
   `(alta: YYYY-MM-DD)`: la real si se puede datar (las notas de `sessions/`
   suelen fecharlos), la de hoy si no. Sin fecha, `vault-drift-audit` no puede
   detectar zombis.
4. En `_PROJECT.md`, al final de `## Pendientes`, una sola línea:

   ```
   Backlog: N ítems → [[pendientes]]
   ```

5. Verifica: `grep` de 2-3 títulos → cada uno aparece en **UN solo archivo**.

## Al disolver

Reabsorbe los ítems del backlog a `## Pendientes` y **borra el archivo** (no lo
dejes vacío: un backlog vacío invita a rellenarlo). Quita la línea de enlace.

## Refrescar el contador — no es cosmética

Si el backlog existe, **recalcula la N de la línea de enlace en cada cierre**.
Una N desfasada es el **primer síntoma** de que las dos listas divergieron, y
es justo lo que `vault-drift-audit` busca. Cuesta un conteo.

## Lo que NO se hace aquí

- **Lo hecho se borra, no se tacha.** Sin `## Hecho`, sin tachados. La historia
  vive en git y en `sessions/`.
- **Un ítem no vive en dos archivos.** Si aparece en ambos, es divergencia —
  resuélvela moviéndolo, no copiándolo.
- **Los bugs no entran**: siguen en `bugs/` con `status: open`.
- **El tope no se toca**: sigue 120 blando / 150 duro.
