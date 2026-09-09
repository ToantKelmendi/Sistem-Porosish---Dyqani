"""Cache Redis për listën e produkteve.

Degradim i butë: nëse Redis nuk është i disponueshëm, funksionet kthejnë None
dhe sistemi vazhdon të lexojë nga baza. Cache-i është optimizim, jo varësi.
"""

import json
import os

try:
    import redis
except ImportError:  # Redis është opsional në zhvillim
    redis = None

REDIS_URL = os.getenv("REDIS_URL", "")
_client = None

if redis and REDIS_URL:
    try:
        _client = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        _client = None


def cache_get(key: str):
    """Kthen vlerën e ruajtur, ose None nëse mungon / Redis është jashtë."""
    if not _client:
        return None
    try:
        raw = _client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def cache_set(key: str, value, ttl: int = 30):
    """Ruan vlerën me afat skadimi; dështimi kurrë nuk e ndalon kërkesën."""
    if not _client:
        return
    try:
        _client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def invalidate(key: str):
    """Fshin çelësin pas një shkrimi, që leximi të mos kthejë të dhëna të vjetra."""
    if not _client:
        return
    try:
        _client.delete(key)
    except Exception:
        pass
