---
title: La RAM del SER8 — llegó de 24 GB. Qué hacer, con precios de agosto 2026
tags: [servidor, ram, ser8, compra, telegram]
created: 2026-08-13
updated: 2026-08-13
status: decision-pendiente
type: analisis
project: atloos
---

# La RAM del SER8 — no la devuelvas, y compra el de 32 GB

## Veredicto en cinco líneas

1. **No devuelvas la máquina.** Pide **reembolso parcial** y quédatela.
2. **Compra un módulo de 32 GB** → te quedas en **56 GB**.
3. **La opción 24+24 = 48 GB está muerta**: no hay stock de 24 GB en México y
   fuera cuesta casi lo mismo que un 32 GB. Pagarías precio de 32 por 24.
4. **32+32 = 64 GB también sale mal**: cuesta el doble y tiras el módulo que ya
   tienes.
5. **Hazlo pronto.** La RAM va a subir otro 30-40 % este trimestre.

**El módulo concreto:** ADATA `AD5S560032G-S`, 32 GB DDR5-5600 CL46 SO-DIMM,
**$6,829 MXN en Cyberpuerta**, 39 piezas en stock.

---

## 1 · Lo que el reporte que me pasaste no dice, y es lo que más pesa

El reporte técnico está bien hecho: confirma el módulo, la ranura libre y las
cuatro rutas. Pero le faltan tres cosas, y las tres cambian la decisión.

### a) Ahora mismo estás en canal simple, y eso sí se nota

Un módulo = **un canal**. El ancho de banda de memoria es aproximadamente **la
mitad** del que tendrías con dos módulos. En un Ryzen 8845HS con **16 hilos**,
eso es un cuello de botella real en compilaciones, suites de tests y builds de
Docker — que es exactamente lo que esta máquina va a hacer todo el día.

> **Meter cualquier segundo módulo es la mejora de rendimiento más grande que
> tienes disponible**, más que cualquier diferencia entre 40, 48 o 56 GB. Y el
> reporte no lo menciona ni una vez.

Cuando metas el segundo módulo, AMD usa **modo flexible**: la parte que empareja
va en doble canal y el sobrante en simple. Con 24+32 → **48 GB a doble canal y
8 GB a canal simple**. Con 24+16 → 32 GB a doble y 8 a simple.

### b) El reporte dimensiona una workstation, y esto es un servidor sin pantalla

Su §12 razona sobre «PyTorch, Jupyter, VS Code, navegadores con muchas
pestañas». Esta máquina **no va a tener nada de eso**: es Ubuntu Server sin
escritorio, corriendo agentes de Claude Code, el puente de Telegram y Docker
para staging. El presupuesto real:

| Pieza | RAM |
|---|---:|
| Ubuntu Server sin escritorio | ~1,0 GB |
| Puente de Telegram | ~0,3 GB |
| Coordinador de Claude Code | 1,5-3 GB |
| 3 subagentes (el techo medido de `workstream-dispatch`) | 4,5-12 GB |
| Docker + staging | 2-6 GB |
| **Total típico** | **9-22 GB** |

**Con 24 GB funciona, pero sin margen ninguno.** El día que corras tres frentes
y un staging a la vez, estás rozando el techo — y estos agentes tienen fugas de
memoria documentadas, que es justo el escenario donde el margen te salva.

Con 40 GB vas cómodo. Con 56 GB vas holgado y dejas de pensar en esto.

### c) La ranura libre es de un solo uso

Tienes **dos ranuras y una ocupada**. Lo que metas en la libre es lo que hay:
para ampliar después habría que **quitar** ese módulo, no añadir otro.

Eso convierte «empiezo barato y ya veré» en una trampa:

| Camino | Hoy | Si luego quieres más | Total |
|---|---:|---:|---:|
| 16 GB ahora | $3,749 | + un 32 GB en Q4 (~$9,000) y tiras el de 16 | **~$12,750** |
| **32 GB ahora** | **$6,829** | nada que hacer | **$6,829** |

El camino barato solo gana si 40 GB te bastan **para siempre**. Con staging de
proyectos por delante (la D9 sigue abierta), yo no apostaría a eso.

---

## 2 · Precios reales, agosto 2026

Cotizado hoy. **Precios en MXN, con IVA, y con el stock que había al mirar.**

