import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QCheckBox, QSpinBox, QComboBox, 
                             QTimeEdit, QLabel, QFrame, QGraphicsDropShadowEffect, 
                             QRadioButton, QButtonGroup, QFileDialog, QScrollArea,
                             QTextEdit)
from PyQt5.QtCore import QThread, pyqtSignal, QTime, Qt, QSettings

from gui.toast import Toast
from core.ssh_manager import SSHManager
from utils.encryption import encrypt_password, decrypt_password
from database.db_manager import DBManager

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
                self.result_signal.emit(False, "Не удалось подключиться к серверу.")
        except Exception as e:
            self.result_signal.emit(False, f"Ошибка соединения: {str(e)}")


class ServerPanel(QWidget):
    saved_signal = pyqtSignal()
    closed_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DBManager()
        self.server_id = None 

        self.setObjectName("OuterContainer")
        
        self.setStyleSheet("""
            #OuterContainer { background: transparent; }
            #RightSidebar { 
                background-color: #1a1b26; 
                border: 1px solid #292e42; 
                border-radius: 12px; 
            }
            QLabel { color: #a9b1d6; font-size: 12px; font-weight: bold; background: transparent; border: none; }
            
            QLineEdit, QSpinBox, QComboBox, QTimeEdit, QTextEdit { 
                background-color: #15161e; 
                color: white; 
                border: 1px solid #292e42; 
                border-radius: 6px; 
                padding: 7px 10px; 
                font-size: 12px; 
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTimeEdit:focus, QTextEdit:focus { 
                border: 1px solid #7aa2f7; 
                background-color: #1e2030;
            }
            
            QCheckBox, QRadioButton { color: #a9b1d6; font-weight: bold; font-size: 12px; spacing: 6px; }
            QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; background-color: #15161e; border: 1px solid #3b4261; border-radius: 4px; }
            QRadioButton::indicator { border-radius: 8px; }
            QCheckBox::indicator:hover, QRadioButton::indicator:hover { border: 1px solid #7aa2f7; }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked { background-color: #7aa2f7; border: 1px solid #7aa2f7; }
            
            QPushButton { border-radius: 6px; padding: 8px; font-weight: bold; border: none; font-size: 12px;}
            #BtnPrimary { background-color: #3b4261; color: white; }
            #BtnPrimary:hover { background-color: #4a5175; }
            #BtnSuccess { background-color: #7aa2f7; color: #1a1b26; }
            #BtnSuccess:hover { background-color: #8db0f8; }
            
            #MainScroll { border: none; background: transparent; }
            QScrollBar:vertical { width: 4px; background: transparent; margin: 0px; }
            QScrollBar::handle:vertical { background: #3b4261; border-radius: 2px; }
            QScrollBar::handle:vertical:hover { background: #565f89; }
        """)

        self.inner_frame = QFrame()
        self.inner_frame.setObjectName("RightSidebar")
        self.inner_frame.setFixedWidth(350) 

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 5)
        self.inner_frame.setGraphicsEffect(shadow)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(15, 20, 25, 20)
        outer_layout.addWidget(self.inner_frame, 0, Qt.AlignLeft)

        self.day_map = {"Каждый день": "*", "Понедельник": "mon", "Вторник": "tue", "Среда": "wed", "Четверг": "thu", "Пятница": "fri", "Суббота": "sat", "Воскресенье": "sun"}
        self.rev_day_map = {v: k for k, v in self.day_map.items()}
        self.cron_rows_list = [] 

        main_layout = QVBoxLayout(self.inner_frame)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(15, 15, 15, 5)
        self.title_lbl = QLabel("Добавить сервер")
        self.title_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; color: #565f89; font-size: 14px; padding: 0;} QPushButton:hover { color: #f7768e; background: rgba(247, 118, 142, 0.1); border-radius: 13px;}")
        close_btn.clicked.connect(self.closed_signal.emit)
        
        header.addWidget(self.title_lbl)
        header.addStretch()
        header.addWidget(close_btn)
        main_layout.addLayout(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("MainScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        
        content_layout = QVBoxLayout(self.scroll_content)
        content_layout.setContentsMargins(15, 5, 15, 15)
        content_layout.setSpacing(10) 
        
        # --- БЛОК 1: ОСНОВНЫЕ ---
        b1, l1 = self.create_block("ОСНОВНЫЕ")
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название (например: Web Server)")
        
        row_host = QHBoxLayout()
        row_host.setSpacing(8)
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("IP адрес или домен")
        self.port_input = QLineEdit("22")
        self.port_input.setPlaceholderText("Порт")
        self.port_input.setFixedWidth(60)
        row_host.addWidget(self.host_input)
        row_host.addWidget(self.port_input)
        
        l1.addWidget(self.name_input)
        l1.addLayout(row_host)
        content_layout.addWidget(b1)

        # --- БЛОК 2: АВТОРИЗАЦИЯ ---
        b2, l2 = self.create_block("АВТОРИЗАЦИЯ")
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Пользователь (root)")
        l2.addWidget(self.user_input)
        
        auth_switch = QHBoxLayout()
        auth_switch.setContentsMargins(2, 2, 2, 2)
        self.radio_pass = QRadioButton("Пароль")
        self.radio_key = QRadioButton("SSH-ключ")
        self.radio_pass.setChecked(True)
        self.radio_pass.toggled.connect(self.toggle_auth_mode)
        
        auth_switch.addWidget(self.radio_pass)
        auth_switch.addWidget(self.radio_key)
        auth_switch.addStretch()
        l2.addLayout(auth_switch)
        
        self.pass_container = QWidget()
        v_pass = QVBoxLayout(self.pass_container)
        v_pass.setContentsMargins(0, 0, 0, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Пароль")
        v_pass.addWidget(self.password_input)
        l2.addWidget(self.pass_container)
        
        # Контейнер для SSH-ключей (Единое поле ввода)
        self.key_container = QWidget()
        v_key = QVBoxLayout(self.key_container)
        v_key.setContentsMargins(0, 0, 0, 0)
        v_key.setSpacing(8)
        
        key_row = QHBoxLayout()
        key_row.setSpacing(8)
        self.key_input = QTextEdit()
        self.key_input.setPlaceholderText("Файл ключа (.pem, .key, .ppk) или текст самого ключа...")
        self.key_input.setFixedHeight(55)
        
        btn_browse_key = QPushButton("Обзор")
        btn_browse_key.setCursor(Qt.PointingHandCursor)
        btn_browse_key.setStyleSheet("background-color: #3b4261; color: white; padding: 7px;")
        btn_browse_key.clicked.connect(self.browse_key)
        
        key_row.addWidget(self.key_input)
        key_row.addWidget(btn_browse_key, alignment=Qt.AlignTop)
        
        self.key_pass_input = QLineEdit()
        self.key_pass_input.setEchoMode(QLineEdit.Password)
        self.key_pass_input.setPlaceholderText("Пароль от ключа (если есть)")
        
        v_key.addLayout(key_row)
        v_key.addWidget(self.key_pass_input)
        
        self.key_container.setVisible(False)
        l2.addWidget(self.key_container)
        
        content_layout.addWidget(b2)

        # --- БЛОК 3: ПУТИ И ПАПКИ ---
        b3, l3 = self.create_block("СИНХРОНИЗАЦИЯ")
        self.remote_path_input = QLineEdit()
        self.remote_path_input.setPlaceholderText("Удаленный путь (на сервере)")
        
        # Локальная папка с кнопкой "Обзор"
        local_row = QHBoxLayout()
        local_row.setSpacing(8)
        self.local_path_input = QLineEdit()
        self.local_path_input.setPlaceholderText("Локальная папка (на ПК)")
        btn_browse_local = QPushButton("Обзор")
        btn_browse_local.setCursor(Qt.PointingHandCursor)
        btn_browse_local.setStyleSheet("background-color: #3b4261; color: white; padding: 7px;")
        btn_browse_local.clicked.connect(self.browse_local_path)
        local_row.addWidget(self.local_path_input)
        local_row.addWidget(btn_browse_local)
        
        l3.addWidget(self.remote_path_input)
        l3.addLayout(local_row)
        content_layout.addWidget(b3)

        # --- БЛОК 4: РАСПИСАНИЕ ---
        b4, l4 = self.create_block("АВТО-БЭКАП")
        
        self.auto_backup_cb = QCheckBox("Включить автоматический бэкап")
        l4.addWidget(self.auto_backup_cb)
        
        self.schedule_container = QWidget()
        self.schedule_container.setVisible(False)
        v_sched = QVBoxLayout(self.schedule_container)
        v_sched.setContentsMargins(0, 10, 0, 0)
        v_sched.setSpacing(12)
        
        row_retention = QHBoxLayout()
        row_retention.setSpacing(10)
        lbl_ret = QLabel("Хранить старые копии (шт):")
        lbl_ret.setStyleSheet("color: #565f89; font-weight: normal;")
        self.max_backups_spinbox = QSpinBox()
        self.max_backups_spinbox.setRange(1, 100)
        self.max_backups_spinbox.setFixedWidth(80)
        
        row_retention.addWidget(lbl_ret)
        row_retention.addWidget(self.max_backups_spinbox)
        row_retention.addStretch() 
        v_sched.addLayout(row_retention)
        
        self.schedule_type_combo = QComboBox()
        self.schedule_type_combo.addItems(["Запуск каждые N минут", "Запуск по расписанию (Cron)"])
        v_sched.addWidget(self.schedule_type_combo)
        
        self.interval_container = QWidget()
        h_int = QHBoxLayout(self.interval_container)
        h_int.setContentsMargins(0, 0, 0, 0)
        h_int.setSpacing(10)
        lbl_int = QLabel("Интервал запуска (мин):")
        lbl_int.setStyleSheet("color: #565f89; font-weight: normal;")
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 10080)
        self.interval_spinbox.setFixedWidth(80)
        h_int.addWidget(lbl_int)
        h_int.addWidget(self.interval_spinbox)
        h_int.addStretch() 
        v_sched.addWidget(self.interval_container)
        
        self.cron_container = QWidget()
        self.cron_container.setVisible(False)
        self.cron_vbox = QVBoxLayout(self.cron_container)
        self.cron_vbox.setContentsMargins(0, 0, 0, 0)
        self.cron_vbox.setSpacing(8)
        
        self.cron_rows_layout = QVBoxLayout()
        self.cron_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.cron_rows_layout.setSpacing(8)
        self.cron_vbox.addLayout(self.cron_rows_layout)
        
        self.btn_add_cron = QPushButton("+ Добавить время")
        self.btn_add_cron.setCursor(Qt.PointingHandCursor)
        self.btn_add_cron.setStyleSheet("QPushButton { background-color: #3b4261; color: white; padding: 6px; } QPushButton:hover { background-color: #4a5175; }")
        self.btn_add_cron.clicked.connect(lambda: self.add_cron_row())
        self.cron_vbox.addWidget(self.btn_add_cron)
        
        v_sched.addWidget(self.cron_container)
        
        l4.addWidget(self.schedule_container)
        content_layout.addWidget(b4)
        
        self.auto_backup_cb.toggled.connect(self.schedule_container.setVisible)
        self.schedule_type_combo.currentIndexChanged.connect(self.toggle_schedule_mode)
        
        content_layout.addStretch(1) 
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # === 3. ПОДВАЛ (ФИКСИРОВАННЫЕ КНОПКИ) ===
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(15, 10, 15, 15)
        footer_layout.setSpacing(8)
        
        self.test_btn = QPushButton("Тест SSH")
        self.test_btn.setObjectName("BtnPrimary")
        self.test_btn.setCursor(Qt.PointingHandCursor)
        self.test_btn.clicked.connect(self.test_connection)
        
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("BtnSuccess")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_server)
        
        footer_layout.addWidget(self.test_btn, stretch=1)
        footer_layout.addWidget(self.save_btn, stretch=1)
        
        main_layout.addLayout(footer_layout)

    def create_block(self, title_text):
        container = QFrame()
        container.setObjectName("BlockFrame")
        container.setStyleSheet("#BlockFrame { background-color: #24283b; border-radius: 10px; border: none; }")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        
        lbl = QLabel(title_text)
        lbl.setStyleSheet("color: #565f89; font-size: 10px; font-weight: bold; text-transform: uppercase;")
        layout.addWidget(lbl)
        
        return container, layout

    def toggle_auth_mode(self):
        is_key = self.radio_key.isChecked()
        self.pass_container.setVisible(not is_key)
        self.key_container.setVisible(is_key)

    def toggle_schedule_mode(self, index):
        self.interval_container.setVisible(index == 0)
        self.cron_container.setVisible(index == 1)

    def add_cron_row(self, day="*", time_str="00:00"):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        
        day_combo = QComboBox()
        day_combo.addItems(list(self.day_map.keys()))
        day_combo.setCurrentText(self.rev_day_map.get(day, "Каждый день"))
        
        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        try:
            h, m = map(int, time_str.split(':'))
            time_edit.setTime(QTime(h, m))
        except:
            time_edit.setTime(QTime(0, 0))
        
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet("QPushButton { background-color: rgba(247, 118, 142, 0.2); color: #f7768e; border-radius: 6px; padding:0;} QPushButton:hover { background-color: #f7768e; color: #1a1b26; }")
        
        row_layout.addWidget(day_combo, stretch=2)
        row_layout.addWidget(time_edit, stretch=1)
        row_layout.addWidget(del_btn)
        
        self.cron_rows_layout.addWidget(row)
        
        row_data = (row, day_combo, time_edit)
        self.cron_rows_list.append(row_data)
        
        del_btn.clicked.connect(lambda: self.remove_cron_row(row_data))

    def remove_cron_row(self, row_data):
        if len(self.cron_rows_list) > 1:
            row_widget, _, _ = row_data
            self.cron_rows_layout.removeWidget(row_widget)
            row_widget.deleteLater()
            self.cron_rows_list.remove(row_data)
        else:
            Toast(self.window(), "Должно быть хотя бы одно расписание!", is_error=True)

    def browse_key(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите SSH-ключ", "", "SSH Keys (*.pem *.key *.ppk);;All Files (*)")
        if path:
            self.key_input.setPlainText(path)

    def browse_local_path(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите локальную папку для бэкапов")
        if path:
            self.local_path_input.setText(path)

    def clear_data(self):
        self.server_id = None
        self.title_lbl.setText("Добавить сервер")
        self.name_input.clear()
        self.host_input.clear()
        self.port_input.setText("22")
        self.user_input.clear()
        
        self.radio_pass.setChecked(True)
        self.password_input.clear()
        self.key_input.clear()
        self.key_pass_input.clear()
        
        settings = QSettings("GodAzrail", "SSHBackupManager")
        default_local = settings.value("default_backup_dir", os.path.join(os.path.expanduser("~"), "SSH_Backups"))
        default_remote = settings.value("default_remote_path", "/")
        
        self.remote_path_input.setText(default_remote)
        self.local_path_input.setText(default_local)
        
        self.auto_backup_cb.setChecked(False)
        self.interval_spinbox.setValue(60)
        self.max_backups_spinbox.setValue(3)
        self.schedule_type_combo.setCurrentIndex(0)
        
        for row_widget, _, _ in self.cron_rows_list:
            self.cron_rows_layout.removeWidget(row_widget)
            row_widget.deleteLater()
        self.cron_rows_list.clear()
        self.add_cron_row()

    def load_data(self, data):
        self.clear_data() 
        
        self.server_id = data[0]
        self.title_lbl.setText("Настройки")
        self.name_input.setText(data[1])
        self.host_input.setText(data[2])
        self.port_input.setText(str(data[3]))
        self.user_input.setText(data[4])
        
        auth_type = data[15] if len(data) >= 16 else 'password'
        if auth_type == 'key':
            self.radio_key.setChecked(True)
            key_val = data[6] if data[6] else ""
            self.key_input.setPlainText(key_val)
            
            try:
                if data[5]: self.key_pass_input.setText(decrypt_password(data[5]))
            except Exception as e:
                self.key_pass_input.clear()
                print(f"Ошибка расшифровки пароля ключа: {e}")
        else:
            self.radio_pass.setChecked(True)
            try:
                if data[5]: self.password_input.setText(decrypt_password(data[5]))
            except Exception as e:
                self.password_input.clear()
                print(f"Ошибка расшифровки пароля: {e}")
            
        self.remote_path_input.setText(data[7])
        self.local_path_input.setText(data[8])
        self.auto_backup_cb.setChecked(bool(data[9]))
        self.interval_spinbox.setValue(int(data[10]))
        
        if len(data) >= 15:
            self.max_backups_spinbox.setValue(int(data[11]))
            if data[12] == 'cron':
                self.schedule_type_combo.setCurrentIndex(1)
                
                cron_day_str = data[13]
                for row_widget, _, _ in self.cron_rows_list:
                    self.cron_rows_layout.removeWidget(row_widget)
                    row_widget.deleteLater()
                self.cron_rows_list.clear()

                if "|" in cron_day_str or ";" in cron_day_str:
                    for p in cron_day_str.split("|"):
                        if ";" in p:
                            d, t = p.split(";")
                            self.add_cron_row(d, t)
                else:
                    self.add_cron_row(data[13], data[14])
            else:
                self.schedule_type_combo.setCurrentIndex(0)

    def test_connection(self):
        host, port, user = self.host_input.text().strip(), self.port_input.text().strip(), self.user_input.text().strip()
        auth_type = 'key' if self.radio_key.isChecked() else 'password'
        password = self.key_pass_input.text() if auth_type == 'key' else self.password_input.text()
        
        key_path = self.key_input.toPlainText().strip() if auth_type == 'key' else None
        
        if not all([host, port, user]):
            Toast(self.window(), "Заполните хост, порт и пользователя!", is_error=True)
            return
            
        if auth_type == 'key' and not key_path:
            Toast(self.window(), "Укажите SSH-ключ!", is_error=True)
            return
            
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Проверка...")
        self.test_thread = SSHTestThread(host, port, user, password, key_path)
        self.test_thread.result_signal.connect(self.on_test_finished)
        self.test_thread.start()

    def on_test_finished(self, success, message):
        self.test_btn.setEnabled(True)
        self.test_btn.setText("Тест SSH")
        Toast(self.window(), message, is_error=not success)

    def save_server(self):
        name, host, port, user = self.name_input.text().strip(), self.host_input.text().strip(), self.port_input.text().strip(), self.user_input.text().strip()
        remote, local = self.remote_path_input.text().strip(), self.local_path_input.text().strip()
        auto, interval = self.auto_backup_cb.isChecked(), self.interval_spinbox.value()
        max_backups = self.max_backups_spinbox.value() 
        schedule_type = 'interval' if self.schedule_type_combo.currentIndex() == 0 else 'cron'
        
        cron_parts = []
        for _, day_combo, time_edit in self.cron_rows_list:
            c_day = self.day_map[day_combo.currentText()]
            c_time = time_edit.time().toString("HH:mm")
            cron_parts.append(f"{c_day};{c_time}")
            
        cron_day_combined = "|".join(cron_parts)
        cron_time_combined = "" 

        auth_type = 'key' if self.radio_key.isChecked() else 'password'
        password = self.key_pass_input.text() if auth_type == 'key' else self.password_input.text()
        key_path_val = self.key_input.toPlainText().strip() if auth_type == 'key' else ""

        if not all([name, host, port, user, remote, local]):
            Toast(self.window(), "Заполните все обязательные поля!", is_error=True)
            return
            
        if auth_type == 'key' and not key_path_val:
            Toast(self.window(), "Укажите SSH-ключ!", is_error=True)
            return
        
        enc_password = encrypt_password(password) if password else b""
        
        if self.server_id: 
            self.db.update_server(self.server_id, name, host, int(port), user, enc_password, key_path_val, remote, local, auto, interval, max_backups, schedule_type, cron_day_combined, cron_time_combined, auth_type)
            Toast(self.window(), "Настройки обновлены!", is_error=False)
        else: 
            self.db.add_server(name, host, int(port), user, enc_password, key_path_val, remote, local, auto, interval, max_backups, schedule_type, cron_day_combined, cron_time_combined, auth_type)
            Toast(self.window(), "Сервер добавлен!", is_error=False)
            
        self.saved_signal.emit()