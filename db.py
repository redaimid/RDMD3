import requests
import logging
import uuid
import config
import datetime
import psycopg2
from psycopg2 import sql

# Конфигурация для работы с PostgreSQL
DB_CONNECTION = {
    'dbname': 'your_db',      # имя базы данных
    'user': 'your_user',      # имя пользователя
    'password': 'your_password',
    'host': 'your_host',      # например, localhost
}

def get_db_connection():
    """Создает и возвращает соединение с базой данных."""
    try:
        conn = psycopg2.connect(**DB_CONNECTION)
        return conn
    except Exception as e:
        logging.error(f"Ошибка подключения к базе данных: {e}")
        return None

def get_user_from_db(user_id):
    """Получает пользователя по vk_id или username."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT * FROM users WHERE vk_id = %s OR username = %s LIMIT 1"),
            [user_id, user_id]
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        logging.error(f"Ошибка при получении пользователя {user_id}: {e}")
        return None

def get_user_by_username(username):
    """Получает пользователя по username."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT * FROM users WHERE username = %s LIMIT 1"),
            [username]
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        logging.error(f"Ошибка при поиске пользователя {username}: {e}")
        return None

def register_user(user_id):
    """Регистрирует нового пользователя."""
    try:
        user_data = {
            "id": str(uuid.uuid4()),
            "username": f"User_{user_id}",
            "vk_id": user_id,
            "balance": 0.0,
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        conn = get_db_connection()
        if conn is None:
            return False

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO users (id, username, vk_id, balance, created_at) VALUES (%s, %s, %s, %s, %s)"),
            [user_data["id"], user_data["username"], user_data["vk_id"], user_data["balance"], user_data["created_at"]]
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Ошибка при регистрации пользователя {user_id}: {e}")
        return False

def update_user_name(user_id, new_name):
    """Обновляет имя пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return False

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("UPDATE users SET username = %s WHERE vk_id = %s"),
            [new_name, user_id]
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Ошибка при обновлении имени пользователя {user_id}: {e}")
        return False

def record_operation(vk_id, op_type, amount, details):
    """Записывает операцию в таблицу операций."""
    try:
        operation_data = {
            "id": str(uuid.uuid4()),
            "operation_tip": op_type,
            "amount": amount,
            "details": f"vk_id: {vk_id} - {details}",
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        conn = get_db_connection()
        if conn is None:
            return False

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO operations (id, operation_tip, amount, details, created_at) VALUES (%s, %s, %s, %s, %s)"),
            [operation_data["id"], operation_data["operation_tip"], operation_data["amount"], operation_data["details"], operation_data["created_at"]]
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Ошибка при записи операции: {e}")
        return False

def get_operations(vk_id):
    """Получает историю операций для пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return []

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT * FROM operations WHERE details LIKE %s ORDER BY created_at DESC"),
            [f"%vk_id: {vk_id}%"]
        )
        operations = cursor.fetchall()
        cursor.close()
        conn.close()
        return operations
    except Exception as e:
        logging.error(f"Ошибка при получении истории операций для пользователя {vk_id}: {e}")
        return []

