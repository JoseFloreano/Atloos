---
title: RFD — Context editing (clear_tool_uses), el ×32 que no se ha investigado
tags: [rfd, coste, contexto, cache, herramientas]
created: 2026-08-17
updated: 2026-08-17
status: propuesto
type: rfd
project: atloos
sprint: 14
fuente: docs/ecosistema/32-ANALISIS-COSTE-Y-HIGIENE.md
---

# 34 · RFD — Context editing

**Cero código. Decisiones numeradas.** Esto no activa nada.

## Por qué ahora

De la descomposición del `/cost` del 08-17: el **73 % de la factura es cache
read** ($226,72 de $310,91) y el caché ya acierta al **99,4 %** en el
coordinador. **No queda caché que exprimir. Lo que queda es tener menos que
releer.**

| Acción | Ahorro | Coste | Relación |
|---|---:|---:|---:|
| Cortar **50 k** de resultados viejos a mitad de sesión | $14,15 | $1,19 | **×12** |
| Cortar **100 k** | **$28,30** | **$0,88** | **×32** |

El mecanismo nativo es `clear_tool_uses_20250919`: borra **resultados de
herramienta** viejos del lado del servidor. Sin proxy y sin segundo canal — al
revés que headroom, que arbitramos en contra justo por eso.

---

## D1 · Qué se pierde, y por eso no todo es borrable

Un resultado borrado **no se puede releer**. La pregunta no es «¿cuánto
borramos?» sino «¿qué es **reconstruible**?».

**Regla propuesta: es seguro borrar lo que se puede volver a obtener con el
mismo comando y el mismo resultado.**

| Clase de resultado | ¿Borrable? | Por qué |
|---|---|---|
| `Read` de un fichero que sigue en disco | **Sí** | Se relee idéntico. Y si cambió, la versión vieja era *deuda*, no activo |
| `Grep`/`Glob` sobre el árbol actual | **Sí** | Reproducible mientras el árbol no cambie |
| `git log`/`git diff --stat` | **Sí** | Reproducible desde el sha |
| Salida de la suite (`run-tests.py`) | **Con cuidado** | Reproducible, pero cuesta ~55 s y el **verde vive en `gate-verde.json`**, no en el contexto |
| Salida de un comando **con efecto** (`git commit`, `push`, `merge --squash`) | **NO** | Irrepetible: correrlo otra vez no observa, actúa |
| Medición puntual (`/cost`, un reloj, `platform.node()` de otra máquina) | **NO** | El estado que midió ya no existe |
| Resultado de un `WebFetch`/MCP remoto | **NO** | La fuente puede haber cambiado y no lo sabrías |
| El fichero que el usuario **pidió** ver | **NO** | Borrarlo obliga a volver a pedírselo |

⚠ **El punto que este repo ya se ha comido dos veces**: lo peligroso no es
perder el dato, es **perderlo sin enterarte** y seguir razonando sobre un
recuerdo. Cualquier adopción tiene que dejar **marca visible** de qué se borró.
Un borrado silencioso es la misma enfermedad que el arnés que finge cobertura.

## D2 · `clear_at_least` y el punto de corte

Borrar **invalida el prefijo** y fuerza una reescritura de caché: por eso la
tabla tiene columna de coste. El corte no puede ser bajo.

- **Propuesta: mínimo 100 k tokens por operación** (×32), nunca 50 k salvo
  medición que lo justifique.
- **Y como mucho una vez por sesión larga.** Dos cortes son dos reescrituras: el
  segundo tiene que ganarse su propio ×N, no heredar el del primero.
- **Nunca en las primeras N vueltas.** Cortar pronto es cortar lo que aún vale;
  el ahorro está en lo viejo, y lo viejo requiere que la sesión sea larga.

**Abierto:** el número exacto de `clear_at_least` depende de cuánto ocupan los
resultados de herramienta frente al resto del contexto, **y hoy no lo sabemos**
— ver D4.

## D3 · Solapamiento con `/compact` y `memory-flush`

Las tres tocan el contexto y **no hacen lo mismo**:

| Pieza | Qué hace | Qué conserva |
|---|---|---|
| `/compact` (y `--autocompact`) | **Resume** toda la conversación | Un resumen: pierde literalidad, conserva hilo |
| `clear_tool_uses` | **Borra** resultados de herramienta viejos | La conversación íntegra: pierde material, conserva razonamiento |
| `memory-flush.py` (PreCompact) | **Bloquea** la compactación una vez y exige volcar al vault | Lo durable, fuera del contexto |

**No se estorban; se ordenan.** El orden correcto es **flush → clear →
compact**: primero lo durable sale a disco, luego se tira el material
reconstruible, y solo si aún no cabe se resume.

⚠ **Riesgo concreto y no hipotético:** `memory-flush` se dispara en `PreCompact`.
Si `clear_tool_uses` **retrasa o evita** la compactación, ese hook **deja de
dispararse** — y con él la última red que obliga a volcar al vault antes de
perder contexto. Adoptar el corte sin mover esa red apaga la capa 3 por efecto
secundario. **Es el mismo patrón que el perfil del bot sin hooks** (auditoría
31, H4): una optimización que apaga una vigilancia en silencio.

## D4 · Cómo se mide si funcionó

Hoy **no se puede**, y esa es la conclusión operativa de este RFD. El formato de
feedback recoge el total del `/cost`, no **de qué está hecho el contexto**.

Antes de activar nada hacen falta las tres columnas que ya pidió el análisis 32:

1. **Llamadas por herramienta, con bytes de salida acumulados.**
2. **El turno en el que entró cada salida grande** (lo que entra pronto se
   relee mucho más).
3. **Modelo por despacho.**

Y la medida de éxito **no es «bajó el cache read»** —eso baja también si la
sesión fue más corta—: es **cache read por turno**, contra una sesión
comparable. Sin ese denominador, adoptarlo sería otra creencia.

## D5 · Disponibilidad real — MEDIDO, no supuesto

Comprobado el 2026-08-17 en `claude-code 2.1.234`:

```
claude --help | grep -iE "context|clear"     → nada de context editing
claude --help | grep -i compact              → solo `--autocompact <auto|tokens>`
grep -r clear_tool_uses ~/.claude/settings.json .claude/settings.json → 0
```

`clear_tool_uses_20250919` es un parámetro de la **Messages API**
(`context_management`), y **Claude Code no lo expone** en su CLI ni en
`settings.json`. Lo que sí hay es `--autocompact`.

> **Conclusión: hoy no se puede activar desde nuestro harness, así que este RFD
> no propone activarlo.** Y eso es un resultado, no un fracaso.

⚠ **Límite de esta comprobación**: mide la superficie **documentada** (`--help`
y `settings.json`). No prueba que no exista una vía interna no documentada; si
alguien la encuentra, este apartado se reabre con la evidencia.

## Decisión

**No se adopta hoy.** Queda esto, en orden:

1. **Ampliar el formato de feedback** con las tres columnas de D4. Es barato y
   desbloquea todo lo demás — y sirve aunque el context editing no llegue nunca.
2. **Vigilar la exposición** en el CLI. Si aparece, se reevalúa con D1-D3 ya
   escritos.
3. **Si algún día se adopta**, mover la red de `memory-flush` antes de tocar
   nada (D3), porque ese es el daño colateral que no se ve.

Mientras tanto, la palanca que **sí** está disponible y ya está escrita es la
del sprint 13: **buscar dentro de un subagente**, cuyos resultados nunca entran
en el contexto del coordinador. No borra lo que ya entró, pero evita que entre —
que es más barato que cualquier ×32.
