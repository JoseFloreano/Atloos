# Skills de APIs y Despliegue: Investigación y Selección
## Diseño y evolución de APIs + production readiness para dev individual

> **Fecha:** Julio 2026
> **Método:** 2 líneas de investigación paralelas; los repos principales se verificaron por **clonado directo** (GitHub API/WebFetch bloqueados ese día — `git clone --depth 1` sí). Protocolo de auditoría `skills/10` §2 vigente para cualquier adopción.
> **Resultado:** 3 skills propias creadas (§4) — el ecosistema tiene buen material de *diseño* de APIs para destilar, un gap de tooling en *evolución* (nadie empaquetó oasdiff) y un gap total en *despliegue indie*.

---

## 1. Resumen ejecutivo

| Categoría | Mejor material externo | Veredicto | Nuestra pieza |
|-----------|------------------------|-----------|---------------|
| Diseño de APIs | wshobson `api-design-principles` (SKILL.md + references, MIT) · ECC `api-design` · ekkx/google-aip-skills (AIP completos) | Destilar, no instalar — mucho volumen, convenciones no nuestras | ⭐ `api-design` (shared) + checklist operativo |
| Evolución/mantenimiento | ECC trae timeline de deprecation; alirezarezvani `api-design-reviewer` detecta breaking "por prosa" | **Gap de tooling**: nadie empaqueta oasdiff — la detección por heurística es inferior | ⭐ `api-evolution` (claude-code) con oasdiff real |
| Despliegue / production readiness | wshobson tiene pipelines enterprise/K8s; ECC `deployment-patterns`; **cero skills de readiness indie** (verificado también en Superpowers y anthropics/skills: nada) | **Gap total** en el nicho dev-individual | ⭐ `deploy-planner` (shared) + cuestionario de 8 secciones |

## 2. Diseño de APIs — lo encontrado

- **wshobson `plugins/backend-development/skills/api-design-principles/`** (MIT, commit jul-2026): REST completo (recursos, idempotencia, versioning, errores, paginación) + GraphQL schema design + su propio `api-design-checklist.md`. El mejor SKILL.md del nicho. También `api-scaffolding` (agentes backend-architect, fastapi-pro, graphql-architect; skill `fastapi-templates`) y `openapi-spec-generation` (OpenAPI 3.1 design-first, referencia Spectral).
- **ECC** (MIT, muy activo): `api-design` (naming, status codes, rate limiting, tabla de idempotencia, **timeline de deprecation de 6 meses**), `backend-patterns` (el único mantenido que cubre Express y Next.js API routes con nombre), `fastapi-patterns` (Pydantic v2, DI, testing httpx).
- **ekkx/google-aip-skills** (commit jul-2026): los Google AIP íntegros como skills, con snapshot auto-refrescado. ⚠️ **Sin LICENSE declarada** en el repo → solo lectura, no copiar (protocolo §2.6).
- **No existen** como skill: guías Zalando ni Microsoft REST. Jeffallan `api-designer` existe pero con mantenimiento moderado (may-2026).
- **vercel-labs**: nada de APIs (solo frontend) — confirmado.

**Decisión:** nuestra `api-design` destila el consenso de todos (que es notablemente uniforme: plural, problem+json, cursor pagination, contrato-primero) en <500 palabras + checklist con notas por stack propio, y deja los externos como lectura. Instalar los de wshobson/ECC además sería solape de triggers directo.

## 3. Evolución y despliegue — los dos gaps

**Evolución:** `alirezarezvani/api-design-reviewer` promete "breaking-change detection" pero verificado por grep: es prosa/heurística, no invoca tooling. [oasdiff](https://github.com/oasdiff/oasdiff) (Apache-2.0, activo) es el estándar para diff de OpenAPI y **nadie lo empaquetó** (solo un listing no verificable en mcpmarket). Nuestra `api-evolution` lo usa directo con fallback manual — detección determinista > opinión del LLM (principio R2 aplicado a contratos).

**Despliegue:** verificado que ni Superpowers ni anthropics/skills tienen nada; wshobson es enterprise/K8s (deployment-pipeline-design, slo-implementation — otro planeta para un indie); ECC `deployment-patterns` es lo más cercano pero sin el modo entrevista ni readiness gates. Las mejores checklists 2026 son artículos, no skills (Rootcode 2026 — cita OWASP ASVS 5.0 y SRE de Google; Port.io como taxonomía). Hallazgo de las comparativas indie: **la categoría "costos" domina las decisiones de dev individual y las checklists enterprise la omiten** — nuestra guía la trata como sección de primera clase con spend caps como gate.

**Plataformas 2026 (para los defaults del cuestionario):** patrón consolidado Vercel (front Next.js, hobby gratis) + Railway (~$5-15/mes, mejor DX) / Fly.io (pay-as-you-go, multi-región, requiere Docker) / Render ($7/servicio predecible, free tier duerme) para backend; Hetzner VPS (~€5) si se acepta ops manual; Flutter web en cualquier estático. Los precios caducan — la skill valida contra doc oficial del día (regla H10 operativa).

## 4. Las 3 skills creadas

| Skill | Carpeta | Núcleo |
|-------|---------|--------|
| `api-design` | `shared/` | Contrato primero: 7 pasos + checklist por stack; OpenAPI versionado como fuente de verdad (insumo de api-evolution); REST vs GraphQL como ADR, no default |
| `api-evolution` | `claude-code/` | Qué-rompe/qué-no memorizable; `oasdiff breaking` real; orden aditivo→deprecar (Sunset fechado)→versionar; grep de clientes propios antes de confiar; limpieza post-sunset como pendiente del vault |
| `deploy-planner` | `shared/` | Entrevista por bloques con el `deploy-questionnaire.md` (8 secciones con defaults 2026 + costos como primera clase) → `deploy-plan.md` en el vault → gates de go-live que encadenan secrets-scan, web-security-review, dependency-audit, backup restaurado y rollback probado |

Cadena: `api-design` → implementar → `api-evolution` (cada cambio publicado) → `deploy-planner` (go-live) → gates con las skills de seguridad → `adr-writer`.

## 5. Fuentes primarias

[wshobson/agents](https://github.com/wshobson/agents) (clonado) · [ECC](https://github.com/affaan-m/everything-claude-code) (clonado) · [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) (clonado) · [ekkx/google-aip-skills](https://github.com/ekkx/google-aip-skills) · [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills) · [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) · [oasdiff](https://github.com/oasdiff/oasdiff) · [Rootcode: Production Readiness 2026](https://www.rootcode.in/blog/production-readiness-checklist-for-web-applications-the-2026-guide-mr33mw4l) · [Port.io checklist](https://www.port.io/blog/production-readiness-checklist-ensuring-smooth-deployments) · [devtoolpicks: Railway vs Render vs Fly 2026](https://devtoolpicks.com/blog/railway-vs-render-vs-fly-io-solo-developers-2026)

**No verificable:** el listing de oasdiff en mcpmarket; cifras de estrellas de ECC; checklists SEO delgadas descartadas sin auditar a fondo.

---

*Doc 15, subserie skills/. Las 3 skills están en `setup/skills/` — activar con el flujo estándar (copiar → sync sin `-NoCoworkBuild` → re-subir zip → probar triggers).*
