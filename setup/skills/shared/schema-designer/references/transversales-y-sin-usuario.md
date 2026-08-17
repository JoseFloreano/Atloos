# Las transversales, y qué hacer sin usuario delante

Detalle de los pasos 4 y 6 del `SKILL.md`. Las dos cosas se extrajeron aquí en
el sprint 10 al recortar el cuerpo: **no se resumieron, se movieron**.

## Las tres transversales — se preguntan UNA VEZ, antes del ERD

Y se preguntan antes porque **ninguna de las tres se retrofitea barato**: las
tres tocan *todas* las tablas a la vez, así que descubrirlas en la tabla nueve
significa migrar las ocho anteriores.

| Pregunta | Si la respuesta es sí | Dónde muerde |
|---|---|---|
| **¿Multi-tenant?** | `tenant_id NOT NULL` en **toda** tabla, y **dentro de toda clave única** | Es la parte que se olvida: un `UNIQUE (email)` en multi-tenant impide que dos clientes tengan el mismo usuario. Va `UNIQUE (tenant_id, email)`. |
| **¿Soft-delete o borrado real?** | `deleted_at` y **consistente en todo el esquema** | Mezclar los dos criterios es peor que elegir mal: una FK desde una tabla con borrado real a una con soft-delete deja filas apuntando a algo que el negocio considera muerto. |
| **¿Se requiere `created_by` / `updated_by`?** | Columnas de auditoría en todas | Añadirlas después obliga a rellenar el histórico con un valor inventado, o a aceptar `NULL` para siempre — que es decir «no sabemos quién». |

**Registra la respuesta** —en el ERD, no en tu cabeza— y aplícala a todas las
tablas. Si el usuario no está para contestar, van como supuesto numerado (abajo).

## Sin usuario disponible: no te detengas, marca

El paso 6 dice «preséntalo y espera acuerdo». En sesión desatendida o como
subagente **no hay a quién esperar**, y pararse ahí convierte la skill en un
bloqueo. La salida es entregar el paquete completo y **decir en voz alta que no
está validado**:

1. **ERD** en Mermaid.
2. **Supuestos numerados** — uno por cada transversal sin contestar y por cada
   decisión de grano que hiciste tú.
3. **DDL**, en la misma entrega — los tres van **juntos**, no en tres turnos.
4. Todo ello encabezado, literal:

   > **DISEÑO NO VALIDADO — revisar ERD antes de ejecutar**

⚠ **Y jamás ejecutes la migración tú mismo** en ese caso. Entregar un diseño sin
validar es legítimo; aplicarlo a una base de datos sin que nadie lo haya mirado
es la operación que `migration-auditor` existe para impedir. Lo primero es
trabajo entregado; lo segundo es un cambio irreversible tomado por quien no
tiene el contexto para tomarlo.

## Y el paso 8, que asusta más de lo que cuesta

Pasar por `migration-auditor` suena a peaje, y en el caso que produce esta skill
casi nunca lo es: **en tablas NUEVAS el checklist se resuelve en segundos** —no
hay filas que migrar, no hay lock largo, no hay rollback que diseñar—. El
auditor es caro cuando la tabla ya tiene datos, que es exactamente cuando lo
quieres.
