import asyncio
import json
import websockets
from .handler import handle_message
from .state import LOBBY, USERS
from .utils import notify_lobby


async def handler(ws):
    print(f"[SERVER] New socket connection: {ws.remote_address}")
    try:
        name = await ws.recv()
        print(f"[SERVER] New client joined: {name}")
        LOBBY[ws] = name
        USERS.add(ws)
        await notify_lobby()
        async for msg in ws:
            data = json.loads(msg)
            await handle_message(ws, data)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        USERS.discard(ws)
        LOBBY.pop(ws, None)
        # ...rest of cleanup logic...
        await notify_lobby()


async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
