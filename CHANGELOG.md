# Changelog

Formati ndjek [Keep a Changelog](https://keepachangelog.com/) dhe versionimi [SemVer](https://semver.org/).

## [1.1.0] — 2026-09-07

### Shtuar
- Dead Letter Queue për event-et që dështojnë procesimin (`messaging.py`).
- Cache Redis me degradim të sjellshëm për listën e produkteve (`inventory-service/app/cache.py`).
- Metrika Prometheus teknike dhe biznesi në `/metrics` (`order-service/app/metrics.py`).
- Audit log JSON append-only për veprimet e shkrimit (`order-service/app/audit.py`).
- API Gateway Nginx me rate limiting (`infra/nginx/nginx.conf`).
- Monitorim: Prometheus + Grafana në `docker-compose.yml`.
- CI me GitHub Actions: ruff + pytest + ndërtim i imazheve.
- Teste automatike për Order Service (8 teste, pa DB/broker real).
- Manifeste Kubernetes me HorizontalPodAutoscaler (`k8s/hpa.yaml`).
- Skema Avro të versionuara për tre event-et (`schemas/avro/`).
- Dokumentim: `docs/ARKITEKTURA.md` me diagramë komponentësh, ERD dhe rrjedhë event-esh.

### Ndryshuar
- `docker-compose.yml`: healthcheck për çdo shërbim dhe `depends_on: condition: service_healthy`.
- Kredencialet lexohen nga `.env` (shabllon: `.env.example`) në vend të vlerave të ngurta.

## [1.0.0] — 2026-08-20

### Shtuar
- Tre mikroshërbime: Order, Inventory, Notification.
- Komunikim pub/sub me exchange `topic` në RabbitMQ.
- Bazë e ndarë për shërbim (PostgreSQL 16).
- Kontroll qasjeje me API key dhe middleware i regjistrimit të kërkesave.
- Ngritje me një komandë përmes Docker Compose.
