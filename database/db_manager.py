import sqlite3
import os
from pathlib import Path

# Определяем защищенную папку в профиле пользователя (например, C:\Users\Имя\AppData\Roaming\SSHBackupManager)
APP_DATA_DIR = Path(os.getenv('APPDATA', Path.home())) / "SSHBackupManager"
DB_DIR = APP_DATA_DIR / "database"
DB_PATH = DB_DIR / "backups.db"

class DBManager:
    def __init__(self):
        # Создаем директорию AppData\Roaming\SSHBackupManager\database, если её нет
        DB_DIR.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, host TEXT, port INTEGER, username TEXT, password BLOB,
                key_path TEXT, remote_path TEXT, local_path TEXT,
                auto_backup BOOLEAN, backup_interval INTEGER DEFAULT 60,
                max_backups INTEGER DEFAULT 3
            )
        ''')
        
        # Безопасное обновление структуры старой базы данных
        try:
            self.cursor.execute("ALTER TABLE servers ADD COLUMN max_backups INTEGER DEFAULT 3")
            self.conn.commit()
        except sqlite3.OperationalError: pass 

        try:
            self.cursor.execute("ALTER TABLE servers ADD COLUMN schedule_type TEXT DEFAULT 'interval'")
            self.cursor.execute("ALTER TABLE servers ADD COLUMN cron_day TEXT DEFAULT '*'")
            self.cursor.execute("ALTER TABLE servers ADD COLUMN cron_time TEXT DEFAULT '00:00'")
            self.conn.commit()
        except sqlite3.OperationalError: pass

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS backup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER, filename TEXT, filepath TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ssh_timeout', '10')")
        self.conn.commit()

    def add_server(self, name, host, port, username, password_blob, key_path, remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time):
        self.cursor.execute('''INSERT INTO servers (name, host, port, username, password, key_path, remote_path, local_path, auto_backup, backup_interval, max_backups, schedule_type, cron_day, cron_time)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                            (name, host, port, username, password_blob, key_path, remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time))
        self.conn.commit()

    def update_server(self, server_id, name, host, port, username, password_blob, key_path, remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time):
        if password_blob:
            self.cursor.execute('''UPDATE servers SET name=?, host=?, port=?, username=?, password=?, key_path=?, remote_path=?, local_path=?, auto_backup=?, backup_interval=?, max_backups=?, schedule_type=?, cron_day=?, cron_time=? WHERE id=?''', 
                                (name, host, port, username, password_blob, key_path, remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time, server_id))
        else:
            self.cursor.execute('''UPDATE servers SET name=?, host=?, port=?, username=?, key_path=?, remote_path=?, local_path=?, auto_backup=?, backup_interval=?, max_backups=?, schedule_type=?, cron_day=?, cron_time=? WHERE id=?''', 
                                (name, host, port, username, key_path, remote, local, auto, interval, max_backups, schedule_type, cron_day, cron_time, server_id))
        self.conn.commit()

    def get_all_servers(self):
        self.cursor.execute("SELECT * FROM servers")
        return self.cursor.fetchall()

    def delete_server(self, server_id):
        self.cursor.execute("DELETE FROM servers WHERE id = ?", (server_id,))
        self.conn.commit()

    def add_history(self, server_id, filename, filepath):
        self.cursor.execute("SELECT id, filename, filepath, timestamp FROM backup_history WHERE server_id = ? ORDER BY timestamp DESC", (server_id,))
        self.cursor.execute("INSERT INTO backup_history (server_id, filename, filepath) VALUES (?, ?, ?)", (server_id, filename, filepath))
        self.conn.commit()

    def get_old_backups_to_delete(self, server_id, max_backups):
        if max_backups <= 0: return []
        self.cursor.execute("SELECT id, filepath FROM backup_history WHERE server_id = ? ORDER BY timestamp DESC LIMIT -1 OFFSET ?", (server_id, max_backups))
        return self.cursor.fetchall()

    def delete_history_record(self, record_id):
        self.cursor.execute("DELETE FROM backup_history WHERE id = ?", (record_id,))
        self.conn.commit()

    def get_server_history(self, server_id):
        self.cursor.execute("SELECT id, filename, filepath, timestamp FROM backup_history WHERE server_id = ? ORDER BY timestamp DESC", (server_id,))
        return self.cursor.fetchall()

    def get_setting(self, key, default=None):
        self.cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = self.cursor.fetchone()
        return row[0] if row else default

    def set_setting(self, key, value):
        self.cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        self.conn.commit()