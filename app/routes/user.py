from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.utils.auth import get_current_user
from app.utils.database import get_db, query_db
from app.forms import RequestForm
from datetime import datetime
from app.services.ticket_service import update_expired_tickets

user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        flash('Пожалуйста, войдите в систему', 'error')
        return redirect(url_for('auth.login'))

    # Обновляем статусы просроченных талонов
    update_expired_tickets()

    # Получаем заявки пользователя
    requests = query_db('''
        SELECT r.*, b.name as branch_name, ic.name as category_name 
        FROM requests r 
        JOIN branches b ON r.branch_id = b.branch_id 
        JOIN item_categories ic ON r.category_id = ic.category_id 
        WHERE r.user_id = %s 
        ORDER BY r.created_at DESC
    ''', [user['user_id']])

    # Получаем активные талоны
    tickets = query_db('''
        SELECT pt.*, b.name as branch_name, i.name as item_name
        FROM pawn_tickets pt
        JOIN branches b ON pt.branch_id = b.branch_id
        JOIN items i ON pt.item_id = i.item_id
        WHERE pt.user_id = %s AND pt.status = 'issued'
        ORDER BY pt.created_at DESC
    ''', [user['user_id']])

    return render_template('user/dashboard.html', requests=requests, tickets=tickets)


@user_bp.route('/request/new', methods=['GET', 'POST'])
def new_request():
    user = get_current_user()
    if not user:
        flash('Пожалуйста, войдите в систему', 'error')
        return redirect(url_for('auth.login'))

    form = RequestForm()

    if form.validate_on_submit():
        conn = get_db()
        cur = conn.cursor()

        # Генерируем номер заявки
        request_number = f"REQ-{datetime.now().strftime('%Y%m%d')}-{user['user_id']}-{datetime.now().timestamp()}"

        try:
            cur.execute('''
                INSERT INTO requests 
                (request_number, user_id, branch_id, category_id, item_name, item_description, estimated_cost) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                request_number,
                user['user_id'],
                form.branch_id.data,
                form.category_id.data,
                form.item_name.data,
                form.item_description.data,
                form.estimated_cost.data
            ))
            conn.commit()

            import json
            cur.execute('''
                INSERT INTO audit_logs (user_id, action_key, payload)
                VALUES (%s, %s, %s)
            ''', (
                user['user_id'],
                'create_request',
                json.dumps({
                    'request_number': request_number,
                    'item_name': form.item_name.data,
                    'estimated_cost': float(form.estimated_cost.data)
                })
            ))
            conn.commit()

            flash('Заявка успешно создана!', 'success')
            return redirect(url_for('user.dashboard'))

        except Exception as e:
            conn.rollback()
            flash(f'Ошибка при создании заявки: {str(e)}', 'error')

    return render_template('user/new_request.html', form=form)


@user_bp.route('/tickets')
def tickets():
    user = get_current_user()
    if not user:
        flash('Пожалуйста, войдите в систему', 'error')
        return redirect(url_for('auth.login'))

    # Получаем активные талоны пользователя
    tickets = query_db('''
        SELECT pt.*, b.name as branch_name, i.name as item_name,
               i.description as item_description, ic.name as category_name,
               CASE 
                   WHEN pt.status = 'issued' THEN 'Активен'
                   WHEN pt.status = 'redeemed' THEN 'Выкуплен'
                   WHEN pt.status = 'defaulted' THEN 'Просрочен'
                   ELSE pt.status
               END as status_text
        FROM pawn_tickets pt
        JOIN branches b ON pt.branch_id = b.branch_id
        JOIN items i ON pt.item_id = i.item_id
        JOIN item_categories ic ON i.category_id = ic.category_id
        WHERE pt.user_id = %s
        ORDER BY pt.created_at DESC
    ''', [user['user_id']])

    return render_template('user/tickets.html', tickets=tickets)

@user_bp.route('/requests')
def my_requests():
    user = get_current_user()
    if not user:
        flash('Пожалуйста, войдите в систему', 'error')
        return redirect(url_for('auth.login'))

    requests = query_db('''
        SELECT r.*, b.name as branch_name, ic.name as category_name,
               CASE 
                   WHEN r.status = 'submitted' THEN 'На рассмотрении'
                   WHEN r.status = 'approved' THEN 'Одобрена'
                   WHEN r.status = 'rejected' THEN 'Отклонена'
                   ELSE r.status
               END as status_text
        FROM requests r 
        JOIN branches b ON r.branch_id = b.branch_id 
        JOIN item_categories ic ON r.category_id = ic.category_id 
        WHERE r.user_id = %s 
        ORDER BY r.created_at DESC
    ''', [user['user_id']])

    return render_template('user/requests.html', requests=requests)