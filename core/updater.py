import os
import sys
import subprocess
import tempfile
import logging
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

logger = logging.getLogger(__name__)

class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, current_version="v1.0.0", owner="GodAzrail", repo="SSH-Backup-Manager"):
        super().__init__()
        self.current_version = current_version
        self.owner = owner
        self.repo = repo

    def run(self):
        try:
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"
            headers = {"Accept": "application/vnd.github.v3+json"}
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name")
                body = data.get("body", "Нет описания изменений.")
                
                download_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break
                
                if not download_url:
                    download_url = data.get("html_url")

                from packaging import version
                if latest_version and version.parse(latest_version) > version.parse(self.current_version):
                    self.update_available.emit(latest_version, download_url, body)
            else:
                self.error_occurred.emit(f"Не удалось проверить обновления (Код: {response.status_code})")
        except Exception as e:
            self.error_occurred.emit(f"Ошибка сети: {str(e)}")

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.save_path = os.path.join(tempfile.gettempdir(), "SSH_Backup_Manager_Update.exe")

    def run(self):
        try:
            response = requests.get(self.url, stream=True, timeout=10)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            self.progress.emit(int(downloaded * 100 / total_size))
            self.finished.emit(self.save_path)
        except Exception as e:
            self.error.emit(str(e))

def apply_update(installer_path):
    try:
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = os.path.abspath(sys.argv[0])
            
        exe_dir = os.path.dirname(exe_path)
        
        logger.info(f"Updater: Application executable path: {exe_path}")
        logger.info(f"Updater: Installer path: {installer_path}")

        bat_path = os.path.join(tempfile.gettempdir(), "ssh_updater.bat")
        
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write('@echo off\n')
            f.write('title SSH Backup Manager Updater\n')
            f.write('echo Updating SSH Backup Manager...\n')
            # ИСПРАВЛЕНИЕ: Гарантируем запуск из директории программы, а не из temp!
            f.write(f'cd /d "{exe_dir}"\n')
            f.write('ping 127.0.0.1 -n 3 > nul\n')
            f.write(f'start /wait "" "{installer_path}" /SILENT /SUPPRESSMSGBOXES /FORCECLOSEAPPLICATIONS\n')
            f.write('if errorlevel 1 (\n')
            f.write('    echo Update failed. Starting existing version...\n')
            f.write(f'    start "" "{exe_path}"\n')
            f.write(') else (\n')
            f.write('    echo Update completed successfully.\n')
            f.write(f'    start "" "{exe_path}"\n')
            f.write(')\n')
            f.write('del "%~f0"\n')

        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=CREATE_NO_WINDOW, shell=False)
        
        logger.info("Updater: Update script launched successfully.")
        
        app = QApplication.instance()
        if app:
            app.quit()
        os._exit(0)
        
    except Exception as e:
        logger.error(f"Error applying update: {e}")
        try:
            from PyQt5.QtWidgets import QMessageBox
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Ошибка обновления")
            msg.setText(f"Не удалось применить обновление:\n{str(e)}")
            msg.exec_()
        except:
            pass