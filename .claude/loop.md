# El bucle de Atloos

Sustituye el prompt de mantenimiento genérico de `/loop`. **Se relee en cada
iteración**, así que se afina con el bucle corriendo: si una vuelta sale mal,
edita este fichero y la siguiente ya obedece. Tope 25.000 bytes; sobra margen.

---

## Cada iteración

1. **Lee `10-Projects/atloos/_PROJECT.md`** y toma el **primer pendiente
   activo**. No el más fácil, no el que se te ocurra: el primero.
2. **Trabaja UNA unidad de él.** Una unidad es lo que cabe entre dos evidencias:
   un arnés que pasa de rojo a verde, un fichero que existe y antes no. Si no
   sabes decir cuál es la evidencia de esta vuelta, la unidad está mal cortada.
3. **Antes de reportarlo hecho, corre su arnés y pega la salida literal.**
   Sin salida pegada, no está hecho — lo diga quien lo diga.
   **Si no hay arnés, dilo y no lo des por hecho.** "Parece correcto" no es un
   estado; es una opinión sobre un estado que nadie miró.
4. **Registra en el vault lo que cambió**: pendientes/estado, 2-5 líneas.
   ⚠ Si hay **otro agente** trabajando este proyecto, escribe SOLO en tu nota
   `10-Projects/atloos/sessions/<fecha>-<tu-tarea>.md` y **no toques
   `_PROJECT.md`** — un archivo, un escritor.

## Cuándo pararse, que es lo que más importa

- **Bloqueado por una decisión del usuario → párate y dilo. No elijas por él.**
  Las decisiones abiertas del proyecto (D1-D9 de los RFD) no las cierra un
  bucle a las tres de la mañana.
- **La premisa del pendiente resultó falsa → párate.** Mal trabajo es peor que
  ningún trabajo; abortar es una salida legítima y no se penaliza.
- **Vas muy por encima del esfuerzo que la tarea pedía → párate y repórtalo.**
  Suele significar que la tarea no era la que creías.
- **Dos vueltas seguidas sin evidencia nueva → párate.** Un bucle que no
  converge gasta hasta que alguien mira.

## Lo que el bucle NO hace

- **No mergear a `main`.** El criterio es la skill `workstream-merge-gate` y
  exige **confirmación humana explícita**; un hook no puede preguntar y un
  bucle no puede consentir por ti.
- **No cosechar** (ni RFDs ni docs de diseño). La cosecha borra ficheros y se
  decide despierto.
- **No tocar otros proyectos del vault.** Solo `10-Projects/atloos/`,
  `brain/`, `daily/`.
- **No revocar, rotar ni publicar nada** hacia fuera: tokens, remotos
  compartidos, ramas del remoto. Eso es del usuario.

## Por qué este fichero existe

El prompt genérico de `/loop` es de mantenimiento y no conoce la ley 1 de esta
casa: **el código de salida no es el estado; el reporte no es el artefacto**.
Un bucle amplifica lo que se le dé. Con el prompt genérico, cuarenta turnos
producen cuarenta reportes; con este, producen evidencia o se paran.

Y el mapa manda sobre el motor: **un bucle solo converge si `_PROJECT.md` dice
la verdad.** Si al leerlo encuentras algo que el repo contradice —un pendiente
ya cerrado, un sha que no cuadra—, **arregla el mapa primero y dilo**. Servir
un hecho falso cuarenta veces es peor que no dar ninguna vuelta.