def transfer_balance(from_user_id, to_user_id, amount):
    """Переводит средства от одного пользователя к другому."""
    try:
        from_user = get_user_from_db(from_user_id)
        to_user = get_user_from_db(to_user_id)

        if not from_user or not to_user:
            return "❌ Один из пользователей не найден."

        if from_user['balance'] < amount:
            return "❌ Недостаточно средств для перевода."

        # Обновление баланса отправителя
        new_balance_from = from_user['balance'] - amount
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("UPDATE users SET balance = %s WHERE vk_id = %s"),
            [new_balance_from, from_user_id]
        )
        # Обновление баланса получателя
        new_balance_to = to_user['balance'] + amount
        cursor.execute(
            sql.SQL("UPDATE users SET balance = %s WHERE vk_id = %s"),
            [new_balance_to, to_user_id]
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Запись операций
        record_operation(from_user_id, "transfer_sent", -amount, f"Перевод средств пользователю {to_user['username']}")
        record_operation(to_user_id, "transfer_received", amount, f"Получены средства от пользователя {from_user['username']}")

        return f"✅ Перевод {amount} средств пользователю {to_user['username']} выполнен успешно."
    except Exception as e:
        logging.error(f"Ошибка при переводе средств: {e}")
        return "❌ Ошибка при переводе средств. Попробуйте позже."
def get_balance(user_id):
    """Получает текущий баланс пользователя."""
    try:
        user = get_user_from_db(user_id)
        if user:
            return f"💰 Ваш текущий баланс: {user['balance']}."
        else:
            return "❌ Пользователь не найден."
    except Exception as e:
        logging.error(f"Ошибка при получении баланса пользователя {user_id}: {e}")
        return "❌ Ошибка при получении баланса."

def deposit_balance(user_id, amount):
    """Пополнение баланса пользователя."""
    try:
        user = get_user_from_db(user_id)
        if not user:
            return "❌ Пользователь не найден."

        new_balance = user['balance'] + amount
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("UPDATE users SET balance = %s WHERE vk_id = %s"),
            [new_balance, user_id]
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Запись операции пополнения
        record_operation(user_id, "deposit", amount, f"Пополнение баланса на {amount}")
        return f"✅ Ваш баланс пополнен на {amount}. Новый баланс: {new_balance}."
    except Exception as e:
        logging.error(f"Ошибка при пополнении баланса пользователя {user_id}: {e}")
        return "❌ Ошибка при пополнении баланса. Попробуйте позже."

def withdraw_balance(user_id, amount):
    """Вывод средств с баланса пользователя."""
    try:
        user = get_user_from_db(user_id)
        if not user:
            return "❌ Пользователь не найден."

        if user['balance'] < amount:
            return "❌ Недостаточно средств для вывода."

        new_balance = user['balance'] - amount
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("UPDATE users SET balance = %s WHERE vk_id = %s"),
            [new_balance, user_id]
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Запись операции вывода
        record_operation(user_id, "withdrawal", -amount, f"Вывод средств на {amount}")
        return f"✅ Ваш баланс был уменьшен на {amount}. Новый баланс: {new_balance}."
    except Exception as e:
        logging.error(f"Ошибка при выводе баланса пользователя {user_id}: {e}")
        return "❌ Ошибка при выводе средств. Попробуйте позже."

def get_user_history(user_id):
    """Получает историю операций пользователя."""
    try:
        operations = get_operations(user_id)
        if not operations:
            return "❌ История операций пуста."

        history = "📜 История операций:\n"
        for op in operations:
            history += f"Тип операции: {op[1]}, Сумма: {op[2]}, Дата: {op[4]}\n"
        return history
    except Exception as e:
        logging.error(f"Ошибка при получении истории операций для пользователя {user_id}: {e}")
        return "❌ Ошибка при получении истории операций."

# Функция для отправки сообщения в Telegram или VK
def send_message(user_id, message):
    """Отправляет сообщение пользователю."""
    try:
        # Здесь можно добавить интеграцию с VK API или Telegram Bot API
        # Например, для Telegram:
        response = requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": user_id, "text": message}
        )
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        return False

def record_operation(user_id, operation_type, amount, details):
    """Записывает операцию в базу данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO operations (user_id, operation_type, amount, details, created_at) VALUES (%s, %s, %s, %s, now())"),
            [user_id, operation_type, amount, details]
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logging.error(f"Ошибка при записи операции для пользователя {user_id}: {e}")

def get_operations(user_id):
    """Получает все операции пользователя из базы данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT * FROM operations WHERE user_id = %s ORDER BY created_at DESC"),
            [user_id]
        )
        operations = cursor.fetchall()
        cursor.close()
        conn.close()
        return operations
    except Exception as e:
        logging.error(f"Ошибка при получении операций пользователя {user_id}: {e}")
        return None

def add_user(vk_id, username=None):
    """Добавляет нового пользователя в базу данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO users (vk_id, username, balance, created_at) VALUES (%s, %s, %s, now())"),
            [vk_id, username, 0]
        )
        conn.commit()
        cursor.close()
        conn.close()
        return "✅ Новый пользователь добавлен в базу данных."
    except Exception as e:
        logging.error(f"Ошибка при добавлении пользователя {vk_id}: {e}")
        return "❌ Ошибка при добавлении пользователя."

def update_username(vk_id, new_username):
    """Обновляет имя пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("UPDATE users SET username = %s WHERE vk_id = %s"),
            [new_username, vk_id]
        )
        conn.commit()
        cursor.close()
        conn.close()
        return f"✅ Имя пользователя
            return None

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT * FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        logging.error(f"Ошибка при получении данных пользователя {vk_id}: {e}")
        return None

