# Protocolo de escalación — el subagente para, el coordinador juzga

No hay canal vivo: el subagente **termina** en `NEEDS_CONTEXT` y el juez
**re-despacha** con la resolución inyectada en el brief. No existe un estado
"esperando ayuda".

---

## Los 6 disparadores por CATEGORÍA

**Obligatorios.** Ante cualquiera, el subagente **PARA y devuelve
`NEEDS_CONTEXT`. No adivina.**

1. Una **premisa del brief está contradicha** por lo que encuentra en el repo.
2. Necesita tocar **algo compartido o fuera de su ownership** declarado.
3. **Acción irreversible** sobre algo marcado "no toques".
4. Va a **exceder el presupuesto** del bloque 5 (máquina, esfuerzo o alcance).
5. Su **medición contradice su predicción** del bloque 6.
6. **Modificó —o necesita modificar— un test o fixture existente.**

## La válvula de confianza — solo como red final

Cualquier duda de baja confianza **no cubierta** por las 6 categorías: también
para.

**Por qué las categorías van primero y la confianza al final:** la confianza
auto-reportada está medida como señal casi inútil — AUROC **0,52–0,60**, apenas
sobre el azar [R], con hasta **+26% de sesgo** hacia lo propio. La escalación
por categoría de riesgo sí está medida en producción: **recall 92%** (Operator)
y **−58% de costo** con más éxito (AgentRunner) (doc 06 §2.3).

Un agente que se siente seguro no es un agente que acierta. Una categoría de
riesgo es objetiva.

---

## Formato de `NEEDS_CONTEXT`

**Nunca una pregunta desnuda.** Tres partes:

```
(a) QUÉ ENCONTRÉ, con evidencia
    paths, números, comandos y su salida. No "parece que...".
(b) 2-3 OPCIONES concretas
    qué se podría hacer, con su consecuencia.
(c) MI RECOMENDACIÓN y por qué
    cuál elegirías y qué te hace preferirla.
```

Sin (a) el juez no puede decidir sin re-investigar; sin (c) le devuelves el
problema entero. Bien hecho, el juez resuelve en una respuesta.

---

## Protocolo del juez (el coordinador)

**Resuelve con tu contexto global si puedes.** Tú ves los otros frentes, el
plan y las decisiones del día; el subagente no.

**Escala al usuario SOLO si:**

- la resolución es **irreversible**;
- toca **compuertas o allow-lists de seguridad** — la lección de la deriva del
  doc 05 §1.4: dos agentes ensancharon la misma allow-list y ninguno debía;
- es una **preferencia de producto o diseño** que no consta en ningún doc.

**TODA resolución se registra en `decisiones-del-dia.md` ANTES de
re-despachar.** Sin excepción: es la única atribución que funciona (la post-hoc
acierta el paso decisivo el 14,2% de las veces). Si no está escrita, el
siguiente frente tomará la decisión contraria.

---

## Fix-loop con tope de 5 rondas

| Ronda | Quién | Nota |
|---|---|---|
| 1–3 | El implementador **original** | Conserva el contexto de su trabajo |
| 4–5 | Implementador **fresco**, modelo más capaz | El original ya demostró que no lo ve |
| 5 | **El juez adjudica** | Aparcar con ruling registrado, o escalar al usuario |

**"Attempted ≠ addressed":** el re-review es *scoped* al issue concreto. Que el
implementador lo haya intentado no lo cierra; se cierra cuando el revisor lo
verifica.

Sin tope, el fix-loop se convierte en un bucle caro que nadie corta.

---

## Las tres prohibiciones del coordinador

1. **Nunca implementa él mismo lo que despachó.** Su contexto tiene que quedar
   limpio para juzgar. El crítico rinde mejor sin el contexto del autor
   (Cognition, doc 06 §3).
2. **Nunca paraleliza implementadores dentro del MISMO frente.** Lo prohíbe SDD
   y lo confirmó el C compiler de 16 agentes: sin descomposición previa, "se
   sobrescribieron entre sí".
3. **3 frentes simultáneos por defecto** (RFD 04 C5). Las fuentes externas
   convergen en 3–5. El nuestro es **un dato con fecha, no un techo**: una
   medición del 2026-08-10 sin repetir, hecha en otra máquina (`ProgramadoMaxi2`)
   cuyo tamaño no consta. ⚠ Y ojo, que
   esta línea decía «nuestro techo real fue la RAM» mientras el resto de la
   skill lo atribuía a la CPU: **dos causas distintas para el mismo número, y
   ninguna comprobada**. Se re-mide con `references/medir-el-techo.md`.
