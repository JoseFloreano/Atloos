# Skills de Python: Investigación y Selección
## Clases, desarrollo general y diseño de APIs de librería

> **Fecha:** Julio 2026
> **Contexto:** Continúa la subserie `skills/` (docs 10, 11, 13, 15). El doc 15 ya cubrió diseño de APIs **REST/HTTP** (`api-design`, `shared/`); este doc cubre lo que faltaba: cómo Claude debe escribir clases y código Python idiomático en general, y cómo diseñar la **API de una librería o módulo Python** (superficie de import, naming, excepciones) — un problema distinto y complementario al de REST.
> **Método:** Investigación web sobre fuentes primarias (Real Python, PEPs, artículos de autores con nombre propio, plugins oficiales de terceros) + lectura del sistema de skills existente (`setup/skills/README.md`, `_template/SKILL.md`, `skill-forge`). Protocolo de auditoría del `skills/10` §2 vigente para toda adopción externa.
> **Resultado:** 2 skills propias creadas (§5) + 1 plugin externo recomendado para adoptar tal cual (§4).
> **Stacks objetivo:** el mismo de siempre — este doc añade Python al catálogo ya cubierto para React/Flutter/C++.

---

## 1. Resumen ejecutivo

| Categoría | Mejor material externo | Veredicto | Nuestra pieza |
|-----------|------------------------|-----------|----------------|
| Clases y modelado de datos | Múltiples fuentes coinciden en un árbol de decisión claro (dataclass/attrs/Pydantic/clase simple) + SOLID adaptado a duck typing (Real Python) | Destilar, no instalar — es criterio, no tooling | ⭐ `python-conventions` (shared) |
| Desarrollo general (toolchain) | Plugin oficial **`astral@astral-sh`** (uv + Ruff + ty) | **Adoptar tal cual** — es del mismo equipo que las herramientas | Nada propio — sería duplicar |
| Diseño de APIs de librería Python | Ben Hoyt, *"Designing Pythonic library APIs"* — la mejor síntesis encontrada, sin equivalente empaquetado como skill | Destilar — no existe como skill en ningún repo verificado | ⭐ `python-api-design` (shared) |
| Testing Python | Ya cubierto en `skills/11` §2.4 (`honnibal/claude-skills`: hypothesis, mutation-testing) | No duplicar | — |

**El hallazgo que gobierna esta investigación:** a diferencia de REST (doc 15, donde el consenso ya viene empaquetado en varias skills de terceros), el diseño de *clases* y de *APIs de librería Python* es terreno de artículos y guías de estilo, no de skills ya escritas. Nadie empaquetó "cuándo uso `@dataclass` vs `attrs` vs Pydantic" ni "cómo estructurar el `__init__.py` de tu paquete" como SKILL.md — dos huecos reales que llenamos con piezas propias cortas.

---

## 2. Clases y modelado de datos — lo encontrado

### 2.1 El árbol de decisión (converge en todas las fuentes consultadas)

| Herramienta | Úsala cuando | Evítala cuando |
|-------------|--------------|-----------------|
| Clase simple (`__init__` a mano) | Necesitas lógica de negocio, no solo datos; comportamiento rico con estado mutable interno | Es solo un contenedor de datos — hay boilerplate gratis con dataclass |
| `@dataclass` (stdlib) | Datos internos, tipos ya confiables, cero dependencias — modelos de dominio, DTOs internos, value objects | Los datos cruzan una frontera de confianza (input de usuario, API, config) y necesitas validación |
| `attrs` | Necesitas validadores por campo, converters, slots antes de 3.10, jerarquías de clases complejas — mejor rendimiento que Pydantic en creación de objetos de alta frecuencia | El equipo no lo conoce y dataclass ya alcanza |
| `Pydantic` | Los datos vienen de fuera (input de API, archivos de config, datos de usuario) y necesitas validación + coerción + serialización + JSON Schema | Es una estructura interna de solo lectura — el overhead de validación no se justifica |

Detalles operativos que vale la pena fijar como convención propia:

