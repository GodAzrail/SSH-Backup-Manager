import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
from gui.main_window import MainWindow
from core.scheduler import BackupScheduler

# Настройка глобального логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    app = QApplication(sys.argv)
    
    # КРИТИЧЕСКИ ВАЖНО ДЛЯ РАБОТЫ В ТРЕЕ:
    # Запрещаем приложению закрываться, когда скрыто главное окно
    app.setQuitOnLastWindowClosed(False) 
    
    app.setStyle("Fusion")
    
    # Темная тема (базовая, для диалогов)
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(43, 43, 43))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(43, 43, 43))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    scheduler = BackupScheduler()
    scheduler.start()
    
    window = MainWindow(scheduler)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()