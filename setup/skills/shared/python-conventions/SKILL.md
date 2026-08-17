---
name: python-conventions
description: >
  Decide cómo modelar datos y clases en Python: cuándo usar clase simple,
  @dataclass, attrs o Pydantic; composición vs herencia; ABC vs
  typing.Protocol; naming y privacidad. Use when the user says "crea una
  clase para X", "cómo modelo esto en Python", "dataclass o Pydantic",
  "define una interfaz en Python", "refactoriza esta clase", or antes de
  escribir cualquier clase nueva en un proyecto Python. Para EXPONER esas
  clases como parte de la API pública de una librería usa python-api-design.
---

# Python Conventions

Modelar bien antes de escribir: la pregunta correcta no es "cómo escribo esta
clase" sino "qué herramienta es la correcta para este dato". Guía completa en
`references/python-classes-guide.md`.

## Pasos

1. **Decide la herramienta de datos** con el árbol de decisión:
   - Los datos **cruzan una frontera de confianza** (input de API, config,
     usuario) → **Pydantic** (validación + coerción + serialización).
   - Los datos son **internos, tipos ya confiables** → **`@dataclass`**
     (stdlib, cero dependencias). `frozen=True` para value objects
     inmutables; `slots=True` (3.10+) si el volumen de instancias importa.
   - Necesitas **validadores por campo, converters, o máximo rendimiento**
     en creación de objetos → **attrs**.
   - Hay **lógica de negocio real** (métodos con estado, no solo datos) →
     clase simple con `__init__` a mano.
2. **Composición antes que herencia**: hereda solo si hay una relación
   "ES-UN" genuina y compartes implementación real. Si solo necesitas que
   varias clases cumplan el mismo contrato, usa un Protocol o compón —
   nunca fuerces una jerarquía para reusar dos métodos.
3. **ABC vs Protocol**: `typing.Protocol` **por defecto** —un contrato que
   varias implementaciones cumplen, y lo único que sirve para clases de
   terceros—; `abc.ABC` solo si controlas la jerarquía **y** compartes
   implementación. Los dos, con sus matices, en
   `references/python-classes-guide.md`.
4. **Aplica SOLID con el matiz de Python**: Single Responsibility → separa
   datos, validación e I/O en clases distintas. Liskov → si una subclase
   cambia el comportamiento esperado del padre (ej. `Penguin.fly()`),
   la jerarquía está mal — separa por capacidad real, no por taxonomía.
   Dependency Inversion → depende de un Protocol, no de la clase concreta;
   así puedes inyectar un doble de prueba sin tocar el código de negocio.
5. **Naming y privacidad**: un solo guion bajo (`_private`) es privado por
   convención — suficiente. Nunca uses doble guion bajo (`__private`) salvo
   que quieras name mangling explícito; se confunde con métodos mágicos y
   rara vez vale la pena. Funciones = verbos, clases = sustantivos.
6. **Verifica antes de terminar**: ¿la clase que escribiste es la
   herramienta más simple que resuelve el problema? Si es un dataclass con
   un método añadido "por si acaso", probablemente sobra.

## Qué NO hacer

- No uses Pydantic para structs internos calientes (overhead de validación
  innecesario) ni dataclass plano para datos que vienen de fuera del
  sistema (sin validación, es una fuente de bugs silenciosos).
- No definas una ABC solo para tipar — si no compartes implementación,
  es un Protocol.
- No sobrecargues operadores (`__add__`, `__getitem__`) salvo que el tipo
  sea genuinamente numérico o indexable.

## Referencias

- `references/python-classes-guide.md` — tabla comparativa completa
  (dataclass/attrs/Pydantic con ejemplos), ejemplo de Protocol vs ABC,
  ejemplo de violación/corrección de Liskov.