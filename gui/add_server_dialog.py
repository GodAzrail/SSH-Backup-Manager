from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                             QPushButton, QCheckBox, QMessageBox, QHBoxLayout, 
                             QSpinBox, QComboBox, QTimeEdit, QStackedWidget, QWidget,
                             QRadioButton, QButtonGroup, QFileDialog, QTextEdit)
from PyQt5.QtCore import QThread, pyqtSignal, QTime
from core.ssh_manager import SSHManager
from utils.encryption import encrypt_password
from database.db_manager import DBManager

DIALOG_STYLE = """
QDialog { background-color: #1a1b26; }
QLabel { color: #a9b1d6; font-size: 13px; font-weight: bold; }
QLineEdit, QSpinBox, QComboBox, QTimeEdit, QTextEdit { 
    background-color: #24283b; 
    color: white; 
    border: 1px solid #565f89; 
    border-radius: 4px; 
    padding: 6px; 
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTimeEdit:focus, QTextEdit:focus { border: 1px solid #7aa2f7; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background-color: #24283b; color: white; selection-background-color: #3b4261; }
QCheckBox, QRadioButton { color: #a9b1d6; font-weight: bold; font-size: 13px; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; background-color: #24283b; border: 1px solid #565f89; border-radius: 3px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked { background-color: #7aa2f7; border: 1px solid #7aa2f7; }
QRadioButton::indicator { border-radius: 8px; }
QPushButton { border-radius: 6px; padding: 8px; font-weight: bold; border: none; }
#BtnPrimary { background-color: #7aa2f7; color: #1a1b26; }
#BtnPrimary:hover { background-color: #8db0f8; }
#BtnSecondary { background-color: #3b4261; color: white; }
#BtnSecondary:hover { background-color: #565f89; }
#BtnSuccess { background-color: #9ece6a; color: #1a1b26; }
#BtnSuccess:hover { background-color: #b3df7a; }
"""

class SSHTestThread(QThread):
    result_signal = pyqtSignal(bool, str)
    def __init__(self, host, port, user, password, key_path):
        super().__init__()
        self.host, self.port, self.user, self.password, self.key_path = host, port, user, password, key_path

    def run(self):
        try:
            manager = SSHManager(self.host, int(self.port), self.user, self.password, self.key_path)
            if manager.test_connection(): 
                self.result_signal.emit(True, "Подключение успешно установлено!")
            else: 
                self.result_signal.emit(False, "Не удалось подключиться.")
        except Exception as e:
            self.result_signal.emit(False, f"Ошибка: {str(e)}")


