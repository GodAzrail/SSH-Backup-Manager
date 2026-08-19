import os
import time 
import logging
from PyQt5.QtCore import QThread, pyqtSignal, QObject, QSettings
from core.ssh_manager import SSHManager
from utils.encryption import decrypt_password
from database.db_manager import DBManager

class GlobalBackupSignals(QObject):
    started = pyqtSignal(int)
    progress = pyqtSignal(int, int, str)  # ID, Процент, Текст (скорость, ETA)
    finished = pyqtSignal(int, bool, str)

global_signals = GlobalBackupSignals()

def translate_error(err_str):
    if not err_str: 
        return "Неизвестная ошибка."
    
    err_str = str(err_str).strip()
    
    translations = {
        "No space left on device": "На сервере закончилось свободное место.",
        "Permission denied": "Отказано в доступе. Проверьте права пользователя.",
        "No such file or directory": "Указанный путь или папка не существует на сервере.",
        "Authentication failed": "Ошибка авторизации (неверный пароль, пользователь или SSH-ключ).",
        "Connection timed out": "Время ожидания подключения истекло. Сервер недоступен.",
        "Network is unreachable": "Сеть недоступна. Проверьте подключение к интернету.",
        "Connection refused": "В подключении отказано. Проверьте правильность порта (обычно 22).",
        "Name or service not known": "Не удалось определить IP-адрес или домен хоста."
    }
    
    for eng, rus in translations.items():
        if eng.lower() in err_str.lower():
            return rus
            
    if "tar: Removing leading" in err_str:
        err_str = err_str.replace("tar: Removing leading '/' from member names", "").strip()
        
    return err_str if err_str else "Произошла ошибка при выполнении операции."

def rotate_backups(server_id, max_backups):
    db = DBManager()
    old_backups = db.get_old_backups_to_delete(server_id, max_backups)
    for record in old_backups:
        record_id, filepath = record[0], record[1]
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logging.info(f"Удален старый бэкап с диска: {filepath}")
            db.delete_history_record(record_id)
            logging.info(f"Удалена запись о бэкапе из БД (ID: {record_id})")
        except Exception as e:
            logging.error(f"Не удалось удалить старый бэкап {filepath}: {e}")

def create_sftp_callback(start_time, max_mb_sec, signal_emitter, server_id=None):
    """Генератор callback-функции для SFTP с расчетом ETA и ограничением скорости"""
    max_bytes_sec = max_mb_sec * 1024 * 1024
    state = {'last_emit': 0}
    
    def callback(transferred, total):
        now = time.time()
        elapsed = now - start_time
        if elapsed <= 0: elapsed = 0.001
        
        current_speed = transferred / elapsed
        
        # Контроль скорости (Rate Limiting)
        if max_bytes_sec > 0 and current_speed > max_bytes_sec:
            expected_time = transferred / max_bytes_sec
            time.sleep(expected_time - elapsed)
            now = time.time()
            elapsed = now - start_time
            current_speed = transferred / elapsed

        # Обновляем UI не чаще 5 раз в секунду, чтобы не перегружать поток GUI
        if now - state['last_emit'] > 0.2 or transferred == total:
            state['last_emit'] = now
            speed_mb = current_speed / (1024 * 1024)
            remaining_bytes = total - transferred
            eta_sec = remaining_bytes / current_speed if current_speed > 0 else 0
            
            percent = int((transferred / total) * 100) if total > 0 else 0
            status_text = f"{percent}% | {speed_mb:.1f} МБ/с | Ост: {int(eta_sec)}с"
            
            if server_id is not None:
                signal_emitter.emit(server_id, percent, status_text)
            else:
                signal_emitter.emit(percent, status_text)
                
    return callback

