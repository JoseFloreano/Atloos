# Verificación de grafos y `Estado del repo` al cerrar

Detalle de los pasos 5 y 7 de `session-close`. Diseño: RFD 10 (C4 y D2).

---

## Graphify: la verificación es INCONDICIONAL (C4)

Hasta 2026-08-07 esto solo se comprobaba *"si hubo cambios estructurales"*. En
campo el hook **nunca estuvo instalado** en un proyecto y el mapa pasó **9 días
congelado** mientras el repo iba de 1.796 a 4.705 nodos, sin que nada lo dijera.

> **Una condición que casi nunca se cumple es indistinguible de una que no
> existe.**

Así que: **si el repo usa Graphify, verifica siempre**, y reporta lo medido —
no un "parece que sí".

1. ¿Existe `.git/hooks/post-commit`? Si no: **ofrece instalarlo**
   (`cp setup/hooks/git-post-commit-graph-report.sh <repo>/.git/hooks/post-commit`
   + `chmod +x`).
2. ¿Qué edad tiene `10-Projects/<proyecto>/codebase-map-snapshot.md`? Repórtala
   en días: *"snapshot de hace 9 días; el hook no está instalado"*.
3. **Aquí no se regenera nada.** El grafo se actualiza en el **commit**, no en
   el cierre — ese fue el motivo de mover la regeneración al hook.

**Qué archivo es cuál** (RFD 10 C2 — la ley del único escritor aplicada a
archivos):

| Archivo | Lo escribe | Qué es |
|---|---|---|
| `codebase-map-snapshot.md` | **solo el hook** | volcado generado; se mide su edad |
| `codebase-map.md` | **solo un humano** | mapa curado; su frescura es juicio humano, no hay generador que la garantice |

Nunca comparten fichero: el `cp` del hook sobre el curado se comió 3.152 bytes
de lecturas humanas con 111.353 de volcado.

**En Cowork se omite**: es toolchain local.

---

## `Estado del repo:` — el campo que hace verificable el arranque (D2)

Línea en `_PROJECT.md`, justo bajo el frontmatter o en *Estado actual*:

```
Estado del repo: a1b2c3d · 2026-08-07
```

**Al cerrar**, en el mismo gesto que recalcula la N del backlog:

- toma el sha corto real de `origin/main` (`git rev-parse --short origin/main`)
  y la fecha de hoy, y **actualiza la línea**;
- si el campo **no existe** (proyecto anterior a esta convención), **añádelo**.
  Eso es lo que hace el mecanismo auto-sanador: `project-resume` lo echa en
  falta una vez, el siguiente cierre lo crea, y a partir de ahí compara.

**Para qué sirve**: `project-resume` lo compara contra `origin/main` al
arrancar. En campo una sesión arrancó sobre un `_PROJECT.md` **desfasado un día
entero** —decía un sha y un conteo de suite que ya no eran— **sin forma de
saberlo**. Con el campo, el arranque dice *"el vault va atrás: tómalo como
orientación, no como verdad"*.

**Lo que NO es**: no es un sustituto de leer el repo, ni un candado. Es una
etiqueta de caducidad.

## Lo que salió del paso 5 al recortar (sprint 10)

**Graphiti** — los episodios ya los escriben las cosechas del paso 4, así que
aquí no se escribe nada nuevo. Es **asíncrono (~25s)**: no esperes
confirmación ni lo busques inmediatamente después. Sin Graphiti disponible se
omite **en silencio**: el vault es la fuente primaria y decirlo cada cierre
sería ruido.

**Graphify** — se verifica **SIEMPRE**, no solo cuando hubo cambios
estructurales. Esa es la parte que se saltaba: «no toqué la estructura, así que
el mapa sigue bien» es exactamente cómo un snapshot envejece sin que nadie lo
note. Hook + edad del snapshot, y **el desfase se reporta en días**.

## Y por qué el paso 2 manda releer `_PROJECT.md` entero

No es prudencia genérica: **el auditor y otras sesiones también escriben en él**,
y ya pasó — en esta misma jornada un segundo escritor añadió una sección a un
fichero mientras otra sesión lo tenía leído. Editar sobre una lectura vieja
sobrescribe trabajo ajeno sin que nadie lo vea.
