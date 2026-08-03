# El Vault con Dos Agentes Concurrentes
## Qué pasa realmente, el misterio de "edita en una copia", y los patrones seguros

> **Fecha:** Julio 2026
> **Disparador:** al correr dos agentes de Claude a la vez sobre el vault, se observó que cuando uno edita un archivo (RFD), el otro "lo hace en una copia". Este doc explica el mecanismo real, cómo diagnosticar qué capa creó la copia, y cómo trabajar multi-agente sin perder datos.
> **Método:** documentación oficial de Anthropic/Microsoft/Obsidian + issues del repo de Claude Code + código fuente del plugin Obsidian Git. Lo no verificable está marcado.

---

## 1. La respuesta corta

**Claude Code no tiene ningún mecanismo de "editar en una copia".** Lo que existe es esto:

1. Claude Code **no usa file locking**. Su única protección es una detección optimista por timestamp: el tool `Edit` exige un `Read` previo, y si el archivo cambió después de esa lectura (porque el OTRO agente lo escribió), falla con:

   > `File has been modified since read, either by the user or by a linter. Read it again before attempting to write it.`

2. Cuando ese error se repite (dos escritores activos = se repite), **el agente improvisa**. Comportamientos documentados en issues: reintenta, omite ediciones en silencio, o cae a `Write` reescribiendo el archivo completo — y ahí **gana el último escritor** (lo del otro agente se pierde sin aviso). Comportamiento reportado pero sin fuente primaria formal: crear una variante — `Nota 2.md`, `Nota-v2.md`, `Nota (copia).md` — para "no pelear" por el archivo.

**Lo que viste es casi seguro el punto 2**: el segundo agente falló su `Edit` una o más veces y decidió, por su cuenta, escribir en un archivo nuevo. No es una feature — es un agente rodeando un conflicto que el sistema no arbitra. El resultado es peor que el error: memoria fragmentada en dos archivos que ya nadie reconcilia.

---

## 2. Diagnóstico: qué capa creó la copia

Cuatro capas rodean el vault y cada una deja una huella distinta. Compara el nombre del archivo duplicado:

| Mecanismo | Huella característica | ¿Aplica a tu caso? |
|-----------|----------------------|---------------------|
| **Agente Claude improvisando** | Nombres ad-hoc: `RFD 2.md`, `RFD-v2.md`, `RFD (copia).md`, `RFD-updated.md` — sin patrón fijo | ✅ Lo más probable |
| **OneDrive** | `RFD-NOMBREDEPC.md` (añade el nombre del equipo; formato documentado por Microsoft, hasta 5 copias) | Solo si escriben DOS MÁQUINAS — dos procesos en la misma máquina jamás generan conflicto OneDrive (hay una sola réplica local) |
| **Obsidian (núcleo / File Recovery)** | Ninguna — Obsidian recarga el archivo ante cambios externos, nunca crea copias; File Recovery guarda snapshots FUERA del vault | ❌ Descartado |
| **Obsidian Git** | Nota `conflict-files-obsidian-git.md` + marcadores `<<<<<<< HEAD` DENTRO de las notas (verificado en su código fuente) | Solo en pull/merge entre máquinas |
| *(Dropbox, para referencia)* | `RFD (conflicted copy 2026-...).md` | No usas Dropbox |

También descartado: el checkpointing/rewind de Claude Code guarda sus snapshots en `~/.claude/file-history/` con nombres hasheados — nunca crea copias visibles junto al original.

**Verificación en tu vault (2 min):** busca los duplicados y clasifícalos con la tabla. Si no llevan nombre de PC ni marcadores git → fue el agente.

---

## 3. Performance del vault con 2 agentes: el costo real no es velocidad

Leer/escribir markdown es trivial para el filesystem — dos agentes no degradan el rendimiento del vault de forma medible (doc 07: retrieval en filesystem <10ms). **El costo real de la concurrencia es la integridad:**

- **Lost updates:** A lee, B escribe, A escribe (vía `Write` tras fallar `Edit`) → lo de B desaparece sin error.
- **Fragmentación:** las "copias" improvisadas parten la memoria en archivos paralelos que las skills (`project-resume`, `adr-writer`) no saben reconciliar — la búsqueda encuentra versiones contradictorias.
- **Amplificación por Obsidian Git:** auto-commit cada 10 min fotografía el estado que haya — incluidas copias huérfanas y pisadas a medias.
- **Amplificación por OneDrive (multi-laptop):** si además el segundo escritor está en otra máquina, se suman conflictos `-NOMBREDEPC` de OneDrive.

La postura oficial de Anthropic para paralelismo confirma el diagnóstico: **la doc de Common Workflows recomienda git worktrees** (`claude --worktree`) precisamente "para que las ediciones no colisionen" — es decir, el producto asume que dos sesiones en la misma carpeta SÍ colisionan.

---

## 4. Patrones seguros para 2+ agentes (del más simple al más robusto)

### P1 — Particionar por proyecto (ya lo tienes — solo respétalo) ⭐

Tus reglas de aislamiento ya dicen que cada sesión toca SOLO `10-Projects/<su-proyecto>/`. **Dos agentes en proyectos distintos no comparten ningún archivo y la concurrencia es un no-problema.** La colisión solo ocurre si ambos trabajan el mismo proyecto — evita eso como configuración por defecto.

