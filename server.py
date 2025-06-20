# =========================================
#              IMPORTS
# =========================================
import asyncio  # Async event loop
import websockets  # WebSocket server
import json  # JSON encoding/decoding
import uuid  # Unique room IDs

# =========================================
#         GLOBAL LOBBY STATE
# =========================================
USERS = set()  # Set of all connected websockets
LOBBY = {}  # Maps websocket to username
OPEN_ROOMS = {}  # Maps room_id to dict: { 'id': room_id, 'users': [usernames] }
USERS_IN_ROOM = set()  # Set of users currently in a room
INVITES = {}  # Maps inviter websocket to invitee websocket


# =========================================
#         UTILITY FUNCTIONS
# =========================================
async def notify_lobby():
    if USERS:
        # Mark users in a room
        in_room = set()
        for ws in USERS:
            # If this user is in a room, mark them
            for ws2 in USERS:
                # If either has a room window open, mark both
                # (We use a simple heuristic: if a user has received a room_joined message, they are in a room)
                # We'll track this with a new dict: USERS_IN_ROOM
                if ws in USERS_IN_ROOM:
                    in_room.add(ws)
        usernames = []
        for user in USERS:
            name = LOBBY[user]
            if user in USERS_IN_ROOM:
                name += " (in room)"
            usernames.append(name)
        open_rooms = [r["id"] for r in OPEN_ROOMS.values()]
        message = json.dumps(
            {
                "type": "lobby_update",
                "users": usernames,
                "open_rooms": open_rooms,
            }
        )
        await asyncio.gather(*(user.send(message) for user in USERS))


# =========================================
#         MESSAGE HANDLER
# =========================================
async def handle_message(ws, data):
    if data.get("type") == "invite":
        if ws in INVITES:
            return
        to_user = data.get("to")
        for ws2, uname in LOBBY.items():
            if uname == to_user and ws2 != ws:
                INVITES[ws] = ws2
                await ws2.send(
                    json.dumps({"type": "invite_received", "from": LOBBY[ws]})
                )
                break
    elif data.get("type") == "invite_response":
        from_user = data.get("from")
        accepted = data.get("accepted")
        inviter_ws = None
        for ws_inviter, ws_invitee in INVITES.items():
            if ws_invitee == ws and LOBBY.get(ws_inviter) == from_user:
                inviter_ws = ws_inviter
                break
        if inviter_ws:
            await inviter_ws.send(
                json.dumps(
                    {"type": "invite_result", "from": LOBBY[ws], "accepted": accepted}
                )
            )
            if accepted:
                # Both users enter a room
                usernames = [LOBBY[ws], LOBBY[inviter_ws]]
                USERS_IN_ROOM.add(ws)
                USERS_IN_ROOM.add(inviter_ws)
                await ws.send(
                    json.dumps({"type": "room_joined", "usernames": usernames})
                )
                await inviter_ws.send(
                    json.dumps({"type": "room_joined", "usernames": usernames})
                )
                await notify_lobby()
            INVITES.pop(inviter_ws, None)
    elif data.get("type") == "enter_room":
        # Inviter requests to enter room after invite accepted
        # Find the invitee
        invitee_ws = INVITES.get(ws)
        if invitee_ws:
            usernames = [LOBBY[ws], LOBBY[invitee_ws]]
            await ws.send(json.dumps({"type": "room_joined", "usernames": usernames}))
            await invitee_ws.send(
                json.dumps({"type": "room_joined", "usernames": usernames})
            )
            INVITES.pop(ws, None)
    elif data.get("type") == "create_room":
        room_id = f"{LOBBY[ws]}'s room"
        OPEN_ROOMS[room_id] = {"id": room_id, "users": [LOBBY[ws]]}
        USERS_IN_ROOM.add(ws)
        await ws.send(json.dumps({"type": "room_joined", "usernames": [LOBBY[ws]]}))
        await notify_lobby()
    elif data.get("type") == "join_room":
        room_id = data.get("room_id")
        room = OPEN_ROOMS.get(room_id)
        if room and len(room["users"]) == 1:
            room["users"].append(LOBBY[ws])
            # Find the websocket of the room creator
            creator_ws = None
            for w, name in LOBBY.items():
                if name == room["users"][0]:
                    creator_ws = w
                    break
            USERS_IN_ROOM.add(ws)
            USERS_IN_ROOM.add(creator_ws)
            usernames = room["users"]
            await ws.send(json.dumps({"type": "room_joined", "usernames": usernames}))
            await creator_ws.send(
                json.dumps({"type": "room_joined", "usernames": usernames})
            )
            await notify_lobby()
    elif data.get("type") == "leave_room":
        name = LOBBY.get(ws)
        USERS_IN_ROOM.discard(ws)
        # Remove user from any open room
        for room_id, room in list(OPEN_ROOMS.items()):
            if name in room["users"]:
                room["users"].remove(name)
                if not room["users"]:
                    del OPEN_ROOMS[room_id]
        for ws2 in list(LOBBY.keys()):
            if ws2 != ws and LOBBY[ws2] in data.get("usernames", []):
                USERS_IN_ROOM.discard(ws2)
                await ws2.send(
                    json.dumps(
                        {
                            "type": "room_update",
                            "usernames": [
                                n for n in data.get("usernames", []) if n != name
                            ],
                        }
                    )
                )
        await ws.send(json.dumps({"type": "room_left"}))
        await notify_lobby()


# =========================================
#         CONNECTION HANDLER
# =========================================
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
        INVITES.pop(ws, None)
        for rid, room in list(OPEN_ROOMS.items()):
            if name in room["users"]:
                room["users"].remove(name)
                if not room["users"]:
                    del OPEN_ROOMS[rid]
        await notify_lobby()


# =========================================
#         SERVER ENTRY POINT
# =========================================
async def main():
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
