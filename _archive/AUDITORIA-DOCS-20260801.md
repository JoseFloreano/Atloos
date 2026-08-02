# Auditoría de la documentación del repo

> **Fecha:** 2026-08-01
> **Alcance:** los 42 `.md` de `docs/` + los 4 READMEs accesibles (`README.md`,
> `setup/README.md`, `setup/skills/README.md`, `setup/hooks/README.md`) +
> `_archive/` y `_to_delete/`. Fuera de alcance: los 31 `SKILL.md` (son contrato
> de agente, no documentación) y `setup/telegram-bridge/README.md` (ver §7).
> **Vara de medir:** `docs/` es **la versión final y refinada**. Puede contener
> componentes de investigación, pero refinados y cerrados — a diferencia de los
> RFDs y ADRs, que son el material en vuelo. Lo que está en `docs/` debe estar
> limpio: cierto hoy, indexado, sin estado provisional.
> **Método:** lectura completa de los 4 READMEs, del índice general y de los 3
> índices de subserie; lectura de cabecera + bloque de estado de los 42 docs;
> verificación cruzada de rutas y afirmaciones contra el árbol real del repo.
> Sin acceso a shell, así que **no hay antigüedad por commit**: todo hallazgo es
> sobre contenido, no sobre fecha de git.
> **Por qué está aquí y no en `docs/`:** es un derivado de mantenimiento, no
> parte del setup — misma regla que los `PROMPT-*.md` de esta carpeta.

---

## 1. Veredicto

La documentación **es buena por dentro y está rota por fuera**. El contenido de
los docs individuales resiste la lectura: las decisiones están justificadas, los
números de terceros vienen marcados como tales, y los docs operativos
(`setup/hooks/README.md`, el registro de secretos de `setup/README.md`) están al
día y son ejemplares. Lo que falló es **la capa de navegación y de estado**: los
índices no siguieron el ritmo de la escritura, el README raíz describe un repo
que ya no existe, y `docs/` acumuló 7 RFDs en vuelo que por contrato no deberían
vivir ahí.

| Capa | Estado | En una línea |
|---|:---:|---|
| Contenido de los docs de investigación | 8/10 | Sólido; le faltan banners de "esto ya cambió" |
| Índices (general + 2 de subserie) | 3/10 | Los tres desfasados; 9 docs sin indexar |
| README raíz | 3/10 | 5 comandos con rutas que no existen; ignora la mitad de `setup/` |
| `setup/README.md` | 7/10 | Excelente en secretos y modo local; tabla de componentes incompleta |
| `setup/skills/README.md` | 8/10 | Al día; un conteo hardcodeado que se desfasará solo |
| `setup/hooks/README.md` | 9/10 | Sin hallazgos |
| Higiene de `docs/` (final vs. en vuelo) | 4/10 | 7 RFDs + 1 subserie de investigación pura viven en `docs/` |
| Residuos (`_to_delete/`, `_archive/`) | 5/10 | `_to_delete/` sigue versionado; `_archive/` sin criterio escrito |

**Los tres arreglos que más rinden**, en orden: (1) el README raíz, (2) los tres
índices, (3) decidir el destino de los 7 RFDs.

---

## 2. Hallazgo estructural — `docs/` tiene material en vuelo

El contrato dice que `docs/` es la versión refinada y cerrada. Hoy contiene
**7 RFDs**, todos con estado provisional declarado en su propia cabecera:

| Archivo | Estado que declara |
|---|---|
| `arquitectura-memoria/10-RFD-GRAPHITI-INTEGRACION-ERRORES.md` | `status: draft` |
| `subagentes/04-RFD-ADOPCION-WORKSTREAMS.md` | «PROPUESTA — no aprobada, nada instalado» |
| `telegram/02-RFD-T2-MODO-ESCRITURA.md` | «propuesta aprobada para implementar; **no** aprobada como fase» |
| `telegram/03-RFD-T5-DESARROLLO-PARALELO.md` | «IDEA REGISTRADA — no diseñada, no aprobada» |
| `telegram/04-RFD-PROGRESO-EN-VIVO.md` | «APROBADO por el auditor con cambios» |
| `telegram/05-RFD-T3-MEMORIA-Y-TOKENS.md` | «propuesta, pendiente de aprobación. NO implementado» |
| `telegram/06-RFD-T4-CONTINUAR-DESDE-AVISO.md` | «IDEA REGISTRADA — no diseñada, no aprobada» |

