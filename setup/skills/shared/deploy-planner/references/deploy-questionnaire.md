# Cuestionario de Despliegue — Guía de entrevista

8 secciones. Para cada pregunta hay un **default sensato** para el stack
(Next.js / FastAPI / Flutter, dev individual, 2026) — proponerlo y dejar que
el usuario corrija es más rápido que preguntar en blanco. Los precios/tiers
cambian: validar contra la doc oficial del día antes de comprometerse.

## 1. Qué se despliega y dónde

- ¿Qué es exactamente? (frontend, API, ambos, app Flutter, worker/cron)
- ¿Tráfico esperado el primer mes? (¿10 usuarios o 10,000? — dimensiona todo lo demás)
- ¿Región/latencia importan? (¿usuarios en un país o globales?)
- ¿Algo con requisitos especiales? (websockets, jobs largos, GPU, archivos grandes)

**Defaults 2026:** Next.js → Vercel (hobby gratis). FastAPI → Railway (~$5-15/mes,
mejor DX) o Fly.io (pay-as-you-go, más regiones, requiere Docker) o Render
($7/servicio, precio predecible; ojo: free duerme a los 15 min). Flutter web →
hosting estático donde sea. Todo-en-VPS (Hetzner ~€5) solo si aceptas ops manual.
Patrón común: Vercel para el front + Railway/Fly para el back.

## 2. Secrets y configuración

- Inventario: ¿qué secrets existen? (API keys, DB URL, JWT secret, OAuth...)
- ¿Dónde vivirán en prod? (secrets manager de la plataforma — nunca en el repo)
- ¿Cómo se separan dev/staging/prod? (valores distintos por entorno, mismo nombre)
- ¿Quién más los conoce y cómo se rotan si se filtran?

**Gate:** correr `secrets-scan` sobre el repo ANTES del primer push a prod.
**Default:** variables de entorno de la plataforma + `.env.example` versionado
(nombres sin valores) — el mismo patrón del setup (auditoría A4).

## 3. Base de datos y migraciones

- ¿Qué DB y dónde? (¿managed de la plataforma, Supabase/Neon, propia?)
- ¿Cómo corren las migraciones en deploy? (¿automáticas en release, manuales, quién las dispara?)
- ¿Las migraciones son reversibles? ¿Probaste el rollback de la última?
- **Backups: ¿automáticos? ¿cada cuánto? ¿HICISTE una restauración de prueba?**
  (la lección A3 del setup: backup no probado = no existe)
- ¿Datos personales? → mínimo: saber qué guardas y poder borrarlo a petición

**Default:** Postgres managed (Neon/Supabase free tier para empezar) +
migraciones con la herramienta del ORM en paso explícito de release (no
auto-mágicas) + la skill `migration-auditor` para las riesgosas.

## 4. Dominio, TLS y borde

- ¿Dominio propio? ¿Dónde está el DNS?
- TLS: automático en toda plataforma seria (Let's Encrypt) — verificar redirect http→https
- ¿CDN/caché para estáticos? (Vercel/Netlify lo dan; en VPS, Cloudflare gratis)
- Headers de seguridad (los del checklist de `web-security-review` A05) y CORS
  restrictivo configurados

## 5. CI/CD y proceso de release

- ¿Qué dispara un deploy? (push a main, tag, botón manual — decidirlo, no heredarlo)
- ¿Qué corre ANTES de desplegar? (mínimo: tests + `dependency-audit` + build)
- ¿Staging/preview? (Vercel lo regala por PR; para APIs, un entorno staging barato
  o al menos deploy manual con smoke test)
- ¿Deploy con downtime o rolling? (para dev individual: rolling de la plataforma basta)

**Default:** GitHub Actions → deploy de la plataforma en push a main con tests
como gate + preview deployments en PRs si el proveedor los da.

## 6. Rollback y fallos

- **¿Cómo vuelves a la versión anterior y cuánto tarda?** (probarlo UNA vez
  antes del go-live; en Vercel/Railway/Render es un click a build anterior —
  saber DÓNDE está el click)
- ¿Qué pasa si la migración de DB falló a la mitad? (por eso: reversibles + backup pre-deploy)
- ¿Health check endpoint para que la plataforma reinicie/enrute? (`/healthz`)
- ¿Qué es "romper prod" para esta app y a quién le duele? (calibra cuánto invertir aquí)

## 7. Observabilidad mínima

- Logs: ¿dónde se leen los de prod? (los de la plataforma bastan al inicio — saber verlos)
- Errores: Sentry (free tier) o equivalente para excepciones con stack trace
- Uptime: un ping externo gratis (UptimeRobot o similar) al `/healthz` con alerta a tu correo
- ¿Alguna métrica de negocio que quieras ver semanalmente? (signups, jobs procesados)

**Anti-over-engineering:** para dev individual esto ES suficiente; Prometheus/
Grafana/tracing distribuido llegan cuando haya tráfico que lo justifique.

## 8. Costos (la sección que las checklists enterprise omiten)

- Presupuesto mensual objetivo: ¿$0, <$20, <$100?
- Suma estimada: hosting + DB + dominio (~$10-15/año) + email transaccional +
  APIs de LLM si la app las usa (→ `model-benchmark` para esa parte)
- **¿Qué pasa si se viraliza?** ¿La plataforma escala la factura sin límite?
  → poner alertas de billing/spend caps donde existan ANTES del go-live
- Revisión: costo real vs estimado al mes 1 (pendiente en el vault)

---

## Gates de go-live (todo verde o no se despliega)

- [ ] `secrets-scan` limpio + secrets solo en el manager de la plataforma
- [ ] `web-security-review` del código expuesto (y `authn-authz-review` si hay auth)
- [ ] `dependency-audit` sin críticas con fix disponible
- [ ] Backup de DB automático activo + UNA restauración probada
- [ ] Rollback probado una vez (sabes el click/comando y cuánto tarda)
- [ ] `/healthz` + uptime ping + Sentry (o equivalentes) activos
- [ ] Alerta/límite de billing configurado
- [ ] `deploy-plan.md` en el vault + ADR de la plataforma elegida
