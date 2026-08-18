import sys
import os
import logging
import ctypes
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QPalette, QColor, QIcon
from PyQt5.QtCore import Qt
from gui.main_window import MainWindow
from core.scheduler import BackupScheduler

# Настройка глобального логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_resource_path(relative_path):
    """ Функция для правильного поиска файлов ресурсов (картинок) после сборки в exe """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Глобальная переменная для хранения "замочка", чтобы сборщик мусора Python его не удалил
_mutex_handle = None

def check_already_running():
    """Проверяет, запущен ли уже экземпляр программы с помощью Windows Mutex."""
    global _mutex_handle
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    _mutex_handle = kernel32.CreateMutexW(None, False, "SSHBackupManager_Unique_Mutex_Lock")
    error_code = ctypes.get_last_error()
    if error_code == 183:  
        return True
    return False

def main():
    if sys.platform == "win32":
        myappid = 'godazrail.sshbackupmanager.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(get_resource_path(os.path.join("icon", "icon.ico"))))
    
    if check_already_running():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("SSH Backup Manager")
        msg.setText("Приложение уже работает!")
        msg.setInformativeText("Проверьте системный трей (иконки возле часов в правом нижнем углу).")
        msg.setStyleSheet("""
            QMessageBox { background-color: #24283b; color: white; } 
            QLabel { color: white; font-size: 13px; }
            QPushButton { background-color: #3b4261; color: white; padding: 6px 12px; border-radius: 6px; min-width: 80px; } 
            QPushButton:hover { background-color: #7aa2f7; color: #1a1b26; }
        """)
        msg.exec_()
        sys.exit(0)
    
    app.setQuitOnLastWindowClosed(False) 
    app.setStyle("Fusion")
    
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
    
    # --- ЛОГИКА ФОНОВОГО ЗАПУСКА ---
    # Если Windows запустила программу с флагом --minimized (из автозапуска)
    if "--minimized" in sys.argv:
        pass # Окно не вызывается, но программа работает в фоне (в трее)
    else:
        window.show() # Обычный запуск руками
    # -------------------------------
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()