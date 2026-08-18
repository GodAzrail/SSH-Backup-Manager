from PyQt5.QtWidgets import QLabel, QFrame, QHBoxLayout, QVBoxLayout, QGraphicsDropShadowEffect, QPushButton
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve
from PyQt5.QtGui import QFont

class Toast(QFrame):
    def __init__(self, parent, message, is_error=False):
        super().__init__(parent)
        
        # Строгий плоский дизайн
        self.setStyleSheet("""
            QFrame {
                background-color: #1e2030;
                border: 1px solid #3b4261;
                border-radius: 8px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(Qt.black)
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 12, 12)
        main_layout.setSpacing(10)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        # Используем синий цвет для успеха, чтобы избежать ядовитого зеленого
        title_color = "#f7768e" if is_error else "#7aa2f7"
        title_text = "Ошибка" if is_error else "Успешно"

        title_lbl = QLabel(title_text)
        title_lbl.setFont(QFont("Arial", 11, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {title_color}; background: transparent; border: none;")
        
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
            QPushButton:hover { color: white; }
        """)
        close_btn.clicked.connect(self.fade_out)
        main_layout.addWidget(close_btn, 0, Qt.AlignTop | Qt.AlignRight)
        
        width = 350
        self.setFixedWidth(width)
        self.adjustSize()
        height = max(self.height(), 65)
        self.resize(width, height)
        
        parent_w = parent.width()
        x_pos = (parent_w - width) // 2
        y_pos = 50 
        start_y = -height - 20 
        
        self.setGeometry(x_pos, start_y, width, height)
        self.show()
        self.raise_()
        
        if hasattr(parent, 'title_bar') and hasattr(parent.title_bar, 'add_history'):
            parent.title_bar.add_history(title_text, message, is_error)
        
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(400)
        self.animation.setEasingCurve(QEasingCurve.OutExpo)
        self.animation.setStartValue(QRect(x_pos, start_y, width, height))
        self.animation.setEndValue(QRect(x_pos, y_pos, width, height))
        self.animation.start()
        
        self.timer = QTimer.singleShot(5000, self.fade_out)

    def fade_out(self):
        if hasattr(self, 'anim_out'): return
            
        self.anim_out = QPropertyAnimation(self, b"geometry")
        self.anim_out.setDuration(400)
        self.anim_out.setEasingCurve(QEasingCurve.InExpo)
        current_rect = self.geometry()
        hide_y = -current_rect.height() - 20 
        
        self.anim_out.setStartValue(current_rect)
        self.anim_out.setEndValue(QRect(current_rect.x(), hide_y, current_rect.width(), current_rect.height()))
        self.anim_out.finished.connect(self.close_toast)
        self.anim_out.start()

    def close_toast(self):
        self.hide()
        self.deleteLater()