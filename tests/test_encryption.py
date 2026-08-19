# tests/test_encryption.py
import os
import sys
import tempfile
import shutil
import sqlite3
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Мокаем PyQt для тестов
import builtins
original_import = builtins.__import__

def mock_import(name, *args, **kwargs):
    if name.startswith('PyQt5'):
        return MagicMock()
    if name == 'gui.toast':
        class MockToast:
            def __init__(self, *args, **kwargs):
                pass
        mock_module = MagicMock()
        mock_module.Toast = MockToast
        return mock_module
    return original_import(name, *args, **kwargs)

builtins.__import__ = mock_import

# Импортируем модули
import utils.path_config
from utils import encryption
from database.db_manager import DBManager

class TestEncryption(unittest.TestCase):
    
    def setUp(self):
        """Подготовка тестовой среды"""
        self.test_dir = tempfile.mkdtemp()
        
        # Сохраняем оригинальные пути и cwd
        self.original_app_data = utils.path_config.APP_DATA_DIR
        self.original_database_dir = utils.path_config.DATABASE_DIR
        self.original_db_path = utils.path_config.DB_PATH
        self.original_security_dir = utils.path_config.SECURITY_DIR
        self.original_key_file = utils.path_config.KEY_FILE
        self.original_cwd = os.getcwd()
        
        # Патчим пути на тестовую директорию
        utils.path_config.APP_DATA_DIR = Path(self.test_dir)
        utils.path_config.DATABASE_DIR = Path(self.test_dir) / 'database'
        utils.path_config.DB_PATH = Path(self.test_dir) / 'database' / 'backups.db'
        utils.path_config.SECURITY_DIR = Path(self.test_dir) / 'security'
        utils.path_config.KEY_FILE = Path(self.test_dir) / 'security' / 'secret.key'
        
        # Меняем рабочую директорию, чтобы legacy-путь указывал в temp
        os.chdir(self.test_dir)
        
        # Создаем директории
        utils.path_config.DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        utils.path_config.SECURITY_DIR.mkdir(parents=True, exist_ok=True)
        
        # Сбрасываем кэшированный ключ в памяти
        encryption._encryption_key = None
        
    def tearDown(self):
        """Очистка после тестов"""
        # Возвращаем рабочую директорию и оригинальные пути
        os.chdir(self.original_cwd)
        utils.path_config.APP_DATA_DIR = self.original_app_data
        utils.path_config.DATABASE_DIR = self.original_database_dir
        utils.path_config.DB_PATH = self.original_db_path
        utils.path_config.SECURITY_DIR = self.original_security_dir
        utils.path_config.KEY_FILE = self.original_key_file
        
        # Удаляем временную папку и сбрасываем кэш
        shutil.rmtree(self.test_dir, ignore_errors=True)
        encryption._encryption_key = None

    def _create_mock_db(self, password_blob=None):
        """Создает моковую БД для проверки миграции и ошибок."""
        utils.path_config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(utils.path_config.DB_PATH)
        c = conn.cursor()
        c.execute("CREATE TABLE servers (id INTEGER PRIMARY KEY, password BLOB)")
        if password_blob is not None:
            c.execute("INSERT INTO servers (password) VALUES (?)", (password_blob,))
        conn.commit()
        conn.close()

    # === TEST 1: stable key location ===
    def test_1_stable_key_location(self):
        """Test 1: Запуск encryption из разных cwd использует один и тот же key"""
        key1 = encryption.get_encryption_key()
        
        # Меняем рабочую директорию и проверяем, что ключ тот же
        encryption._encryption_key = None # Сброс кэша памяти
        with patch('os.getcwd', return_value='/fake/path'):
            key2 = encryption.get_encryption_key()
            self.assertEqual(key1, key2)

    # === TEST 2: credentials survive restart ===
    def test_2_credentials_survive_restart(self):
        """Test 2: Credentials сохраняются после перезапуска"""
        password = "test_password_123"
        encrypted = encryption.encrypt_password(password)
        
        # Симуляция перезапуска
        encryption._encryption_key = None
        
        # Расшифровка
        decrypted = encryption.decrypt_password(encrypted)
        self.assertEqual(decrypted, password)

    # === TEST 3: different cwd ===
    def test_3_different_cwd(self):
        """Test 3: Credentials работают при запуске из разных cwd"""
        password = "secure_pass_456"
        with patch('os.getcwd', return_value='/cwd/A'):
            encrypted = encryption.encrypt_password(password)
        
        encryption._encryption_key = None
        
        with patch('os.getcwd', return_value='/cwd/B'):
            decrypted = encryption.decrypt_password(encrypted)
            self.assertEqual(decrypted, password)

    # === TEST 4: DB exists but key missing ===
    def test_4_db_exists_key_missing(self):
        """Test 4: БД существует, но ключ отсутствует - НЕ создавать новый ключ"""
        self._create_mock_db()
        
        if utils.path_config.KEY_FILE.exists():
            utils.path_config.KEY_FILE.unlink()
            
        legacy_path = Path(os.getcwd()) / 'config' / 'secret.key'
        if legacy_path.exists():
            legacy_path.unlink()
            
        encryption._encryption_key = None
        
        # Должно выбросить EncryptionError
        with self.assertRaises(encryption.EncryptionError):
            encryption.get_encryption_key()
            
        # Проверяем, что ключ НЕ создался
        self.assertFalse(utils.path_config.KEY_FILE.exists())

    # === TEST 5: legacy migration ===
    def test_5_legacy_migration(self):
        """Test 5: Миграция старого ключа из config/secret.key"""
        # Убедимся что нового ключа нет
        if utils.path_config.KEY_FILE.exists():
            utils.path_config.KEY_FILE.unlink()
            
        legacy_key = Fernet.generate_key()
        f = Fernet(legacy_key)
        encrypted_pass = f.encrypt(b"test_password")
        
        # Создаём БД с зашифрованным паролем
        self._create_mock_db(encrypted_pass)
        
        # Создаём легаси ключ в cwd/config/secret.key
        legacy_dir = Path(os.getcwd()) / 'config'
        legacy_dir.mkdir(parents=True, exist_ok=True)
        legacy_key_file = legacy_dir / 'secret.key'
        with open(legacy_key_file, 'wb') as f_out:
            f_out.write(legacy_key)
            
        self.assertFalse(utils.path_config.KEY_FILE.exists())
        
        # Запуск получения ключа должен инициировать миграцию
        migrated_key = encryption.get_encryption_key()
        
        self.assertEqual(migrated_key, legacy_key)
        self.assertTrue(utils.path_config.KEY_FILE.exists())
        self.assertTrue(legacy_key_file.exists()) # Legacy ключ не удаляем для надежности
        self.assertEqual(encryption.decrypt_password(encrypted_pass), "test_password")

    # === TEST 6: invalid key ===
    def test_6_invalid_key(self):
        """Test 6: Невалидный ключ вызывает EncryptionError (защита кредов)"""
        password = "test_password"
        encrypted = encryption.encrypt_password(password)
        
        old_key = utils.path_config.KEY_FILE.read_bytes()
        
        # Подменяем ключ на другой
        new_key = Fernet.generate_key()
        utils.path_config.KEY_FILE.write_bytes(new_key)
        encryption._encryption_key = None
        
        with self.assertRaises(encryption.EncryptionError):
            encryption.decrypt_password(encrypted)
            
        # Восстанавливаем оригинальный ключ
        utils.path_config.KEY_FILE.write_bytes(old_key)
        encryption._encryption_key = None
        self.assertEqual(encryption.decrypt_password(encrypted), password)

    # === TEST 7: explicit password clear ===
    def test_7_explicit_password_clear(self):
        """Test 7: Проверка, что БД не затирает пароли сама по себе"""
        password = "original_password"
        encrypted = encryption.encrypt_password(password)
        
        db = DBManager()
        db.add_server("test", "localhost", 22, "user", encrypted, "", "/", "/", False, 60, 3, "interval", "*", "00:00", "password")
        db.conn.close()
        
        # Проверяем, что данные записались
        db = DBManager()
        servers = db.get_all_servers()
        self.assertEqual(len(servers), 1)
        self.assertEqual(servers[0][5], encrypted)
        db.conn.close()

    # === TEST 8: concurrent initialization ===
    def test_8_concurrent_initialization(self):
        """Test 8: Два процесса одновременно создают ключ - должен быть один ключ"""
        if utils.path_config.KEY_FILE.exists():
            utils.path_config.KEY_FILE.unlink()
        encryption._encryption_key = None
        
        results = []
        def fetch_key():
            try:
                # Очищаем кэш локально для каждого потока
                encryption._encryption_key = None
                encryption.get_encryption_key()
                results.append(utils.path_config.KEY_FILE.read_bytes())
            except Exception as e:
                results.append(e)

        threads = [threading.Thread(target=fetch_key) for _ in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()
        
        valid = True
        try:
            key1 = utils.path_config.KEY_FILE.read_bytes()
            Fernet(key1)
        except Exception:
            valid = False
            
        self.assertTrue(valid)
        # У всех потоков должен быть одинаковый ключ в файле
        self.assertEqual(len(set(r for r in results if isinstance(r, bytes))), 1)

if __name__ == '__main__':
    unittest.main(verbosity=2)