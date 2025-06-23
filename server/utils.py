# Utility functions for the server

import asyncio
import json
from .state import USERS, LOBBY, OPEN_ROOMS, USERS_IN_ROOM


async def notify_lobby():
    if USERS:
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
