import sys
import os
import datetime
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import QIcon

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class NotificationItem(QFrame):
    """Карточка одного уведомления в истории колокольчика"""
    def __init__(self, title, msg, is_error):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #24283b;
                border-radius: 6px;
                border: 1px solid #3b4261;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        top_layout = QHBoxLayout()
        title_color = "#f7768e" if is_error else "#7aa2f7"
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {title_color}; font-weight: bold; font-size: 12px; border: none;")
        
        time_lbl = QLabel(datetime.datetime.now().strftime("%H:%M"))
        time_lbl.setStyleSheet("color: #565f89; font-size: 10px; border: none;")
        
        top_layout.addWidget(title_lbl)
        top_layout.addStretch()
        top_layout.addWidget(time_lbl)
        
        msg_lbl = QLabel(msg)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #a9b1d6; font-size: 11px; border: none;")
        
        layout.addLayout(top_layout)
        layout.addWidget(msg_lbl)

class NotificationPopup(QWidget):
    """Всплывающее окно с последними 5 уведомлениями"""
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedWidth(320)
        self.setStyleSheet("QWidget { background-color: #1e2030; border: 1px solid #292e42; border-radius: 8px; }")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(8)
        
        header = QLabel("Последние уведомления")
        header.setStyleSheet("color: white; font-weight: bold; font-size: 13px; border: none; padding-bottom: 5px;")
        self.main_layout.addWidget(header)
        
        self.items_layout = QVBoxLayout()
        self.items_layout.setSpacing(6)
        self.main_layout.addLayout(self.items_layout)
        
        self.empty_lbl = QLabel("Нет новых уведомлений")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setStyleSheet("color: #565f89; font-size: 12px; border: none; padding: 20px 0;")
        self.items_layout.addWidget(self.empty_lbl)
        
        self.notifications = []

    def add_notification(self, title, msg, is_error):
        self.empty_lbl.hide()
        item = NotificationItem(title, msg, is_error)
        
        self.notifications.insert(0, item)
        self.items_layout.insertWidget(0, item)
        
        if len(self.notifications) > 5:
            old_item = self.notifications.pop()
            self.items_layout.removeWidget(old_item)
            old_item.deleteLater()

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

        layout.addStretch(1)

        self.update_btn = QPushButton("🚀 Доступно обновление!")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setFixedHeight(28)
        self.update_btn.setStyleSheet("""
            QPushButton { 
                background-color: #7aa2f7; 
                color: #1a1b26; 
                border: none;
                border-radius: 6px; 
                padding: 0px 15px; 
                font-weight: bold; 
                font-size: 12px; 
            }
            QPushButton:hover { background-color: #8db0f8; }
            QPushButton:pressed { background-color: #6b8fd8; }
            QPushButton:disabled { background-color: #292e42; color: #565f89; }
        """)
        self.update_btn.hide()
        layout.addWidget(self.update_btn)

        layout.addStretch(1)

        # --- ИСПРАВЛЕННЫЙ КОЛОКОЛЬЧИК (ИКОНКА SVG) ---
        self.btn_bell = QPushButton()
        self.btn_bell.setIcon(QIcon(get_resource_path(os.path.join("icon", "bell.svg"))))
        self.btn_bell.setIconSize(QSize(16, 16))
        self.btn_bell.setFixedSize(45, 40)
        self.btn_bell.setCursor(Qt.PointingHandCursor)
        
        self.btn_bell.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }
            QPushButton:hover {
                background-color: rgba(59, 66, 97, 0.5);
            }
            QPushButton:focus {
                outline: none;
            }
        """)
        self.btn_bell.clicked.connect(self.show_notifications)
        
        # Индикатор новых уведомлений
        self.badge = QLabel(self.btn_bell)
        self.badge.setFixedSize(8, 8)
        self.badge.setStyleSheet("background-color: #f7768e; border-radius: 4px;")
        self.badge.move(26, 10)
        self.badge.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.badge.hide()
        
        self.popup = NotificationPopup(self.parent_window)

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

        layout.addWidget(self.btn_bell)
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)

    def add_history(self, title, msg, is_error):
        self.popup.add_notification(title, msg, is_error)
        if self.popup.isHidden():
            self.badge.show()

    def show_notifications(self):
        self.badge.hide()
        pos = self.btn_bell.mapToGlobal(QPoint(0, self.btn_bell.height()))
        x = pos.x() - self.popup.width() + self.btn_bell.width()
        self.popup.move(x, pos.y() + 5)
        self.popup.show()

    def toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()