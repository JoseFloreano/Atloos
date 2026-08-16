---
name: skill-forge
description: >
  Crea, mejora y prueba skills de NUESTRO sistema (setup/skills con carpetas
  shared/claude-code/cowork) aplicando las mejores prácticas oficiales de
  authoring y nuestras convenciones de sync/auditoría. Use when the user says
  "crea una skill", "nueva skill para X", "mejora esta skill", "la skill no
  dispara", "optimiza la descripción", or al detectar un gap que merece skill
  propia. Para plugins completos de Cowork usa `cowork:cowork-plugin` (skill
  bundled de Cowork, no está en Claude Code); esto es para skills propias.
---

# Skill Forge

Meta-skill adaptada a nuestro setup: combina el proceso del `bundled:skill-creator`
oficial de Anthropic y el hallazgo clave de `superpowers:writing-skills` (Superpowers) con
nuestras reglas de carpetas, sync y auditoría.

## Las 3 reglas que más fallan (aprendidas del ecosistema)

1. **«La instrucción no dice cuándo, solo dice qué»** — y por eso no se cumple
   (frase del humano; Graphify se incumplió 3 jornadas de 3). Nombra un
   **momento reconocible desde fuera**: *un disparador que exige que el agente
   se autodiagnostique el tipo de pregunta no se dispara nunca*. Y la
   descripción **jamás resume el CÓMO**, o el agente sigue el atajo y no lee el
   cuerpo. Los dos casos de campo: `references/disparadores.md`.
2. **Dos unidades y un carácter prohibido; confundirlas bloqueó una subida**: el
   cuerpo se mide en **palabras** (≤450, duro 500); la `description`, en
   **caracteres** (**≤1024**) **y no admite angulares** — `<persona>` rompe la
   subida. Progressive disclosure: descripción (~60 tokens, siempre en
   contexto) → cuerpo → `references/`. Lo extenso NUNCA va en el cuerpo.
3. **Triggers estrechos > amplios**: disparar de más contamina todas las
   sesiones; revisa el solape contra `setup/skills/` y Superpowers ANTES de
   escribir.

## Pasos

1. **Justifica el gap**: ¿qué falla hoy sin la skill? ¿Ya lo cubre Superpowers
   o una skill existente? Los duplicados se descartan: casi todo el "debugging
   metodológico" externo ya estaba en Superpowers (`skills/11`).
2. **Decide carpeta** con la tabla de skills/README.md: metodología pura →
   `shared/`; toolchain/MCP local → `claude-code/`; sandbox/documentos/web →
   `cowork/`. Nombre kebab-case único.
3. **Escribe desde `_template/SKILL.md`**: frontmatter (regla 1), Requisitos
   con fallback declarado (sirve en Code y en Cowork, o di por qué no), Pasos
   imperativos numerados, paso final de verificación, y "Qué NO hacer" si hay
   anti-patrones conocidos.
   **Toda skill que nombres va entre backticks y con namespace**
   (`superpowers:`, `bundled:`, `cowork:`, `mcp:`); sin prefijo = propia y
   debe existir. Lo comprueba `test-skill-catalog.py`.
4. **Integra con el sistema**: si produce conocimiento durable → termina en
   `memory-keeper`/`adr-writer`; si toca el vault → respeta el aislamiento por
   proyecto; si es de terceros → protocolo de auditoría (`skills/10` §2) y
   licencia (CC BY-SA obliga a compartir igual).
5. **Prueba de triggers**: 3 que DEBEN disparar y 2 que NO, en sesión nueva y
   fuera del repo; una es la petición real que falló, **literal**. Si falla,
   ajusta la descripción, no el cuerpo (`references/disparadores.md`).
6. **Despliega**: `setup/skills/<categoría>/` → commit → `sync-skills` (con
   build de Cowork si es shared/cowork → re-subir el zip).

## Qué NO hacer

- No crear la skill si bastaba una línea en CLAUDE.md
  (siempre-necesario → CLAUDE.md; contextual → skill).
- No escribir descripciones "por si acaso" amplias — el costo es disparos falsos
  en todas las sesiones futuras.
