import logging
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QPushButton, 
                             QLabel, QScrollArea, QHBoxLayout, QMessageBox, QProgressBar, 
                             QFrame, QListWidget, QListWidgetItem, QGraphicsDropShadowEffect,
                             QSystemTrayIcon, QMenu, QAction, qApp, QStyle, QStackedWidget, QTextEdit)
# ИСПРАВЛЕНИЕ: Добавлен QTimer в импорты
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QEvent, QObject, QTimer 
from PyQt5.QtGui import QFont
from database.db_manager import DBManager
from gui.server_panel import ServerPanel 
from gui.history_window import HistoryView, FlowWidget 
from gui.settings_dialog import SettingsView
from core.backup_manager import BackupThread
from core.ssh_manager import SSHManager
from utils.encryption import decrypt_password

STYLESHEET = """
QMainWindow { background-color: #1a1b26; }
QListWidget { background-color: #1e2030; border: none; outline: none; color: #a9b1d6; font-size: 14px; font-weight: bold; padding: 10px 0px; }
QListWidget::item { padding: 15px 20px; border-radius: 8px; margin: 3px 10px; }
QListWidget::item:selected { background-color: #3b4261; color: white; border-left: 3px solid #7aa2f7; }
QListWidget::item:hover:!selected { background-color: #2a2d3d; }
QPushButton { border-radius: 8px; padding: 8px 12px; font-weight: bold; border: none; }
#BtnPrimary { background-color: #7aa2f7; color: #1a1b26; font-size: 13px; min-width: 150px; padding: 10px 20px; }
#BtnPrimary:hover { background-color: #8db0f8; }
#BtnPrimary:pressed { background-color: #6b8fd8; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background: #3b4261; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #4a5175; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""

class LogSignal(QObject):
    msg = pyqtSignal(str)

class QtLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.emitter = LogSignal()

    def emit(self, record):
        msg = self.format(record)
        self.emitter.msg.emit(msg)

class StatusCheckThread(QThread):
    status_signal = pyqtSignal(bool)
    def __init__(self, server_data):
        super().__init__()
        self.server_data = server_data
    def run(self):
        try:
            host, port, user, pwd_blob, key_path = self.server_data[2], self.server_data[3], self.server_data[4], self.server_data[5], self.server_data[6]
            password = decrypt_password(pwd_blob) if pwd_blob else None
            manager = SSHManager(host, int(port), user, password, key_path)
            self.status_signal.emit(manager.test_connection())
        except Exception:
            self.status_signal.emit(False)

class ServerCard(QFrame):
    def __init__(self, server_data, delete_cb, edit_cb, history_cb):
        super().__init__()
        self.server_data = server_data
        self.setFixedSize(300, 150) 
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
        
        self.setStyleSheet("""
            QFrame { background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #2a2d3d, stop: 1 #24283b); border-radius: 15px; border: 1px solid #3b4261; }
            QFrame:hover { background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #32364a, stop: 1 #2f354d); border: 1px solid #4a5175; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        top_layout = QHBoxLayout()
        top_layout.setSpacing(12)
        
        icon = QLabel("UB")
        icon.setFixedSize(45, 45)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFont(QFont("Arial", 14, QFont.Bold))
        icon.setStyleSheet("QLabel { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #ff9e64, stop: 1 #f7768e); color: #1a1b26; border-radius: 22px; font-weight: bold; min-width: 45px; max-width: 45px; min-height: 45px; max-height: 45px; }")
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        name = QLabel(server_data[1])
        name.setFont(QFont("Arial", 13, QFont.Bold))
        name.setStyleSheet("QLabel { color: white; background: transparent; border: none; }")
        
        host_info = f"{server_data[4]}@{server_data[2]}"
        if server_data[3] and int(server_data[3]) != 22:  
            host_info += f":{server_data[3]}"
        
        sub = QLabel(f"SSH • {host_info}")
        sub.setFont(QFont("Arial", 10))
        sub.setStyleSheet("QLabel { color: #565f89; background: transparent; border: none; }")
        
        auto_backup = bool(server_data[9])
        if not auto_backup:
            schedule_text = "Авто-бэкап: Выключен"
        else:
            if len(server_data) >= 15:
                schedule_type = server_data[12]
                if schedule_type == 'interval':
                    schedule_text = f"Авто-бэкап: каждые {server_data[10]} мин."
                else:
                    cron_day = server_data[13]
                    day_map_ru = {"*": "Ежедневно", "mon": "По понедельникам", "tue": "По вторникам", "wed": "По средам", "thu": "По четвергам", "fri": "По пятницам", "sat": "По субботам", "sun": "По воскресеньям"}
                    schedule_text = f"Авто-бэкап: {day_map_ru.get(cron_day, cron_day)} в {server_data[14]}"
            else:
                schedule_text = f"Авто-бэкап: каждые {server_data[10]} мин."

        schedule_label = QLabel(schedule_text)
        schedule_label.setFont(QFont("Arial", 9))
        schedule_label.setStyleSheet("QLabel { color: #7aa2f7; background: transparent; border: none; }")

        text_layout.addWidget(name)
        text_layout.addWidget(sub)
        text_layout.addWidget(schedule_label) 
        
        top_layout.addWidget(icon)
        top_layout.addLayout(text_layout)
        top_layout.addStretch()
        
        self.status_dot = QLabel("●")
        self.status_dot.setFixedSize(15, 15)
        self.status_dot.setAlignment(Qt.AlignCenter)
        self.set_dot_color("#565f89") 
        top_layout.addWidget(self.status_dot)
        
        self.check_thread = StatusCheckThread(self.server_data)
        self.check_thread.status_signal.connect(self.update_network_status)
        self.check_thread.start()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.backup_btn = QPushButton("Бэкап")
        self.backup_btn.setCursor(Qt.PointingHandCursor)
        self.backup_btn.setFont(QFont("Arial", 10, QFont.Bold))
        self.backup_btn.setStyleSheet("""
            QPushButton { background-color: #9ece6a; color: #1a1b26; padding: 6px 10px; border-radius: 6px; min-width: 65px; }
            QPushButton:hover { background-color: #b3df7a; }
            QPushButton:disabled { background-color: #3b4261; color: #a9b1d6; }
        """)
        self.backup_btn.clicked.connect(self.start_backup)

        self.history_btn = QPushButton("История")
        self.history_btn.setCursor(Qt.PointingHandCursor)
        self.history_btn.setFont(QFont("Arial", 10, QFont.Bold))
        self.history_btn.setStyleSheet("""
            QPushButton { background-color: #3b4261; color: white; padding: 6px 10px; border-radius: 6px; }
            QPushButton:hover { background-color: #7aa2f7; color: #1a1b26; }
        """)
        self.history_btn.clicked.connect(lambda: history_cb(self.server_data))
        
        edit_btn = QPushButton("⚙")
        edit_btn.setCursor(Qt.PointingHandCursor)
        edit_btn.setFixedSize(30, 30)
        edit_btn.setFont(QFont("Arial", 14))
        edit_btn.setStyleSheet("QPushButton { background-color: rgba(59, 66, 97, 0.5); color: #a9b1d6; font-size: 14px; border-radius: 6px; padding: 0px; text-align: center; } QPushButton:hover { background-color: #3b4261; color: white; }")
        edit_btn.clicked.connect(lambda: edit_cb(self.server_data))

        del_btn = QPushButton("✕")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setFixedSize(30, 30)
        del_btn.setFont(QFont("Arial", 12))
        del_btn.setStyleSheet("QPushButton { background-color: rgba(247, 118, 142, 0.2); color: #f7768e; font-size: 12px; border-radius: 6px; padding: 0px; text-align: center; } QPushButton:hover { background-color: #f7768e; color: #1a1b26; }")
        del_btn.clicked.connect(lambda: delete_cb(self.server_data[0]))
        
        btn_layout.addWidget(self.backup_btn)
        btn_layout.addWidget(self.history_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.progress.setStyleSheet("QProgressBar { background-color: #1a1b26; border-radius: 3px; border: none; } QProgressBar::chunk { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #7aa2f7, stop: 1 #9ece6a); border-radius: 3px; }")

        layout.addLayout(top_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(self.progress)
        
        # --- ТАЙМЕР ДЛЯ БЭКАПА ---
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer_display)
        self.elapsed_seconds = 0

    def set_dot_color(self, color):
        self.status_dot.setStyleSheet(f"QLabel {{ color: {color}; font-size: 12px; background: transparent; border: none; min-width: 15px; max-width: 15px; min-height: 15px; max-height: 15px; }}")

    def update_network_status(self, is_online):
        color = "#9ece6a" if is_online else "#f7768e" 
        self.set_dot_color(color)
        self.status_dot.setToolTip("Сервер онлайн" if is_online else "Сервер недоступен")

    # Обновление текста на кнопке во время бэкапа
    def update_timer_display(self):
        self.elapsed_seconds += 1
        mins = self.elapsed_seconds // 60
        secs = self.elapsed_seconds % 60
        self.backup_btn.setText(f"⏳ {mins:02}:{secs:02}")

    def start_backup(self):
        self.backup_btn.setEnabled(False)
        self.elapsed_seconds = 0
        self.backup_btn.setText("⏳ 00:00")
        self.timer.start(1000) # Запускаем таймер (1 раз в секунду)
        
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.thread = BackupThread(self.server_data)
        self.thread.progress_signal.connect(self.progress.setValue)
        self.thread.finished_signal.connect(self.on_finish)
        self.thread.start()

    def on_finish(self, success, msg):
        self.timer.stop() # Останавливаем таймер
        self.backup_btn.setEnabled(True)
        self.backup_btn.setText("Бэкап")
        self.progress.setVisible(False)
        self.progress.setValue(0)
        if success: QMessageBox.information(self, "Успех", msg)
        else: QMessageBox.critical(self, "Ошибка", msg)

class MainWindow(QMainWindow):
    def __init__(self, scheduler):
        super().__init__()
        self.scheduler = scheduler
        self.setWindowTitle("SSH Backup Manager")
        self.resize(1590, 700)
        self.setMinimumSize(1590, 700)
        self.setStyleSheet(STYLESHEET)
        self.db = DBManager()
        
        self.gui_logger = QtLogHandler()
        self.gui_logger.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
        logging.getLogger().addHandler(self.gui_logger)
        self.gui_logger.emitter.msg.connect(self.append_log)
        
        self.init_tray_icon()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(240)
        sidebar_container.setStyleSheet("QWidget { background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #1e2030, stop: 1 #24283b); border-right: 1px solid #3b4261; }")
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(0)
        
        logo = QLabel("SSH Backup\nManager")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFont(QFont("Arial", 16, QFont.Bold))
        logo.setStyleSheet("QLabel { color: white; padding: 20px; background: transparent; border: none; }")
        sidebar_layout.addWidget(logo)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("QFrame { color: #3b4261; background-color: #3b4261; border: none; height: 1px; margin: 10px 20px; }")
        sidebar_layout.addWidget(separator)
        
        self.sidebar = QListWidget()
        self.sidebar.setStyleSheet("QListWidget { background: transparent; border: none; outline: none; }")
        
        item_hosts = QListWidgetItem("Серверы")
        item_logs = QListWidgetItem("Логи")
        item_settings = QListWidgetItem("Настройки")
        
        item_hosts.setSizeHint(QSize(200, 50))
        item_logs.setSizeHint(QSize(200, 50))
        item_settings.setSizeHint(QSize(200, 50))
        
        self.sidebar.addItem(item_hosts)
        self.sidebar.addItem(item_logs)
        self.sidebar.addItem(item_settings)
        self.sidebar.setCurrentItem(item_hosts)
        self.sidebar.itemClicked.connect(self.handle_sidebar)
        
        sidebar_layout.addWidget(self.sidebar)
        sidebar_layout.addStretch()
        version_label = QLabel("v1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("QLabel { color: #565f89; font-size: 11px; background: transparent; border: none; padding: 10px; }")
        sidebar_layout.addWidget(version_label)

        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)

        self.servers_page = QWidget()
        servers_layout = QVBoxLayout(self.servers_page)
        servers_layout.setContentsMargins(0, 0, 0, 0)
        servers_layout.setSpacing(20)
        
        header = QHBoxLayout()
        header.setSpacing(15)
        
        title_container = QVBoxLayout()
        title = QLabel("Серверы")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setStyleSheet("QLabel { color: white; background: transparent; border: none; }")
        subtitle = QLabel("Управление вашими SSH серверами")
        subtitle.setFont(QFont("Arial", 11))
        subtitle.setStyleSheet("QLabel { color: #565f89; background: transparent; border: none; }")
        title_container.addWidget(title)
        title_container.addWidget(subtitle)
        
        add_btn = QPushButton("+ Добавить сервер")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setObjectName("BtnPrimary")
        add_btn.setFixedSize(180, 40)
        add_btn.setFont(QFont("Arial", 11, QFont.Bold))
        add_btn.clicked.connect(self.open_add_server_panel)
        
        header.addLayout(title_container)
        header.addStretch()
        header.addWidget(add_btn, 0, Qt.AlignVCenter)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        
        self.flow_widget = FlowWidget()
        self.flow_widget.setStyleSheet("background: transparent;")
        self.scroll.setWidget(self.flow_widget)
        
        servers_layout.addLayout(header)
        servers_layout.addWidget(self.scroll)
        self.content_stack.addWidget(self.servers_page) 
        
        self.logs_page = QWidget()
        logs_layout = QVBoxLayout(self.logs_page)
        logs_layout.setContentsMargins(0, 0, 0, 0)
        logs_layout.setSpacing(15)
        
        logs_title = QLabel("Консоль логов")
        logs_title.setFont(QFont("Arial", 28, QFont.Bold))
        logs_title.setStyleSheet("QLabel { color: white; background: transparent; border: none; }")
        
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("""
            QTextEdit {
                background-color: #0f111a; color: #a9b1d6; 
                font-family: 'Consolas', 'Courier New', monospace; 
                font-size: 13px; border: 1px solid #3b4261; 
                border-radius: 8px; padding: 10px;
            }
        """)
        
        logs_layout.addWidget(logs_title)
        logs_layout.addWidget(self.log_console)
        self.content_stack.addWidget(self.logs_page)
        
        self.settings_page = SettingsView(self.scheduler, self)
        self.content_stack.addWidget(self.settings_page)

        self.right_panel = ServerPanel()
        self.right_panel.hide() 
        self.right_panel.saved_signal.connect(self.on_server_saved)
        self.right_panel.closed_signal.connect(self.right_panel.hide)

        main_layout.addWidget(sidebar_container)
        main_layout.addWidget(content_wrapper)
        main_layout.addWidget(self.right_panel)
        
        self.load_servers()

    def append_log(self, text):
        self.log_console.append(text)
        scrollbar = self.log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def open_history_window(self, server_data):
        history_view = HistoryView(server_data[0], server_data[1], self)
        history_view.back_signal.connect(lambda: self.close_history(history_view)) 
        self.content_stack.addWidget(history_view)
        self.content_stack.setCurrentWidget(history_view) 

    def close_history(self, widget):
        self.content_stack.setCurrentIndex(0) 
        self.content_stack.removeWidget(widget)
        widget.deleteLater()

    def open_add_server_panel(self):
        self.right_panel.clear_data()
        self.right_panel.show()

    def open_edit_server_panel(self, data):
        self.right_panel.load_data(data)
        self.right_panel.show()

    def on_server_saved(self):
        self.scheduler.reload_jobs()
        self.load_servers()
        self.right_panel.hide()

    def init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = self.style().standardIcon(QStyle.SP_DriveNetIcon)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("SSH Backup Manager - Работает")

        tray_menu = QMenu()
        restore_action = QAction("Развернуть", self)
        restore_action.triggered.connect(self.show_window)
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.quit_app)

        tray_menu.addAction(restore_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

    def show_window(self):
        self.showNormal() 
        self.activateWindow()

    def quit_app(self):
        qApp.quit()

    def closeEvent(self, event):
        event.ignore() 
        self.hide() 
        self.tray_icon.showMessage("SSH Backup Manager", "Программа продолжает работу в фоновом режиме.", QSystemTrayIcon.Information, 2000)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.hide() 
        super().changeEvent(event)

    def handle_sidebar(self, item):
        if item.text() == "Серверы":
            self.content_stack.setCurrentIndex(0)
        elif item.text() == "Логи":
            self.content_stack.setCurrentIndex(1)
        elif item.text() == "Настройки":
            self.content_stack.setCurrentIndex(2)

    def load_servers(self):
        self.flow_widget.clear() 
        
        servers = self.db.get_all_servers()
        for srv in servers:
            card = ServerCard(srv, self.delete_server_handler, self.open_edit_server_panel, self.open_history_window)
            self.flow_widget.addWidget(card) 

    def delete_server_handler(self, server_id):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Удаление сервера")
        msg_box.setText("Вы уверены, что хотите удалить этот сервер?")
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.button(QMessageBox.Yes).setText("Да, удалить")
        msg_box.button(QMessageBox.No).setText("Отмена")
        msg_box.setStyleSheet("QMessageBox { background-color: #24283b; color: white; } QPushButton { background-color: #3b4261; color: white; padding: 8px 16px; border-radius: 6px; min-width: 80px; } QPushButton:hover { background-color: #4a5175; }")
        
        if msg_box.exec_() == QMessageBox.Yes:
            self.db.delete_server(server_id)
            self.scheduler.reload_jobs()
            self.load_servers()