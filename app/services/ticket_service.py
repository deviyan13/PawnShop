from app.utils.database import get_db, query_db
from datetime import datetime, date
from decimal import Decimal


def update_expired_tickets():
    """Обновляет статус талонов, у которых истек срок"""
    conn = get_db()
    cur = conn.cursor()

    try:
        # Находим талоны с истекшим сроком и статусом 'issued'
        cur.execute('''
            UPDATE pawn_tickets 
            SET status = 'defaulted', updated_at = NOW()
            WHERE status = 'issued' AND end_date < CURRENT_DATE
            RETURNING ticket_id, ticket_number
        ''')

        updated_tickets = cur.fetchall()

        # Логируем действие для каждого просроченного талона
        import json
        for ticket in updated_tickets:
            cur.execute('''
                INSERT INTO audit_logs (action_key, payload)
                VALUES (%s, %s)
            ''', (
                'ticket_expired_auto',
                json.dumps({
                    'ticket_id': ticket['ticket_id'],
                    'ticket_number': ticket['ticket_number']
                })
            ))

        conn.commit()

        if updated_tickets:
            print(f"Автоматически обновлено {len(updated_tickets)} просроченных талонов")

        return len(updated_tickets)

    except Exception as e:
        conn.rollback()
        print(f"Ошибка при обновлении просроченных талонов: {str(e)}")
        return 0


def calculate_loan_amount(estimated_cost, tariff):
    """Рассчитывает сумму займа на основе тарифа"""
    loan_amount = estimated_cost * Decimal(tariff['loan_percent']) / Decimal(100)

    if tariff['max_loan']:
        loan_amount = min(loan_amount, Decimal(tariff['max_loan']))

    if tariff['min_loan']:
        loan_amount = max(loan_amount, Decimal(tariff['min_loan']))

    return loan_amount


def calculate_ransom_amount(loan_amount, interest_rate, loan_days):
    """Рассчитывает сумму выкупа"""
    monthly_rate = Decimal(interest_rate) / Decimal(100)
    # Преобразуем срок в месяцы (30 дней = 1 месяц)
    months = Decimal(loan_days) / Decimal(30)
    ransom_amount = loan_amount * (1 + monthly_rate * months)
    return ransom_amount