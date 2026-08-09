# Dimensionado del servidor 24/7: fugas de memoria, presupuesto de RAM y la compra

> **Fecha:** 2026-08-09 · **Autor:** Cowork (auditor externo, nube).
> **Base:** `c3a21b1`. **Decisión de compra ya tomada por el usuario** — este
> documento no discute *si*, sino **cómo dimensionar** y **cómo mitigar**.
> **Origen:** el usuario quiere multiagentes + `/goal` + `/loop` por Telegram en
> la mini PC, y reservar RAM para desplegar proyectos en pruebas antes de
> AWS/Azure/GCP.
> **Contexto:** `telegram/01-MINIPC-SERVIDOR-24-7.md` (⚠ su línea de RAM está
> desfasada, §5) · `ADR-20260801-os-servidor-24-7` (sigue `proposed`) ·
> `ecosistema/18` (el bucle) · `auditoria/19` (los diez conflictos).

---

## 0. Las cuatro cosas que cambian la decisión

1. **Las fugas no están resueltas, pero ahora hay herramientas oficiales para
   convivir con ellas.** Los dos issues que citaba `telegram/01` están cerrados;
   la *categoría* sigue viva, con dos issues abiertos con números feos. Lo nuevo
   y bueno: **Anthropic añadió variables de entorno diseñadas exactamente para
   agentes de larga duración desatendidos**, y una de ellas cierra el diseño que
   propuse en la auditoría 19.

2. **`--max-old-space-size` no arregla esto.** La fuga que sigue abierta es
   **off-heap** (memoria nativa, no el heap de V8). El flag solo cambia dónde
   revienta. Lo que funciona es el cgroup.

3. **El presupuesto de RAM lo domina algo que `telegram/01` no contempló**: si
   el staging del proyecto de RAG carga el **modelo de reranking en memoria**,
   esa app pesa más que Postgres. Es el mayor consumidor individual del box, no
   la base de datos.

4. **La RAM está en máximos históricos y no va a bajar.** DRAM +172% en 2025,
   DDR5 hasta +300-400%, y la escasez se proyecta **hasta 2027-2028**. Eso
   convierte "compro 32 y amplío después" en una **mala estrategia financiera**,
   no solo en una molestia: con 2 slots no se añade, se **tira** lo viejo.

---

# Parte 1 — Las fugas de memoria

## 1.1 Estado real, a 2026-08-09

Los dos issues que cita `telegram/01`:

| Issue | Qué reportaba | Estado |
|---|---|---|
| #17650 | ~3 GB en 18 s de arranque (v2.0.76) | **Cerrado** |
| #34161 | 10-13 GB tras 3 mensajes → OOM | **Cerrado como duplicado** |

Pero la categoría sigue viva, con dos abiertos y con cifras:

| Issue | Qué reporta | Estado |
|---|---|---|
| **#67433** | **RSS crece 400-500 MB/min en reposo**, v2.1.170, Ubuntu 24.04. Reintentado tras 3 auto-updates | **ABIERTO** (11-jun-2026) |
| **#56693** | Leak de V8 hasta 113 GB, crash del equipo | **ABIERTO** (6-may-2026) |

Y el dato que mejor describe la situación: **el changelog oficial muestra
parches de fugas distintas cada pocas semanas hasta agosto de 2026.** Versión
actual **2.1.226 (8-ago-2026)**.

> No es un bug que se cerró. Es una familia de fugas que se va cerrando de una
> en una. Diseña el servidor asumiendo que **habrá** una fuga, no que no la hay.

## 1.2 No es una causa, son ocho — y eso importa

El changelog identifica fuentes distintas, cada una con su parche:

