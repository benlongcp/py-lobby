from PyQt5 import QtWidgets
import asyncio
import json


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
