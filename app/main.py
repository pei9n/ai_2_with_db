import json
import uuid
import pika
from datetime import datetime
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from database import create_tables, SessionLocal
from init_db import init_demo_data
from service import deposit, predict, get_history, get_transactions
from orm_models import UserORM, MLModelORM

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
QUEUE_NAME = "ml_tasks"

app = FastAPI(title="ML Digit Recognition API")
security = HTTPBasic()


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=4)


class DepositRequest(BaseModel):
    amount: float = Field(gt=0)


class PredictRequest(BaseModel):
    model_id: int = Field(gt=0)
    x1: float = 1.2
    x2: float = 5.7

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str


def get_user(credentials: HTTPBasicCredentials = Depends(security)):
    db = SessionLocal()
    user = db.query(UserORM).filter(UserORM.login == credentials.username).first()
    db.close()
    if not user or user.password != credentials.password:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return user


@app.on_event("startup")
def startup():
    create_tables()
    init_demo_data()



@app.post("/auth/register")
def register(data: RegisterRequest):
    db = SessionLocal()
    if db.query(UserORM).filter(UserORM.login == data.login).first():
        db.close()
        raise HTTPException(400, "Логин занят")
    user = UserORM(login=data.login, password=data.password, role="user", balance=0)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return {"id": user.id, "login": user.login, "role": user.role, "balance": user.balance}

@app.post("/auth/login")
def login(credentials: HTTPBasicCredentials = Depends(security)):
    """Вход в систему — проверка логина и пароля"""
    db = SessionLocal()
    user = db.query(UserORM).filter(UserORM.login == credentials.username).first()
    db.close()
    
    if not user or user.password != credentials.password:
        raise HTTPException(401, "Неверный логин или пароль")
    
    return {"id": user.id, "login": user.login, "role": user.role, "balance": user.balance}


@app.get("/users/me")
def me(user: UserORM = Depends(get_user)):
    return {"id": user.id, "login": user.login, "role": user.role, "balance": user.balance}


@app.get("/balance")
def balance(user: UserORM = Depends(get_user)):
    return {"balance": user.balance}


@app.post("/balance/deposit")
def deposit_money(data: DepositRequest, user: UserORM = Depends(get_user)):
    new_balance = deposit(user.id, data.amount)
    return {"balance": new_balance, "message": f"Пополнено {data.amount}₽"}


@app.post("/predict")
def make_prediction(data: PredictRequest, user: UserORM = Depends(get_user)):
    """Отправить ML-задачу в очередь RabbitMQ"""
    # Генерируем ID задачи
    task_id = str(uuid.uuid4())
    
    # Проверяем модель
    db = SessionLocal()
    model = db.query(MLModelORM).filter(MLModelORM.id == data.model_id).first()
    db.close()
    
    if not model:
        raise HTTPException(404, "Модель не найдена")
    
    if user.balance < model.cost_predict:
        raise HTTPException(402, f"Недостаточно средств! Нужно: {model.cost_predict}")
    
    # Формируем сообщение
    message = {
        "task_id": task_id,
        "features": {"x1": data.x1, "x2": data.x2},
        "model": model.name,
        "timestamp": datetime.now().isoformat()
    }
    
    # Отправляем в RabbitMQ
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
        )
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
    except Exception as e:
        raise HTTPException(500, f"Ошибка RabbitMQ: {e}")
    
    return {
        "status": "accepted",
        "task_id": task_id,
        "message": "Задача отправлена в очередь",
        "model": model.name
    }


@app.get("/history/tasks")
def tasks_history(user: UserORM = Depends(get_user)):
    tasks = get_history(user.id)
    return [{"id": t.id, "status": t.status, "result": t.result, "date": str(t.created_at)} for t in tasks]


@app.get("/history/transactions")
def transactions_history(user: UserORM = Depends(get_user)):
    txns = get_transactions(user.id)
    return [{"type": t.type_of_tran, "summa": t.summa, "date": str(t.date_time)} for t in txns]


@app.get("/health")
def health():
    return {"status": "OK"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("APP_PORT", "8000")))

