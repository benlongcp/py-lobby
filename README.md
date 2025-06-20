# py-lobby: Python PyQt WebSocket Lobby System

## Structure
- server.py: WebSocket server for lobby, rooms, and chat
- client.py: PyQt client for UI and WebSocket communication

## Features
- Lobby with connected users and open rooms
- Invite users to private rooms (2 users max)
- Accept/decline invitations
- Open rooms (public, joinable)
- Room chat (private or open)
- Leave room to return to lobby

## Requirements
- Python 3.8+
- websockets
- PyQt5

## Install dependencies
pip install websockets PyQt5

## Run server
python server.py

## Run client
python client.py

---

This is a starter scaffold. See server.py and client.py for implementation details.
