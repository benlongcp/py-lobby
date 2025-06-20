import sys
import asyncio
import json
from PyQt5 import QtWidgets, QtCore
import websockets
import qasync


class LobbyWindow(QtWidgets.QWidget):
    def __init__(self, ws, username):
        super().__init__()
        self.ws = ws
        self.username = username
        self.setWindowTitle(f"Lobby - {username}")
        self.resize(600, 400)
        self.layout = QtWidgets.QHBoxLayout(self)
        # User list
        self.user_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.user_list)
        # Invite button
        self.invite_button = QtWidgets.QPushButton("Invite")
        self.invite_button.setEnabled(False)
        self.invite_button.clicked.connect(self.invite_selected_user)
        user_col = QtWidgets.QVBoxLayout()
        user_col.addWidget(self.user_list)
        user_col.addWidget(self.invite_button)
        user_col.addStretch()
        user_col_widget = QtWidgets.QWidget()
        user_col_widget.setLayout(user_col)
        self.layout.addWidget(user_col_widget)
        # Open rooms list
        self.room_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.room_list)
        # Create open room button
        self.create_room_button = QtWidgets.QPushButton("Create Open Room")
        self.create_room_button.clicked.connect(self.create_open_room)
        room_col = QtWidgets.QVBoxLayout()
        room_col.addWidget(self.room_list)
        room_col.addWidget(self.create_room_button)
        room_col.addStretch()
        room_col_widget = QtWidgets.QWidget()
        room_col_widget.setLayout(room_col)
        self.layout.addWidget(room_col_widget)
        # Connect signals
        self.user_list.itemSelectionChanged.connect(self.on_user_selected)

    def on_user_selected(self):
        selected = self.user_list.selectedItems()
        if selected and selected[0].text().replace(" (you)", "") != self.username:
            self.invite_button.setEnabled(True)
        else:
            self.invite_button.setEnabled(False)

    def update_users(self, users):
        self.user_list.clear()
        for user in users:
            label = user
            if user == self.username:
                label = f"{user} (you)"
            self.user_list.addItem(label)

    def update_rooms(self, rooms):
        self.room_list.clear()
        for room in rooms:
            self.room_list.addItem(room)
        self.room_list.itemSelectionChanged.connect(self.on_room_selected)
        self.join_room_button = getattr(self, "join_room_button", None)
        if not self.join_room_button:
            self.join_room_button = QtWidgets.QPushButton("Join Room")
            self.join_room_button.setEnabled(False)
            self.join_room_button.clicked.connect(self.join_selected_room)
            self.layout.addWidget(self.join_room_button)

    def on_room_selected(self):
        selected = self.room_list.selectedItems()
        if selected:
            self.join_room_button.setEnabled(True)
        else:
            self.join_room_button.setEnabled(False)

    def invite_selected_user(self):
        selected = self.user_list.selectedItems()
        if selected:
            user = selected[0].text().replace(" (you)", "")
            asyncio.create_task(
                self.ws.send(json.dumps({"type": "invite", "to": user}))
            )

    def create_open_room(self):
        asyncio.create_task(self.ws.send(json.dumps({"type": "create_room"})))

    def join_selected_room(self):
        selected = self.room_list.selectedItems()
        if selected:
            room_id = selected[0].text()
            asyncio.create_task(
                self.ws.send(json.dumps({"type": "join_room", "room_id": room_id}))
            )

    def open_room(self, usernames):
        self.room_window = RoomWindow(self.ws, usernames, self.username, self)
        self.room_window.show()
        self.hide()


class NamePrompt(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enter your name")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.input = QtWidgets.QLineEdit()
        self.layout.addWidget(self.input)
        self.button = QtWidgets.QPushButton("Join Lobby")
        self.layout.addWidget(self.button)
        self.button.clicked.connect(self.accept)

    def get_name(self):
        return self.input.text().strip()


class RoomWindow(QtWidgets.QWidget):
    def __init__(self, ws, usernames, my_username, lobby):
        super().__init__()
        self.ws = ws
        self.usernames = usernames
        self.my_username = my_username
        self.lobby = lobby
        self.setWindowTitle(f"Room - {', '.join(usernames)}")
        self.resize(300, 200)
        layout = QtWidgets.QVBoxLayout(self)
        self.user_list = QtWidgets.QListWidget()
        self.update_user_list(usernames)
        layout.addWidget(self.user_list)
        self.leave_button = QtWidgets.QPushButton("Leave Room")
        self.leave_button.clicked.connect(self.leave_room)
        layout.addWidget(self.leave_button)

    def update_user_list(self, usernames):
        self.user_list.clear()
        for user in usernames:
            label = user
            if user == self.my_username:
                label += " (you)"
            self.user_list.addItem(label)

    def leave_room(self):
        asyncio.create_task(self.ws.send(json.dumps({"type": "leave_room"})))
        self.close()
        self.lobby.show()


async def handle_ws_messages(ws, lobby):
    room_window = None
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
                # Open room for both users
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
        # ...handle other message types...


async def main_async():
    app = QtWidgets.QApplication(sys.argv)
    prompt = NamePrompt()
    if prompt.exec_() == QtWidgets.QDialog.Accepted:
        username = prompt.get_name()
        if not username:
            QtWidgets.QMessageBox.warning(None, "Error", "Username cannot be empty.")
            sys.exit()
        async with websockets.connect("ws://localhost:8765") as ws:
            await ws.send(username)
            lobby = LobbyWindow(ws, username)
            lobby.show()
            lobby.update_users([username])
            asyncio.create_task(handle_ws_messages(ws, lobby))
            await asyncio.Future()  # Keep the coroutine alive
            return
    else:
        sys.exit()


if __name__ == "__main__":
    qasync.run(main_async())
