from sqlalchemy import Column, Integer
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import declarative_base
Base = declarative_base()
class CSRFToken(Base):
    __tablename__ = 'dummy_csrftoken'
    id = Column(Integer, primary_key=True)
