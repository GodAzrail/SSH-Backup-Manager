import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLayout, QFrame, QDialog,
                             QScrollArea, QLabel, QPushButton, QHBoxLayout, QGraphicsDropShadowEffect, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize

from gui.toast import Toast
from database.db_manager import DBManager
from core.backup_manager import RestoreThread

# ==========================================
# КАСТОМНОЕ ДИАЛОГОВОЕ ОКНО
# ==========================================
class CustomConfirmDialog(QDialog):
    def __init__(self, parent, title, message, confirm_text, is_danger=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(450, 220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        self.frame = QFrame(self)
        self.frame.setStyleSheet("""
            QFrame { background-color: #24283b; border: 1px solid #3b4261; border-radius: 12px; }
            QLabel { background: transparent; border: none; }
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 5)
        self.frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        frame_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; color: #565f89; border: none; font-size: 14px; font-weight: bold; } QPushButton:hover { color: #f7768e; }")
        close_btn.clicked.connect(self.reject)
        
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)

        msg_layout = QHBoxLayout()
        icon = QLabel("⚠️")
        icon.setStyleSheet("font-size: 32px;")
        icon.setAlignment(Qt.AlignTop)
        
        text_lbl = QLabel(message)
        text_lbl.setStyleSheet("color: #a9b1d6; font-size: 13px; line-height: 1.5;")
        text_lbl.setWordWrap(True)
        
        msg_layout.addWidget(icon)
        msg_layout.addSpacing(10)
        msg_layout.addWidget(text_lbl, 1)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("QPushButton { background-color: #1e2030; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold; border: 1px solid #3b4261;} QPushButton:hover { background-color: #3b4261; }")
        cancel_btn.clicked.connect(self.reject)

        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        if is_danger:
            confirm_btn.setStyleSheet("QPushButton { background-color: rgba(247, 118, 142, 0.2); color: #f7768e; padding: 8px 16px; border-radius: 6px; font-weight: bold; border: none;} QPushButton:hover { background-color: #f7768e; color: #1a1b26; }")
        else:
            confirm_btn.setStyleSheet("QPushButton { background-color: #7aa2f7; color: #1a1b26; padding: 8px 16px; border-radius: 6px; font-weight: bold; border: none;} QPushButton:hover { background-color: #8db0f8; }")
        confirm_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)

        frame_layout.addLayout(header_layout)
        frame_layout.addLayout(msg_layout)
        frame_layout.addStretch()
        frame_layout.addLayout(btn_layout)
        layout.addWidget(self.frame)
        self._is_tracking = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_tracking = True
            self._start_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._is_tracking: self.move(event.globalPos() - self._start_pos)

    def mouseReleaseEvent(self, event):
        self._is_tracking = False


# ==========================================
# РЕЗИНОВАЯ СЕТКА (С ИСПРАВЛЕНИЕМ АРТЕФАКТОВ)
# ==========================================
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=20):
        super().__init__(parent)
        if parent is not None: self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item: item = self.takeAt(0)

    def addItem(self, item): self.itemList.append(item)
    def count(self): return len(self.itemList)
    def itemAt(self, index):
        if 0 <= index < len(self.itemList): return self.itemList[index]
        return None
    def takeAt(self, index):
        if 0 <= index < len(self.itemList): return self.itemList.pop(index)
        return None
    def expandingDirections(self): return Qt.Orientations(Qt.Orientation(0))
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self.doLayout(QRect(0, 0, width, 0), True)
    
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)
        
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self.itemList: size = size.expandedTo(item.minimumSize())
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
        # ИСПРАВЛЕНО: Перед удалением виджета принудительно его скрываем,
        # чтобы Qt не оставляла призрачные следы (артефакты графики) на экране.
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget(): 
                item.widget().hide()
                item.widget().deleteLater()
        self.update() # Принудительно заставляем слой перерисоваться
                
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setMinimumHeight(self.layout.heightForWidth(self.width()))

# ==========================================
# КАРТОЧКА ИСТОРИИ (ПЛОСКИЙ ДИЗАЙН)
# ==========================================
class HistoryCard(QFrame):
    def __init__(self, record, server_data, delete_cb):
        super().__init__()
        self.record_id = record[0]
        self.server_data = server_data 
        filename, self.filepath, timestamp = record[1], record[2], record[3]

        self.setFixedSize(300, 140) 
        self.setObjectName("HistoryCard")
        
        # Убрана тень
        self.setStyleSheet("""
            QFrame#HistoryCard { background-color: #1e2030; border-radius: 8px; border: 1px solid #292e42; }
            QFrame#HistoryCard:hover { background-color: #24283b; border: 1px solid #3b4261; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(6)

        name_lbl = QLabel(filename)
        name_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 13px; background: transparent; border: none;")

        time_lbl = QLabel(f"Создан: {timestamp}")
        time_lbl.setStyleSheet("color: #a9b1d6; font-size: 11px; background: transparent; border: none;")

        path_lbl = QLabel(self.filepath)
        path_lbl.setStyleSheet("color: #565f89; font-size: 10px; background: transparent; border: none;")
        path_lbl.setWordWrap(True)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        self.restore_btn = QPushButton("▶ Восстановить")
        self.restore_btn.setCursor(Qt.PointingHandCursor)
        self.restore_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #7aa2f7; border: 1px solid #3b4261; padding: 4px 10px; border-radius: 5px; font-weight: bold;}
            QPushButton:hover { background-color: rgba(122, 162, 247, 0.1); border: 1px solid #7aa2f7; }
            QPushButton:disabled { background-color: transparent; color: #565f89; border: 1px solid #292e42; }
        """)
        self.restore_btn.clicked.connect(self.start_restore)

        del_btn = QPushButton("✕")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet("""
            QPushButton { background-color: transparent; color: #565f89; border: 1px solid transparent; border-radius: 5px; font-size: 12px;}
            QPushButton:hover { background-color: rgba(247, 118, 142, 0.2); color: #f7768e; }
        """)
        del_btn.clicked.connect(lambda: delete_cb(self.record_id, self.filepath))

        btn_layout.addWidget(self.restore_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(del_btn)

        self.progress = QProgressBar()
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.progress.setStyleSheet("QProgressBar { background-color: #1a1b26; border-radius: 2px; border: none; } QProgressBar::chunk { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #7aa2f7, stop: 1 #9ece6a); border-radius: 2px; }")

        layout.addWidget(name_lbl)
        layout.addWidget(time_lbl)
        layout.addWidget(path_lbl)
        layout.addStretch()
        layout.addLayout(btn_layout)
        layout.addWidget(self.progress)

    def start_restore(self):
        dialog = CustomConfirmDialog(
            self.window(), 
            "Восстановление", 
            "Вы собираетесь восстановить этот архив на сервер.\nЭто действие ПЕРЕЗАПИШЕТ существующие файлы в папке. Вы уверены?", 
            "Да, восстановить"
        )
        if dialog.exec_():
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
        self.restore_btn.setText("▶ Восстановить")
        self.progress.setVisible(False)
        self.progress.setValue(0)
        Toast(self.window(), msg, is_error=not success)


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
        self.back_btn.setStyleSheet("QPushButton { background-color: #3b4261; color: white; border-radius: 6px; font-weight: bold; font-size: 13px; border: none;} QPushButton:hover { background-color: #7aa2f7; color: #1a1b26; }")
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
        dialog = CustomConfirmDialog(
            self.window(), 
            "Удаление архива", 
            "Вы уверены, что хотите безвозвратно удалить этот архив с диска? Это действие нельзя отменить.", 
            "Удалить",
            is_danger=True 
        )

        if dialog.exec_():
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception:
                pass
            self.db.delete_history_record(record_id)
            self.load_history()
            Toast(self.window(), "Архив успешно удален!", is_error=False)