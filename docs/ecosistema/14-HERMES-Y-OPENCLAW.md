# Hermes y OpenClaw: ¿Aditivos o Estorbo?
## Evaluación de los dos asistentes personales open-source contra nuestro setup

> **Fecha:** Julio 2026
> **Pregunta:** ¿suman al setup (Claude Code + Cowork + skills + vault + scheduled tasks) o estorban?
> **Método:** 3 líneas de investigación paralelas sobre fuentes primarias (repos, docs oficiales, reportes de seguridad de Snyk/Censys, posts fechados de usuarios que corren ambos). Lo no verificable está marcado.

---

## 1. Veredicto ejecutivo

**Hoy: estorban más que suman. No adoptar ninguno.** El ~85% de lo que ofrecen ya lo tienes resuelto — y mejor integrado: su memoria duplicaría el vault (la comunidad escribe puentes a mano para sincronizar OpenClaw↔Obsidian — un problema que tú no tienes), sus skills duplican tu sistema SKILL.md, su cron duplica los scheduled tasks de Cowork y `claude -p`, y en código Claude Code les gana sin discusión (test de 30 días documentado: refactor de 400 líneas en 6 min vs 25 min).

**La excepción estrecha y real:** canales de mensajería *entrantes* (que tu asistente responda por WhatsApp/Telegram a las 3 AM) y proactividad always-on multi-proveedor. Eso NO lo cubre tu setup — y es lo único que lo justificaría. Si esa necesidad aparece de verdad, la sección §6 dice cuál elegir y cómo. Mientras tanto: hay dos ideas robables sin adoptar nada (§7), y tu formato de skills ya es portable a ambos (siguen el spec AgentSkills) — la puerta queda abierta gratis.

---

## 2. Qué son (verificado a julio 2026)

**OpenClaw** (ex-Clawdbot → ex-Moltbot, MIT): gateway always-on en Node que conecta un agente a WhatsApp/Telegram/Discord/Signal/iMessage y 10+ canales, con cron, memoria en markdown, skills (spec AgentSkills + gating propio) y su registro ClawHub. Tras irse Steinberger a OpenAI (feb 2026), lo gobierna la OpenClaw Foundation (501c3, sponsors: OpenAI, NVIDIA, Microsoft). Enorme tracción (~384k stars; "4.5M instancias/semana" según la fundación — cifra propia no verificable).

