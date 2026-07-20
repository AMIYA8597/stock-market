import threading, time
from flask_socketio import emit
from .data_service import get_latest_price

def start_price_broadcast(socketio, ticker='NIFTY'):
    """Background thread that fetches latest price every 5 seconds and emits via SocketIO."""
    def run():
        while True:
            try:
                data = get_latest_price(ticker)
                if data:
                    socketio.emit('price_update', data, namespace='/prices')
            except Exception as e:
                # log or ignore
                pass
            time.sleep(5)
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
