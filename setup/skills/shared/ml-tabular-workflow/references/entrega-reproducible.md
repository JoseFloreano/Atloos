# Entrega reproducible — lo que de verdad se pide

## El marco correcto, y por qué no se copia entero

**Model Cards** (Mitchell et al., FAT* 2019) y **Datasheets for Datasets**
(Gebru et al., CACM 2021) son el marco correcto: documentan uso previsto,
población, métricas desagregadas, limitaciones y procedencia del dato.

Y para **un desarrollador solo** son sobre-ingeniería. Una datasheet completa es
un documento de equipo con revisión; pedirla aquí garantiza que no se escriba
ninguna. Lo que sigue es el recorte que sí se sostiene, y conserva la parte que
importa: **que dentro de seis meses se pueda reproducir el número**.

## Los seis mínimos

### 1 · Semillas fijas, todas

`random_state` en el split, en el modelo, en cualquier remuestreo, y la semilla
del framework si aplica. Una semilla suelta convierte «no reproduce» en una
tarde perdida.

### 2 · Lockfile con versiones exactas

`requirements.txt` con `==`, o `uv.lock` / `poetry.lock`. `scikit-learn>=1.3` no
es reproducible: entre menores cambian defaults de estimadores y de codificadores
y el número se mueve sin que nadie tocara nada.

### 3 · Hash o timestamp del snapshot de datos

El dataset **cambia**: filas nuevas, correcciones retroactivas, borrados. Sin un
identificador del snapshot no hay forma de saber si la diferencia de mañana es
del modelo o del dato. Un hash del fichero, o la marca de la partición, o la
fecha de corte de la consulta — cualquiera sirve mientras quede escrito.

### 4 · Los índices exactos del split, guardados

El más olvidado y el que más caro sale.

> **`random_state=42` no protege si cambia el tamaño del dataset.**

La semilla fija la secuencia pseudoaleatoria, no la partición: con una fila más,
`train_test_split` produce **otro reparto**. Si alguna vez hay que comparar el
modelo nuevo contra el viejo, hacerlo sobre splits distintos no compara nada.

Guarda los índices (o las claves primarias) de train / validación / test como
artefacto, junto al modelo.

### 5 · Model card de una página

Seis apartados, y cabe en una página:

- **Para qué sirve** y, sobre todo, **para qué no** (uso fuera de alcance).
- **Datos**: origen, periodo, snapshot, tamaño, balance de clases.
- **Métrica y umbral**, con la matriz de coste que lo justifica.
- **Baseline** contra el que se compara y por cuánto lo supera.
- **Limitaciones conocidas** y en qué subpoblaciones va peor.
- **Cuándo hay que revisarlo** (fecha o condición de deriva).

### 6 · Registro de experimentos ligero

No hace falta plataforma. Un CSV o un JSON por corrida con: fecha, commit,
snapshot de datos, hiperparámetros, métrica, umbral, y una línea de qué se
probaba. El valor no está en la herramienta: está en poder contestar *«¿esto ya
lo probamos?»* sin fiarse de la memoria.

## La prueba de que está bien

Borra el entorno, clónalo desde el lockfile, corre el script y **compara el
número con el reportado**. Si no coincide, falta uno de los seis. Si no puedes
hacer esa prueba, la entrega no está terminada — da igual lo bueno que sea el
modelo.
