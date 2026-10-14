import os
import time

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_CODE_HEAD_CACHE: str | None = None
_CODE_HEAD_RESOLVED: bool = False
_DB_REVISION_CACHE: tuple[float, str | None] = (0.0, None)
_DB_REVISION_TTL_SECONDS: float = 30.0


def _get_code_head() -> str | None:
    global _CODE_HEAD_CACHE, _CODE_HEAD_RESOLVED
    if _CODE_HEAD_RESOLVED:
        return _CODE_HEAD_CACHE
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
        alembic_cfg.set_main_option(
            "script_location", os.path.join(os.path.dirname(__file__), "..", "..", "alembic")
        )
        script = ScriptDirectory.from_config(alembic_cfg)
        _CODE_HEAD_CACHE = script.get_current_head()
        _CODE_HEAD_RESOLVED = True
    except Exception as e:
        logger.warning("schema_guard_code_head_failed", error=str(e), error_type=type(e).__name__)
        _CODE_HEAD_CACHE = None
    return _CODE_HEAD_CACHE


async def schema_guard() -> dict:
    global _DB_REVISION_CACHE
    now = time.monotonic()
    cached_ts, cached_rev = _DB_REVISION_CACHE

    from app.core.test_state import is_test_mode

    if (
        not is_test_mode()
        and cached_rev is not None
        and (now - cached_ts) < _DB_REVISION_TTL_SECONDS
    ):
        db_revision = cached_rev
    else:
        db_revision = None
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                db_revision = result.scalar()
                if db_revision is not None:
                    _DB_REVISION_CACHE = (now, db_revision)
        except Exception:
            pass

    code_head = _get_code_head()

    if db_revision == code_head:
        status = "ok"
    else:
        status = "mismatch"

    return {
        "schema": status,
        "db_revision": db_revision,
        "code_head": code_head,
    }
