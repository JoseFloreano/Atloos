---
title: Auditoría del sprint 13 — el check aguanta mis tres mutaciones, y dos números siguen mintiendo
tags: [auditoria, sprint13, systemd, higiene, coste]
created: 2026-08-18
updated: 2026-08-18
status: cerrada
type: auditoria
project: atloos
base: d6d18e7
---

# Auditoría del sprint 13

**Veredicto: aceptado, con dos hallazgos pequeños y una concesión mía.**
Cero bloqueantes. **Con esto, el último bloqueo estructural del alta de la SER8
queda cerrado**: la unit existe, versionada.

---

## 1 · Lo que repliqué

**El check del README sobrevive a MIS mutaciones, no solo a la suya [R].** Le pasé
tres que él no escribió, sobre un árbol de laboratorio:

| Mutación | Esperado | Resultado |
|---|---|---|
| Reintroducir la frase que aplazaba systemd | caza | **exit 1**, con la línea citada |
| **Borrar la plantilla** (el recíproco) | caza | **exit 1** — «si el README la nombra, existe» |
| Quitar `MemorySwapMax=0` de la unit | caza | **exit 1** — «la plantilla lo declara» |

La segunda es la que vale: **impide que «arreglar» el check sea borrar la
plantilla**. La tercera comprueba una **propiedad** del artefacto, no su texto —
es la lección del sprint 7 aplicada sin que se la pidiera.

**La unit está bien pensada [R].** Unit de usuario, `ExecStart` al intérprete del
venv con la comprobación al lado, `Restart=on-failure` + `RestartSec=30`,
`OOMPolicy=kill`, y la fórmula de memoria del manual en vez de un número
huérfano. Las dos adiciones que hizo sin pedirlas están bien argumentadas, y la
segunda es la que yo no había visto:

> *«El cgroup no es solo el daemon. Cada invocación lanza un `claude` hijo que
> vive dentro: el techo cubre daemon + agentes concurrentes.»*

**La allowlist podada [R]**: −15 líneas en `.claude/settings.json`.

**El corte de los defaults de modelo es mejor que el que yo pedí.** Yo pedí
«mecánico vs con juicio». Él escribió:

> *«No es fácil contra difícil —toda tarea parece difícil de cerca, y por eso
> todo acababa en caro—: es si una respuesta equivocada **se delata sola**. Si
> puedes nombrar el comando que comprueba el resultado, el frente es barato.»*

Eso es un criterio **operable**. El mío era una etiqueta.

---

## 2 · Concesión: mi «20×» era falso, su 8,2× es el correcto

El encargo decía *«la misma basura cuesta ~20× más en el turno 50 que en el turno
1 000»*. Con 1 132 turnos son **1 082 relecturas contra 132 = 8,2×**. El 20×
sale contra el turno ~1 080, no el 1 000.

**Metí un número sin comprobar dentro de una regla de higiene** — exactamente lo
que ese fichero reprocha. Él lo recalculó y escribió el 8×. Correcto, y la
corrección va en el sitio donde más duele que estuviera mal.

---

## 3 · H1 · Los 16 `py` del puente **no salieron**

Medido con **el mismo patrón** que usé antes del sprint, para que la comparación
valga:

```
main -> 16 ocurrencias
HEAD -> 16 ocurrencias
módulos del puente tocados en la rama: 0
```

(El único `.py` de `telegram-bridge/` que cambia en el diff es el arnés nuevo.)

⚠ **Y esto lo permitía mi propio encargo**: el orden de sacrificio era
`S5 → S4`, así que sacrificar S5a era legítimo. **Lo que falta es declararlo.**
S5b (la allowlist) sí se hizo, así que la entrega quedó a medias sin que la
mitad ausente aparezca como deuda. *(La sección «Antes/después» del reporte llegó
cortada; si lo declaró ahí, esta nota se cae sola.)*

---

## 4 · H2 · La cabecera del snippet dice 913 y el fichero mide 936

**Medido por mí [R]:**

```
caracteres que entran al CLAUDE.md:  3 396
la cabecera declara:                 3 314 car / 913 tokens
delta:                               +82 caracteres
```

Con la propia relación del fichero (3 314 car ÷ 913 tok = 3,63 car/tok), **3 396
car ≈ 936 tokens**. Su reporte dice **943**; el orden de magnitud coincide y la
diferencia es de método, no importa.

Lo que importa es lo otro: **la cabecera sigue diciendo 913 y 3 314**. El número
que gobierna está desactualizado **dentro del fichero que existe precisamente
para que ningún número lo esté**, y es el fichero que viaja al `CLAUDE.md` de
cada proyecto.

> **Octava vez el mismo patrón**, y esta vez en el emblema. Se arregla en un
> minuto: la cabecera se vuelve a medir cada vez que el fichero cambia, o el
> arnés lo mide por ti.

---

## 5 · Nota de despliegue (no es defecto, pero muerde en la SER8)

La unit trae `MemoryHigh=3G` / `MemoryMax=4G`, **declarados en el comentario como
«el valor CONSERVADOR para arrancar con 24 GB»** con la orden de subirlos con el
RSS medido. Está bien escrito.

⚠ **Pero la SER8 tiene 56 GB**, y la fila que le toca en la tabla del manual es
`MemoryMax=16G`. Instalar el ejemplo tal cual deja **4 GB para el daemon MÁS
todos los agentes concurrentes**. Con `OOMPolicy=kill` + `Restart=on-failure` +
`RestartSec=30`, el síntoma en una headless no es un error: es que **el bot
«olvida» lo que estaba haciendo y vuelve 30 s después**, sin nada visible para
quien lo usa.

**Eso tiene que ser un paso del prompt de alta, no una nota al pie.**

---

## 6 · Lo que queda abierto, y él lo declara

- **`skill-forge`** y **la regla 6 del `CLAUDE.md`** siguen ancladas a un juicio
  propio. La regla 6 es peor: *«2+ sesiones a la vez»* es un **INOBSERVABLE** —
  el agente no puede ver otras sesiones. Un disparador que pide un dato que el
  agente no tiene nunca dispara, y no por disciplina.
- **Procedencia colgando**: `higiene-de-salida.md` cita
  `docs/ecosistema/32-…`, que **sigue sin trackear** (es mío). En otra máquina la
  cita no resuelve. **O entra, o la cita se cambia.**
- **`.git/worktrees/sprint13-verify`** — directorio administrativo que
  `git worktree prune` no puede borrar en Windows/OneDrive. Novena entrada del
  mismo problema.
- **El snippet a 7-14 tokens del techo.** El siguiente que añada una línea la
  paga recortando otra. Eso ya no es holgura: es un presupuesto agotado.

---

## 7 · Cuándo se puede hacer el alta de la SER8

**Tres condiciones, y las tres son de empujar, no de construir:**

1. **Integrar el sprint 13 por el gate y pushear.** Hoy `d6d18e7` está sin
   integrar y sin empujar.
2. **Empujar el vault.** Es el bloqueo que arrastras y **crece cada día**: si la
   SER8 clona antes, `project-resume` arranca sobre memoria vieja — el fallo que
   costó un despacho entero el 08-17.
3. **Los dos números de §3 y §4**, que son de minutos y viajan a cada proyecto.

Cumplidas esas, **el prompt de `_archive/PROMPT-ser8-alta-vault-y-daemon.md` se
puede pegar**, con la corrección de memoria de §5 añadida como paso.

---

**Escrito por el auditor externo desde el puente, sobre `d6d18e7`.** Fichero
nuevo en `docs/auditoria/`, **sin commitear**.
