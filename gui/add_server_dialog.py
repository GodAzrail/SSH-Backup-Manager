from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                             QPushButton, QCheckBox, QMessageBox, QHBoxLayout, 
                             QSpinBox, QComboBox, QTimeEdit, QStackedWidget, QWidget)
from PyQt5.QtCore import QThread, pyqtSignal, QTime
from core.ssh_manager import SSHManager
from utils.encryption import encrypt_password
from database.db_manager import DBManager

DIALOG_STYLE = """
QDialog { background-color: #1a1b26; }
QLabel { color: #a9b1d6; font-size: 13px; font-weight: bold; }
QLineEdit, QSpinBox, QComboBox, QTimeEdit { 
    background-color: #24283b; 
    color: white; 
    border: 1px solid #565f89; 
    border-radius: 4px; 
    padding: 6px; 
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTimeEdit:focus { border: 1px solid #7aa2f7; }
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView { background-color: #24283b; color: white; selection-background-color: #3b4261; }
QCheckBox { color: #a9b1d6; font-weight: bold; font-size: 13px; }
QCheckBox::indicator { width: 16px; height: 16px; background-color: #24283b; border: 1px solid #565f89; border-radius: 3px; }
QCheckBox::indicator:checked { background-color: #7aa2f7; border: 1px solid #7aa2f7; }
QPushButton { border-radius: 6px; padding: 8px; font-weight: bold; border: none; }
#BtnPrimary { background-color: #7aa2f7; color: #1a1b26; }
#BtnPrimary:hover { background-color: #8db0f8; }
#BtnSuccess { background-color: #9ece6a; color: #1a1b26; }
#BtnSuccess:hover { background-color: #b3df7a; }
"""

class SSHTestThread(QThread):
    result_signal = pyqtSignal(bool, str)
    def __init__(self, host, port, user, password):
        super().__init__()
        self.host, self.port, self.user, self.password = host, port, user, password

    def run(self):
        try:
            manager = SSHManager(self.host, int(self.port), self.user, self.password)
            if manager.test_connection(): self.result_signal.emit(True, "Подключение успешно установлено!")
            else: self.result_signal.emit(False, "Не удалось подключиться.")
        except Exception as e:
            self.result_signal.emit(False, f"Ошибка: {str(e)}")

class AddServerDialog(QDialog):
    def __init__(self, parent=None, server_data=None):
        super().__init__(parent)
        self.db = DBManager()
        self.server_data = server_data 
        
        self.setWindowTitle("Настройка сервера" if server_data else "Добавление нового сервера")
        self.setFixedSize(450, 600) 
        self.setStyleSheet(DIALOG_STYLE)

        self.day_map = {
            "Каждый день": "*", "Понедельник": "mon", "Вторник": "tue", 
            "Среда": "wed", "Четверг": "thu", "Пятница": "fri", 
            "Суббота": "sat", "Воскресенье": "sun"
        }
        self.rev_day_map = {v: k for k, v in self.day_map.items()}

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.host_input = QLineEdit()
        self.port_input = QLineEdit("22")
        self.user_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Оставьте пустым, чтобы не менять" if server_data else "Пароль")
        self.remote_path_input = QLineEdit()
        self.local_path_input = QLineEdit()
        self.local_path_input.setText(self.db.get_setting('default_backup_path', 'C:\\Backups'))
        
        self.auto_backup_cb = QCheckBox("Включить автоматический бекап")
        self.max_backups_spinbox = QSpinBox()
        self.max_backups_spinbox.setRange(0, 100) 
        self.max_backups_spinbox.setValue(3)

        self.schedule_type_combo = QComboBox()
        self.schedule_type_combo.addItems(["Каждые N минут", "Точное время (расписание)"])
        
        self.stack = QStackedWidget()
        self.stack.setFixedHeight(35) # <--- ИСПРАВЛЕНИЕ ДИЗАЙНА (ограничение высоты)
        
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 10080)
        self.interval_spinbox.setValue(60)
        self.stack.addWidget(self.interval_spinbox)
        
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
        self.stack.addWidget(cron_widget)
        
        self.schedule_type_combo.currentIndexChanged.connect(self.stack.setCurrentIndex)

        form_layout.addRow("Название:", self.name_input)
        form_layout.addRow("Хост (IP):", self.host_input)
        form_layout.addRow("Порт SSH:", self.port_input)
        form_layout.addRow("Пользователь:", self.user_input)
        form_layout.addRow("Пароль:", self.password_input)
        form_layout.addRow("Путь на сервере:", self.remote_path_input)
        form_layout.addRow("Папка сохранения:", self.local_path_input)
        form_layout.addRow("Хранить бэкапов:", self.max_backups_spinbox)
        form_layout.addRow("Режим расписания:", self.schedule_type_combo)
        form_layout.addRow("Настройка времени:", self.stack)
        
        layout.addLayout(form_layout)
        layout.addWidget(self.auto_backup_cb)

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

    def test_connection(self):
        host, port, user, password = self.host_input.text(), self.port_input.text(), self.user_input.text(), self.password_input.text()
        if not all([host, port, user]):
            QMessageBox.warning(self, "Ошибка", "Заполните хост, порт и пользователя!")
            return
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Проверка...")
        self.test_thread = SSHTestThread(host, port, user, password)
        self.test_thread.result_signal.connect(self.on_test_finished)
        self.test_thread.start()

    def on_test_finished(self, success, message):
        self.test_btn.setEnabled(True)
        self.test_btn.setText("Тест подключения")
        if success: QMessageBox.information(self, "Успех", message)
        else: QMessageBox.critical(self, "Ошибка", message)

    def save_server(self):
        name, host, port, user = self.name_input.text(), self.host_input.text(), self.port_input.text(), self.user_input.text()
        password, remote, local = self.password_input.text(), self.remote_path_input.text(), self.local_path_input.text()
        auto = self.auto_backup_cb.isChecked()
        max_backups = self.max_backups_spinbox.value() 
        interval = self.interval_spinbox.value()
        
        schedule_type = 'interval' if self.schedule_type_combo.currentIndex() == 0 else 'cron'
        cron_day = self.day_map[self.cron_day_combo.currentText()]
        cron_time = self.cron_time_edit.time().toString("HH:mm")

        if not all([name, host, port, user, remote, local]):
            QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля!")
            return
        
        enc_password = encrypt_password(password) if password else b""
        
        if self.server_data: 
            self.db.update_server(self.server_data[0], name, host, int(port), user, enc_password, "", remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time)
        else: 
            self.db.add_server(name, host, int(port), user, enc_password, "", remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time)
            
        self.accept()