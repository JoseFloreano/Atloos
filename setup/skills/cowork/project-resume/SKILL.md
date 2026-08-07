---
name: project-resume
description: >
  (Variante Cowork) Pone al día la sesión sobre un proyecto YA enganchado
  leyendo su memoria durable del vault de Obsidian conectado, para no empezar
  en frío. Use al INICIO de una sesión de Cowork sobre un proyecto, o cuando el
  usuario dice "retomemos X", "sigamos con", "ponte al día", "qué teníamos
  pendiente", "resume this project", "catch up". Solo lee y orienta, no
  modifica nada. Si el proyecto no tiene carpeta en 10-Projects/, dilo — el
  alta (project-onboard) se hace desde Claude Code.
---

# Project Resume (Cowork)

Carga el contexto durable de un proyecto existente al arrancar una sesión de
Cowork. **Solo lectura** — no escribe memoria ni commitea nada en este paso.

## Requisitos

- Carpeta del vault conectada a la sesión (`ObsidianVault/` o al menos
  `10-Projects/<proyecto>/`). Si no está conectada, PARA y pide al usuario
  conectarla con "Add folder" — sin vault no hay memoria que retomar.
- MCP `graphiti-memory` — **opcional** (solo existe vía puente del desktop
  app): si no está, omite su búsqueda en silencio; el vault es la fuente primaria.

## Pasos

1. Identifica el **proyecto activo**: de la sección "Active Project" de las
   instrucciones del proyecto de Cowork, o pregunta. Respeta el aislamiento:
   solo lee `10-Projects/<nombre>/` — carpetas de otros proyectos están
   OFF-LIMITS.
2. Stage-a y lee `10-Projects/<nombre>/_PROJECT.md` desde la carpeta conectada.
   Si no existe, el proyecto no está enganchado → sugiere correr
   `project-onboard` desde Claude Code y para.
   Si trae la línea `Backlog: N ítems → [[pendientes]]`, **menciónala sin stage-ar
   el archivo** ("hay N más en el backlog"): el arranque debe costar lo mismo
   que antes. Solo cárgalo si el usuario pregunta por el backlog.
   Compara **`Estado del repo:`** contra `origin/main`: si difieren, avisa
   *"el vault va atrás — tómalo como orientación, no como verdad"*. Si el campo
   no está (proyecto anterior a la convención), **dilo UNA vez**: `session-close`
   lo añadirá al cerrar. Sin repo conectado no se puede comparar: reporta
   **"no verificado"** — pero solo si el campo existe; si no, no fabriques ruido.
3. Stage-a **solo `ADRs/_INDEX.md`** y léelo: una línea por decisión con su
   `summary`. Stage-a un ADR completo únicamente si su fecha es ≥ la de la nota
   más reciente de `sessions/`, o si la tarea de hoy lo toca. Si `_INDEX.md` no
   existe, el proyecto no está migrado: stage-a los ~3 ADRs más recientes y
   dilo.
4. Revisa `bugs/` **solo los `status: open`** (`open | fixed | invalid | wontfix`).
   Stage-a solo lo que vas a leer — no la carpeta completa (anti-patrón de dump).

   > Presupuesto de arranque: si lo que vas a stage-ar y leer al arrancar pasa
   > de ~10 KB, algo está mal — dilo en vez de leerlo.
5. *(Solo si graphiti-memory está disponible)* `search_facts("recent decisions
   and known issues", group_ids=["<nombre>", "dev-global"])`.
6. **Resume al usuario** en pocas líneas: estado actual, decisiones clave, bugs
   conocidos y pendientes; pregunta en qué quiere continuar.
7. No modifiques nada aquí. Hallazgos → `memory-keeper`; decisiones →
   `adr-writer`; y recuerda que en Cowork todo cambio al vault debe
   **commitearse de vuelta** a la carpeta conectada al final.
