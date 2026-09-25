"""
Project P4: Background Tasks & Audit Worker
"""
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger("worker")

audit_log_sink: list[dict] = []


async def process_audit_log(user_id: str, action: str, resource_id: str):
    """Background worker simulating asynchronous audit ingestion."""
    await asyncio.sleep(0.01)
    record = {
        "user_id": user_id,
        "action": action,
        "resource_id": resource_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    audit_log_sink.append(record)
    logger.info(f"[AUDIT EVENT] User {user_id} performed '{action}' on {resource_id}")
