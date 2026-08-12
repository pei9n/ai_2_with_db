from database import SessionLocal
from orm_models import UserORM, MLModelORM


def init_demo_data():
    """Создать демо-данные, если их нет"""
    db = SessionLocal()

    # Проверяем, есть ли уже данные
    if db.query(UserORM).first():
        db.close()
        print("Данные уже есть, пропускаем")
        return

    # Пользователи
    db.add(UserORM(login="demo", password="demo123", role="UserORM", balance=100))
    db.add(UserORM(login="admin", password="admin123", role="admin", balance=1000))

    # ML-модели
    db.add(MLModelORM(name="Распознавание цифр v1", description="Базовая", cost=5))
    db.add(MLModelORM(name="Распознавание цифр v2", description="Точная", cost=10))
    db.add(MLModelORM(name="Премиум модель", description="С объяснением", cost=20))

    db.commit()
    db.close()
    print("Демо-данные созданы!")