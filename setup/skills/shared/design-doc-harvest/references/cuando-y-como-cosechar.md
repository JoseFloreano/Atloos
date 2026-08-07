# Cuándo se cosecha un RFD, y cómo se redirigen sus referencias

Detalle de los pasos 1, 5 y 5b de `design-doc-harvest`.

## Cuándo — la tabla de estados

   | Estado del RFD | Qué se hace |
|---|---|
| Propuesta abierta / en discusión | se queda |
| Aprobado pero **no** implementado | se queda |
| Implementado, con la **auditoría abierta o con condiciones pendientes** | se queda — todavía NO se cosecha |
| Implementado **y con las condiciones de auditoría cerradas** | cosecha → ADR → **redirigir referencias (paso 5)** → `git rm` |
| Abandonado | **redirigir referencias (paso 5)** → borrar sin ADR, con confirmación |

"Auditado" significa **condiciones de auditoría cerradas**, no "hubo
auditoría". Un RFD con la auditoría aprobada *con condiciones* pendientes NO
se cosecha.

Si hay varios features mezclados, lista y confirma con el usuario CUÁLES
corresponden a lo ya implementado.

## Cómo — redirigir antes de borrar

"Git conserva la historia" es cierto
para el contenido y falso para los enlaces:

```bash
# sustituye NN por el número real: para el RFD 02 -> "RFD 02|02-RFD"
# OJO al alcance: TODO el repo, no solo docs/ — y también el vault
grep -rn -E "RFD 02|02-RFD" . --exclude-dir=.git --exclude-dir=.superpowers
grep -rn -E "RFD 02|02-RFD" <vault>/10-Projects/<proyecto>/
```

Copiado literal con `NN` el comando no matchea nada — no confundas "cero
resultados porque no sustituiste NN" con "no hay referencias entrantes": lo
segundo lleva a borrar y reproducir el mismo huérfano que este paso existe
para evitar.

**Buscar solo en `docs/` no basta**, y es un error ya cometido: al cosechar
el RFD 09 quedaron citas colgando en `_archive/` (dos prompts que apuntaban
al diseño borrado) y en el propio ADR del vault. Los ADR y las notas del
vault también citan documentos del repo: el enlace roto se ve igual de mal
desde ahí.

Actualiza cada cita para que apunte al ADR resultante. Solo cuando el grep
deje de devolver referencias huérfanas se borra el archivo. (Precedente real:
al cosechar el RFD 02 hubo que redirigir **31 líneas en 10 archivos** — casi
todas en una subserie distinta, `subagentes/`, que seguía en vuelo. Las
referencias entrantes casi siempre son más de las que parecen: cuéntalas con
el grep, no de memoria.)
5b. **¿El RFD vive en el VAULT y no en el repo?** Entonces el paso 6 NO aplica:
el vault **es** la memoria, no andamiaje. Cosecha a ADR y **archiva** el RFD
en `RFDs/_archive/` con un **cartel** al principio apuntando a su ADR —
nunca `git rm`.

Y si las referencias entrantes pasan de **~20**, el cartel es la **vía
aceptada** en vez de reescribir cada cita: en campo, 6 RFD tenían **118
citas** y reescribirlas era inviable. Los wikilinks de Obsidian sobreviven al
cambio de carpeta porque resuelven por nombre; **solo hay que reescribir las
citas por RUTA** (fueron 3).

