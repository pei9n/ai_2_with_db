 ML Digit Recognition Service

Сервис распознавания рукописных цифр с использованием ML-модели.

 Функциональность

- Регистрация и авторизация пользователей
- Управление балансом (пополнение/списание)
- Отправка ML-задач на предсказание
- Асинхронная обработка через RabbitMQ
- История транзакций и ML-запросов
- Web-интерфейс (личный кабинет)
- REST API

 Технологии

- Python 3.11
- FastAPI
- SQLAlchemy (PostgreSQL)
- RabbitMQ
- Docker / Docker Compose
- Jinja2
- Nginx

 Структура проекта

project/

app/

  main.py # FastAPI приложени
  
  database.py # подключение к БД
  
  orm_models.py # SQLAlchemy модели
  
  service.py # бизнес-логика
  
  init_db.py # демо-данные
  
  worker.py # ML-воркер
  
  templates/ # HTML шаблоны
  
  static/ # CSS
  
  requirements.txt
  
  .env
  
  Dockerfile
  
 web-proxy/
  nginx.conf
  Dockerfile
 docker-compose.yml


 Запуск

 Требования

- Docker
- Docker Compose

 Шаги

1. Клонировать репозиторий:
bash
git clone <URL>

Запустить все сервисы
docker compose up -d --build

Подождать 10-15 секунд (инициализация БД и демо-данных).

http://localhost/health

Доступ к сервисам

Сервис	URL	Логин/Пароль

Web-интерфейс	http://localhost	—

Swagger API	http://localhost/docs	—

RabbitMQ UI	http://localhost:15672	guest/guest

PostgreSQL	localhost:5432	ml_user/ml_password

Демо-пользователи

Логин	Пароль	Баланс

demo	demo123	100₽

admin	admin123	1000₽

REST API

Метод	URL	Описание

POST	/auth/register	Регистрация

POST	/auth/login	Вход

GET	/users/me	Данные пользователя

GET	/balance	Баланс

POST	/balance/deposit	Пополнение

POST	/predict	ML-запрос

GET	/history/tasks	История задач

GET	/history/transactions	История транзакций

GET	/task/{task_id}	Задача по ID


Тестирование
# Запустить тесты
python app/test.py

Остановка
docker compose down

