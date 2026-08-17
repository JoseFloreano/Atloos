# EARS y el campo que fuerza el número

## EARS — las seis plantillas, verbatim

De Mavin et al., *"Easy Approach to Requirements Syntax"*, Rolls-Royce,
RE'09. Se escriben tal cual; el valor está en que la forma delata lo que falta.

```
Ubicuo:      The <system> shall <response>
Evento:      When <trigger>, the <system> shall <response>
Estado:      While <precondition>, the <system> shall <response>
Opcional:    Where <feature is included>, the <system> shall <response>
No deseado:  If <trigger>, then the <system> shall <response>
Complejo:    While <precondition>, When <trigger>, the <system> shall <response>
```

### Honestidad obligatoria sobre EARS

- **Adopción amplia**: Airbus, Bosch, Intel, NASA, Siemens.
- ⚠ **No hay estudio controlado publicado** que mida su reducción de
  ambigüedad. **Adoptado ≠ probado.** No lo presentes como demostrado.
- Da claridad **sintáctica**. **No garantiza completitud**: un conjunto de
  frases impecables puede omitir el caso que hunde el proyecto.
- **Se rompe con más de ~3 precondiciones** — lo dice su propio autor (RE'16).
  A partir de ahí, tabla de decisión o máquina de estados. Forzar la plantilla
  produce frases correctas e ilegibles.

## El campo que fuerza el número — tres tradiciones

Quédate con **una** y cita las otras. La recomendada aquí es Volere, por
liviana: se puede añadir a cualquier plantilla sin adoptar un método entero.

### Volere · `Fit Criterion` (Robertson) ⭐

Un campo por requisito que dice **cómo se comprobaría**.

> *"fácil de usar para niños de 11 años"*
> → *"el 80% de un panel de niños de 11 años completa [tareas] en [tiempo]"*

La regla operativa, y es la más útil de todo este fichero:

> **Si no puedes escribir el fit criterion, el requisito no está entendido.**
> No es que falte redactar: falta entender.

### Planguage (Gilb)

Más pesado y más potente: `Scale` (la unidad exacta) · `Meter` (el instrumento
con el que se mide) · `Goal` (lo que se busca) · `Fail` (lo inaceptable) ·
`Stretch` (lo ambicioso). La separación `Goal`/`Fail` es su mejor idea: dice
qué se negocia y qué no.

⚠ `gilb.com` ya **no aloja el material original**; cítalo por espejos y dilo.

### Quality Attribute Scenarios (SEI)

De *Software Architecture in Practice*, cap. 4. Seis partes: fuente, estímulo,
entorno, artefacto, respuesta y **response measure** — la sexta es la que
fuerza el número, igual que el fit criterion.

---

## El puente con `/goal` — el ejemplo trabajado

**Un requisito verificable y una condición de `/goal` son el mismo objeto a dos
altitudes.** EARS da la sintaxis; el fit criterion, el instrumento; y
`claude-code:goal-forge` pide exactamente eso más el comando que lo prueba.

⚠ Esa skill **solo existe en Claude Code**. En Cowork, este apartado se lee
como método —la bajada de altitud sigue siendo válida—, pero no hay `/goal` que
forjar: el documento termina en el traspaso del paso 6.

**RF-07 (EARS, evento):**
> When a user submits the login form with valid credentials, the system shall
> establish an authenticated session.

**Fit criterion (Volere):**
> El 100% de los casos de `tests/auth/test_login.py` pasa, y el p95 del
> endpoint es < 300 ms medido con k6 a 500 usuarios concurrentes.

**Condición de `/goal` (vía `claude-code:goal-forge`):**
> `pytest tests/auth -q` sale 0 con 0 fallos y escribe
> `.claude/verde-auth.json` con el sha del HEAD; sin tocar `src/billing/`;
> o para a los 15 turnos.

Lo que cambia entre las tres no es el contenido: es **quién lo lee**. La
primera la lee una persona, la segunda un QA, la tercera un evaluador que no
ejecuta herramientas — y por eso la tercera tiene que nombrar el comando y el
artefacto. Si al bajar de altitud te falta el comando, el fit criterion estaba
incompleto: no lo inventes en la condición, súbelo y arregla el requisito.
