from sqlalchemy import Column, Integer
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import declarative_base
Base = declarative_base()
class ModelMetric(Base):
    __tablename__ = 'dummy_modelmetric'
    id = Column(Integer, primary_key=True)