**El ciclo correcto ya existe y ya se ejecutó una vez**: el RFD 09 se cosechó a
`ADR-20260801-higiene-vault` en el vault y se retiró de `docs/` — el índice
general lo registra tachado en su línea 24. Ese es el precedente. Ninguno de
estos 7 ha pasado por ahí.

A esto se suma la subserie `subagentes/` (5 docs), cuyo propio índice declara
«investigación — nada instalado ni configurado todavía»: material de
investigación sin refinar ni cerrar, exactamente lo que el contrato excluye.

**Decisión pendiente (no la toma esta auditoría):** o los RFDs se cosechan a ADR
y se retiran, o `docs/` admite explícitamente una zona en vuelo — p. ej.
`docs/_rfd/` — y el contrato se reescribe para decirlo. Lo que no funciona es el
estado actual, donde un lector no puede distinguir por la ubicación qué está
decidido y qué no.

---

## 3. Hallazgos por severidad

### Alta — rompe a quien sigue las instrucciones

**H1. El README raíz manda 5 comandos con rutas que no existen.**

| Línea | Dice | Ruta real |
|---|---|---|
| 189 | `setup/docker/docker-compose.yml` | `setup/docker-compose.yml` |
| 190 | `setup/docker/.env.example` | `setup/.env.example` |
| 213 | `setup/config/config.yaml` | `setup/config.yaml` |
| 255 | `setup/config/graphiti-project-template.json` | `setup/graphiti-project-template.json` |
| 321 | `setup/scripts/setup-new-machine.sh` | `setup/setup-new-machine.sh` |

El mismo error se repite en `setup/README.md:280`. Los subdirectorios `docker/` y
`config/` no existen: los archivos están en la raíz de `setup/`. Ojo con el
matiz: `setup/scripts/` **sí** existe, pero contiene `adr-index.py`, no los
bootstrap.

**H2. El README raíz ignora la mitad del repo.** Cero menciones a: puente
Telegram, hooks, `sync-skills`, `sync-hooks`, modo single-laptop, `adr-index.py`.
Todo eso está implementado y documentado en otro sitio. Quien lea solo el README
se lleva el setup de julio.

**H3. Contradicción de estado sobre Graphiti.** El README (Fase 3, líneas
180-257) manda montarlo como parte del camino A. `setup/README.md:125` declara
«**Estado (julio 2026): POSPUESTO por decisión propia**», el índice general lo
repite, y el RFD 10 documenta 8 errores de integración sin resolver. El camino de
instalación principal lleva a un componente que el propio setup tiene apagado.

**H4. Los tres índices están desfasados.** 9 docs existentes no aparecen en el
índice general:

- toda la subserie **`telegram/`** (6 docs) — la línea de trabajo activa;
- `ecosistema/16-AHORRO-TOKENS-ROBADO-DE-HERMES-OPENCLAW.md` — y es la fuente de
  R1 y R5, citados en `setup/README.md:34` y en el README de hooks;
- `bd-y-nube/06-AUDITORIA-ADVERSARIAL-SKILLS.md`;
- `arquitectura-memoria/08b-RESUMEN-FUNCIONAL-DEEPSEEK.md`.

Además el índice general (línea 62) dice que los docs **«02–05 pendientes»** de
`bd-y-nube` están por escribir: los cinco existen desde hace tiempo.

