---
name: skill-forge
description: >
  Crea, mejora y prueba skills de NUESTRO sistema (setup/skills con carpetas
  shared/claude-code/cowork) aplicando las mejores prácticas oficiales de
  authoring y nuestras convenciones de sync/auditoría. Use when the user says
  "crea una skill", "nueva skill para X", "mejora esta skill", "la skill no
  dispara", "optimiza la descripción", or al detectar un gap que merece skill
  propia. Para plugins completos de Cowork usa cowork-plugin; esto es para
  skills del sistema propio.
---

# Skill Forge

Meta-skill adaptada a nuestro setup: combina el proceso del `skill-creator`
oficial de Anthropic y el hallazgo clave de `writing-skills` (Superpowers) con
nuestras reglas de carpetas, sync y auditoría.

## Las 3 reglas que más fallan (aprendidas del ecosistema)

1. **La descripción dice CUÁNDO, jamás resume el CÓMO** (hallazgo de obra):
   si la descripción resume el workflow, el agente sigue el atajo y nunca lee
   el cuerpo. Formato: qué hace en una frase + "Use when..." + frases gatillo
   literales del usuario + anti-triggers ("NO usar si...").
2. **Progressive disclosure en 3 niveles**: descripción (~60 tokens, siempre en
   contexto) → cuerpo (<500 palabras, al disparar) → `references/`/`scripts/`
   (solo si se necesitan). Lo extenso NUNCA va en el cuerpo.
3. **Triggers estrechos > amplios**: una skill que dispara de más contamina
   sesiones; revisar solape contra las skills existentes ANTES de escribir
   (lee las descripciones de `setup/skills/` y de Superpowers).

## Pasos

1. **Justifica el gap**: ¿qué falla hoy sin la skill? ¿Ya lo cubre Superpowers
   o una skill existente? (los duplicados se descartan — `skills/11` mostró que casi
   todo el "debugging metodológico" externo duplicaba systematic-debugging).
2. **Decide carpeta** con la tabla de skills/README.md: metodología pura →
   `shared/`; toolchain/MCP local → `claude-code/`; sandbox/documentos/web →
   `cowork/`. Nombre kebab-case único.
3. **Escribe desde `_template/SKILL.md`**: frontmatter (regla 1), Requisitos
   con fallback declarado (la misma skill debe servir en Code y Cowork o
   declarar por qué no), Pasos imperativos numerados, paso final de
   verificación, sección "Qué NO hacer" si hay anti-patrones conocidos.
4. **Integra con el sistema**: si produce conocimiento durable → termina en
   `memory-keeper`/`adr-writer`; si toca el vault → respeta el aislamiento por
   proyecto; si es de terceros adaptada → protocolo de auditoría (`skills/10` §2)
   y atribución de licencia (CC BY-SA exige compartir igual).
5. **Prueba de triggers (mínimo viable)**: 3 frases que DEBEN dispararla y 2
   que NO deben (las vecinas más cercanas). Corre las 5 en sesión nueva; si
   falla, ajusta la descripción — no el cuerpo. Para evals serias con A/B y
   varianza: usa el `skill-creator` oficial (Cowork lo trae; en Code se
   instala de anthropics/skills).
6. **Despliega**: carpeta → `setup/skills/<categoría>/` → commit → `sync-skills`
   (sin `-NoCoworkBuild` si es shared/cowork → re-subir dev-skills.zip) →
   commit al repo (regla de flujo git del README).

## Qué NO hacer

- No crear la skill si la respuesta correcta era una línea en CLAUDE.md
  (siempre-necesario → CLAUDE.md; contextual → skill).
- No escribir descripciones "por si acaso" amplias — el costo es disparos falsos
  en todas las sesiones futuras.
