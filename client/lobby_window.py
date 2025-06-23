from PyQt5 import QtWidgets
import asyncio
import json
from .room_window import RoomWindow


class LobbyWindow(QtWidgets.QWidget):
    def __init__(self, ws, username):
        super().__init__()
        self.ws = ws
        self.username = username
        self.setWindowTitle(f"Lobby - {username}")
        self.resize(600, 400)
        self.layout = QtWidgets.QHBoxLayout(self)
        self.user_list = QtWidgets.QListWidget()
        self.user_list.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.layout.addWidget(self.user_list)
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
        self.room_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.room_list)
        self.create_room_button = QtWidgets.QPushButton("Create Open Room")
        self.create_room_button.clicked.connect(self.create_open_room)
        self.join_room_button = QtWidgets.QPushButton("Join Room")
        self.join_room_button.setEnabled(False)
        self.join_room_button.clicked.connect(self.join_selected_room)
        room_col = QtWidgets.QVBoxLayout()
        room_col.addWidget(self.room_list)
        room_col.addWidget(self.create_room_button)
        room_col.addSpacing(12)
        room_col.addWidget(self.join_room_button)
        room_col.addStretch()
        room_col_widget = QtWidgets.QWidget()
        room_col_widget.setLayout(room_col)
        self.layout.addWidget(room_col_widget)
        self.user_list.itemSelectionChanged.connect(self.on_user_selected)
        self.room_list.itemSelectionChanged.connect(self.on_room_selected)

    def on_user_selected(self):
        selected = self.user_list.selectedItems()
        valid = [
            item
            for item in selected
            if item.text().replace(" (you)", "") != self.username
        ]
        self.invite_button.setEnabled(bool(valid))

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

    def on_room_selected(self):
        selected = self.room_list.selectedItems()
        self.join_room_button.setEnabled(bool(selected))

    def join_selected_room(self):
        selected = self.room_list.selectedItems()
        if selected:
            room_id = selected[0].text()
            asyncio.create_task(
                self.ws.send(json.dumps({"type": "join_room", "room_id": room_id}))
            )

    def invite_selected_user(self):
        selected = self.user_list.selectedItems()
        users = [
            item.text().replace(" (you)", "")
            for item in selected
            if item.text().replace(" (you)", "") != self.username
        ]
        if users:
            asyncio.create_task(
                self.ws.send(json.dumps({"type": "invite", "to": users}))
            )

    def create_open_room(self):
        asyncio.create_task(self.ws.send(json.dumps({"type": "create_room"})))

    def open_room(self, usernames):
        self.room_window = RoomWindow(self.ws, usernames, self.username, self)
        self.room_window.show()
        self.hide()
