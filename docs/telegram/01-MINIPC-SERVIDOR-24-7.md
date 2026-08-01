# Mini PC para el servidor Telegram/Claude Code 24/7
## Investigación de mercado México y recomendación

> **Fecha:** 2026-08-01 (precios verificados ese día donde se indica ✔)
> **Presupuesto:** ≤$20,000 MXN. **Veredicto corto: necesitas ~la mitad.**
> **Caso de uso:** daemon Telegram + Claude Code headless + subagentes en paralelo + tests/builds + Docker (FalkorDB/Postgres). Sin GPU (la Legion cubre eso; aquí no hay inferencia local).

---

## 1. Lo que realmente necesitas (esto redefine la compra)

**Los subagentes de Claude Code NO son procesos nuevos**: corren dentro del mismo proceso como conversaciones API concurrentes (docs oficiales: "Subagents work within a single session", límite default 20 concurrentes). Mandar 10 subagentes cuesta **red y tokens, no CPU local**. La CPU local solo trabaja cuando esos subagentes corren tests/builds vía Bash — ahí sí, varios pytest/vitest simultáneos quieren hilos.

**El recurso que dimensiona todo es la RAM**, y su presupuesto real medido/reportado:

| Componente | RAM |
|---|---|
| Linux headless + Docker + FalkorDB/Redis + Postgres idle + bot | ~1.5-2 GB |
| 6-10 sesiones `claude` (~300 MB-1.5 GB c/u; presupuestar 1 GB) | 6-10 GB |
| 2-3 suites de tests/builds concurrentes | 3-6 GB |
| **Pico realista** | **~11-18 GB** |

