# Prompt para reportar tu sesión

Pega **todo lo que hay entre las líneas** en tu sesión de Claude Code (o de
Cowork) **al terminar de trabajar**, no al empezar. Claude recogerá la evidencia
de máquina, te preguntará lo que solo tú sabes, y dejará el archivo en
`feedback/reportes/`.

Antes de pegarlo, léete el [README](README.md) — sobre todo la regla de
**limpieza de secretos**: tú eres el último filtro, no Claude.

---

Vas a escribir un **reporte de feedback** sobre esta sesión, para el repo
`Atloos`. Sigue este orden y no te lo saltes.

**Regla que gobierna todo lo demás: tú eres parte de lo que se está evaluando.**
Un agente calificando su propia sesión es un conflicto de interés, así que el
reporte separa tres cosas y **nunca las mezcla**:

- `[R]` — **hecho de máquina**: lo comprobaste con un comando y pegas la salida.
- `[AR]` — **tu impresión** como agente. Va marcada como opinión, no como dato.
- `[H]` — **lo que dice el humano**. Se lo preguntas; no lo rellenas por él.

---

### Paso 1 · Recoge la evidencia de máquina (sin preguntar nada todavía)

Corre estos comandos y guarda las salidas literales. Si alguno falla o no
aplica, escribe `no disponible` — **no inventes ni estimes**.

```bash
claude --version
git -C . log --oneline -1
git -C . status --porcelain | wc -l
```

Y saca del contexto de esta sesión, **sin adivinar**:

- Sistema operativo y si estás en Claude Code, Cowork o el puente de Telegram.
- **Qué skills se cargaron de verdad** en esta sesión, y cuáles no.
- **Qué hooks se dispararon**, y si alguno bloqueó algo (exit 2).
- Número aproximado de turnos y duración. Si el usuario puede correr `/cost`,
  pídeselo y pega el número tal cual.

**Y lo de Graphify, que tiene sección propia porque es lo que peor se cumple:**

```bash
graphify --version
ls .git/hooks/post-commit
grep -c "graphify query" CLAUDE.md
```

- ¿El `CLAUDE.md` de este proyecto lleva **el disparador nuevo** («antes de tu
  primer `grep` de exploración…») o **la línea vieja** que escribe
  `graphify claude install` («For codebase questions, first run `graphify
  query`»)? Cítala literal, sea cual sea.
- **Mira hacia atrás en esta sesión: ¿corriste `graphify query` ANTES de tu
  primer `grep` de exploración?** Contesta con lo que pasó de verdad, no con lo
  que se supone que debías hacer. Si no lo corriste, **eso no es un fallo que
  ocultar: es el dato**.
- Si lo corriste: cuántos sitios devolvió, cuántos resultaron ser los reales,
  si los decisivos estaban dentro, cuántos `loc=` apuntaban a `L1` y cuánto
  tardó. Las referencias de campo son 5 de 9 sitios (con los 2 decisivos
  fuera), 49 de 65 en `L1`, 1,7 s.
- Tras el último commit: ¿se regeneró `codebase-map-snapshot.md` en el vault?
  ¿El `codebase-map.md` **curado** quedó intacto?

Si no puedes determinar un dato con certeza, la respuesta correcta es
`no lo sé`. Un reporte con huecos honestos vale; uno con datos inventados
envenena el registro.

### Paso 2 · Pregúntale al humano

Hazle estas preguntas **de una en una**, en lenguaje llano, y espera respuesta.
No las contestes tú.

1. **¿Qué querías conseguir en esta sesión, en una frase?**
2. **¿Lo conseguiste?** — sirvió / sirvió con fricciones / no sirvió.
3. **¿Qué te estorbó?** Insiste aquí. Si dice "nada", pregúntale por el momento
   en que tuvo que repetirse, corregirte o explicarte algo dos veces.
4. **¿Hubo algo que esperabas que existiera y no existía?**
5. **¿Alguna skill se disparó cuando no tocaba, o no se disparó cuando sí?**
   Si la respuesta es sí, pídele **la frase literal que escribió** — esa frase
   es el artefacto que sirve para arreglar el trigger; una paráfrasis no sirve.
6. **Si no corriste `graphify query` antes del primer `grep`: ¿por qué crees
   que no?** Pregúntaselo tal cual, y anota tu propia respuesta también. Las dos
   valen: la instrucción se escribió para que un agente la cumpliera, así que si
   no se cumplió, *tu* motivo es tan informativo como el suyo.
7. **Si sí lo corriste: ¿la salida se usó como lista de candidatos, o alguien la
   trató como la respuesta?**

### Paso 3 · Escribe el archivo

Ruta y nombre:

```
feedback/reportes/AAAA-MM-DD-<alias-maquina>-<slug-tarea>.md
```

Ejemplo: `feedback/reportes/2026-08-09-legion-win11-merge-gate.md`

Copia la estructura exacta de [`_PLANTILLA.md`](_PLANTILLA.md): el frontmatter
completo y **las nueve secciones, todas**. Reglas de contenido:

- **La sección «Qué NO funcionó» no puede quedar vacía.** Si de verdad no hubo
  nada, escribe por qué crees que no lo hubo (tarea corta, camino muy trillado,
  no se tocó código…). Un repo donde todos los reportes dicen "todo bien" no
  tiene feedback: tiene cortesía.
- **En la sección 6, `graphify: no-usado` es una respuesta perfectamente
  válida** y probablemente la más útil. No la maquilles: si no está instalado,
  pon `no-instalado`, contesta la primera línea y borra el resto.
- **Marca cada afirmación con `[R]`, `[AR]` o `[H]`.** Sin marca, no entra.
- **Pega salidas literales**, no resúmenes de salidas.
- **No adornes al usuario ni a ti mismo.** Si te equivocaste, escríbelo: la
  sección de fricciones es más útil que la de aciertos.

### Paso 4 · Limpia antes de guardar

Repasa el borrador y **quita**:

- Rutas absolutas con el nombre de usuario (`C:\Users\...`, `/home/...`) →
  déjalas relativas al repo.
- Claves, tokens, cadenas tipo `sk-`, `ghp_`, JWT (`eyJ...`), URLs con
  `?token=` o `&key=`.
- Correos, teléfonos, nombres de clientes y nombres de proyectos ajenos.
- Fragmentos de código de repos privados que no sean de este setup.

Corre el validador y **no guardes hasta que salga en verde**:

```bash
py feedback/_herramientas/valida-reporte.py feedback/reportes/<tu-archivo>.md
```

### Paso 5 · Enséñaselo antes de dar nada por hecho

Muéstrale el reporte al humano y dile literalmente:

> «Este reporte habla de mi propio trabajo. Léelo antes de que lo guardemos y
> cambia lo que no coincida con lo que viviste — sobre todo la parte de lo que
> no funcionó.»

Espera su OK. **Si te dice que algo no fue así, gana su versión**, y lo dejas
escrito como él lo cuenta.

### Lo que NO debes hacer

- **No commitees ni hagas push.** Deja el archivo en el árbol de trabajo y dile
  al humano cómo subirlo.
- **No toques ningún otro fichero del repo** — ni docs, ni skills, ni el vault.
- **No borres ni edites reportes de otros.**
- **No suavices el reporte** porque hable mal de ti. Es literalmente para eso.
- **No inventes números** de turnos, coste o duración. `no disponible` es una
  respuesta válida; un número plausible inventado, no.
