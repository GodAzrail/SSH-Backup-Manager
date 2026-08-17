import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QSpinBox, QMessageBox, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from database.db_manager import DBManager

class SettingsView(QWidget):
    def __init__(self, scheduler, parent=None):
        super().__init__(parent)
        self.scheduler = scheduler
        self.db = DBManager()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        title = QLabel("Глобальные настройки")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setStyleSheet("QLabel { color: white; background: transparent; border: none; }")
        layout.addWidget(title)
        
        container = QFrame()
        container.setStyleSheet("""
            QFrame { 
                background-color: #24283b; 
                border-radius: 15px; 
                border: 1px solid #3b4261; 
            }
        """)
        
        cont_layout = QVBoxLayout(container)
        cont_layout.setContentsMargins(25, 25, 25, 25)
        cont_layout.setSpacing(20)

        label_style = "QLabel { color: #a9b1d6; font-size: 14px; font-weight: bold; border: none; background: transparent; }"
        input_style = """
            QLineEdit, QSpinBox { 
                background-color: #1a1b26; color: #c0caf5; 
                border: 1px solid #3b4261; border-radius: 6px; 
                padding: 8px; font-size: 13px; 
            }
            QLineEdit:focus, QSpinBox:focus { border: 1px solid #7aa2f7; }
        """
        
        # --- Папка бэкапов ---
        path_layout = QHBoxLayout()
        path_lbl = QLabel("Стандартная папка:")
        path_lbl.setFixedWidth(160)
        path_lbl.setStyleSheet(label_style)
        
        self.path_input = QLineEdit()
        self.path_input.setStyleSheet(input_style)
        
        browse_btn = QPushButton("Обзор...")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet("""
            QPushButton { background-color: #7aa2f7; color: #1a1b26; padding: 8px 15px; border-radius: 6px; font-weight: bold; border: none; } 
            QPushButton:hover { background-color: #8db0f8; }
        """)
        browse_btn.clicked.connect(self.browse_path)
        
        path_layout.addWidget(path_lbl)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_btn)

        # --- Тайм-аут ---
        timeout_layout = QHBoxLayout()
        timeout_lbl = QLabel("Тайм-аут SSH (сек):")
        timeout_lbl.setFixedWidth(160)
        timeout_lbl.setStyleSheet(label_style)
        
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(5, 300)
        self.timeout_input.setStyleSheet(input_style)
        self.timeout_input.setFixedWidth(100)
        
        timeout_layout.addWidget(timeout_lbl)
        timeout_layout.addWidget(self.timeout_input)
        timeout_layout.addStretch()

        cont_layout.addLayout(path_layout)
        cont_layout.addLayout(timeout_layout)
        
        # --- Кнопка сохранения ---
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить настройки")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedSize(200, 40)
        save_btn.setStyleSheet("""
            QPushButton { background-color: #9ece6a; color: #1a1b26; border-radius: 6px; font-weight: bold; font-size: 14px; border: none; } 
            QPushButton:hover { background-color: #b3df7a; }
        """)
        save_btn.clicked.connect(self.save_settings)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)

        cont_layout.addLayout(btn_layout)
        
        layout.addWidget(container)
        layout.addStretch() # Прижимаем плашку к верху

        self.load_settings()

    def load_settings(self):
        # Универсальная попытка загрузить настройки (чтобы не сломалось от разных названий методов БД)
        try:
            if hasattr(self.db, 'get_settings'):
                settings = self.db.get_settings()
                if settings:
                    if isinstance(settings, tuple) or isinstance(settings, list):
                        self.path_input.setText(str(settings[0]))
                        self.timeout_input.setValue(int(settings[1]))
                    elif isinstance(settings, dict):
                        self.path_input.setText(settings.get('path', 'C:\\Backups'))
                        self.timeout_input.setValue(int(settings.get('timeout', 10)))
        except Exception as e:
            print(f"Не удалось загрузить настройки: {e}")
            self.path_input.setText("C:\\Backups")
            self.timeout_input.setValue(10)

    def browse_path(self):
        d = QFileDialog.getExistingDirectory(self, "Выберите папку", self.path_input.text())
        if d:
            self.path_input.setText(os.path.normpath(d))

    def save_settings(self):
        path = self.path_input.text()
        timeout = self.timeout_input.value()
        
        # Универсальная попытка сохранить настройки
        try:
            if hasattr(self.db, 'save_settings'):
                self.db.save_settings(path, timeout)
            elif hasattr(self.db, 'update_settings'):
                self.db.update_settings(path, timeout)
        except Exception as e:
             print(f"Не удалось сохранить настройки: {e}")
             
        if self.scheduler:
            self.scheduler.reload_jobs()
            
        QMessageBox.information(self, "Успех", "Настройки успешно сохранены!")