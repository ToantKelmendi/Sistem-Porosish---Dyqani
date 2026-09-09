# Dyqani Teknologjik — Sistem Procesimi Porosish

Sistem i procesimit të porosive i ndarë në tre mikroshërbime të pavarura që
komunikojnë vetëm përmes ngjarjeve (event-eve) mbi RabbitMQ. Projekt individual
për lëndën **Sistemet e Procesimit të Dhënave Dizajnuese**.

**Autor:** Toant Kelmendi · **Mësimdhënës:** prof. Dr.sc. Liridon Hoti · **Version:** 1.1.0

---

## Përmbajtja

- [Problemi dhe zgjidhja](#problemi-dhe-zgjidhja)
- [Arkitektura](#arkitektura)
- [Ngritja e sistemit](#ngritja-e-sistemit)
- [API-t](#api-t)
- [Provë e plotë e rrjedhës](#provë-e-plotë-e-rrjedhës)
- [Siguria](#siguria)
- [Testet](#testet)
- [Monitorimi](#monitorimi)
- [Struktura e projektit](#struktura-e-projektit)
- [Ndërfaqja në shfletues](#ndërfaqja-në-shfletues)
- [Dokumentet](#dokumentet)

---

## Problemi dhe zgjidhja

Kur një klient bën porosi, tri gjëra duhen bërë: të ruhet porosia, të rezervohet
stoku, të njoftohet klienti. Nëse të tria ndodhin brenda së njëjtës kërkesë HTTP,
klienti pret sa më e ngadalta prej tyre, dhe një defekt te stoku ndalon pranimin
e porosive.

Zgjidhja: **ndarje sipas domenit + komunikim asinkron**. Order Service e ruan
porosinë, publikon `order.created` dhe përgjigjet menjëherë me 201. Inventory
Service dhe Notification Service reagojnë kur të munden. Asnjë shërbim nuk e
thërret tjetrin drejtpërdrejt.

## Arkitektura

```
Klienti --HTTP + X-API-Key--> Order Service :8001 --order.created--> orders_exchange (topic)
                                     |                                      |
                                 orders_db                 +----------------+----------------+
                                                           |                                 |
                                              Inventory Service :8002            Notification Service :8003
                                              bind: order.created                bind: order.#
                                              inventory_db + Redis               pa bazë të dhënash
                                              publikon: order.stock_reserved
                                                         order.stock_failed
```

| Shërbimi | Porti | Baza | Roli |
| --- | --- | --- | --- |
| Order Service | 8001 | orders_db | Pranon porositë, publikon ngjarje |
| Inventory Service | 8002 | inventory_db | Rezervon stokun, menaxhon produktet |
| Notification Service | 8003 | — | Njofton klientin për çdo ndryshim |

Diagramet e plota (komponentësh, ERD, sekuencë) janë në
[`docs/ARKITEKTURA.md`](docs/ARKITEKTURA.md).

### Ngjarjet e domenit

| Ngjarja | Prodhuesi | Ngarkesa |
| --- | --- | --- |
| `order.created` | Order Service | `{ order_id, customer_email, items[] }` |
| `order.stock_reserved` | Inventory Service | `{ order_id }` |
| `order.stock_failed` | Inventory Service | `{ order_id }` |

Skemat e versionuara: [`schemas/avro/`](schemas/avro).

## Ngritja e sistemit

**Parakushtet:** Docker dhe Docker Compose.

```bash
# 1. Konfigurimi
cp .env.example .env
# plotëso fjalëkalimet dhe gjenero API_KEY:
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Ngritja — një komandë ngre gjithçka
docker compose up --build

# 3. Verifikimi
docker compose ps
curl http://localhost:8001/health
```

Skema e bazave krijohet vetë në startup. Shërbimet presin derisa bazat dhe
brokeri të jenë `healthy`.

**Ndalja:** `docker compose down` (me `-v` fshihen edhe të dhënat).

## API-t

Dokumentacioni interaktiv gjenerohet vetë:

| Shërbimi | Swagger UI |
| --- | --- |
| Order Service | http://localhost:8001/docs |
| Inventory Service | http://localhost:8002/docs |
| Notification Service | http://localhost:8003/docs |

| Metoda | Rruga | Mbrojtur | Përshkrimi |
| --- | --- | --- | --- |
| GET | `:8001/health` | jo | Gjendja e shërbimit |
| GET | `:8001/metrics` | jo | Metrika Prometheus |
| POST | `:8001/orders` | po | Krijon porosi, publikon `order.created` |
| GET | `:8001/orders` | po | Lista e porosive |
| GET | `:8001/orders/{id}` | po | Një porosi e vetme |
| POST | `:8002/products` | po | Regjistron produkt |
| GET | `:8002/products` | po | Lista e produkteve (me cache) |
| GET | `:8002/health` | jo | Gjendja e shërbimit |
| GET | `:8003/health` | jo | Gjendja e shërbimit |

## Provë e plotë e rrjedhës

```bash
export API_KEY=$(grep '^API_KEY=' .env | cut -d= -f2)

# 1. Regjistro një produkt
curl -X POST "http://localhost:8002/products?name=Laptop&price=500&quantity_in_stock=10" \
     -H "X-API-Key: $API_KEY"

# 2. Bëj një porosi
curl -X POST http://localhost:8001/orders \
     -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
     -d '{"customer_name":"Ardit Krasniqi","customer_email":"ardit@example.com",
          "items":[{"product_id":1,"quantity":2,"unit_price":500}]}'

# 3. Shiko njoftimet
docker compose logs -f notification-service
#   [notification] Porosia 1 u pranua, email konfirmimi u dërgua.
#   [notification] Porosia 1 u konfirmua, stoku u rezervua.

# 4. Verifiko stokun: 10 -> 8
curl http://localhost:8002/products -H "X-API-Key: $API_KEY"
```

**Rastet negative:**

```bash
# Pa API key -> 401
curl -i -X POST http://localhost:8001/orders -d '{}'

# Sasi mbi stokun -> order.stock_failed, stoku nuk ndryshon
# Ndalje e shërbimit -> porositë presin në radhë dhe procesohen pas rindezjes
docker compose stop inventory-service
# ...bëj disa porosi...
docker compose start inventory-service
```

## Siguria

| Masa | Zbatimi |
| --- | --- |
| Kontroll qasjeje | `verify_api_key` si dependency në çdo endpoint biznesi; 401 pa `X-API-Key` |
| Kredencialet | Vetëm nga variabla mjedisi; `.env` në `.gitignore`, `.env.example` si shabllon |
| Izolim i të dhënave | Secili shërbim ka kredenciale vetëm për bazën e vet |
| Validim i hyrjeve | Pydantic v2: `EmailStr`, kufij sasie dhe çmimi -> 422 |
| Log i kërkesave | `RequestLoggingMiddleware`: metoda, rruga, statusi, kohëzgjatja |
| Audit log | `audit.py`: veprimet e shkrimit në JSON me kohë dhe aktor |
| Rate limiting | `infra/nginx/nginx.conf` para shërbimeve |

**Ku është API Key-i:** në `.env` lokal (nuk hyn kurrë në Git). Kodi e lexon me
`os.getenv("API_KEY")` te `app/security.py`. Në CI vjen nga GitHub Secrets, në
Kubernetes nga Secret-i `spdd-secrets`.

## Testet

```bash
cd order-service
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Testet nuk kërkojnë PostgreSQL as RabbitMQ: baza zëvendësohet me SQLite in-memory
përmes `app.dependency_overrides`, dhe `publish_event` mock-ohet për të kapur
ngjarjet. Prandaj ekzekutohen në CI për çdo push, në pak sekonda.

## Monitorimi

| Çfarë | Ku |
| --- | --- |
| Gjendja e shërbimeve | `/health` në të tria + healthcheck i compose-it |
| Metrika | `:8001/metrics` (Prometheus), konfigurimi te `infra/monitoring/` |
| Radhët dhe konsumatorët | RabbitMQ Management: http://localhost:15672 |
| Logs | `docker compose logs -f <shërbimi>` |

## Struktura e projektit

```
dyqani-teknologjik/
├── docker-compose.yml          # Orkestrimi: 7 kontejnerë, healthcheck, restart
├── .env.example                # Shabllon konfigurimi (pa vlera)
├── pyproject.toml              # ruff + pytest
├── CHANGELOG.md                # Historiku i versioneve
├── git-init-history.sh         # Krijon historinë e commit-eve
├── .github/workflows/ci.yml    # Lint, teste, ndërtim imazhesh, provë compose
├── order-service/
│   ├── Dockerfile · requirements.txt · requirements-dev.txt
│   ├── app/
│   │   ├── main.py             # Rrugët HTTP
│   │   ├── models.py           # ORM: Customer, Order, OrderItem
│   │   ├── schemas.py          # Kontratat Pydantic
│   │   ├── database.py         # Sesioni dhe engine-i
│   │   ├── messaging.py        # Publikimi i ngjarjeve
│   │   ├── security.py         # verify_api_key
│   │   ├── metrics.py          # Metrika Prometheus
│   │   ├── audit.py            # Audit log
│   │   └── logging_middleware.py
│   └── tests/                  # 8 teste pytest
├── inventory-service/
│   └── app/  main · models · database · consumer · cache · messaging · security
├── notification-service/
│   └── app/  main · consumer
├── docs/ARKITEKTURA.md         # Diagramet: komponentë, ERD, sekuencë
├── infra/                      # nginx.conf, prometheus.yml
├── k8s/                        # deployment.yaml, hpa.yaml
├── schemas/avro/               # Skema ngjarjesh të versionuara
├── nderfaqja/                  # Ndërfaqja në shfletues (shih më poshtë)
└── dokumente/                  # Raporti teknik dhe deklarata (.docx)
```

## Ndërfaqja në shfletues

Dosja `nderfaqja/` përmban një faqe që hapet drejtpërdrejt në shfletues, pa server:

| Faqja | Për kë |
| --- | --- |
| `Dyqani.dc.html` | Klienti: produktet, porosia, statusi, kthimi |


Dyqani dhe konsola ndajnë të njëjtën gjendje: një porosi e bërë në dyqan shfaqet
menjëherë si ngjarje në konsolë. Konsola ka edhe modalitetin **Sistemi real**,
që dërgon kërkesa të vërteta te `:8001` me API key.

## Dokumentet

- `dokumente/Deklarata-e-Origjinalitetit.docx` — deklarata e punës individuale

## Licenca

Projekt akademik, i realizuar për qëllime mësimore.