def perform_background_backup(server_data):
    server_id, name, host, port, username, pwd_blob, key_path, remote_path, local_path, auto, interval, max_backups, schedule_type, cron_day, cron_time, *extra = server_data
    ssh_mgr = None
    remote_archive_path = None
    start_time = time.time()
    
    global_signals.started.emit(server_id)
    
    try:
        logging.info(f"[{name}] Авто-бэкап запущен по расписанию.")
        password = decrypt_password(pwd_blob) if pwd_blob else None
        ssh_mgr = SSHManager(host, port, username, password, key_path)
        
        global_signals.progress.emit(server_id, 0, "Подключение по SSH...")
        ssh_mgr.connect()
        
        ssh_mgr.client.exec_command("rm -f /tmp/*backup_*.tar.gz /tmp/restore_*.tar.gz")
        
        global_signals.progress.emit(server_id, 0, "Экспорт Docker контейнеров...")
        docker_cmd = """
        mkdir -p /tmp/docker_dumps
        if command -v docker &> /dev/null; then
            docker ps -a > /tmp/docker_dumps/ps_list.txt 2>/dev/null
            docker inspect $(docker ps -aq) > /tmp/docker_dumps/containers.json 2>/dev/null
        fi
        """
        stdin, stdout, stderr = ssh_mgr.client.exec_command(docker_cmd)
        stdout.channel.recv_exit_status() # Ждем завершения дампа
        
        archive_name = f"full_backup_{int(time.time())}.tar.gz" if remote_path == "/" else f"backup_{int(time.time())}.tar.gz"
        remote_archive_path = f"/tmp/{archive_name}"
        
        global_signals.progress.emit(server_id, 0, "Создание tar-архива...")
        if remote_path == "/":
            command = (f"tar -czpf {remote_archive_path} --exclude={remote_archive_path} "
                       f"--exclude=/proc --exclude=/sys --exclude=/dev --exclude=/run "
                       f"--exclude=/tmp/*.tar.gz --exclude=/mnt --exclude=/media --exclude=/lost+found {remote_path} /tmp/docker_dumps")
        else:
            command = f"tar -czpf {remote_archive_path} {remote_path} /tmp/docker_dumps"

        stdin, stdout, stderr = ssh_mgr.client.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status not in [0, 1]: 
            raise Exception(stderr.read().decode().strip())

        server_backup_dir = os.path.join(local_path, name)
        if not os.path.exists(server_backup_dir):
            os.makedirs(server_backup_dir)
            
        local_archive_path = os.path.join(server_backup_dir, archive_name)

        logging.info(f"[{name}] Загрузка готового архива...")
        max_speed = QSettings("GodAzrail", "SSHBackupManager").value("max_download_speed", 0, type=int)
        
        sftp = ssh_mgr.client.open_sftp()
        sftp_cb = create_sftp_callback(time.time(), max_speed, global_signals.progress, server_id)
        sftp.get(remote_archive_path, local_archive_path, callback=sftp_cb)
        
        logging.info(f"[{name}] Очистка временных файлов на сервере...")
        sftp.remove(remote_archive_path)
        ssh_mgr.client.exec_command("rm -rf /tmp/docker_dumps")
        sftp.close()
        
        db = DBManager()
        db.add_history(server_id, archive_name, local_archive_path)
        rotate_backups(server_id, max_backups)
        
        duration = int(time.time() - start_time)
        mins, secs = duration // 60, duration % 60
        time_str = f"{mins} мин. {secs} сек." if mins > 0 else f"{secs} сек."
        
        logging.info(f"[{name}] Авто-бэкап успешно завершен за {time_str}")
        global_signals.finished.emit(server_id, True, f"Авто-бэкап завершен за {time_str}")
        return True
    except Exception as e:
        ru_error = translate_error(e)
        logging.error(f"[{name}] Ошибка авто-бэкапа: {ru_error}")
        if ssh_mgr and ssh_mgr.client and remote_archive_path:
            try:
                ssh_mgr.client.exec_command(f"rm -f {remote_archive_path}")
            except:
                pass
        global_signals.finished.emit(server_id, False, ru_error)
        return False
    finally:
        if ssh_mgr and ssh_mgr.client:
            ssh_mgr.client.close()


