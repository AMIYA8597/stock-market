# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "websockets",
# ]
# ///

import asyncio
import json

import websockets


async def test_connection():
    uri = "ws://localhost:8000/ws/prices"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Sending subscribe message for market:RELIANCE.NS")
            await websocket.send(json.dumps({
                "action": "subscribe",
                "symbols": ["RELIANCE.NS"]
            }))

            # Wait for 3 messages
            for _ in range(3):
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10)
                    data = json.loads(message)
                    print(f"Received: {json.dumps(data, indent=2)}")
                except TimeoutError:
                    print("Timeout waiting for message")
                    break
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
