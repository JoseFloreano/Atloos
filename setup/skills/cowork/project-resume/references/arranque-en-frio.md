# Arranque en frío — los dos matices del paso 2

Detalle del paso 2 del `SKILL.md`, extraído en el sprint 10. Gemelo del fichero
del mismo nombre en la variante de Claude Code, con una diferencia que lo cambia
todo: **aquí stage-ar cuesta**. En Cowork cada fichero que entra a la sesión se
paga, así que la regla no es «lee menos», es **«no stage-es lo que no vas a
leer»**.

## 1 · El backlog se menciona, no se carga

Si `_PROJECT.md` trae la línea:

```
Backlog: N ítems → [[pendientes]]
```

**menciónala sin stage-ar el archivo** — basta con decir *«hay N más en el
backlog»*. El arranque debe costar lo mismo que antes de que el backlog
existiera; si cargarlo fuera automático, partir el tablero en dos ficheros no
habría servido de nada. **Solo cárgalo si el usuario pregunta por él.**

## 2 · `Estado del repo:` — y los tres casos, que no son uno

Compara el campo contra `origin/main`. Los tres desenlaces son distintos y se
reportan distinto:

| Situación | Qué se dice |
|---|---|
| El campo existe y **coincide** | nada; el vault está al día |
| El campo existe y **difiere** | **avisa**: *«el vault va atrás — tómalo como orientación, no como verdad»* |
| El campo existe y **no hay repo conectado** | sin repo no se **puede comparar**: **reporta** «no verificado», que no es lo mismo que estar al día |
| **El campo no está** (proyecto anterior a la convención) | **dilo UNA vez** y sigue: `session-close` lo añadirá al cerrar |

⚠ **El último caso es el que produce ruido si se hace mal.** Si el campo no
existe, no reportes «no verificado»: no hay nada que verificar, y repetirlo cada
arranque entrena al usuario a ignorar los avisos. **No fabriques ruido por un
campo que su época no pedía** — es la misma regla que hace que el validador de
reportes archive los formatos viejos en vez de exigirles el contrato de hoy.
