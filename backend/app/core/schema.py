import os

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine

settings = get_settings()

async def schema_guard() -> dict:
    # Get current DB revision
    db_revision = None
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            db_revision = result.scalar()
    except Exception:
        pass

    # Get code head
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
        alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "..", "alembic"))
        script = ScriptDirectory.from_config(alembic_cfg)
        code_head = script.get_current_head()
    except Exception:
        code_head = None

    if db_revision == code_head:
        status = "ok"
    else:
        status = "mismatch"

    return {
        "schema": status,
        "db_revision": db_revision,
        "code_head": code_head
    }