| Fuente de la fuga | Arreglada en |
|---|---|
| **Memoria off-heap / nativa** (99% *Anonymous/private-dirty*) | **sigue abierta** (#67433) |
| MCP stdio: stderr acumulado sin tope (hasta 64 MB por servidor) | 2.1.208 |
| Resultados de tools MCP truncados pero **retenidos enteros** toda la sesión | 2.1.217 |
| **Sesiones headless/SDK: crecimiento sin acotar por payloads grandes de tools** | 2.1.208 |
| Caché de lectura que pineaba hasta 1000 ficheros completos | 2.1.208 (tope 16 MB) |
| Transcript: no podaba backups de ediciones superadas (**hasta 79× de reducción**) | 2.1.208 |
| Documentos LSP nunca cerrados | 2.1.208 (LRU de 50) |
| El indicador de uso de contexto re-analizaba el transcript entero cada turno | 2.1.203 |
| El auto-updater buffereaba el binario en memoria (~400 MB de pico) | 2.1.205 |

Dos lecturas para nosotros:

- **El modo headless tenía un vector propio**, nombrado como categoría separada
  en el changelog. Y headless es exactamente lo que corre en el servidor.
- **La que sigue abierta es off-heap**, y por eso `NODE_OPTIONS=--max-old-space-size`
  no la cubre: solo acota objetos JS. Es un cinturón, no la solución.

## 1.3 ⚠ Y algo que cambió hace dos días

`CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` **fue eliminada el 2026-08-07** (v2.1.224).
Antes topaba en 200 el total acumulado de subagentes por sesión; ahora es no-op:
*"long-running sessions no longer refuse new agents (concurrency and depth limits
still apply)"*.

Para un box que va a correr multiagentes en bucle, esto quita una barrera que
antes acotaba el crecimiento del transcript. **Los topes que quedan son los de
concurrencia y profundidad, no el acumulado.** El único freno al acumulado es
ahora la compactación y el reinicio.

Y recuerda la corrección que ya está en `telegram/01`: **los subagentes NO son
procesos nuevos**, corren dentro del mismo proceso. Multiagente no multiplica
procesos: **concentra memoria en uno solo**. Para la fuga, eso es peor, no mejor.

## 1.4 El runbook de mitigación

Ordenado por eficacia. Lo marcado ⭐ es lo que yo pondría desde el día uno.

### a) ⭐ Variables oficiales pensadas para agentes desatendidos

Estas tres son el hallazgo más valioso de la investigación, porque **cierran el
diseño que propuse en la auditoría 19** (*«MemoryMax mata, systemd reanuda, y la
condición de la meta es el contrato de recuperación»*): resulta que Anthropic ya
construyó la pieza que faltaba.

| Variable | Qué hace |
|---|---|
| **`CLAUDE_CODE_RESUME_INTERRUPTED_TURN=1`** | Al reiniciar, **retoma automáticamente** si la sesión anterior murió a media vuelta. La doc dice literalmente que es para *"spawn scripts for long-running agents"* |
| `CLAUDE_CODE_RESUME_INTERRUPTED_TURN_MAX_AGE_MS` | Acota cuán vieja puede ser la sesión para intentar el auto-resume (evita retomar un kill de hace días) |
| `CLAUDE_CODE_RESUME_PROMPT` | Personaliza el mensaje de continuación (default: *"Continue from where you left off."*) |

Con esto, el ciclo completo queda: **el cgroup mata → systemd reinicia → Claude
retoma el turno interrumpido solo → y la condición de `/goal` sigue siendo el
contrato de qué significa "terminado".** No hace falta escribir el supervisor:
ya existe.

### b) ⭐ Acotar el contexto, que es acotar la memoria

