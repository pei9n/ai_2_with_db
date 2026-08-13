import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from database import create_tables, SessionLocal
from init_db import init_demo_data
from service import deposit, predict, get_history, get_transactions
from orm_models import UserORM

app = FastAPI(title="ML Digit Recognition API")
security = HTTPBasic()


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=4)


class DepositRequest(BaseModel):
    amount: float = Field(gt=0)


class PredictRequest(BaseModel):
    model_id: int = Field(gt=0)


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
    try:
        result = predict(user.id, data.model_id)
        return {"status": "ok", **result}
    except ValueError as e:
        raise HTTPException(status_code=402, detail=str(e))


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