def update_balance(vk_id, amount, operation_type):
    """Обновляет баланс пользователя в базе данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        # Получаем текущий баланс
        cursor.execute(
            sql.SQL("SELECT balance FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        current_balance = cursor.fetchone()
        if current_balance is None:
            return "❌ Пользователь не найден в базе данных."

        new_balance = current_balance[0] + amount
        if new_balance < 0:
            return "❌ Недостаточно средств на балансе."

        # Обновляем баланс
        cursor.execute(
            sql.SQL("UPDATE users SET balance = %s WHERE vk_id = %s"),
            [new_balance, vk_id]
        )
        # Записываем операцию в таблицу операций
        record_operation(vk_id, operation_type, amount, f"Обновление баланса на {amount}")
        conn.commit()
        cursor.close()
        conn.close()

        return f"✅ Баланс обновлен. Новый баланс: {new_balance}."
    except Exception as e:
        logging.error(f"Ошибка при обновлении баланса пользователя {vk_id}: {e}")
        return "❌ Ошибка при обновлении баланса."

def get_balance(vk_id):
    """Получает текущий баланс пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT balance FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        balance = cursor.fetchone()
        cursor.close()
        conn.close()
        if balance is None:
            return "❌ Пользователь не найден."
        return f"Ваш текущий баланс: {balance[0]}."
    except Exception as e:
        logging.error(f"Ошибка при получении баланса пользователя {vk_id}: {e}")
        return "❌ Ошибка при получении баланса."
