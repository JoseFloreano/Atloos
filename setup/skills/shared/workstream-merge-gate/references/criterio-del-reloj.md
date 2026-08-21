# El criterio del reloj — un suelo, nunca un techo

La ley de la skill dice que **el código de salida no es el estado**. La duración
es la segunda señal que lo demuestra, y es gratis: ya la tienes medida.

## Un suelo sin máquina no es un suelo (2026-08-19)

El gate sobre la SER8 (floreano-server) dio **13 s** contra el suelo escrito de
**46-49 s**: muy por debajo de ⅔, o sea la señal de verde falso. **No lo era.**
Los 41 arneses salieron nombrados y el veredicto fue `41/41`. Dos causas, y las
dos invisibles en el número:

1. Los 46-49 s se midieron en **la Legion**, y el `_PROJECT.md` guardaba la cifra
   **sin decir de qué máquina era**.
2. En la SER8 **6 arneses corren parciales** — sin PowerShell, sin tokenizador,
   sin Python 3.10 (con exención declarada) y sin el SDK de Telegram: hacen menos
   trabajo. En la Legion esos 6 corren enteros.

Un suelo es «el mínimo de una corrida completa y sana **en esa máquina**». Sin
el nombre de la máquina no es comparable con nada, y comparar igualmente es
peor que no mirar el reloj: convierte la herramienta que caza verdes falsos en
una que tumba verdes buenos. Si el suelo que tienes no dice de dónde salió,
**remídelo aquí antes de usarlo** — no lo ajustes a ojo.
→ [[bug-suelo-del-reloj-sin-maquina]]

## El suelo, y por qué funciona

**Una corrida sospechosamente rápida no es un verde.** Si la suite tarda mucho
menos que su suelo conocido, algo no se ejecutó: faltaba un artefacto, un
fixture no cargó, el runner no descubrió los tests, o se corrió en un árbol
incompleto. El exit code sale 0 igualmente, porque cero tests fallidos y cero
tests corridos dan lo mismo.

**Está medido, no es teoría.** En la jornada del 2026-08-10 el gate cazó **dos
verdes falsos por la duración y ninguno por exit code**:

| Corrida | Duración | Suelo conocido | Qué escondía |
|---|---:|---:|---|
| 1.ª | **117 s** | ~330 s | la suite no corrió entera |
| 2.ª | **146 s** | ~330 s | el inventario copiado a los worktrees estaba **incompleto** |

El segundo caso es el que justifica el criterio entero: destapó un defecto del
procedimiento de despacho —lo que se copiaba a cada worktree no bastaba— que
ningún test rojo iba a revelar, porque los tests que faltaban ni siquiera se
intentaron.

## Cómo se usa

1. **Ten el suelo escrito, y con fecha.** Es el mínimo histórico de una corrida
   completa y sana **en esa máquina y con esa suite**, no un promedio. Si no lo
   tienes, la primera corrida verificada lo establece — y se anota.

   > ⚠ **Un suelo caduca cuando la suite crece, y el viejo desafina en la
   > dirección peligrosa.** El ⅔ de un suelo obsoleto es un umbral *más bajo*
   > que el correcto, así que acepta como buenas corridas que hoy son verdes
   > falsos. **Reanota el suelo cada vez que el conteo de tests cambie de forma
   > apreciable**, junto al número de tests que lo produjo — sin el conteo, el
   > segundo no dice nada.
   >
   > | Repo | Suelo | Tests | Fecha |
   > |---|---:|---:|---|
   > | recomendador-cobranza | **551 s** | 4 985 | 2026-08-17 · **vigente** |
   > | recomendador-cobranza | ~330 s | — | 2026-08-10 · **jubilado** |
   >
   > El ~330 s que aparece más abajo es el de la jornada del 08-10 y **se queda
   > ahí**: es la evidencia de aquel día, no el umbral de hoy. Aplicar el ⅔ con
   > él daría ~220 s donde el vigente da ~367 s.
