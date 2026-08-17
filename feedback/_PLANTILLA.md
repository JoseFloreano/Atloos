---
formato: 3
tipo: feedback
fecha: 2026-08-09
reporter: alias-o-nombre
maquina: legion-win11
so: Windows 11
nucleos: 24
ram_gb: 31
superficie: claude-code
claude_code: 2.1.226
setup_sha: 9d2827b
tarea: Una línea con lo que se intentó hacer
duracion_min: 45
turnos: 30
veredicto: sirvio-con-fricciones
skills_disparadas: [session-close, workstream-merge-gate]
skills_existentes_que_no_dispararon: []
skills_inexistentes: []
hooks_disparados: [check-vault-updated]
graphify: usado
bloqueantes: 0
coste_medido: si
---

<!-- `formato:` es la VERSIÓN DEL CONTRATO, y existe para que endurecerlo no
     borre la historia. Si falta, el validador asume 1 — así los cuatro
     reportes escritos antes de esto declaran su contrato POR OMISIÓN, sin
     tocarlos. Una plantilla nueva nace en 2 y no puede elegir el viejo.
     ⚠ No es una puerta trasera: un reporte con fecha posterior al 2026-08-14
     que declare 1 se bloquea igual.
     La v3 (2026-08-16) anade `nucleos` y `ram_gb`.

     Las tres claves nuevas, y por qué:
     · setup_sha — el commit del repo desde el que se corrió `sync-skills` en
       ESTA máquina. `claude_code:` fija el harness y no dice qué skills había,
       que es justo lo que el reporte evalúa.
     · skills_existentes_que_no_dispararon — existían y NO cargaron. Antes se
       llamaba `skills_que_faltaron` y `[]` se leía como "no faltó ninguna"
       mientras la sección 8 decía lo contrario. Si además hacía falta una que
       NO existe, va en `skills_inexistentes`.
     · coste_medido — `si` o `no`. No obliga a correr `/cost`; obliga a decir
       si se corrió. Con `no`, la sección 4 tiene que decirlo con esas
       palabras: "no se corrió `/cost`". -->


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

$ "$HOME/.claude/scripts/py" -c "import os; print(os.cpu_count())"
<salida literal>          ← va tambien al frontmatter, en `nucleos:`

$ "$HOME/.claude/scripts/py" -c "import psutil; print(round(psutil.virtual_memory().total/2**30))"
<salida literal>          ← va tambien al frontmatter, en `ram_gb:`
```

> **El tamano de la maquina es `[R]` OBLIGATORIO desde la v3**, y no es
> burocracia: esta seccion se llama «Evidencia de maquina» y hasta hoy pedia la
> version del harness, el sha de git y el estado del arbol — **ni una sola
> propiedad de la maquina**. Por ese hueco, el x2,05 que gobierna el techo de
> frentes se midio en `ProgramadoMaxi2` y **nadie puede decir de cuantos
> nucleos**; encima se construyo un presupuesto «para 8» que no era de esa
> maquina ni de esta. Cuatro sprints y ocho ficheros.
>
> Si no tienes `psutil`, la RAM en Windows sale de
> `(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory` y en Linux de
> `free -g`. Redondea a GB enteros; lo que se necesita es el orden de magnitud.

> ⚠ **Y la regla que cierra el agujero de verdad: TODA CIFRA DE TIEMPO NOMBRA
> LA SUITE Y EL PROYECTO DE LOS QUE SALE.** «La suite paso de ~330 s a 677 s»
> no dice de que suite, asi que el numero viajo cuatro sprints hasta acabar
> gobernando despachos de OTRO repo cuya suite tarda 43 s. Se escribe
> «la suite de <proyecto> (<n> tests) paso de X a Y».

[R] Skills cargadas: <lista, o «no lo sé»>
[R] Hooks disparados: <lista, y si alguno bloqueó (exit 2)>
[R] Coste (`/cost`): <salida literal>
[R] Sha del setup (`git -C <repo> rev-parse --short HEAD` en la máquina desde la
    que se corrió `sync-skills`): <sha>

> **El sha del setup no es opcional.** `claude_code: 2.1.226` fija el harness y
> no dice qué skills tenía la máquina — y esa es la pregunta que decide si el
> reporte prueba algo. Sin él no se puede saber si la skill que "no disparó"
> estaba siquiera instalada.

## 3. Qué funcionó

- [H] …
- [R] …

## 4. Qué NO funcionó

> **Obligatoria, las dos mitades.** Van separadas a propósito: mezclarlas hace
> que la segunda se quede sin escribir.
> Y si no corriste `/cost`, **dilo aquí con esas palabras**: «no se corrió
> `/cost`». En los dos reportes de dos no se midió y nadie lo echó de menos,
> porque no había ningún sitio donde faltara.

### 4a · El setup

> Lo que te estorbó, te bloqueó o te hizo perder tiempo: skills, hooks, gates,
> worktrees, documentación que mentía. Si de verdad no hubo nada, escribe por
> qué crees que no lo hubo. Un repo donde todos los reportes dicen "todo bien"
> no tiene feedback: tiene cortesía.

- [H] …

### 4b · Yo, el agente

> **Qué hiciste mal tú.** No lo que el setup te hizo: lo que hiciste tú con él.
> Instrumentos mal elegidos, comandos mal leídos, supuestos que no verificaste,
> reglas que conocías y te saltaste, trabajo que rehiciste por no mirar antes.
>
> **Esto no es penitencia: es el material más útil del reporte.** En los cuatro
> reportes anteriores, cada fallo confesado aquí destapó un defecto real del
> setup — porque **un agente competente que tropieza dos veces con lo mismo
> está señalando una arista, no una torpeza**.
>
> Si de verdad no encontraste ninguno, dilo **y di qué buscaste** para
> afirmarlo. «Ninguno» sin método es lo mismo que no haber mirado.
>
> ⚠ Esta guía va entre `>` A PROPÓSITO: el validador descarta las citas al
> contar, así que una 4b sin rellenar tiene 2 caracteres útiles y bloquea. Si
> la guía fuese texto normal, la propia plantilla satisfaría el check y éste
> sería decorativo — que es el defecto que este repo lleva tres sprints
> cazando.

- [AR] …

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

> **La rellena una persona, y el validador la comprueba.** Sin ella el reporte
> es el borrador de un agente sobre su propio trabajo. `pendiente`, `TODO`,
> `<algo entre ángulos>` o menos de ~60 caracteres útiles **bloquean**.

- [H] Leído y corregido por: <alias> · <AAAA-MM-DD>
- [H] Cambios que pedí sobre el borrador del agente: <descríbelos, o di que no
  pediste ninguno y por qué te parece fiel>
