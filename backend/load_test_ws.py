import asyncio
import json
import random
import time

import websockets

URI = "ws://localhost:8000/ws/prices"
NUM_CLIENTS = 500
SYMBOLS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]

async def client_task(client_id):
    try:
        async with websockets.connect(URI) as websocket:
            symbol = random.choice(SYMBOLS)
            await websocket.send(json.dumps({
                "action": "subscribe",
                "symbols": [symbol]
            }))

            message_count = 0
            start_time = time.time()

            # Listen for 15 seconds
            while time.time() - start_time < 15:
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    message_count += 1
                except TimeoutError:
                    continue
            return message_count
    except Exception as e:
        return f"Error: {e}"

async def main():
    print(f"Starting load test with {NUM_CLIENTS} concurrent clients...")
    start = time.time()

    tasks = [asyncio.create_task(client_task(i)) for i in range(NUM_CLIENTS)]
    results = await asyncio.gather(*tasks)

    end = time.time()

    errors = [r for r in results if isinstance(r, str) and r.startswith("Error")]
    successes = [r for r in results if isinstance(r, int)]

    print(f"Load test completed in {end - start:.2f} seconds.")
    print(f"Total Successful Connections: {len(successes)}")
    print(f"Total Errors: {len(errors)}")
    if successes:
        print(f"Average messages received per client: {sum(successes) / len(successes):.2f}")
    if errors:
        print(f"Sample error: {errors[0]}")

if __name__ == "__main__":
    asyncio.run(main())