Y los índices de subserie tampoco cierran: `arquitectura-memoria/00` lista solo
los docs 01–06 (faltan 07, 08, 08b, 10-RFD, 11); `bd-y-nube/00` lista 01–05
(falta 06).

### Media — engaña al lector sobre el estado real

**H5. Cabeceras contradichas por los hechos.**

- `telegram/00-DISENO-TELEGRAM-BRIDGE.md:4` — «BORRADOR […] **Nada
  implementado**». T1, T2 y T3 están implementados; el código vive en
  `setup/telegram-bridge/`. El mismo doc se contradice a sí mismo: la línea 28
  ubica el script en `setup/scripts/`, la 94 lo ubica bien en
  `setup/telegram-bridge/` (nombre real: `notify_telegram.py`).
- `telegram/05-RFD-T3-MEMORIA-Y-TOKENS.md:3` — «NO implementado». C1b, C2, C3 y
  C4 están implementados según el estado del proyecto.
- `auditoria/09-AUDITORIA-SETUP.md:27` — «nada está implementado aún (estado
  actual: checkboxes vacíos)». Era cierto en julio. El índice general ya anota
  «mitigaciones (aplicadas)», pero el doc por dentro no lo dice: quien lo abra
  directo se lleva un diagnóstico caducado.
- `arquitectura-memoria/06-ARQUITECTURA-FINAL-RECOMENDADA.md` — presenta Graphiti
  como «prioridad media» del plan vigente y da checklist de instalación (línea
  135), sin nota de que está pospuesto ni del RFD 10.

Los cuatro se arreglan con un banner de 2 líneas arriba, no reescribiendo el doc.

**H6. La numeración global perdió la unicidad.** La convención declarada
(`docs/00-INDICE-GENERAL.md:77`) es que los docs se referencian por número y que
eso es «estable ante movimientos de carpeta». Hoy hay cuatro números duplicados:

| Nº | Ocupantes |
|---|---|
| 08 | `arquitectura-memoria/08` (DeepSeek) · `cowork-y-multiagente/08` (Cowork vs Code) |
| 10 | `skills/10` (protocolo de auditoría) · `arquitectura-memoria/10-RFD` (Graphiti) |
| 11 | `skills/11` (testing) · `arquitectura-memoria/11` (guía Graphiti) · `_to_delete/11` |
| 16 | `skills/16` (Python) · `ecosistema/16` (ahorro de tokens) |

La ambigüedad ya está viva en el texto: `skills/13:6` cita «doc 10 §2»
refiriéndose a `skills/10`, mientras `arquitectura-memoria/10` es otra cosa;
`auditoria/09:135` cita «doc 08 §7» refiriéndose a `cowork/08`. Súmale que «09»
designa a la vez la auditoría del setup y el RFD 09 (higiene, ya cosechado).
Las subseries nuevas (`bd-y-nube`, `subagentes`, `telegram`) además reiniciaron
en 00/01 y chocan con la serie original 00–06.

Recomendación: dejar de citar por número y citar por ruta (`skills/10 §2`). El
número puede quedarse en el nombre de archivo como orden de lectura dentro de la
carpeta, pero no debe ser el identificador.

**H7. `setup/README.md` — la tabla de componentes (líneas 9-16) está
incompleta.** No lista `telegram-bridge/` (5 módulos Python, el componente
activo), `scripts/adr-index.py`, `sync-hooks.ps1` ni
`superpowers-vault-preferences.md`. Esa tabla es donde uno busca «qué hay aquí».

**H8. `_to_delete/` sigue versionado** con `11-BUGFIXES-WINDOWS-Y-MODO-LOCAL.md`
y `bom-test.ps1`. El índice general (línea 78) cita justamente ese reporte como
**precedente** de la regla «los docs temporales se cosechan y se retiran» — pero
no se retiró. Además su número 11 alimenta la colisión de H6.

### Baja — higiene

