# Arkitektura e sistemit

## 1. Diagramë komponentësh

```mermaid
flowchart TD
    C[Klienti] -->|HTTP + X-API-Key| G[Gateway Nginx :8080<br/>rate limiting]
    G --> OS[Order Service :8001]
    G --> IS[Inventory Service :8002]
    OS -->|order.created| EX{{orders_exchange<br/>topic · durable}}
    EX -->|bind order.created| IS
    EX -->|bind order.#| NS[Notification Service :8003]
    IS -->|order.stock_reserved<br/>order.stock_failed| EX
    OS --- ODB[(orders_db)]
    IS --- IDB[(inventory_db)]
    IS --- R[(Redis cache)]
    EX -.->|mesazhe të dështuara| DLQ[(orders_dead_letter)]
    OS -->|/metrics| P[Prometheus]
    IS -->|/metrics| P
    P --> GF[Grafana]
```

Pse kjo ndarje: pranimi i porosisë nuk duhet të varet nga kohëzgjatja e kontrollit të
stokut, dhe njoftimi i klientit nuk duhet të bllokojë asnjërën. Order Service nuk e njeh
Inventory Service — komunikimi kalon vetëm përmes event-eve, kështu që një konsumator i
re shtohet me një `queue_bind`, pa ndryshuar prodhuesin.

## 2. Modeli i të dhënave (ERD)

```mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : "bën"
    ORDER ||--o{ ORDER_ITEM : "përmban"
    CUSTOMER {
        int id PK
        string name
        string email UK
    }
    ORDER {
        int id PK
        int customer_id FK
        string status "pending|stock_reserved|stock_failed"
        datetime created_at
    }
    ORDER_ITEM {
        int id PK
        int order_id FK
        int product_id "referencë logjike"
        int quantity
        float unit_price
    }
    PRODUCT {
        int id PK
        string name
        float price
        int quantity_in_stock
    }
```

`CUSTOMER`, `ORDER` dhe `ORDER_ITEM` janë në `orders_db`; `PRODUCT` është në
`inventory_db`. Nuk ekziston foreign key ndër-bazë — `product_id` është referencë
logjike që transportohet në event. Kjo është ndarja sipas domain-it: secili shërbim
mund të shkallëzohet dhe migrohet i pavarur.

Integriteti: `email` është `unique`; `ORDER → ORDER_ITEM` ka
`cascade="all, delete-orphan"`; indekse në `orders.customer_id`,
`order_items.order_id` dhe `orders.status` (kolonat më të filtruara).

## 3. Rrjedha e një porosie

```mermaid
sequenceDiagram
    participant K as Klienti
    participant O as Order Service
    participant B as orders_exchange
    participant I as Inventory Service
    participant N as Notification Service
    K->>O: POST /orders (X-API-Key)
    O->>O: ruaj porosinë (status pending)
    O->>B: publiko order.created (delivery_mode=2)
    O-->>K: 201 Created
    B->>I: order.created (prefetch 1)
    I->>I: kontrollo dhe zbrit stokun (transaksion)
    I->>B: order.stock_reserved | order.stock_failed
    I->>B: basic_ack
    B->>N: order.# 
    N->>K: email njoftimi
```

Përgjigjja 201 kthehet para se stoku të kontrollohet — kjo është arsyeja pse koha e
përgjigjes nuk varet nga Inventory Service.

## 4. Qëndrueshmëria

| Mekanizmi | Ku | Çfarë mbron |
| --- | --- | --- |
| `restart: on-failure` | docker-compose.yml | Rifillim automatik i kontejnerit |
| Healthcheck + `service_healthy` | docker-compose.yml | Nisje në rendin e duhur |
| Retry loop 5s | consumer.py | Brokeri mund të ngrihet më vonë |
| `delivery_mode=2` + radhë durable | messaging.py | Mesazhi mbijeton rinisjen e brokerit |
| `basic_ack` manual | consumer.py | Mesazhi hiqet vetëm pas suksesit |
| Dead Letter Queue | messaging.py | Mesazhet e dështuara ruhen për inspektim |
| `prefetch_count=1` | consumer.py | Ndarje e drejtë mes replikave |
| HPA (CPU/RAM + thellësi radhe) | k8s/hpa.yaml | Shkallëzim automatik nën ngarkesë |
