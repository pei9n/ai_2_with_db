from datetime import datetime
from database import SessionLocal
from orm_models import UserORM, MLModelORM, TransactionORM, MLTaskORM


def deposit(user_id: int, amount: int):
    """Пополнение баланса"""
    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")
    
    db = SessionLocal()
    user = db.query(UserORM).filter(UserORM.id == user_id).first()
    
    if not user:
        db.close()
        raise ValueError("Пользователь не найден")
    
    user.balance += amount
    
    transaction = TransactionORM(
        type_of_tran="deposit",
        summa=amount,
        date_time=datetime.now(),
        user_id=user_id
    )
    db.add(transaction)
    db.commit()
    
    #  Сохраняем баланс ДО закрытия сессии
    new_balance = user.balance
    
    db.close()
    
    return new_balance  


def charge(user_id: int, amount: int):
    """Списание средств"""
    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")
    
    db = SessionLocal()
    user = db.query(UserORM).filter(UserORM.id == user_id).first()
    
    if not user:
        db.close()
        raise ValueError("Пользователь не найден")
    
    if user.balance < amount:
        db.close()
        raise ValueError(f"Недостаточно средств")
    
    user.balance -= amount
    
    transaction = TransactionORM(
        type_of_tran="charge",
        summa=amount,
        date_time=datetime.now(),
        user_id=user_id
    )
    db.add(transaction)
    db.commit()
    
    #  Сохраняем ДО закрытия
    new_balance = user.balance
    
    db.close()
    
    return new_balance


def predict(user_id: int, model_id: int, data=None):
    """Выполнить предсказание (как ML_task.run)"""
    db = SessionLocal()
    user = db.query(UserORM).filter(UserORM.id == user_id).first()
    model = db.query(MLModelORM).filter(MLModelORM.id == model_id).first()
    
    # Проверка баланса (как в ML_task.run)
    if user.balance < model.cost_predict:
        db.close()
        raise ValueError(f"Недостаточно средств! Нужно: {model.cost_predict}, есть: {user.balance}")
    
    # Списание
    user.balance -= model.cost_predict
    db.add(TransactionORM(
        type_of_tran="charge",
        summa=model.cost_predict,
        date_time=datetime.now(),
        user_id=user_id
    ))
    
    # Создаём задачу (статус Processing -> Completed)
    task = MLTaskORM(
        data=data,
        status="completed",
        result='{"digit": 5, "confidence": 0.98}',  # как predict() в ML_model
        user_id=user_id,
        model_id=model_id
    )
    db.add(task)
    db.commit()
    db.close()
    
    print(f"Предсказание выполнено! Цифра: 5, уверенность: 0.98")
    return {"digit": 5, "confidence": 0.98}


def get_user(user_id: int):
    """Получить пользователя"""
    db = SessionLocal()
    user = db.query(UserORM).filter(UserORM.id == user_id).first()
    db.close()
    return user


def get_history(user_id: int):
    """История ML-задач пользователя"""
    db = SessionLocal()
    tasks = (
        db.query(MLTaskORM)
        .filter(MLTaskORM.user_id == user_id)
        .order_by(MLTaskORM.created_at.desc())
        .all()
    )
    db.close()
    return tasks


def get_transactions(user_id: int):
    """История транзакций пользователя"""
    db = SessionLocal()
    transactions = (
        db.query(TransactionORM)
        .filter(TransactionORM.user_id == user_id)
        .order_by(TransactionORM.date_time.desc())
        .all()
    )
    db.close()
    return transactions