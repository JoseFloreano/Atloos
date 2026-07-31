# Diseño de API de librería Python — checklist operativo

Revisar antes de publicar o refactorizar la superficie pública de un paquete.

## Estructura

- [ ] Todo lo que el usuario necesita se importa desde el nivel superior
      del paquete (`from .api import order` en `__init__.py`)
- [ ] Ningún import de usuario baja más de 2 niveles de submódulo
- [ ] El nombre de función no repite el nombre del módulo
      (`miquete.order`, no `miquete.order_miquete`)
- [ ] Se puede reorganizar la implementación interna sin tocar la firma
      pública

## Estado y configuración

- [ ] Cero variables mutables a nivel de módulo usadas como config global
- [ ] Todo default vive en la firma de la función, no en una constante
      importable y sobreescribible
- [ ] Si hay estado entre llamadas (conexiones, auth, cache), es una clase
      instanciable, no módulo-como-singleton

## Naming

- [ ] Funciones son verbos, clases son sustantivos
- [ ] Nombres tan cortos como se pueda sin perder claridad (el nombre del
      módulo ya da contexto — no hace falta repetirlo)
- [ ] Privado = un solo guion bajo (`_interno`); nunca doble guion bajo
      salvo que se necesite name mangling explícito

## Errores

- [ ] Existe una excepción base propia (`class Error(Exception)`)
- [ ] Las excepciones específicas heredan de esa base — permite
      `except paquete.Error` para capturar todo
- [ ] Se reusan excepciones de stdlib cuando el caso ya mapea 1:1
      (`ValueError`, `FileNotFoundError`, etc.) en vez de inventar una nueva
- [ ] Ningún error se traga silenciosamente ni se convierte en un valor de
      retorno ambiguo (ej. `None` para "no encontrado" Y para "error")

## Compatibilidad y versionado

- [ ] Los cambios nuevos se añaden como kwargs opcionales con default,
      nunca reordenando/quitando parámetros existentes
- [ ] Semver: mayor solo al reestructurar la API por completo; menor al
      añadir funcionalidad compatible; parche para fixes sin cambio de API
- [ ] Cambios incompatibles documentados en release notes, no solo en el
      changelog de git

## Tipos

- [ ] Toda la superficie pública tiene type hints
- [ ] Las clases que son sobre todo datos usan `@dataclass` (ver skill
      `python-conventions` para el árbol de decisión completo)
- [ ] Un type checker (`ty`/BasedPyright/Mypy) corre en CI sobre el paquete

## Ejemplo completo — jerarquía de excepciones y compatibilidad

```python
# miquete/__init__.py
from .api import order
from .exceptions import Error, NetworkError, APIError, OrderError

__all__ = ["order", "Error", "NetworkError", "APIError", "OrderError"]

# miquete/exceptions.py
class Error(Exception):
    """Base de todas las excepciones de esta librería."""

class NetworkError(Error):
    """Error de red de bajo nivel."""

class APIError(Error):
    """Error 5xx del servicio remoto."""

class OrderError(Error):
    """Error 4xx con detalle accionable para el caller."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")

# miquete/api.py
import requests
from .exceptions import NetworkError, APIError, OrderError

def order(
    items: list[str],
    *,
    timeout: float = 10,
    fish_type: str = "battered",  # añadido después, backward-compatible
) -> dict:
    """Coloca un pedido.

    Args:
        items: lista de productos a pedir.
        timeout: segundos antes de abortar la petición.
        fish_type: 'battered' o 'crumbed' (añadido en v1.1, opcional).
    """
    try:
        response = requests.post(_url, json={"items": items}, timeout=timeout)
    except requests.RequestException as e:
        raise NetworkError(f"Network error: {e}") from e

    if 500 <= response.status_code <= 599:
        raise APIError(f"API error {response.status_code}: {response.text}")
    if 400 <= response.status_code <= 499:
        data = response.json()
        raise OrderError(response.status_code, data["error_message"])

    return response.json()
```

Uso del lado del caller — el punto de la jerarquía de excepciones:

```python
try:
    miquete.order(["chips"])
except miquete.OrderError as e:
    print(f"Pedido rechazado: {e.message}")
except miquete.Error as e:
    print(f"Error inesperado: {e}")
```