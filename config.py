import logging
import re
from db import get_user_data, update_user_balance, log_user_activity, get_user_activity, get_transaction_history, delete_user_account, get_all_users
from utils import is_valid_vk_id, is_valid_username

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Функция обработки команды /start
def start_command(user_id):
    """Обработчик команды /start."""
    logging.info(f"Команда /start для пользователя {user_id}")
    user_data = get_user_data(user_id)
    if user_data:
        return f"👋 Привет, {user_data['username']}! Ваш баланс: {user_data['balance']}."
    else:
        return "❌ Пользователь не найден."

# Функция обработки команды /balance
def balance_command(user_id):
    """Обработчик команды /balance."""
    logging.info(f"Команда /balance для пользователя {user_id}")
    user_data = get_user_data(user_id)
    if user_data:
        return f"💰 Ваш баланс: {user_data['balance']}."
    else:
        return "❌ Пользователь не найден."

# Функция обработки команды /deposit
def deposit_command(user_id, amount):
    """Обработчик команды /deposit для пополнения счета."""
    logging.info(f"Пополнение счета пользователя {user_id} на {amount} рублей")
    user_data = get_user_data(user_id)
    if user_data:
        new_balance = update_user_balance(user_id, amount)
        log_user_activity(user_id, "Пополнение", f"Пополнение на {amount} рублей.")
        return f"✅ Баланс пополнен! Новый баланс: {new_balance}."
    else:
        return "❌ Пользователь не найден."

# Функция обработки команды /withdraw
def withdraw_command(user_id, amount):
    """Обработчик команды /withdraw для снятия средств."""
    logging.info(f"Снятие средств с баланса пользователя {user_id} на {amount} рублей")
    user_data = get_user_data(user_id)
    if user_data:
        if user_data['balance'] >= amount:
            new_balance = update_user_balance(user_id, -amount)
            log_user_activity(user_id, "Снятие", f"Снятие на {amount} рублей.")
            return f"✅ Средства сняты! Новый баланс: {new_balance}."
        else:
            return "❌ Недостаточно средств на счете."
    else:
        return "❌ Пользователь не найден."

# Функция обработки команды /history
def history_command(user_id):
    """Обработчик команды /history для получения истории транзакций."""
    logging.info(f"Запрос истории транзакций пользователя {user_id}")
    transactions = get_transaction_history(user_id)
    return transactions if transactions else "❌ История транзакций пуста."

# Функция обработки команды /activity
def activity_command(user_id):
    """Обработчик команды /activity для получения истории активности пользователя."""
    logging.info(f"Запрос истории активности пользователя {user_id}")
    activities = get_user_activity(user_id)
    return activities if activities else "❌ Нет активности для данного пользователя."

# Функция обработки команды /delete_account
def delete_account_command(user_id):
    """Обработчик команды /delete_account для удаления аккаунта."""
    logging.info(f"Удаление аккаунта пользователя {user_id}")
    result = delete_user_account(user_id)
    return result

# Функция обработки команды /users
def all_users_command():
    """Обработчик команды /users для получения списка всех пользователей."""
    logging.info("Запрос списка всех пользователей")
    users = get_all_users()
    return users if users else "❌ Нет пользователей в системе."

# Проверка валидности ID или username
def validate_vk_user(identifier):
    """Проверяет, является ли переданный идентификатор валидным (id или username)."""
    if is_valid_vk_id(identifier):
        return f"✅ Это валидный VK ID: {identifier}"
    elif is_valid_username(identifier):
        return f"✅ Это валидный username: {identifier}"
    else:
        return "❌ Невалидный идентификатор. Пожалуйста, укажите корректный VK ID или username."

# Основной обработчик входящих команд
def handle_command(command, *args):
    """Обработчик команд."""
    if command == "/start":
        return start_command(args[0])
    elif command == "/balance":
        return balance_command(args[0])
    elif command == "/deposit":
        return deposit_command(args[0], float(args[1]))
    elif command == "/withdraw":
        return withdraw_command(args[0], float(args[1]))
    elif command == "/history":
        return history_command(args[0])
    elif command == "/activity":
        return activity_command(args[0])
    elif command == "/delete_account":
        return delete_account_command(args[0])
    elif command == "/users":
        return all_users_command()
    elif command == "/validate":
        return validate_vk_user(args[0])
    else:
        return "❌ Неизвестная команда."

# Пример использования:
if __name__ == "__main__":
    user_id = "12345"  # Пример id пользователя
    print(handle_command("/start", user_id))  # Команда /start
    print(handle_command("/balance", user_id))  # Команда /balance
    print(handle_command("/deposit", user_id, "100"))  # Команда /deposit
    print(handle_command("/withdraw", user_id, "50"))  # Команда /withdraw
    print(handle_command("/history", user_id))  # Команда /history
    print(handle_command("/activity", user_id))  # Команда /activity
    print(handle_command("/delete_account", user_id))  # Команда /delete_account
    print(handle_command("/users"))  # Команда /users
    print(handle_command("/validate", "username"))  # Команда /validate
