import paramiko
import logging
from database.db_manager import DBManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SSHManager:
    def __init__(self, host, port, username, password=None, key_path=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Получаем тайм-аут из настроек
        db = DBManager()
        self.timeout = int(db.get_setting('ssh_timeout', 10))

    def connect(self):
        if self.key_path:
            key = paramiko.RSAKey.from_private_key_file(self.key_path)
            self.client.connect(self.host, port=self.port, username=self.username, pkey=key, timeout=self.timeout)
        else:
            self.client.connect(self.host, port=self.port, username=self.username, password=self.password, timeout=self.timeout)

    def test_connection(self) -> bool:
        try:
            self.connect()
            logging.info(f"Успешное подключение к {self.host}")
            self.client.close()
            return True
        except Exception as e:
            logging.error(f"Ошибка подключения к {self.host}: {str(e)}")
            return False