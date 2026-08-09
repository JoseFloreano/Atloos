---
name: api-design
description: >
  Diseña APIs REST (y valora GraphQL cuando aplica) con contrato primero:
  naming de recursos, métodos e idempotencia, errores, paginación, versioning
  y OpenAPI. Use when the user says "diseña la API", "los endpoints para X",
  "¿cómo estructuro esta API?", "REST o GraphQL", "define el contrato", or
  before implementing any new API surface. Cubre FastAPI, Express y Next.js
  API routes. Para EVOLUCIONAR una API existente sin romper clientes usa
  api-evolution.
---

# API Design

Contrato primero, implementación después: una API es una promesa pública —
cambiarla cuesta 10× más que diseñarla bien. Checklist completo en
`references/api-design-checklist.md`.

## Pasos

1. **Modela recursos, no acciones**: sustantivos en plural (`/invoices`,
   `/invoices/{id}/payments`), máximo 2 niveles de anidado; las acciones que
   no mapean a CRUD van como sub-recurso (`POST /invoices/{id}/send`), no
   como verbo en la URL.
2. **Métodos con su semántica**: GET seguro y cacheable; PUT/DELETE
   idempotentes; POST no — si el cliente puede reintentar (pagos, creación),
   soporta `Idempotency-Key`. PATCH para parcial.
3. **Contrato de errores único** para toda la API (formato problem+json:
   `type/title/status/detail` + código propio). Status correctos: 400 vs 401
   vs 403 vs 404 vs 409 vs 422 vs 429 — nunca 200 con `{"error": ...}`.
4. **Paginación desde el día uno** en toda colección (cursor para feeds/datos
   vivos, offset solo para listas chicas y estables) + filtrado/orden con
   parámetros consistentes (`?sort=-created_at`).
5. **Versioning decidido ANTES del primer cliente**: por defecto `/v1` en la
   ruta; los cambios aditivos (campos nuevos opcionales) no versionan, los
   breaking sí — la política completa vive en `api-evolution`.
6. **Escribe el OpenAPI** (o el schema GraphQL) como fuente de verdad ANTES de
   implementar: en FastAPI sale casi gratis de los modelos Pydantic; en
   Express/Next mantén `openapi.yaml` a mano o con zod-to-openapi. Guárdalo
   versionado — es el insumo de `api-evolution` para detectar breaking changes.
7. **Revisa contra el checklist** de references (auth en cada endpoint —
   cruzar con `authn-authz-review` —, rate limiting, CORS, consistencia de
   naming) y registra las decisiones no obvias con `adr-writer`.

## GraphQL: cuándo sí

Clientes múltiples con necesidades de datos muy distintas, o grafos de datos
profundos. Si es un backend para TU frontend: REST simple gana en costo de
mantenimiento. La decisión REST vs GraphQL es un ADR, no un default.

## Referencias

- `references/api-design-checklist.md` — el checklist operativo completo.
- Para profundizar (leídas en la investigación, adoptables aparte): Google AIP
  empaquetados (ekkx/google-aip-skills — sin licencia declarada, solo lectura),
  "api-design-principles" de wshobson y "api-design" de ECC (trabajo ajeno
  citado, no skills de este catálogo).