2. **Compara cada verde contra él.** Regla práctica: por debajo de **~⅔ del
   suelo**, el verde no se acepta sin mirar.
3. **Mirar significa contar.** El número que resuelve la duda no es el tiempo:
   es **cuántos tests se ejecutaron** y **cuántos se saltaron**. Un verde rápido
   con la cuenta correcta es una máquina descargada; un verde rápido con menos
   tests es el fallo. La duración es el detector, el conteo es el diagnóstico.

## ⚠ El reverso: no lo conviertas en un techo

Esto es lo que hace peligroso el criterio si se implementa mal. **Lento no es
sospechoso.** Bajo carga real, la misma suite pasó de 6-7 min a **19 min 30 s**,
y en esas condiciones aparecieron **rojos que no eran rojos**: un test que medía
CPU y un `SIGTERM` de timeout. Ninguno de los dos era un defecto del código.

De ahí, tres cosas:

- **El suelo es un suelo.** No hay techo, no hay ventana, no hay rango. Solo la
  cota inferior dispara sospecha.
- **Un timeout no es un fallo del código** hasta que se reproduce sin carga. Con
  frentes en paralelo, la suite compite consigo misma.
- **Los tests sensibles a carga** —latencia, CPU, tiempos de espera— hay que
  saber cuáles son. Si uno de esos es el único rojo bajo carga, el veredicto
  correcto es *«repetir en serie»*, no *«rama rechazada»*.

Convertir esto en un techo produciría falsos rojos justo cuando más frentes hay,
que es cuando el gate tiene que ser fiable. Un gate que grita en falso se
desactiva, y entonces no queda gate.

## El verde que el reloj NO caza: más skips de los esperados

El suelo cubre la corrida que **no se ejecutó**. No cubre la que se ejecutó
entera y **se saltó de más**, y esa es la misma enfermedad con otra cara.

> Un worktree no hereda lo que git no versiona. Sin un CSV de 9,6 MB, la suite
> **no avisa: finge.** Cae a un dataset sintético **a propósito** —está escrito
> así— y salta **~115 tests de más**. Verde, exit 0, y una duración que puede
> quedar dentro del rango. Costó **tres corridas de gate** descubrirlo.

Por eso el conteo no es solo el diagnóstico del verde rápido: **es un detector
por derecho propio.**

- **El número de skips esperado se declara ANTES**, con el inventario del frente
  (bloque 2 de `workstream-dispatch` → `references/plantilla-despacho.md`).
- **Skips por encima de lo declarado ⇒ el verde no se acepta**, aunque el reloj
  esté en su sitio y no haya un solo rojo.
- **La frase que hay que poder decirle al frente**: *«si ves 115 skips de más,
  no es que tu código esté bien: es que te falta un artefacto.»*

⚠ **Firma, no techo** — igual que arriba. Un skip de más puede ser legítimo (un
test marcado, una dependencia opcional ausente a propósito). Lo que dispara es
la **diferencia contra un número declarado**, no un máximo inventado; y como la
firma del bloque 2, es **lista cerrada**: lo que no esté en ella se investiga,
no se excusa.

## Y el otro caso, el que ya estaba

Un instrumento sin `load_dotenv()` "midió" 1,5 M de filas en **3,6 s**. Mismo
patrón fuera del gate: el tiempo delataba lo que el resultado no.

## Las cifras que estaban en el cuerpo (sprint 10)

**Los dos verdes falsos**: **117 s** y **146 s** contra un suelo de **~330 s**,
en la jornada de los 16 subagentes. Ninguno de los dos se delató por exit code —
los dos salieron 0.

**Y el reverso, que es por qué esto es suelo y nunca techo**: bajo carga la misma
suite llegó a **19 min 30 s** y dio **rojos que no eran rojos**. Si el criterio
fuera «tarda demasiado, algo va mal», ese día habría tumbado un merge correcto.
