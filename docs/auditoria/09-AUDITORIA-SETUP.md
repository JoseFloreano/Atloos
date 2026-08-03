# Auditoría del Setup Completo
## Fortalezas, debilidades, riesgos y plan de mitigación

> **Banner (2026-08-01):** este doc es la foto de JULIO. Las mitigaciones que
> propone ya fueron **aplicadas** (fixes A1-A7/R1-R9, sesión "aplica todos los
> fixes") y el "nada está implementado aún" quedó obsoleto. Sigue siendo la
> referencia del *método* de auditoría, no del estado actual.

> **Fecha:** Julio 2026
> **Alcance:** Docs 00–08, todos los archivos de `setup/` (incluidos los añadidos en la sesión de skills/memoria), y la arquitectura Cowork + Claude Code.
> **Método:** Lectura línea por línea de cada archivo ejecutable, cruzada contra los hallazgos H1–H10 y las decisiones documentadas. Cada hallazgo cita el archivo y la evidencia. Incluye autocrítica de lo construido en esta misma sesión.

---

## 1. Resumen ejecutivo

La arquitectura conceptual es sólida — la investigación es honesta, las decisiones están justificadas y la capa durable (markdown en OneDrive) es la correcta. **El problema está en la brecha entre lo que los docs deciden y lo que los archivos ejecutables hacen.** La auditoría encontró 3 contradicciones internas donde los scripts implementan exactamente lo que los docs prohíben, y un camino de restauración de backups que probablemente no funciona.

| Capa | Calificación | Veredicto en una línea |
|------|:---:|------------------------|
| Arquitectura conceptual (docs 00–08) | 9/10 | Capas correctas, benchmarks tratados con honestidad |
| Vault Obsidian + convenciones | 8/10 | Base durable correcta; tensión git+OneDrive sin resolver |
| Sistema de skills (nuevo) | 8/10 | Modular y probado; fricción de actualización en Cowork |
| Aislamiento de memoria por proyecto | 7/10 | Reglas correctas pero probabilísticas — falta enforcement |
| Config Docker / Graphiti | 6/10 | Defaults contradicen las propias recomendaciones |
| Scripts de bootstrap | 5/10 | **Implementan Estrategia B mientras los docs mandan A** |
| Backups y recuperación | 4/10 | Windows sin automatización real; restore probablemente roto con AOF |
| Seguridad | 5/10 | API keys en OneDrive plano; puertos expuestos a la LAN |

**Los 5 hallazgos que hay que atender antes de implementar Fase 3** (detalle en §3): A1 datos de FalkorDB en OneDrive por default, A2 backup automático inexistente en Windows, A3 restauración probablemente inefectiva con AOF activo, A4 API keys en claro en OneDrive, A5 imágenes Docker en `:latest` cuando el propio doc 03 exige fijarlas.

Lo positivo del timing: **nada está implementado aún** (estado actual: checkboxes vacíos). Todos los hallazgos críticos son corregibles editando archivos, sin migrar nada.

---

## 2. Fortalezas — qué está bien y por qué importa

### F1. El principio "retrieval > dump" aplicado con disciplina
Toda la arquitectura se deriva de un solo principio correcto y verificado por terceros (Letta 74% vs Mem0 68.5%). Las 4 capas (Graphify/vault/Graphiti/CLAUDE.md) asignan la herramienta óptima a cada tipo de dato en vez de forzar un sistema único. Esto es lo contrario del over-engineering típico.

### F2. Cultura de benchmarks honesta (H10)
Los docs tratan los números de vendors como marketing, citan el caso donde Mem0 publicó datos desfavorables a sí mismo, y marcan las métricas de reducción de tokens como "casos individuales, no benchmarks controlados". Esa cultura es el mejor antídoto contra decisiones basadas en hype.

### F3. La capa durable es agnóstica al producto
Markdown en OneDrive funciona igual para Claude Code, Cowork, el humano y cualquier herramienta futura. Es inspeccionable, versionable y sin vendor lock-in. Fue la decisión que hizo trivial extender el setup a Cowork (`cowork-y-multiagente/08`).

### F4. Graphiti es opcional y está marcado como tal
Prioridad media, con sección explícita "Cuándo NO usar Graphiti" y el vault duplicando las decisiones importantes (ADRs). Si Graphiti falla o se abandona, la memoria esencial sobrevive. Pocos setups tienen esta degradación elegante diseñada.

### F5. Decisiones de sincronización basadas en limitaciones reales
Copias en vez de symlinks (H8), allowlist explícita en gitignore, credenciales identificadas como no-sincronizables, `CLAUDE_CONFIG_DIR` para multi-cuenta. El doc 04 es de lo mejor del repo.

### F6. El sistema de skills nuevo tiene las propiedades correctas
Una sola fuente de verdad, sync idempotente probado (manifest que permite borrar sin tocar skills manuales), fallbacks declarados en las skills compartidas, y el trigger automático depende solo de escribir buenas descripciones — que el template fuerza.

### F7. Config de Graphiti bien pensada en los detalles finos
Entity types custom para desarrollo (ArchitectureDecision, BugFix...), deduplicación a 0.85, SEMAPHORE_LIMIT documentado por tier de API, telemetría deshabilitada. Alguien pensó en el segundo orden.

---

## 3. Hallazgos críticos — contradicciones internas y bugs

Estos no son riesgos teóricos: son casos donde **el setup ejecutable hace lo que los docs prohíben**, o donde un camino crítico probablemente falla.

### 🔴 A1. Los scripts de bootstrap implementan Estrategia B, los docs mandan Estrategia A

**Evidencia:** `setup-new-machine.sh` genera `.env` con `FALKORDB_DATA_PATH=${GRAPHITI_DATA}/falkordb` donde `GRAPHITI_DATA=${ONEDRIVE}/DevSetup/graphiti-data` — es decir, **datos vivos de FalkorDB dentro de OneDrive**. `setup-new-machine.ps1` hace lo mismo y además reescribe la ruta a formato Docker apuntando al mismo OneDrive. El encabezado del `docker-compose.yml` dice "Datos en: ~/OneDrive/DevSetup/graphiti-data/ (portable)".

**Contradicción:** H2 ("FalkorDB + OneDrive directo = riesgo de corrupción"), anti-patrón 4 del doc 06 ("riesgo inaceptable porque la corrupción puede ser silenciosa"), y el propio `.env.example` cuyo default sí es correcto (`./data`). Quien siga el camino feliz del bootstrap termina exactamente en la configuración que la investigación calificó de inaceptable — y el `.env.example` correcto nunca se usa porque los scripts generan su propio `.env`.

**Impacto:** corrupción silenciosa posible del grafo; descubrible días después; agravada porque el backup automático tampoco funciona en Windows (A2).

**Mitigación (editar 3 archivos):** en ambos scripts, generar `FALKORDB_DATA_PATH` apuntando a disco local (`$env:LOCALAPPDATA\graphiti\data` en Windows, `~/.local/share/graphiti/data` en Unix) y dejar OneDrive solo para `backups/`. Corregir el encabezado del docker-compose. Añadir al script una validación explícita: si la ruta resuelta contiene "OneDrive", abortar con advertencia salvo flag `-ForceOneDrive`.

### 🔴 A2. En Windows no hay backup automático — el script que se agenda no existe

**Evidencia:** `setup-new-machine.ps1` registra una tarea de Task Scheduler que ejecuta `"$GraphitiDocker\backup-graph.ps1"` — pero ese archivo **no existe en el repo** (solo existe `backup-graph.sh`, bash) y nada lo copia ahí. El `if (Test-Path $backupScript)` hace que el paso se salte silenciosamente: el resumen final no avisa que quedaste sin backups.

**Impacto:** tu OS principal es Windows. La "Estrategia A: peor caso 4 horas de pérdida" (doc 07, decisiones validadas) es hoy "peor caso: todo, desde siempre". Combinado con A1, es el par de fallas que convierte un riesgo bajo en uno real.

**Mitigación:** escribir `backup-graph.ps1` (portar el .sh: BGSAVE → esperar LASTSAVE → docker cp → manifest → rotación), incluirlo en el repo, y que el setup lo copie antes de registrar la tarea. Si el paso falla, decirlo en el resumen final, no callar. Verificar además la sintaxis del trigger repetitivo (`-RepetitionInterval` sin `-RepetitionDuration` falla en algunas versiones de PowerShell 5.1).

### 🔴 A3. La restauración de backups probablemente no restaura nada (gotcha clásico de Redis/AOF)

**Evidencia:** el compose arranca FalkorDB con `--appendonly yes`. Con AOF habilitado, Redis/FalkorDB **carga desde los archivos AOF al arrancar e ignora `dump.rdb`**. Los tres caminos de restauración del setup (paso 6 del .ps1, paso 7 del .sh, y el `restore_cmd` del manifiesto de backup) copian solo `dump.rdb` y reinician — en una máquina donde el AOF ya existe, el servidor recargará el AOF viejo; en una máquina nueva, puede arrancar con grafo vacío e inmediatamente sobrescribir el estado.

**Impacto:** el mecanismo de recuperación —la única red de seguridad de la Estrategia A— puede fallar silenciosamente justo cuando se necesita. Nadie lo notaría hasta el primer desastre real, porque la restauración "termina sin error".

**Mitigación:** (1) documentar y automatizar el procedimiento correcto de restore: detener container → colocar `dump.rdb` → arrancar temporalmente con `--appendonly no` → verificar datos (`DBSIZE`) → `BGREWRITEAOF` → reactivar AOF; (2) hacer un **simulacro de restauración** al terminar la Fase 3 y repetirlo mensualmente — un backup no probado no es un backup; (3) opcional: respaldar el AOF de forma consistente en frío (con el container detenido) en vez del `docker cp` en caliente actual, que puede copiar un AOF a mitad de escritura.

### 🟠 A4. API keys en texto plano dentro de OneDrive

**Evidencia:** ambos scripts crean el `.env` (con `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) en `OneDrive/DevSetup/graphiti-docker/.env`; la estructura del doc 04 lo consagra. El anti-patrón 5 del doc 06 dice literalmente: "nunca en OneDrive sin cifrado".

**Impacto:** las keys viajan en claro a la nube de Microsoft y a cada laptop sincronizada; quedan expuestas ante cualquier acceso al OneDrive (phishing de cuenta Microsoft es el vector más común). El costo de una filtración es facturación ajena + rotación de todas las keys.

**Mitigación:** mover el `.env` a ruta local no sincronizada (`%LOCALAPPDATA%\graphiti\.env` / `~/.config/graphiti/.env`) y referenciarlo con `docker compose --env-file`; el bootstrap pide las keys una vez por máquina (son 2 valores — el costo de re-tecleo es trivial frente al riesgo). Alternativa si insistes en sincronizarlas: cifrado (age/sops) con la passphrase fuera de OneDrive.

### 🟠 A5. Imágenes Docker en `:latest` — el propio doc 03 exige fijarlas

**Evidencia:** `falkordb/falkordb:latest` y `falkordb/graphiti-knowledge-graph-mcp:latest` en el compose. La tabla de limitaciones del doc 03 dice: "MCP en estado experimental → fijar versión de imagen Docker".

**Impacto:** un `docker compose pull` en la laptop 2 puede traer una versión incompatible con el grafo escrito por la laptop 1 (formato RDB, esquema del grafo, API del MCP). Con datos compartidos vía backups, la versión divergente entre máquinas es un vector de corrupción lógica.

**Mitigación:** fijar tags concretos en el compose (elegirlos al implementar Fase 3), anotarlos en el manifiesto de backup, y actualizarlos deliberadamente en todas las laptops a la vez.

### 🟠 A6. El default del compose usa Anthropic experimental para extracción — contra H7

**Evidencia:** `LLM_PROVIDER=${LLM_PROVIDER:-anthropic}` y `MODEL_NAME=${MODEL_NAME:-claude-sonnet-4-6}` en el compose. H7 y el config.yaml recomiendan OpenAI. Como los env vars del compose **pisan** al config.yaml (jerarquía documentada en el propio archivo), un `.env` incompleto o ausente activa silenciosamente la ruta experimental — cuyo modo de fallo es precisamente "el episodio se guarda pero las entidades no se extraen", invisible.

**Mitigación:** cambiar los defaults del compose a `openai`/`gpt-4.1-mini`, o mejor: hacer que el MCP no arranque si `LLM_PROVIDER` no está definido explícitamente (fail-fast > default silencioso).

### 🟡 A7. Bugs menores encontrados de paso

- `backup-graph.sh` genera un `manifest.json` **inválido**: incrusta la salida multilínea de `INFO keyspace` cruda dentro de un string JSON (los saltos de línea rompen el JSON). Escapar o reducir a un campo simple (`db0_keys=N`).
- `setup-new-machine.ps1` solo convierte unidades `C:`/`D:` al formato Docker; otras letras de unidad fallan.
- El resumen final del `.sh` tiene un bug de sintaxis bash en la línea del título (`${BOLD}${FALKORDB_OK && ...}` no es una expansión válida — imprime literal o falla).
- `config.yaml` declara `queue.max_workers: 3` "debe coincidir con SEMAPHORE_LIMIT" — dos fuentes para el mismo valor; derivar una de la otra.

---

## 4. Riesgos por categoría (más allá de los bugs)

### R1. Proceso humano — el protocolo multi-laptop depende de memoria humana

La Estrategia A exige "docker compose stop + backup + esperar sync" antes de cambiar de laptop. Los humanos olvidan; el resultado es **fork silencioso del grafo** (laptop A y B con historias divergentes, el backup más reciente pisa al otro).
*Probabilidad: alta con el tiempo. Impacto: medio (pérdida parcial, confusión).*
**Mitigación:** el manifiesto de backup ya incluye `hostname` — úsalo: al arrancar, el setup/backup script compara el hostname del backup más reciente con el local y **avisa si otro host escribió después que tú**. Es la versión barata de un lock distribuido. Si el cambio de laptop es frecuente (varias veces/semana), reconsiderar Estrategia C (FalkorDB Cloud) — el costo mensual compra la eliminación completa de esta clase de riesgo.

### R2. Integridad de memoria — el aislamiento por proyecto es probabilístico

Las reglas de `memory-instructions.md` (group_ids obligatorios, carpetas de otros proyectos off-limits) son instrucciones a un LLM: compliance alta pero no garantizada, y degradándose en sesiones largas (el propio H4 documenta que la compliance cae con el volumen de instrucciones). El principio del doc 05 aplica: *"CLAUDE.md dice qué hacer; los hooks lo garantizan."*
*Probabilidad: media. Impacto: alto (es exactamente la alucinación cross-proyecto que quieres evitar).*
**Mitigación (Claude Code):** hook `PreToolUse` que inspeccione toda llamada a herramientas `graphiti-*`: si `add_episode` no lleva `group_id` o `search_*` no lleva `group_ids`, **bloquear** (exit 2). Es determinista, son ~15 líneas de script, y convierte la regla más importante del setup en una garantía. **Mitigación (Cowork):** no se pueden usar hooks sobre tu disco — reducir superficie: conectar al proyecto de Cowork solo `10-Projects/<proyecto>/` + `brain/`, no el vault completo. Lo que no está montado no puede contaminarse.

### R3. Integridad de memoria — fallos silenciosos de extracción y "memory rot"

Dos degradaciones lentas: (a) episodios cuyo texto se guarda pero cuyas entidades no se extraen (H7) — el grafo parece crecer pero no responde; (b) hechos y notas que envejecen sin invalidarse (el vault no tiene TTL; `_PROJECT.md` se actualiza "al cerrar sesión" solo si el agente cumple).
*Probabilidad: alta a 6+ meses. Impacto: medio — memoria que devuelve cosas viejas es peor que no tener memoria.*
**Mitigación:** la scheduled task quincenal de Cowork ya propuesta en `cowork-y-multiagente/08` §7, con checklist concreto: (1) muestrear 5 episodios recientes de Graphiti y verificar que `search_facts` los encuentra; (2) listar notas del vault con `updated` > 90 días y estado `active` para revisión; (3) detectar duplicados > 80%. La regla 5 de memory-instructions ("si el hecho contradice el presente, confía en el presente y actualiza") es la defensa en caliente — mantenerla.

### R4. Seguridad — superficie de red y de inyección

- **Puertos expuestos:** el compose publica `6379` (FalkorDB **sin password** — `FALKORDB_PASSWORD=` vacío), `3000` y `8000` (MCP sin auth) en todas las interfaces. En el wifi de un café, cualquiera en la LAN puede leer/escribir tu grafo de memoria. **Mitigación de una línea por puerto:** `"127.0.0.1:6379:6379"` etc. — con laptops, hacerlo siempre.
- **Skills como vector de inyección de instrucciones:** todo lo que esté en `claude-skills/` se convierte en instrucciones auto-cargadas para ambos agentes en todas tus laptops. Quien pueda escribir en tu OneDrive puede inyectar comportamiento. **Mitigación:** incluir `claude-skills/` en el repo git (excluyendo `_build/`) y revisar `git diff` ante cualquier cambio que no reconozcas; jamás copiar skills de terceros sin leerlas completas.
- **`.claude.json` compartido en Windows** (doc 04 ya lo documenta): riesgo de fuga de contexto entre cuentas si usas multi-cuenta simultánea — aplicar la solución de USERPROFILE aislado solo si de verdad corres instancias simultáneas.

### R5. Dependencias — ecosistema joven y proyectos pequeños

Graphify (v0.5.x, proyecto pequeño), MCP de Graphiti ("experimental", API puede cambiar), plugin Obsidian MCP (un mantenedor), Superpowers (sano: 200k instalaciones). El `smart_memory` del `.graphiti.json` depende de un PR reciente (#1209) — puede no comportarse como el template asume.
*Probabilidad: media-alta a 12 meses. Impacto: bajo-medio gracias a F4 (degradación elegante).*
**Mitigación:** el digest mensual de releases vía scheduled task de Cowork (ya propuesto); pinning de versiones (A5); y mantener la regla arquitectónica de que **el vault es siempre la copia canónica** — cualquier dependencia puede morir sin pérdida de conocimiento.

### R6. Vault — tensión git + OneDrive sin resolver

Doc 01 manda Obsidian Git *sobre* un vault que vive en OneDrive → el directorio `.git/` (miles de archivos pequeños que cambian en cada auto-commit de 10 min) se sincroniza por OneDrive, exactamente lo que el doc 04 clasifica como "funciona pero innecesario" y fuente de sync lenta/conflictos. Dos mecanismos de sincronización sobre la misma carpeta compiten.
**Mitigación (elegir una):** (a) vault en OneDrive + Obsidian Git con **remote en GitHub y `.git` excluido de OneDrive** (git detached: `core.worktree` o carpeta `.git` fuera del vault); (b) prescindir de OneDrive para el vault y usar solo git como transporte (pull al abrir, push al cerrar — el plugin lo automatiza); (c) aceptar el costo y monitorear. La opción (a) conserva lo mejor de ambos.

### R7. Presupuesto de contexto — la deuda se reacumula

El snippet `memory-instructions.md` endurecido (esta sesión) ronda los ~700 tokens; sumado al CLAUDE.md base del proyecto rompe el presupuesto de H4 (<500 tokens totales). Autocrítica directa: **al endurecer el aislamiento violé el hallazgo H4 del propio repo.**
**Mitigación:** comprimir el snippet a ~250 tokens dejando solo la identidad del proyecto + las 5 reglas de aislamiento en forma telegráfica, y mover formato de episodios, listas de qué guardar y ejemplos a una skill `memory-keeper` en `shared/` (se carga solo cuando se va a guardar memoria — progressive disclosure, que es exactamente para lo que existe el sistema de skills que acabamos de montar). El hook de R2 reduce además la necesidad de repetir la regla en prosa.

### R8. Skills — fricciones del sistema nuevo (autocrítica)

- **Staleness en Cowork:** el plugin `dev-skills` se re-sube a mano; las skills de Code se actualizan solas vía sync. Divergencia inevitable entre productos. *Mitigación:* la versión fechada en `plugin.json` ya delata el desfase; añadir al inicio de `cowork-project-instructions.md` la instrucción de avisar si la versión del plugin tiene > 30 días.
- **El sync no corre solo:** en las otras laptops hay que acordarse de correr `sync-skills`. *Mitigación:* tarea de Task Scheduler/launchd al login (una línea en el bootstrap).
- **Carrera de numeración de ADRs:** dos laptops offline pueden crear `ADR-007` ambas; OneDrive genera archivos "conflicto". *Mitigación:* cambiar la convención de la skill `adr-writer` a `ADR-YYYYMMDD-tema.md` — sin contador global, sin carrera.
- **bash 4+ en macOS** ya documentado en el header del script; riesgo residual bajo.

### R9. Costo y cuota

Cowork consume cuota significativamente mayor que chat (docs oficiales); las scheduled tasks se suman. Graphiti en OpenAI es negligible (~$1/mes). *Mitigación:* empezar con 2 scheduled tasks (no 6), revisar consumo real al mes, y mantener las auditorías quincenales — no diarias.

---

## 5. Matriz de riesgos consolidada

| # | Riesgo | Prob. | Impacto | Severidad | Mitigación clave | Esfuerzo |
|---|--------|:-----:|:-------:|:---------:|------------------|:--------:|
| A1 | Datos FalkorDB en OneDrive (bootstrap) | Alta | Alto | 🔴 | Rutas locales en scripts + validación anti-OneDrive | 1 h |
| A2 | Sin backups automáticos en Windows | Cierta | Alto | 🔴 | Escribir backup-graph.ps1 + avisar si falta | 1–2 h |
| A3 | Restore inefectivo con AOF activo | Media | Alto | 🔴 | Procedimiento de restore correcto + simulacro mensual | 2 h |
| A4 | API keys en claro en OneDrive | Media | Alto | 🟠 | .env local por máquina (--env-file) | 30 min |
| R2 | Aislamiento por proyecto sin enforcement | Media | Alto | 🟠 | Hook PreToolUse valida group_id; Cowork: montar solo carpeta del proyecto | 1 h |
| R4 | Puertos abiertos sin auth en LAN | Media | Medio | 🟠 | Bind a 127.0.0.1 en compose | 5 min |
| A5 | Imágenes Docker :latest | Media | Medio | 🟠 | Pinnear tags | 10 min |
| A6 | Default anthropic experimental en extracción | Media | Medio | 🟠 | Default openai o fail-fast | 10 min |
| R1 | Fork del grafo entre laptops | Alta | Medio | 🟠 | Check de hostname del último backup al arrancar | 1 h |
| R6 | .git del vault sincronizado por OneDrive | Alta | Bajo-Medio | 🟡 | Remote GitHub + .git fuera de OneDrive | 1 h |
| R3 | Memory rot / extracción silenciosamente fallida | Alta (6m+) | Medio | 🟡 | Auditoría quincenal Cowork (muestreo + stale report) | task |
| R7 | Snippet de memoria rompe presupuesto H4 | Cierta | Bajo | 🟡 | Comprimir a ~250 tokens + skill memory-keeper | 1 h |
| R8 | Staleness plugin Cowork / ADR race / sync manual | Media | Bajo | 🟡 | Versión fechada + ADR por fecha + tarea al login | 1 h |
| R5 | Churn del ecosistema (Graphify/MCP experimental) | Media | Bajo | 🟡 | Digest mensual + vault como copia canónica | task |
| A7 | Bugs menores (manifest JSON, unidades, echo) | Cierta | Bajo | 🟡 | Fixes puntuales | 30 min |

---

## 6. Plan de mitigación priorizado

### Antes de la Fase 3 (bloqueantes — nada de esto requiere migrar datos porque aún no hay datos)

1. Corregir rutas de datos en ambos bootstrap scripts → disco local (A1) + validación anti-OneDrive.
2. Escribir `backup-graph.ps1` e integrarlo al setup de Windows (A2).
3. Corregir procedimiento de restore para AOF + documentar simulacro (A3).
4. `.env` fuera de OneDrive con `--env-file` (A4).
5. En el compose: bind a 127.0.0.1, pinnear tags, default `openai` (R4, A5, A6). Son ~10 líneas.

### En la primera semana de uso real

6. Hook `PreToolUse` de validación de `group_id` (R2) — la garantía determinista del aislamiento.
7. Comprimir `memory-instructions.md` y crear skill `memory-keeper` en `shared/` (R7).
8. Check de hostname en el flujo de backup/arranque (R1).
9. Decidir la estrategia git-vs-OneDrive del vault antes de crear el vault (R6) — es gratis ahora, caro después.

### Continuo (delegable a Cowork)

10. Scheduled task quincenal: auditoría de vault + muestreo de Graphiti (R3).
11. Scheduled task mensual: digest de releases del ecosistema + recordatorio de re-subir `dev-skills.zip` si cambió (R5, R8).
12. Simulacro de restore mensual hasta que aburra, luego trimestral (A3).

### Criterios de salida (recomendación nueva)

Definir hoy, por escrito, cuándo se abandona un componente — evita la falacia del costo hundido:
- **Graphiti**: si tras 4 semanas de Fase 3 hay < 5 búsquedas útiles/semana, apagarlo y quedarse con vault (el doc 03 §9 ya insinúa este criterio; falta el número y la fecha de revisión).
- **Estrategia A**: si olvidas el protocolo de cambio de laptop 2 veces en un mes, migrar a FalkorDB Cloud.
- **Obsidian Git**: si genera > 2 conflictos/mes con OneDrive, elegir un solo mecanismo de sync.

---

## 7. Supuestos a verificar empíricamente (no confirmables desde docs)

| Supuesto | Cómo verificarlo | Cuándo |
|----------|------------------|--------|
| El comportamiento AOF-ignora-RDB aplica a la versión exacta de FalkorDB usada (A3) | Simulacro de restore con datos de prueba | Fase 3, día 1 |
| `REDIS_ARGS` es la variable que la imagen `falkordb/falkordb` respeta (vs `FALKORDB_ARGS`) | `docker exec ... redis-cli CONFIG GET appendonly` tras arrancar | Fase 3, día 1 |
| El MCP local de Graphiti se proxea a Cowork vía desktop app (`cowork-y-multiagente/08` §6.3) | Registrar el MCP y probar desde sesión Cowork | Fase 3 |
| `smart_memory` del `.graphiti.json` es honrado por la versión del MCP server | Guardar un episodio tipo Preference y verificar a qué group_id llegó | Fase 3 |
| El trigger repetitivo de Task Scheduler se registra bien en tu versión de PowerShell (A2) | `Get-ScheduledTaskInfo GraphitiBackup` tras 8 horas | Fase 3 |
| Las skills auto-disparan con descripciones en español mezclado con inglés | Prueba de 3 prompts por skill tras el primer sync | Fase 0 |

---

## 8. Conclusión

El setup tiene una arquitectura conceptual de primera y una ejecución de scripts que aún no le hace justicia: los tres hallazgos rojos (A1–A3) forman una cadena — datos en el lugar prohibido, sin backups en tu OS principal, y con restauración dudosa — que anularía en la práctica la principal garantía de seguridad del diseño. La buena noticia es doble: nada está implementado todavía (corregir es editar texto, no migrar datos), y ninguna corrección cuestiona las decisiones de fondo — al contrario, todas consisten en hacer que los archivos cumplan lo que los docs ya decidieron bien.

Prioridad sugerida si solo tienes una hora: A1 + los 10 minutos del compose (R4/A5/A6). Si tienes una tarde: todo el bloque "antes de la Fase 3".

---

*Este documento extiende la serie 00–08. Auditoría realizada sobre el estado del repo a julio 2026, previa a cualquier implementación. Los hallazgos A1–A7 citan archivos del directorio `setup/`; re-auditar tras aplicar las correcciones.*
