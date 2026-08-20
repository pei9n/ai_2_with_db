import os
import json
import pika
from datetime import datetime
from database import SessionLocal
from orm_models import MLTaskORM, UserORM, TransactionORM

WORKER_ID = os.getenv("WORKER_ID", "worker-1")
QUEUE_NAME = "ml_tasks"


def update_task_status(task_id, status, result=None):
    """Обновить статус задачи в БД"""
    db = SessionLocal()
    task = db.query(MLTaskORM).filter(MLTaskORM.id == task_id).first()
    if task:
        task.status = status
        if result:
            task.result = result
        db.commit()
    db.close()


def refund_if_needed(task_id):
    """Вернуть средства при ошибке"""
    db = SessionLocal()
    task = db.query(MLTaskORM).filter(MLTaskORM.id == task_id).first()
    if task and task.status == "failed":
        # Находим транзакцию списания
        txn = db.query(TransactionORM).filter(
            TransactionORM.task_id == task_id,
            TransactionORM.type_of_tran == "charge"
        ).first()
        if txn:
            # Возвращаем деньги
            user = db.query(UserORM).filter(UserORM.id == task.user_id).first()
            user.balance += txn.summa
            db.add(TransactionORM(
                type_of_tran="refund",
                summa=txn.summa,
                date_time=datetime.now(),
                user_id=user.id,
                task_id=task_id
            ))
            db.commit()
    db.close()


def callback(ch, method, properties, body):
    """Обработка сообщения"""
    try:
        msg = json.loads(body)
        task_id = msg["task_id"]
        x1 = msg["features"]["x1"]
        x2 = msg["features"]["x2"]
        prediction = round(x1 * 2 + x2 * 3, 2)
        
        result = json.dumps({
            "prediction": prediction,
            "worker_id": WORKER_ID,
            "status": "success"
        })
        
        #  Обновляем статус в БД
        update_task_status(task_id, "completed", result)
        
        print(f"[{WORKER_ID}] Задача {task_id} выполнена: {prediction}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"[{WORKER_ID}] Ошибка: {e}")
        
        # возвращаем деньги
        if 'msg' in locals():
            update_task_status(msg["task_id"], "failed")
            refund_if_needed(msg["task_id"])
        
        ch.basic_ack(delivery_tag=method.delivery_tag)


connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=os.getenv("RABBITMQ_HOST", "rabbitmq"))
)
channel = connection.channel()
channel.queue_declare(queue=QUEUE_NAME, durable=True)
channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

print(f"[{WORKER_ID}] Запущен, жду task")
channel.start_consuming()