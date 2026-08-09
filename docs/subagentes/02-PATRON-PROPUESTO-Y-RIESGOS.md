# Patrón Propuesto y Riesgos
## Cómo componer las cuatro capas del doc 01 en un flujo usable

---

## 1. Escalera de decisión (reutiliza `agentic-system-design`)

No todo trabajo "con varias partes" justifica workstreams paralelos con rama
propia. Antes de montar nada:

1. ¿Las partes tocan **archivos distintos** de verdad, sin solapes? Si dos
   frentes necesitan editar el mismo archivo, **no son dos frentes** — es uno
   con una dependencia interna, y paralelizarlo solo compra un merge conflict.
2. ¿El trabajo de cada frente es lo bastante largo para pagar el overhead de
   un worktree + una rama + su propio contexto? Para cambios de minutos,
   `subagent-driven-development` (Superpowers) dentro de una sola sesión ya
   alcanza — sin ramas nuevas.
3. Solo si 1 y 2 se cumplen: workstreams paralelos, uno por rama/worktree.

## 2. El patrón, en cuatro pasos

```
1. DESCOMPONER          Un agente (o el humano) parte el trabajo en frentes
   con ownership          con límites de archivo explícitos. Manual con
                          using-git-worktrees, o con el preset --plan-first
                          del plugin wshobson si está instalado.

2. AISLAR                Un worktree + una rama por frente:
   por frente               claude --worktree <frente>   (nativo)
                          o Agent Teams si los frentes necesitan coordinarse
                            entre sí durante la ejecución (no solo al final).

3. VERIFICAR              Cada frente cierra con su propia verificación
   antes de ofrecer         (tests, lint) — verification-before-completion
                            (Superpowers) + finishing-a-development-branch
                            decide CÓMO se integra ese frente.

4. MERGEAR                UN agente coordinador (nunca cada frente) aplica
   con gate                el criterio de integración — ver §3.
```

El paso 4 es la pieza que ninguna capa externa resuelve con nuestro criterio:
es donde entra `workstream-merge-gate` (doc 03).

## 3. El gate de merge (generaliza C4 del `ADR-20260801-puente-telegram`, fuera del puente)

El `ADR-20260801-puente-telegram` ya lo resolvió para el contexto Telegram; el criterio traslada
igual a una sesión normal de Claude Code:

| Regla | Por qué |
|---|---|
| Sin test verde después del último commit del frente → no se mergea | Un merge sin verde es la forma más fácil de romper algo sin verlo (mismo principio que C4) |
| Orden de integración explícito, uno a la vez | Dos frentes mergeados "a la vez" sobre la misma base pueden generar conflictos que ninguno de los dos vio en su propio worktree |
| Squash por defecto | La historia de `main` queda legible; el detalle del frente vive en su rama hasta que se borra |
| Confirmación humana si el repo/rama destino es sensible | Mismo criterio de C4: botón solo para lo que toca `main` de verdad — no para cada commit intermedio |
| Limpieza tras integrar (worktree + rama local) | Evita el mismo problema de worktrees huérfanos que el `ADR-20260801-puente-telegram` ya resolvió con reconciliación al arrancar |

## 4. Qué mecanismo usar según el caso

| Caso | Mecanismo recomendado |
|---|---|
| 2-3 frentes que NO necesitan hablar entre sí durante la ejecución | `subagent-driven-development` + `using-git-worktrees` (Superpowers) — sin instalar nada |
| 2-5 frentes que sí necesitan coordinarse (contratos de interfaz a medio hacer) | Agent Teams nativo + worktrees; considerar el plugin wshobson por sus presets y el file-ownership explícito |
| Automatización sin humano en el loop, con verificación adversarial entre pasos | El Workflow de este entorno (`pipeline`/`parallel`, `isolation: 'worktree'`) — pero requiere opt-in explícito del usuario por su costo, no es el caso por defecto |
| Más de 5 frentes | Parar y preguntar por qué — doc 01 §1.2 y la fuente de costo (§5) coinciden en que pasar de 5 necesita una razón concreta, no solo "hay más trabajo" |

## 5. Riesgos y costo (cifras de terceros, orden de magnitud — H10)

- **Costo escala con el número de frentes activos**, no es gratis paralelizar:
  reportes 2026 sitúan un agente activo en ~$13 USD/día base, y 5 concurrentes
  pueden llevar el gasto diario a $50-65 USD. Un caso límite documentado (16
  agentes, ~2 semanas) llegó a ~$20,000 USD. Aplicar `token-audit`/
  `model-benchmark` (ya existentes) ANTES de decidir cuántos frentes abrir.
- **Conflictos de merge**: la causa #1 reportada es la misma que el doc 12 ya
  diagnosticó para el vault — dos escritores sobre el mismo archivo sin
  ownership claro. El paso 1 del patrón (ownership explícito) es la mitigación,
  no el gate de merge (que llega demasiado tarde para evitarlo, solo para
  detectarlo).
- **OneDrive**: si el repo vive sincronizado (como este), los worktrees de
  workstreams deben crearse **fuera** de la carpeta de OneDrive — mismo
  criterio H8/A1 que ya aplicó el `ADR-20260801-puente-telegram` (símlinks/archivos con lock no
  sincronizan bien; un checkout completo dentro de OneDrive añade tormentas
  de sync). Verificar dónde resuelve `.claude/worktrees/` por defecto en cada
  máquina antes de usarlo con un repo dentro de OneDrive.
- **Memoria (S4 de doc 00)**: sin briefing explícito, un teammate/subagente
  puede operar con el `group_id`/vault equivocado. No es un riesgo de
  terceros — es específico de este setup y solo lo cierra algo propio.
- **Rebases divergentes**: si un frente tarda mucho, `main` avanza bajo sus
  pies. El patrón no lo resuelve automáticamente — el coordinador debe decidir
  si rebasear el frente antes de mergear o si el frente ya quedó obsoleto.

## 6. Lo que esta investigación NO recomienda

- No instalar Agent Teams (flag experimental) como default para trabajo
  cotidiano de 1-2 frentes — el mecanismo nativo `--worktree` sin coordinación
  entre agentes ya alcanza y es más barato.
- No escribir un orquestador propio desde cero — las cuatro capas del doc 01
  cubren el mecanismo; construir uno nuevo repetiría el trabajo ya hecho.
- No aplicar este patrón a este mismo repo (`Atloos`) como caso de uso
  principal: es un repo de docs + scripts, sin código de aplicación con
  módulos independientes que se presten a ownership por archivo. El caso de
  uso real está en los proyectos de aplicación del usuario (AlphaDogs,
  RecetIA, etc.), donde sí hay features con fronteras claras.