def get_user_from_db(vk_id):
    """Получает пользователя по vk_id."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT * FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        logging.error(f"Ошибка при получении данных пользователя {vk_id}: {e}")
        return None

def register_user(user_id):
    """Регистрирует нового пользователя в базе данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        # Генерация уникального ID для нового пользователя
        user_data = {
            "vk_id": user_id,
            "username": f"User_{user_id}",
            "balance": 0.0,
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        
        cursor.execute(
            sql.SQL("INSERT INTO users (vk_id, username, balance, created_at) VALUES (%s, %s, %s, %s)"),
            [user_data['vk_id'], user_data['username'], user_data['balance'], user_data['created_at']]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Регистрация прошла успешно!"
    except Exception as e:
        logging.error(f"Ошибка при регистрации пользователя {user_id}: {e}")
        return "❌ Ошибка регистрации."

def update_user_name(vk_id, new_name):
    """Обновляет имя пользователя в базе данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        # Проверка длины нового имени
        if len(new_name) < 3 or len(new_name) > 20:
            return "❌ Имя должно быть от 3 до 20 символов."

        cursor.execute(
            sql.SQL("UPDATE users SET username = %s WHERE vk_id = %s"),
            [new_name, vk_id]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return f"✅ Имя успешно изменено на {new_name}."
    except Exception as e:
        logging.error(f"Ошибка при обновлении имени пользователя {vk_id}: {e}")
        return "❌ Ошибка при изменении имени."

def record_operation(vk_id, op_type, amount, details):
    """Записывает операцию в таблицу операций."""
    try:
        conn = get_db_connection()
        if conn is None:
            return False

        cursor = conn.cursor()
        operation_data = {
            "vk_id": vk_id,
            "operation_tip": op_type,
            "amount": amount,
            "details": details,
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        cursor.execute(
            sql.SQL("INSERT INTO operations (vk_id, operation_tip, amount, details, created_at) VALUES (%s, %s, %s, %s, %s)"),
            [operation_data['vk_id'], operation_data['operation_tip'], operation_data['amount'], operation_data['details'], operation_data['created_at']]
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        logging.error(f"Ошибка при записи операции {details}: {e}")
        return False

def get_operations(vk_id):
    """Получает историю операций пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return []

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT * FROM operations WHERE vk_id = %s ORDER BY created_at DESC"),
            [vk_id]
        )
        operations = cursor.fetchall()
        cursor.close()
        conn.close()
        return operations
    except Exception as e:
        logging.error(f"Ошибка при получении истории операций для пользователя {vk_id}: {e}")
        return []
def get_user_balance(vk_id):
    """Получает баланс пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT balance FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        balance = cursor.fetchone()
        cursor.close()
        conn.close()
        if balance:
            return balance[0]
        return 0.0
    except Exception as e:
        logging.error(f"Ошибка при получении баланса для пользователя {vk_id}: {e}")
        return 0.0

def update_user_balance(vk_id, new_balance):
    """Обновляет баланс пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("UPDATE users SET balance = %s WHERE vk_id = %s"),
            [new_balance, vk_id]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return f"✅ Баланс успешно обновлён на {new_balance}."
    except Exception as e:
        logging.error(f"Ошибка при обновлении баланса для пользователя {vk_id}: {e}")
        return "❌ Ошибка при обновлении баланса."

def transfer_balance(from_vk_id, to_vk_id, amount):
    """Перевод средств между двумя пользователями."""
    try:
        from_balance = get_user_balance(from_vk_id)
        to_balance = get_user_balance(to_vk_id)

        if from_balance is None or to_balance is None:
            return "❌ Ошибка получения баланса одного из пользователей."

        if from_balance < amount:
            return "❌ Недостаточно средств на балансе для перевода."

        # Обновляем балансы обоих пользователей
        new_from_balance = from_balance - amount
        new_to_balance = to_balance + amount

        # Обновляем данные в базе
        update_user_balance(from_vk_id, new_from_balance)
        update_user_balance(to_vk_id, new_to_balance)

        # Записываем операцию перевода
        record_operation(from_vk_id, "перевод", -amount, f"Перевод на {to_vk_id}")
        record_operation(to_vk_id, "перевод", amount, f"Перевод от {from_vk_id}")

        return f"✅ Перевод в размере {amount} успешно выполнен от {from_vk_id} к {to_vk_id}."
    except Exception as e:
        logging.error(f"Ошибка при переводе средств с {from_vk_id} на {to_vk_id}: {e}")
        return "❌ Ошибка при выполнении перевода."

def get_user_info(vk_id):
    """Получает полную информацию о пользователе."""
    try:
        user = get_user_from_db(vk_id)
        if not user:
            return "❌ Пользователь не найден."

        username = user[1]  # предполагаем, что имя в 2-й колонке
        balance = user[2]  # предполагаем, что баланс в 3-й колонке
        created_at = user[4]  # предполагаем, что дата регистрации в 5-й колонке

        return f"Информация о пользователе {username}:\n" \
               f"Баланс: {balance}💰\n" \
               f"Дата регистрации: {created_at}"

    except Exception as e:
        logging.error(f"Ошибка при получении информации о пользователе {vk_id}: {e}")
        return "❌ Ошибка при получении информации о пользователе."

def delete_user(vk_id):
    """Удаляет пользователя из базы данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("DELETE FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return f"✅ Пользователь с ID {vk_id} успешно удалён."
    except Exception as e:
        logging.error(f"Ошибка при удалении пользователя {vk_id}: {e}")
        return "❌ Ошибка при удалении пользователя."

# Пример использования:
if __name__ == "__main__":
    vk_id_example = "12345"

    # Регистрация нового пользователя
    print(register_user(vk_id_example))

    # Получение информации о пользователе
    print(get_user_info(vk_id_example))

    # Изменение имени пользователя
    print(update_user_name(vk_id_example, "NewUsername"))

    # Перевод средств
    print(transfer_balance("12345", "67890", 50))

    # Удаление пользователя
    print(delete_user(vk_id_example))
def record_operation(vk_id, operation_type, amount, details):
    """Записывает операцию в базу данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO operations (vk_id, operation_type, amount, details, created_at) "
                    "VALUES (%s, %s, %s, %s, now())"),
            [vk_id, operation_type, amount, details]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Операция успешно сохранена."
    except Exception as e:
        logging.error(f"Ошибка при записи операции для пользователя {vk_id}: {e}")
        return "❌ Ошибка при записи операции."

