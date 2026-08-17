# `feedback/` — cómo reportar tu sesión

Aquí caen los reportes de quien prueba este setup: **qué pasó de verdad en una
sesión de Claude Code (o de Cowork, o del bot de Telegram)**, no si el repo te
gustó.

Si acabas de terminar una sesión y quieres reportar, solo necesitas esto:

1. Abre [`PROMPT.md`](PROMPT.md) y pega su contenido en tu sesión, **antes de
   cerrarla**.
2. Contesta las preguntas que te haga.
3. Léete el borrador y corrígelo.
4. Corre el validador y sube el archivo.

Lo demás de este README explica por qué está montado así.

---

## La regla que gobierna esta carpeta

> **El que reporta la sesión es el que la vivió — y si es el agente, está
> calificando su propio trabajo.**

Por eso el formato separa tres cosas y nunca las mezcla:

| Marca | Qué es | Quién la pone |
|---|---|---|
| `[R]` | **Hecho de máquina**: hay un comando y su salida literal | el agente, corriendo el comando |
| `[AR]` | **Impresión del agente** sobre su propia sesión | el agente, y va marcada como opinión |
| `[H]` | **Lo que dice el humano** | el humano, y **gana** si contradice al agente |

Un reporte sin marcas no entra. Es la misma ley que gobierna el resto del repo:
*el reporte no es el artefacto*.

## Qué queremos de verdad

Lo más valioso que puedes reportar, por orden:

1. **Una skill que NO se disparó cuando tocaba** — y la **frase literal** que
   escribiste. La frase literal es el artefacto; una paráfrasis no sirve para
   arreglar un trigger. Este repo ya perdió dos merges a `main` por un trigger
   que perdía un concurso de descripciones: ese fallo se arregló porque alguien
   apuntó las frases exactas.
2. **Un hook que bloqueó algo legítimo**, o que **no** bloqueó algo que debía.
3. **Algo que esperabas que existiera y no existe.**
4. **El momento en que tuviste que repetirte** o explicar dos veces lo mismo.

Lo que menos aporta: «funcionó bien». Si todo funcionó, lo interesante es *por
qué* — tarea corta, camino trillado, no se tocó código.

## Estructura de la carpeta

```
feedback/
├── README.md                        ← esto
├── PROMPT.md                        ← pégalo en tu sesión al terminar
├── _PLANTILLA.md                    ← la estructura en blanco
├── _EJEMPLO.md                      ← un reporte completo, para ver el formato
├── _herramientas/
│   └── valida-reporte.py            ← compruébalo antes de subirlo
└── reportes/
    └── AAAA-MM-DD-<maquina>-<tarea>.md
```

Los ficheros que empiezan por `_` son andamiaje, no reportes: el validador los
trata distinto y no llevan fecha en el nombre.

## Nombre del archivo

```
feedback/reportes/AAAA-MM-DD-<alias-maquina>-<slug-tarea>.md
```

Ejemplo: `2026-08-09-legion-win11-merge-gate.md`

Minúsculas, sin espacios, sin acentos, guiones para separar. El alias de máquina
es tuyo (`legion-win11`, `mac-m2`, `minipc-debian`) — **no** el hostname real si
lleva tu nombre.

## El formato

Frontmatter obligatorio (lo que permite agregar reportes sin leerlos todos):

```yaml
---
tipo: feedback
fecha: 2026-08-09
reporter: alias
maquina: legion-win11
so: Windows 11
superficie: claude-code        # claude-code | cowork | telegram
claude_code: 2.1.226
tarea: Una línea con lo que se intentó
duracion_min: 45
turnos: 30
veredicto: sirvio-con-fricciones   # sirvio | sirvio-con-fricciones | no-sirvio
skills_disparadas: [session-close]
skills_que_faltaron: []
hooks_disparados: [check-vault-updated]
graphify: usado                # usado | no-usado | no-instalado
bloqueantes: 0
---
```

Y **las nueve secciones, todas**, en este orden:

1. Qué se intentó
2. Evidencia de máquina
3. Qué funcionó
4. **Qué NO funcionó** ← obligatoria, no puede quedar vacía
5. Triggers — lo que se escribió literalmente
6. **Graphify — ¿se usó el mapa?**
7. Fricciones menores
8. Lo que esperaba y no existe
9. Confirmación del humano

