import requests
from PyQt5.QtCore import QThread, pyqtSignal

class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str, str) # (новая_версия, ссылка_на_скачивание, описание)
    error_occurred = pyqtSignal(str)

    def __init__(self, current_version="v1.0.0", owner="", repo=""):
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
                latest_version = data.get("tag_name") # Например, "v1.1.0"
                body = data.get("body", "Нет описания изменений.")
                
                # Ищем установщик (.exe) среди прикрепленных файлов релиза
                download_url = None
                for asset in data.get("assets", []):
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break
                
                # Если файл не прикрепили к релизу, даем ссылку на саму страницу релиза
                if not download_url:
                    download_url = data.get("html_url")

                if latest_version and latest_version != self.current_version and download_url:
                    self.update_available.emit(latest_version, download_url, body)
            else:
                self.error_occurred.emit(f"Не удалось проверить обновления (Код: {response.status_code})")
        except Exception as e:
            self.error_occurred.emit(f"Ошибка сети: {str(e)}")