def get_user_operations(vk_id):
    """Получает список операций пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT operation_type, amount, details, created_at FROM operations WHERE vk_id = %s ORDER BY created_at DESC"),
            [vk_id]
        )
        operations = cursor.fetchall()
        cursor.close()
        conn.close()

        if not operations:
            return "❌ Нет операций для данного пользователя."

        operations_list = "📜 История операций:\n"
        for operation in operations:
            operation_type = operation[0]
            amount = operation[1]
            details = operation[2]
            created_at = operation[3]
            operations_list += f"{operation_type} - {amount} (Детали: {details}) - {created_at}\n"

        return operations_list
    except Exception as e:
        logging.error(f"Ошибка при получении операций для пользователя {vk_id}: {e}")
        return "❌ Ошибка при получении операций."

def add_funds(vk_id, amount):
    """Пополнение баланса пользователя."""
    try:
        current_balance = get_user_balance(vk_id)

        if current_balance is None:
            return "❌ Ошибка получения текущего баланса."

        new_balance = current_balance + amount
        update_user_balance(vk_id, new_balance)

        # Записываем операцию пополнения
        record_operation(vk_id, "пополнение", amount, f"Пополнение баланса на {amount}.")

        return f"✅ Баланс успешно пополнен на {amount}. Новый баланс: {new_balance}."
    except Exception as e:
        logging.error(f"Ошибка при пополнении баланса для пользователя {vk_id}: {e}")
        return "❌ Ошибка при пополнении баланса."

def withdraw_funds(vk_id, amount):
    """Снятие средств с баланса пользователя."""
    try:
        current_balance = get_user_balance(vk_id)

        if current_balance is None:
            return "❌ Ошибка получения текущего баланса."

        if current_balance < amount:
            return "❌ Недостаточно средств для снятия."

        new_balance = current_balance - amount
        update_user_balance(vk_id, new_balance)

        # Записываем операцию снятия
        record_operation(vk_id, "снятие", -amount, f"Снятие баланса на {amount}.")

        return f"✅ Баланс успешно снят на {amount}. Новый баланс: {new_balance}."
    except Exception as e:
        logging.error(f"Ошибка при снятии средств для пользователя {vk_id}: {e}")
        return "❌ Ошибка при снятии средств."

def get_system_info():
    """Получает общую информацию о системе."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT sum(balance) FROM users")
        total_balance = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return f"📊 Общая информация:\n" \
               f"Пользователей: {total_users}\n" \
               f"Общий баланс: {total_balance if total_balance else 0}💰"
    except Exception as e:
        logging.error(f"Ошибка при получении информации о системе: {e}")
        return "❌ Ошибка при получении системной информации."

# Пример использования:
if __name__ == "__main__":
    vk_id_example = "12345"

    # Регистрация нового пользователя
    print(register_user(vk_id_example))

    # Пополнение баланса
    print(add_funds(vk_id_example, 100))

    # Снятие средств
    print(withdraw_funds(vk_id_example, 50))

    # Получение информации о пользователе
    print(get_user_info(vk_id_example))

    # Получение операций пользователя
    print(get_user_operations(vk_id_example))

    # Получение системной информации
    print(get_system_info())
# Продолжение работы с функциями и логикой

def update_user_balance(vk_id, new_balance):
    """Обновляет баланс пользователя в базе данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("UPDATE users SET balance = %s WHERE vk_id = %s"),
            [new_balance, vk_id]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return f"✅ Баланс успешно обновлен: {new_balance}."
    except Exception as e:
        logging.error(f"Ошибка при обновлении баланса для пользователя {vk_id}: {e}")
        return "❌ Ошибка при обновлении баланса."

def get_user_balance(vk_id):
    """Получает текущий баланс пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None  # Если нет соединения, возвращаем None

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT balance FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        balance = cursor.fetchone()

        cursor.close()
        conn.close()

        if balance is None:
            return None  # Если баланс не найден, возвращаем None

        return balance[0]  # Возвращаем сам баланс
    except Exception as e:
        logging.error(f"Ошибка при получении баланса для пользователя {vk_id}: {e}")
        return None

def register_user(vk_id):
    """Регистрация нового пользователя в системе."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO users (vk_id, balance) VALUES (%s, %s) ON CONFLICT (vk_id) DO NOTHING"),
            [vk_id, 0]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Пользователь успешно зарегистрирован."
    except Exception as e:
        logging.error(f"Ошибка при регистрации пользователя {vk_id}: {e}")
        return "❌ Ошибка при регистрации пользователя."

def get_user_info(vk_id):
    """Получает информацию о пользователе."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT vk_id, balance FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user is None:
            return "❌ Пользователь не найден."

        return f"🧑‍💼 Информация о пользователе:\nVK ID: {user[0]}\nБаланс: {user[1]}💰"
    except Exception as e:
        logging.error(f"Ошибка при получении информации о пользователе {vk_id}: {e}")
        return "❌ Ошибка при получении информации о пользователе."

