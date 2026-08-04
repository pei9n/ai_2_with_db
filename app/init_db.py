from database import SessionLocal
from models import User, MLModel


def init_demo_data():
    """Создать демо-данные, если их нет"""
    db = SessionLocal()

    # Проверяем, есть ли уже данные
    if db.query(User).first():
        db.close()
        print("Данные уже есть, пропускаем")
        return

    # Пользователи
    db.add(User(login="demo", password="demo123", role="user", balance=100))
    db.add(User(login="admin", password="admin123", role="admin", balance=1000))

    # ML-модели
    db.add(MLModel(name="Распознавание цифр v1", description="Базовая", cost=5))
    db.add(MLModel(name="Распознавание цифр v2", description="Точная", cost=10))
    db.add(MLModel(name="Премиум модель", description="С объяснением", cost=20))

    db.commit()
    db.close()
    print("Демо-данные созданы!")