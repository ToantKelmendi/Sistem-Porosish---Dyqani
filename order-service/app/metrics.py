"""Metrika Prometheus për Order Service.

Ekspozohen në /metrics dhe grumbullohen nga Prometheus sipas
infra/monitoring/prometheus.yml.
"""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

ORDERS_CREATED = Counter(
    "orders_created_total", "Numri i porosive të krijuara me sukses"
)

EVENTS_PUBLISHED = Counter(
    "events_published_total", "Ngjarje të publikuara", ["routing_key"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds", "Kohëzgjatja e kërkesave HTTP", ["endpoint"]
)


def metrics_payload():
    """Kthen (trupin, content-type) e gatshëm për përgjigjen HTTP."""
    return generate_latest(), CONTENT_TYPE_LATEST