class BackupThread(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, server_data):
        super().__init__()
        self.server_data = server_data

    def run(self):
        server_id, name, host, port, username, pwd_blob, key_path, remote_path, local_path, auto, interval, max_backups, schedule_type, cron_day, cron_time, *extra = self.server_data
        ssh_mgr = None
        remote_archive_path = None
        start_time = time.time()
        try:
            password = decrypt_password(pwd_blob) if pwd_blob else None
            ssh_mgr = SSHManager(host, port, username, password, key_path)
            
            self.progress_signal.emit(0, "Подключение по SSH...")
            logging.info(f"[{name}] Подключение по SSH...")
            ssh_mgr.connect()
            
            ssh_mgr.client.exec_command("rm -f /tmp/*backup_*.tar.gz /tmp/restore_*.tar.gz")
            
            self.progress_signal.emit(0, "Экспорт Docker контейнеров...")
            docker_cmd = """
            mkdir -p /tmp/docker_dumps
            if command -v docker &> /dev/null; then
                docker ps -a > /tmp/docker_dumps/ps_list.txt 2>/dev/null
                docker inspect $(docker ps -aq) > /tmp/docker_dumps/containers.json 2>/dev/null
            fi
            """
            stdin, stdout, stderr = ssh_mgr.client.exec_command(docker_cmd)
            stdout.channel.recv_exit_status()

            archive_name = f"full_backup_{int(time.time())}.tar.gz" if remote_path == "/" else f"backup_{int(time.time())}.tar.gz"
            remote_archive_path = f"/tmp/{archive_name}"
            
            self.progress_signal.emit(0, "Выполнение tar-архивации...")
            logging.info(f"[{name}] Выполнение tar-архивации (это может занять время)...")
            
            if remote_path == "/":
                command = (f"tar -czpf {remote_archive_path} --exclude={remote_archive_path} "
                           f"--exclude=/proc --exclude=/sys --exclude=/dev --exclude=/run "
                           f"--exclude=/tmp/*.tar.gz --exclude=/mnt --exclude=/media --exclude=/lost+found {remote_path} /tmp/docker_dumps")
            else:
                command = f"tar -czpf {remote_archive_path} {remote_path} /tmp/docker_dumps"

            stdin, stdout, stderr = ssh_mgr.client.exec_command(command)
            if stdout.channel.recv_exit_status() not in [0, 1]: 
                raise Exception(stderr.read().decode().strip())

            server_backup_dir = os.path.join(local_path, name)
            if not os.path.exists(server_backup_dir): 
                os.makedirs(server_backup_dir)
                
            local_archive_path = os.path.join(server_backup_dir, archive_name)
            
            self.progress_signal.emit(0, "Инициализация загрузки...")
            logging.info(f"[{name}] Загрузка архива на локальный ПК...")
            
            max_speed = QSettings("GodAzrail", "SSHBackupManager").value("max_download_speed", 0, type=int)
            sftp = ssh_mgr.client.open_sftp()
            sftp_cb = create_sftp_callback(time.time(), max_speed, self.progress_signal)
            
            sftp.get(remote_archive_path, local_archive_path, callback=sftp_cb)
            
            self.progress_signal.emit(100, "Очистка сервера...")
            logging.info(f"[{name}] Очистка временных файлов на сервере...")
            sftp.remove(remote_archive_path)
            ssh_mgr.client.exec_command("rm -rf /tmp/docker_dumps")
            sftp.close()
            
            db = DBManager()
            db.add_history(server_id, archive_name, local_archive_path)
            rotate_backups(server_id, max_backups)
            
            duration = int(time.time() - start_time)
            mins, secs = duration // 60, duration % 60
            time_str = f"{mins} мин. {secs} сек." if mins > 0 else f"{secs} сек."
            
            logging.info(f"[{name}] Бэкап успешно завершен за {time_str}!")
            self.finished_signal.emit(True, f"Сохранен за {time_str}")

        except Exception as e:
            ru_error = translate_error(e)
            logging.error(f"[{name}] Ошибка: {ru_error}")
            if ssh_mgr and ssh_mgr.client and remote_archive_path:
                try:
                    logging.info(f"[{name}] Экстренное удаление поврежденного архива...")
                    ssh_mgr.client.exec_command(f"rm -f {remote_archive_path}")
                except:
                    pass
            self.finished_signal.emit(False, ru_error)
        finally:
            if ssh_mgr and ssh_mgr.client:
                ssh_mgr.client.close()


class RestoreThread(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, server_data, filepath):
        super().__init__()
        self.server_data = server_data
        self.filepath = filepath

    def run(self):
        server_id, name, host, port, username, pwd_blob, key_path, remote_path, local_path, auto, interval, max_backups, schedule_type, cron_day, cron_time, *extra = self.server_data
        ssh_mgr = None
        remote_archive_path = None
        start_time = time.time()
        try:
            password = decrypt_password(pwd_blob) if pwd_blob else None
            ssh_mgr = SSHManager(host, port, username, password, key_path)
            
            self.progress_signal.emit(0, "Подключение для восстановления...")
            logging.info(f"[{name}] Подключение для восстановления...")
            ssh_mgr.connect()
            
            remote_archive_path = f"/tmp/restore_{int(time.time())}.tar.gz"
            
            logging.info(f"[{name}] Отправка бэкапа на сервер...")
            max_speed = QSettings("GodAzrail", "SSHBackupManager").value("max_download_speed", 0, type=int)
            sftp = ssh_mgr.client.open_sftp()
            sftp_cb = create_sftp_callback(time.time(), max_speed, self.progress_signal)
            
            sftp.put(self.filepath, remote_archive_path, callback=sftp_cb)
            sftp.close()
            
            self.progress_signal.emit(100, "Распаковка архива...")
            logging.info(f"[{name}] Распаковка архива в корень файловой системы (замена файлов)...")
            command = f"tar -xzpf {remote_archive_path} -C /"
            stdin, stdout, stderr = ssh_mgr.client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            self.progress_signal.emit(100, "Очистка сервера...")
            logging.info(f"[{name}] Очистка временных файлов...")
            ssh_mgr.client.exec_command(f"rm -f {remote_archive_path}")
            
            if exit_status not in [0, 1]: 
                raise Exception(stderr.read().decode().strip())
                
            duration = int(time.time() - start_time)
            mins, secs = duration // 60, duration % 60
            time_str = f"{mins} мин. {secs} сек." if mins > 0 else f"{secs} сек."
            
            logging.info(f"[{name}] Восстановление успешно завершено за {time_str}!")
            self.finished_signal.emit(True, f"Файлы успешно восстановлены из бэкапа за {time_str}!")

        except Exception as e:
            ru_error = translate_error(e)
            logging.error(f"[{name}] Ошибка восстановления: {ru_error}")
            if ssh_mgr and ssh_mgr.client and remote_archive_path:
                try:
                    ssh_mgr.client.exec_command(f"rm -f {remote_archive_path}")
                except:
                    pass
            self.finished_signal.emit(False, ru_error)
        finally:
            if ssh_mgr and ssh_mgr.client:
                ssh_mgr.client.close()