# Skills Propuestas
## Qué NO crear (ya existe), qué sí, y el plan de adopción

---

## 1. Qué NO crear — ya cubierto

| Necesidad | Ya cubierto por | Por qué no duplicar |
|---|---|---|
| Aislamiento por rama/worktree | `claude --worktree` (nativo) + `using-git-worktrees` (Superpowers) | Mecanismo probado, cero instalación |
| Decidir si 2+ tareas son de verdad independientes | `dispatching-parallel-agents` (Superpowers) | Es exactamente el criterio del doc 02 §1 |
| Repartir un plan entre tareas independientes | `subagent-driven-development` (Superpowers) | Cubre la orquestación dentro de la sesión |
| Verificar antes de decir "listo" | `verification-before-completion` (Superpowers) | El gate de merge (§3 doc 02) lo asume como prerrequisito, no lo reemplaza |
| Decidir cómo integrar una rama terminada | `finishing-a-development-branch` (Superpowers) | Genérico — nuestro `workstream-merge-gate` (abajo) lo especializa con nuestros criterios, no lo sustituye |
| File-ownership + contratos de interfaz al descomponer | `parallel-feature-development` del plugin `agent-teams` (wshobson, evaluado en doc 13, no instalado) | Instalar cuando el caso de uso aparezca — protocolo doc 10 §2 |
| Elegir modelo/costo por etapa | `model-benchmark`, `token-audit` (ya existentes) | Aplicar antes del fan-out, no crear una versión "workstreams" de lo mismo |

## 2. Skills propias nuevas — huecos verificados

### 2.1 `workstream-merge-gate` (`shared/`) — prioridad 🔴 alta

Generaliza el `/merge` del RFD 02 C4 fuera del contexto del puente Telegram,
para usarse igual desde una sesión normal de Claude Code cuando un agente
coordinador integra el trabajo de uno o más workstreams.

**Contenido mínimo:**
- No mergear sin verificación (tests/lint) verde después del último commit
  del frente.
- Un frente a la vez; orden explícito si hay más de uno pendiente.
- Squash por defecto; mensaje que resume el frente, no el detalle de commits.
- Limpieza tras integrar: borrar worktree y rama local ya mergeada.
- Si el destino es `main` (o la rama protegida del repo) y hay riesgo real:
  pedir confirmación explícita antes de ejecutar — mismo criterio que el botón
  caduco de C4, adaptado a texto en vez de UI de Telegram.

**Requisitos (regla 3 del `_template`):** comando de test declarado por el
usuario o inferido del proyecto; fallback si no hay ninguno: avisar y no
mergear (igual que "sin `test` en `projects.json`" bloquea `/merge` en el
RFD 02).

### 2.2 `workstream-memory-briefing` (`shared/`) — prioridad 🟠 media

Cierra el hueco S4 (doc 00): antes de lanzar un teammate/subagente a un
workstream sobre UN proyecto con Memory Rules propias, le inyecta el resumen
de esas reglas (`group_ids` permitidos, carpetas de vault en las que puede
leer/escribir, si el modo es solo-lectura) desde el `CLAUDE.md` del proyecto
activo — nadie externo (Agent Teams, el plugin de wshobson) lo hace por
diseño, porque no conocen este sistema de memoria.

**Contenido mínimo:**
- Extraer la sección "Memory Rules" (o equivalente) del `CLAUDE.md` del
  proyecto antes de crear cada worktree/teammate.
- Incluirla literal en el prompt inicial de cada frente — no resumida, para
  no perder matices (regla de `writing-skills`: la instrucción debe ser
  ejecutable, no un resumen que invite a saltársela).
- Si el proyecto no tiene Memory Rules propias (no está enganchado al vault),
  decirlo y continuar sin bloquear — no todo proyecto las necesita.

**Nota:** esta skill solo tiene sentido si el patrón usa Agent Teams o
subagentes reales lanzados por separado (no si el propio usuario abre 2-3
sesiones de `claude --worktree` a mano — ahí cada sesión ya carga su propio
`CLAUDE.md` sin intermediarios).

### 2.3 Backlog, no crear todavía: presupuesto por fan-out

La necesidad ("no abrir 6 frentes sin saber el costo") ya la resuelve
`token-audit` si se invoca antes de decidir cuántos workstreams abrir — no
amerita una skill nueva. Revisar solo si en el uso real se repite 3+ veces
pedir esto y `token-audit` no encaja bien (regla de "3 repeticiones → skill"
del doc 16 de la subserie ecosistema).

## 3. Tabla resumen

| Skill | Carpeta | Origen | Prioridad |
|---|---|---|---|
| `workstream-merge-gate` | `shared/` | Propia (generaliza RFD 02 C4) | 🔴 Alta |
| `workstream-memory-briefing` | `shared/` | Propia (cierra hueco S4) | 🟠 Media |
| `agent-teams` (plugin) | marketplace, no `claude-skills/` | wshobson, ya evaluado doc 13 | 🟡 Instalar solo cuando el caso de uso aparezca |

## 4. Plan de adopción

1. **Piloto sin skill nueva.** Probar el patrón del doc 02 con 2 frentes
   reales en un proyecto de bajo riesgo, usando solo lo ya instalado
   (`--worktree` + Superpowers) y aplicando el gate de merge A MANO. Medir
   costo real vs. la estimación de §5 del doc 02.
2. **Si el patrón se repite:** escribir `workstream-merge-gate` primero (es
   la pieza que más falta y la de mayor retorno) y registrar la decisión
   con `adr-writer` si cambia algo del flujo de git del repo en cuestión.
3. **`workstream-memory-briefing` solo si de verdad se usa Agent Teams** o
   subagentes lanzados por separado con Memory Rules de por medio — si el
   patrón termina siendo "el usuario mismo abre 2-3 sesiones en worktrees
   distintos", ni siquiera hace falta: cada sesión ya hereda su propio
   `CLAUDE.md`.
4. **Instalar el plugin `agent-teams` de wshobson** únicamente cuando la
   descomposición con file-ownership explícito empiece a doler a mano —
   protocolo de importación completo (doc 10 §2, doc 05 §2) antes de copiar
   nada a `claude-skills/`.

## 5. Nota de honestidad (H10)

La mayoría de fuentes citadas en el doc 01 son blogs y guías de terceros
fechados en 2026, no documentación oficial (salvo `code.claude.com/docs`).
Las cifras de costo son casos individuales autoreportados, sin réplica
externa — tratarlas como orden de magnitud para decidir "¿vale la pena medir
esto en un piloto?", nunca como presupuesto exacto. El plan de adopción (§4)
está diseñado a propósito para medir con datos propios antes de comprometerse
a escribir o instalar nada.

---

*Cierra la investigación de `docs/subagentes/` (00–03). Nada de esto está
instalado: es investigación, igual que el resto de subseries del repo.*
