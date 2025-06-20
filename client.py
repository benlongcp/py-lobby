import sys  # Import system-specific parameters and functions
import asyncio  # Import asyncio for async event loop support
import json  # Import json for encoding/decoding messages
from PyQt5 import QtWidgets, QtCore  # Import PyQt5 widgets and core
import websockets  # Import websockets for WebSocket client
import qasync  # Import qasync for Qt/asyncio integration


# -----------------------------------------
# LobbyWindow: Main lobby UI
# -----------------------------------------
class LobbyWindow(QtWidgets.QWidget):  # Define the main lobby window
    def __init__(self, ws, username):  # Constructor
        super().__init__()  # Call parent constructor
        self.ws = ws  # Store WebSocket connection
        self.username = username  # Store this client's username
        self.setWindowTitle(f"Lobby - {username}")  # Set window title
        self.resize(600, 400)  # Set window size
        self.layout = QtWidgets.QHBoxLayout(self)  # Create horizontal layout
        self.user_list = QtWidgets.QListWidget()  # Create user list widget
        self.user_list.setSelectionMode(
            QtWidgets.QAbstractItemView.MultiSelection
        )  # Allow multi-selection
        self.layout.addWidget(self.user_list)  # Add user list to layout
        self.invite_button = QtWidgets.QPushButton("Invite")  # Create invite button
        self.invite_button.setEnabled(False)  # Disable invite button by default
        self.invite_button.clicked.connect(self.invite_selected_user)  # Connect click
        user_col = QtWidgets.QVBoxLayout()  # Create vertical layout for user column
        user_col.addWidget(self.user_list)  # Add user list to column
        user_col.addWidget(self.invite_button)  # Add invite button to column
        user_col.addStretch()  # Add stretch to push widgets up
        user_col_widget = QtWidgets.QWidget()  # Create widget for user column
        user_col_widget.setLayout(user_col)  # Set layout
        self.layout.addWidget(user_col_widget)  # Add user column to main layout
        # Open rooms list (right)
        self.room_list = QtWidgets.QListWidget()
        self.layout.addWidget(self.room_list)
        # Create open room button
        self.create_room_button = QtWidgets.QPushButton("Create Open Room")
        self.create_room_button.clicked.connect(self.create_open_room)
        # Join room button (moved here)
        self.join_room_button = QtWidgets.QPushButton("Join Room")
        self.join_room_button.setEnabled(False)
        self.join_room_button.clicked.connect(self.join_selected_room)
        room_col = QtWidgets.QVBoxLayout()
        room_col.addWidget(self.room_list)
        room_col.addWidget(self.create_room_button)
        room_col.addSpacing(12)  # Add margin between buttons
        room_col.addWidget(self.join_room_button)
        room_col.addStretch()
        room_col_widget = QtWidgets.QWidget()
        room_col_widget.setLayout(room_col)
        self.layout.addWidget(room_col_widget)
        # Connect signals
        self.user_list.itemSelectionChanged.connect(self.on_user_selected)
        self.room_list.itemSelectionChanged.connect(self.on_room_selected)

    def on_user_selected(self):  # Called when user selection changes
        # Enable invite button if at least one other user is selected
        selected = self.user_list.selectedItems()
        valid = [
            item
            for item in selected
            if item.text().replace(" (you)", "") != self.username
        ]
        self.invite_button.setEnabled(bool(valid))

    def update_users(self, users):  # Update the user list
        # Update the user list in the lobby
        self.user_list.clear()  # Clear list
        for user in users:  # For each user
            label = user  # Start with username
            if user == self.username:  # If this is me
                label = f"{user} (you)"  # Mark as (you)
            self.user_list.addItem(label)  # Add to list

    def update_rooms(self, rooms):  # Update the open rooms list
        # Update the open rooms list
        self.room_list.clear()  # Clear list
        for room in rooms:  # For each room
            self.room_list.addItem(room)  # Add to list

    def on_room_selected(self):  # Called when room selection changes
        # Enable join room button if a room is selected
        selected = self.room_list.selectedItems()  # Get selected items
        self.join_room_button.setEnabled(bool(selected))  # Enable if any selected

    def join_selected_room(self):  # Join the selected room
        # Send join_room request to server
        selected = self.room_list.selectedItems()  # Get selected items
        if selected:
            room_id = selected[0].text()  # Get room id
            asyncio.create_task(
                self.ws.send(json.dumps({"type": "join_room", "room_id": room_id}))
            )  # Send join request

    def invite_selected_user(self):  # Invite the selected users
        # Send invite to all selected users (except self)
        selected = self.user_list.selectedItems()
        users = [
            item.text().replace(" (you)", "")
            for item in selected
            if item.text().replace(" (you)", "") != self.username
        ]
        if users:
            asyncio.create_task(
                self.ws.send(json.dumps({"type": "invite", "to": users}))
            )  # Send invite to all selected users

    def create_open_room(self):  # Create a new open room
        # Send create_room request to server
        asyncio.create_task(
            self.ws.send(json.dumps({"type": "create_room"}))
        )  # Send create room request

    def open_room(self, usernames):  # Open the room window
        # Open the room window and hide the lobby
        self.room_window = RoomWindow(
            self.ws, usernames, self.username, self
        )  # Create room window
        self.room_window.show()  # Show room window
        self.hide()  # Hide lobby


# -----------------------------------------
# NamePrompt: Dialog to enter username
# -----------------------------------------
class NamePrompt(QtWidgets.QDialog):  # Username prompt dialog
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enter your name")  # Set dialog title
        self.layout = QtWidgets.QVBoxLayout(self)  # Create layout
        self.input = QtWidgets.QLineEdit()  # Input field
        self.layout.addWidget(self.input)  # Add input to layout
        self.button = QtWidgets.QPushButton("Join Lobby")  # Join button
        self.layout.addWidget(self.button)  # Add button to layout
        self.button.clicked.connect(self.accept)  # Connect click

    def get_name(self):  # Get entered username
        return self.input.text().strip()


