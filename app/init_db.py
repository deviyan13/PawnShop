import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def init_database():
    """Создает все таблицы в базе данных"""

    # Подключаемся к БД
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'flask_pawn_shop_db'),
        user=os.getenv('DB_USER', 'lombard_user'),
        password=os.getenv('DB_PASSWORD', '123456')
    )
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # Создаем схему если не существует
        schema = os.getenv('DB_SCHEMA', 'lombard')
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

        # Устанавливаем схему поиска
        cur.execute(f"SET search_path TO {schema}, public")

        print("Создание таблиц...")

        # SQL для создания таблиц (из вашего ТЗ)
        sql_script = """
        
        CREATE SCHEMA IF NOT EXISTS lombard;
        SET search_path = lombard, public;
        
        -- 1. roles
        CREATE TABLE IF NOT EXISTS roles (
            role_id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            role_name VARCHAR(50) NOT NULL UNIQUE,
            description TEXT
        );
        
        -- 2. branches (филиалы)
        CREATE TABLE IF NOT EXISTS branches (
            branch_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name VARCHAR(150) NOT NULL UNIQUE,
            address TEXT,
            phone VARCHAR(30),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
        );
        
        -- 3. users (клиенты и работники - БЕЗ привязки к филиалу)
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL, -- изменено на хэш
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            phone VARCHAR(30),
            role_id SMALLINT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(role_id) ON DELETE RESTRICT
        );
        
        -- 4. item_categories
        CREATE TABLE IF NOT EXISTS item_categories (
            category_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name VARCHAR(120) NOT NULL UNIQUE,
            description TEXT
        );
        
        -- 5. requests (заявки - привязываются к филиалу)
        CREATE TABLE IF NOT EXISTS requests (
            request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            request_number VARCHAR(60) NOT NULL UNIQUE,
            user_id BIGINT NOT NULL, -- кто подал заявку
            branch_id INT NOT NULL, -- в какой филиал подана заявка
            category_id INT NOT NULL,
            item_name VARCHAR(200) NOT NULL,
            item_description TEXT,
            estimated_cost NUMERIC(12,2) NOT NULL CHECK (estimated_cost >= 0),
            status VARCHAR(50) NOT NULL DEFAULT 'submitted', -- submitted, cancelled, approved, rejected
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT fk_request_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            CONSTRAINT fk_request_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE RESTRICT,
            CONSTRAINT fk_request_category FOREIGN KEY (category_id) REFERENCES item_categories(category_id) ON DELETE RESTRICT
        );
        
        -- 6. items (создаётся при одобрении заявки админом)
        CREATE TABLE IF NOT EXISTS items (
            item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            owner_user_id BIGINT NOT NULL,
            branch_id INT, -- филиал, где хранится вещь
            category_id INT NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            estimated_cost NUMERIC(12,2) NOT NULL CHECK (estimated_cost >= 0),
            declared_characteristics JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT fk_item_owner FOREIGN KEY (owner_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            CONSTRAINT fk_item_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE SET NULL,
            CONSTRAINT fk_item_category FOREIGN KEY (category_id) REFERENCES item_categories(category_id) ON DELETE RESTRICT
        );
        
        -- 7. tariffs (упрощенная и улучшенная структура)
        CREATE TABLE IF NOT EXISTS tariffs (
            tariff_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            category_id INT, -- NULL = для всех категорий
            branch_id INT, -- NULL = для всех филиалов
            loan_percent NUMERIC(6,3) NOT NULL CHECK (loan_percent >= 0 AND loan_percent <= 100), -- % от оценочной стоимости
            interest_rate NUMERIC(6,3) NOT NULL CHECK (interest_rate >= 0), -- процентная ставка в месяц
            min_loan NUMERIC(12,2) DEFAULT 0,
            max_loan NUMERIC(12,2),
            effective_from DATE NOT NULL,
            effective_to DATE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            description TEXT,
            CONSTRAINT fk_tariff_category FOREIGN KEY (category_id) REFERENCES item_categories(category_id) ON DELETE SET NULL,
            CONSTRAINT fk_tariff_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE SET NULL,
            CONSTRAINT chk_tariff_dates CHECK (effective_to IS NULL OR effective_to > effective_from)
        );
        
        -- 8. pawn_tickets (талон - создаётся при оформлении заявки)
        CREATE TABLE IF NOT EXISTS pawn_tickets (
            ticket_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            ticket_number VARCHAR(60) NOT NULL UNIQUE,
            request_id BIGINT, -- ссылка на исходную заявку
            user_id BIGINT NOT NULL, -- владелец/клиент
            item_id BIGINT NOT NULL,
            branch_id INT NOT NULL,
            admission_date DATE NOT NULL,
            end_date DATE NOT NULL,
            loan_amount NUMERIC(12,2) NOT NULL CHECK (loan_amount >= 0),
            ransom_amount NUMERIC(12,2) NOT NULL CHECK (ransom_amount >= 0),
            tariff_id BIGINT NOT NULL, -- ссылка на примененный тариф
            status VARCHAR(50) NOT NULL, -- issued, redeemed, defaulted, archived
            created_by BIGINT, -- админ, оформивший талон
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT fk_ticket_request FOREIGN KEY (request_id) REFERENCES requests(request_id) ON DELETE RESTRICT,
            CONSTRAINT fk_ticket_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
            CONSTRAINT fk_ticket_item FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE RESTRICT,
            CONSTRAINT fk_ticket_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE RESTRICT,
            CONSTRAINT fk_ticket_creator FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
            CONSTRAINT fk_ticket_tariff FOREIGN KEY (tariff_id) REFERENCES tariffs(tariff_id) ON DELETE RESTRICT
        );
        
        -- 9. payments
        CREATE TABLE IF NOT EXISTS payments (
            payment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            ticket_id BIGINT NOT NULL,
            amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
            payment_type VARCHAR(50) NOT NULL, -- 'ransom','extension','fee','penalty'
            payment_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            processed_by BIGINT,
            note TEXT,
            CONSTRAINT fk_payments_ticket FOREIGN KEY (ticket_id) REFERENCES pawn_tickets(ticket_id) ON DELETE CASCADE,
            CONSTRAINT fk_payments_user FOREIGN KEY (processed_by) REFERENCES users(user_id) ON DELETE SET NULL
        );
        
        -- 10. attachments
        CREATE TABLE IF NOT EXISTS attachments (
            attachment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            item_id BIGINT,
            request_id BIGINT,
            ticket_id BIGINT,
            file_path TEXT NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            mime_type VARCHAR(100),
            uploaded_by BIGINT,
            uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT fk_attach_item FOREIGN KEY (item_id) REFERENCES items(item_id) ON DELETE CASCADE,
            CONSTRAINT fk_attach_request FOREIGN KEY (request_id) REFERENCES requests(request_id) ON DELETE CASCADE,
            CONSTRAINT fk_attach_ticket FOREIGN KEY (ticket_id) REFERENCES pawn_tickets(ticket_id) ON DELETE CASCADE,
            CONSTRAINT fk_attach_user FOREIGN KEY (uploaded_by) REFERENCES users(user_id) ON DELETE SET NULL,
            CHECK (
                (CASE WHEN item_id IS NOT NULL THEN 1 ELSE 0 END)
                + (CASE WHEN request_id IS NOT NULL THEN 1 ELSE 0 END)
                + (CASE WHEN ticket_id IS NOT NULL THEN 1 ELSE 0 END)
                = 1
            )
        );
        
        -- 11. audit_logs
        CREATE TABLE IF NOT EXISTS audit_logs (
            log_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id BIGINT, -- nullable для system actions
            action_key VARCHAR(100) NOT NULL,
            action_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            ip_address INET,
            user_agent TEXT,
            payload JSONB,
            CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
        );
        
        -- 12. user_branches (новая таблица для связи админов с филиалами)
        CREATE TABLE IF NOT EXISTS user_branches (
            user_id BIGINT NOT NULL,
            branch_id INT NOT NULL,
            is_primary BOOLEAN NOT NULL DEFAULT FALSE,
            assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT pk_user_branches PRIMARY KEY (user_id, branch_id),
            CONSTRAINT fk_ub_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            CONSTRAINT fk_ub_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE CASCADE
        );
        
        -- ================= Индексы =================
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status);
        CREATE INDEX IF NOT EXISTS idx_requests_user ON requests(user_id);
        CREATE INDEX IF NOT EXISTS idx_requests_branch ON requests(branch_id);
        CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner_user_id);
        CREATE INDEX IF NOT EXISTS idx_tickets_status ON pawn_tickets(status);
        CREATE INDEX IF NOT EXISTS idx_tickets_user ON pawn_tickets(user_id);
        CREATE INDEX IF NOT EXISTS idx_payments_ticket ON payments(ticket_id);
        CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(action_time);
        CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_tariffs_active ON tariffs(is_active, effective_from, effective_to);
        CREATE INDEX IF NOT EXISTS idx_tariffs_category_branch ON tariffs(category_id, branch_id);
        
        -- ================ Триггеры для updated_at =================
        CREATE OR REPLACE FUNCTION lombard_set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        
        CREATE TRIGGER trg_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE PROCEDURE lombard_set_updated_at();
        
        CREATE TRIGGER trg_requests_updated_at
            BEFORE UPDATE ON requests
            FOR EACH ROW EXECUTE PROCEDURE lombard_set_updated_at();
        
        CREATE TRIGGER trg_tickets_updated_at
            BEFORE UPDATE ON pawn_tickets
            FOR EACH ROW EXECUTE PROCEDURE lombard_set_updated_at();
        
        
        
        -- Функция для выбора подходящего тарифа
        CREATE OR REPLACE FUNCTION find_tariff(
            p_category_id INT,
            p_branch_id INT,
            p_estimated_cost NUMERIC
        ) RETURNS tariffs AS $$
        DECLARE
            selected_tariff tariffs;
        BEGIN
            -- Приоритет выбора: категория+филиал -> категория -> филиал -> общий
            SELECT * INTO selected_tariff
            FROM tariffs 
            WHERE is_active = true
              AND effective_from <= CURRENT_DATE
              AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
              AND (category_id = p_category_id OR category_id IS NULL)
              AND (branch_id = p_branch_id OR branch_id IS NULL)
              AND (min_loan IS NULL OR min_loan <= p_estimated_cost)
              AND (max_loan IS NULL OR max_loan >= p_estimated_cost)
            ORDER BY 
                CASE 
                    WHEN category_id = p_category_id AND branch_id = p_branch_id THEN 1
                    WHEN category_id = p_category_id AND branch_id IS NULL THEN 2
                    WHEN category_id IS NULL AND branch_id = p_branch_id THEN 3
                    ELSE 4
                END,
                effective_from DESC
            LIMIT 1;
            
            RETURN selected_tariff;
        END;
        $$ LANGUAGE plpgsql;
        """

        # Выполняем SQL скрипт
        cur.execute(sql_script)

        print("Таблицы успешно созданы!")

    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    init_database()