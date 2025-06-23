from PyQt5 import QtWidgets


class NamePrompt(QtWidgets.QDialog):
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