| Capacidad | Modelo | Precio | Tienda | Stock |
|---|---|---:|---|---|
| **16 GB** | ADATA `AD5S560016G-S` CL46 | **$3,749** | Cyberpuerta | 10 pzas |
| 16 GB | Kingston FURY `KF556S40IB-16` CL40 | $3,899 | PCEL | 100+ |
| **24 GB** | Corsair `CMSX24GX5M1A5600C48` | *(último precio $5,069)* | Cyberpuerta / PCEL | **AGOTADO en los dos** |
| 24 GB | Crucial `CT24G56C46S5` | **360,66 USD** | Newegg (3.º) | importación · B&H lo da por **descontinuado** |
| **32 GB** | **ADATA `AD5S560032G-S` CL46** | **$6,829** | **Cyberpuerta** | **39 pzas** |
| 32 GB | Kingston FURY `KF556S40IB-32` CL40 | $6,999 | PCEL | 100+ |
| 32 GB | Kingston FURY `KF556S40IB-32` (mismo) | $8,939 | miPC | 99 pzas |
| 32 GB | Crucial `CT32G56C46S5` | — | Cyberpuerta / CityShop | **AGOTADO** |
| **2×32 GB** | ADATA ×2 | ~$13,658 | Cyberpuerta | armándolo suelto |

**Tres cosas saltan a la vista:**

- **Crucial desapareció del canal mexicano.** Los tres modelos que el reporte
  recomienda por nombre —`CT16/CT24/CT32G56C46S5`— están agotados, con aviso de
  «sin existencias desde hace varias semanas, probablemente fuera del mercado».
  El reporte te manda a comprar exactamente lo que no se consigue.
- **El módulo de 24 GB cuesta casi lo mismo que uno de 32 GB** (360 vs 399 USD
  en Newegg) **y no hay en México.** Eso mata la opción de 48 GB por sí sola:
  pagarías precio de 32 GB, con importación y espera, para recibir 24 GB.
- **La misma pieza Kingston vale $6,999 en PCEL y $8,939 en miPC.** 28 % de
  diferencia. Cotiza en dos o tres tiendas antes de dar clic, siempre.

### Por qué el ADATA y no el Kingston FURY

Cuesta $170 menos, pero no es por eso. El FURY Impact es **CL40 con perfil
XMP**; el ADATA es **CL46 JEDEC**, igual que tu módulo Micron. Al mezclar, el
sistema se queda con el temporizado más lento de los dos, así que el CL40 no te
compra nada — y sí añade una variable de más en una máquina que tiene que
arrancar sola a las 4 de la mañana sin nadie mirando. **Para un servidor, menos
variables gana.**

---

## 3 · Las cuatro rutas, ordenadas para ESTA máquina

| Ruta | Total | Coste | Doble canal | Veredicto |
|---|---:|---:|---|---|
| **24 + 32** | **56 GB** | **$6,829** | 48 GB dobles + 8 simples | ✅ **Cómpralo** |
| 24 + 16 | 40 GB | $3,749 | 32 dobles + 8 simples | ⚠️ Solo si el dinero aprieta hoy |
| 24 + 24 | 48 GB | ~$7,500 + importación | 48 GB dobles | ❌ **Descartada**: sin stock, precio de 32 por 24 |
| 32 + 32 | 64 GB | ~$13,658 | 64 GB dobles | ❌ El doble de dinero y tiras tu módulo |

**El orden del reporte (56 > 48 > 40) casi coincide con el mío, pero por razones
distintas y con una diferencia importante**: él pone 48 GB como «mejor
equilibrio» y en el mercado real esa opción **no existe**.

---

## 4 · Lo del vendedor: reclama, no devuelvas

Te vendieron 32 GB y te entregaron 24 GB. Eso es un incumplimiento y tienes la
evidencia. **La pregunta no es si reclamar, sino qué pedir.**

### Pide reembolso parcial, no devolución

| | Devolver | **Reembolso parcial** |
|---|---|---|
| Tiempo | 2-4 semanas sin máquina | días |
| Riesgo | el reemplazo puede venir del mismo lote mal etiquetado | ninguno |
| RAM | te quedas sin el módulo de 24 GB | **te lo quedas** |
| Precio de la RAM al recomprar | 30-40 % más caro en Q4 | compras ahora |