# -----------------------------------------
# RoomWindow: UI for a room (2 users)
# -----------------------------------------
class RoomWindow(QtWidgets.QWidget):  # Room window
    def __init__(self, ws, usernames, my_username, lobby):
        super().__init__()
        self.ws = ws  # WebSocket connection
        self.usernames = usernames  # List of usernames in the room
        self.my_username = my_username  # This client's username
        self.lobby = lobby  # Reference to the lobby window
        self.setWindowTitle(f"Room - {', '.join(usernames)}")  # Set window title
        self.resize(300, 200)  # Set window size
        layout = QtWidgets.QVBoxLayout(self)  # Create layout
        self.user_list = QtWidgets.QListWidget()  # User list widget
        self.update_user_list(usernames)  # Populate user list
        layout.addWidget(self.user_list)  # Add user list to layout
        self.leave_button = QtWidgets.QPushButton("Leave Room")  # Leave button
        self.leave_button.clicked.connect(self.leave_room)  # Connect click
        layout.addWidget(self.leave_button)  # Add leave button

    def update_user_list(self, usernames):  # Update user list in room
        # Update the user list in the room
        self.user_list.clear()  # Clear list
        for user in usernames:  # For each user
            label = user  # Start with username
            if user == self.my_username:  # If this is me
                label += " (you)"  # Mark as (you)
            self.user_list.addItem(label)  # Add to list

    def leave_room(self):  # Leave the room
        # Send leave_room request to server and return to lobby
        asyncio.create_task(
            self.ws.send(json.dumps({"type": "leave_room"}))
        )  # Send leave request
        self.close()  # Close room window
        self.lobby.show()  # Show lobby window


# -----------------------------------------
# WebSocket message handler
# -----------------------------------------
async def handle_ws_messages(ws, lobby):  # Handle messages from server
    # Listen for messages from the server and update UI accordingly
    async for msg in ws:  # For each message
        data = json.loads(msg)  # Parse JSON
        if data.get("type") == "lobby_update":  # Lobby update
            users = data.get("users", [])  # Get user list
            rooms = data.get("open_rooms", [])  # Get room list
            lobby.update_users(users)  # Update user list
            lobby.update_rooms(rooms)  # Update room list
        elif data.get("type") == "invite_received":  # Received invite
            from_user = data.get("from")  # Who invited me
            reply = QtWidgets.QMessageBox.question(
                lobby,
                "Invitation",
                f"You have been invited by {from_user}! Accept?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )  # Show accept/decline dialog
            if reply == QtWidgets.QMessageBox.Yes:  # If accepted
                await ws.send(
                    json.dumps(
                        {"type": "invite_response", "from": from_user, "accepted": True}
                    )
                )  # Send accept
            else:  # If declined
                await ws.send(
                    json.dumps(
                        {
                            "type": "invite_response",
                            "from": from_user,
                            "accepted": False,
                        }
                    )
                )  # Send decline
        elif data.get("type") == "invite_result":  # Invite result
            from_user = data.get("from")  # Who responded
            accepted = data.get("accepted")  # Was it accepted?
            if accepted:  # If accepted
                QtWidgets.QMessageBox.information(
                    lobby, "Invite Accepted", f"{from_user} accepted your invitation!"
                )  # Show info
                # Open room for both users
                await ws.send(
                    json.dumps({"type": "enter_room"})
                )  # Request to enter room
            else:  # If declined
                QtWidgets.QMessageBox.information(
                    lobby, "Invite Declined", f"{from_user} declined your invitation."
                )  # Show info
        elif data.get("type") == "room_joined":  # Joined a room
            usernames = data.get("usernames", [])  # Get usernames in room
            lobby.open_room(usernames)  # Open room window
        elif data.get("type") == "room_update":  # Room user list update
            usernames = data.get("usernames", [])  # Get usernames
            if hasattr(lobby, "room_window") and lobby.room_window.isVisible():
                lobby.room_window.update_user_list(usernames)  # Update room user list
        elif data.get("type") == "room_left":  # Left the room
            if hasattr(lobby, "room_window") and lobby.room_window.isVisible():
                lobby.room_window.close()  # Close room window
                lobby.show()  # Show lobby window
        elif data.get("type") == "room_join_denied":  # Join denied
            reason = data.get("reason", "You cannot join this room.")
            QtWidgets.QMessageBox.warning(lobby, "Join Room Denied", reason)
        # ...handle other message types...


# -----------------------------------------
# Main entry point
# -----------------------------------------
async def main_async():  # Main async entry point
    app = QtWidgets.QApplication(sys.argv)  # Create Qt application
    prompt = NamePrompt()  # Create username prompt
    if prompt.exec_() == QtWidgets.QDialog.Accepted:  # If user entered name
        username = prompt.get_name()  # Get username
        if not username:  # If empty
            QtWidgets.QMessageBox.warning(
                None, "Error", "Username cannot be empty."
            )  # Warn
            sys.exit()  # Exit
        async with websockets.connect("ws://localhost:8765") as ws:  # Connect to server
            await ws.send(username)  # Send username
            lobby = LobbyWindow(ws, username)  # Create lobby window
            lobby.show()  # Show lobby
            lobby.update_users([username])  # Show own name immediately
            asyncio.create_task(handle_ws_messages(ws, lobby))  # Start message handler
            await asyncio.Future()  # Keep the coroutine alive
            return
    else:
        sys.exit()  # Exit if dialog cancelled


if __name__ == "__main__":  # If run as main script
    qasync.run(main_async())  # Start the Qt/asyncio event loop