- `@dataclass(frozen=True)` para value objects inmutables (config, coordenadas, IDs compuestos) — quedan hasheables gratis.
- `@dataclass(slots=True)` (Python 3.10+) cuando el volumen de instancias importa: reduce memoria 30-40% y acelera el acceso a atributos, a cambio de no poder añadir atributos dinámicos.
- Pydantic v2 (núcleo en Rust) es 5-50× más rápido que v1 pero sigue siendo más lento que un dataclass plano por el trabajo de validación — la regla no cambia: Pydantic es para el borde de confianza, no para structs internos calientes.

### 2.2 Composición sobre herencia — y cuándo sí heredar

El consenso (Real Python, guía SOLID en Python, y la nota práctica de ingeniería de datos) es el mismo que en cualquier lenguaje, con el matiz de duck typing: en Python, el Open/Closed Principle se logra normalmente con **composición y protocolos**, no con jerarquías de herencia profundas — en vez de modificar una clase existente para añadir comportamiento, se componen clases nuevas que delegan, o se definen interfaces basadas en protocolo que las clases nuevas implementan sin tocar la jerarquía. La duplicación puntual es más barata que una capa de abstracción mal ajustada.

Regla operativa: heredar solo cuando hay una relación "ES-UN" genuina y se comparte implementación real (no solo firma); en cualquier otro caso, componer o usar un Protocol.

### 2.3 ABCs vs `typing.Protocol` — la distinción que Claude debe aplicar bien

Python ofrece dos formas de modelar interfaces, y confundirlas es el error más común en código generado:

- **`abc.ABC` + `@abstractmethod`**: interfaz por herencia. Fuerza el contrato en tiempo de instanciación (no puedes instanciar una subclase que no implementó el método abstracto) y permite compartir implementación entre subclases. Úsalo cuando tienes control de la jerarquía y quieres reforzar el contrato en runtime.
- **`typing.Protocol`** (PEP 544): interfaz estructural — subtipado estático, equivalente formal del duck typing. Cualquier clase que tenga los métodos requeridos satisface el Protocol **sin heredar de él ni registrarse**. Úsalo para tipar clases de terceros que no controlas, o cuando quieres mantener las clases desacopladas; añade `@runtime_checkable` si además necesitas `isinstance()` en runtime.

Regla operativa: Protocol por defecto para "definir un contrato que varias implementaciones cumplen"; ABC solo cuando además hay lógica compartida real que vale la pena heredar.

### 2.4 SOLID en Python — con las adaptaciones que importan

Los 5 principios trasladan bien, con dos matices propios del lenguaje: el Liskov Substitution Principle se viola con frecuencia cuando una subclase sobreescribe un método cambiando el comportamiento esperado por el padre (el clásico ejemplo Bird/Penguin — resuelto separando `FlyingBird`/`SwimmingBird` en vez de forzar `fly()` en todas las aves); y el Dependency Inversion Principle en Python casi siempre se implementa con un Protocol como abstracción, no con una ABC pesada — el servicio depende de la interfaz, no de la implementación concreta, lo que permite inyectar una implementación de prueba sin tocar el código de negocio.

### 2.5 Naming y privacidad — el detalle que Claude sí necesita fijado

- Un solo guion bajo (`_private`) es privacidad por convención — suficiente, y es lo que hay que usar por defecto.
- Doble guion bajo (`__extra_private`) activa *name mangling*, genera más confusión que protección (se confunde visualmente con los métodos mágicos `__init__`, `__eq__`, etc.) y rara vez vale la pena.
- Funciones = verbos, clases = sustantivos, como regla general — sin obsesionarse cuando la palabra es ambigua en inglés (naming completo en doc 03 de `python-api-design`, §3).

---

## 3. Desarrollo general — toolchain y estructura de proyecto

### 3.1 El plugin oficial de Astral ya resuelve esto

El equipo que mantiene **uv** y **Ruff** (Astral) publica un plugin oficial de Claude Code que empaqueta exactamente lo que un proyecto Python moderno necesita: `/astral:uv`, `/astral:ruff` y `/astral:ty` (su nuevo type checker en Rust, 10-60× más rápido que Mypy/Pyright aunque en beta a mediados de 2026 — para tipado estricto de producción, `BasedPyright` sigue siendo la opción madura), más un language server de `ty` que transmite diagnósticos de tipos directamente a la conversación. Instalación:

