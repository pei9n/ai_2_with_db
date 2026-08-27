import json
import uuid
import pika
from datetime import datetime
import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from database import create_tables, SessionLocal
from init_db import init_demo_data
from service import deposit, predict, get_history, get_transactions
from orm_models import UserORM, MLModelORM, TransactionORM, MLTaskORM
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from fastapi import Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware



RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
QUEUE_NAME = "ml_tasks"


app = FastAPI(title="ML Digit Recognition API")
app.add_middleware(SessionMiddleware, secret_key="my-secret-key")
security = HTTPBasic()
templates = Jinja2Templates(directory="/app/templates")
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

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

def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    db = SessionLocal()
    user = db.query(UserORM).filter(UserORM.id == user_id).first()
    db.close()
    return user

@app.on_event("startup")
def startup():
    create_tables()
    init_demo_data()

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@app.get("/dashboard")
def dashboard_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    
    db = SessionLocal()
    transactions = db.query(TransactionORM).filter(TransactionORM.user_id == user.id).all()
    tasks = db.query(MLTaskORM).filter(MLTaskORM.user_id == user.id).all()
    db.close()
    
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user,
        "transactions": transactions,
        "tasks": tasks
    })


@app.post("/register")
def register_form(request: Request, login: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    if db.query(UserORM).filter(UserORM.login == login).first():
        db.close()
        return templates.TemplateResponse(request, "register.html", {"error": "Логин занят"})
    
    user = UserORM(login=login, password=password, role="user", balance=0)
    db.add(user)
    db.commit()
    db.close()
    
    return RedirectResponse("/login", status_code=303)

@app.post("/login")
def login_form(request: Request, login: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(UserORM).filter(UserORM.login == login).first()
    db.close()
    if not user or user.password != password:
        return templates.TemplateResponse(request, "login.html", {"error": "Неверный логин или пароль"})
    
    request.session["user_id"] = user.id 
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/users/me")
def me(user: UserORM = Depends(get_user)):
    return {"id": user.id, "login": user.login, "role": user.role, "balance": user.balance}


@app.get("/balance")
def balance(user: UserORM = Depends(get_user)):
    return {"balance": user.balance}


@app.post("/balance/deposit")
def deposit_form(request: Request, amount: str = Form(...)):
    try:
        amount_float = float(amount)
    except ValueError:
        return templates.TemplateResponse(request, "dashboard.html", {
    "error": "Введите число",
    "user": get_current_user(request)
        })
    
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    
    amount_float = float(amount)
    deposit(user.id, amount_float)
    return RedirectResponse("/dashboard", status_code=303)


@app.post("/predict-form")
def predict_form(
    request: Request,
    model_id: str = Form(...),
    x1: str = Form("1.2"),
    x2: str = Form("5.7")
):
    """Обработка формы ML-запроса"""
    # Конвертируем
    try:
        model_id_int = int(model_id)
        x1_float = float(x1)
        x2_float = float(x2)
    except ValueError:
        return templates.TemplateResponse(request, "dashboard.html", {
    "error": "Введите корректные числа",
    "user": get_current_user(request)
        })

    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    
    # Получаем пользователя (пока demo id=1)
    db = SessionLocal()
    db_user = db.query(UserORM).filter(UserORM.id == user.id).first()
    model = db.query(MLModelORM).filter(MLModelORM.id == model_id_int).first()
    
    if not model:
        db.close()
        return templates.TemplateResponse(request, "dashboard.html", {
    "error": "Модель не найдена",
    "user": get_current_user(request)
        })
    
    if db_user.balance < model.cost_predict:
        db.close()
        return templates.TemplateResponse(request, "dashboard.html", {
    "error": "Недостаточно средств",
    "user": get_current_user(request)
        })
    
    task_id = str(uuid.uuid4())

    model_name = model.name
    
    # Списание
    db_user.balance -= model.cost_predict
    db.add(TransactionORM(
        type_of_tran="charge",
        summa=model.cost_predict,
        date_time=datetime.now(),
        user_id=db_user.id,
        task_id=task_id
    ))
    db.add(MLTaskORM(
        id=task_id,
        data=json.dumps({"x1": x1_float, "x2": x2_float}),
        status="pending",
        user_id=db_user.id,
        model_id=model.id
    ))
    db.commit()
    db.close()
    
    # Отправка в RabbitMQ
    message = {
    "task_id": task_id,
    "features": {"x1": x1_float, "x2": x2_float},
    "model": model_name,  # ← используйте сохранённую переменную
    "timestamp": datetime.now().isoformat()
    }
    
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_publish(exchange='', routing_key=QUEUE_NAME, body=json.dumps(message))
        connection.close()
    except Exception as e:
        return templates.TemplateResponse(request, "dashboard.html", {"error": f"Ошибка: {e}"})
    
    return RedirectResponse("/dashboard", status_code=303)


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

@app.get("/task/{task_id}")
def get_task(task_id: str, user: UserORM = Depends(get_user)):
    """Получить задачу по task_id"""
    db = SessionLocal()
    task = db.query(MLTaskORM).filter(MLTaskORM.id == task_id).first()
    db.close()
    
    if not task:
        raise HTTPException(404, "Задача не найдена")
    if task.user_id != user.id:
        raise HTTPException(403, "Нет доступа к этой задаче")
    
    return {
        "task_id": task.id,
        "status": task.status,
        "result": task.result,
        "created_at": str(task.created_at)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("APP_PORT", "8000")))