**Hermes Agent** (Nous Research, MIT, feb 2026): el competidor que lo destronó como agente open-source más usado (mayo 2026, app #1 en OpenRouter). Mismo nicho (asistente personal multi-canal, VPS de $5, model-agnostic) con un diferencial real: **loop de auto-mejora** — crea skills automáticamente tras 3+ repeticiones de un workflow, con un "Curator" que las califica y consolida. Trae migración oficial desde OpenClaw (`hermes claw migrate`). Desambiguación: no confundir con los modelos Hermes 3/4 de la misma Nous (esos son LLMs, usables vía OpenRouter, y de hecho una opción *dentro* del agente).

## 3. Matriz de solape contra el setup

| Capacidad | Ellos | Tú ya tienes | Solape |
|-----------|-------|--------------|--------|
| Memoria persistente | MEMORY.md propio (+puentes a Obsidian hechos a mano por la comunidad) | Vault + git + aislamiento por proyecto + anti-drift | **Total** — y el suyo crearía la segunda memoria que el doc 12 enseña a evitar |
| Skills | AgentSkills spec + registros públicos (ClawHub / Skills Hub ~90k) | claude-skills propio, auditado, git-tracked | **Total** en mecanismo; sus registros son el riesgo ToxicSkills en persona |
| Tareas programadas | Cron/heartbeat 24/7 | Scheduled tasks Cowork (nube, sin laptop) + `claude -p` en cron | **Alto** — te falta solo el heartbeat proactivo continuo |
| Código | Mediocre (documentado) | Claude Code | Cero — ganas tú |
| Canales entrantes (WhatsApp/Telegram…) | ✅ Su nicho real | ❌ Nada | **El único gap genuino** |
| Enforcement determinista | Parcial (allowlists) | Hooks propios (R2, anti-drift) | Tuyo es más fino |

## 4. Los costos que no se ven en el README

- **Facturación:** desde el **4-abr-2026 Anthropic bloqueó las suscripciones Pro/Max para agentes de terceros** (aumentos de 10-50× reportados al pasar a API); en mayo reinstauró acceso parcial vía un pool de créditos separado cuyo tamaño no está documentado (**estado actual no verificable**). Realidad reportada de un OpenClaw 24/7: $800-1,500/mes con modelos frontier vía API; $150-300/mes con routing agresivo a modelos baratos. Tu setup actual: la suscripción que ya pagas.
- **Seguridad (OpenClaw, historial 2026):** 21,600-42,600 instancias expuestas a internet (Censys/Bitsight); CVE-2026-25253 y -24763 (8.8), -27001 (prompt injection vía Unicode); campaña **ClawHavoc**: 824+ skills maliciosas en ClawHub distribuyendo Atomic Stealer (llaves de exchanges, wallets, SSH). La respuesta (escaneo VirusTotal automático) es estática — insuficiente contra injection en lenguaje natural según terceros. Hermes es más joven: menos historial ≠ más seguro.
- **Operación:** VPS/Docker, updates de seguridad frecuentes, 2 renames en 3 meses como síntoma de ciclo caótico, y el género de posts "OpenClaw is Dead" (workflows inestables, migración de vuelta a Claude Code). Nadie publica horas/mes de mantenimiento (**no verificable**), pero el patrón cualitativo es consistente.

## 5. Por qué "estorban" en tu caso específico

Tu arquitectura tiene UNA fuente de verdad por tipo de dato (doc 02) y acabas de invertir en anti-drift (doc 12, hooks). Adoptar cualquiera de los dos hoy significa: segunda memoria que driftea, segundo registro de skills sin tu protocolo de auditoría, segundo cron, segunda superficie de ataque siempre encendida, y una factura nueva — a cambio de capacidades que en un ~85% ya tienes. Es el anti-patrón de over-engineering que tu doc 02 describe, en versión infraestructura.

## 6. Si el gap de mensajería se vuelve real (criterios de adopción)

Adoptar SOLO cuando puedas nombrar 3+ automatizaciones concretas que requieran canal entrante o proactividad continua. Entonces:

1. **Preferir Hermes Agent** sobre OpenClaw como primera evaluación: momentum actual, loop de auto-skills, migración limpia, y sin el historial ClawHavoc — pero aplicándole el MISMO escepticismo (es pre-1.0 y su Skills Hub tiene el mismo modelo de riesgo).
2. **Reglas innegociables de despliegue** (de las lecciones OpenClaw): loopback + Tailscale (jamás expuesto a internet), pairing/allowlist de remitentes, cero skills de registros públicos sin el protocolo `skills/10` §2, sandbox Docker, y **el vault sigue siendo la memoria canónica** — el asistente escribe al vault (vía su carpeta git), no a una memoria propia.
3. **Modelo barato por defecto** (router a Gemini/Kimi-class) con escalado puntual — nunca frontier en heartbeats.
4. Diseñarlo con `agentic-system-design` + `context-engineering` + `model-benchmark`, y registrar la decisión con `adr-writer`.

## 7. Qué robarles sin adoptarlos (gratis)

- **El loop de auto-skills de Hermes, en manual:** su mejor idea — "3+ repeticiones del mismo workflow → skill" — no necesita Hermes: es una regla de disciplina para ti con `skill-forge`. Cuando notes que le pides lo mismo a Claude por tercera vez, forja la skill.
- **El heartbeat como patrón, no como daemon:** un scheduled task de Cowork con checklist proactivo (¿algo urgente en X? ¿drift en el vault?) da el 80% de la proactividad con 0% de gateway expuesto.
- **Portabilidad ya ganada:** tu sistema de skills sigue el spec AgentSkills — si algún día adoptas cualquiera de los dos, tus skills entran tal cual. No hay lock-in que resolver hoy.

## 8. Criterios de re-evaluación

Revisar este veredicto si: (a) nombras las 3 automatizaciones de canal entrante (§6); (b) Anthropic clarifica/amplía el pool de créditos para agentes de terceros (cambiaría la economía por completo); (c) Hermes llega a 1.0 con firma de skills o revisión humana en su Hub; (d) el digest mensual del ecosistema detecta que alguno resolvió la memoria-como-plugin (escribir nativamente a un vault externo).

## 9. Fuentes

**OpenClaw:** [repo](https://github.com/openclaw/openclaw) · [docs security](https://docs.openclaw.ai/gateway/security) · [Foundation](https://openclaw.ai/blog/introducing-openclaw-foundation) · [Snyk ToxicSkills](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/) · [VirusTotal partnership](https://openclaw.ai/blog/virustotal-partnership) · [MintMCP CVEs](https://www.mintmcp.com/blog/openclaw-cve-explained) · [TNW: bloqueo de suscripciones](https://thenextweb.com/news/anthropic-openclaw-claude-subscription-ban-cost) · [VentureBeat: reinstauración con pool](https://venturebeat.com/technology/anthropic-reinstates-openclaw-and-third-party-agent-usage-on-claude-subscriptions-with-a-catch)
**Hermes:** [NousResearch/hermes-agent](https://github.com/nousresearch/hermes-agent) · [hermes-agent.ai](https://hermes-agent.ai) · [TechTimes: destrona a OpenClaw](https://www.techtimes.com/articles/316694/20260515/nous-researchs-hermes-agent-dethrones-openclaw-worlds-most-used-open-source-ai-agent.htm) · [MarkTechPost: #1 en OpenRouter](https://www.marktechpost.com/2026/05/10/openclaw-vs-hermes-agent-why-nous-researchs-self-improving-agent-now-leads-openrouters-global-rankings/) · [Composio comparativa](https://composio.dev/content/openclaw-vs-hermes-agent)
**Experiencias de integración:** [Khare: 30 días con ambos](https://mohitkhare.me/blog/openclaw-vs-claude-code-2026/) · [openclaw+obsidian sync](https://eastondev.com/blog/en/posts/ai/20260227-openclaw-obsidian-sync/) · [perelweb: costos reales](https://perelweb.be/blog/openclaw-token-management-smart-model-manager/) · [betterclaw vs Cowork](https://www.betterclaw.io/blog/openclaw-vs-claude-cowork) · ["OpenClaw is Dead"](https://medium.com/data-science-in-your-pocket/openclaw-is-dead-6f6e3cab731f) · [HN: rename](https://news.ycombinator.com/item?id=46820783)

**No verificable:** estado exacto del pool de créditos de Anthropic hoy; "4.5M instancias/semana" y "138 CVEs" (cifras sin fuente independiente); conteos exactos de stars/skills de Hermes; horas de mantenimiento mensual.

---

*Doc 14, inaugura la subserie `ecosistema/` (evaluaciones de herramientas externas contra el setup). Próxima revisión: cuando dispare alguno de los criterios del §8 o el digest mensual lo amerite.*
