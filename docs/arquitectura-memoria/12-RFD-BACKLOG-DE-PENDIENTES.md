# RFD — `pendientes.md`: la válvula del tope de 120 líneas

> **Estado:** **IMPLEMENTADO (2026-08-05) — pendiente de auditoría externa.**
> Hasta que cierre, este RFD **no se cosecha** y la enmienda al
> `ADR-20260801-higiene-vault` (§4.4) **no se escribe**: la regla de
> `design-doc-harvest` exige condiciones de auditoría CERRADAS.
>
> | Encargo | Commit |
> |---|---|
> | Plantilla `templates/pendientes.md` | vault |
> | `session-close`: umbrales en ambas direcciones + `references/backlog-pendientes.md` | `b8ca2a1` |
> | `vault-drift-audit`: los 4 checks del §2.3 | `4b607cc` |
> | `project-resume`: menciona sin abrir (**las 2 variantes**) | `eefd25f` |
> | Piloto `claude-setup` migrado | vault |
>
> **Piloto medido:** 131 → **116 líneas**, 13 pendientes → **6 activos + 6 en
> backlog**. Arranque de `project-resume`: 8,6 KB (cargar el backlog sería +29%).
> Prueba sembrada: zombi de 40 días y duplicado **cazados**, más la N desfasada.
> Semillas retiradas y re-corrida limpia.
> **Fecha:** 2026-08-05 · **Autor:** Cowork (auditor, nube).
> **Contexto:** `ADR-20260801-higiene-vault` (vault) — este RFD lo ENMIENDA,
> no lo reemplaza · plantillas en `ObsidianVault/templates/` · skills
> `session-close`, `vault-drift-audit`, `project-resume`.
> **Disparador empírico:** `claude-setup/_PROJECT.md` está en **120/120
> líneas** (el tope exacto del ADR) con **17 pendientes** — la presión es
> real, no hipotética.

---

## 1. Problema

El ADR de higiene fija `_PROJECT.md` ≤120 líneas para forzar curación. Un
proyecto sano puede acumular más pendientes legítimos de los que caben en
ese presupuesto (hoy: claude-setup, 17). Sin válvula, pasan dos cosas malas:
o se borran pendientes reales para caber (pérdida), o el tope se estira
(muere el mecanismo de curación). La tentación obvia —un `pendientes.md`
suelto— sin reglas se convierte en el cementerio que el ADR mató (el
`## Hecho` reencarnado) y en una segunda fuente de verdad que diverge
(ley 3 del setup: las listas no compartidas divergen).

## 2. Diseño

### 2.1 Umbrales, con histéresis

- **Crear** `10-Projects/<proyecto>/pendientes.md` cuando la sección
  `## Pendientes` de `_PROJECT.md` supere **12 ítems** (checkboxes de
  primer nivel), o cuando el tope de 120 se rompa por culpa de pendientes.
- **Disolver** (reabsorber a `_PROJECT.md` y borrar el archivo) cuando el
  total activos+backlog caiga a **≤8**.
- La banda 8–12 evita el churn de crear/disolver cada semana.

### 2.2 Contrato del archivo

1. **Un pendiente vive en UN solo archivo.** `_PROJECT.md` conserva solo
   los **5–7 activos** (lo que se trabajará próximo) + una línea de enlace
   al backlog con el conteo (`Backlog: N ítems → [[pendientes]]`). Nunca
   duplica ítems.
2. Cada ítem del backlog lleva **fecha de alta** (`alta: YYYY-MM-DD`) y el
   contexto mínimo para retomarlo sin arqueología (1–3 líneas, enlaces).
3. **Lo hecho se BORRA, no se tacha.** Sin `## Hecho`, sin tachados: la
   historia vive en git y en las notas de sesión. Mismo principio del ADR.
4. **Un solo escritor por convención**: la sesión que cierra
   (`session-close`) o el coordinador. Los subagentes nunca escriben el
   backlog (reglas 6–7 del memory-snippet).
5. Frontmatter máquina-legible: `type: backlog`, `project:`, `updated:`.

### 2.3 Cobertura de auditoría — la regla sin la cual esto es un punto ciego

`vault-drift-audit` gana cuatro checks:

| Check | Hallazgo |
|---|---|
| Ítem de backlog sin tocar **>30 días** | Zombi: proponer borrar o re-priorizar (espíritu de "proposed >14 días") |
| Ítem duplicado `_PROJECT.md` ↔ `pendientes.md` | Divergencia en gestación |
| `pendientes.md` existe con total **≤8** | Disolver (histéresis) |
| **>12** pendientes en `_PROJECT.md` sin backlog | Crear |

### 2.4 Qué skill cambia y qué NO

- **`session-close`**: al cerrar, detecta umbral (ambas direcciones),
  propone crear/disolver y mueve ítems. Es el único punto de escritura.
- **`vault-drift-audit`**: los 4 checks del §2.3.
- **`project-resume`**: sigue leyendo solo `_PROJECT.md`; menciona "hay N
  más en el backlog" desde la línea de enlace, **sin cargar**
  `pendientes.md` (cero tokens extra en el arranque). Lo carga solo si el
  usuario pregunta por el backlog.
- **`bugs/` no cambia**: los defectos siguen ahí con `status: open`. El
  backlog es para pendientes de proyecto, no para bugs.
- **Plantilla nueva** en `ObsidianVault/templates/pendientes.md`.
- El presupuesto de `_PROJECT.md` (≤120) **no cambia**: esta válvula existe
  para defenderlo, no para relajarlo.

## 3. Alternativas rechazadas

- **Solo curar más agresivo, sin backlog**: rechazada — claude-setup tiene
  17 pendientes reales; borrar valor para caber es el fallo que la válvula
  evita.
- **Carpeta `backlog/` un-archivo-por-ítem (estilo `bugs/`)**: más granular
  y máquina-legible, pero fricción de captura desproporcionada para
  pendientes de 1 línea. `bugs/` ya la usa donde ese costo se paga.
- **Subir el tope de 120**: rechazada de plano — el tope ES el mecanismo.

## 4. Criterios de éxito

1. **Piloto = claude-setup**: `_PROJECT.md` queda con 5–7 activos y <120
   líneas; los demás migran al backlog con fecha de alta; `grep` de
   cualquier ítem da exactamente 1 archivo.
2. `vault-drift-audit` caza un zombi sembrado (>30 días) y un duplicado
   sembrado, en prueba deliberada.
3. `project-resume` arranca con el mismo costo de tokens que antes
   (no lee el backlog).
4. La enmienda queda en `ADR-20260801-higiene-vault` (enriquecer el
   existente — H7 —, no ADR nuevo) al cerrar la implementación.

---

*Implementar = prompt propio para el Opus (después de W2) + auditoría
externa. La cosecha de este RFD sigue la regla de `design-doc-harvest`.*