**Cuánto pedir:** los 8 GB que faltan, a precio de hoy, valen entre **$1,700 y
$2,300 MXN** (un 16 GB cuesta $3,749 y un 32 GB $6,829: sale a ~$215/GB). Pide
**$2,500** y negocia. Los vendedores de Amazon MX y Mercado Libre aceptan
reembolso parcial con mucha frecuencia, porque **una devolución les cuesta más
que el descuento**.

Y si no aceptan: entonces sí devuélvela, porque el argumento cambia.

### ⚠ Haz esto ANTES de tocar nada

**No abras la carcasa ni instales Linux hasta cerrar la reclamación.** Instalar
Ubuntu borra Windows, y con él las capturas que prueban qué te entregaron.
Abrir la máquina le da al vendedor un argumento para rechazarte.

Guarda, en este orden:

1. Captura del anuncio donde dice **32 GB** (y el número de pedido).
2. Captura del Administrador de tareas mostrando la memoria total.
3. La salida de PowerShell con `Manufacturer`, `PartNumber` y `Capacity`.
4. La salida con `MemoryDevices = 2`.
5. La factura.

Esa parte del reporte que me pasaste es correcta y es la más urgente de todo el
documento.

---

## 5 · El otro argumento, y no es menor: el reloj

Estamos en una **escasez global de DRAM**. Los fabricantes —Samsung, SK Hynix,
Micron— están desviando producción a **HBM para GPUs de centros de datos de IA**,
que deja mucho más margen. Cerca del **50 % de la producción mundial ya está
comprometida en contratos largos con hyperscalers**, y se espera que llegue al
70 %.

Lo que eso significa en fechas:

| Periodo | Movimiento esperado |
|---|---|
| Q3 2026 (**ahora**) | +40-50 % sobre Q2 |
| Q4 2026 | **+30-40 % adicional** |
| 2027 | +40-45 % interanual |
| 2028 | primer alivio previsto |

Un SODIMM de 32 GB ronda hoy $6,800-7,000 MXN cuando históricamente costaba
cerca de la mitad. **Si lo compras en noviembre, el mismo módulo puede estar
cerca de $9,000.**

> Esto convierte el módulo de 24 GB que te enviaron por error en algo que **vale
> más de lo que valía cuando lo compraste**. Devolver la máquina significa
> devolver ese módulo y recomprar memoria en un mercado peor. Es el argumento
> más fuerte de todo el documento para quedártela.

---

## 6 · Qué hacer, en orden

1. **Hoy** — junta las cinco capturas y abre la reclamación pidiendo reembolso
   parcial de **$2,500 MXN**. No abras la máquina.
2. **Mientras contestan** — compra el **ADATA `AD5S560032G-S`** en Cyberpuerta
   ($6,829). Cotiza también en PCEL y DDTech por si bajó; la dispersión entre
   tiendas es del 28 %.
3. **Cuando llegue** — apaga, desenchufa, quita la tapa inferior, y mete el
   módulo en la ranura libre a 45° hasta que las pestañas laterales encajen
   solas. **No fuerces**: solo entra en una orientación.
4. **Enciende y comprueba.** Windows todavía está, aprovéchalo:

   ```powershell
   Get-CimInstance Win32_PhysicalMemory | Format-Table DeviceLocator, Manufacturer, PartNumber, Capacity, Speed, ConfiguredClockSpeed
   ```

   Deben salir **dos filas**, y `ConfiguredClockSpeed` debe decir **5600** en
   las dos. Si dice 4800 o 5200, el sistema bajó la velocidad para poder
   convivir con los dos módulos: **no es un fallo**, pero anótalo.

5. **MemTest86, una pasada completa, antes de instalar nada.** Descárgalo de
   <https://www.memtest86.com>, grábalo a un USB y déjalo correr — tarda entre
   2 y 4 horas con 56 GB, así que déjalo de noche.

   > **Esto no es opcional al mezclar capacidades distintas.** Hay reportes de
   > SER8 con ciertos kits que dan errores de memoria. Un error de RAM en un
   > servidor 24/7 no se manifiesta como un fallo claro: se manifiesta como
   > cosas raras cada varios días que te vuelven loco durante un mes. **Cuatro
   > horas ahora, o cuatro semanas después.**

6. **Solo entonces**, `23-MANUAL-INSTALACION-SER8.md` desde la Parte 1.