**H9. `_archive/` mezcla dos cosas sin criterio escrito**: investigación previa
(`OptimalClaudeCode.md`) y prompts operativos derivados de RFDs
(`PROMPT-higiene-vault-trabajo.md`, `PROMPT-migrar-alphadogs-rfd09.md`). La regla
buena existe pero está enterrada dentro de uno de los prompts: «vive en
`_archive/` para no contaminar `docs/`». Merece un `_archive/README.md` de cinco
líneas. De paso, `README.md:14` describe `_archive/` como «análisis previo de
referencia histórica», descripción que ya se quedó corta.

**H10. Tabla «Documentación de referencia» del README (líneas 478-488)**: cubre
solo `arquitectura-memoria/`. Ninguna de las 6 subseries posteriores aparece.

**H11. `README.md:12` dice que `docs/` tiene «8 documentos».** Tiene 42.

**H12. `setup/skills/README.md:94` — «15 de 29» hardcodeado en prosa.** Hoy
cuadra (19 `shared/` + 10 `claude-code/` = 29, con 15 ✓). Pero hay 31 skills
contando las 2 de `cowork/`, y cualquier alta desfasa el número en silencio.
Además las 2 de `cowork/` (`project-resume`, `vault-drift-audit`) no tienen fila
en el registro: es defendible (el perfil bot solo mira `shared` + `claude-code`),
pero conviene decirlo en una línea para que la ausencia no se lea como olvido.

**H13. `uv tool install graphifyy`** (README líneas 62 y 405, y
`arquitectura-memoria/06:135`) — doble «y». Aparece igual en los tres sitios, así
que probablemente es el nombre real del paquete en PyPI. Verificar una vez y, si
es correcto, dejar una nota al margen para que nadie lo «arregle» rompiendo el
comando.

---

## 4. Veredicto por archivo

Leyenda: **OK** = sin hallazgos · **BANNER** = el cuerpo sirve, falta nota de
estado · **ACT** = necesita edición · **IDX** = falta indexarlo ·
**RFD** = material en vuelo, decidir destino (§2) · **RET** = retirar.

| Archivo | Veredicto | Qué le falta |
|---|:---:|---|
| `README.md` | **ACT** | H1, H2, H3, H10, H11, H13 — la reescritura más urgente |
| `docs/00-INDICE-GENERAL.md` | **ACT** | H4 (9 docs sin indexar + `bd-y-nube` mal declarado), H6 |
| `setup/README.md` | **ACT** | H7, ruta de la línea 280 (H1). El resto está al día |
| `setup/skills/README.md` | **ACT** | H12 (menor) |
| `setup/hooks/README.md` | **OK** | Sin hallazgos |
| `arquitectura-memoria/00-INDICE` | **ACT** | Lista 01–06; faltan 07, 08, 08b, 10-RFD, 11 |
| `arquitectura-memoria/01`–`05` | **OK** | Cabecera y estado consistentes |
| `arquitectura-memoria/06` | **BANNER** | Graphiti pospuesto + remite al RFD 10 |
| `arquitectura-memoria/07` | **OK** | Es la referencia rápida; sigue siendo la puerta correcta |
| `arquitectura-memoria/08` | **OK** | — |
| `arquitectura-memoria/08b` | **IDX** | Existe y no está en ningún índice |
| `arquitectura-memoria/10-RFD` | **RFD** | `status: draft` |
| `arquitectura-memoria/11` | **OK** | `status: ready`; deriva del RFD 10 |
| `cowork-y-multiagente/08`, `12` | **OK** | — |
| `auditoria/09` | **BANNER** | «nada implementado aún» ya no es cierto |
| `skills/10`, `11`, `13`, `15`, `16` | **OK** | Cabeceras al día; citas por número afectadas por H6 |
| `ecosistema/14` | **OK** | — |
| `ecosistema/16` | **IDX** | Sin indexar, y lo citan `setup/README` y el README de hooks |
| `bd-y-nube/00-INDICE` | **ACT** | Falta el 06 |
| `bd-y-nube/01`–`05` | **OK** | — |
| `bd-y-nube/06` | **IDX** | Sin indexar |
| `subagentes/00`–`03` | **RFD** | Subserie declarada «investigación — nada instalado» |
| `subagentes/04-RFD` | **RFD** | «PROPUESTA — no aprobada» |
| `telegram/00` | **ACT** + **IDX** | «Nada implementado» es falso; ruta del script mal en :28 |
| `telegram/01` | **IDX** | Investigación de compra, cerrada; solo falta indexar |
| `telegram/02`–`06` (5 RFDs) | **RFD** + **IDX** | Ver §2 |
| `_to_delete/` (2 archivos) | **RET** | H8 |
| `_archive/` | **ACT** | Falta `README.md` con el criterio (H9) |

