# Skills de Testing y Debugging: Investigación y Selección
## Qué adoptar, qué ya cubre Superpowers, y los huecos para skills propias

> **Fecha:** Julio 2026
> **Contexto:** Continúa el `skills/10` (catálogo de diseño/desarrollo) con las dos categorías que faltaban. Mismo método: fuentes primarias fetcheadas (SKILL.md leídos en raw), solapes verificados contra lo ya instalado (Superpowers, skills propias). Aplica el **protocolo de auditoría del `skills/10` §2** antes de instalar cualquier cosa de esta lista.
> **Stacks objetivo:** React/Next.js, Flutter/Dart, Python, C++.

---

## 1. Resumen ejecutivo

**Testing:** el punto de partida es no duplicar — `test-driven-development` y `verification-before-completion` (Superpowers) ya cubren el *proceso*; lo que falta es *tooling y técnica por stack*. Las adopciones con mejor relación valor/riesgo: `webapp-testing` (Anthropic, E2E web con Playwright), el pack `testing-handbook-skills` de Trail of Bits (fuzzing/sanitizers/coverage — oro para C++), `property-based-testing` (ToB, portable y multi-stack) y `flutter-tester` (Harishwarrior). Para Python, la colección de Matthew Honnibal (autor de spaCy) es pequeña pero de autor de primera línea.

**Debugging:** `systematic-debugging` (Superpowers) es más completo de lo que parece — verificado su SKILL.md: 4 fases con root-cause tracing, regla "no fix sin causa raíz", failing-test-first, e incluso esperas condicionales (timing/flaky parcial). **Casi todo lo que el ecosistema ofrece de "debugging metodológico" lo duplica** — se descarta. Lo que complementa: agentes especializados (build-resolvers de ECC, diagnostics de wshobson) y técnicas puntuales de performance/leaks. **Los huecos reales no los cubre nadie: son candidatos a skills propias** (§5).

| Decisión | Elementos |
|----------|-----------|
| ✅ Adoptar | webapp-testing · ToB testing-handbook (subset) · ToB property-based-testing · flutter-tester · honnibal (hypothesis/mutation) |
| ⚠️ Evaluar como plugin | wshobson `unit-testing`/`qa-orchestra` + plugins debugging/diagnostics |
| ❌ Descartar (duplican Superpowers) | wshobson TDD-workflow · 5-whys-skill · bug-fix de claude-mpm-skills |
| 🛠️ Skills propias (huecos verificados) | git-bisect asistido · flaky-tests · runbook gdb/sanitizers · golden tests Flutter |

---

## 2. Testing — catálogo verificado

### 2.1 `webapp-testing` (Anthropic, oficial) ⭐

Verificado su SKILL.md: usa **Playwright en Python** (no MCP) con `scripts/with_server.py` para levantar frontend/backend, capturar screenshots, logs de consola y descubrir selectores. Apache-2.0. **Dependencia:** `pip install playwright` + Chromium. Complementa (no duplica) a Superpowers: TDD es proceso, esto es verificación E2E ejecutable — encaja como el brazo web de `verification-before-completion`.
**Destino:** `claude-code/` (necesita el toolchain; en Cowork el sandbox también puede correr Playwright, pero contra apps locales no).

### 2.2 Trail of Bits `testing-handbook-skills` (16 skills) ⭐ para C++

Del Testing Handbook de ToB (appsec.guide): fuzzers (libFuzzer, AFL++, libAFL, cargo-fuzz, Atheris para Python), harness writing, **AddressSanitizer**, coverage analysis, diccionarios, OSS-Fuzz, más Semgrep/CodeQL y cripto (Wycheproof, constant-time). CC BY-SA 4.0, activo 2026. **Solape con Superpowers: cero** — nada de esto existe ahí.
**Matiz:** casi todas asumen binarios instalados (LLVM/clang, AFL++). Adoptar el subset del stack real: `addresssanitizer`, `coverage-analysis`, `fuzzing-harness` (C++), `atheris` (Python) — el resto cuando se necesite.
**Destino:** `claude-code/` con prefijo `tob-` (atribución CC BY-SA, igual que `skills/10` §8.1).

### 2.3 ToB `property-based-testing` ⭐ el más portable

Verificado: hub de decisión + referencias (roundtrip, idempotencia, invariantes) cubriendo **Hypothesis (Python), fast-check (JS/TS), proptest**. Sin dependencias propias — markdown puro. Multi-stack por diseño.
**Destino:** `shared/` (la técnica aplica igual en Code y Cowork).

### 2.4 Por stack

| Stack | Skill | Veredicto |
|-------|-------|-----------|
| Flutter | `flutter-tester` (Harishwarrior, MIT) — unit/widget/integration con Mockito y Riverpod | Adoptar a `claude-code/`. **Sin golden tests** — hueco confirmado por segunda vez (`skills/10` §6.4) |
| Python | `honnibal/claude-skills` (MIT) — `hypothesis-tests`, `mutation-testing` (manual: Claude introduce bugs deliberados para auditar la suite), `try-except` | Adoptar selectivamente; repo chico (17 commits) pero autor de spaCy. La mutation manual complementa TDD como auditoría de calidad de suite sin binarios |
| React/Next | Nada dominante fuera de webapp-testing; skills de Vitest/RTL solo en agregadores sin fuente primaria | **No adoptar de terceros** — skill propia corta con tus convenciones RTL/Vitest cuando toque proyecto React |
| C++ | Sin skill de referencia para GoogleTest/Catch2 | Cubrir con ToB (sanitizers/fuzzing) + skill propia de conventions cuando toque |

