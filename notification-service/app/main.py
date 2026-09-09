"""Notification Service — konsumator i pastër, pa bazë të dhënash.

Nuk mban gjendje: dëgjon të gjitha ngjarjet e domenit (order.#) dhe njofton
klientin. Prandaj shkallëzohet lirshëm dhe nuk ka nevojë për migrime.
"""

import threading

from fastapi import FastAPI

from app.consumer import start_consumer

app = FastAPI(
    title="Notification Service",
    version="1.1.0",
    description="Njoftimi i klientit për çdo ndryshim statusi të porosisë.",
)


@app.on_event("startup")
def on_startup():
    threading.Thread(target=start_consumer, daemon=True).start()


@app.get("/health", tags=["monitorim"])
def health():
    """Endpoint publik, pa autentikim — përdoret nga Docker/Kubernetes."""
    return {"status": "ok", "service": "notification-service"}
