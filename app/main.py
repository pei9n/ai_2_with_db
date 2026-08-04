import os
from fastapi import FastAPI
from init_db import init_demo_data
from service import deposit, charge, predict, get_user, get_history, get_transactions


app = FastAPI()


@app.on_event("startup")
def startup():
    init_demo_data()


@app.get("/")
def home():
    return {"message": "ML сервис работает"}


@app.get("/health")
def health():
    return {"status": "OK"}


@app.get("/users/{user_id}")
def user_info(user_id: int):
    user = get_user(user_id)
    return {"id": user.id, "login": user.login, "role": user.role, "balance": user.balance}


@app.post("/deposit")
def deposit_money(user_id: int, amount: float):
    balance = deposit(user_id, amount)
    return {"status": "ok", "balance": balance}


@app.post("/predict")
def make_prediction(user_id: int, model_id: int):
    try:
        result = predict(user_id, model_id)
        return {"status": "ok", **result}
    except ValueError as e:
        return {"status": "error", "message": str(e)}


@app.get("/history/{user_id}")
def user_history(user_id: int):
    tasks = get_history(user_id)
    return [
        {"id": t.id, "status": t.status, "result": t.result, "date": str(t.created_at)}
        for t in tasks
    ]


@app.get("/transactions/{user_id}")
def user_transactions(user_id: int):
    transactions = get_transactions(user_id)
    return [
        {"type": t.type_of_tran, "summa": t.summa, "date": str(t.date_time)}
        for t in transactions
    ]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("APP_PORT", "8000")))