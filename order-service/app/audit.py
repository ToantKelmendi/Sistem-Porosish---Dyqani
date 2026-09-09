"""Audit log për veprimet e shkrimit.

Ndryshe nga logu i kërkesave (që regjistron çdo HTTP), audit-i mban vetëm
ndryshimet e gjendjes: kush, çfarë, mbi cilin entitet dhe kur. Formati JSON
e bën të lexueshëm nga vegla si Loki ose Elasticsearch.
"""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("audit")


def audit_write(action: str, entity: str, entity_id, actor: str = "system"):
    """Shënon një veprim shkrimi në audit log."""
    logger.info(
        json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "entity": entity,
                "entity_id": entity_id,
                "actor": actor,
            },
            ensure_ascii=False,
        )
    )
