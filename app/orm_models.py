from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base




class UserORM(Base):
    """Таблица: User"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="user")
    balance = Column(Float, default=0.0)

    # Связи
    transactions = relationship("TransactionORM", back_populates="user")
    tasks = relationship("MLTaskORM", back_populates="user")


class MLModelORM(Base):
    """Таблица: ML_model"""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String)
    cost_predict = Column(Float, nullable=False, default=5.0)


class TransactionORM(Base):
    """Таблица: Transaction (Wallet.transactions)"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type_of_tran = Column(String, nullable=False)  # Deposit или Charge
    summa = Column(Float, nullable=False)
    date_time = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(String, nullable=True)

    # Связь
    user = relationship("UserORM", back_populates="transactions")


class MLTaskORM(Base):
    """Таблица: ML_task"""
    __tablename__ = "ml_tasks"

    id = Column(String, primary_key=True)
    data = Column(String, nullable=True)
    status = Column(String, default="pending")
    result = Column(String, nullable=True)  # JSON-строка с результатом
    created_at = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("ml_models.id"), nullable=False)

    # Связи
    user = relationship("UserORM", back_populates="tasks")