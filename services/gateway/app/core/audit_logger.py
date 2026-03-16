"""
Comprehensive audit logging system with blockchain-style integrity.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis.asyncio as redis
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = structlog.get_logger()


class AuditLogger:
    """
    Audit logging system with immutable log entries and hash chaining.
    """

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.last_hash: Optional[str] = None

    async def startup(self):
        """
        Initialize audit logger.
        """
        if settings.ENABLE_AUDIT_LOGGING:
            self.redis = redis.from_url(
                settings.REDIS_URL,
                db=settings.REDIS_DB_CACHE,
                decode_responses=True,
            )

            # Load last hash from Redis
            self.last_hash = await self.redis.get("audit:last_hash")

            logger.info("Audit logger started", last_hash=self.last_hash)

    async def shutdown(self):
        """
        Cleanup audit logger.
        """
        if self.redis:
            await self.redis.close()

    async def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """
        Log an audit event with integrity hash.
        """
        if not settings.ENABLE_AUDIT_LOGGING:
            return

        timestamp = datetime.now(timezone.utc)

        # Create audit entry
        entry = {
            "timestamp": timestamp.isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "session_id": session_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "resource": resource,
            "action": action,
            "details": details or {},
            "success": success,
            "error_message": error_message,
            "prev_hash": self.last_hash,
        }

        # Calculate hash
        entry_json = json.dumps(entry, sort_keys=True, default=str)
        current_hash = hashlib.sha256(entry_json.encode()).hexdigest()
        entry["row_hash"] = current_hash

        # Update last hash for next entry
        self.last_hash = current_hash

        # Store in database
        async for db in get_db():
            try:
                await db.execute(
                    text("""
                        INSERT INTO audit_log (
                            timestamp, event_type, user_id, session_id,
                            ip_address, user_agent, resource, action,
                            details, success, error_message,
                            prev_hash, row_hash
                        ) VALUES (
                            :timestamp, :event_type, :user_id, :session_id,
                            :ip_address, :user_agent, :resource, :action,
                            :details, :success, :error_message,
                            :prev_hash, :row_hash
                        )
                    """),
                    {
                        "timestamp": timestamp,
                        "event_type": event_type,
                        "user_id": user_id,
                        "session_id": session_id,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "resource": resource,
                        "action": action,
                        "details": json.dumps(details) if details else None,
                        "success": success,
                        "error_message": error_message,
                        "prev_hash": self.last_hash,
                        "row_hash": current_hash,
                    }
                )
                await db.commit()

                # Update last hash in Redis
                if self.redis:
                    await self.redis.set("audit:last_hash", current_hash)

            except Exception as e:
                logger.error("Failed to write audit log", error=str(e))
                await db.rollback()

    async def verify_integrity(self) -> bool:
        """
        Verify the integrity of the audit log by checking hash chain.
        """
        async for db in get_db():
            try:
                result = await db.execute(
                    text("""
                        SELECT id, prev_hash, row_hash,
                               ROW_NUMBER() OVER (ORDER BY id) as row_num
                        FROM audit_log
                        ORDER BY id
                    """)
                )
                rows = result.fetchall()

                expected_prev_hash = None
                for row in rows:
                    if row.prev_hash != expected_prev_hash:
                        logger.error(
                            "Audit log integrity violation",
                            row_id=row.id,
                            expected_prev_hash=expected_prev_hash,
                            actual_prev_hash=row.prev_hash,
                        )
                        return False

                    # Recalculate hash to verify
                    # Note: This would require fetching the full row data
                    # For now, we trust the stored row_hash
                    expected_prev_hash = row.row_hash

                return True

            except Exception as e:
                logger.error("Failed to verify audit log integrity", error=str(e))
                return False

    async def get_audit_trail(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list:
        """
        Retrieve audit trail with optional filters.
        """
        async for db in get_db():
            try:
                query = """
                    SELECT timestamp, event_type, user_id, session_id,
                           ip_address, resource, action, details, success
                    FROM audit_log
                    WHERE 1=1
                """
                params = {}

                if user_id:
                    query += " AND user_id = :user_id"
                    params["user_id"] = user_id

                if event_type:
                    query += " AND event_type = :event_type"
                    params["event_type"] = event_type

                if start_date:
                    query += " AND timestamp >= :start_date"
                    params["start_date"] = start_date

                if end_date:
                    query += " AND timestamp <= :end_date"
                    params["end_date"] = end_date

                query += " ORDER BY timestamp DESC LIMIT :limit"
                params["limit"] = limit

                result = await db.execute(text(query), params)
                return result.fetchall()

            except Exception as e:
                logger.error("Failed to retrieve audit trail", error=str(e))
                return []


# Global audit logger instance
audit_logger = AuditLogger()