Los **OK** salen de revisión de cabecera, bloque de estado y verificación de
referencias cruzadas — **no** de lectura línea por línea del cuerpo. Un doc puede
estar limpio de estado y tener contenido caducado por dentro; eso requiere otra
pasada, por subserie.

---

## 5. Plan de acción sugerido

Ordenado por rendimiento, no por esfuerzo:

1. **Reescribir el README raíz** (H1, H2, H3, H10, H11). Es la puerta de entrada
   y hoy da comandos que fallan. Debe ganar: sección del puente Telegram, hooks,
   sync de skills, modo single-laptop, y un estado honesto de Graphiti.
2. **Regenerar los tres índices** (H4). Mecánico y desbloquea la navegación.
3. **Poner los 4 banners de estado** (H5). Dos líneas cada uno.
4. **Decidir el destino de los 7 RFDs y de la subserie `subagentes/`** (§2).
   Es la decisión de fondo; las tres anteriores no dependen de ella.
5. **Cerrar la numeración** (H6): pasar las citas a rutas y degradar el número a
   orden de lectura dentro de la carpeta.
6. **Retirar `_to_delete/`** (H8) y añadir `_archive/README.md` (H9).
7. **Completar la tabla de componentes de `setup/README.md`** (H7).
8. **Auditar `setup/telegram-bridge/README.md`** aparte (§7).

Los pasos 1-3 y 6-7 son independientes entre sí: se pueden repartir.

---

## 6. Lo que está bien y no hay que tocar

Vale la pena registrarlo para no «mejorarlo» por inercia:

- **El registro de secretos de `setup/README.md`** (tabla + las 2 reglas + la
  excepción tolerada declarada como tal). Es el mejor bloque de documentación del
  repo: cada secreto tiene ruta, consumidor y procedimiento de rotación, y la
  regla «toda pieza nueva añade su fila en el MISMO PR» le da mantenimiento.
- **`setup/hooks/README.md`**: los 4 hooks documentados con qué garantizan, por
  qué existe cada decisión de diseño, cómo probarlos y qué rompe si los tocas.
- **El registro de skills del perfil bot** (`setup/skills/README.md`): criterio de
  inclusión explícito + justificación por fila + default seguro («si falta la
  fila, se excluye»).
- **La cultura de números honestos** en los docs de investigación: las cifras de
  terceros vienen marcadas como no verificables, y los benchmarks desfavorables
  se citan igual. No la diluyas al refinar.

---

## 7. Lo que no pude auditar

- **`setup/telegram-bridge/README.md`** — la ruta estaba denegada por los
  permisos de la sesión en que se hizo esta auditoría. Es el README del
  componente en trabajo activo; queda pendiente y probablemente sea el más
  importante después del README raíz.
- **Antigüedad por commit** — sin shell no hay `git log`, así que no sé qué docs
  llevan más tiempo sin tocarse. Todos los hallazgos son de contenido.
- **El cuerpo de los 36 docs marcados OK** — verifiqué cabecera, estado y
  referencias cruzadas, no el argumento completo. Ver la nota al pie de §4.
- **Los 31 `SKILL.md`** — fuera de alcance por decisión, son contrato de agente.
