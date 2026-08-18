# Higiene de salida de herramienta — pide la respuesta, no el material

Hermana de `higiene-de-shell.md`: aquella evita **fallos** de shell, esta evita
**volumen**. Las dos las paga el frente, pero esta la paga también la sesión que
no despacha nada — por eso la regla corta vive en el `CLAUDE.md` y el detalle,
aquí.

**La regla es una sola: pide la respuesta, no el material.** Todo lo de abajo
son casos de esa regla.

Y no hay atajo por compresión: medida sobre las dos cargas grandes reales de
este proyecto, la compresión externa da **0 %** — `git log --stat` de 800
commits, **0,0 %**; un `Read` de un `.py`, **0,0 %** (`router:excluded:tool`, el
código está protegido por diseño). Lo único que las reduce es no pedirlas
enteras.

## Lo que cuesta, en dinero — y por qué la regla se queda corta

**Procedencia: sesión del 2026-08-17, `/cost` literal, 1 132 turnos**
(descompuesto en `docs/ecosistema/32-ANALISIS-COSTE-Y-HIGIENE.md`). El **73 %**
de aquella factura —$226,72 de $310,91— fue **cache read**: releer el contexto.
El *output*, el 13 %. Se releyeron **241 k tokens en cada uno de los 1 132
turnos**.

| Basura metida en el contexto | Coste en aquella sesión |
|---|---:|
| 1 k tokens | **$0,57** |
| 10 k tokens | **$5,66** |
| 50 k tokens | **$28,30** |

Es la primera vez que este repo puede ponerle **precio** a una fila de abajo:
un `git log --stat` de los medidos (222 314 bytes) son ~55 k tokens ⇒ del orden
de **$30 por descuido**.

**El gasto real es `bytes × llamadas × turnos restantes`, y las ocho filas solo
tienen término para el primer factor.** Las dos reglas que faltan:

- **Si vas a hacer más de un puñado de búsquedas, hazlas DENTRO de un
  subagente.** Un subagente devuelve solo su mensaje final: sus búsquedas
  **nunca entran en el contexto del coordinador**. Medido en campo: **170
  llamadas de `Grep`/`grep`/`rg` en una sola sesión**, todas en el contexto del
  coordinador. Aunque cada una fuera impecable (1-2 k tokens), son 170-340 k
  releídos más de mil veces — **la higiene por comando no puede con eso**.
- **La higiene vale al principio.** Lo que entra en el turno 50 de 1 132 se
  relee 1 082 veces; lo mismo en el turno 1 000, solo 132: **8 veces más caro
  por entrar pronto** (para llegar a 20× hay que comparar el turno 50 con el
  1 080, no con el 1 000).

## Las ocho filas

Las cifras son **de este repo, medidas** (2026-08-15, 138 commits, `b9a9d98`),
en bytes de salida. Las tres sin cifra propia no se midieron aquí y se dice.

| En vez de | Pide | Antes → después | Ahorro |
|---|---|---|---|
| `git log --stat` | `git log --oneline -n 50` | 222 314 → 4 267 | **−98,1 %** |
| `git diff` entero | `git diff --stat`, y luego el fichero | 59 566 → 590 | **−99,0 %** |
| `find .` / `ls -R` | `Glob`, o `find -maxdepth N` | 28 737 → 1 606 | **−94,4 %** |
| `Read` de un fichero grande | `Grep -n` y luego `Read` con `offset`/`limit` | 35 882 → 3 044 | **−91,5 %** |
| Volcar la salida de cada arnés | El runner de dos tiempos (`run-tests.py`) | 27 374 → 656 | **−97,6 %** |
| `git status` | `git status --short` | 723 → 335 | −53,7 % |
| `pytest` con traza completa | `pytest -q --tb=line` | 275 KB (medido fuera) | no medible aquí¹ |
| JSON de API entero | `jq` con el recorte **antes** de leerlo | — | 61 % campos cortos, **2 % texto largo**² |
| `npm install` / `pip install` en crudo | `-q`, y la salida a fichero | — | no medido |

