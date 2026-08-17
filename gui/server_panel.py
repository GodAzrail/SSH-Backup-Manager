from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                             QPushButton, QCheckBox, QHBoxLayout, 
                             QSpinBox, QComboBox, QTimeEdit, QStackedWidget, QLabel, QFrame,
                             QGraphicsDropShadowEffect)
from PyQt5.QtCore import QThread, pyqtSignal, QTime, Qt

# Импортируем наш стильный Toast
from gui.toast import Toast

from core.ssh_manager import SSHManager
from utils.encryption import encrypt_password
from database.db_manager import DBManager

class SSHTestThread(QThread):
    result_signal = pyqtSignal(bool, str)
    def __init__(self, host, port, user, password):
        super().__init__()
        self.host, self.port, self.user, self.password = host, port, user, password

    def run(self):
        try:
            manager = SSHManager(self.host, int(self.port), self.user, self.password)
            if manager.test_connection(): 
                self.result_signal.emit(True, "Подключение успешно установлено!")
            else: 
                self.result_signal.emit(False, "Не удалось подключиться к серверу.")
        except Exception as e:
            self.result_signal.emit(False, f"Ошибка соединения: {str(e)}")

# ОБНОВЛЕНО: Теперь наследуемся от QWidget (прозрачный контейнер)
class ServerPanel(QWidget):
    saved_signal = pyqtSignal()
    closed_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DBManager()
        self.server_id = None 

        self.setObjectName("OuterContainer")
        
        # --- ОБНОВЛЕНО: Настройка прозрачного внешнего контейнера и стилей внутренних элементов ---
        self.setStyleSheet("""
            #OuterContainer { background: transparent; }
            #RightSidebar { 
                background-color: #1e2030; 
                border: 1px solid #3b4261; 
                border-radius: 16px; 
            }
            QLabel { color: #a9b1d6; font-size: 13px; font-weight: bold; background: transparent; border: none; }
            QLineEdit, QSpinBox, QComboBox, QTimeEdit { background-color: #24283b; color: white; border: 1px solid #3b4261; border-radius: 6px; padding: 6px; }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTimeEdit:focus { border: 1px solid #7aa2f7; }
            
            QCheckBox { color: #a9b1d6; font-weight: bold; font-size: 13px; spacing: 10px; }
            QCheckBox::indicator { width: 18px; height: 18px; background-color: #24283b; border: 2px solid #3b4261; border-radius: 4px; }
            QCheckBox::indicator:hover { border: 2px solid #7aa2f7; }
            QCheckBox::indicator:checked { background-color: #9ece6a; border: 2px solid #9ece6a; }
            
            QPushButton { border-radius: 6px; padding: 8px; font-weight: bold; border: none; }
            #BtnPrimary { background-color: #7aa2f7; color: #1a1b26; }
            #BtnPrimary:hover { background-color: #8db0f8; }
            #BtnSuccess { background-color: #9ece6a; color: #1a1b26; }
            #BtnSuccess:hover { background-color: #b3df7a; }
        """)

        # --- ОБНОВЛЕНО: Создаем внутренний закругленный блок ---
        self.inner_frame = QFrame()
        self.inner_frame.setObjectName("RightSidebar")
        self.inner_frame.setFixedWidth(340) # Жесткая фиксация спасает от сжимания во время анимации

        # Добавляем тень для блока
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 8)
        self.inner_frame.setGraphicsEffect(shadow)

        # Располагаем внутренний блок во внешнем контейнере (с отступами)
        outer_layout = QVBoxLayout(self)
        # Отступы: Слева: 15, Сверху: 30, Справа: 30, Снизу: 30
        outer_layout.setContentsMargins(15, 30, 30, 30)
        outer_layout.addWidget(self.inner_frame, 0, Qt.AlignLeft)

        self.day_map = {"Каждый день": "*", "Понедельник": "mon", "Вторник": "tue", "Среда": "wed", "Четверг": "thu", "Пятница": "fri", "Суббота": "sat", "Воскресенье": "sun"}
        self.rev_day_map = {v: k for k, v in self.day_map.items()}

        # Теперь главный layout привязан к INNER FRAME
        main_layout = QVBoxLayout(self.inner_frame)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Шапка
        header = QHBoxLayout()
        header.setContentsMargins(20, 20, 20, 10)
        self.title_lbl = QLabel("Настройка сервера")
        self.title_lbl.setStyleSheet("color: white; font-size: 18px;")
        
        close_btn = QPushButton("→|")
        close_btn.setFixedSize(35, 35)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; color: #f7768e; font-size: 16px; } QPushButton:hover { background: #24283b; }")
        close_btn.clicked.connect(self.closed_signal.emit)
        
        header.addWidget(self.title_lbl)
        header.addStretch()
        header.addWidget(close_btn)
        main_layout.addLayout(header)

        # 2. Форма ввода
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        form_layout = QFormLayout(content_widget)
        form_layout.setContentsMargins(20, 0, 20, 10)

        self.name_input = QLineEdit()
        self.host_input = QLineEdit()
        self.port_input = QLineEdit("22")
        self.user_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.remote_path_input = QLineEdit()
        self.local_path_input = QLineEdit()
        
        self.auto_backup_cb = QCheckBox("Автоматический бекап")
        self.max_backups_spinbox = QSpinBox()
        self.max_backups_spinbox.setRange(0, 100) 

        self.schedule_type_combo = QComboBox()
        self.schedule_type_combo.addItems(["Каждые N минут", "По расписанию"])
        
        self.stack = QStackedWidget()
        self.stack.setFixedHeight(35)
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 10080)
        self.stack.addWidget(self.interval_spinbox)
        
        cron_widget = QWidget()
        cron_layout = QHBoxLayout(cron_widget)
        cron_layout.setContentsMargins(0, 0, 0, 0)
        self.cron_day_combo = QComboBox()
        self.cron_day_combo.addItems(list(self.day_map.keys()))
        self.cron_time_edit = QTimeEdit()
        self.cron_time_edit.setDisplayFormat("HH:mm")
        cron_layout.addWidget(self.cron_day_combo)
        cron_layout.addWidget(self.cron_time_edit)
        self.stack.addWidget(cron_widget)
        
        self.schedule_type_combo.currentIndexChanged.connect(self.stack.setCurrentIndex)

        form_layout.addRow("Название:", self.name_input)
        form_layout.addRow("Хост (IP):", self.host_input)
        form_layout.addRow("Порт:", self.port_input)
        form_layout.addRow("Юзер:", self.user_input)
        form_layout.addRow("Пароль:", self.password_input)
        form_layout.addRow("Путь SSH:", self.remote_path_input)
        form_layout.addRow("Папка ПК:", self.local_path_input)
        form_layout.addRow("Хранить шт:", self.max_backups_spinbox)
        form_layout.addRow(self.auto_backup_cb)
        form_layout.addRow("Режим:", self.schedule_type_combo)
        form_layout.addRow("Время:", self.stack)

        main_layout.addWidget(content_widget)

        # Пружина, сдвигающая кнопки вниз
        main_layout.addStretch(1)

        # 3. Кнопки сохранения внизу
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 10, 20, 20)
        self.test_btn = QPushButton("Тест SSH")
        self.test_btn.setObjectName("BtnPrimary")
        self.test_btn.setCursor(Qt.PointingHandCursor)
        self.test_btn.clicked.connect(self.test_connection)
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("BtnSuccess")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_server)
        
        btn_layout.addWidget(self.test_btn)
        btn_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(btn_layout)

    def clear_data(self):
        self.server_id = None
        self.title_lbl.setText("Новый сервер")
        self.name_input.clear()
        self.host_input.clear()
        self.port_input.setText("22")
        self.user_input.clear()
        self.password_input.clear()
        self.password_input.setPlaceholderText("Пароль")
        self.remote_path_input.clear()
        self.local_path_input.setText(self.db.get_setting('default_backup_path', 'C:\\Backups'))
        self.auto_backup_cb.setChecked(False)
        self.interval_spinbox.setValue(60)
        self.max_backups_spinbox.setValue(3)
        self.schedule_type_combo.setCurrentIndex(0)
        self.cron_time_edit.setTime(QTime(0, 0))

    def load_data(self, data):
        self.server_id = data[0]
        self.title_lbl.setText("Настройки сервера")
        self.name_input.setText(data[1])
        self.host_input.setText(data[2])
        self.port_input.setText(str(data[3]))
        self.user_input.setText(data[4])
        self.password_input.clear()
        self.password_input.setPlaceholderText("Пусто = не менять")
        self.remote_path_input.setText(data[7])
        self.local_path_input.setText(data[8])
        self.auto_backup_cb.setChecked(bool(data[9]))
        self.interval_spinbox.setValue(int(data[10]))
        
        if len(data) >= 15:
            self.max_backups_spinbox.setValue(int(data[11]))
            if data[12] == 'cron':
                self.schedule_type_combo.setCurrentIndex(1)
                self.cron_day_combo.setCurrentText(self.rev_day_map.get(data[13], "Каждый день"))
                h, m = map(int, data[14].split(':'))
                self.cron_time_edit.setTime(QTime(h, m))
            else:
                self.schedule_type_combo.setCurrentIndex(0)

    def test_connection(self):
        host, port, user, password = self.host_input.text(), self.port_input.text(), self.user_input.text(), self.password_input.text()
        
        if not all([host, port, user]):
            Toast(self.window(), "Заполните хост, порт и пользователя!", is_error=True)
            return
            
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Проверка...")
        self.test_thread = SSHTestThread(host, port, user, password)
        self.test_thread.result_signal.connect(self.on_test_finished)
        self.test_thread.start()

    def on_test_finished(self, success, message):
        self.test_btn.setEnabled(True)
        self.test_btn.setText("Тест SSH")
        
        Toast(self.window(), message, is_error=not success)

    def save_server(self):
        name, host, port, user = self.name_input.text(), self.host_input.text(), self.port_input.text(), self.user_input.text()
        password, remote, local = self.password_input.text(), self.remote_path_input.text(), self.local_path_input.text()
        auto, interval = self.auto_backup_cb.isChecked(), self.interval_spinbox.value()
        max_backups = self.max_backups_spinbox.value() 
        schedule_type = 'interval' if self.schedule_type_combo.currentIndex() == 0 else 'cron'
        cron_day = self.day_map[self.cron_day_combo.currentText()]
        cron_time = self.cron_time_edit.time().toString("HH:mm")

        if not all([name, host, port, user, remote, local]):
            Toast(self.window(), "Заполните все обязательные поля!", is_error=True)
            return
        
        enc_password = encrypt_password(password) if password else b""
        
        if self.server_id: 
            self.db.update_server(self.server_id, name, host, int(port), user, enc_password, "", remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time)
            Toast(self.window(), "Настройки сервера обновлены!", is_error=False)
        else: 
            self.db.add_server(name, host, int(port), user, enc_password, "", remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time)
            Toast(self.window(), "Новый сервер успешно добавлен!", is_error=False)
            
        self.saved_signal.emit()