def record_system_event(event_type, message):
    """Записывает системные события в базу данных для аудита."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO system_events (event_type, message, created_at) VALUES (%s, %s, now())"),
            [event_type, message]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Системное событие успешно записано."
    except Exception as e:
        logging.error(f"Ошибка при записи системного события: {e}")
        return "❌ Ошибка при записи системного события."

def get_system_events():
    """Получает список всех системных событий."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute("SELECT event_type, message, created_at FROM system_events ORDER BY created_at DESC")
        events = cursor.fetchall()

        cursor.close()
        conn.close()

        if not events:
            return "❌ Нет системных событий."

        events_list = "📜 Системные события:\n"
        for event in events:
            event_type = event[0]
            message = event[1]
            created_at = event[2]
            events_list += f"{event_type} - {message} - {created_at}\n"

        return events_list
    except Exception as e:
        logging.error(f"Ошибка при получении системных событий: {e}")
        return "❌ Ошибка при получении системных событий."

# Пример использования:
if __name__ == "__main__":
    vk_id_example = "12345"

    # Регистрация нового пользователя
    print(register_user(vk_id_example))

    # Пополнение баланса
    print(add_funds(vk_id_example, 100))

    # Снятие средств
    print(withdraw_funds(vk_id_example, 50))

    # Получение информации о пользователе
    print(get_user_info(vk_id_example))

    # Получение операций пользователя
    print(get_user_operations(vk_id_example))

    # Получение системной информации
    print(get_system_info())

    # Получение системных событий
    print(get_system_events())

    # Запись системного события
    print(record_system_event("INFO", "Бот запущен успешно"))
# Дополнительные функции для работы с базой данных и расширения функционала

def add_funds(vk_id, amount):
    """Функция для добавления средств на счет пользователя."""
    try:
        # Проверяем текущий баланс пользователя перед добавлением средств
        current_balance = get_user_balance(vk_id)
        if current_balance is None:
            return "❌ Пользователь не найден."

        new_balance = current_balance + amount
        update_balance_result = update_user_balance(vk_id, new_balance)

        # Записываем операцию пополнения
        record_user_operation(vk_id, 'deposit', amount, f"Пополнение на {amount} рублей")

        return f"✅ Пополнение счета на {amount} рублей. Новый баланс: {new_balance}."
    except Exception as e:
        logging.error(f"Ошибка при добавлении средств на счет пользователя {vk_id}: {e}")
        return "❌ Ошибка при добавлении средств на счет."

def withdraw_funds(vk_id, amount):
    """Функция для снятия средств с аккаунта пользователя."""
    try:
        current_balance = get_user_balance(vk_id)
        if current_balance is None:
            return "❌ Пользователь не найден."

        if current_balance < amount:
            return "❌ Недостаточно средств на счете для снятия."

        new_balance = current_balance - amount
        update_balance_result = update_user_balance(vk_id, new_balance)

        # Записываем операцию снятия
        record_user_operation(vk_id, 'withdraw', amount, f"Снятие {amount} рублей")

        return f"✅ Снятие {amount} рублей. Новый баланс: {new_balance}."
    except Exception as e:
        logging.error(f"Ошибка при снятии средств с аккаунта пользователя {vk_id}: {e}")
        return "❌ Ошибка при снятии средств."

def record_user_operation(vk_id, operation_type, amount, details):
    """Записывает операцию пользователя (пополнение/снятие) в базу данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO operations (vk_id, operation_type, amount, details) VALUES (%s, %s, %s, %s)"),
            [vk_id, operation_type, amount, details]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Операция успешно записана."
    except Exception as e:
        logging.error(f"Ошибка при записи операции пользователя {vk_id}: {e}")
        return "❌ Ошибка при записи операции."

def get_user_operations(vk_id):
    """Получает список операций пользователя по его VK ID."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT operation_type, amount, details, created_at FROM operations WHERE vk_id = %s ORDER BY created_at DESC"),
            [vk_id]
        )
        operations = cursor.fetchall()

        cursor.close()
        conn.close()

        if not operations:
            return "❌ Нет операций для данного пользователя."

        operations_list = "📝 Операции пользователя:\n"
        for op in operations:
            op_type = op[0]
            op_amount = op[1]
            op_details = op[2]
            op_created_at = op[3]
            operations_list += f"{op_type} - {op_amount} - {op_details} - {op_created_at}\n"

        return operations_list
    except Exception as e:
        logging.error(f"Ошибка при получении операций пользователя {vk_id}: {e}")
        return "❌ Ошибка при получении операций."

