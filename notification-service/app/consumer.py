"""Konsumon të gjitha ngjarjet e domenit të porosive.

Lidhja bëhet me modelin `order.#`, jo me ngjarje të veçanta — prandaj një
ngjarje e re (p.sh. order.returned) mbërrin këtu pa asnjë ndryshim kodi.

Dërgimi real i email-it është jashtë fushëveprimit të projektit; funksioni
_send_notification shënon pikën ku do të lidhej një ofrues si SendGrid.
"""

import json
import os
import time

import pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "orders_exchange"
QUEUE_NAME = "notification_order_events"
RETRY_SECONDS = 5

MESAZHET = {
    "order.created": "Porosia {oid} u pranua, email konfirmimi u dërgua.",
    "order.stock_reserved": "Porosia {oid} u konfirmua, stoku u rezervua.",
    "order.stock_failed": "Porosia {oid} nuk u plotësua dot, stok i pamjaftueshëm.",
    "order.returned": "Porosia {oid} u kthye, shuma do të rimbursohet.",
}


def _send_notification(routing_key: str, payload: dict):
    """Formaton dhe 'dërgon' njoftimin për klientin."""
    order_id = payload.get("order_id")
    shabllon = MESAZHET.get(routing_key)
    if shabllon:
        print("[notification] " + shabllon.format(oid=order_id))


def start_consumer():
    """Konsumon order.# pafundësisht, me rilidhje automatike."""
    while True:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.exchange_declare(
                exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
            )
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.queue_bind(
                exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key="order.#"
            )

            def callback(ch, method, properties, body):
                payload = json.loads(body.decode("utf-8"))
                _send_notification(method.routing_key, payload)
                ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            print("[notification-service] I lidhur me RabbitMQ, në pritje të order.#")
            channel.start_consuming()
        except Exception as exc:
            print(f"[notification-service] Lidhja dështoi ({exc}), riprovë pas {RETRY_SECONDS}s")
            time.sleep(RETRY_SECONDS)
