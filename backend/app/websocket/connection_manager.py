"""WebSocket connection manager accessors."""

from app.core.websocket_manager import ConnectionManager, ws_manager


def get_connection_manager() -> ConnectionManager:
    """Return the shared connection manager instance."""
    return ws_manager