⚠ Los **memory leaks de Claude Code son la falla más documentada** de este patrón (issues #17650, #34161: sesiones que se van a 10+ GB). Para un daemon 24/7 la estabilidad la dan sesiones cortas con `--resume`, `systemd` con `MemoryMax=` y margen de RAM — más que el fierro.

**Spec objetivo**: 8 hilos+ (rendimientos decrecientes ≈8 hilos físicos para proyectos chicos-medianos), **32 GB RAM** (16 funciona pero un leak te tira sesiones), 512 GB NVMe (cualquiera; Gen4/5 no paga), **Ethernet** (el cuello es la API de Anthropic; el cable elimina los micro-cortes de WiFi que abortan tool calls), Linux headless (Windows 11 te come 4-6 GB de saque).

**Qué NO pagar**: GPU, DDR5 vs DDR4, >16 hilos, NVMe premium. Orden del dinero: RAM 32 GB > 8 cores > NVMe cualquiera > eficiencia.

**Luz (CFE)**: N150 ≈ $95-250 MXN/año; Ryzen HS ≈ $190-500/año. Diferencia irrelevante — no elijas por watts. (Un desktop viejo de torre sí cuesta: $600-1,700/año y riesgo de empujarte a DAC.)

## 2. Candidatos con precio verificado en México

| Opción | Specs | Precio | Nota |
|---|---|---|---|
| **Beelink SER5 (Ryzen 7 5800H)** | 8c/**16t**, 16 GB DDR4 (2×SODIMM, hasta 64), 1 TB | **$7,630 ✔** Lapson México (¡1 pieza!); alt. Walmart $10,679 | + 32 GB por ~$1,500-1,900 más ⇒ **~$9,200-9,500 total** |
| **GMKtec NucBox M3 (i5-12450H)** | 8c/12t, **32 GB ya incluidos**, 1 TB, dual M.2, 2.5GbE | **$14,100 ✔** Lapson, en stock | Turnkey: nada que ampliar. QC GMKtec irregular: reinstalar SO limpio, estresar en ventana de devolución |
| **Minisforum UM773 (7735HS)** | 8c/16t, 32 GB DDR5, 1 TB, 2.5GbE | **$19,400 ✔** Lapson | La marca más fiable, pero caro para lo que este caso pide |
| **Beelink SER8 (8845HS)** | 8c/16t, 32 GB, 1 TB, dual NVMe, idle 7-10 W medido | rango $16-22k (Amazon MX/ML, **no verificado**) | Si aparece ≤$18k es el mejor fierro de la lista |
| **Tiny corporativo usado (ThinkCentre M720q/M920q i7-8700T)** | 6c/**12t**, 32 GB baratos, build corporativo | ~$5,000-8,000 (ML/refurb; Canemtek desde $3,400 configs base — rango estimado) | El clásico homelab sigue vigente; riesgo = vendedor, no hardware |
| **Mac mini M4** | 10 cores, 16 GB **no ampliables**, 256 GB | **$9,899 ✔** Costco (jul-2026), $10.1-12k Liverpool/Amazon | Mejor máquina objetivamente (4 W idle, re-encendido tras corte verificado) — pero 16 GB fijos MENOS la VM de Docker en macOS la descartan para TU caso de paralelismo |
| **Raspberry Pi 5 16 GB + NVMe** | 4c/4t ARM | kit ~$9,500-11,000 | **Falsa economía 2026** (precios Pi +70-90%): cuesta como el Mac mini y rinde como N100 |
| **N150 (ASUS NUC 14 barebone $3,749 ✔ + RAM/SSD)** | 4c/4t | ~$7,500-8,000 armado | Solo si el silencio de watts te obsesiona; 4 hilos serializan tus tests |

## 3. Recomendación

**Compra principal: Beelink SER5 5800H 16GB/1TB ($7,630, Lapson) + 2×16 GB DDR4 (~$1,600) ⇒ ~$9,200 MXN.** 16 hilos Zen 3 y 32 GB: exactamente paralelismo y eficiencia sin pagar potencia pico. Si esa pieza única vuela: **GMKtec M3 32GB a $14,100** (turnkey) o cotizar el **SER8 en Amazon MX** antes de considerar el UM773.

**Con lo que sobra (~$10k) sí hay dos compras que valen más que mejor CPU:**
- **UPS/no-break de ~750-1000 VA (~$1,500-2,500)** — para un servidor 24/7 en México es más importante que cualquier upgrade: sobrevive cortes, protege el SSD, y el bot no se cae a mitad de una tarea.
- (Opcional) NVMe extra para backups locales del vault/repos.

**Setup sugerido al llegar**: Debian/Ubuntu Server headless + Docker + `systemd` para el daemon (con `MemoryMax=` y `Restart=always`), Ethernet, reinstalación limpia del SO (obligatoria en marcas chinas — precedente ACEMAGIC 2024 con malware de fábrica), Memtest + stress-test dentro de los 30 días de devolución, BIOS: "Restore on AC Power Loss" = ON (el equivalente del autorestart — clave para cortes de luz).

**Notas Linux por si eliges otro modelo**: NIC Intel i226 = cero drama; Realtek RTL8125 funciona pero con historial de caídas (fix conocido: `r8125-dkms`); N100/S12 Pro a veces requieren `intel_idle.max_cstate=1`.

## 4. Fuentes principales

Docs oficiales Claude Code (setup: "4 GB+ RAM, x64 or ARM64"; sub-agents; SDK) · GitHub issues #17650/#34161/#22188 (leaks) · pytest-xdist y Jest docs (workers = cores físicos) · ServeTheHome (mediciones de consumo SER7/SER8/EQ12 Pro/M720q) · Lapson México, Cyberpuerta, Walmart MX (precios ✔ 2026-08-01) · Promodescuentos/Costco (Mac mini M4) · Apple support (autorestart tras corte) · Tom's Hardware (ACEMAGIC malware) · tarifas CFE 2026 (calcele.com). Los informes completos de los 3 agentes (con todas las URLs) quedaron en la sesión.

---

*Complementa a `00-DISENO-TELEGRAM-BRIDGE.md`: esta máquina es donde correría el daemon de la vía 2. Decisión de compra → ADR cuando se ejecute.*
