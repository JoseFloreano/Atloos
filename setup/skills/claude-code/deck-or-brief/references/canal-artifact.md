# El canal `Artifact` — las cinco restricciones y el esqueleto que las cumple

Son **requisitos conocidos de antemano**, no descubrimientos. Descubrirlos
fallando cuesta el documento entero, porque las tres primeras no fallan con un
error legible: fallan con una página en blanco.

1. **Un solo fichero.** CSS y JS **en línea**; imágenes como `data:` URL.
2. **Sin CDN y sin fuentes remotas.** La CSP bloquea cualquier petición a otro
   host: scripts, hojas de estilo, tipografías, imágenes remotas, `fetch`.
   **Si no está en el fichero, no existe.**
3. **Nada de `localStorage` ni `sessionStorage`** — no están soportados y
   **rompen el artefacto**. El estado (pantalla actual, tema elegido) vive en
   **variables de JavaScript**, y se pierde al recargar: eso está bien para un
   mazo y hay que asumirlo, no sortearlo.
4. **Tema claro y oscuro.** Lo decide el contenedor, no tú: hay tres estados
   —`data-theme="light"`, `data-theme="dark"` y el de sistema, que no marca
   nada—. Define la paleta completa en `:root` y **redefine solo los tokens** en
   los dos bloques oscuros. Y da a `body` un fondo explícito: sin él, la página
   hereda el del contenedor.
5. **Que imprima.** `@media print` y `page-break-inside: avoid`. **Un mazo que
   no se puede mandar en PDF acaba rehecho en PowerPoint**, y entonces esta
   skill no sirvió para nada.

⚠ Y una que muerde al final: la descarga que inicia la propia página está
bloqueada para quien la ve. **No ofrezcas el PDF con un enlace de descarga** —
usa la impresión del navegador, que es el punto 5.

## Esqueleto

Cumple las cinco de salida. El contenido va donde dice; lo demás se toca poco.

```html
<title>Nombre corto y distintivo</title>
<style>
  :root{                       /* paleta clara COMPLETA: nunca definas un color
                                  solo dentro de un @media */
    --fondo:#fff; --texto:#141414; --tenue:#5b5b5b;
    --linea:#e2e2e2; --acento:#1f5fd6;
  }
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){        /* el de sistema */
      --fondo:#111; --texto:#f2f2f2; --tenue:#a8a8a8;
      --linea:#2c2c2c; --acento:#7aa7ff;
    }
  }
  :root[data-theme="dark"]{                 /* y el elegido a mano */
    --fondo:#111; --texto:#f2f2f2; --tenue:#a8a8a8;
    --linea:#2c2c2c; --acento:#7aa7ff;
  }
  body{background:var(--fondo); color:var(--texto); margin:0;
       font:16px/1.6 system-ui, sans-serif;}   /* fuentes del sistema: no viajan
                                                  por la red */
  .pantalla{max-width:60rem; margin:0 auto; padding:3rem 1.5rem;
            min-height:100vh; box-sizing:border-box;}
  .numero{font-size:clamp(2.5rem,8vw,5rem); line-height:1; font-weight:700;}
  .fuente{color:var(--tenue); font-size:.85rem;}   /* de dónde salió el número */
  table{width:100%; border-collapse:collapse;}
  .ancho{overflow-x:auto;}      /* lo ancho scrollea DENTRO, no la página */
  @media print{
    .pantalla{min-height:0; page-break-after:always; padding:1.5rem 0;}
    .pantalla, table, figure{page-break-inside:avoid;}
    :root{--fondo:#fff; --texto:#000; --linea:#999;}
  }
</style>

<section class="pantalla">
  <h1>El titular ES la conclusión, no el tema</h1>
  <p class="numero">38 %</p>
  <p class="fuente">Cortes sin reasignar · export de cobranza, jun–ago 2026</p>
</section>

<script>
  // El estado vive aquí. Nada de localStorage: rompe el artefacto.
  let pantalla = 0;
</script>
```

## Antes de entregar

- `shared:web-design-guidelines` sobre el fichero — accesibilidad, foco,
  estados. Es su revisor natural y no es opcional.
- Imprime a PDF de verdad y míralo. El `@media print` que nadie ejecutó no
  cuenta como cumplido.
- Míralo en los dos temas, incluido el de sistema (el que no marca nada).
- **El pedido, literal, en la última pantalla.**
