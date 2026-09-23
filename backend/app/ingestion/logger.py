import uuid
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.operational import IngestionRun, DataQualityEvent

class IngestionLogger:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def start_run(self, engine_name: str, target: str, config: Optional[Dict[str, Any]] = None) -> IngestionRun:
        run = IngestionRun(
            job_type=engine_name,
            dataset_type=target,
            provider="system",
            status="running"
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def complete_run(self, run: IngestionRun, rows_processed: int, error_message: Optional[str] = None):
        run.status = "completed" if not error_message else "failed"
        run.successful_count = rows_processed
        run.error_message = error_message
        self.session.add(run)
        await self.session.commit()

    async def log_quality_event(self, run_id: uuid.UUID, instrument_id: uuid.UUID, severity: str, issue_type: str, details: Dict[str, Any]):
        event = DataQualityEvent(
            run_id=run_id,
            instrument_id=instrument_id,
            severity=severity,
            issue_type=issue_type,
            description=str(details)
        )
        self.session.add(event)
        await self.session.commit()
