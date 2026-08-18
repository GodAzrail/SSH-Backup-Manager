import logging
from apscheduler.schedulers.background import BackgroundScheduler
from database.db_manager import DBManager
from core.backup_manager import perform_background_backup

class BackupScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.db = DBManager()

    def start(self):
        self.scheduler.start()
        self.reload_jobs()
        logging.info("Планировщик запущен.")

    def reload_jobs(self):
        self.scheduler.remove_all_jobs()
        servers = self.db.get_all_servers()
        
        for srv in servers:
            # Если база старая и не имеет новых полей, пропускаем
            if len(srv) < 15: continue
            
            auto_backup = srv[9] 
            interval = srv[10] 
            schedule_type = srv[12]
            cron_day = srv[13]
            cron_time = srv[14]

            if auto_backup:
                if schedule_type == 'interval':
                    self.scheduler.add_job(
                        perform_background_backup, 
                        'interval', 
                        minutes=interval, 
                        args=[srv], 
                        id=f"server_{srv[0]}"
                    )
                    logging.info(f"Добавлена задача (Интервал) для {srv[1]}: каждые {interval} мин.")
                
                elif schedule_type == 'cron':
                    # Парсинг нового и старого форматов
                    schedules = []
                    if "|" in cron_day or ";" in cron_day:
                        # Новый формат: "mon;12:00|wed;15:00"
                        parts = cron_day.split("|")
                        for p in parts:
                            if ";" in p:
                                d, t = p.split(";")
                                schedules.append((d, t))
                    else:
                        # Старый формат: cron_day="mon", cron_time="12:00"
                        schedules.append((cron_day, cron_time))

                    # Создаем задачу для каждого расписания
                    for i, (c_day, c_time) in enumerate(schedules):
                        try:
                            hour, minute = map(int, c_time.split(':'))
                            self.scheduler.add_job(
                                perform_background_backup, 
                                'cron', 
                                day_of_week=c_day, 
                                hour=hour, 
                                minute=minute,
                                args=[srv], 
                                id=f"server_{srv[0]}_cron_{i}"
                            )
                            log_day = "Ежедневно" if c_day == "*" else c_day
                            logging.info(f"Добавлена задача (CRON) для {srv[1]}: {log_day} в {c_time}")
                        except Exception as e:
                            logging.error(f"Ошибка парсинга CRON для {srv[1]}: {e}")