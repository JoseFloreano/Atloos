# El criterio del reloj — un suelo, nunca un techo

La ley de la skill dice que **el código de salida no es el estado**. La duración
es la segunda señal que lo demuestra, y es gratis: ya la tienes medida.

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

1. **Ten el suelo escrito.** Es el mínimo histórico de una corrida completa y
   sana en esa máquina, no un promedio. Si no lo tienes, la primera corrida
   verificada lo establece — y se anota.
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

## Y el otro caso, el que ya estaba

Un instrumento sin `load_dotenv()` "midió" 1,5 M de filas en **3,6 s**. Mismo
patrón fuera del gate: el tiempo delataba lo que el resultado no.
