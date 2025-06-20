# =========================================
#              IMPORTS
# =========================================
import asyncio  # Import asyncio for async event loop support
import websockets  # Import websockets for WebSocket server
import json  # Import json for encoding/decoding messages
import uuid  # Import uuid for generating unique room IDs

# =========================================
#         GLOBAL LOBBY STATE
# =========================================
USERS = set()  # Set to store all connected websocket clients
LOBBY = {}  # Dictionary mapping websocket to username
OPEN_ROOMS = {}  # Dictionary mapping room_id to room info (id, users)
INVITES = {}  # Dictionary mapping inviter websocket to set of invitee websockets
USERS_IN_ROOM = set()  # Set of websockets currently in a room
# Track invited users for each room (room_id -> set of usernames)
ROOM_INVITEES = {}


# =========================================
#         UTILITY FUNCTIONS
# =========================================
async def notify_lobby():  # Function to notify all users of the current lobby state
    if USERS:  # If there are any connected users
        usernames = []  # List to store usernames for the lobby update
        for user in USERS:  # Iterate through all connected users
            name = LOBBY[user]  # Get the username for this websocket
            if user in USERS_IN_ROOM:  # If the user is in a room
                name += " (in room)"  # Mark them as in a room
            usernames.append(name)  # Add the username to the list
        open_rooms = [r["id"] for r in OPEN_ROOMS.values()]  # List of open room IDs
        # Create the lobby update message as JSON
        message = json.dumps(
            {
                "type": "lobby_update",  # Message type
                "users": usernames,  # List of usernames
                "open_rooms": open_rooms,  # List of open room IDs
            }
        )
        # Send the message to all users
        await asyncio.gather(*(user.send(message) for user in USERS))


