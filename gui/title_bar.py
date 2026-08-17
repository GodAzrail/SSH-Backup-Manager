from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
            QPushButton {
                background: transparent;
                border: none;
                color: #a9b1d6;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton#BtnClose:hover {
                background-color: #f7768e;
                color: #1a1b26;
            }
            QPushButton.WindowButton:hover {
                background-color: rgba(59, 66, 97, 0.5);
                color: white;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Заполняем пустое пространство слева
        layout.addStretch()

        # Кнопки управления окном
        self.btn_minimize = QPushButton("—")
        self.btn_minimize.setProperty("class", "WindowButton")
        self.btn_minimize.setFixedSize(45, 40)
        self.btn_minimize.setCursor(Qt.PointingHandCursor)
        self.btn_minimize.clicked.connect(self.parent_window.showMinimized)

        self.btn_maximize = QPushButton("🗖")
        self.btn_maximize.setProperty("class", "WindowButton")
        self.btn_maximize.setFixedSize(45, 40)
        self.btn_maximize.setCursor(Qt.PointingHandCursor)
        self.btn_maximize.clicked.connect(self.toggle_maximize)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("BtnClose")
        self.btn_close.setFixedSize(45, 40)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.parent_window.close)

        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)

    def toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()