¹ **Este repo no usa pytest.** `run-tests.py` corre cada arnés como subproceso
serial; no hay `pytest.ini`, ni `addopts`, ni pytest-xdist instalado
(verificado, sprint 8 · S3). La fila vale para otros proyectos; aquí su
equivalente es la fila del runner, que ya está medida.

² El recorte con `jq` **no siempre paga**: en campos cortos quita el 61 %, en
texto largo el 2 %. Si el JSON es mayormente prosa, recortar campos no te salva
— tienes que pedir menos registros.

## ⚠ Una fila que es higiene *y* corrección

`--name-only` **no aplica `--ignore-cr-at-eol`** al decidir si un fichero
cambió; `--numstat` sí. Reproducido en laboratorio (159 ficheros, cambiando
**solo** los CR de fin de línea, `core.autocrlf=false`):

```
git diff --name-only --ignore-cr-at-eol | wc -l   → 159
git diff --numstat   --ignore-cr-at-eol | wc -l   → 0
git status --short                      | wc -l   → 159
```

**159 ficheros «modificados» y cero cambios reales.** Esta fila no es sobre
tokens: es sobre **creerse un número falso**. 159 rutas de ruido en el contexto
y, peor, una conclusión equivocada sobre el estado del árbol — «hay que revisar
159 ficheros» cuando no hay nada que revisar. Para decidir *si algo cambió*, la
respuesta la da `--numstat` (o `--stat`), no `--name-only`.

⚠ En este repo `core.autocrlf=true` y no hay `.gitattributes`, así que hoy no se
reproduce: git normaliza a la entrada y el diff sale limpio. Aparece **en cuanto
un checkout, un worktree o una copia dejan el fin de línea distinto** — que es
justo lo que hace un `cp` de restauración, y pasó restaurando un fichero durante
este mismo sprint.

## ⚠ El reverso, que es donde esto se estropea

**Nunca apliques la higiene al comando cuya falla estás diagnosticando.**
`--tb=line` es correcto para saber **si** pasó; es exactamente lo que no quieres
cuando ya sabes que falló y buscas por qué. Una fila de arriba aplicada al
comando equivocado convierte un ahorro en una segunda corrida.

**La forma correcta son dos tiempos: la barata para todos, la cara solo para los
que fallaron.** No es teoría — es lo que ya hace `run-tests.py`, y de ahí sale
su −97,6 %: imprime una línea por arnés y **solo vuelca la salida completa de
los que fallaron**. Copia esa forma.

Y la otra ley, que es de la casa: **redirigir a fichero no puede tragarse el
código de salida.**

```bash
# SÍ — sin tubería
cmd > /tmp/a.txt 2>&1; echo "exit=$?"; wc -c < /tmp/a.txt

# NO — `$?` es el de `tail`, y `tail` casi siempre sale 0
cmd | tail -5; echo $?
```

Leer `$?` detrás de una tubería es un mentiroso silencioso, está cobrado tres
veces este mes y tiene su propia entrada en `higiene-de-shell.md` §4. Aquí se
repite porque **el instrumento de medir el ahorro es justo el que la pisa**.

## Cómo medir una fila nueva

Sin tubería, y el `exit` a la vista:

```bash
caro   > /tmp/a.txt 2>&1; echo "exit=$?"; wc -c < /tmp/a.txt
barato > /tmp/b.txt 2>&1; echo "exit=$?"; wc -c < /tmp/b.txt
```

Una fila sin cifra propia es un consejo, no una medida — y este repo lleva cinco
números escritos en contratos que nadie midió (las 500 palabras, el techo de
`_PROJECT.md`, los 1024 caracteres, los umbrales 8/12 del tablero, el techo de 3
frentes). Si añades fila, mídela o márcala «no medido», como están marcadas las
tres de arriba.
