# Procedencia y atribución — `migration-auditor`

Checklist base (5 puntos) del patrón comunitario homónimo del catálogo web de
Agensi (sin repo público; consultado jul 2026), vía
`docs/bd-y-nube/02-SKILLS-BASES-DE-DATOS.md` §1.3.

El **punto 6** (objetos dependientes y topología) y los matices de mecanismo
—qué reescribe, qué solo bloquea, qué falla con error en vez de truncar— se
añadieron en auditoría propia contra la documentación oficial de
PostgreSQL/MySQL/SQLite (ago 2026, doc 06 de la subserie).

**Reescrito propio, sin código de terceros.**

---

## Por qué esta skill no promete una garantía dura

Hasta el 2026-08-09 el cuerpo decía que *"la garantía dura es el hook
validate-migration-review (Fase S2)"*. Ese hook **nunca se construyó**: era una
de las 12 piezas del catálogo `docs/bd-y-nube/` que quedaron propuestas y que
la poda de F0 borró.

*(Los dos nombres muertos van aquí sin backticks a propósito: escritos como
código, `test-skill-catalog.py` los vuelve a contar como referencias vivas —
lo comprobé escribiéndolos así. Narrar una referencia muerta no puede
resucitarla.)*

La auditoría del RFD 17 lo llamó la peor de las referencias colgantes, y con
razón: las otras mandaban usar algo ausente; esta **afirmaba que existía una
red de máquina**. Un lector que la creyera ejecutaría la migración pensando
que algo lo frenaría si se saltaba la revisión.

Si algún día se construye ese hook, esta sección se borra y el cuerpo vuelve a
prometer lo que entonces sí será verdad. Antes no.