---

## 7 · Lo que cambia en el resto del setup

- **`MemoryMax` de los servicios**: con 24 GB y techo de 3 frentes, **4 GB por
  frente**, no 8. Si te quedas en 56 GB, puede volver a 8 GB. Está anotado en la
  Parte 8.3 del manual.
- **Swap**: con 24 GB deja de ser una formalidad. Los 8 GB del manual se quedan
  aunque subas a 56.
- **D8 queda cerrada de una forma que no habíamos previsto**: la pregunta era
  «32 o 64 GB» y la respuesta real del mercado es **56 GB por un tercio de lo
  que costarían 64**.
- **D9 (staging permanente o bajo demanda)** se vuelve más fácil con 56 GB:
  puedes dejarlo permanente sin pelearte con el presupuesto.

---

## Lo que no pude comprobar

- **Mercado Libre y Amazon México bloquean el acceso automático** (robots.txt),
  así que no tengo precios verificables de ninguno de los dos. Suelen ser
  competitivos: **cotiza ahí también antes de comprar**, con los números de
  parte exactos de la tabla.
- **El precio del Corsair de 24 GB ($5,069)** es el último publicado en
  Cyberpuerta, con el producto **agotado**. No es un precio comprable y no lo
  uses para decidir.
- **No probé la mezcla concreta** Micron 24 GB + ADATA 32 GB en un SER8. Es una
  combinación razonable —los dos JEDEC 5600 CL46— pero **razonable no es
  verificado**, y por eso el paso 5 es MemTest86 y por eso el paso 2 dice que
  compres donde acepten devolución.

---

## Fuentes

- [Cyberpuerta — ADATA AD5S560032G-S 32 GB DDR5-5600 CL46 SO-DIMM](https://www.cyberpuerta.mx/Computo-Hardware/Memorias-RAM-y-Flash/Memorias-RAM-para-Laptop/)
- [Cyberpuerta — ADATA AD5S560016G-S 16 GB DDR5-5600 CL46](https://www.cyberpuerta.mx/Computo-Hardware/Memorias-RAM-y-Flash/Memorias-RAM-para-Laptop/Memoria-Ram-Adata-AD5S560016G-S-DDR5-5600MHz-16GB-CL46-SO-DIMM.html)
- [PCEL — Kingston FURY Impact KF556S40IB-32](https://www.pcel.com/Kingston-KF556S40IB-32-Memoria-SODIMM-Kingston-FURY-Impact-Black-DDR5-PC5-44800-5600MHz-Non-ECC-CL40-32GB-474672)
- [Cyberpuerta — Corsair 24 GB SO-DIMM (agotado)](https://www.cyberpuerta.mx/Computo-Hardware/Memorias-RAM-y-Flash/Memorias-RAM-para-Laptop/Memoria-RAM-para-Laptop-Corsair-Vengeance-DDR5-5600MHz-24GB-Non-ECC-CL48-262-pin-SO-DIMM.html)
- [B&H — Crucial CT24G56C46S5, marcado descontinuado](https://www.bhphotovideo.com/c/product/1775612-REG/crucial_ct24g56c46s5_ram_24gb_ddr5_5600_so_dimm.html)
- [Newegg — Crucial CT2K32G56C46S5 64 GB kit](https://www.newegg.com/crucial-64gb-ddr5-5600-cas-latency-cl46-laptop-memory/p/N82E16820156317)
- [La crisis de la RAM en 2026: +40-50 % en Q3, +30-40 % en Q4, sin alivio hasta 2028](https://wwwhatsnew.com/2026/07/01/crisis-ram-precio-ddr4-ddr5-sube-40-50-por-ciento-2026/)
- [Escasez de memoria 2026 — causas y horizonte](https://techdigitalia.com/escasez-memoria-ram-2026-crisis-global/)
- [Foro Beelink — SER8 actualizado a 64 GB (2×32)](https://bbs.bee-link.com/d/4019-beelink-ser8-8845hs-ram-upgade-32gb-2x16gb-5600--64gb-2x32gb-4800)
- [ServeTheHome — SER8 de fábrica con 2×16 GB Crucial DDR5-5600](https://www.servethehome.com/beelink-ser8-review-amd-ryzen-7-8845hs-powered-mini-pc/2/)
