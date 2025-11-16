import schedule
import time
from app.services.ticket_service import update_expired_tickets
from app.utils.database import get_db


def run_scheduler():
    """Запускает планировщик для автоматических задач"""
    # Ежедневная проверка просроченных талонов в 00:01
    schedule.every().day.at("00:01").do(update_expired_tickets)

    print("Планировщик запущен...")

    while True:
        schedule.run_pending()
        time.sleep(60)