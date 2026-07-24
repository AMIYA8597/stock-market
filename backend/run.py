import os

from .app import create_app

app, socketio = create_app()
# Start background price broadcast for default ticker (can be changed via client)
from .socket_events import start_price_broadcast

start_price_broadcast(socketio, ticker="NIFTY")

if __name__ == "__main__":
    # Use eventlet for production
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
