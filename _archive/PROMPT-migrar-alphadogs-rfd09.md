# Prompt — Migrar `alphadogs` al contrato del RFD 09

> **Para:** una sesión de Claude Code aparte, en el repo de AlphaDogs.
> **Por qué separado:** el usuario está trabajando en ese proyecto ahora mismo;
> `tt1-revisor-chatbot` ya se migró (commit `e1ca5ef` del vault) y sirve de
> referencia viva de cómo queda el resultado.
> **Fecha:** 2026-08-01.

---

Vas a migrar la carpeta de `alphadogs` en el vault de Obsidian al contrato de
higiene que ya se aplicó a los otros dos proyectos. Es un cambio de convención en
notas, no de código: **no vas a tocar el repo de AlphaDogs en ningún momento**.

## Contexto en una frase

`_PROJECT.md` se lee entero al arrancar cada sesión. Cuando acumula historial
fechado deja de describir el presente y empieza a cobrar peaje en cada arranque.
El contrato lo fija como estado presente, con tope de líneas, y manda lo que pasó
a `sessions/`.

## Dónde está todo

- **Vault:** `C:\Users\jlflo\OneDrive\DevSetup\ObsidianVault` — es **su propio
  repo git**, distinto del repo de AlphaDogs.
- **Carpeta a migrar:** `10-Projects/alphadogs/`
- **El diseño y su porqué:** `docs/arquitectura-memoria/09-RFD-HIGIENE-VAULT.md`
  en el repo `ClaudeSetup`
  (`C:\Users\jlflo\OneDrive\Documentos\Mis_Documentos\Proyectos\Coding\Python\Otros\ClaudeSetup`).
  Lee §3.0 (las tres capas) y §3.1 (el contrato). No hace falta más.
- **Referencia viva del resultado:** `10-Projects/tt1-revisor-chatbot/` —
  ya migrado. Mira su `_PROJECT.md` y sus dos notas de `sessions/`: eso es
  exactamente lo que tienes que producir aquí.
- **La plantilla canónica:** `templates/project-note.md` del vault.

## Estado de partida (verificado el 2026-08-01 — vuelve a comprobarlo)

`10-Projects/alphadogs/_PROJECT.md`: **100 líneas / 6 072 bytes**. Ya está bajo
el tope de 120, así que **no se trata de recortar**, sino de sacar el historial
de donde no va.

Secciones actuales: `Qué es` · `Estado actual` · `Decisiones clave` ·
`Bugs / issues conocidos` · `Convenciones que difieren del default`.

Dos cosas concretas que hay que arreglar:

1. **`Estado actual` contiene dos bloques fechados** (ambos `2026-08-01`): uno de
   onboarding + hook de Graphify + sprint, y otro de análisis del eval-gate. Eso
   es historial dentro de la sección que debe describir el presente.
2. **Faltan `## Pendientes` y `## Próximo paso`**, y `Bugs / issues conocidos`
   se llama `## Bugs abiertos` en el contrato.

Ya existe `sessions/2026-08-01-analisis-eval-rag.md`, y el segundo bloque fechado
la cita explícitamente: **ese bloque se funde ahí, no se duplica**.

## Reglas duras

1. **Nada se borra: el contenido se mueve.** Un bloque desaparece de su origen
   solo cuando has verificado que llegó a su destino.
2. **Verifica antes de reescribir, nunca después.** Si reescribes primero y la
   verificación falla, el contenido ya no está.
3. **Punto de retorno primero:** commit del vault antes de tocar nada, y anota
   el sha.
4. **Solo `10-Projects/alphadogs/`.** Los otros proyectos del vault y el repo de
   AlphaDogs están fuera de alcance.
5. **Distingue historial de estado vivo.** Los pendientes, las convenciones y los
   wikilinks NO son historial aunque estén dentro de un bloque fechado: se
   quedan, reescritos en presente.

## Pasos