# =========================================
#         MESSAGE HANDLER
# =========================================
async def handle_message(ws, data):  # Function to handle messages from clients
    if data.get("type") == "invite":  # If the message is an invite
        to_users = data.get("to")  # Get the usernames being invited (list)
        if not isinstance(to_users, list):
            to_users = [to_users] if to_users else []
        if ws not in INVITES:
            INVITES[ws] = set()
        room_id = f"{LOBBY[ws]}'s room"
        # Track invitees for this room
        if room_id not in ROOM_INVITEES:
            ROOM_INVITEES[room_id] = set()
        for to_user in to_users:
            # Find the websocket for the invited user
            for ws2, uname in LOBBY.items():
                if uname == to_user and ws2 != ws and ws2 not in INVITES[ws]:
                    INVITES[ws].add(ws2)
                    ROOM_INVITEES[room_id].add(uname)  # Track invitee for room
                    await ws2.send(
                        json.dumps({"type": "invite_received", "from": LOBBY[ws]})
                    )
    elif data.get("type") == "invite_response":  # If the message is an invite response
        from_user = data.get("from")  # Get the inviter's username
        accepted = data.get("accepted")  # Get whether the invite was accepted
        inviter_ws = None
        # Find the inviter for this invitee
        for ws_inviter, invitees in INVITES.items():
            if ws in invitees and LOBBY.get(ws_inviter) == from_user:
                inviter_ws = ws_inviter
                break
        if inviter_ws:
            await inviter_ws.send(
                json.dumps(
                    {"type": "invite_result", "from": LOBBY[ws], "accepted": accepted}
                )
            )
            room_id = f"{LOBBY[inviter_ws]}'s room"
            if accepted:
                if room_id not in OPEN_ROOMS:
                    OPEN_ROOMS[room_id] = {"id": room_id, "users": [LOBBY[inviter_ws]]}
                room = OPEN_ROOMS[room_id]
                if LOBBY[ws] not in room["users"]:
                    room["users"].append(LOBBY[ws])
                # Update USERS_IN_ROOM for all room members
                ws_list = [w for w, name in LOBBY.items() if name in room["users"]]
                for w in ws_list:
                    USERS_IN_ROOM.add(w)
                    await w.send(
                        json.dumps({"type": "room_joined", "usernames": room["users"]})
                    )
                await notify_lobby()
            # Remove invitee from inviter's invite set
            INVITES[inviter_ws].discard(ws)
            if not INVITES[inviter_ws]:
                INVITES.pop(inviter_ws)
    elif data.get("type") == "create_room":  # If the message is to create a room
        # Room name is <username>'s room
        room_id = f"{LOBBY[ws]}'s room"
        # Create the room
        OPEN_ROOMS[room_id] = {"id": room_id, "users": [LOBBY[ws]]}
        USERS_IN_ROOM.add(ws)  # Mark creator as in room
        # If this is a manual room creation, allow anyone to join (clear invitees)
        ROOM_INVITEES[room_id] = set()
        # Notify creator
        await ws.send(json.dumps({"type": "room_joined", "usernames": [LOBBY[ws]]}))
        await notify_lobby()  # Update lobby for all
    elif data.get("type") == "join_room":  # If the message is to join a room
        room_id = data.get("room_id")  # Get the room ID
        room = OPEN_ROOMS.get(room_id)  # Get the room info
        allowed = False
        if room:
            # Robustly extract creator's username from room_id
            if room_id.endswith("'s room"):
                inviter = room_id.rsplit("'s room", 1)[0]
                inviter = inviter.rstrip()
            else:
                inviter = None
            if LOBBY[ws] == inviter:
                allowed = True
            elif not ROOM_INVITEES.get(room_id):
                allowed = True  # Open room
            elif LOBBY[ws] in ROOM_INVITEES.get(room_id, set()):
                allowed = True  # Was invited (even if declined)
        if room and allowed and LOBBY[ws] not in room["users"]:
            room["users"].append(LOBBY[ws])  # Add the joining user
            ws_list = [w for w, name in LOBBY.items() if name in room["users"]]
            for w in ws_list:
                USERS_IN_ROOM.add(w)  # Mark all as in room
                await w.send(
                    json.dumps({"type": "room_joined", "usernames": room["users"]})
                )  # Notify all
            await notify_lobby()  # Update lobby for all
        elif room and not allowed:
            await ws.send(
                json.dumps(
                    {
                        "type": "room_join_denied",
                        "reason": "You are not invited to this room.",
                    }
                )
            )  # Notify user they can't join
    elif data.get("type") == "leave_room":  # If the message is to leave a room
        name = LOBBY.get(ws)  # Get the username
        USERS_IN_ROOM.discard(ws)  # Remove from in-room set
        # Remove user from any open room
        for room_id, room in list(
            OPEN_ROOMS.items()
        ):  # Remove user from all open rooms
            if name in room["users"]:
                room["users"].remove(name)
                # Notify remaining users in the room
                ws_list = [w for w, n in LOBBY.items() if n in room["users"]]
                for w in ws_list:
                    await w.send(
                        json.dumps({"type": "room_update", "usernames": room["users"]})
                    )
                if not room["users"]:
                    del OPEN_ROOMS[room_id]
                    ROOM_INVITEES.pop(room_id, None)
        await ws.send(json.dumps({"type": "room_left"}))  # Notify leaver
        await notify_lobby()  # Update lobby for all


# =========================================
#         CONNECTION HANDLER
# =========================================
async def handler(ws):  # Main connection handler for each client
    print(f"[SERVER] New socket connection: {ws.remote_address}")  # Log new connection
    try:
        name = await ws.recv()  # Receive username from client
        print(f"[SERVER] New client joined: {name}")  # Log join
        LOBBY[ws] = name  # Store username for this websocket
        USERS.add(ws)  # Add websocket to USERS set
        await notify_lobby()  # Notify all users of lobby state
        # Listen for messages from this client
        async for msg in ws:
            data = json.loads(msg)  # Parse message as JSON
            await handle_message(ws, data)  # Handle the message
    except Exception as e:
        print(f"Error: {e}")  # Log any errors
    finally:
        USERS.discard(ws)  # Remove websocket from USERS set
        LOBBY.pop(ws, None)  # Remove from LOBBY dict
        INVITES.pop(ws, None)  # Remove any pending invites
        USERS_IN_ROOM.discard(ws)  # Remove from in-room set
        # Remove user from any open room
        for room_id, room in list(OPEN_ROOMS.items()):
            if name in room["users"]:
                room["users"].remove(name)
                if not room["users"]:
                    del OPEN_ROOMS[room_id]
        await notify_lobby()  # Notify all users of lobby state


# =========================================
#         SERVER ENTRY POINT
# =========================================
async def main():  # Main server entry point
    # Start WebSocket server
    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")  # Log server start
        await asyncio.Future()  # Run forever


if __name__ == "__main__":  # If this script is run directly
    asyncio.run(main())  # Start the server
