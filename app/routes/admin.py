from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.utils.auth import get_current_user
from app.utils.database import get_db, query_db
from app.services.tariff_service import find_tariff
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Декоратор для проверки прав администратора"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or session.get('user_role') != 1:
            flash('Доступ запрещен. Требуются права администратора.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Получаем филиалы, к которым привязан администратор
    user_branches = query_db('''
        SELECT b.* FROM user_branches ub
        JOIN branches b ON ub.branch_id = b.branch_id
        WHERE ub.user_id = %s
    ''', [session['user_id']])

    branch_ids = [b['branch_id'] for b in user_branches]

    # Статистика по заявкам
    pending_requests = query_db('''
        SELECT COUNT(*) as count FROM requests 
        WHERE status = 'submitted' AND branch_id = ANY(%s)
    ''', [branch_ids], one=True)

    active_tickets = query_db('''
        SELECT COUNT(*) as count FROM pawn_tickets 
        WHERE status = 'issued' AND branch_id = ANY(%s)
    ''', [branch_ids], one=True)

    # Последние заявки
    recent_requests = query_db('''
        SELECT r.*, u.first_name, u.last_name, b.name as branch_name, ic.name as category_name
        FROM requests r
        JOIN users u ON r.user_id = u.user_id
        JOIN branches b ON r.branch_id = b.branch_id
        JOIN item_categories ic ON r.category_id = ic.category_id
        WHERE r.status = 'submitted' AND r.branch_id = ANY(%s)
        ORDER BY r.created_at DESC
        LIMIT 10
    ''', [branch_ids])

    return render_template('admin/dashboard.html',
                           pending_requests=pending_requests['count'],
                           active_tickets=active_tickets['count'],
                           recent_requests=recent_requests,
                           branches=user_branches)


@admin_bp.route('/requests')
@admin_required
def requests():
    # Получаем филиалы администратора
    user_branches = query_db('''
        SELECT b.branch_id FROM user_branches ub
        JOIN branches b ON ub.branch_id = b.branch_id
        WHERE ub.user_id = %s
    ''', [session['user_id']])

    branch_ids = [b['branch_id'] for b in user_branches]

    status_filter = request.args.get('status', 'submitted')

    requests = query_db('''
        SELECT r.*, u.first_name, u.last_name, u.email, u.phone,
               b.name as branch_name, ic.name as category_name
        FROM requests r
        JOIN users u ON r.user_id = u.user_id
        JOIN branches b ON r.branch_id = b.branch_id
        JOIN item_categories ic ON r.category_id = ic.category_id
        WHERE r.status = %s AND r.branch_id = ANY(%s)
        ORDER BY r.created_at DESC
    ''', [status_filter, branch_ids])

    return render_template('admin/requests.html',
                           requests=requests,
                           status_filter=status_filter)


@admin_bp.route('/request/<int:request_id>')
@admin_required
def request_detail(request_id):
    request_data = query_db('''
        SELECT r.*, u.first_name, u.last_name, u.email, u.phone,
               b.name as branch_name, ic.name as category_name
        FROM requests r
        JOIN users u ON r.user_id = u.user_id
        JOIN branches b ON r.branch_id = b.branch_id
        JOIN item_categories ic ON r.category_id = ic.category_id
        WHERE r.request_id = %s
    ''', [request_id], one=True)

    if not request_data:
        flash('Заявка не найдена', 'error')
        return redirect(url_for('admin.requests'))

    # Проверяем, что заявка принадлежит филиалу администратора
    user_branches = query_db('''
        SELECT branch_id FROM user_branches WHERE user_id = %s
    ''', [session['user_id']])

    branch_ids = [b['branch_id'] for b in user_branches]
    if request_data['branch_id'] not in branch_ids:
        flash('У вас нет доступа к этой заявке', 'error')
        return redirect(url_for('admin.requests'))

    # Ищем подходящий тариф
    tariff = find_tariff(request_data['category_id'], request_data['branch_id'], request_data['estimated_cost'])

    return render_template('admin/request_detail.html',
                           request=request_data,
                           tariff=tariff)


@admin_bp.route('/request/<int:request_id>/approve', methods=['POST'])
@admin_required
def approve_request(request_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        # Получаем данные заявки
        request_data = query_db('SELECT * FROM requests WHERE request_id = %s', [request_id], one=True)

        if not request_data or request_data['status'] != 'submitted':
            flash('Невозможно обработать заявку', 'error')
            return redirect(url_for('admin.requests'))

        # Находим подходящий тариф
        tariff = find_tariff(request_data['category_id'], request_data['branch_id'], request_data['estimated_cost'])

        if not tariff:
            flash('Не найден подходящий тариф', 'error')
            return redirect(url_for('admin.request_detail', request_id=request_id))

        # Рассчитываем суммы
        loan_amount = min(
            request_data['estimated_cost'] * tariff['loan_percent'] / 100,
            tariff['max_loan'] if tariff['max_loan'] else float('inf')
        )
        loan_amount = max(loan_amount, tariff['min_loan'] if tariff['min_loan'] else 0)

        # Выкупная сумма (заём + проценты за 1 месяц)
        ransom_amount = loan_amount * (1 + tariff['interest_rate'] / 100)

        # Создаем запись вещи
        cur.execute('''
            INSERT INTO items (owner_user_id, branch_id, category_id, name, description, estimated_cost)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING item_id
        ''', (
            request_data['user_id'],
            request_data['branch_id'],
            request_data['category_id'],
            request_data['item_name'],
            request_data['item_description'],
            request_data['estimated_cost']
        ))
        item_id = cur.fetchone()['item_id']

        # Создаем талон
        ticket_number = f"TKT-{datetime.now().strftime('%Y%m%d')}-{request_id}"
        admission_date = datetime.now().date()
        end_date = admission_date + timedelta(days=30)  # 30 дней

        cur.execute('''
            INSERT INTO pawn_tickets 
            (ticket_number, request_id, user_id, item_id, branch_id, admission_date, end_date,
             loan_amount, ransom_amount, tariff_id, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            ticket_number,
            request_id,
            request_data['user_id'],
            item_id,
            request_data['branch_id'],
            admission_date,
            end_date,
            loan_amount,
            ransom_amount,
            tariff['tariff_id'],
            'issued',
            session['user_id']
        ))

        # Обновляем статус заявки
        cur.execute('UPDATE requests SET status = %s WHERE request_id = %s',
                    ('approved', request_id))

        # Логируем действие
        import json
        cur.execute('''
            INSERT INTO audit_logs (user_id, action_key, payload)
            VALUES (%s, %s, %s)
        ''', (
            session['user_id'],
            'approve_request',
            json.dumps({
                'request_id': request_id,
                'ticket_number': ticket_number,
                'loan_amount': float(loan_amount),
                'ransom_amount': float(ransom_amount)
            })
        ))

        conn.commit()
        flash('Заявка одобрена! Талон успешно создан.', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Ошибка при обработке заявки: {str(e)}', 'error')

    return redirect(url_for('admin.requests'))


@admin_bp.route('/request/<int:request_id>/reject', methods=['POST'])
@admin_required
def reject_request(request_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute('UPDATE requests SET status = %s WHERE request_id = %s',
                    ('rejected', request_id))

        # Логируем действие
        import json
        cur.execute('''
            INSERT INTO audit_logs (user_id, action_key, payload)
            VALUES (%s, %s, %s)
        ''', (
            session['user_id'],
            'reject_request',
            json.dumps({'request_id': request_id})
        ))
        conn.commit()
        flash('Заявка отклонена', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Ошибка при отклонении заявки: {str(e)}', 'error')

    return redirect(url_for('admin.requests'))


@admin_bp.route('/tickets')
@admin_required
def tickets():
    # Получаем филиалы администратора
    user_branches = query_db('''
        SELECT b.branch_id FROM user_branches ub
        JOIN branches b ON ub.branch_id = b.branch_id
        WHERE ub.user_id = %s
    ''', [session['user_id']])

    branch_ids = [b['branch_id'] for b in user_branches]

    status_filter = request.args.get('status', 'issued')

    tickets = query_db('''
        SELECT pt.*, u.first_name, u.last_name, u.phone,
               b.name as branch_name, i.name as item_name,
               ic.name as category_name,
               CASE 
                   WHEN pt.status = 'issued' THEN 'Активен'
                   WHEN pt.status = 'redeemed' THEN 'Выкуплен'
                   WHEN pt.status = 'defaulted' THEN 'Просрочен'
                   ELSE pt.status
               END as status_text
        FROM pawn_tickets pt
        JOIN users u ON pt.user_id = u.user_id
        JOIN branches b ON pt.branch_id = b.branch_id
        JOIN items i ON pt.item_id = i.item_id
        JOIN item_categories ic ON i.category_id = ic.category_id
        WHERE pt.status = %s AND pt.branch_id = ANY(%s)
        ORDER BY pt.end_date ASC
    ''', [status_filter, branch_ids])

    return render_template('admin/tickets.html', tickets=tickets, status_filter=status_filter)


@admin_bp.route('/ticket/<int:ticket_id>/redeem', methods=['POST'])
@admin_required
def redeem_ticket(ticket_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        # Обновляем статус талона
        cur.execute('UPDATE pawn_tickets SET status = %s, updated_at = NOW() WHERE ticket_id = %s',
                    ('redeemed', ticket_id))

        # Создаем запись о платеже
        cur.execute('''
            INSERT INTO payments (ticket_id, amount, payment_type, processed_by)
            SELECT ticket_id, ransom_amount, 'ransom', %s
            FROM pawn_tickets 
            WHERE ticket_id = %s
        ''', (session['user_id'], ticket_id))

        # Логируем действие
        import json
        cur.execute('''
            INSERT INTO audit_logs (user_id, action_key, payload)
            VALUES (%s, %s, %s)
        ''', (
            session['user_id'],
            'redeem_ticket',
            json.dumps({'ticket_id': ticket_id})
        ))

        conn.commit()
        flash('Талон успешно выкуплен!', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'Ошибка при выкупе талона: {str(e)}', 'error')

    return redirect(url_for('admin.tickets'))


@admin_bp.route('/branches')
@admin_required
def branches():
    # Получаем филиалы администратора с статистикой
    user_branches = query_db('''
        SELECT b.*, ub.is_primary,
               (SELECT COUNT(*) FROM requests r WHERE r.branch_id = b.branch_id AND r.status = 'submitted') as pending_requests,
               (SELECT COUNT(*) FROM pawn_tickets pt WHERE pt.branch_id = b.branch_id AND pt.status = 'issued') as active_tickets,
               (SELECT COALESCE(SUM(loan_amount), 0) FROM pawn_tickets pt WHERE pt.branch_id = b.branch_id AND pt.status = 'issued') as total_loans
        FROM user_branches ub
        JOIN branches b ON ub.branch_id = b.branch_id
        WHERE ub.user_id = %s
        ORDER BY ub.is_primary DESC, b.name
    ''', [session['user_id']])

    return render_template('admin/branches.html', branches=user_branches)


@admin_bp.route('/reports')
@admin_required
def reports():
    # Получаем филиалы администратора
    user_branches = query_db('''
        SELECT b.branch_id FROM user_branches ub
        JOIN branches b ON ub.branch_id = b.branch_id
        WHERE ub.user_id = %s
    ''', [session['user_id']])

    branch_ids = [b['branch_id'] for b in user_branches]

    # Статистика по заявкам
    requests_stats = query_db('''
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'submitted') as pending,
            COUNT(*) FILTER (WHERE status = 'approved') as approved,
            COUNT(*) FILTER (WHERE status = 'rejected') as rejected
        FROM requests 
        WHERE branch_id = ANY(%s)
    ''', [branch_ids], one=True)

    # Статистика по талонам
    tickets_stats = query_db('''
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'issued') as active,
            COUNT(*) FILTER (WHERE status = 'redeemed') as redeemed,
            COUNT(*) FILTER (WHERE status = 'defaulted') as defaulted,
            COALESCE(SUM(loan_amount), 0) as total_loans,
            COALESCE(SUM(ransom_amount), 0) as total_ransom
        FROM pawn_tickets 
        WHERE branch_id = ANY(%s)
    ''', [branch_ids], one=True)

    # Самые активные пользователи
    top_users = query_db('''
        SELECT u.first_name, u.last_name, u.email,
               COUNT(r.request_id) as request_count,
               COALESCE(SUM(r.estimated_cost), 0) as total_estimated
        FROM users u
        LEFT JOIN requests r ON u.user_id = r.user_id
        WHERE r.branch_id = ANY(%s) OR r.branch_id IS NULL
        GROUP BY u.user_id, u.first_name, u.last_name, u.email
        ORDER BY request_count DESC
        LIMIT 5
    ''', [branch_ids])

    return render_template('admin/reports.html',
                           requests_stats=requests_stats,
                           tickets_stats=tickets_stats,
                           top_users=top_users)