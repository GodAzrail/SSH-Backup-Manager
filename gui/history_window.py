import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLayout, QFrame,
                             QScrollArea, QLabel, QPushButton, QMessageBox, QHBoxLayout, QGraphicsDropShadowEffect, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize
from database.db_manager import DBManager
from core.backup_manager import RestoreThread

# ==========================================
# РЕЗИНОВАЯ СЕТКА (Авто-перенос элементов)
# ==========================================
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=20):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item: item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margin, _, _, _ = self.getContentsMargins()
        size += QSize(2 * margin, 2 * margin)
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            spaceX = self.spacing()
            spaceY = self.spacing()
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()

class FlowWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = FlowLayout(self, margin=0, spacing=20)

    def addWidget(self, widget):
        self.layout.addWidget(widget)

    def clear(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setMinimumHeight(self.layout.heightForWidth(self.width()))

# ==========================================
# ИНТЕРФЕЙС КАРТОЧЕК И ОКНА
# ==========================================
class HistoryCard(QFrame):
    def __init__(self, record, server_data, delete_cb):
        super().__init__()
        self.record_id = record[0]
        self.server_data = server_data 
        filename, self.filepath, timestamp = record[1], record[2], record[3]

        self.setFixedSize(300, 160) 
        self.setObjectName("HistoryCard")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
        
        self.setStyleSheet("""
            QFrame#HistoryCard { 
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #2a2d3d, stop: 1 #24283b); 
                border-radius: 15px; 
                border: 1px solid #3b4261; 
            }
            QFrame#HistoryCard:hover { 
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #32364a, stop: 1 #2f354d); 
                border: 1px solid #4a5175; 
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        name_lbl = QLabel(filename)
        name_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent; border: none;")

        time_lbl = QLabel(f"Создан: {timestamp}")
        time_lbl.setStyleSheet("color: #9ece6a; font-size: 12px; background: transparent; border: none;")

        # ИСПРАВЛЕНО: Теперь используется self.filepath
        path_lbl = QLabel(self.filepath)
        path_lbl.setStyleSheet("color: #565f89; font-size: 10px; background: transparent; border: none;")
        path_lbl.setWordWrap(True)

        btn_layout = QHBoxLayout()
        
        self.restore_btn = QPushButton("Восстановить")
        self.restore_btn.setCursor(Qt.PointingHandCursor)
        self.restore_btn.setStyleSheet("""
            QPushButton { background-color: #7aa2f7; color: #1a1b26; padding: 6px 12px; border-radius: 6px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #8db0f8; }
            QPushButton:disabled { background-color: #3b4261; color: #565f89; }
        """)
        self.restore_btn.clicked.connect(self.start_restore)

        del_btn = QPushButton("Удалить файл")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet("""
            QPushButton { background-color: rgba(247, 118, 142, 0.2); color: #f7768e; padding: 6px; border-radius: 6px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #f7768e; color: #1a1b26; }
        """)
        del_btn.clicked.connect(lambda: delete_cb(self.record_id, self.filepath))

        btn_layout.addWidget(self.restore_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(del_btn)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #1a1b26; border-radius: 3px; border: none; }
            QProgressBar::chunk { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #7aa2f7, stop: 1 #9ece6a); border-radius: 3px; }
        """)

        layout.addWidget(name_lbl)
        layout.addWidget(time_lbl)
        layout.addWidget(path_lbl)
        layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addWidget(self.progress)

    def start_restore(self):
        reply = QMessageBox.warning(self, 'Внимание!', 
                                    'Вы собираетесь восстановить этот архив на сервер.\nЭто действие ПЕРЕЗАПИШЕТ существующие файлы в папке.\nВы уверены?', 
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.restore_btn.setEnabled(False)
            self.restore_btn.setText("...")
            self.progress.setVisible(True)
            self.progress.setValue(0)
            
            self.thread = RestoreThread(self.server_data, self.filepath)
            self.thread.progress_signal.connect(self.progress.setValue)
            self.thread.finished_signal.connect(self.on_restore_finished)
            self.thread.start()

    def on_restore_finished(self, success, msg):
        self.restore_btn.setEnabled(True)
        self.restore_btn.setText("Восстановить")
        self.progress.setVisible(False)
        self.progress.setValue(0)
        
        if success:
            QMessageBox.information(self, "Успех", msg)
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось восстановить бэкап:\n{msg}")


class HistoryView(QWidget):
    back_signal = pyqtSignal()

    def __init__(self, server_id, server_name, parent=None):
        super().__init__(parent)
        self.server_id = server_id
        self.db = DBManager()
        self.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        self.back_btn = QPushButton("← Назад")
        self.back_btn.setFixedSize(100, 35)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton { background-color: #3b4261; color: white; border-radius: 6px; font-weight: bold; font-size: 13px; border: none;}
            QPushButton:hover { background-color: #7aa2f7; color: #1a1b26; }
        """)
        self.back_btn.clicked.connect(self.back_signal.emit)

        title = QLabel(f"История бэкапов: {server_name}")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold; border: none;")
        
        header_layout.addWidget(self.back_btn)
        header_layout.addWidget(title)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("border: none; background: transparent;")

        self.flow_widget = FlowWidget()
        self.flow_widget.setStyleSheet("background: transparent;")
        self.scroll.setWidget(self.flow_widget)

        layout.addWidget(self.scroll)
        self.load_history()

    def load_history(self):
        self.flow_widget.clear()

        servers = self.db.get_all_servers()
        server_data = next((s for s in servers if s[0] == self.server_id), None)

        records = self.db.get_server_history(self.server_id)
        if not records:
            empty = QLabel("Нет сохраненных бэкапов")
            empty.setStyleSheet("color: #565f89; font-size: 16px; border: none;")
            self.flow_widget.addWidget(empty)
            return

        for r in records:
            card = HistoryCard(r, server_data, self.delete_record)
            self.flow_widget.addWidget(card)

    def delete_record(self, record_id, filepath):
        reply = QMessageBox.question(self, 'Удаление', 'Безвозвратно удалить этот архив с диска?', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                pass
            self.db.delete_history_record(record_id)
            self.load_history()