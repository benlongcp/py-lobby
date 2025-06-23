# Message handler logic for the server

from .state import USERS, LOBBY, OPEN_ROOMS, INVITES, USERS_IN_ROOM, ROOM_INVITEES
from .utils import notify_lobby
import json


async def handle_message(ws, data):
    if data.get("type") == "invite":
        to_users = data.get("to")
        if not isinstance(to_users, list):
            to_users = [to_users] if to_users else []
        if ws not in INVITES:
            INVITES[ws] = set()
        room_id = f"{LOBBY[ws]}'s room"
        if room_id not in ROOM_INVITEES:
            ROOM_INVITEES[room_id] = set()
        for to_user in to_users:
            for ws2, uname in LOBBY.items():
                if uname == to_user and ws2 != ws and ws2 not in INVITES[ws]:
                    INVITES[ws].add(ws2)
                    ROOM_INVITEES[room_id].add(uname)
                    await ws2.send(
                        json.dumps({"type": "invite_received", "from": LOBBY[ws]})
                    )
    elif data.get("type") == "invite_response":
        from_user = data.get("from")
        accepted = data.get("accepted")
        inviter_ws = None
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
                ws_list = [w for w, name in LOBBY.items() if name in room["users"]]
                for w in ws_list:
                    USERS_IN_ROOM.add(w)
                    await w.send(
                        json.dumps({"type": "room_joined", "usernames": room["users"]})
                    )
                await notify_lobby()
            INVITES[inviter_ws].discard(ws)
            if not INVITES[inviter_ws]:
                INVITES.pop(inviter_ws)
    elif data.get("type") == "create_room":
        room_id = f"{LOBBY[ws]}'s room"
        OPEN_ROOMS[room_id] = {"id": room_id, "users": [LOBBY[ws]]}
        USERS_IN_ROOM.add(ws)
        ROOM_INVITEES[room_id] = set()
        await ws.send(json.dumps({"type": "room_joined", "usernames": [LOBBY[ws]]}))
        await notify_lobby()
    elif data.get("type") == "join_room":
        room_id = data.get("room_id")
        room = OPEN_ROOMS.get(room_id)
        allowed = False
        if room:
            if room_id.endswith("'s room"):
                inviter = room_id.rsplit("'s room", 1)[0]
                inviter = inviter.rstrip()
            else:
                inviter = None
            if LOBBY[ws] == inviter:
                allowed = True
            elif not ROOM_INVITEES.get(room_id):
                allowed = True
            elif LOBBY[ws] in ROOM_INVITEES.get(room_id, set()):
                allowed = True
        if room and allowed and LOBBY[ws] not in room["users"]:
            room["users"].append(LOBBY[ws])
            ws_list = [w for w, name in LOBBY.items() if name in room["users"]]
            for w in ws_list:
                USERS_IN_ROOM.add(w)
                await w.send(
                    json.dumps({"type": "room_joined", "usernames": room["users"]})
                )
            await notify_lobby()
        elif room and not allowed:
            await ws.send(
                json.dumps(
                    {
                        "type": "room_join_denied",
                        "reason": "You are not invited to this room.",
                    }
                )
            )
    elif data.get("type") == "leave_room":
        name = LOBBY.get(ws)
        USERS_IN_ROOM.discard(ws)
        for room_id, room in list(OPEN_ROOMS.items()):
            if name in room["users"]:
                room["users"].remove(name)
                ws_list = [w for w, n in LOBBY.items() if n in room["users"]]
                for w in ws_list:
                    await w.send(
                        json.dumps({"type": "room_update", "usernames": room["users"]})
                    )
                if not room["users"]:
                    del OPEN_ROOMS[room_id]
                    ROOM_INVITEES.pop(room_id, None)
        await ws.send(json.dumps({"type": "room_left"}))
        await notify_lobby()