La 4 es obligatoria a propósito. **Un repo donde todos los reportes dicen «todo
bien» no tiene feedback: tiene cortesía.** Si de verdad no hubo nada, escribe
por qué crees que no lo hubo.

## Por qué Graphify tiene sección propia

Porque es la instrucción que peor se cumple del setup, y porque **ahora mismo
nadie está midiendo si eso cambió**.

La historia corta: la instrucción de correr `graphify query` se incumplió **dos
jornadas de dos** con la herramienta instalada y al día. El diagnóstico fue que
decía *"úsalo pronto"* — que no nombra un momento. Se reescribió para que
nombrara uno (*«antes de tu primer `grep` de exploración»*) y para que llevara
la expectativa con números en vez de adjetivos: en campo devolvió **5 de 9
sitios en 1,7 s**, con **los 2 decisivos fuera**, y **49 de 65** `loc=`
apuntaban a `L1` — es decir, señala el fichero, no la línea. Es una **primera
pasada con omisiones garantizadas**, no una respuesta.

Ese cambio es una **predicción**: que con el disparador nuevo sí se corra. Los
reportes son el único sitio donde esa predicción se puede contrastar con lo que
pasa de verdad. Por eso la sección pregunta tres cosas y ninguna es opcional:

1. **Qué línea lleva el `CLAUDE.md` del proyecto** — la nueva o la vieja que
   escribe `graphify claude install`. Una copia desplegada que se quedó atrás
   explica por sí sola cualquier incumplimiento.
2. **Si se corrió antes del primer `grep`** — y si no, **por qué**. Esa
   respuesta vale más que todo lo demás de la sección.
3. **La calibración**, cuando se corrió: cuántos sitios de cuántos, si los
   decisivos entraron, cuántos `loc=` en `L1`. Sin números, «funcionó bien» no
   se puede comparar contra el 5 de 9 de campo.

`graphify: no-usado` es una respuesta legítima y probablemente la más útil que
puedes dar. **No la maquilles.**

## Antes de subir: limpia y valida

**Tú eres el último filtro de secretos, no el agente.** Quita del borrador:

- Rutas absolutas con tu usuario (`C:\Users\…`, `/home/…`).
- Claves y tokens: `sk-…`, `ghp_…`, JWT (`eyJ…`), URLs con `?token=`.
- Correos, teléfonos, nombres de clientes, nombres de proyectos ajenos.
- Código de repos privados que no sean este setup.

Luego:

```bash
setup/scripts/py feedback/_herramientas/valida-reporte.py feedback/reportes/<tu-archivo>.md
```

El validador **bloquea** lo que puede costar caro (una clave reutilizable por un
tercero) y solo **avisa** de lo que es higiene (una ruta con tu nombre). La
separación es deliberada: un check bloqueante que grita en falso se desactiva a
las dos semanas y entonces no protege de nada.

Corriéndolo sin argumentos valida todos los reportes de `reportes/`.

> Detalle a propósito: `_PLANTILLA.md` **falla** el validador. Es la prueba de
> que el check detecta una plantilla sin rellenar en vez de dejarla pasar.

## Qué pasa con tu reporte

Sigue el mismo ciclo que los documentos de diseño del repo:

1. **Llega** a `reportes/`.
2. **Se tría**: cada hallazgo va a donde le toca — un bug al registro de bugs,
   una decisión a un ADR, un arreglo a un pendiente del proyecto.
3. **Se cosecha**: cuando el hallazgo está cerrado, el reporte **se borra** del
   repo. La historia vive en git; lo durable vive en el ADR o en el bug.

Lo hecho **se borra, no se tacha**, igual que en el resto del setup. Un reporte
que se queda «pendiente» para siempre es el mismo tipo de basura que un catálogo
de skills que nadie construyó.

**Antes de borrar un reporte, comprueba que nada lo referencia** (`grep` del
nombre del archivo → 0). Quitar algo del sitio dejando referencias entrantes
vivas es exactamente el fallo que este repo ya se comió una vez.

## Lo que NO va en esta carpeta

- **Bugs del código de tus proyectos.** Esto es feedback del *setup*.
- **Peticiones de funcionalidad sin una sesión detrás.** Si no lo probaste, no
  es feedback: es una idea, y las ideas van por otro canal.
- **Reportes escritos sin que el humano los lea.** El paso 8 no es decorativo.
- **Cualquier cosa con un secreto dentro**, aunque el validador no lo cace: la
  lista de patrones es un cinturón, no una garantía.
