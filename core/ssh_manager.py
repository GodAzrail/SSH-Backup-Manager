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
            # При использовании key_filename Paramiko сам определяет тип ключа (RSA, Ed25519, ECDSA и т.д.)
            connect_kwargs = {
                'hostname': self.host,
                'port': self.port,
                'username': self.username,
                'key_filename': self.key_path,
                'timeout': self.timeout
            }
            # Если пароль передан при выборе ключа, он используется как фраза для его расшифровки (passphrase)
            if self.password:
                connect_kwargs['passphrase'] = self.password
                
            self.client.connect(**connect_kwargs)
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