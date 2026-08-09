---
tipo: feedback
fecha: 2026-08-07
reporter: ejemplo
maquina: legion-win11
so: Windows 11
superficie: claude-code
claude_code: 2.1.219
tarea: Integrar la rama feat/redondeo a main en un repo de laboratorio
duracion_min: 40
turnos: 22
veredicto: sirvio-con-fricciones
skills_disparadas: [workstream-merge-gate, session-close]
skills_que_faltaron: []
hooks_disparados: [merge-gate-guard, check-vault-updated]
graphify: no-usado
bloqueantes: 1
---

# Feedback — integrar una rama a main con el gate

> Ejemplo de referencia. No es un reporte real: sirve para ver el formato y
> para probar el validador. Bórralo cuando haya reportes de verdad.

> Leyenda: `[R]` comprobado con un comando · `[AR]` impresión del agente ·
> `[H]` lo dice el humano.

## 1. Qué se intentó

[H] Cerrar una rama de trabajo y meterla a `main` sin saltarme el criterio, a
ver si el gate estorbaba o ayudaba.

## 2. Evidencia de máquina

```
$ claude --version
2.1.219 (Claude Code)

$ git log --oneline -1
dc34355 chore: ajusta la constante del IVA

$ git status --porcelain | wc -l
0
```

[R] Skills cargadas: `workstream-merge-gate` (al escribir «intégrala a main»),
`session-close` (al escribir «cerramos»).
[R] Hooks disparados: `merge-gate-guard` bloqueó una vez con exit 2 —
`.claude/gate-verde.json` tenía el sha anterior al último commit.
`check-vault-updated` no llegó a disparar.
[R] Coste (`/cost`): no disponible, se me olvidó correrlo antes de cerrar.

## 3. Qué funcionó

- [H] El bloqueo del hook fue correcto y el mensaje decía exactamente qué correr
  para arreglarlo. No tuve que buscar en la documentación.
- [R] Tras correr el helper, el merge pasó a la primera y quedó un solo commit
  squash.

## 4. Qué NO funcionó

- [H] Tuve que decir dos veces que quería integrar la rama. La primera vez el
  agente se puso a revisar el diff por su cuenta sin cargar el gate, y solo
  cargó la skill cuando repetí la frase con la palabra «main».
- [H] El mensaje de bloqueo es bueno pero largo: en una terminal estrecha ocupa
  toda la pantalla y tapa lo que estaba haciendo antes.
- [AR] Yo asumí que el verde de hacía diez minutos seguía valiendo. No lo
  comprobé hasta que el hook me paró. Fue el hook, no yo.

## 5. Triggers — lo que se escribió literalmente

| Frase literal del humano | Qué esperaba que cargara | Qué cargó |
|---|---|---|
| «ya terminé esto, revísalo» | `workstream-merge-gate` | nada |
| «intégrala a main» | `workstream-merge-gate` | `workstream-merge-gate` |

## 6. Graphify — ¿se usó el mapa?

**Instalación**

- [R] `graphify` instalado en este repo: **sí** (`graphify --version` → 0.9.5)
- [R] Hook `post-commit` instalado: **no**. `.git/hooks/post-commit` no existe
  en este laboratorio.
- [R] El `CLAUDE.md` del proyecto lleva: **la línea vieja** — *"For codebase
  questions, first run `graphify query`"*. La sustitución de `project-onboard`
  §7 nunca se aplicó aquí, porque el repo se creó a mano y no pasó por el
  onboarding.

**Uso**

- [R] ¿Se corrió `graphify query` antes del primer `grep`? **No.**
- [AR] Por qué no: hice `grep -rn "IVA"` de reflejo, en el primer minuto. La
  línea que el `CLAUDE.md` tenía —*"for codebase questions"*— no me sonó a que
  aplicara: yo no tenía una «pregunta sobre el codebase», tenía que encontrar
  una constante. **El disparador nuevo («antes de tu primer `grep`») sí me
  habría parado**, porque nombra el momento exacto en el que estaba.
- [H] No me di cuenta de que no lo había usado hasta que el agente lo escribió
  en este reporte.

**Calibración**

No aplica: no se corrió.

- [R] Tras el commit no se regeneró ningún snapshot (el hook no está instalado);
  no hay `codebase-map.md` curado en este repo, así que no había nada que
  proteger.

## 7. Fricciones menores

- [H] El helper hay que correrlo desde la raíz del repo; desde una subcarpeta
  falla sin decir por qué.
- [AR] No supe estimar cuánto iba a tardar la suite y no avisé antes de lanzarla.

## 8. Lo que esperaba y no existe

- [H] Algo que me dijera, antes de empezar, si la rama está lista o le falta
  algo — un «pre-check» en vez de descubrirlo en el paso 2.

## 9. Confirmación del humano

- [H] Leído y corregido por: ejemplo · 2026-08-07
- [H] Cambios que pedí sobre el borrador del agente: quitó la parte donde decía
  que «todo fue fluido»; no lo fue.