def record_error_message(vk_id, error_message):
    """Записывает сообщение об ошибке в базу данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO system_errors (vk_id, error_message, created_at) VALUES (%s, %s, now())"),
            [vk_id, error_message]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Сообщение об ошибке успешно записано."
    except Exception as e:
        logging.error(f"Ошибка при записи сообщения об ошибке пользователя {vk_id}: {e}")
        return "❌ Ошибка при записи сообщения об ошибке."

# Пример обработки ошибок, вызов функций
if __name__ == "__main__":
    # Пример ошибок
    print(record_error_message("12345", "Не удалось выполнить операцию пополнения"))
    print(record_user_operation("12345", "deposit", 200, "Пополнение счета"))
    print(get_user_operations("12345"))
    
    # Пополнение баланса
    print(add_funds("12345", 150))

    # Снятие средств
    print(withdraw_funds("12345", 50))

    # Получение информации о пользователе
    print(get_user_info("12345"))
    
    # Запись системного события
    print(record_system_event("WARNING", "Низкий баланс для пользователя 12345"))

    # Получение системных событий
    print(get_system_events())
# Дальше продолжаем добавление дополнительных функций для работы с базой данных, обеспечения логирования и взаимодействия с другими частями системы.

def get_system_events(event_type=None):
    """Получает системные события из базы данных (по типу события или все)."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()

        # Если тип события не передан, получаем все события
        if event_type:
            cursor.execute(
                sql.SQL("SELECT event_type, message, created_at FROM system_events WHERE event_type = %s ORDER BY created_at DESC"),
                [event_type]
            )
        else:
            cursor.execute(
                sql.SQL("SELECT event_type, message, created_at FROM system_events ORDER BY created_at DESC")
            )
        
        events = cursor.fetchall()

        cursor.close()
        conn.close()

        if not events:
            return "❌ Нет системных событий."

        events_list = "🗂 Системные события:\n"
        for event in events:
            event_type = event[0]
            event_message = event[1]
            event_created_at = event[2]
            events_list += f"{event_type} - {event_message} - {event_created_at}\n"

        return events_list
    except Exception as e:
        logging.error(f"Ошибка при получении системных событий: {e}")
        return "❌ Ошибка при получении системных событий."

def record_system_event(event_type, message):
    """Записывает системное событие в базу данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO system_events (event_type, message, created_at) VALUES (%s, %s, now())"),
            [event_type, message]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Системное событие успешно записано."
    except Exception as e:
        logging.error(f"Ошибка при записи системного события: {e}")
        return "❌ Ошибка при записи системного события."

def get_user_info(vk_id):
    """Получает информацию о пользователе, включая баланс и количество операций."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT vk_id, balance, created_at FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        user_info = cursor.fetchone()

        cursor.close()
        conn.close()

        if not user_info:
            return "❌ Пользователь не найден."

        vk_id = user_info[0]
        balance = user_info[1]
        created_at = user_info[2]

        user_info_str = f"📋 Информация о пользователе:\n"
        user_info_str += f"ID пользователя: {vk_id}\n"
        user_info_str += f"Баланс: {balance}\n"
        user_info_str += f"Дата регистрации: {created_at}\n"

        return user_info_str
    except Exception as e:
        logging.error(f"Ошибка при получении информации о пользователе {vk_id}: {e}")
        return "❌ Ошибка при получении информации о пользователе."

def update_user_balance(vk_id, new_balance):
    """Обновляет баланс пользователя в базе данных."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("UPDATE users SET balance = %s WHERE vk_id = %s"),
            [new_balance, vk_id]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Баланс успешно обновлен."
    except Exception as e:
        logging.error(f"Ошибка при обновлении баланса пользователя {vk_id}: {e}")
        return "❌ Ошибка при обновлении баланса."

def get_user_balance(vk_id):
    """Получает текущий баланс пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return None  # если нет подключения, возвращаем None

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT balance FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            return result[0]
        else:
            return None
    except Exception as e:
        logging.error(f"Ошибка при получении баланса пользователя {vk_id}: {e}")
        return None

