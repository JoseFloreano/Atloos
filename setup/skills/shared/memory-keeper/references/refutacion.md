# Modo refutación — retirar un hecho que resultó falso

Detalle del `SKILL.md`, extraído en el sprint 10. **Guardar sabemos; retirar no
sabíamos**, y esa asimetría costó caro: el estado falso de Graphiti se propagó
de una nota a `_PROJECT.md` y hubo que corregirlo a mano en **tres sitios**.

## La regla: no lo borres — márcalo

Borrar deja el hueco **sin explicación**, y el mismo error vuelve por la misma
puerta seis semanas después. Una afirmación retirada dice qué se creía y por qué
dejó de creerse; una ausencia no dice nada.

## Los dos sitios, y son dos escrituras distintas

**1 · En su nota original**, **bajo** el hecho:

```markdown
> ❌ **REFUTADO (YYYY-MM-DD):** <qué resultó falso>.
> **Medido en:** <comando//archivo/nota que lo refutó>. Lo correcto es <…>.
```

**2 · Donde ese hecho se propagó** —`_PROJECT.md`, índices, `pendientes.md`—,
su línea va **tachada**, con enlace a la refutación:

```markdown
- ~~[[nota-del-hecho]] — lo que se creía~~ → refutado, ver [[nota-que-refuta]]
```

⚠ **Los dos, no uno.** Marcar el original y dejar las copias en pie es
exactamente cómo el hecho falso sobrevivió: cada arranque leía una copia sin
tachar y la servía como estado vigente.

## El requisito que impide abusar de esto

**Una medición, no una sospecha.** Decidir que un hecho es falso es juicio; esta
skill da el formato, **la evidencia la aporta quien midió**. Sin comando ni
artefacto que lo respalde, no se refuta: **se pregunta**.

Es la diferencia entre corregir la memoria y reescribirla a gusto.

## Con Graphiti disponible

Además, un `add_episode` que **nombre el hecho refutado** — no un episodio
suelto que nadie relaciona con el original. Un desmentido que no cita lo que
desmiente es un hecho nuevo más, y compite con el viejo en vez de retirarlo.

## Quién lo vigila

`cowork:vault-drift-audit` audita esto: **un hecho refutado cuyo original sigue
sin marcar en algún sitio es divergencia**, y sale como hallazgo.
