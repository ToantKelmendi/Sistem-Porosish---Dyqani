"""Middleware që regjistron çdo kërkesë HTTP.

Përse: rubrika kërkon "regjistrimi i aktiviteteve". Një log për kërkesë, me
kohëzgjatjen, e bën të mundur si auditimin (kush kërkoi çfarë) ashtu edhe
matjen e performancës pa vegla të jashtme.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("request_logger")
logging.basicConfig(level=logging.INFO)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Regjistron çdo kërkesë HTTP: metoda, rruga, kodi i përgjigjes, kohëzgjatja."""

    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
