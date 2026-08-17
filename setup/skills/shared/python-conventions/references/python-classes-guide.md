# Guía de clases en Python — referencia extendida

## Tabla de decisión: clase simple / dataclass / attrs / Pydantic

| Herramienta | Úsala cuando | Evítala cuando | Ejemplo mínimo |
|-------------|--------------|-----------------|-----------------|
| Clase simple | Lógica de negocio con estado mutable interno, métodos que hacen trabajo real | Es solo un contenedor de datos | `class Order: def __init__(self, items): self.items = items` |
| `@dataclass` | Datos internos, tipos confiables, cero dependencias | Datos externos sin validar | ver abajo |
| `attrs` | Validadores por campo, converters, máximo rendimiento en creación | dataclass ya alcanza | `@define class Point: x: int; y: int` |
| Pydantic | Datos que cruzan una frontera de confianza | Struct interno de solo lectura, hot path | `class UserIn(BaseModel): email: str` |

### Dataclass — patrones útiles

```python
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class Coordinates:
    """Value object inmutable — hasheable gratis, 30-40% menos memoria."""
    lat: float
    lon: float

@dataclass
class Order:
    items: list[str] = field(default_factory=list)  # nunca uses [] como default

    def total_items(self) -> int:
        return len(self.items)
```

`frozen=True` da `__hash__` automático (usable en sets/dict keys) y lanza
`FrozenInstanceError` si algo intenta mutar la instancia después de crearla.
`slots=True` (Python 3.10+) genera `__slots__`: reduce memoria y acelera el
acceso a atributos, a cambio de no poder añadir atributos dinámicos.

### attrs — cuándo aporta sobre dataclass

```python
from attrs import define, field, validators

@define
class Point:
    x: int = field(validator=validators.instance_of(int))
    y: int = field(validator=validators.instance_of(int))
```

attrs da validadores por campo, converters, y slots por defecto en todas las
versiones (dataclass solo desde 3.10). Es la opción cuando necesitas más
control que dataclass pero no quieres el overhead de validación de Pydantic.

### Pydantic — el borde de confianza

```python
from pydantic import BaseModel, EmailStr

class UserIn(BaseModel):
    """Frontera de confianza: input de API. Valida, coacciona, serializa."""
    email: EmailStr
    age: int
```

Pydantic v2 (núcleo Rust) es 5-50× más rápido que v1, pero sigue siendo más
lento que un dataclass plano por el trabajo de validación — resérvalo para
donde la validación es el punto (requests de API, config, datos de usuario).

## Protocol vs ABC — ejemplo lado a lado

```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

# ABC: fuerza herencia, comparte implementación
class Logger(ABC):
    @abstractmethod
    def log(self, message: str) -> None: ...

    def log_error(self, message: str) -> None:
        """Implementación compartida — ventaja real de ABC."""
        self.log(f"ERROR: {message}")

# Protocol: estructural, sin herencia, tipa clases que no controlas
@runtime_checkable
class SupportsLog(Protocol):
    def log(self, message: str) -> None: ...

class ThirdPartyLogger:
    """No hereda de nada — igual satisface SupportsLog."""
    def log(self, message: str) -> None:
        print(message)
```

Regla rápida: si necesitas compartir código entre implementaciones, ABC. Si
solo necesitas verificar que algo "tiene la forma correcta" (incluida una
clase que no puedes modificar), Protocol.

## Liskov — el error más común en jerarquías Python

```python
# MAL: fuerza una capacidad que no todas las subclases tienen
class Bird(ABC):
    @abstractmethod
    def fly(self): ...

class Penguin(Bird):
    def fly(self):
        raise NotImplementedError("Penguins can't fly")  # rompe LSP

# BIEN: separa por capacidad real
class Bird(ABC):
    @abstractmethod
    def move(self): ...

class FlyingBird(Bird):
    def move(self):
        return "Soaring through the skies"

class SwimmingBird(Bird):
    def move(self):
        return "Swimming through the waters"
```

Si una subclase necesita lanzar `NotImplementedError` en un método del padre,
la jerarquía está diseñada incorrectamente — es señal de separar por lo que
cada tipo realmente puede hacer, no por taxonomía biológica/de negocio.
## ABC vs Protocol para interfaces — el detalle del paso 3

Extraído del cuerpo en el sprint 10. La regla corta está allí; aquí está por qué.

**`abc.ABC` + `@abstractmethod`** — cuando controlas la jerarquía y quieres
**forzar el contrato en `__init__`**: una subclase que no llegue a **implementar** el método
**no se puede instanciar**, y el error salta al construir, no al llamar. Pide dos
condiciones a la vez: que la jerarquía sea tuya **y** que compartas
implementación entre subclases. Si solo se cumple una, no es tu caso.

**`typing.Protocol`** (+ `@runtime_checkable` si necesitas `isinstance`) — el
**por defecto**. Sirve para "definir un contrato que varias implementaciones
cumplen" sin obligarlas a heredar de nada, y **especialmente** si tipas clases de terceros que no controlas —
ahí es lo único que funciona: no puedes hacer que la clase de otro
herede de tu ABC, pero sí puedes describir la forma que ya tiene.

El sesgo por defecto hacia `Protocol` no es estético: una ABC es una dependencia
que viaja hacia arriba —quien implementa tiene que importar tu módulo—, mientras
que un Protocol se queda en el lado de quien consume.
