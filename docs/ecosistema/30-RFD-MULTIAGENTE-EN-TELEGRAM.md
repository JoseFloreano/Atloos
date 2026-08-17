---
title: RFD 30 — El multiagente en Telegram, y quién arbitra cuando no hay nadie delante
fecha: 2026-08-17
sprint: 11
status: propuesto
decisiones: [D20, D21, D22, D23, D24, D25, D26, D27]
arbitradas: []
depende_de: [ADR-20260805-workstreams-paralelos, ADR-20260801-bot-memoria-y-perfil, RFD-25, RFD-26]
implementado: no
---

# RFD 30 — Una conversación, N frentes

La pieza base ya existe: `gitops.py` hace **worktree por conversación**. Lo que
falta es el salto de *una conversación, un worktree* a *una conversación, N
frentes*. Este documento no lo construye — decide **bajo qué reglas** se
construiría.

**Cero código.** Siete decisiones numeradas, con mi voto y su porqué.

---

## 0 · La precondición, antes de cualquier decisión

Haciendo el mapa de S4 aparecieron dos defectos del daemon que **no son de
diseño multiagente, pero lo bloquean**:

| Dónde | Qué pasa en Linux |
|---|---|
| `tg_daemon.py:111` | Las denegaciones de secretos (`.ssh`, `.aws`, `.gnupg`, `.config/gh`, los `.env`) se construyen con separador `\` hardcodeado. En Linux **no casan con nada**: fallan abiertas, en silencio |
| `tg_daemon.py:1229` | La segunda barrera del aislamiento de T2 —la que impide escribir en el árbol del usuario— tiene la misma causa y **se evapora en Linux** |

Con **un** frente en Windows esto lleva latente desde que se escribió. Con **N**
frentes en la SER8 se multiplica por N y se activa el mismo día del despliegue.

> **D20 · ¿El multiagente espera a que esos dos estén arreglados y con arnés?**
> **Mi voto: sí, y es bloqueante.** No por prudencia genérica: porque la
> superficie de riesgo de la pregunta 4 se calcula sobre barreras que hoy, en la
> máquina de destino, **no existen**. Discutir qué no puede hacer un frente
> mientras la barrera no aplica es discutir sobre un dibujo.

---

## 1 · Quién arbitra cuando el humano está en el teléfono

Hoy `workstream-dispatch` supone un humano delante que arbitra escalaciones. Por
Telegram no lo hay: hay un humano **intermitente**, que puede tardar horas.

La tentación es poner un LLM de coordinador. **El ADR-20260801 ya resolvió esta
forma exacta para la memoria**: el bot accede al sistema de memoria *a través
del daemon (código determinista), nunca a través del LLM*. La misma razón vale
aquí, y más fuerte: un coordinador LLM que arbitra escalaciones sin nadie
mirando es precisamente el modo de fallo que el gate existe para impedir.

> **D21 · ¿Quién es el coordinador?** **Mi voto: el daemon, y solo el daemon.**
> Reparte frentes, recoge estados y publica; **no decide nada que un humano
> tendría que decidir**. Lo que hoy es «el coordinador arbitra» pasa a ser «el
> daemon pregunta y espera». Si algún día hay un LLM coordinando, va **debajo**
> del daemon y sin autoridad para desbloquear.

### Y qué pasa si nadie contesta

Tres opciones reales: **esperar**, **decidir solo**, o **aparcar**.

| Opción | Qué gana | Qué pierde |
|---|---|---|
| Esperar indefinidamente | nada se rompe | el frente ocupa recursos y el chat calla: indistinguible de colgado |
| Decidir solo | avanza | es exactamente lo que ningún criterio de esta casa permite |
| **Aparcar** | conserva el trabajo, libera la máquina, deja el porqué escrito | hay que retomar a mano |

> **D22 · La escalación tiene reloj, y su vencimiento es APARCAR.** **Mi voto:**
> al escalar, el frente sigue con el trabajo que **no dependa** de la respuesta;
> cuando se queda sin trabajo independiente **o** pasan **60 minutos**, lo que
> ocurra primero, **aparca**: commit del avance en su rama, una nota con la
> pregunta sin responder, y para. A las **3 horas** el daemon lo repite en el
> chat una sola vez y no vuelve a insistir.
>
> Aparcar es barato —una rama y una nota— y es la única salida que no miente:
> ni finge que avanza, ni finge que terminó. **Un frente aparcado con su
> pregunta escrita vale más que uno que adivinó bien.**

---

## 2 · Cuántos frentes

⚠ **El techo de 3 no está anclado, y no se cita aquí como medido.** El ×2,05 que
lo sostenía salió de **otra máquina** (`ProgramadoMaxi2`), **otra suite**, y su
pico es `[AR]` — ver `workstream-dispatch/references/medir-el-techo.md`. Lo que
sigue no lo reemplaza por otro número inventado: cambia **quién** pone el techo.

**Y no se pone `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`** (arbitrado en contra,
RFD 26 §3.4). Además sería la herramienta equivocada: es una pista para el
agente, no un límite que la máquina imponga.

> **D23 · El techo no es un número escrito: es lo que la máquina concede.**
> **Mi voto:** se arranca en **2 frentes**, y el límite real lo pone el
> presupuesto de recursos de D24 —scopes de systemd, que sí son un techo
> aplicado— más **una regla de integración**: *un solo integrador a la vez*,
> venga de donde venga (es el paso 4 de `workstream-merge-gate`, y no cambia
> porque el disparador sea un teléfono).
>
> Subir de 2 exige **una medida en la SER8**, no una intuición: dos jornadas
> comparables, con el tiempo de pared y el pico de RSS por frente anotados.
> Mientras no exista esa medida, 2. Y cuando exista, el número que salga se
> escribe **con la máquina y la suite al lado**, que es la lección que costó
> cuatro sprints.

---

## 3 · La contención real: **la RAM ya no es el cuello**

Aquí hay que corregir el supuesto del encargo, y con números medidos en la SER8
el 2026-08-17:

| | Valor |
|---|---|
| Instalada (24 + 32, confirmado en BIOS) | 56 GB |
| **Visible al SO** | **50,8 GiB** (`MemTotal`) — la diferencia se la queda el firmware y la iGPU 780M |
| Disponible en reposo | 49 GiB (uso base: 1,0 GiB) |
| Swap | 8 GiB (`/swap.img`) |
| Núcleos | 16 (Ryzen 7 PRO 8845HS) |
| cgroup | **v2** · systemd 255 |
| Controladores delegados al `user.slice` | **`cpu memory pids`** → los límites por frente se ponen **sin root** |
| Disco libre | 857 GiB |

El presupuesto del doc 24 se escribió suponiendo **24 GB**. Rehecho sobre 50,8
GiB visibles:

| Partida | Reserva |
|---|---|
| Ubuntu Server | 2,0 GiB |
| Puente + daemon | 0,5 GiB |
| Coordinador | 3,0 GiB |
| Docker + staging | 6,0 GiB |
| **Reservado** | **11,5 GiB** |
| **Libre para frentes** | **≈ 39 GiB** |

A 4 GiB de techo por frente, **caben ~9**. A 3 GiB, ~13.

> **Conclusión que hay que decir en voz alta: con 56 GB la RAM deja de ser la
> contención.** Con 24 GB lo era y el doc 24 tenía razón. Hoy el cuello se ha
> movido, y los candidatos son el coste de API, el reloj de pared de la suite, y
> **el humano que tiene que revisar N frentes desde un teléfono** — que no
> escala con la RAM.

> **D24 · Los límites por frente se ponen con systemd, y se ponen igual.**
> **Mi voto:** cada frente en su scope con `MemoryHigh=3G`, `MemoryMax=4G`,
> `MemorySwapMax=0` y `CPUQuota=200%`. No porque falte RAM —sobra— sino porque
> **un techo por frente convierte un frente que se desboca en un frente muerto
> en vez de en una máquina inservible**. `MemorySwapMax=0` es la parte que
> importa: con 8 GiB de swap, sin esa línea un frente desbocado no muere, se
> arrastra, y arrastra a los otros. Es la diferencia entre un fallo limpio y una
> tarde perdida.
>
> Y el motivo por el que esto solo existe en Linux ya estaba escrito (RFD 26
> §1.4): en Windows no hay equivalente. **Es un argumento a favor de que el
> multiagente viva en la SER8 y no en la Legion.**

---

## 4 · Qué NO puede hacer un frente lanzado desde el teléfono

T2 tiene tres reglas y una allowlist. N frentes escribiendo a la vez las
multiplican por N. La lista siguiente es **cerrada**: lo que no está, se
investiga antes de permitirse — no se excusa.

| Prohibido, aunque el humano lo pida | Por qué |
|---|---|
| Empujar o integrar a rama protegida | El merge es de D25, y pasa por un integrador único con confirmación explícita |
| Escribir fuera de **su** worktree | Es la barrera de `tg_daemon.py:1229`, hoy rota en Linux (§0) |
| Leer rutas de secretos | Es la barrera de `tg_daemon.py:111`, hoy rota en Linux (§0) |
| Modificar la propia allowlist, el `projects.json` o los hooks | Un frente que puede ampliar sus permisos no tiene permisos |
| Borrar worktrees o ramas que no sean los suyos | Un frente no arregla a otro frente |
| Tocar el modelo de ningún agente | D18 sigue suspendida |
| Instalar dependencias del sistema | Cambia la máquina para todos, y nadie lo ve desde el chat |

> **D25 · «El humano lo pidió» no levanta ninguna de estas.** **Mi voto: sí,
> cerrado.** Una orden por Telegram llega sin contexto, sin diff delante y a
> menudo desde la calle. El sitio para levantar una prohibición es una sesión
> con la pantalla, no un chat. Lo que el humano SÍ puede hacer desde el teléfono
> es **aprobar** algo que el daemon ya verificó — que es el modelo del botón de
> `/merge`, y funciona.

---

## 5 · Qué se ve desde el chat

> *«Un frente que tarda 20 minutos sin decir nada es indistinguible de uno
> colgado.»* Correcto, y hoy el bot ya tiene la pieza: `.tg/progress.md`, una
> línea por etapa, que `/progress` publica.

Con N frentes el problema cambia de forma: no es *«¿qué está haciendo?»* sino
*«¿cuál de los N está atascado?»*.

> **D26 · El silencio es un estado, y se reporta solo.** **Mi voto:** cada
> frente escribe su `.tg/progress.md` como hoy; el daemon publica **un** panel
> con una línea por frente —rama, etapa, minutos desde la última línea— y marca
> **`SILENCIO`** al que pase de **10 minutos** sin escribir. No lo mata: lo
> nombra. Un frente legítimamente lento (una suite de 19 min ya pasó, RFD 26)
> sigue vivo y visible; uno colgado deja de esconderse entre los otros.
>
> El umbral es un **suelo de atención, nunca un techo de ejecución** — la misma
> distinción del criterio del reloj, y por la misma razón: convertirlo en un
> techo produciría muertes en falso justo cuando más frentes hay.

---

## 6 · La deuda que este RFD hereda y no puede ignorar

Del mapa de S4: **el daemon y el gate no comparten evidencia.** El gate escribe
`.claude/gate-verde.json` en el `.git` común; el daemon guarda `test_ok_sha` en
su estado. Con un frente es una duplicación fea. Con N frentes es peor: un verde
producido por un frente no lo puede leer el que integra.

> **D27 · Una sola forma de evidencia.** **Mi voto: sí, y antes de subir de 2
> frentes.** Que `/test` escriba la evidencia en el formato del gate, en el
> `.git` común, que es donde ya la ve *quien integre desde cualquier worktree*.
> Con eso el `/merge` del bot deja de tener su propio criterio y pasa a tener el
> de la casa — incluidos **el reloj** y **los tests que el implementador no
> escribió**, que son los dos huecos medidos en el doc 29.

---

## Lo que no pude comprobar

- **El pico real de RSS por frente en la SER8.** El 4 GiB de D24 viene del
  rango del doc 24 (1,5-4 GiB por subagente), que se midió en otra máquina. Es
  una reserva prudente, **no una medida de esta**. La primera jornada real la
  corrige.
- **Si el perfil bot puede llevar hooks.** El doc 29 establece que hoy
  `claude-tg-profile` queda fuera de lo que `sync-hooks` cablea; no he probado
  a apuntarlo ahí ni sé si el perfil recortado los aceptaría sin romper la
  autenticación.
- **El coste de API de N frentes en paralelo desde el puente.** No hay ninguna
  jornada multiagente por Telegram de la que sacar el número.

---

## Resumen de decisiones

| # | Decisión | Mi voto |
|---|---|---|
| **D20** | ¿Bloquea el multiagente hasta arreglar los dos separadores? | **Sí, bloqueante** |
| **D21** | ¿Quién coordina? | **El daemon, determinista; nunca un LLM** |
| **D22** | ¿Qué pasa si nadie contesta una escalación? | **Aparcar a los 60 min; recordatorio único a las 3 h** |
| **D23** | ¿Cuántos frentes? | **Empezar en 2; el techo lo pone systemd, no un número escrito** |
| **D24** | ¿Cómo se acota cada frente? | **`MemoryHigh=3G` · `MemoryMax=4G` · `MemorySwapMax=0` · `CPUQuota=200%`** |
| **D25** | ¿«El humano lo pidió» levanta las prohibiciones? | **No. Lista cerrada** |
| **D26** | ¿Cómo se ve un frente atascado? | **Panel por frente; `SILENCIO` a los 10 min, sin matar** |
| **D27** | ¿Evidencia unificada gate ↔ daemon? | **Sí, antes de subir de 2 frentes** |

**Las firma el humano. No están implementadas.**