### P2 — Un escritor por archivo (mismo proyecto)

Si dos agentes deben trabajar el mismo proyecto: reparte la **propiedad de archivos**, no el archivo. Agente A es dueño del RFD/ADR (escribe); B lo lee y propone cambios en el chat o en `sessions/<fecha>-B.md`. Regla simple: quien creó/abrió el documento en esa sesión es el único que lo escribe.

### P3 — Archivos por-agente para lo concurrente

Lo que ambos necesitan escribir a la vez (notas de sesión, hallazgos) va a archivos separados por agente: `sessions/2026-07-22-agente-a.md` / `...-agente-b.md`. Un humano (o una sesión posterior) consolida. Append a archivos distintos = cero conflictos.

### P4 — Para código: worktrees (la vía oficial)

En repos de código, `claude --worktree <nombre>` da a cada sesión su checkout aislado — es la recomendación oficial y Superpowers trae `using-git-worktrees`. **No aplica al vault** (el vault es una sola réplica sincronizada, no un repo por-rama) — por eso el vault necesita P1–P3.

### P5 — Si la escritura concurrente se vuelve necesidad real: Graphiti

Este es exactamente el problema que una cola de episodios resuelve: `add_episode` es asíncrono y sin contención de archivos — N escritores no se pisan. Si el trabajo multi-agente sobre la misma memoria se vuelve frecuente, es el mejor argumento práctico para activar la Fase 3 (con la ruta Gemini gratis del README).

---

## 5. La regla anti-copias (lista para pegar)

Añadir a `memory-instructions.md` / `cowork-project-instructions.md` (y por esta vía a las skills) cuando decidas aplicarla — por ahora solo documentada aquí:

```markdown
## Concurrent-write rule
If Edit fails with "File has been modified since read": re-read and retry ONCE.
If it fails again, another writer is active on this file — STOP and tell the user.
NEVER work around it by creating a copy/variant of the file (RFD 2.md, -v2, (copia));
fragmented memory is worse than a paused edit.
```

Y su complemento operativo: antes de lanzar dos agentes sobre el mismo proyecto, decide quién es dueño de qué archivo (P2) o dales proyectos distintos (P1).

---

## 6. Protocolo de prueba en tu máquina (10 min, reproducible)

1. Crea `10-Projects/_test-concurrencia/nota.md` con 3 líneas.
2. Abre dos sesiones de Claude Code en la misma carpeta. Pide a AMBAS: "lee nota.md y luego agrega una línea con tu marca (A/B) al final".
3. Observa: una debería recibir `File has been modified since read` en el primer intento de Edit.
4. Registra qué hace el agente que falló: ¿re-lee y reintenta (bien)? ¿reescribe todo con Write (riesgo de pisar)? ¿crea `nota 2.md` (el bug que viste)?
5. Repite con la regla del §5 pegada en el CLAUDE.md del proyecto de prueba → el agente que falla debe parar y avisar en vez de crear copias.
6. Limpieza: borra `_test-concurrencia/`. Si el vault está en OneDrive y quieres ver la huella `-NOMBREDEPC`, repite el experimento con la laptop 2 como segundo escritor (requiere editar casi simultáneamente).

Resultado esperado tras aplicar la regla: cero archivos nuevos no solicitados, y el conflicto se reporta en vez de esconderse.

---

## 7. Fuentes

**Claude Code:** [Common workflows — parallel sessions with worktrees](https://code.claude.com/docs/en/common-workflows) · [Worktrees](https://code.claude.com/docs/en/worktrees) · [Checkpointing](https://code.claude.com/docs/en/checkpointing) · issues [#28383](https://github.com/anthropics/claude-code/issues/28383), [#48390](https://github.com/anthropics/claude-code/issues/48390), [#3513](https://github.com/anthropics/claude-code/issues/3513) (degradación del agente al fallar Edit), [#12891](https://github.com/anthropics/claude-code/issues/12891) (variante Windows).
**OneDrive:** [Microsoft Learn — Troubleshoot sync issues](https://learn.microsoft.com/en-us/troubleshoot/sharepoint/sync/troubleshoot-sync-issues) (formato `Archivo-NOMBREDEPC`).
**Obsidian:** [File Recovery (oficial)](https://help.obsidian.md/Plugins/File+recovery) · [foro: recarga ante cambios externos](https://forum.obsidian.md/t/monitoring-for-external-changes/51660).
**Obsidian Git:** [constants.ts — CONFLICT_OUTPUT_FILE](https://raw.githubusercontent.com/Vinzent03/obsidian-git/master/src/constants.ts) · issues [#803](https://github.com/Vinzent03/obsidian-git/issues/803), [#617](https://github.com/Vinzent03/obsidian-git/issues/617).

**Marcado como no verificable:** el patrón exacto "crear archivo-copia" del agente no está documentado formalmente por Anthropic (los issues documentan reintentos, omisiones y fallback a Write); queda confirmable con el protocolo del §6.

---

*Doc 12 de la serie. Relacionado: `cowork-y-multiagente/08` §6 (Cowork y el puente), doc 07 H2/H8 (OneDrive), auditoría R2 (enforcement > instrucciones — la regla del §5 es el mismo principio aplicado a concurrencia).*