```
/plugin marketplace add astral-sh/claude-code-plugins
/plugin install astral@astral-sh
```

No tiene sentido escribir una skill propia de "cómo usar uv/ruff" — sería duplicar trabajo del propio fabricante de la herramienta, exactamente el mismo criterio que ya aplicamos al descartar duplicados de Superpowers en el `skills/11`.

### 3.2 Estructura de proyecto recomendada

El patrón que converge en las fuentes 2026: `uv init <proyecto> --package` genera un layout `src/<paquete>/` instalable (en vez de un `main.py` suelto), con `tests/` separado que importa el paquete por nombre — la estructura correcta para cualquier cosa más allá de un script de un archivo. Complementa directamente al §3.1 de `python-api-design` (la superficie pública vive en `__init__.py`, la estructura interna es un detalle de implementación).

### 3.3 Lo que NO se repite aquí

- **Testing** (Hypothesis, mutation testing, pytest): ya está en el `skills/11` §2.4 — `honnibal/claude-skills`.
- **Hooks de enforcement** (auto-lint post-escritura, bloquear `pip`/`python` suelto a favor de `uv run`): el patrón ya está documentado en `setup/hooks/README.md` y en el doc de arquitectura 05 §6 — aplica el mismo principio: la skill dice qué hacer, el hook lo garantiza. Un hook `PostToolUse` típico para Python:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit|MultiEdit",
      "hooks": [{
        "type": "command",
        "command": "echo \"$CLAUDE_TOOL_INPUT_FILE_PATH\" | grep -q '\\.py$' && uv run ruff format \"$CLAUDE_TOOL_INPUT_FILE_PATH\" 2>/dev/null || true"
      }]
    }]
  }
}
```

---

## 4. Diseño de APIs de librería Python — lo encontrado

Este es distinto del `api-design` REST del doc 15: aquí la "API" es la superficie que otro **código Python** importa (`import fishnchips; fishnchips.order(...)`), no un endpoint HTTP. La mejor síntesis encontrada — sin equivalente como skill en ningún repo auditado — es el artículo de Ben Hoyt (autor con trayectoria en la comunidad Python, ex-mantenedor de bibliotecas de infraestructura), que destila principios reutilizados por Requests y otras librerías de referencia:

- **Estructura plana**: exponer la API completa desde `__init__.py` (`from .api import order`) para que el usuario haga `import fishnchips` sin necesitar saber cómo está dividido internamente el paquete. La estructura de archivos es un detalle de implementación, no parte del contrato.
- **`import lib` mejor que `from lib import Thing`**: diseñar para que el código de uso se lea `fishnchips.order(...)`, no `order(...)` a secas — el nombre del módulo da contexto sin tener que rastrear el import.
- **Sin configuración ni estado global**: nunca una constante mutable a nivel de módulo (`DEFAULT_TIMEOUT = 10`) que cualquier importador pueda pisar; usar defaults en la firma de la función, y si hace falta estado entre llamadas, una clase (`Session`) en vez de variables de módulo.
- **Nombres cortos pero claros**: el nombre del módulo ya da contexto — `requests.get()`, no `requests.send_get_request_and_receive_response()`.
- **Jerarquía de excepciones propia**: una clase base (`class Error(Exception)`) y subclases específicas para cada familia de fallo — permite `except fishnchips.Error` para capturar todo, y subclases específicas cuando el caller necesita detalle. Reusar excepciones de stdlib (`ValueError`, `FileNotFoundError`) cuando el caso ya mapea 1:1 a una de ellas.
- **Compatibilidad hacia atrás vía kwargs**: los argumentos con nombre y el tipado dinámico de Python permiten añadir funcionalidad (nuevos parámetros opcionales) sin romper llamadas existentes — la razón por la que semver debe subir la versión mayor solo al reestructurar la API por completo, no en cada función nueva.
- **Type hints en la API pública, siempre**: documentan el contrato, habilitan mejor autocompletado/IDE y atrapan errores antes de ejecutar — el costo de escribirlos vale la pena específicamente en la superficie pública, aunque sea tedioso en firmas muy dinámicas.
- **`@dataclass` para clases que son sobre todo datos** — la recomendación conecta directo con §2.1 de este doc.
- **Comedimiento con el "poder" de Python**: sobrecargar operadores, magia en `__getattr__`, DSLs propios — todo eso existe, pero solo se justifica cuando el tipo que se está modelando genuinamente lo necesita (un tipo numérico, una colección indexable). Getters/setters de propiedad deben ser baratos — nunca I/O ni excepciones dentro de un `@property`.

---

## 5. Las 2 skills creadas

| Skill | Carpeta | Núcleo |
|-------|---------|--------|
| `python-conventions` | `shared/` | Árbol de decisión clase simple / dataclass / attrs / Pydantic; composición sobre herencia; ABC vs Protocol; SOLID adaptado; naming y privacidad |
| `python-api-design` | `shared/` | Estructura plana del paquete, sin estado/config global, jerarquía de excepciones propia, compat hacia atrás con kwargs, type hints en la superficie pública |

Ambas van a `shared/` porque son pura metodología — no dependen de ningún MCP ni toolchain local, y sirven igual en Claude Code y Cowork (revisar un diseño de librería en un documento de Cowork es un caso de uso legítimo).

Cadena de uso: `python-conventions` (cómo modelar los datos y las clases) → `python-api-design` (cómo exponerlas al mundo) → astral plugin (`/astral:ruff`, `/astral:ty`) para el toolchain → `adr-writer` si la decisión de diseño (p. ej. "usamos attrs, no Pydantic, para el dominio interno") merece quedar registrada.

---

## 6. Fuentes primarias

| Categoría | Fuentes |
|-----------|---------|
| Dataclasses / attrs / Pydantic | [Real Python — Data Classes Guide](https://realpython.com/python-data-classes/) · [Python Dataclasses: The Complete Guide 2026](https://devtoolbox.dedyn.io/blog/python-dataclasses-guide) · [Dataclasses vs Pydantic vs attrs](https://www.iamraghuveer.com/posts/python-dataclasses-pydantic-attrs/) · [Why I use attrs instead of pydantic](https://threeofwands.com/why-i-use-attrs-instead-of-pydantic/) · [Python Data Class Libraries comparison (Pi Stack)](https://www.pistack.xyz/posts/2026-07-03-python-data-class-libraries-dataclasses-attrs-pydantic-cattrs/) |
| Composición, SOLID, ABC/Protocol | [Deep Engineering — Steven Lott on OOP Design in Python](https://deepengineering.net/p/deep-engineering-38-steven-lott-on) · [Real Python — SOLID Principles in Python](https://realpython.com/solid-principles-python/) · [SOLID in Python: Complete Guide](https://universopython.com/en/blog/solid-python-principles) · [Real Python — Implementing Interfaces: ABCs and Protocols](https://realpython.com/python-interface/) · [typing docs — Protocols and structural subtyping](https://typing.python.org/en/latest/reference/protocols.html) |
| Diseño de API de librería Python | ⭐ [Ben Hoyt — Designing Pythonic library APIs](https://benhoyt.com/writings/python-api-design/) (fuente principal de §4) |
| Toolchain / desarrollo general | [jlevy/simple-modern-uv](https://github.com/jlevy/simple-modern-uv) (template + skill de agente) · [pydevtools — How to use Python skills with Claude Code](https://pydevtools.com/handbook/how-to/how-to-use-python-skills-with-claude-code/) · [pydevtools — Set up a Python project for Claude Code](https://pydevtools.com/handbook/tutorial/set-up-a-python-project-for-claude-code/) · [pydevtools — Configure Ruff with Claude Code](https://pydevtools.com/handbook/how-to/how-to-configure-ruff-with-claude-code/) |

**No verificable:** cobertura exacta de `ty` sobre Pydantic/Django a la fecha de lectura (declarada por el propio proyecto como incompleta, sujeta a cambio); si el plugin `astral@astral-sh` recibe actualizaciones automáticas o requiere reinstalación manual — validar en la primera adopción.

---

*Doc 16, subserie skills/. Las 2 skills están en `setup/skills/shared/` — activar con el flujo estándar (copiar → `sync-skills` sin `-NoCoworkBuild` → re-subir `dev-skills.zip` → probar triggers). El plugin astral se instala aparte con los dos comandos de §3.1 — no pasa por `claude-skills/`.*