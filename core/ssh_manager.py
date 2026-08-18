import paramiko
import logging
import io
from database.db_manager import DBManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SSHManager:
    def __init__(self, host, port, username, password=None, key_path=None):
        self.host = host
        self.port = int(port)
        self.username = username
        self.password = password
        self.key_path = key_path
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        db = DBManager()
        self.timeout = int(db.get_setting('ssh_timeout', 10))

    def connect(self):
        connect_kwargs = {
            'hostname': self.host,
            'port': self.port,
            'username': self.username,
            'timeout': self.timeout
        }
        
        if self.key_path:
            if self.password:
                connect_kwargs['passphrase'] = self.password
            
            # Проверяем, является ли содержимое сырым текстом ключа
            if "PRIVATE KEY" in self.key_path:
                key_file = io.StringIO(self.key_path)
                pkey = None
                
                # Перебираем форматы ключей для расшифровки
                for key_class in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey):
                    try:
                        key_file.seek(0)
                        pkey = key_class.from_private_key(key_file, password=self.password)
                        break
                    except Exception:
                        pass
                        
                if pkey:
                    connect_kwargs['pkey'] = pkey
                else:
                    raise ValueError("Не удалось расшифровать или распознать формат текста приватного ключа.")
            else:
                # Иначе воспринимаем как путь к файлу
                connect_kwargs['key_filename'] = self.key_path
                
        else:
            connect_kwargs['password'] = self.password
            
        self.client.connect(**connect_kwargs)

    def test_connection(self) -> bool:
        try:
            self.connect()
            logging.info(f"Успешное подключение к {self.host}")
            self.client.close()
            return True
        except Exception as e:
            logging.error(f"Ошибка подключения к {self.host}: {str(e)}")
            return False