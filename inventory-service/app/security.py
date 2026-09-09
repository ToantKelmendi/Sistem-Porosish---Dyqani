"""Kontrolli i qasjes për endpoint-et e biznesit.

Kredenciali nuk qëndron kurrë në kod: lexohet nga variabla e mjedisit API_KEY,
e cila vendoset në .env (jashtë Git-it) ose në secrets të CI/CD-së.
"""

import os

from fastapi import Header, HTTPException, status

API_KEY = os.getenv("API_KEY", "changeme")


def verify_api_key(x_api_key: str = Header(...)):
    """Kontrollon që kërkesa përmban header-in X-API-Key të saktë."""
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key e pavlefshme ose mungon (header X-API-Key)",
        )
