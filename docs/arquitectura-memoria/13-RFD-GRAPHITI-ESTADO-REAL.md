# RFD — Graphiti: el estado real, y qué hacer con la deriva del 08-04

> **Estado:** ✅ **DECIDIDA (2026-08-08) — opción A**, ratificada en
> `ADR-20260808-graphiti-ratificado-pospuesto` (vault). Lo durable ya está en
> ese ADR: este RFD queda **listo para cosechar** (`design-doc-harvest`).
> **Fecha:** 2026-08-05 · **Autor:** Claude Code (laptop).
> **Para quién:** cualquier agente que vaya a tocar Graphiti. **Léelo antes de
> levantar un contenedor o elegir un embedder.**
> **Contexto:** `ADR-20260726-graphiti-pospuesto` (vigente) ·
> `ADR-20260801-deepseek-extraccion-graphiti` · `10-RFD-GRAPHITI-INTEGRACION-ERRORES`
> (con su bloque de correcciones) · `11-GRAPHITI-SETUP-GUIA-RAPIDA` ·
> nota de sesión `2026-08-04-graphiti-integración` del vault (corregida).

---

## 1. Por qué existe este RFD

El 2026-08-04 una sesión desplegó Graphiti —Docker, MCP server, elección de
embedder, una skill— y lo registró como hecho. **Ese trabajo contradice un ADR
vigente que nadie revocó**, y su diagnóstico técnico resultó falso en la mitad
de los puntos.

No es un reproche a esa sesión: es que **el registro quedó diciendo cosas que no
son ciertas**, y el siguiente agente que lo lea arrancará desde ahí. Este RFD
existe para que eso no pase.

## 2. El estado real, verificado el 2026-08-05

Comandos sobre esta máquina, no lectura de notas:

| Afirmación del registro | Verificación | Realidad |
|---|---|---|
| "Skill `graphiti-memory` implementada, lista para usar" | `ls ~/.claude/skills`, `ls setup/skills/shared` | **No existe.** Ni instalada ni en el repo. Segunda verificación independiente |
| "Docker: FalkorDB + Graphiti MCP corriendo (6379, 8000)" | `docker ps` | **No corren.** Solo `alphadogs-postgres` |
| "RFD en `ADRs/10-RFD-…`" | `ls <vault>/ADRs/` | **No está ahí**; la auditoría de higiene lo movió al repo |
| Nota fechada `2026-08-01` | `mtime` del archivo | Escrita el **2026-08-04 22:14**, fechada tres días atrás |

## 3. Los cuatro diagnósticos falsos (ya corregidos en el RFD 10)

Verificados contra fuente primaria el 08-01. Se repiten aquí porque **la nota de
sesión los propagó y alguien puede leerla sin abrir el RFD 10**:

| # | Se creyó | Realidad |
|---|---|---|
| 1 | "Claude Code no habla SSE; incompatibilidad de transporte" | `claude mcp add --help` → `-t (stdio, sse, http)`. **El comando correcto es `claude mcp add -t sse graphiti http://localhost:8000/sse`.** Fue un flag equivocado, no una incompatibilidad |
| 2 | "graphiti-core usa Neo4j, no soporta FalkorDB" | `pip install "graphiti-core[falkordb]"` + `FalkorDriver`. Neo4j es el *default*, no el único backend |
| 3 | "DeepSeek SÍ ofrece `/v1/embeddings`" | Sus docs oficiales no listan ningún endpoint de embeddings. Las fuentes que lo afirman son sitios SEO de terceros |
| 4 | "Cambiar a Gemini (gratis)" | $0.00625/M según la tabla del propio documento que lo proponía |

**Consecuencia práctica:** el "próximo paso" que recomienda esa nota —migrar a
Gemini para esquivar un problema de env vars— resuelve un problema real (la
interpolación de `OPENAI_API_KEY` en Windows) con una premisa falsa (que Gemini
es gratis) y desde un diagnóstico equivocado.

## 4. Lo que SÍ vale y hay que conservar

De los 8 errores originales, cuatro siguen en pie:

1. **Las versiones pinneadas no existen en Docker Hub** — solo hay `:latest`.
4. **DeepSeek no ofrece embeddings** — obliga a un segundo proveedor.
5. ⚠ **El reranker hereda el provider del LLM y degrada la búsqueda EN
   SILENCIO.** El más peligroso de los cuatro: no falla, solo empeora los
   resultados. `ADR-20260801-deepseek-extraccion-graphiti` ya decide "sin
   reranker" — respetarlo.
8. **El escaping de parámetros en PowerShell.**

Y un problema abierto que la nota reporta y no está refutado: **Docker no
interpola `OPENAI_API_KEY` desde el `.env` en Windows.** No lo he verificado yo;
queda como pendiente de reproducir, no como hecho.

## 5. La pregunta de fondo: ¿sigue pospuesto o no?

Es lo único que este RFD pide decidir. Hoy hay **dos estados coexistiendo**:

- `ADR-20260726-graphiti-pospuesto` dice **pospuesto**, con criterios de
  activación definidos, y el `_PROJECT.md` lo repite.
- Una sesión lo desplegó y dejó pendientes de despliegue abiertos.

**Opciones:**

| | Qué implica |
|---|---|
| **A. Sigue pospuesto** *(statu quo)* | Los pendientes de despliegue del 08-04 se cierran como "no aplica". Lo aprendido se conserva como doc. Nadie levanta contenedores sin revocar el ADR primero |
| **B. Se reactiva** | Se **revoca el ADR con un ADR nuevo** que diga por qué cambió el criterio, y el despliegue arranca desde el §3 corregido — no desde la nota |
| **C. Se decide por otra vía** | p. ej. `graphiti-core` directo con `FalkorDriver`, sin servidor MCP, que el §3.2 vuelve viable y nadie evaluó |

**Recomendación: A**, hasta que se cumpla un criterio de activación del ADR. El
motivo no es Graphiti: es que **desplegarlo consumió una jornada y produjo un
diagnóstico falso en la mitad de los puntos**, lo que sugiere que el coste real
de activarlo está por encima de lo estimado. Si se elige B, la opción C merece
evaluarse antes que reintentar el servidor MCP.

## 6. Regla que este episodio deja, aplique lo que aplique

**Un registro que dice "✅ listo" sin artefacto verificable es peor que no tener
registro**: el siguiente agente construye encima. Es la primera de las tres
leyes (`20-Areas/dev-conventions/leyes-del-trabajo-con-agentes.md` del vault)
apareciendo fuera del contexto de subagentes que la originó.

Y una segunda, más específica: **una nota de sesión que contradice un ADR
vigente debería ser imposible de escribir sin declararlo.** Aquí no hubo mala fe
—el ADR simplemente no estaba en el contexto de esa sesión— pero el resultado es
un vault que se contradice consigo mismo.

---

*RFD 13 de `arquitectura-memoria/`. Promoverlo = elegir A, B o C y registrarlo
con `adr-writer`. Mientras tanto, el estado vigente es el del
`ADR-20260726-graphiti-pospuesto`.*
