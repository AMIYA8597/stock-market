"""Re-export shim: canonical Organization model lives in app.models.identity."""
from app.models.identity import Organization

__all__ = ["Organization"]
