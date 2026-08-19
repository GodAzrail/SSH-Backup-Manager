import os
import sys
import time
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem,
                             QFrame, QMenu, QMessageBox, QDialog, QDialogButtonBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import (Qt, QObject, pyqtSlot, pyqtSignal, QThread, QUrl,
                          QPropertyAnimation, QEasingCurve, QSettings, QPoint, QSize)
from PyQt5.QtGui import QColor, QFont, QIcon


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class EditSnippetDialog(QDialog):
    """Диалог для редактирования сниппета"""
    def __init__(self, name, command, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать сниппет")
        self.setFixedSize(400, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e2030;
                color: white;
            }
            QLabel {
                color: #a9b1d6;
            }
            QLineEdit {
                background-color: #1a1b26;
                color: white;
                border: 1px solid #565f89;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #7aa2f7;
            }
            QPushButton {
                background-color: #7aa2f7;
                color: #1a1b26;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #8db0f8;
            }
            QPushButton[text="Отмена"] {
                background-color: #3b4261;
                color: white;
            }
            QPushButton[text="Отмена"]:hover {
                background-color: #565f89;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Поле для названия
        name_label = QLabel("Название:")
        self.name_edit = QLineEdit(name)
        layout.addWidget(name_label)
        layout.addWidget(self.name_edit)

        # Поле для команды
        cmd_label = QLabel("Команда:")
        self.cmd_edit = QLineEdit(command)
        layout.addWidget(cmd_label)
        layout.addWidget(self.cmd_edit)

        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Ok).setText("Сохранить")
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        layout.addWidget(button_box)

    def get_data(self):
        return self.name_edit.text().strip(), self.cmd_edit.text().strip()


class SSHShellThread(QThread):
    data_received = pyqtSignal(str)
    disconnected = pyqtSignal()

    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self.running = True

    def run(self):
        while self.running:
            if self.channel.recv_ready():
                try:
                    data = self.channel.recv(4096).decode('utf-8', errors='ignore')
                    self.data_received.emit(data)
                except Exception:
                    self.disconnected.emit()
                    break
            if self.channel.exit_status_ready():
                self.disconnected.emit()
                break
            time.sleep(0.01)

    def stop(self):
        self.running = False


class TerminalBridge(QObject):
    def __init__(self, ssh_channel):
        super().__init__()
        self.ssh_channel = ssh_channel

    @pyqtSlot(str)
    def send_data(self, data):
        if self.ssh_channel and self.ssh_channel.send_ready():
            self.ssh_channel.send(data.encode('utf-8'))


class TerminalSession(QWidget):
    def __init__(self, ssh_manager, parent=None):
        super().__init__(parent)
        self.ssh_manager = ssh_manager
        self.ssh_channel = self.ssh_manager.invoke_shell()
        self.is_sidebar_open = False

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # --- 1. ТЕРМИНАЛ ---
        self.browser = QWebEngineView(self)
        self.browser.page().setBackgroundColor(QColor(26, 27, 38))
        self.browser.setStyleSheet("background-color: #1a1b26; border: none;")

        self.channel = QWebChannel()
        self.bridge = TerminalBridge(self.ssh_channel)
        self.channel.registerObject("bridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)

        self.browser.loadFinished.connect(self.on_load_finished)
        html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'terminal.html'))
        self.browser.setUrl(QUrl.fromLocalFile(html_path))

        self.layout.addWidget(self.browser)

        # --- 2. ПЛАВАЮЩАЯ КНОПКА ВЫЗОВА САЙДБАРА ---
        self.toggle_btn = QPushButton(self)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setFixedSize(40, 40)

        icon_path = get_resource_path(os.path.join("icos", "sidebar.svg"))
        if not os.path.exists(icon_path):
            icon_path = get_resource_path(os.path.join("icon", "sidebar.svg"))

        if os.path.exists(icon_path):
            self.toggle_btn.setIcon(QIcon(icon_path))
            self.toggle_btn.setIconSize(QSize(22, 22))
        else:
            self.toggle_btn.setText("⚡")

        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e2030;
                border: 1px solid #292e42;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #24283b;
                border: 1px solid #7aa2f7;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_snippets)

        # --- 3. ПЛАВАЮЩИЙ САЙДБАР (СТИЛЬ ADD SERVER) ---
        self.sidebar = QFrame(self)
        self.sidebar.setFixedWidth(360)
        self.sidebar.setObjectName("SidebarMain")

        # Основной фон плавающей карточки
        self.sidebar.setStyleSheet("""
            QFrame#SidebarMain {
                background-color: #1e2030;
                border-radius: 12px;
                border: 1px solid #292e42;
            }
            QLabel { border: none; background: transparent; }
        """)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        sidebar_layout.setSpacing(15)

        # --- ШАПКА САЙДБАРА ---
        header_layout = QHBoxLayout()
        title = QLabel("Сниппеты")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setStyleSheet("color: white;")

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #565f89; border: none; font-size: 14px; font-weight: bold; }
            QPushButton:hover { color: #f7768e; background: rgba(247, 118, 142, 0.2); border-radius: 4px; }
        """)
        self.close_btn.clicked.connect(self.toggle_snippets)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)

        # --- БЛОК 1: СПИСОК КОМАНД ---
        list_group = QFrame()
        list_group.setStyleSheet("QFrame { background-color: #24283b; border-radius: 8px; }")
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(15, 15, 15, 15)
        list_layout.setSpacing(10)

        list_header_layout = QHBoxLayout()
        list_title = QLabel("СОХРАНЕННЫЕ КОМАНДЫ")
        list_title.setStyleSheet("color: #565f89; font-weight: bold; font-size: 10px;")
        list_hint = QLabel("(правый клик - меню)")
        list_hint.setStyleSheet("color: #565f89; font-size: 10px; font-style: italic;")

        list_header_layout.addWidget(list_title)
        list_header_layout.addStretch()
        list_header_layout.addWidget(list_hint)

        self.snippet_list = QListWidget()
        self.snippet_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item {
                background: #1a1b26;
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 6px;
                color: #a9b1d6;
                font-weight: bold;
                border: 1px solid #3b4261;
            }
            QListWidget::item:hover {
                background: #3b4261;
                color: white;
                border: 1px solid #7aa2f7;
            }
            QListWidget::item:selected {
                background: #3b4261;
                border: 1px solid #7aa2f7;
            }
        """)
        self.snippet_list.itemClicked.connect(self.on_snippet_clicked)
        self.snippet_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.snippet_list.customContextMenuRequested.connect(self.show_context_menu)

        list_layout.addLayout(list_header_layout)
        list_layout.addWidget(self.snippet_list)

        # --- БЛОК 2: ДОБАВИТЬ НОВУЮ ---
        add_group = QFrame()
        add_group.setStyleSheet("QFrame { background-color: #24283b; border-radius: 8px; }")
        add_layout = QVBoxLayout(add_group)
        add_layout.setContentsMargins(15, 15, 15, 15)
        add_layout.setSpacing(10)

        add_title = QLabel("ДОБАВИТЬ СНИППЕТ")
        add_title.setStyleSheet("color: #565f89; font-weight: bold; font-size: 10px;")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название (напр: Web Server)")
        self.name_input.setStyleSheet("""
            QLineEdit { background-color: #1a1b26; color: white; border: 1px solid #565f89; border-radius: 4px; padding: 8px; }
            QLineEdit:focus { border: 1px solid #7aa2f7; }
        """)

        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Команда (напр: apt update)")
        self.cmd_input.setStyleSheet("""
            QLineEdit { background-color: #1a1b26; color: white; border: 1px solid #565f89; border-radius: 4px; padding: 8px; }
            QLineEdit:focus { border: 1px solid #7aa2f7; }
        """)

        add_btn = QPushButton("Сохранить команду")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton { background-color: #7aa2f7; color: #1a1b26; border-radius: 6px; padding: 10px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #8db0f8; }
        """)
        add_btn.clicked.connect(self.add_snippet)

        add_layout.addWidget(add_title)
        add_layout.addWidget(self.name_input)
        add_layout.addWidget(self.cmd_input)
        add_layout.addWidget(add_btn)

        sidebar_layout.addLayout(header_layout)
        sidebar_layout.addWidget(list_group)
        sidebar_layout.addWidget(add_group)

        self.load_snippets()

    def resizeEvent(self, event):
        """ Динамическое позиционирование (отступы от краев) """
        super().resizeEvent(event)

        margin = 15

        # Кнопка в правом верхнем углу
        self.toggle_btn.move(self.width() - self.toggle_btn.width() - margin, margin)

        # Высота сайдбара с учетом отступов сверху и снизу
        self.sidebar.setFixedHeight(self.height() - margin * 2)

        # Позиция по X
        if self.is_sidebar_open:
            self.sidebar.move(self.width() - self.sidebar.width() - margin, margin)
        else:
            self.sidebar.move(self.width() + 20, margin)

    def toggle_snippets(self):
        """ Плавная анимация появления плавающей панели """
        self.is_sidebar_open = not self.is_sidebar_open
        margin = 15
        target_x = self.width() - self.sidebar.width() - margin if self.is_sidebar_open else self.width() + 20

        if self.is_sidebar_open:
            self.sidebar.raise_()

        self.anim = QPropertyAnimation(self.sidebar, b"pos")
        self.anim.setDuration(350)
        self.anim.setStartValue(self.sidebar.pos())
        self.anim.setEndValue(QPoint(target_x, margin))
        self.anim.setEasingCurve(QEasingCurve.OutExpo)
        self.anim.start()

    def load_snippets(self):
        settings = QSettings("GodAzrail", "SSHBackupManager")
        snippets_json = settings.value("custom_snippets", "{}")
        try:
            self.snippets = json.loads(snippets_json)
        except:
            self.snippets = {}

        self.snippet_list.clear()
        for name, cmd in self.snippets.items():
            # --- ИЗМЕНЕНО: отображаем только название ---
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, cmd)
            item.setData(Qt.UserRole + 1, name)
            self.snippet_list.addItem(item)

    def add_snippet(self):
        name = self.name_input.text().strip()
        cmd = self.cmd_input.text().strip()
        if name and cmd:
            self.snippets[name] = cmd
            settings = QSettings("GodAzrail", "SSHBackupManager")
            settings.setValue("custom_snippets", json.dumps(self.snippets))
            self.load_snippets()
            self.name_input.clear()
            self.cmd_input.clear()

    def show_context_menu(self, pos):
        item = self.snippet_list.itemAt(pos)
        if item:
            menu = QMenu()
            menu.setStyleSheet("""
                QMenu { background: #24283b; color: white; border: 1px solid #3b4261; border-radius: 4px; padding: 5px; }
                QMenu::item:selected { background: #f7768e; border-radius: 4px; }
            """)

            # --- ДОБАВЛЕНО: кнопка "Редактировать" ---
            edit_action = menu.addAction("✏️ Редактировать")
            delete_action = menu.addAction("🗑 Удалить команду")
            action = menu.exec_(self.snippet_list.mapToGlobal(pos))

            name = item.data(Qt.UserRole + 1)

            if action == delete_action:
                if name in self.snippets:
                    del self.snippets[name]
                    settings = QSettings("GodAzrail", "SSHBackupManager")
                    settings.setValue("custom_snippets", json.dumps(self.snippets))
                    self.load_snippets()

            elif action == edit_action:
                if name in self.snippets:
                    current_cmd = self.snippets[name]
                    dialog = EditSnippetDialog(name, current_cmd, self)
                    if dialog.exec_() == QDialog.Accepted:
                        new_name, new_cmd = dialog.get_data()
                        if new_name and new_cmd:
                            # Удаляем старую запись
                            del self.snippets[name]
                            # Добавляем новую
                            self.snippets[new_name] = new_cmd
                            settings = QSettings("GodAzrail", "SSHBackupManager")
                            settings.setValue("custom_snippets", json.dumps(self.snippets))
                            self.load_snippets()

    def on_snippet_clicked(self, item):
        cmd = item.data(Qt.UserRole)
        if cmd:
            if not cmd.endswith('\n'):
                cmd += '\n'
            self.send_command(cmd)

    def on_load_finished(self, ok):
        if ok:
            self.shell_thread = SSHShellThread(self.ssh_channel)
            self.shell_thread.data_received.connect(self.write_to_terminal)
            self.shell_thread.disconnected.connect(self.on_disconnect)
            self.shell_thread.start()
        else:
            self.browser.setHtml("<h2 style='color:red;'>Ошибка загрузки terminal.html</h2>")

    def write_to_terminal(self, data):
        escaped_data = data.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
        self.browser.page().runJavaScript(f'writeTerm("{escaped_data}");')

    def send_command(self, cmd):
        if self.ssh_channel and self.ssh_channel.send_ready():
            self.ssh_channel.send(cmd.encode('utf-8'))

    def on_disconnect(self):
        self.write_to_terminal("\r\n\r\n[ОТКЛЮЧЕНО] Соединение с сервером закрыто.\r\n")

    def closeEvent(self, event):
        if hasattr(self, 'shell_thread'):
            self.shell_thread.stop()
            self.shell_thread.wait()
        if self.ssh_channel:
            self.ssh_channel.close()
        self.ssh_manager.client.close()
        super().closeEvent(event)