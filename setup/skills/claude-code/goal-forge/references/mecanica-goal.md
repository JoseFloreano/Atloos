# La mecánica de `/goal`, desde la fuente

Todo esto sale de `code.claude.com/docs/en/goal`, no de blogs. **Corrección
importante**: el artículo más citado sobre `/goal` y `/loop` afirma que son
slash commands personalizados que uno escribe en `.claude/commands/goal.md`.
Es falso — son **nativos**.

## Los comandos

```text
/goal all tests in test/auth pass and the lint step is clean
/goal                 # estado: condición, duración, turnos, gasto, última razón
/goal clear           # también: stop, off, reset, none, cancel
```

## El ciclo

- Ponerla **arranca un turno inmediatamente**, con la condición como directiva.
- Tras **cada turno**, un modelo pequeño y rápido (Haiku por defecto) responde
  sí/no con una razón corta. Si es "no", esa razón **se le pasa a Claude como
  guía del turno siguiente** — o sea, una condición bien escrita no solo cierra
  la meta: dirige el trabajo. Si es "sí", la meta se limpia sola.
- Es **un envoltorio sobre un Stop hook de tipo `prompt`** con alcance de
  sesión. Por eso exige workspace de confianza y **no está disponible con
  `disableAllHooks` ni con `allowManagedHooksOnly`**.
- **No cambia permisos.** Para que los turnos corran desatendidos hay que
  emparejarlo con auto mode — y sin el guard, eso es un bucle autónomo con un
  evaluador que cree reportes: la peor combinación posible aquí.

## Y el dato que gobierna todo lo demás

> **El evaluador no llama a herramientas.** Solo puede juzgar lo que Claude ya
> volcó en la conversación.

No es un bug: la documentación lo dice y recomienda escribir la condición *"como
algo que la propia salida de Claude pueda demostrar"*. Es un contrato razonable
para el caso general. El caso general no es este proyecto.

## Los límites, con su consecuencia

| Límite | Qué implica al forjar |
|---|---|
| Una meta activa por sesión | Una nueva **reemplaza** a la anterior sin avisar |
| 4.000 caracteres | Suficiente; si no cabe, la meta son dos metas |
| Sobrevive a `--resume`/`--continue` | Pero **turnos, cronómetro y gasto se reinician** |

⚠ **El reinicio del contador es el que muerde.** En un servidor con
`MemoryMax=` y `Restart=on-failure`, cada kill devuelve la cláusula de corte a
cero: una meta que debía parar a los 20 turnos puede correr 20 más por cada
reinicio. La cláusula acota **una vida del proceso**, no la meta. Si el trabajo
va a correr desatendido, el techo real hay que ponerlo fuera
(`CLAUDE_CODE_MAX_TURNS`, o el propio `StartLimitBurst` de systemd).

## Headless

`claude -p "/goal …"` corre el bucle entero en una invocación. Con la salida de
texto por defecto **no imprime nada hasta cumplir la meta**: usa
`--output-format stream-json --verbose` o parecerá colgado.

## Perilla que NO es local

`ANTHROPIC_DEFAULT_HAIKU_MODEL` cambia el evaluador de `/goal`… y **también el
modelo de todo lo que use el modelo pequeño** (resúmenes de conversación,
funcionalidad de fondo). No la toques creyendo que solo afecta a las metas.

## Ejemplos forjados

**Mal — la cierra una frase:**
> el arnés del merge gate pasa y el código queda limpio

**Bien:**
> `py setup/hooks/tests/test-merge-gate-guard.py` imprime `23/23 casos OK` [repo]
> y `.claude/gate-verde.json` registra el sha del HEAD actual; sin tocar
> `setup/skills/`; o para a los 20 turnos

**Mal — dos metas disfrazadas de una:**
> los tests pasan y la documentación está actualizada

**Bien (la segunda mitad es otra meta, o no es medible y hay que decirlo):**
> `py -m pytest -q` sale 0 con 0 fallos; o para a los 15 turnos

## De dónde viene esta disciplina

No es nueva: son los **bloques 6 (predicción obligatoria)** y **7 (contrato de
reporte)** de `references/plantilla-despacho.md` de `workstream-dispatch`, que
ya obligan a decir qué esperas y cómo se comprueba. `goal-forge` es esa misma
disciplina comprimida a 4.000 caracteres y puesta donde el evaluador la lee.