# Пример использования:
if __name__ == "__main__":
    # Пример записей о пользователе
    print(get_user_info("12345"))
    print(add_funds("12345", 500))  # Пополнение
    print(withdraw_funds("12345", 100))  # Снятие

    # Пример записи системного события
    print(record_system_event("INFO", "Пользователь успешно пополнил баланс"))
    print(get_system_events())  # Получаем все события
# Завершаем дополнительные функции для работы с базой данных и взаимодействие с другими частями системы.

def log_user_activity(vk_id, action_type, details):
    """Записывает действия пользователя в журнал."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("INSERT INTO user_activity (vk_id, action_type, details, created_at) VALUES (%s, %s, %s, now())"),
            [vk_id, action_type, details]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Действие пользователя успешно записано."
    except Exception as e:
        logging.error(f"Ошибка при записи действия пользователя {vk_id}: {e}")
        return "❌ Ошибка при записи действия пользователя."

def get_user_activity(vk_id):
    """Получает активность пользователя (действия) за все время."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT action_type, details, created_at FROM user_activity WHERE vk_id = %s ORDER BY created_at DESC"),
            [vk_id]
        )
        activities = cursor.fetchall()

        cursor.close()
        conn.close()

        if not activities:
            return "❌ Нет активности для данного пользователя."

        activity_list = "🗂 История действий пользователя:\n"
        for activity in activities:
            action_type = activity[0]
            details = activity[1]
            created_at = activity[2]
            activity_list += f"{action_type} - {details} - {created_at}\n"

        return activity_list
    except Exception as e:
        logging.error(f"Ошибка при получении активности пользователя {vk_id}: {e}")
        return "❌ Ошибка при получении активности пользователя."

def delete_user_account(vk_id):
    """Удаляет аккаунт пользователя и всю его информацию."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("DELETE FROM users WHERE vk_id = %s"),
            [vk_id]
        )
        conn.commit()
        cursor.close()
        conn.close()

        return "✅ Аккаунт пользователя успешно удален."
    except Exception as e:
        logging.error(f"Ошибка при удалении аккаунта пользователя {vk_id}: {e}")
        return "❌ Ошибка при удалении аккаунта пользователя."

def get_all_users():
    """Получает информацию обо всех пользователях."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT vk_id, balance, created_at FROM users ORDER BY created_at DESC")
        )
        users = cursor.fetchall()

        cursor.close()
        conn.close()

        if not users:
            return "❌ Нет пользователей в системе."

        users_list = "🗂 Все пользователи:\n"
        for user in users:
            vk_id = user[0]
            balance = user[1]
            created_at = user[2]
            users_list += f"ID пользователя: {vk_id} - Баланс: {balance} - Дата регистрации: {created_at}\n"

        return users_list
    except Exception as e:
        logging.error(f"Ошибка при получении списка всех пользователей: {e}")
        return "❌ Ошибка при получении списка пользователей."

def get_transaction_history(vk_id):
    """Получает историю транзакций пользователя."""
    try:
        conn = get_db_connection()
        if conn is None:
            return "❌ Ошибка подключения к базе данных."

        cursor = conn.cursor()
        cursor.execute(
            sql.SQL("SELECT transaction_type, amount, created_at FROM transactions WHERE vk_id = %s ORDER BY created_at DESC"),
            [vk_id]
        )
        transactions = cursor.fetchall()

        cursor.close()
        conn.close()

        if not transactions:
            return "❌ Нет транзакций для данного пользователя."

        transactions_list = "🗂 История транзакций:\n"
        for transaction in transactions:
            transaction_type = transaction[0]
            amount = transaction[1]
            created_at = transaction[2]
            transactions_list += f"{transaction_type} - Сумма: {amount} - Дата: {created_at}\n"

        return transactions_list
    except Exception as e:
        logging.error(f"Ошибка при получении истории транзакций пользователя {vk_id}: {e}")
        return "❌ Ошибка при получении истории транзакций."

# Пример использования:

if __name__ == "__main__":
    # Пример получения информации обо всех пользователях
    print(get_all_users())

    # Пример записи действий пользователя
    print(log_user_activity("12345", "Пополнение", "Пользователь пополнил баланс на 500"))

    # Пример получения активности пользователя
    print(get_user_activity("12345"))

    # Пример удаления аккаунта пользователя
    print(delete_user_account("12345"))

    # Пример получения истории транзакций пользователя
    print(get_transaction_history("12345"))
