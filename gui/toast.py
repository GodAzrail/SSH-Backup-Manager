from PyQt5.QtWidgets import QLabel, QFrame, QHBoxLayout, QVBoxLayout, QGraphicsDropShadowEffect, QPushButton
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve
from PyQt5.QtGui import QFont

class Toast(QFrame):
    def __init__(self, parent, message, is_error=False):
        super().__init__(parent)
        
        bg_color = "#1e2030"
        accent_color = "#f7768e" if is_error else "#9ece6a"
        title_text = "Ошибка" if is_error else "Операция успешна"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-left: 4px solid {accent_color};
                border-top: 1px solid #3b4261;
                border-right: 1px solid #3b4261;
                border-bottom: 1px solid #3b4261;
                border-radius: 6px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 12, 12)
        main_layout.setSpacing(12)
        
        icon_label = QLabel("❌" if is_error else "✅")
        icon_label.setStyleSheet("background: transparent; border: none; font-size: 16px;")
        main_layout.addWidget(icon_label, 0, Qt.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_lbl = QLabel(title_text)
        title_lbl.setFont(QFont("Arial", 11, QFont.Bold))
        title_lbl.setStyleSheet("color: white; background: transparent; border: none;")
        
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Arial", 10))
        msg_lbl.setStyleSheet("color: #a9b1d6; background: transparent; border: none;")
        msg_lbl.setWordWrap(True)
        
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(msg_lbl)
        text_layout.addStretch()
        
        main_layout.addLayout(text_layout, 1)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #565f89;
                border: none;
                font-size: 14px;
                font-weight: bold;
                padding: 0px; 
            }
            QPushButton:hover {
                color: white;
            }
        """)
        close_btn.clicked.connect(self.fade_out)
        main_layout.addWidget(close_btn, 0, Qt.AlignTop)
        
        width = 300
        self.setFixedWidth(width)
        self.adjustSize()
        height = max(self.height(), 65)
        self.resize(width, height)
        
        # --- НОВАЯ ПОЗИЦИЯ: СНИЗУ СПРАВА ---
        parent_w = parent.width()
        parent_h = parent.height()
        
        margin_right = 30
        margin_bottom = 40
        
        y_pos = parent_h - height - margin_bottom
        
        # Позиции для анимации по горизонтали (выезжает справа)
        start_x = parent_w + 10  # Начинается за правым краем окна
        end_x = parent_w - width - margin_right # Останавливается с отступом
        
        self.setGeometry(start_x, y_pos, width, height)
        self.show()
        self.raise_()
        
        # Анимация появления (движение влево)
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QEasingCurve.OutExpo)
        self.animation.setStartValue(QRect(start_x, y_pos, width, height))
        self.animation.setEndValue(QRect(end_x, y_pos, width, height))
        self.animation.start()
        
        self.timer = QTimer.singleShot(4000, self.fade_out)

    def fade_out(self):
        if hasattr(self, 'anim_out'): 
            return
            
        # Анимация скрытия (движение обратно вправо)
        self.anim_out = QPropertyAnimation(self, b"geometry")
        self.anim_out.setDuration(400)
        self.anim_out.setEasingCurve(QEasingCurve.InExpo)
        current_rect = self.geometry()
        
        hide_x = current_rect.x() + current_rect.width() + 50 # Уводим за экран
        
        self.anim_out.setStartValue(current_rect)
        self.anim_out.setEndValue(QRect(hide_x, current_rect.y(), current_rect.width(), current_rect.height()))
        self.anim_out.finished.connect(self.close_toast)
        self.anim_out.start()

    def close_toast(self):
        self.hide()
        self.deleteLater()