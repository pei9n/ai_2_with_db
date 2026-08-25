import requests
import json

BASE_URL = "http://localhost"
TEST_LOGIN = "0000"
TEST_PASSWORD = "0000"

def print_result(name, success, detail=""):
    """Вывод результата теста"""
    if success:
        print(f"✅ {name}")
    else:
        print(f"❌ {name} — {detail}")

def test_all():
    print("=" * 50)
    print("ТЕСТИРОВАНИЕ ML-СЕРВИСА")
    print("=" * 50)
    
    # Шаг 1: Регистрация
    print("\n📌 Шаг 1: Работа с пользователями")
    
    # Создание пользователя
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={"login": TEST_LOGIN, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        print_result("Создание пользователя", True)
    elif response.status_code == 400 and "занят" in response.text:
        print_result("Создание пользователя", True, "уже существует")
    else:
        print_result("Создание пользователя", False, response.text)
    
    # Авторизация
    auth = (TEST_LOGIN, TEST_PASSWORD)
    response = requests.get(f"{BASE_URL}/users/me", auth=auth)
    print_result("Авторизация", response.status_code == 200)
    
    # Повторная авторизация
    response = requests.get(f"{BASE_URL}/users/me", auth=auth)
    print_result("Повторная авторизация", response.status_code == 200)
    
    # Ошибка при неверном пароле
    response = requests.get(f"{BASE_URL}/users/me", auth=(TEST_LOGIN, "wrong_pass"))
    print_result("Ошибка при неверном пароле", response.status_code == 401)
    
    # Шаг 2: Баланс
    print("\n📌 Шаг 2: Работа с балансом")
    
    # Текущий баланс
    response = requests.get(f"{BASE_URL}/balance", auth=auth)
    initial_balance = response.json()["balance"]
    print_result(f"Получение баланса (начальный: {initial_balance})", response.status_code == 200)
    
    # Пополнение
    response = requests.post(
        f"{BASE_URL}/balance/deposit",
        json={"amount": 100},
        auth=auth
    )
    print_result("Пополнение баланса", response.status_code == 200)
    
    # Обновлённый баланс
    response = requests.get(f"{BASE_URL}/balance", auth=auth)
    new_balance = response.json()["balance"]
    print_result(f"Баланс после пополнения: {new_balance}", new_balance == initial_balance + 100)
    
    # Шаг 3: ML-запросы и списание
    print("\n📌 Шаг 3: ML-запросы")
    
    # Успешный запрос
    balance_before = requests.get(f"{BASE_URL}/balance", auth=auth).json()["balance"]
    
    response = requests.post(
        f"{BASE_URL}/predict",
        json={"model_id": 1, "x1": 2.5, "x2": 3.7},
        auth=auth
    )
    print_result("Отправка ML-запроса", response.status_code == 200)
    
    task_id = None
    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print_result(f"Получен task_id: {task_id}", task_id is not None)
    
    # Баланс после списания
    balance_after = requests.get(f"{BASE_URL}/balance", auth=auth).json()["balance"]
    model_cost = 5.0
    print_result(
        f"Списание кредитов ({balance_before} → {balance_after})",
        balance_after == balance_before - model_cost
    )
    
    # Запрос при недостаточном балансе
    # Создаём пользователя без денег
    requests.post(f"{BASE_URL}/auth/register", json={"login": "poor_user", "password": "test123"})
    poor_auth = ("poor_user", "test123")
    
    response = requests.post(
        f"{BASE_URL}/predict",
        json={"model_id": 1, "x1": 1, "x2": 1},
        auth=poor_auth
    )
    print_result("Запрет при недостаточном балансе", response.status_code == 402)
    
    # Некорректные данные
    response = requests.post(
        f"{BASE_URL}/predict",
        json={"model_id": 999, "x1": 1, "x2": 1},
        auth=auth
    )
    print_result("Обработка некорректных данных (модель не найдена)", response.status_code == 404)
    
    # Шаг 4: Получение результата
    print("\n📌 Шаг 4: Получение результата")
    
    if task_id:
        response = requests.get(f"{BASE_URL}/task/{task_id}", auth=auth)
        print_result("Получение задачи по task_id", response.status_code == 200)
        if response.status_code == 200:
            task_data = response.json()
            print_result(f"Статус задачи: {task_data['status']}", True)
    
    # Шаг 5: История
    print("\n📌 Шаг 5: История операций")
    
    response = requests.get(f"{BASE_URL}/history/transactions", auth=auth)
    transactions = response.json()
    print_result(f"История транзакций ({len(transactions)} записей)", len(transactions) > 0)
    
    for t in transactions:
        print(f"  • {t['type']}: {t['summa']}₽ ({t['date']})")
    
    response = requests.get(f"{BASE_URL}/history/tasks", auth=auth)
    tasks = response.json()
    print_result(f"История ML-запросов ({len(tasks)} записей)", len(tasks) > 0)
    
    print("\n" + "=" * 50)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 50)


if __name__ == "__main__":
    test_all()