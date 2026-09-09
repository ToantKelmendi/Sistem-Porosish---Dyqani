"""Inventory Service — pronari i vetëm i të dhënave të stokut.

Ka dy role: API për menaxhimin e produkteve, dhe konsumator që reagon ndaj
ngjarjes order.created. Konsumatori niset në thread të veçantë që të mos e
bllokojë serverin HTTP.
"""

import threading

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.cache import cache_get, cache_set, invalidate
from app.consumer import start_consumer
from app.database import Base, engine, get_db
from app.logging_middleware import RequestLoggingMiddleware
from app.security import verify_api_key

app = FastAPI(
    title="Inventory Service",
    version="1.1.0",
    description="Menaxhimi i produkteve dhe rezervimi automatik i stokut.",
)
app.add_middleware(RequestLoggingMiddleware)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    threading.Thread(target=start_consumer, daemon=True).start()


@app.get("/health", tags=["monitorim"])
def health():
    """Endpoint publik, pa autentikim — përdoret nga Docker/Kubernetes."""
    return {"status": "ok", "service": "inventory-service"}


@app.post("/products", status_code=201, dependencies=[Depends(verify_api_key)], tags=["produkte"])
def create_product(
    name: str, price: float, quantity_in_stock: int, db: Session = Depends(get_db)
):
    """Regjistron një produkt të ri dhe pavlefshmëron cache-in e listës."""
    if price <= 0 or quantity_in_stock < 0:
        raise HTTPException(status_code=422, detail="Çmimi ose sasia e pavlefshme")
    product = models.Product(name=name, price=price, quantity_in_stock=quantity_in_stock)
    db.add(product)
    db.commit()
    db.refresh(product)
    invalidate("products:all")
    return product


@app.get("/products", dependencies=[Depends(verify_api_key)], tags=["produkte"])
def list_products(db: Session = Depends(get_db)):
    """Lista e produkteve, e shërbyer nga cache kur është e ngrohtë.

    Kjo është rruga më e thirrur e sistemit dhe ndryshon rrallë — prandaj
    pikërisht këtu cache-i ka kuptim.
    """
    cached = cache_get("products:all")
    if cached is not None:
        return cached
    products = [
        {
            "id": p.id,
            "name": p.name,
            "price": p.price,
            "quantity_in_stock": p.quantity_in_stock,
        }
        for p in db.query(models.Product).all()
    ]
    cache_set("products:all", products, ttl=30)
    return products
