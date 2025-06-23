import json
from PyQt5 import QtWidgets
import asyncio


async def handle_ws_messages(ws, lobby):
    async for msg in ws:
        data = json.loads(msg)
        if data.get("type") == "lobby_update":
            users = data.get("users", [])
            rooms = data.get("open_rooms", [])
            lobby.update_users(users)
            lobby.update_rooms(rooms)
        elif data.get("type") == "invite_received":
            from_user = data.get("from")
            reply = QtWidgets.QMessageBox.question(
                lobby,
                "Invitation",
                f"You have been invited by {from_user}! Accept?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if reply == QtWidgets.QMessageBox.Yes:
                await ws.send(
                    json.dumps(
                        {"type": "invite_response", "from": from_user, "accepted": True}
                    )
                )
            else:
                await ws.send(
                    json.dumps(
                        {
                            "type": "invite_response",
                            "from": from_user,
                            "accepted": False,
                        }
                    )
                )
        elif data.get("type") == "invite_result":
            from_user = data.get("from")
            accepted = data.get("accepted")
            if accepted:
                QtWidgets.QMessageBox.information(
                    lobby, "Invite Accepted", f"{from_user} accepted your invitation!"
                )
                await ws.send(json.dumps({"type": "enter_room"}))
            else:
                QtWidgets.QMessageBox.information(
                    lobby, "Invite Declined", f"{from_user} declined your invitation."
                )
        elif data.get("type") == "room_joined":
            usernames = data.get("usernames", [])
            lobby.open_room(usernames)
        elif data.get("type") == "room_update":
            usernames = data.get("usernames", [])
            if hasattr(lobby, "room_window") and lobby.room_window.isVisible():
                lobby.room_window.update_user_list(usernames)
        elif data.get("type") == "room_left":
            if hasattr(lobby, "room_window") and lobby.room_window.isVisible():
                lobby.room_window.close()
                lobby.show()
        elif data.get("type") == "room_join_denied":
            reason = data.get("reason", "You cannot join this room.")
            QtWidgets.QMessageBox.warning(lobby, "Join Room Denied", reason)
        # ...handle other message types...
