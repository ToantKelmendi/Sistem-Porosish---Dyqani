"""Publikimi i ngjarjeve në RabbitMQ.

Exchange-i është i tipit *topic* dhe *durable*: prodhuesi nuk i njeh
konsumatorët, dhe një konsumator i ri shtohet vetëm duke u lidhur me një
routing key — pa asnjë ndryshim këtu.

delivery_mode=2 i bën mesazhet të qëndrueshme, kështu që një rindezje e
brokerit nuk i humb ato.
"""

import json
import os

import pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
EXCHANGE_NAME = "orders_exchange"


def _get_channel():
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    channel.exchange_declare(
        exchange=EXCHANGE_NAME, exchange_type="topic", durable=True
    )
    return connection, channel


def publish_event(routing_key: str, payload: dict):
    """Publikon një ngjarje të domenit, p.sh. order.created."""
    connection, channel = _get_channel()
    try:
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json", delivery_mode=2
            ),
        )
    finally:
        connection.close()
