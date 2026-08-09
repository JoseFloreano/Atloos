---
tipo: feedback
fecha: 2026-08-09
reporter: alias-o-nombre
maquina: legion-win11
so: Windows 11
superficie: claude-code
claude_code: 2.1.226
tarea: Una línea con lo que se intentó hacer
duracion_min: 45
turnos: 30
veredicto: sirvio-con-fricciones
skills_disparadas: [session-close, workstream-merge-gate]
skills_que_faltaron: []
hooks_disparados: [check-vault-updated]
graphify: usado
bloqueantes: 0
---

# Feedback — <tarea en pocas palabras>

> Leyenda: `[R]` comprobado con un comando · `[AR]` impresión del agente ·
> `[H]` lo dice el humano.

## 1. Qué se intentó

[H] <una o dos frases, en palabras del humano>

## 2. Evidencia de máquina

```
$ claude --version
<salida literal>

$ git log --oneline -1
<salida literal>

$ git status --porcelain | wc -l
<salida literal>
```

[R] Skills cargadas: <lista, o «no lo sé»>
[R] Hooks disparados: <lista, y si alguno bloqueó (exit 2)>
[R] Coste (`/cost`): <literal, o «no disponible»>

## 3. Qué funcionó

- [H] …
- [R] …

## 4. Qué NO funcionó

> **Obligatoria.** Si no hubo nada, explica por qué crees que no lo hubo.

- [H] …

## 5. Triggers — lo que se escribió literalmente

| Frase literal del humano | Qué esperaba que cargara | Qué cargó |
|---|---|---|
| «…» | `skill-x` | `skill-y` / nada |

> Si no hubo ningún caso, escribe «ninguno» y borra la tabla.

## 6. Graphify — ¿se usó el mapa?

**Instalación**

- [R] `graphify` instalado en este repo: sí / no / no lo sé
- [R] Hook `post-commit` instalado (`.git/hooks/post-commit`): sí / no
- [R] El `CLAUDE.md` del proyecto lleva: **el disparador nuevo** («antes de tu
  primer `grep`…») / **la línea vieja** («For codebase questions, first run
  `graphify query`») / ninguna de las dos

**Uso**

- [R] ¿Se corrió `graphify query` **antes del primer `grep`** de exploración?
  sí / no
- [H][AR] Si **no**: ¿por qué? ← *la respuesta más valiosa de esta sección*

**Calibración** (solo si se corrió)

| Medida | Valor | Referencia de campo |
|---|---|---|
| Sitios que devolvió / sitios reales | …/… | 5 de 9 |
| ¿Los decisivos estaban dentro? | sí / no | los 2 decisivos quedaron fuera |
| `loc=` que apuntaban a `L1` | …/… | 49 de 65 |
| Tiempo hasta la respuesta | … s | 1,7 s |

- [AR] ¿La salida sirvió como **lista de candidatos** o se tomó como respuesta?
- [R] Tras el commit, ¿se regeneró `codebase-map-snapshot.md` en el vault?
  ¿El `codebase-map.md` **curado** quedó intacto?

> Si graphify no está instalado, pon `graphify: no-instalado` en el frontmatter,
> contesta la primera línea y borra el resto de la sección.

## 7. Fricciones menores

- [H] …
- [AR] …

## 8. Lo que esperaba y no existe

- [H] …

## 9. Confirmación del humano

- [H] Leído y corregido por: <alias> · <fecha>
- [H] Cambios que pedí sobre el borrador del agente: <ninguno / cuáles>
