"""Re-export shim: canonical Instrument model lives in app.models.market."""
from app.models.market import Instrument

__all__ = ["Instrument"]
