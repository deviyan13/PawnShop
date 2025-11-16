from app.utils.database import query_db


def find_tariff(category_id, branch_id, estimated_cost):
    """
    Находит подходящий тариф по приоритету:
    1. Категория + Филиал
    2. Категория
    3. Филиал
    4. Общий тариф
    """
    try:
        # Сначала ищем наиболее специфичный тариф
        tariffs = query_db('''
            SELECT * FROM tariffs 
            WHERE is_active = true
              AND effective_from <= CURRENT_DATE
              AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
              AND (category_id = %s OR category_id IS NULL)
              AND (branch_id = %s OR branch_id IS NULL)
              AND (min_loan IS NULL OR min_loan <= %s)
              AND (max_loan IS NULL OR max_loan >= %s)
            ORDER BY 
              CASE 
                WHEN category_id IS NOT NULL AND branch_id IS NOT NULL THEN 1
                WHEN category_id IS NOT NULL AND branch_id IS NULL THEN 2
                WHEN category_id IS NULL AND branch_id IS NOT NULL THEN 3
                ELSE 4
              END,
              effective_from DESC
            LIMIT 1
        ''', (category_id, branch_id, estimated_cost, estimated_cost))

        if tariffs:
            return tariffs[0]

        # Если не нашли, пробуем найти любой активный тариф без проверки суммы
        fallback_tariff = query_db('''
            SELECT * FROM tariffs 
            WHERE is_active = true
              AND effective_from <= CURRENT_DATE
              AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
            ORDER BY 
              CASE 
                WHEN category_id IS NOT NULL AND branch_id IS NOT NULL THEN 1
                WHEN category_id IS NOT NULL AND branch_id IS NULL THEN 2
                WHEN category_id IS NULL AND branch_id IS NOT NULL THEN 3
                ELSE 4
              END
            LIMIT 1
        ''', one=True)

        return fallback_tariff

    except Exception as e:
        print(f"Error in find_tariff: {e}")
        return None