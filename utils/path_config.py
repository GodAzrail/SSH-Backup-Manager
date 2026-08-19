import os
import sys
from pathlib import Path

def get_app_data_dir() -> Path:
    if sys.platform == "win32":
        base_dir = os.getenv("APPDATA")
        if not base_dir:
            base_dir = Path.home() / "AppData" / "Roaming"
    else:
        base_dir = Path.home() / ".config"
    
    return Path(base_dir) / "SSHBackupManager"

APP_DATA_DIR = get_app_data_dir()
DATABASE_DIR = APP_DATA_DIR / "database"
SECURITY_DIR = APP_DATA_DIR / "security"

DB_PATH = DATABASE_DIR / "backups.db"
KEY_FILE = SECURITY_DIR / "secret.key"

def ensure_dirs():
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    SECURITY_DIR.mkdir(parents=True, exist_ok=True)
    
    # Ограничиваем права доступа к папке с ключами (особенно важно для Windows)
    if sys.platform == "win32":
        try:
            os.chmod(SECURITY_DIR, 0o700)
        except Exception:
            pass

ensure_dirs()