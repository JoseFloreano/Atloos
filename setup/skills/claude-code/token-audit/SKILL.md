---
name: token-audit
description: >
  Audita y reduce el overhead de tokens del setup de Claude Code: CLAUDE.md
  (presupuesto H4), MCPs conectados (H3), descripciones de skills y gasto real
  medido con ccusage//cost. Use when the user says "audita los tokens", "por
  qué gasto tanto contexto", "optimiza el CLAUDE.md", "cuánto overhead tengo",
  "token audit", or cuando las sesiones se sienten lentas/caras o el contexto
  se llena rápido.
---

# Token Audit

Aplica NUESTRAS reglas medidas (docs 05-07) al setup real de esta máquina.
Medir primero, recortar después — nunca al revés.

## Requisitos

- Claude Code local con acceso a `~/.claude/` y al proyecto activo.
- `ccusage` opcional (`npx ccusage@latest`) para gasto real; sin él, usa `/cost`
  y `/context` de la sesión.

## Presupuestos (la vara contra la que se audita)

| Componente | Presupuesto | Fuente |
|-----------|-------------|--------|
| CLAUDE.md global + proyecto | < 500 tokens c/u | H4 (3,847→312 = 91.9% menos overhead) |
| MCPs conectados | ≤ 8-10, con tool search activo | H3 (10-20k tokens/MCP sin lazy loading) |
| Descripciones de skills | ~40-60 tokens c/u; sin solapes | `skills/10` §8.3 |
| Instrucciones totales siempre-en-contexto | degradación sobre ~150 instrucciones | H4 |

## Pasos

1. **Mide el estado actual**: `/context` en una sesión del proyecto (desglose
   de qué ocupa la ventana); `npx ccusage@latest` para gasto por día/sesión
   (separa cache reads de input real — si el cache hit es bajo, hay churn de
   contexto). Anota números ANTES de tocar nada.
2. **CLAUDE.md** (global y por proyecto): cuenta tokens (~4 chars/token). Sobre
   presupuesto → aplica la cirugía H4: lo contextual se va a una skill
   (progressive disclosure), lo determinista a un hook, los ejemplos a
   references. Nunca borres las reglas de aislamiento de memoria.
3. **MCPs**: `claude mcp list` — ¿cuáles NO se usaron esta semana? Fuera del
   scope user (se re-agregan por proyecto cuando toquen). Verifica tool search
   activo. Recuerda H9: no conectar/desconectar mid-sesión.
4. **Skills**: revisa `~/.claude/skills/` — ¿descripciones infladas que resumen
   el workflow? ¿solapes de triggers entre vecinas? Recorta descripciones, no
   cuerpos (el cuerpo solo carga al disparar).
5. **Patrones de sesión**: contexto que se llena rápido = archivos enormes
   leídos completos, dumps de logs, falta de subagents para exploración.
   Recomienda los cambios de hábito concretos que apliquen.
6. **Re-mide y reporta**: mismos comandos del paso 1; entrega tabla
   antes/después (tokens de arranque, componentes recortados, ahorro estimado
   por sesión y por mes). Si el hallazgo es una convención nueva ("este MCP
   solo por proyecto"), regístrala con `memory-keeper` en dev-global.

## Qué NO hacer

- No recortes compliance por tokens: las reglas de memoria/aislamiento y los
  hooks se quedan — su costo está pagado por lo que previenen.
- No adoptes optimizadores de terceros sin auditar (el más popular del nicho
  tiene licencia no-comercial — ver doc 13).