1. **Punto de retorno.** `git -C <vault> add -A && git -C <vault> commit` y
   apunta el sha.
2. **Re-verifica el estado de partida** (líneas, secciones, los dos bloques
   fechados). Si no coincide con lo descrito arriba, **para y dilo**: alguien lo
   editó desde entonces y el mapa cambia.
3. **Mueve el historial:**
   - El bloque del análisis del eval-gate → **funde** en
     `sessions/2026-08-01-analisis-eval-rag.md`, como sección al final:
     `## Lo que quedó registrado en _PROJECT.md (migrado el <fecha>)`.
   - El bloque de onboarding + Graphify + sprint → **nota nueva**
     `sessions/2026-08-01-<slug-descriptivo>.md`, con la **fecha real del
     trabajo** en el nombre y en el frontmatter, y `harvested: false`. Copia el
     frontmatter de las notas de `tt1-revisor-chatbot/sessions/`.
4. **Verifica que nada se perdió, ANTES de reescribir.** Escoge 4-6 frases
   características de los bloques movidos y búscalas en `sessions/`. Si alguna
   no aparece, **para**.
5. **Reescribe `_PROJECT.md`** con los siete apartados en este orden:
   `Qué es · Estado actual · Decisiones clave · Bugs abiertos · Convenciones que
   difieren del default · Pendientes · Próximo paso`.
   - "Estado actual" en **presente**: cómo está el sistema hoy, sin fechas ni
     narración. Añade wikilinks a las notas de sesión para el historial.
   - "Pendientes" con checkboxes: saca los que hoy están enterrados en los
     bloques fechados.
   - "Próximo paso": una o dos frases sobre lo que desbloquea el trabajo.
   - Deja al final el comentario HTML del tope y la prohibición de `## Hecho`
     (cópialo de la plantilla o de `tt1-revisor-chatbot/_PROJECT.md`).
6. **Índice de ADRs.** Si `10-Projects/alphadogs/ADRs/` existe y tiene
   `ADR-*.md`, genera el índice:
   ```
   py "C:\Users\jlflo\OneDrive\Documentos\Mis_Documentos\Proyectos\Coding\Python\Otros\ClaudeSetup\setup\scripts\adr-index.py" "C:\Users\jlflo\OneDrive\DevSetup\ObsidianVault\10-Projects\alphadogs\ADRs"
   ```
   Córrelo **dos veces** y compara el hash: debe salir idéntico. Si la carpeta no
   existe o está vacía, el script sale con **exit 1** y eso es correcto — no hay
   nada que indexar. No inventes ADRs para llenarla.
7. **Commit en el repo del vault** (solo la carpeta de alphadogs), con un mensaje
   que diga qué se movió y por qué.

## Verificación final

```bash
P="C:/Users/jlflo/OneDrive/DevSetup/ObsidianVault/10-Projects/alphadogs"
wc -l < "$P/_PROJECT.md"          # <= 120
grep -c "^## Hecho" "$P/_PROJECT.md"   # 0
grep "^## " "$P/_PROJECT.md"      # los 7 apartados, en orden
```

Y la que no es un comando: **lee el `_PROJECT.md` resultante como si acabaras de
llegar al proyecto.** ¿Sabes en qué estado está y qué toca hacer, sin haber
vivido nada de lo anterior? Si no, el "Estado actual" no está bien escrito.

## Qué NO hacer

- No toques el repo de AlphaDogs ni su código: esto es solo el vault.
- No borres notas de sesión ni las reescribas "para que queden mejor": se
  fusiona contenido, no se reinterpreta.
- No crees `ADRs/` ni `bugs/` vacías por simetría. Se crean cuando hay algo.
- No migres otros proyectos del vault.
- No inventes pendientes ni estado que no estén ya escritos en algún sitio. Si
  algo es ambiguo, **pregunta al usuario** — está trabajando en este proyecto y
  sabe la respuesta.
