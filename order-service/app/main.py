"""Order Service — pika hyrëse HTTP e sistemit.

Përgjegjësia: pranon porosinë, e ruan në orders_db dhe publikon ngjarjen
`order.created`. NUK pret kontrollin e stokut — pikërisht kjo e mban kohën e
përgjigjes të pavarur nga shërbimet e tjera.

Endpoint-et e biznesit mbrohen me X-API-Key; /health dhe /metrics mbeten publike
sepse i thërret monitorimi.
"""

from typing import List

from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy.orm import Session

from app import models, schemas
from app.audit import audit_write
from app.database import Base, engine, get_db
from app.logging_middleware import RequestLoggingMiddleware
from app.messaging import publish_event
from app.metrics import ORDERS_CREATED, metrics_payload
from app.security import verify_api_key

app = FastAPI(
    title="Order Service",
    version="1.1.0",
    description="Pranimi i porosive dhe publikimi i ngjarjeve të domenit.",
)
app.add_middleware(RequestLoggingMiddleware)


@app.on_event("startup")
def on_startup():
    """Krijon skemën nëse mungon — ngritja e sistemit mbetet një komandë e vetme."""
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["monitorim"])
def health():
    """Endpoint publik, pa autentikim — përdoret nga Docker/Kubernetes."""
    return {"status": "ok", "service": "order-service"}


@app.get("/metrics", tags=["monitorim"])
def metrics():
    """Metrika në format Prometheus."""
    body, content_type = metrics_payload()
    return Response(content=body, media_type=content_type)


@app.post(
    "/orders",
    response_model=schemas.OrderOut,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
    tags=["porosi"],
)
def create_order(order_in: schemas.OrderCreate, db: Session = Depends(get_db)):
    """Krijon porosinë dhe publikon order.created.

    Klienti identifikohet me email: nëse ekziston, ripërdoret; përndryshe
    krijohet. Kjo mban unique-in e emailit të vlefshëm pa kërkuar regjistrim
    të veçantë.
    """
    customer = (
        db.query(models.Customer)
        .filter(models.Customer.email == order_in.customer_email)
        .first()
    )
    if not customer:
        customer = models.Customer(
            name=order_in.customer_name, email=order_in.customer_email
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

    order = models.Order(customer_id=customer.id, status="pending")
    db.add(order)
    db.commit()
    db.refresh(order)

    for item in order_in.items:
        db.add(
            models.OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
        )
    db.commit()
    db.refresh(order)

    publish_event(
        "order.created",
        {
            "order_id": order.id,
            "customer_email": customer.email,
            "items": [
                {"product_id": i.product_id, "quantity": i.quantity}
                for i in order.items
            ],
        },
    )
    ORDERS_CREATED.inc()
    audit_write("order.create", entity="order", entity_id=order.id, actor=customer.email)

    return order


@app.get(
    "/orders/{order_id}",
    response_model=schemas.OrderOut,
    dependencies=[Depends(verify_api_key)],
    tags=["porosi"],
)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Kthen një porosi të vetme me artikujt e saj."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Porosia nuk u gjet")
    return order


@app.get(
    "/orders",
    response_model=List[schemas.OrderOut],
    dependencies=[Depends(verify_api_key)],
    tags=["porosi"],
)
def list_orders(db: Session = Depends(get_db)):
    """Lista e porosive — në prodhim do të shtohej faqosje (limit/offset)."""
    return db.query(models.Order).all()
