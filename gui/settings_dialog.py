import os
import sys
import winreg
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QCheckBox, QFileDialog, QFrame, QScrollArea, QSpinBox)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

class SettingsView(QWidget):
    def __init__(self, scheduler, main_window):
        super().__init__()
        self.scheduler = scheduler
        self.main_window = main_window
        
        self.settings = QSettings("GodAzrail", "SSHBackupManager")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Заголовок
        header_layout = QVBoxLayout()
        title = QLabel("Настройки")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setStyleSheet("color: white; padding-bottom: 5px;")
        header_layout.addWidget(title)
        
        # Прокручиваемая область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        content_layout.setContentsMargins(0, 10, 20, 10)
        
        # --- ГЛАВНЫЙ МАКЕТ: ДВЕ КОЛОНКИ ---
        columns_layout = QHBoxLayout()
        columns_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        columns_layout.setSpacing(25)
        
        col_left = QVBoxLayout()
        col_left.setAlignment(Qt.AlignTop)
        col_left.setSpacing(20)
        
        col_right = QVBoxLayout()
        col_right.setAlignment(Qt.AlignTop)
        col_right.setSpacing(20)
        
        # --- БЛОК 1: СИСТЕМА (Левая колонка) ---
        system_group = self.create_group("Системные настройки")
        
        self.cb_autostart = QCheckBox("Автозапуск вместе с Windows")
        self.cb_autostart.setChecked(self.is_autostart_enabled())
        self.cb_autostart.toggled.connect(self.toggle_autostart)
        self.style_checkbox(self.cb_autostart)
        
        self.cb_start_minimized = QCheckBox("Запускать свернутым в системный трей")
        self.cb_start_minimized.setChecked(self.settings.value("start_minimized", True, type=bool))
        self.cb_start_minimized.toggled.connect(lambda v: self.settings.setValue("start_minimized", v))
        self.style_checkbox(self.cb_start_minimized)

        interval_layout = QHBoxLayout()
        lbl_interval = QLabel("Интервал проверки сети (сек):")
        lbl_interval.setStyleSheet("color: #a9b1d6; font-size: 14px; font-weight: bold;")
        
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(5, 3600)
        self.spin_interval.setValue(self.settings.value("check_interval", 60, type=int))
        self.spin_interval.setCursor(Qt.PointingHandCursor)
        self.spin_interval.setStyleSheet("""
            QSpinBox { 
                background-color: #1a1b26; color: white; 
                border: 1px solid #3b4261; border-radius: 6px; 
                padding: 4px 8px; font-size: 14px; font-weight: bold; min-width: 70px;
            }
            QSpinBox::up-button, QSpinBox::down-button { background-color: #3b4261; border-radius: 3px; margin: 1px; }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover { background-color: #7aa2f7; }
        """)
        self.spin_interval.valueChanged.connect(lambda v: self.settings.setValue("check_interval", v))
        
        interval_layout.addWidget(lbl_interval)
        interval_layout.addStretch()
        interval_layout.addWidget(self.spin_interval)

        system_group.layout().addWidget(self.cb_autostart)
        system_group.layout().addWidget(self.cb_start_minimized)
        system_group.layout().addLayout(interval_layout)
        
        # --- БЛОК 2: УВЕДОМЛЕНИЯ (Левая колонка) ---
        notif_group = self.create_group("Уведомления")
        
        self.cb_notify_success = QCheckBox("Уведомления об успешных бэкапах")
        self.cb_notify_success.setChecked(self.settings.value("notify_success", True, type=bool))
        self.cb_notify_success.toggled.connect(lambda v: self.settings.setValue("notify_success", v))
        self.style_checkbox(self.cb_notify_success)

        self.cb_notify_error = QCheckBox("Уведомления об ошибках соединения")
        self.cb_notify_error.setChecked(self.settings.value("notify_error", True, type=bool))
        self.cb_notify_error.toggled.connect(lambda v: self.settings.setValue("notify_error", v))
        self.style_checkbox(self.cb_notify_error)
        
        notif_group.layout().addWidget(self.cb_notify_success)
        notif_group.layout().addWidget(self.cb_notify_error)
        
        # --- БЛОК 3: ХРАНИЛИЩЕ (Правая колонка) ---
        folder_group = self.create_group("Хранилище")
        
        lbl_folder = QLabel("Папка для сохранения бэкапов по умолчанию:")
        lbl_folder.setStyleSheet("color: #a9b1d6; font-size: 14px; font-weight: bold;")
        
        folder_row = QHBoxLayout()
        folder_row.setSpacing(10)
        
        default_path = os.path.join(os.path.expanduser("~"), "SSH_Backups")
        saved_path = self.settings.value("default_backup_dir", default_path)
        
        self.lbl_path = QLabel(saved_path)
        self.lbl_path.setStyleSheet("color: white; background-color: #1a1b26; padding: 8px 12px; border-radius: 6px; border: 1px solid #3b4261;")
        
        btn_browse = QPushButton("Изменить")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setStyleSheet("""
            QPushButton { background-color: #3b4261; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #7aa2f7; color: #1a1b26; }
        """)
        btn_browse.clicked.connect(self.choose_folder)
        
        folder_row.addWidget(self.lbl_path, stretch=1)
        folder_row.addWidget(btn_browse)
        
        folder_group.layout().addWidget(lbl_folder)
        folder_group.layout().addLayout(folder_row)
        
        # Распределяем по колонкам
        col_left.addWidget(system_group)
        col_left.addWidget(notif_group)
        
        col_right.addWidget(folder_group)
        
        columns_layout.addLayout(col_left, stretch=1)
        columns_layout.addLayout(col_right, stretch=1)
        
        content_layout.addLayout(columns_layout)
        scroll.setWidget(content_widget)
        
        layout.addLayout(header_layout)
        layout.addWidget(scroll)

    def create_group(self, title_text):
        """Создает стилизованную карточку"""
        group = QFrame()
        group.setStyleSheet("""
            QFrame { background-color: #1e2030; border-radius: 10px; border: 1px solid #292e42; }
        """)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(20, 15, 20, 20)
        group_layout.setSpacing(12)
        
        title = QLabel(title_text)
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("color: #7aa2f7; border: none; background: transparent;")
        group_layout.addWidget(title)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #3b4261; border: none; height: 1px; margin-bottom: 5px;")
        group_layout.addWidget(line)
        
        return group

    def style_checkbox(self, cb):
        cb.setCursor(Qt.PointingHandCursor)
        cb.setStyleSheet("""
            QCheckBox { color: #a9b1d6; font-size: 14px; font-weight: bold; background: transparent; border: none; padding-top: 2px; padding-bottom: 2px; }
            QCheckBox:hover { color: white; }
            QCheckBox::indicator { width: 20px; height: 20px; border-radius: 5px; border: 2px solid #3b4261; background: #1a1b26; }
            QCheckBox::indicator:hover { border: 2px solid #7aa2f7; }
            QCheckBox::indicator:checked { background: #7aa2f7; border: 2px solid #7aa2f7; 
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMWExYjI2IiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiLz48L3N2Zz4=);
            }
        """)

    def is_autostart_enabled(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, "SSHBackupManager")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False

    def toggle_autostart(self, checked):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            app_name = "SSHBackupManager"
            if checked:
                exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
                start_minimized = self.settings.value("start_minimized", True, type=bool)
                args = ' --minimized' if start_minimized else ''
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"{args}')
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            from gui.toast import Toast
            Toast(self.main_window, f"Не удалось изменить автозапуск: {e}", is_error=True)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для бэкапов", self.lbl_path.text())
        if folder:
            folder = os.path.normpath(folder)
            self.lbl_path.setText(folder)
            self.settings.setValue("default_backup_dir", folder)