---
name: python-api-design
description: >
  Diseña la superficie pública de una librería, módulo o paquete Python que
  otro código va a importar: estructura de __init__.py, naming, manejo de
  errores, compatibilidad hacia atrás y type hints. Use when the user says
  "diseña esta librería", "cómo estructuro este paquete", "qué expongo en
  __init__.py", "esta API de Python es difícil de usar", "cómo versiono este
  paquete", or antes de publicar/refactorizar la superficie pública de un
  módulo Python. Para diseñar endpoints REST/HTTP usa api-design; esta skill
  es para APIs que se consumen con `import`, no con HTTP.
---

# Python API Design

Una API de librería es una promesa pública: cambiarla después cuesta mucho
más que diseñarla bien la primera vez. Principios destilados de la práctica
de librerías Python de referencia (Requests, stdlib bien y mal diseñada).

## Pasos

1. **Estructura plana desde `__init__.py`**: expón la API completa ahí
   (`from .api import order`) para que el usuario haga `import miquete` sin
   necesitar saber cómo está dividido internamente el paquete. La
   estructura de archivos es un detalle de implementación — puedes
   reorganizarla sin romper a nadie mientras el `__init__.py` se mantenga.
2. **Diseña para `import lib` sobre `from lib import Thing`**: el código de
   uso debe leerse `miquete.order(...)`, no `order(...)` a secas — el
   nombre del módulo da contexto sin rastrear el import. No dupliques el
   nombre del módulo en la función (`miquete.order`, nunca
   `miquete.order_miquete`).
3. **Cero configuración ni estado global mutable**: nada como
   `DEFAULT_TIMEOUT = 10` a nivel de módulo — cualquier importador lo puede
   pisar y afecta a todos. Usa defaults en la firma de la función
   (`def order(timeout=10)`); si hace falta estado entre llamadas (conexión
   reusada, auth), usa una clase (`Session`), nunca variables de módulo.
4. **Jerarquía de excepciones propia**: define una base
   (`class Error(Exception)`) y subclases específicas por familia de fallo.
   Permite `except miquete.Error` para capturar todo y subclases específicas
   cuando el caller necesita detalle. Reusa excepciones de stdlib
   (`ValueError`, `FileNotFoundError`) cuando el caso ya mapea 1:1.
5. **Compatibilidad hacia atrás con kwargs**: añade funcionalidad con
   argumentos con nombre y defaults — nunca reordenes ni elimines
   parámetros existentes sin subir la versión mayor. Solo rompe
   compatibilidad al reestructurar la API por completo, no función por
   función.
6. **Type hints en toda la superficie pública**: documentan el contrato,
   habilitan autocompletado en el IDE del usuario y atrapan errores antes
   de tiempo de ejecución. Es la parte donde el esfuerzo de tipar
   definitivamente vale la pena, aunque el resto del código interno sea más
   laxo.
7. **Verifica antes de publicar**: ¿un usuario nuevo puede adivinar cómo se
   usa esto sin leer el código fuente? ¿El nombre más corto y claro posible
   ya está tomado por algo interno? ¿Hay alguna clase que sobrecarga
   operadores sin ser genuinamente numérica/indexable?

## Qué NO hacer

- No anides módulos más de 2 niveles (`pkg.sub.subsub.Thing` es una señal de
  alerta, no una convención) — aplana con imports en `__init__.py`.
- No mezcles el modelo de dominio interno con el modelo expuesto al usuario
  — la superficie pública puede ser un dataclass simple aunque internamente
  uses algo más complejo.
- No dejes que un `@property` haga I/O o lance excepciones — debe verse
  barato y serlo.

## Referencias

- `references/python-api-design-checklist.md` — checklist operativo +
  ejemplo completo de jerarquía de excepciones y versionado.