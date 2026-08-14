# Higiene de shell — cuatro reglas, cuatro incidentes

No es un tratado de bash. Son **cuatro fallos del 2026-08-13**, ninguno del
modelo y todos del entorno: uno casi filtra un secreto, otro borró las palabras
que importaban de un mensaje de commit, y dos hicieron leer un resultado que no
existía. Van en el despacho porque las paga el frente, no el coordinador.

## 1 · Nunca `source` de un fichero de entorno

> 🔴 Un `source` del `.env` **imprimió parte de una contraseña de MySQL en el
> transcript**. El transcript se guarda, se comparte y se pega en reportes.

`source`/`.` ejecuta el fichero: cualquier línea con eco, error o expansión
acaba en la salida. Y un `.env` no está escrito para ser ejecutado.

```bash
# NO
source .env

# SÍ, desde Python (la vía por defecto)
from dotenv import load_dotenv; load_dotenv("/ruta/explicita/.env")

# SÍ, desde bash, si no queda otra: exporta en silencio y vuelve a apagarlo
set -a; . ./.env >/dev/null 2>&1; set +a
```

Y por lo mismo el `.env` **se copia al worktree, nunca se enlaza** (bloque 2).

## 2 · Heredoc siempre con el delimitador entrecomillado

> 🔴 Backticks sin escapar dentro de un heredoc: **bash los ejecutó** y el commit
> `f1fead9` perdió **las cuatro palabras que nombraban lo importante**. El rastro
> fue un `en_duda: command not found` que nadie miró a tiempo.

```bash
# NO — expande $VAR, `cmd` y \
git commit -F- <<EOF
Arregla `en_duda` y $ruta
EOF

# SÍ — el delimitador entrecomillado apaga TODA expansión
git commit -F- <<'EOF'
Arregla `en_duda` y $ruta
EOF
```

Regla sin excepción para texto en prosa (mensajes de commit, documentos,
reportes): **`<<'EOF'`**. Solo se usa `<<EOF` cuando de verdad quieres interpolar,
y entonces se dice en el propio comando.

## 3 · `grep -c` sale 1 cuando cuenta 0

> 🔴 Un `grep -c` que contó 0 **rompió una cadena `&&`** y el borrado de ramas
> nunca corrió. La salida imprimió «ESTADO FINAL» tan tranquila.

Contar cero no es un error, pero `grep` lo señaliza como tal — igual que
`grep -q` sin coincidencias. En una cadena `&&`, eso aborta el resto en silencio.

```bash
# NO
git branch -r | grep -c "tg/" && git push origin --delete ...

# SÍ
n=$(git branch -r | grep -c "tg/" || true); echo "$n"; git push origin --delete ...
```

En cadenas de limpieza, `;` en vez de `&&` salvo que la dependencia sea real.

## 4 · El exit code NO se lee detrás de una tubería

> 🔴 Tres salidas perdidas por el instrumento: `tail -4` se comió líneas
> `FAILED`, `tail -1` ocultó un error de merge, y el `grep` de arriba. Es la
> misma trampa que la auditoría 22 ya documentó — **y se volvió a pisar dos
> veces el mismo día**.

`cmd | tail` deja en `$?` el estado de `tail`, que casi siempre es 0. Un
`echo $?` detrás de una tubería es un mentiroso silencioso.

```bash
# NO
py arnes.py | tail -5; echo $?

# SÍ — sin tubería
py arnes.py > salida.txt 2>&1; echo $?; tail -5 salida.txt

# SÍ — con tubería, leyendo el estado del PRIMERO
py arnes.py | tail -5; echo "${PIPESTATUS[0]}"
```

Y el corolario que vale para cualquier filtro: **`tail`/`head`/`grep` deciden qué
ves.** Si el veredicto depende de lo que salió, guarda la salida entera y filtra
después — nunca al revés.
