import asyncio
import websockets
import json
from beeper import beep
clients = set()

async def handler(ws):
    clients.add(ws)
    try:
        async for message in ws:
            data = json.loads(message)
            beep()
            print(f"Received message: {data}")
    finally:
        clients.remove(ws)

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