| Variable | Para qué |
|---|---|
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` (100k–1M tokens) | Fija en tokens cuándo dispara el auto-compact. La doc dice *"for scripts and cloud environments"* |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (1–100) | Lo mismo en porcentaje |
| `MAX_MCP_OUTPUT_TOKENS` (default 25.000) | Tope de las respuestas de tools MCP |
| `BASH_MAX_OUTPUT_LENGTH` (default 30.000) | Salida de Bash que entra al contexto |
| `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` | Tope de lecturas de fichero |
| `MAX_THINKING_TOKENS` | Presupuesto de thinking |

🚫 **`DISABLE_AUTO_COMPACT=1` NO se pone en un 24/7.** Es justo el mecanismo que
acota la memoria de contexto.

### c) ⭐ Acotar los subagentes

| Variable | Default |
|---|---|
| `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | 20 (v2.1.217+) — **bájalo en el servidor** |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | 3 (v2.1.219+) |
| `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | 10 |
| `CLAUDE_SUBAGENT_BG_SHELL_MAX_MS` | 60 min de vida a un shell en background de subagente |
| `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` | Elimina esa superficie entera si no la usas |

⚠ **`CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP`: NO la actives.** Por defecto,
Claude Code **ya mata solo** los shells en background cuando el SO reporta
presión de memoria tras 30 min ociosos. Activarla **desactiva** esa defensa.

### d) ⭐ Headless bien lanzado

- **`--bare`** — se salta el auto-discovery de hooks, skills, plugins, MCP y
  `CLAUDE.md`. La doc lo llama *"the recommended mode for scripted and SDK calls"*.
  Menos superficie cargada, menos memoria de base.
  ⚠ **Pero ojo con nuestro caso**: `--bare` **se salta los hooks**, y nuestros
  hooks son la garantía (`merge-gate-guard`, anti-drift). Para el trabajo del
  bot que toca código, `--bare` es una mala idea; para consultas de solo lectura,
  es correcto. **Decidir por tipo de tarea, no por defecto.**
- `CLAUDE_CODE_RETRY_WATCHDOG=1` — reintenta 429/529 indefinidamente; pensada
  para sesiones desatendidas.
- `CLAUDE_CODE_MAX_TURNS` — cinturón anti-bucle.
- **`SIGTERM` es la parada limpia**: aborta el turno, mata el árbol de procesos,
  **corre los hooks `SessionEnd`** y sale con 143. `SIGKILL` del cgroup **no
  corre nada**. Reserva el kill para la emergencia.

### e) El cgroup, que es lo que de verdad acota

```ini
# /etc/systemd/system/claude-worker@.service  (esbozo, no probado)
[Service]
Environment=CLAUDE_CODE_RESUME_INTERRUPTED_TURN=1
Environment=CLAUDE_CODE_RETRY_WATCHDOG=1
Environment=CLAUDE_CODE_AUTO_COMPACT_WINDOW=150000
Environment=CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=6
MemoryHigh=3G          # throttle: el kernel reclama y frena
MemoryMax=4G           # kill duro, acotado a ESTE cgroup
MemorySwapMax=0
OOMPolicy=kill
Restart=on-failure
RestartSec=15
StartLimitIntervalSec=3600
StartLimitBurst=20     # ⚠ generoso a propósito, ver abajo
```

Tres cosas que hay que saber y que cuestan caro descubrir:

1. **`MemoryHigh` sola congela sin matar.** Un experimento publicado la probó en
   ambas capas y el proceso quedó estrangulado, vivo y sin avanzar. Para una
   herramienta autónoma **matar rápido es mejor que estrangular**: `High` para
   frenar, `Max` para matar.
2. **`MemoryMax` mata dentro de su cgroup**, no globalmente. Ese es el punto: el
   radio de daño queda contenido y no se lleva por delante tu SSH ni el staging.
3. ⚠ **`StartLimitBurst` bajo es una trampa silenciosa.** Si la fuga es real vas
   a tocar el techo varias veces al día; agotado el burst, **systemd deja de
   reiniciar sin decir nada**. Es exactamente el fallo que el RFD 17 §4.5 llama
   *"la ausencia de algo bueno: no hay error que capturar"*. Ponlo holgado **y
   que el latido lo vigile** (C2 de la auditoría 19).

`WatchdogSec` **no aplica**: Claude Code no hace `sd_notify`. Lo que sustituye
al watchdog es el latido cruzado.

---

# Parte 2 — El presupuesto de RAM

## 2.1 Lo que pesa cada cosa

Cifras medidas donde las hay; marcadas como estimación donde no.

| Pieza | Reposo | Bajo carga | |
|---|---|---|---|
| Debian headless + systemd + sshd + journald | 1–1,5 GB | | est. |
| Docker/containerd | 50-100 MB limpio | **100-400 MB tras semanas** | [AR] |
| **PostgreSQL** — conexión | **1,3 MB con `huge_pages`, 7,6 MB sin** | | **[R] medido** |
| PostgreSQL — `shared_buffers` en box compartido | **2-4 GB (6-12%)**, no el 25% de libro | | |
| **pgvector HNSW** | ~20-25 KB/vector en despliegues reales (3-4× el vector crudo) | | [R-ish] |
| Redis vacío | **~3 MB** | + dataset × 1,5-2 | [R] |
| Caddy | ~40 MB | 96-160 MB | [AR] |
| Worker FastAPI normal | 40-80 MB | ~600 MB sin optimizar | |
| **Worker FastAPI con modelo de reranking cargado** | **cientos de MB a 1-2 GB+ por worker** | | **est. — el mayor consumidor** |
| Daemon de Telegram | 200-300 MB | | est. |
| **Sesión de Claude Code** | ~1 GB "sana" | **techo 1,5-2 GB por las fugas** | |

**El titular**: en el proyecto de RAG, **el modelo de reranking en memoria pesa
más que Postgres**. Cualquier presupuesto que ponga la base de datos como el
inquilino grande está mal planteado.

## 2.2 Los dos escenarios, con 32 GB

### Escenario A — staging **bajo demanda** (se levanta para probar, se baja)

| Bloque | `MemoryMax` |
|---|---|
| SO + Docker + journald | 2,0 GB |
| Daemon de Telegram | 0,3 GB |
| **6 sesiones de Claude Code** (multiagente + bucle) a 2 GB de techo | **12,0 GB** |
| Staging completo, cuando está arriba | 10-12 GB |
| **Suma con staging arriba** | **~26 GB** |
| Colchón zram | 4-6 GB comprimidos |

**Cabe, con margen ajustado.** Es un box que funciona si aceptas no tener el
staging permanentemente encendido.

### Escenario B — staging **permanente** (Postgres+pgvector+Redis+Caddy+2 apps con modelo)

| Bloque | `MemoryMax` |
|---|---|
| SO + Docker + journald | 2,0 GB |
| Daemon de Telegram | 0,3 GB |
| Postgres + pgvector (índice residente) | 5-6 GB |
| Redis + Caddy | 1,2 GB |
| 2 apps Python, una con reranker | **6-10 GB** |
| **Subtotal staging permanente** | **~15-18 GB** |
| **Queda para agentes** | **~12-14 GB** → **6-7 sesiones** de 2 GB |

**También cabe, pero sin colchón.** Y "sin colchón" en un box con una fuga
abierta que crece 400-500 MB/min significa que el día que dos sesiones se
desmadren a la vez, el OOM killer elige por ti.

> **Conclusión honesta: 32 GB alcanzan para el escenario A cómodamente y para el
> B con la soga al cuello.** Lo que decide no es el número: es si el staging vive
> encendido.

## 2.3 Con 64 GB

El escenario B pasa de "con la soga al cuello" a "cómodo": ~18 GB de staging
permanente, 12-16 GB de agentes, y **~30 GB de colchón real** para las fugas,
los picos de build de índices HNSW (`maintenance_work_mem` alto durante
`CREATE INDEX`) y un segundo proyecto en staging a la vez.

No es lujo: es que **el patrón de uso que describiste —multiagente, bucle
continuo, y staging— es el que más rápido consume el colchón.**

## 2.4 Cómo se acota de verdad (y el papel del zram)

- **`systemd` slices**: agrupa el staging en `staging.slice` y los agentes en
  `agents.slice`, con `MemoryHigh`/`MemoryMax` por slice. Se propaga a las
  unidades hijas.
- **Docker**: `--memory` es techo duro (mata con exit 137); `--memory-swap`
  igual a `--memory` = sin swap. `--memory-reservation` es blando y **no
  garantizado**: no lo uses como límite.
- **zram**: en 32 GB físicos no es "más RAM". Su papel real aquí es otro: como
  vas a **sobre-comprometer** los `MemoryMax` (la suma pasa de 32 porque no todo
  pica a la vez), zram da unos GB comprimidos (ratio ~2:1-3:1) que convierten un
  *"muere ahora"* en *"se pone lento un rato"*. **Colchón, no memoria.** No lo
  cuentes en el presupuesto.

## 2.5 Lo que NO deberías montar

- **k3s.** Cuesta **0,8-1,5 GB solo de control plane** antes de un pod tuyo, y
  solo da paridad real si tu producción **es** Kubernetes gestionado. Con Caddy
  como reverse proxy, tu prod no es k8s: `docker compose` cubre lo que de verdad
  varía entre laptop y nube (env vars, red, volúmenes, healthchecks).
- **LocalStack / Azurite / emuladores GCP encendidos 24/7.** LocalStack no
  publica mínimo de RAM, tiene issues de fuga propios, y la práctica sugiere
  4-8 GB con varios servicios. Para 1 dev con 2-3 proyectos: levántalos **solo
  durante los tests de integración**, y usa el free tier real del proveedor para
  el *"¿se comporta como en la nube?"* — que es justo donde los emuladores
  divergen.
- **Podman "para ahorrar RAM".** La diferencia con Docker son decenas de MB,
  ruido en 32 GB. Podman rootless vale la pena por **superficie de ataque** (sin
  daemon root) en un box con Caddy expuesto, no por memoria. Decídelo por
  seguridad, no por presupuesto.

---

# Parte 3 — La compra

## 3.1 ⚠ El presupuesto de `telegram/01` está desfasado en la línea de RAM

El doc dice (01-ago-2026):

> *SER5 $7,630 + 2×16 GB DDR4 (~$1,600) ⇒ **~$9,200 MXN**.*

Precio verificado hoy (09-ago-2026, Cyberpuerta): **2×16 GB DDR4-3200 SODIMM
≈ $3,858 MXN**. La línea de RAM está a **~2,4× de la estimación**, y el total
real sería **~$11,500**, no $9,200.

Ocho días. Es la ley 2 otra vez, y con dinero de por medio: **re-cotiza antes de
comprar, no confíes en la tabla del doc.**

## 3.2 El contexto que lo explica: la RAM está en máximos

- DRAM **+172% durante 2025**; kits DDR5 hasta **+300-400%** frente a finales de
  2025.
- Micron (junio 2026): la escasez **dura hasta 2027**, mejora gradual hacia 2028.
- Señal concreta: el Crucial 16 GB DDR4-3200 SODIMM lleva **semanas agotado** en
  Cyberpuerta, con nota de que probablemente no vuelva a haber existencia.

**Consecuencia directa para tu pregunta**: esperar **no va a abaratar** la
ampliación futura. Es más probable que el kit de 64 GB cueste igual o más dentro
de 12-18 meses.

## 3.3 Ampliabilidad, modelo por modelo

| Modelo | RAM | Slots | Máximo real | |
|---|---|---|---|---|
| **Beelink SER5** (5800H) | DDR4-3200 **SODIMM** | 2 | **64 GB** | [R] spec oficial |
| **GMKtec NucBox M3** (i5-12450H) | DDR4-3200 **SODIMM** | 2 | **64 GB** | [R] + OWC vende kits de 64 GB específicos para este modelo |
| **Beelink SER8** (8845HS) | DDR5-5600 **SODIMM** (no soldada) | 2 | **64 GB práctico** (la web dice "256 GB": es marketing del chipset) | [R] |
| **Minisforum UM773** (7735HS) | DDR5 SODIMM | 2 | **64 GB oficial** (limitado a 4800) | [R] |
| Minisforum AI X1 Pro | DDR5 SODIMM | 2 | **128 GB oficial** | [R] — pero es gama muy superior |

⚠ **Verifica siempre por modelo, no por chip.** Los equipos con Ryzen AI Max+
395 (GMKtec EVO-X2 y similares) anuncian "hasta 128 GB" pero llevan **LPDDR5X
soldada: cero ampliable**.

## 3.4 El número que responde tu pregunta

Con **2 slots no se añade: se reemplaza**. Pasar de 32 a 64 después significa
tirar (o revender) el kit inicial.

| Ruta | 32 ahora | 64 después | **Total** | vs 64 directo | **Desperdicio** |
|---|---:|---:|---:|---:|---:|
| **DDR4** (SER5 / NucBox M3) | $3,858 | $8,378 | **$12,236** | $8,378 | **$3,858** |
| **DDR5** (SER8 / UM773) | $7,398 | $14,498 | **$21,896** | $14,498 | **$7,398** |

Con reventa del kit usado (40-60% en un mercado escaso), el desperdicio real
baja a ~$1,500-2,300 (DDR4) o ~$3,000-4,400 (DDR5). Sigue sin ser gratis.

Y el dato que reordena todo:

> **64 GB de DDR4 ($8,378) cuestan menos que 32 GB de DDR5 ($7,398)… casi lo
> mismo.** La plataforma DDR4 te da el doble de memoria por el mismo dinero.

Para un servidor headless sin necesidad de ancho de banda de memoria, **DDR4 es
la elección de coste total**, y además es la que hace barata la ampliación.

## 3.5 Recomendación

**Plataforma DDR4 (SER5 o NucBox M3), y 64 GB de una vez si el presupuesto
aguanta.**

El razonamiento, en tres pasos:

1. Tu patrón de uso —multiagente + bucle continuo + staging permanente— es
   precisamente el que consume el colchón. Con 32 GB, el escenario B (§2.2) cabe
   pero sin margen para la fuga que sigue abierta.
2. "Compro 32 y amplío" cuesta **$3,858 MXN de más** en DDR4 y no se abarata
   esperando, porque la escasez va hasta 2027-2028.
3. 64 GB en DDR4 cuesta lo mismo que 32 GB en DDR5. Si vas a gastar ese dinero,
   gástalo en capacidad, no en ancho de banda que un servidor headless no usa.

Números aproximados, **a re-cotizar el día de la compra**:

| | SER5 + 32 GB | SER5 + 64 GB | GMKtec M3 (32 incluidos) |
|---|---:|---:|---:|
| Equipo | $7,630 | $7,630 | $14,100 |
| RAM | $3,858 | $8,378 | incluida |
| **Total** | **~$11,500** | **~$16,000** | **~$14,100** |
| UPS 750-1000 VA | +$1,500-2,500 | +$1,500-2,500 | +$1,500-2,500 |

⚠ El SER5 a $7,630 era **una sola pieza** en Lapson el 01-08. Verifica
disponibilidad antes de planear sobre ese precio. El NucBox M3 es la alternativa
turnkey y **también llega a 64 GB** — con la ventaja de que su kit de ampliación
está verificado por un tercero (OWC).

**Y no recortes el UPS.** En un 24/7 en México vale más que cualquier upgrade de
CPU: protege el SSD, sobrevive cortes y evita que el bot muera a media tarea. Es
además el N0 físico de la guardia.

---

## 4. Decisiones abiertas

### D8 · ¿32 o 64 GB?

| | Opción | Coste | Consecuencia |
|---|---|---|---|
| **(a)** ⭐ | **64 GB DDR4 de entrada** | ~$16,000 | Escenario B con colchón real; no vuelves a tocar el tema |
| **(b)** | 32 GB ahora, 64 cuando duela | ~$11,500 + $8,378 después | Funciona hoy; **$3,858 tirados** y sin garantía de stock en 2027 |
| **(c)** | 32 GB y staging solo bajo demanda | ~$11,500 | Cabe cómodo, pero renuncias al staging permanente |

**Mi voto: (a)**, y si el presupuesto no da hoy, **(c) antes que (b)** — porque
(c) es una decisión de diseño consciente y (b) es pagar dos veces por lo mismo.

### D9 · ¿El staging vive encendido o se levanta a demanda?

Es la variable que decide si 32 GB alcanzan. Y tiene una respuesta intermedia
buena: **Postgres+Redis permanentes** (son baratos: ~6 GB) y **las apps con
modelo, a demanda** (son las caras). Eso deja el escenario A con la comodidad
del B.

### D10 · ¿`--bare` en el servidor?

Ahorra memoria de base **saltándose los hooks** — y los hooks son nuestra
garantía. Propongo: `--bare` para tareas de solo lectura del bot, **nunca** para
tareas que tocan código. Requiere que el daemon distinga las dos, que hoy no
hace.

---

## 5. Lo que hay que probar antes de confiar en nada de esto

Ninguna cifra de este documento es una medición mía sobre tu hardware. El plan
mínimo, en la ventana de devolución de 30 días:

1. **Memtest 24 h + stress test** (ya está en el ADR).
2. **Medir una sesión real** de Claude Code del bot durante una jornada:
   `systemd-cgtop` sobre su slice, muestreado cada minuto. Es el número que
   nadie ha publicado y que decide todo el presupuesto.
3. **Provocar el OOM a propósito**: bajar `MemoryMax` a 1 GB, lanzar una tarea
   real y comprobar que (a) muere, (b) systemd reinicia, (c)
   `CLAUDE_CODE_RESUME_INTERRUPTED_TURN` retoma, y (d) el trabajo no se pierde.
   **Es el canario del diseño de C3 de la auditoría 19.** Sin esa prueba, la
   recuperación es una convención escrita — y ya sabemos cómo acaban.
4. **Medir el índice HNSW real** con tu corpus, en vez de la fórmula: las dos
   fórmulas publicadas no coinciden entre sí (0,7 GB vs 2,5 GB para el mismo
   caso).

## 6. Sesgo declarado

Estoy recomendando gastar **$4,500 MXN más** de lo que el doc original
presupuestaba, y lo hago desde una posición cómoda: no pago yo. El contraargumento
honesto es que el escenario A cabe holgado en 32 GB, que la fuga puede cerrarse
en las próximas semanas —Anthropic lleva parcheándolas sin parar— y que el
staging permanente es una elección, no un requisito. Si D9 sale "a demanda",
**(c) es tan defendible como (a)** y ahorra $4,500.
