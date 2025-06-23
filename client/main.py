import sys
import asyncio
import websockets
import qasync
from PyQt5 import QtWidgets
from .lobby_window import LobbyWindow
from .dialogs import NamePrompt
from .ws_handler import handle_ws_messages


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
            await asyncio.Future()
            return
    else:
        sys.exit()


if __name__ == "__main__":
    qasync.run(main_async())
