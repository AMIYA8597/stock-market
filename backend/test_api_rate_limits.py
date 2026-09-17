import asyncio
import httpx
import websockets

async def test_auth_rate_limit():
    print("Testing /auth/login rate limits...")
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000/api/v1") as client:
        # Hit 6 times, limit is 5 per 300s
        for i in range(6):
            res = await client.post("/auth/login", json={"email": "test_rl@example.com", "password": "password123"})
            print(f"Request {i+1}: Status {res.status_code}")
            if res.status_code == 429:
                print("SUCCESS: 429 Rate Limit hit on auth!")
                return
        print("FAILED: No 429 hit on auth!")

async def test_expensive_endpoint_rate_limit():
    print("\nTesting /ai/predict rate limits...")
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000/api/v1") as client:
        # Hit 6 times, limit is 5 per 60s
        for i in range(6):
            res = await client.post("/ai/predict", json={"symbol": "RELIANCE"})
            print(f"Request {i+1}: Status {res.status_code}")
            if res.status_code == 429:
                print("SUCCESS: 429 Rate Limit hit on AI!")
                return
        print("FAILED: No 429 hit on AI!")

async def test_websocket_limits():
    print("\nTesting WebSocket connection limits...")
    conns = []
    try:
        # Limit is 5
        for i in range(6):
            ws = await websockets.connect("ws://127.0.0.1:8000/ws/prices")
            conns.append(ws)
            print(f"WS {i+1} connected.")
            # Try to receive to catch the close frame if the server rejected us
            try:
                await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError:
                pass # Normal if the server just keeps it open without sending

            await asyncio.sleep(0.1)
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 1008:
            print("SUCCESS: WS Connection closed with 1008 (Limit Reached)!")
            return
        print(f"WS failed with other code: {e}")
    finally:
        for ws in conns:
            await ws.close()

async def main():
    await test_auth_rate_limit()
    await test_expensive_endpoint_rate_limit()
    await test_websocket_limits()

if __name__ == "__main__":
    asyncio.run(main())