class AddServerDialog(QDialog):
    def __init__(self, parent=None, server_data=None):
        super().__init__(parent)
        self.db = DBManager()
        self.server_data = server_data 
        
        self.setWindowTitle("Настройка сервера" if server_data else "Добавление нового сервера")
        self.setFixedSize(480, 680) 
        self.setStyleSheet(DIALOG_STYLE)

        self.day_map = {
            "Каждый день": "*", "Понедельник": "mon", "Вторник": "tue", 
            "Среда": "wed", "Четверг": "thu", "Пятница": "fri", 
            "Суббота": "sat", "Воскресенье": "sun"
        }
        self.rev_day_map = {v: k for k, v in self.day_map.items()}

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # ОСНОВНЫЕ
        self.name_input = QLineEdit()
        self.host_input = QLineEdit()
        self.port_input = QLineEdit("22")
        self.user_input = QLineEdit()
        self.remote_path_input = QLineEdit()

        # АВТОРИЗАЦИЯ
        self.auth_group = QButtonGroup(self)
        self.radio_pass = QRadioButton("Пароль")
        self.radio_key = QRadioButton("SSH-ключ")
        self.auth_group.addButton(self.radio_pass)
        self.auth_group.addButton(self.radio_key)
        self.radio_pass.setChecked(True)

        auth_type_layout = QHBoxLayout()
        auth_type_layout.addWidget(self.radio_pass)
        auth_type_layout.addWidget(self.radio_key)

        self.auth_stack = QStackedWidget()
        
        # Страница: Пароль
        pass_page = QWidget()
        pass_layout = QVBoxLayout(pass_page)
        pass_layout.setContentsMargins(0, 0, 0, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Оставьте пустым, чтобы не менять" if server_data else "Пароль")
        pass_layout.addWidget(self.password_input)
        
        # Страница: SSH-Ключ
        key_page = QWidget()
        key_layout = QVBoxLayout(key_page)
        key_layout.setContentsMargins(0, 0, 0, 0)
        
        self.key_type_combo = QComboBox()
        self.key_type_combo.addItems(["Файл ключа", "Вставить текст ключа"])
        
        self.key_stack = QStackedWidget()
        self.key_stack.setFixedHeight(80)
        
        key_file_page = QWidget()
        key_file_layout = QHBoxLayout(key_file_page)
        key_file_layout.setContentsMargins(0, 0, 0, 0)
        self.key_file_input = QLineEdit()
        self.key_file_input.setPlaceholderText("Путь к ключу (.pem, .key, .ppk, .pub)")
        self.key_browse_btn = QPushButton("Обзор")
        self.key_browse_btn.setObjectName("BtnSecondary")
        self.key_browse_btn.clicked.connect(self.browse_key_file)
        key_file_layout.addWidget(self.key_file_input)
        key_file_layout.addWidget(self.key_browse_btn)
        
        key_text_page = QWidget()
        key_text_layout = QVBoxLayout(key_text_page)
        key_text_layout.setContentsMargins(0, 0, 0, 0)
        self.key_text_input = QTextEdit()
        self.key_text_input.setPlaceholderText("Вставьте содержимое приватного ключа сюда...")
        key_text_layout.addWidget(self.key_text_input)
        
        self.key_stack.addWidget(key_file_page)
        self.key_stack.addWidget(key_text_page)
        self.key_type_combo.currentIndexChanged.connect(self.key_stack.setCurrentIndex)
        
        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.Password)
        self.passphrase_input.setPlaceholderText("Пароль от ключа (если есть)")
        
        key_layout.addWidget(self.key_type_combo)
        key_layout.addWidget(self.key_stack)
        key_layout.addWidget(self.passphrase_input)

        self.auth_stack.addWidget(pass_page)
        self.auth_stack.addWidget(key_page)
        self.radio_pass.toggled.connect(lambda: self.auth_stack.setCurrentIndex(0))
        self.radio_key.toggled.connect(lambda: self.auth_stack.setCurrentIndex(1))

        # СИНХРОНИЗАЦИЯ
        local_path_layout = QHBoxLayout()
        self.local_path_input = QLineEdit()
        self.local_path_input.setText(self.db.get_setting('default_backup_path', 'C:\\Backups'))
        self.local_browse_btn = QPushButton("Обзор")
        self.local_browse_btn.setObjectName("BtnSecondary")
        self.local_browse_btn.clicked.connect(self.browse_local_path)
        local_path_layout.addWidget(self.local_path_input)
        local_path_layout.addWidget(self.local_browse_btn)
        
        self.auto_backup_cb = QCheckBox("Включить автоматический бекап")
        self.max_backups_spinbox = QSpinBox()
        self.max_backups_spinbox.setRange(0, 100) 
        self.max_backups_spinbox.setValue(3)

        self.schedule_type_combo = QComboBox()
        self.schedule_type_combo.addItems(["Каждые N минут", "Точное время (расписание)"])
        
        self.time_stack = QStackedWidget()
        self.time_stack.setFixedHeight(35)
        
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 10080)
        self.interval_spinbox.setValue(60)
        self.time_stack.addWidget(self.interval_spinbox)
        
        cron_widget = QWidget()
        cron_layout = QHBoxLayout(cron_widget)
        cron_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cron_day_combo = QComboBox()
        self.cron_day_combo.addItems(list(self.day_map.keys()))
        self.cron_time_edit = QTimeEdit()
        self.cron_time_edit.setDisplayFormat("HH:mm")
        self.cron_time_edit.setTime(QTime(0, 0))
        
        cron_layout.addWidget(self.cron_day_combo)
        cron_layout.addWidget(self.cron_time_edit)
        self.time_stack.addWidget(cron_widget)
        
        self.schedule_type_combo.currentIndexChanged.connect(self.time_stack.setCurrentIndex)

        # Сборка формы
        form_layout.addRow("Название:", self.name_input)
        form_layout.addRow("Хост (IP):", self.host_input)
        form_layout.addRow("Порт SSH:", self.port_input)
        form_layout.addRow("Пользователь:", self.user_input)
        form_layout.addRow("Тип авторизации:", auth_type_layout)
        form_layout.addRow("", self.auth_stack)
        form_layout.addRow("Путь на сервере:", self.remote_path_input)
        form_layout.addRow("Папка сохранения:", local_path_layout)
        form_layout.addRow("Хранить бэкапов:", self.max_backups_spinbox)
        form_layout.addRow("Режим расписания:", self.schedule_type_combo)
        form_layout.addRow("Настройка времени:", self.time_stack)
        
        layout.addLayout(form_layout)
        layout.addWidget(self.auto_backup_cb)

        # Заполнение данных при редактировании
        if self.server_data:
            self.name_input.setText(server_data[1])
            self.host_input.setText(server_data[2])
            self.port_input.setText(str(server_data[3]))
            self.user_input.setText(server_data[4])
            self.remote_path_input.setText(server_data[7])
            self.local_path_input.setText(server_data[8])
            self.auto_backup_cb.setChecked(bool(server_data[9]))
            self.interval_spinbox.setValue(int(server_data[10]))
            
            if len(server_data) >= 15:
                self.max_backups_spinbox.setValue(int(server_data[11]))
                s_type = server_data[12]
                c_day = server_data[13]
                c_time = server_data[14]
                if s_type == 'cron':
                    self.schedule_type_combo.setCurrentIndex(1)
                    self.cron_day_combo.setCurrentText(self.rev_day_map.get(c_day, "Каждый день"))
                    h, m = map(int, c_time.split(':'))
                    self.cron_time_edit.setTime(QTime(h, m))

            if len(server_data) >= 16:
                auth_type = server_data[15]
                key_path_val = server_data[6]
                
                if auth_type == 'key':
                    self.radio_key.setChecked(True)
                    if key_path_val and "PRIVATE KEY" in key_path_val:
                        self.key_type_combo.setCurrentIndex(1)
                        self.key_text_input.setPlainText(key_path_val)
                    else:
                        self.key_type_combo.setCurrentIndex(0)
                        self.key_file_input.setText(key_path_val if key_path_val else "")

        btn_layout = QHBoxLayout()
        self.test_btn = QPushButton("Тест подключения")
        self.test_btn.setObjectName("BtnPrimary")
        self.test_btn.clicked.connect(self.test_connection)
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("BtnSuccess")
        self.save_btn.clicked.connect(self.save_server)
        
        btn_layout.addWidget(self.test_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def browse_local_path(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку для бэкапов")
        if path:
            self.local_path_input.setText(path)

    def browse_key_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл ключа", "", "Key files (*.pem *.key *.ppk *.pub);;All files (*.*)")
        if path:
            self.key_file_input.setText(path)

    def validate_key_input(self):
        """Проверяет, не вставил ли пользователь публичный ключ вместо приватного"""
        if self.radio_key.isChecked():
            if self.key_type_combo.currentIndex() == 0:  # Режим файла
                key_path = self.key_file_input.text().strip()
                if key_path.lower().endswith('.pub'):
                    QMessageBox.warning(self, "Ошибка SSH-ключа", 
                                        "Вы выбрали публичный ключ (.pub).\n\n"
                                        "Для подключения к серверу нужен ПРИВАТНЫЙ ключ (обычно это файл без расширения или .pem / .ppk). "
                                        "Публичный ключ (.pub) должен находиться на самом сервере.")
                    return False
            else:  # Режим текста
                key_text = self.key_text_input.toPlainText().strip()
                if key_text.startswith("ssh-rsa") or key_text.startswith("ssh-ed25519") or key_text.startswith("ecdsa-"):
                    QMessageBox.warning(self, "Ошибка SSH-ключа", 
                                        "Вы вставили текст публичного ключа.\n\n"
                                        "Для авторизации требуется ПРИВАТНЫЙ ключ. "
                                        "Его текст выглядит как большой блок символов и обычно начинается со строк '-----BEGIN OPENSSH PRIVATE KEY-----'.")
                    return False
                if key_text and "PRIVATE KEY" not in key_text:
                    QMessageBox.warning(self, "Подозрительный ключ", 
                                        "Вставленный текст не похож на приватный ключ (отсутствует маркер PRIVATE KEY).\n\n"
                                        "Убедитесь, что вы скопировали содержимое приватного ключа полностью, включая первую и последнюю строки с дефисами.")
                    return False
        return True

    def test_connection(self):
        # ИЗМЕНЕНИЕ: Запускаем проверку перед тестом
        if not self.validate_key_input():
            return

        host, port, user = self.host_input.text(), self.port_input.text(), self.user_input.text()
        
        auth_type = 'password' if self.radio_pass.isChecked() else 'key'
        if auth_type == 'password':
            password = self.password_input.text()
            key_path = ""
        else:
            password = self.passphrase_input.text()
            key_path = self.key_file_input.text() if self.key_type_combo.currentIndex() == 0 else self.key_text_input.toPlainText()

        if not all([host, port, user]):
            QMessageBox.warning(self, "Ошибка", "Заполните хост, порт и пользователя!")
            return
            
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Проверка...")
        self.test_thread = SSHTestThread(host, port, user, password, key_path)
        self.test_thread.result_signal.connect(self.on_test_finished)
        self.test_thread.start()

    def on_test_finished(self, success, message):
        self.test_btn.setEnabled(True)
        self.test_btn.setText("Тест подключения")
        if success: QMessageBox.information(self, "Успех", message)
        else: QMessageBox.critical(self, "Ошибка", message)

    def save_server(self):
        # ИЗМЕНЕНИЕ: Запускаем проверку перед сохранением
        if not self.validate_key_input():
            return

        name, host, port, user = self.name_input.text(), self.host_input.text(), self.port_input.text(), self.user_input.text()
        remote, local = self.remote_path_input.text(), self.local_path_input.text()
        auto = self.auto_backup_cb.isChecked()
        max_backups = self.max_backups_spinbox.value() 
        interval = self.interval_spinbox.value()
        
        schedule_type = 'interval' if self.schedule_type_combo.currentIndex() == 0 else 'cron'
        cron_day = self.day_map[self.cron_day_combo.currentText()]
        cron_time = self.cron_time_edit.time().toString("HH:mm")

        if not all([name, host, port, user, remote, local]):
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля!")
            return
            
        auth_type = 'password' if self.radio_pass.isChecked() else 'key'
        key_path_val = ""
        pass_val = self.password_input.text()
        
        if auth_type == 'key':
            pass_val = self.passphrase_input.text()
            if self.key_type_combo.currentIndex() == 0:
                key_path_val = self.key_file_input.text()
            else:
                key_path_val = self.key_text_input.toPlainText()
        
        enc_password = encrypt_password(pass_val) if pass_val else b""
        
        if self.server_data: 
            self.db.update_server(self.server_data[0], name, host, int(port), user, enc_password, key_path_val, remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time, auth_type)
        else: 
            self.db.add_server(name, host, int(port), user, enc_password, key_path_val, remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time, auth_type)
            
        self.accept()