### 2.5 wshobson: `unit-testing` y `qa-orchestra`

Plugins (formato agents+skills+commands), MIT, activo. `qa-orchestra` = QA multi-agente con validación vía Chrome MCP. **Ojo:** su plugin TDD-workflow **duplica** el de Superpowers — no instalar ese. Los otros dos: evaluar como plugin de marketplace (no van a `claude-skills/`).

---

## 3. Debugging — qué ya tienes y qué no

### 3.1 Lo que `systematic-debugging` ya cubre (verificado en su SKILL.md)

Cuatro fases: investigación de causa raíz (reproducir, cambios recientes, trazar data flow hacia atrás) → análisis de patrones vs código sano → hipótesis única + test mínimo → fix con failing test primero. Regla "3+ fixes fallidos → cuestionar la arquitectura". Sub-referencias: `root-cause-tracing.md`, `defense-in-depth.md`, `condition-based-waiting.md` (polling vs timeouts).

**Implicación:** RCA genérico, 5-whys, "debugging científico", reproduce-first — **todo eso ya está**. Descartados por duplicación: `5-whys-skill` (además 1 commit, abandonado), `bug-fix` de claude-mpm-skills, y cualquier "systematic debugging" alternativo.

### 3.2 Complementos reales (solape casi nulo)

- **ECC build-resolvers** (affaan-m, MIT): agentes por lenguaje (cpp, pytorch, rust...) + `/build-fix` — enfocados en errores de *build*, no de runtime. Complementa limpio.
- **wshobson plugins Debugging (6) / Diagnostics (4) / Incident Response (4)**: agentes delegables (`error-detective`, `distributed-debugging`) — evaluar como plugin.
- **jeremylongshore** (mega-marketplace): `memory-leak-detector`, `log-analysis-tool`, `application-profiler` — usar solo como **cantera** (`skills/10`: volumen ≠ calidad; auditar duro antes de copiar cualquier pieza).

### 3.3 Sinergia con tus skills

El final natural de todo debugging exitoso ya lo tienes: `memory-keeper` guarda síntoma → causa raíz → fix. Cualquier skill de debugging que adoptes o crees debe terminar con "guarda el hallazgo con memory-keeper" — un bug resuelto y no registrado se vuelve a pagar.

---

## 4. Mapa de adopción

```
claude-skills/
├── shared/
│   └── property-based-testing/       ← ToB (portable puro)
├── claude-code/
│   ├── webapp-testing/               ← Anthropic (Playwright)
│   ├── tob-addresssanitizer/         ┐
│   ├── tob-coverage-analysis/        │ ToB testing-handbook (subset C++/Py,
│   ├── tob-fuzzing-harness/          │ prefijo tob- por CC BY-SA)
│   ├── tob-atheris/                  ┘
│   ├── flutter-tester/               ← Harishwarrior
│   └── hypothesis-tests/ mutation-testing/  ← honnibal (Python)
└── (plugins de marketplace, NO a claude-skills/):
    wshobson unit-testing + qa-orchestra + debugging/diagnostics · ECC build-resolvers
```

Presupuesto de contexto: +8-9 skills = ~400-500 tokens de descripciones al inicio (progressive disclosure). Cuidado con solape de triggers entre `webapp-testing` y `qa-orchestra` si instalas ambos — elegir uno como default de E2E.

---

## 5. Huecos verificados → skills propias (backlog)

Confirmado por búsqueda exhaustiva que NO existen como skill mantenida — candidatas a crear con tu `_template` cuando duelan de verdad:

1. **`git-bisect-assist`** — bisect asistido (reproducir → bisect run → causa → memory-keeper). Encaja perfecto con tu sistema; es corta.
2. **`flaky-test-hunter`** — detección y estabilización de tests intermitentes (condition-based-waiting de Superpowers cubre una parte; falta el workflow de detección/cuarentena).
3. **`gdb-sanitizers-runbook`** (C++) — gdb + ASan/UBSan/Valgrind con recetas del stack propio.
4. **`golden-tests-flutter`** — el hueco confirmado dos veces; nadie lo mantiene.
5. **`debugpy-runbook`** (Python) y **`hydration-debug`** (Next.js) — menores; solo si duelen.

---

## 6. Fuentes primarias

[anthropics/skills — webapp-testing](https://github.com/anthropics/skills) · [ToB testing-handbook docs](https://trailofbits-skills.mintlify.app/plugins/testing-handbook-skills) · [trailofbits/skills](https://github.com/trailofbits/skills) · [obra/superpowers — systematic-debugging SKILL.md](https://raw.githubusercontent.com/obra/superpowers/main/skills/systematic-debugging/SKILL.md) · [Harishwarrior/flutter-claude-skills](https://github.com/Harishwarrior/flutter-claude-skills) · [honnibal/claude-skills](https://github.com/honnibal/claude-skills) · [wshobson/agents](https://github.com/wshobson/agents) · [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) · [jeremylongshore](https://github.com/jeremylongshore/claude-code-plugins) · [awesome-skills/5-whys](https://github.com/awesome-skills/5-whys-skill) · [bobmatnyc/claude-mpm-skills](https://github.com/bobmatnyc/claude-mpm-skills)

**No verificable:** contenido interno de los plugins de wshobson (bloqueo de robots); calidad individual de piezas de jeremylongshore; skills de Vitest/RTL en agregadores sin repo primario.

---

*Doc 11 de la serie (sustituye al reporte temporal de bugfixes, ya retirado). Ejecutar adopciones con el protocolo del `skills/10` §2: leer línea por línea, congelar copia en git, sync, probar triggers.*
