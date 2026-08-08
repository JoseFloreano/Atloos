---
name: memory-keeper
description: >
  Guarda conocimiento durable de la sesión en la memoria del proyecto (Graphiti
  + vault de Obsidian) con el formato y los criterios correctos. Use when the
  user says "guarda esto", "recuerda que", "que no se olvide", when a non-obvious
  bug gets fixed, when a convention or pinned version is established, or al
  cerrar una sesión de trabajo con hallazgos que deben sobrevivir. NOT for
  architecture decisions (use adr-writer for those).
---

# Memory Keeper

Criterios y formato para escribir memoria durable. Las reglas de aislamiento
(group_id del proyecto activo, nunca otros proyectos) están en el CLAUDE.md /
instrucciones del proyecto y son innegociables.

## Requisitos

- MCP `graphiti-memory` — si no está disponible (típico en Cowork sin puente):
  guarda solo en el vault (`10-Projects/<proyecto>/`) y omite Graphiti sin avisar error.
- Vault de Obsidian — si tampoco está: ofrece guardar en `docs/` del repo.

## Qué guardar (alto valor)

- Causas raíz de bugs no-obvios y su fix (síntoma → causa → fix → archivos)
- Versiones pinneadas y POR QUÉ (breaking changes, notas de migración)
- Convenciones del proyecto que difieren de los defaults
- Decisiones "por qué NO X" — lo explícitamente rechazado vale tanto como lo elegido
- Procedimientos no triviales descubiertos (cómo deployar, cómo correr X)

## Qué NO guardar

- Output temporal de debugging; ideas especulativas aún no decididas
- Nada que ya esté en CLAUDE.md o .graphiti.json
- Nada que cambie cada sesión

## Pasos

1. **Search before saving**: `search_facts`/`search_nodes` con los `group_ids`
   del proyecto. Si existe algo similar (>0.8), actualiza en vez de duplicar.
2. Guarda con JSON estructurado y `group_id` del proyecto activo:

   ```python
   add_episode(
     name="Fix: hot reload rompe estado Riverpod en Windows",
     episode_body={
       "symptom": "...", "root_cause": "...", "fix": "...",
       "files": ["lib/providers/auth_provider.dart"], "date": "<fecha>"
     },
     group_id="<proyecto-activo>"
   )
   ```

3. `add_episode` es asíncrono (~25s): NO esperes confirmación ni lo busques
   inmediatamente después.
4. Si el hallazgo es consultable por humanos (bug importante, procedimiento),
   duplica al vault: `10-Projects/<proyecto>/bugs/` o `brain/` según alcance.
5. Verifica: el episodio usa el group_id correcto y no creaste un duplicado.

## Modo refutación — retirar un hecho que resultó falso

Guardar sabemos; **retirar no sabíamos**. El estado falso de Graphiti se
propagó de una nota a `_PROJECT.md` y hubo que corregirlo a mano en tres
sitios. Cuando una **medición** contradice un hecho ya guardado:

**No lo borres — márcalo.** Borrar deja el hueco sin explicación y el mismo
error vuelve. Bajo el hecho, en su nota original:

```markdown
> ❌ **REFUTADO (YYYY-MM-DD):** <qué resultó falso>.
> **Medido en:** <comando//archivo/nota que lo refutó>. Lo correcto es <…>.
```

Y **donde ese hecho se propagó** —`_PROJECT.md`, índices, `pendientes.md`—, su
línea va **tachada** con enlace a la refutación:

```markdown
- ~~[[nota-del-hecho]] — lo que se creía~~ → refutado, ver [[nota-que-refuta]]
```

Requisito: **una medición, no una sospecha**. Decidir que un hecho es falso es
juicio; esta skill da el formato, la evidencia la aporta quien midió. Sin
comando ni artefacto que lo respalde, no se refuta: se pregunta.

Con Graphiti disponible, además un `add_episode` que **nombre el hecho
refutado** (no un episodio suelto que nadie relaciona con el original).

`vault-drift-audit` audita esto: un hecho refutado cuyo original sigue sin
marcar en algún sitio es divergencia.
