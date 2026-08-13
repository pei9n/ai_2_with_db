import os
import json
import time
from datetime import datetime
import pika

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
QUEUE_NAME = "ml_tasks"
WORKER_ID = os.getenv("WORKER_ID", "worker-1")


def mock_predict(features):
    """Mock ML-модель"""
    result = features.get("x1", 0) * 2 + features.get("x2", 0) * 3
    return round(result, 2)


def process_message(ch, method, properties, body):
    """Обработка сообщения из очереди"""
    try:
        message = json.loads(body)
        task_id = message.get("task_id")
        features = message.get("features", {})
        model_name = message.get("model")
        
        print(f"[{WORKER_ID}] Получена задача: {task_id}")
        print(f"[{WORKER_ID}] Модель: {model_name}")
        print(f"[{WORKER_ID}] Фичи: {features}")
        
        # Валидация
        if not task_id or not features:
            print(f"[{WORKER_ID}] Ошибка: нет task_id или features")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        
        prediction = mock_predict(features)
        
        result = {
            "task_id": task_id,
            "prediction": prediction,
            "worker_id": WORKER_ID,
            "status": "success"
        }
        
        print(f"[{WORKER_ID}] Результат: {json.dumps(result)}")
        print("-" * 50)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"[{WORKER_ID}] Ошибка обработки: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)


def start_worker():
    """Запустить воркер"""
    print(f"[{WORKER_ID}] Запущен, ожидание задач...")
    
    
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
    )
    channel = connection.channel()
    
    
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    
    
    channel.basic_qos(prefetch_count=1)  
    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=process_message
    )
    
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print(f"[{WORKER_ID}] Остановлен")
        connection.close()


if __name__ == "__main__":
    start_worker()