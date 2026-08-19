import os
import sqlite3
import logging
import threading
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

# ИСПРАВЛЕНИЕ: Импортируем сам модуль, а не переменные,
# чтобы тесты могли безопасно подменять пути на временные (temp) директории.
import utils.path_config

logger = logging.getLogger(__name__)

_encryption_key = None
_key_lock = threading.Lock()  # Блокировка для многопоточной безопасности (Test 8)

class EncryptionError(Exception):
    """Кастомное исключение для ошибок шифрования (перехватывается в GUI)."""
    pass

def _get_legacy_key_path() -> Path:
    """Возвращает путь к старому ключу относительно текущей рабочей директории."""
    return Path(os.getcwd()) / "config" / "secret.key"

def _test_key_against_db(key: bytes) -> bool:
    """Проверяет, подходит ли ключ к сохраненным паролям в базе данных."""
    if not utils.path_config.DB_PATH.exists():
        return True
        
    try:
        f = Fernet(key)
        conn = sqlite3.connect(utils.path_config.DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем структуру базы, чтобы не упасть, если таблицы нет
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='servers'")
        if not cursor.fetchone():
            conn.close()
            return True

        cursor.execute("SELECT password FROM servers WHERE password IS NOT NULL AND password != '' LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            f.decrypt(row[0])  # Если ключ неверный, выбросит InvalidToken
        return True
    except InvalidToken:
        return False
    except sqlite3.OperationalError:
        return True
    except Exception as e:
        logger.error("Credential decrypt test failed during migration.")
        return False

def _migrate_legacy_key() -> bool:
    """Переносит старый ключ, если он валиден и подходит к текущей БД."""
    legacy_path = _get_legacy_key_path()
    if legacy_path.exists() and not utils.path_config.KEY_FILE.exists():
        logger.info("Found legacy encryption key, attempting migration...")
        try:
            with open(legacy_path, "rb") as f:
                legacy_key = f.read()
            
            Fernet(legacy_key) # Проверка формата ключа
            
            if not _test_key_against_db(legacy_key):
                logger.error("Legacy key does not match existing database credentials. Migration aborted.")
                return False

            # Атомарное сохранение ключа
            utils.path_config.SECURITY_DIR.mkdir(parents=True, exist_ok=True)
            temp_key = utils.path_config.KEY_FILE.with_suffix('.tmp')
            with open(temp_key, "wb") as f:
                f.write(legacy_key)
            temp_key.replace(utils.path_config.KEY_FILE)
            
            if os.name == 'posix':
                os.chmod(utils.path_config.KEY_FILE, 0o600)
                
            logger.info("Encryption key migrated from legacy location successfully.")
            return True
        except Exception as e:
            logger.error("Failed to migrate legacy key.")
            return False
    return False

def get_encryption_key() -> bytes:
    """Возвращает ключ шифрования. Безопасно обрабатывает отсутствие ключа при наличии БД."""
    global _encryption_key
    
    # ИСПРАВЛЕНИЕ: Используем Lock для потокобезопасности при конкурентном запуске
    with _key_lock:
        if _encryption_key:
            return _encryption_key

        if not utils.path_config.KEY_FILE.exists():
            _migrate_legacy_key()

        if utils.path_config.KEY_FILE.exists():
            try:
                with open(utils.path_config.KEY_FILE, "rb") as f:
                    _encryption_key = f.read()
                return _encryption_key
            except Exception:
                logger.error("Failed to load encryption key.")
                raise EncryptionError("Encryption key is missing or corrupted.")

        # ЗАЩИТА: БД существует, а ключа нет нигде
        if utils.path_config.DB_PATH.exists():
            logger.error("Database exists but encryption key is missing. Refusing to generate a new key.")
            raise EncryptionError("Saved credentials could not be decrypted. The encryption key is missing.")

        # Чистая установка
        logger.info("Generating new encryption key for new installation.")
        _encryption_key = Fernet.generate_key()
        
        utils.path_config.SECURITY_DIR.mkdir(parents=True, exist_ok=True)
        temp_key = utils.path_config.KEY_FILE.with_suffix('.tmp')
        with open(temp_key, "wb") as f:
            f.write(_encryption_key)
        temp_key.replace(utils.path_config.KEY_FILE)
        
        if os.name == 'posix':
            os.chmod(utils.path_config.KEY_FILE, 0o600)

        return _encryption_key

def encrypt_password(password: str) -> bytes:
    """Шифрует пароль."""
    if not password:
        return b""
    try:
        key = get_encryption_key()
        f = Fernet(key)
        return f.encrypt(password.encode("utf-8"))
    except EncryptionError:
        raise
    except Exception:
        logger.error("Encryption failed.")
        raise EncryptionError("Failed to encrypt password.")

def decrypt_password(encrypted_password: bytes) -> str:
    """Расшифровывает пароль. В случае несовпадения ключей выбрасывает EncryptionError."""
    if not encrypted_password:
        return ""
    try:
        key = get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted_password).decode("utf-8")
    except InvalidToken:
        logger.error("Credential decrypt failed: InvalidToken.")
        raise EncryptionError("Saved credentials could not be decrypted.")
    except EncryptionError:
        raise
    except Exception:
        logger.error("Decryption failed due to unknown error.")
        raise EncryptionError("Saved credentials could not be decrypted.")