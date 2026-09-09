"""Konsumatori i ngjarjes order.created — zemra e procesimit të stokut.

Tri vendime që vlen t'i vëresh:

1. Rezervimi është *all-or-nothing*: kontrollohen të gjithë artikujt para se të
   zbritet ndonjë. Kështu stoku nuk mbetet kurrë gjysmë i zbritur.
2. Konfirmimi (basic_ack) jepet vetëm pas procesimit të suksesshëm; nëse
   procesi bie në mes, mesazhi rikthehet në radhë.
3. Mesazhet që dështojnë vazhdimisht kalojnë në Dead Letter Queue, në vend që
   të bllokojnë radhën kryesore.
"""

import json
import os
import time

import pika

from app import models
from app.cache import invalidate
from app.database import SessionLocal
from app.messaging import publish_event

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "orders_exchange"
QUEUE_NAME = "inventory_order_created"
DLX_NAME = "orders_dlx"
DLQ_NAME = "inventory_order_created_dlq"
RETRY_SECONDS = 5


def _handle_order_created(payload: dict):
    """Rezervon stokun për porosinë dhe publikon rezultatin si ngjarje."""
    db = SessionLocal()
    try:
        # Faza 1 — verifikim: a mbulohen TË GJITHË artikujt?
        all_reserved = True
        for item in payload["items"]:
            product = (
                db.query(models.Product)
                .filter(models.Product.id == item["product_id"])
                .first()
            )
            if not product or product.quantity_in_stock < item["quantity"]:
                all_reserved = False
                break

        # Faza 2 — zbritje, vetëm nëse verifikimi kaloi.
        if all_reserved:
            for item in payload["items"]:
                product = (
                    db.query(models.Product)
                    .filter(models.Product.id == item["product_id"])
                    .first()
                )
                product.quantity_in_stock -= item["quantity"]
            db.commit()
            invalidate("products:all")
            publish_event("order.stock_reserved", {"order_id": payload["order_id"]})
        else:
            publish_event("order.stock_failed", {"order_id": payload["order_id"]})
    finally:
        db.close()


def _declare(channel):
    """Deklaron exchange-in, radhën kryesore dhe Dead Letter Queue-në."""
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=DLX_NAME, exchange_type="fanout", durable=True)
    channel.queue_declare(queue=DLQ_NAME, durable=True)
    channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME)
    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
        arguments={"x-dead-letter-exchange": DLX_NAME},
    )
    channel.queue_bind(
        exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key="order.created"
    )


def start_consumer():
    """Lidhet me brokerin dhe konsumon pafundësisht, me retry në dështim.

    Cikli i retry-t lejon që shërbimi të ngrihet edhe kur RabbitMQ nuk është
    ende gati — kërkesë e domosdoshme për `docker compose up` me një komandë.
    """
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            _declare(channel)

            def callback(ch, method, properties, body):
                try:
                    payload = json.loads(body.decode("utf-8"))
                    _handle_order_created(payload)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as exc:
                    # requeue=False -> mesazhi shkon në DLQ, nuk rikthehet pafund.
                    print(f"[inventory-service] Dështoi procesimi ({exc}) -> DLQ")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            print("[inventory-service] I lidhur me RabbitMQ, në pritje të order.created")
            channel.start_consuming()
        except Exception as exc:
            print(f"[inventory-service] Lidhja dështoi ({exc}), riprovë pas {RETRY_SECONDS}s")
            time.sleep(RETRY_SECONDS)
